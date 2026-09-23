"""Prüft `libreverbum/pipeline.py` — bauplan.md T15, Durchstich für ein Kapitel."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from cli import interaction
from libreverbum import anki, dictionary, epub, extraction, pipeline, profile
from libreverbum.entities import (
    Book,
    Card,
    CardDirection,
    CefrLevel,
    Chapter,
    Event,
    KnowledgeState,
    Lemma,
    Occurrence,
    Origin,
    Sense,
)
from libreverbum.extraction import load_nlp

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from conftest import ModelServerDouble
    from spacy.language import Language

# ------------------------------------------------------------------------- Mini-EPUB
#
# Eigens für diese Datei, nicht die Vorrichtung aus conftest.py: Deren Kapiteltexte
# ("This is the first chapter...") enthalten keines der sieben Stichwörter aus
# mini_dictionary_db, ein Durchlauf fände dort also nie eine Auswahlliste. Der Text unten
# ist auf die Vorrichtung abgestimmt (bauplan.md T2) und enthält zugleich den `saw`-Fall
# (technik.md, „Warum die Reihenfolge zwingend ist"): "saw" muss als Vergangenheitsform
# von "see" erkannt werden, nicht als Säge — dictionary.candidates(..., Lemma("see", ...))
# liefert für das Mini-Wörterbuch folgerichtig eine leere Liste, "see" steht nicht darin.

_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

# Enthält street, bank, red, draw, watch — je genau einmal im Kontext ihrer Wortart aus
# mini_dictionary_db —, "saw" für den Regel-2-Beleg oben, und "gave up" als getrenntes
# Verb-Partikel-Paar (technik.md, „Grenze: rund ein Fünftel der Phrasal Verbs steht
# getrennt") für das Mini-Wörterbuch-Stichwort "give up" (bauplan.md T2). Ohne diesen
# letzten Satz enthielte die Vorrichtung kein einziges Phrasal Verb, obwohl das
# Mini-Wörterbuch eines führt — ein Durchlauf könnte einen fehlenden Aufruf von
# `dictionary.particle_verb_candidates`/`contiguous_candidates` dann nie bemerken
# (Review T15, „Geprüft und in Ordnung", letzter Punkt).
_CHAPTER_1_TEXT = (
    "He walked along a quiet street and saw the old bank stood beside the river, its "
    "walls painted red. She wanted to draw a picture and watch the sunset from there. "
    "In the end she gave up the chase."
)
_CHAPTER_2_TEXT = "This unrelated second chapter names nothing from the dictionary at all."


def _chapter_xhtml(title: str, paragraph: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body><h1>{title}</h1><p>{paragraph}</p></body>
</html>
"""


def _nav_xhtml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chapter1.xhtml">Erstes Kapitel</a></li>
      <li><a href="chapter2.xhtml">Zweites Kapitel</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _package_opf(*, with_navigation: bool) -> str:
    nav_item = (
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml"'
        ' properties="nav"/>\n    '
        if with_navigation
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:pipeline-test</dc:identifier>
    <dc:title>Pipeline-Testbuch</dc:title>
    <dc:creator>Testautorin</dc:creator>
  </metadata>
  <manifest>
    {nav_item}<item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
"""


def _build_pipeline_epub(path: Path, *, with_navigation: bool = True) -> None:
    """Baut ein Zwei-Kapitel-EPUB, dessen erstes Kapitel auf `mini_dictionary_db`
    abgestimmt ist (siehe Kommentar oben) — für die Prüfung von `pipeline.run_chapter`."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _package_opf(with_navigation=with_navigation))
        archive.writestr("OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", _CHAPTER_1_TEXT))
        archive.writestr("OEBPS/chapter2.xhtml", _chapter_xhtml("Zweites Kapitel", _CHAPTER_2_TEXT))
        if with_navigation:
            archive.writestr("OEBPS/nav.xhtml", _nav_xhtml())


@pytest.fixture
def pipeline_epub(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline.epub"
    _build_pipeline_epub(path, with_navigation=True)
    return path


@pytest.fixture
def pipeline_epub_without_navigation(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline_no_nav.epub"
    _build_pipeline_epub(path, with_navigation=False)
    return path


# Reiner Vorspann/Impressum (technik.md §8) nach demselben Muster wie
# tests/test_epub.py, `_LICENSE_ONLY_XHTML`: Die Endmarke steht vor jedem echten Wort, der
# ganze Text fällt beim Aussteuern weg (bauplan-phase2.md AP 4). Bewusst **ohne**
# `_chapter_xhtml`, dessen `<h1>{title}</h1>` ein Wort **vor** die Endmarke setzte und die
# Vorrichtung damit unbrauchbar machte — genau das Wort bliebe nach dem Aussteuern übrig.
_LICENSE_ONLY_CHAPTER_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Lizenz</title></head>
<body>
<p>*** END OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Lizenztext, der komplett aussteuern muss.</p>
</body>
</html>
"""


def _build_pipeline_epub_with_a_chapter_without_text(path: Path) -> None:
    """Wie `_build_pipeline_epub`, aber das zweite Kapitel besteht nur aus Vorspann/
    Impressum (bauplan-phase2.md AP 4) — für `pipeline.list_chapters`s `skip_reason`."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _package_opf(with_navigation=True))
        archive.writestr("OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", _CHAPTER_1_TEXT))
        archive.writestr("OEBPS/chapter2.xhtml", _LICENSE_ONLY_CHAPTER_XHTML)
        archive.writestr("OEBPS/nav.xhtml", _nav_xhtml())


@pytest.fixture
def pipeline_epub_with_a_chapter_without_text(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline_license_only.epub"
    _build_pipeline_epub_with_a_chapter_without_text(path)
    return path


def _build_pipeline_epub_with_a_missing_chapter_document(path: Path) -> None:
    """Wie `_build_pipeline_epub`, aber `chapter2.xhtml` fehlt im Archiv, obwohl Manifest
    und Navigation es nennen — ein echter Fehlschlagweg (kein gepatchter), an dem
    `epub.read_chapter` einen `ValueError` wirft, der **kein** `ChapterWithoutTextError`
    ist (bauplan-phase2.md AP 4, zweiter Prüfweg: „jeder andere ValueError … läuft weiter
    durch")."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _package_opf(with_navigation=True))
        archive.writestr("OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", _CHAPTER_1_TEXT))
        # chapter2.xhtml wird bewusst nicht geschrieben.
        archive.writestr("OEBPS/nav.xhtml", _nav_xhtml())


@pytest.fixture
def pipeline_epub_with_a_missing_chapter_document(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline_missing_document.epub"
    _build_pipeline_epub_with_a_missing_chapter_document(path)
    return path


# Zwei Kapitel, die genau eine unbekannte Grundform teilen ("watch" als Substantiv, in
# mini_dictionary_db vorhanden) — sonst kein gemeinsames Inhaltswort (bauplan-phase2.md
# AP 7, Befund 3, Durchsicht c6f3875: Vereinigung statt Summe fürs Buch).
_SHARED_WORD_CHAPTER_1_TEXT = "She looked at the old watch on the table."
_SHARED_WORD_CHAPTER_2_TEXT = "He also had a golden watch in his pocket."


def _build_two_chapter_epub_sharing_a_word(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _package_opf(with_navigation=True))
        archive.writestr(
            "OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", _SHARED_WORD_CHAPTER_1_TEXT)
        )
        archive.writestr(
            "OEBPS/chapter2.xhtml", _chapter_xhtml("Zweites Kapitel", _SHARED_WORD_CHAPTER_2_TEXT)
        )
        archive.writestr("OEBPS/nav.xhtml", _nav_xhtml())


@pytest.fixture
def pipeline_epub_sharing_a_word(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline_shared_word.epub"
    _build_two_chapter_epub_sharing_a_word(path)
    return path


@pytest.fixture(scope="module")
def nlp() -> Language:
    """Lädt das spaCy-Modell einmal für alle Tests dieser Datei (technik.md §5, rund eine
    Sekunde) — genau die Voraussetzung, die `pipeline.run_chapter` an den Aufrufer stellt."""
    return load_nlp()


@pytest.fixture
def profile_path(tmp_path: Path) -> Path:
    return tmp_path / "profil.sqlite3"


@pytest.fixture
def existing_profile_path(profile_path: Path) -> Path:
    """Wie `profile_path`, nur liegt die Datei schon vor — leer, aber mit angelegtem
    Schema (Befund 1, Durchsicht c6f3875): `assess_book` legt seit dieser Nachbesserung
    nie mehr selbst eine Profildatei an (Entscheidung Dominiks 23.09.2026), jeder Test
    dafür muss die Datei also vorher selbst anlegen — genau das übernimmt diese
    Vorrichtung, damit es nicht in jedem Testkörper wiederholt wird."""
    profile.open_profile(profile_path).close()
    return profile_path


def _entry(result: pipeline.ChapterVocabulary, lemma_text: str) -> pipeline.VocabularyEntry:
    matches = [e for e in result.entries if e.occurrence.lemma.text == lemma_text]
    assert len(matches) == 1, f"{lemma_text!r} genau einmal erwartet, {len(matches)}-mal gefunden"
    return matches[0]


def _expressions(
    result: pipeline.ChapterVocabulary, lemma_text: str
) -> list[pipeline.VocabularyEntry]:
    """Filtert `expressions` nach der Wortfolge. Seit der Entdopplung (mittel 5, Abnahme
    T17, 25.08.2026) liefert das für eine Wortfolge, die beide Wege aus T4 finden — den
    Verb-Partikel-Weg (`Lemma.pos == "VERB"`) und den n-Gramm-Weg (`Lemma.pos == ""`) —,
    genau einen Eintrag (die Partikelverb-Fassung, `pipeline.run_chapter`, „Regeln")."""
    return [e for e in result.expressions if e.occurrence.lemma.text == lemma_text]


def _record_known(con: sqlite3.Connection, sense: Sense, book: Book, chapter_number: int) -> None:
    """Legt die Kapitelzeile an, die `profile.record_event` als Fremdschlüssel braucht
    (`event.chapter_number`, siehe `profile._SCHEMA`), und hängt danach ein `known`-Ereignis
    an. `profile.py` bekommt dafür bewusst keine eigene Schreibfunktion (Regel 14) — dieselbe
    Handhabung wie in `tests/test_profile.py`, `_add_chapter`; ein künftiger Schreibzugriff
    aus `pipeline` (nach T11) müsste dieselbe Zeile anlegen, siehe Bericht."""
    book_id = profile.ensure_book(con, book)
    con.execute(
        "INSERT OR IGNORE INTO chapter (book_id, number, title) VALUES (?, ?, ?)",
        (book_id, chapter_number, "Testkapitel"),
    )
    con.commit()
    profile.record_event(
        con,
        Event(
            sense=sense,
            knowledge_state=KnowledgeState.KNOWN,
            origin=Origin.TRIAGE,
            timestamp=datetime.now(UTC),
            book=book,
            chapter_number=chapter_number,
        ),
    )


# ------------------------------------------------------------------------------ Tests


def test_run_chapter_reads_the_chapter_chosen_by_number(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Bauplan.md T15: `run_chapter` liest das Kapitel, dessen Nummer übergeben wird —
    nicht etwa immer das erste — und liefert dessen Titel und Text unverändert weiter."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=2,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    assert result.chapter.number == 2
    assert result.chapter.title == "Zweites Kapitel"
    assert not any(e.occurrence.lemma.text == "street" for e in result.entries)


def test_run_chapter_raises_for_an_unknown_chapter_number(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Regel 13 (dokumentation.md §4): eine Kapitelnummer, die es im Buch nicht gibt,
    bricht sichtbar ab statt ein leeres Ergebnis zu liefern, das wie ein Kapitel ohne
    Wortschatz aussähe."""
    with pytest.raises(ValueError, match="Kapitel Nummer 99"):
        pipeline.run_chapter(
            epub_path=pipeline_epub,
            chapter_number=99,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
        )


def test_run_chapter_notice_is_none_when_navigation_is_present(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """`BookStructure.notice` (technik.md §8) wird unverändert weitergereicht: Nennt die
    Datei eine Navigation, bleibt der Hinweis aus."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    assert result.notice is None


def test_run_chapter_notice_is_set_when_navigation_is_missing(
    pipeline_epub_without_navigation: Path,
    mini_dictionary_db: Path,
    profile_path: Path,
    nlp: Language,
) -> None:
    """technik.md §8: Fehlt die Navigation, liefert `epub.read_structure` den Hinweis
    `NAVIGATION_MISSING_NOTICE` — `run_chapter` darf ihn nicht verschlucken, sonst bekäme
    der spätere Aufrufer (T16) nie zu sehen, dass die Kapitelgrenzen nicht aus dem Buch
    stammen."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub_without_navigation,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    assert result.notice == epub.NAVIGATION_MISSING_NOTICE


def test_run_chapter_attaches_dictionary_candidates_to_each_occurrence(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Bauplan.md T15: Jedes Vorkommen bekommt genau die Auswahlliste, die
    `dictionary.candidates` für seine Grundform und Wortart liefert — `street`, `red` und
    `watch` je eine Zeile, `bank` und `draw` je zwei (mini_dictionary_db, bauplan.md T2)."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )

    street = _entry(result, "street")
    assert street.occurrence.lemma.pos == "NOUN"
    assert [s.wikdict_trans_list for s in street.candidates] == ["Straße"]

    red = _entry(result, "red")
    assert red.occurrence.lemma.pos == "ADJ"
    assert [s.wikdict_trans_list for s in red.candidates] == ["rot | Rot"]

    watch = _entry(result, "watch")
    assert watch.occurrence.lemma.pos == "VERB"
    assert [s.wikdict_trans_list for s in watch.candidates] == ["beobachten | überwachen | ansehen"]

    bank = _entry(result, "bank")
    assert bank.occurrence.lemma.pos == "NOUN"
    assert len(bank.candidates) == 2

    draw = _entry(result, "draw")
    assert draw.occurrence.lemma.pos == "VERB"
    assert len(draw.candidates) == 2


def test_run_chapter_keeps_the_saw_case_from_scoring_a_saw_meaning(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """technik.md, „Warum die Reihenfolge zwingend ist": "saw" im Belegsatz ist die
    Vergangenheitsform von "see", nicht die Säge. Der Durchstich muss die Grundform "see"
    ans Wörterbuch weiterreichen — das Mini-Wörterbuch kennt "see" nicht, die Auswahlliste
    trägt statt der Säge-Bedeutungen von "saw" nur den unsicheren Platzhalter ohne
    Wörterbucheintrag (Befund mittel, zweite T16-Durchsicht: derselbe Platzhalter wie
    `dictionary.particle_verb_candidates` für ein Phrasal Verb ohne Treffer, damit er auf
    Schreib- und Leseseite gleich aussieht, siehe Moduldocstring `pipeline.py`)."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    see = _entry(result, "see")
    assert len(see.candidates) == 1
    assert see.candidates[0].uncertain is True
    assert see.candidates[0].wikdict_trans_list is None
    assert not any(e.occurrence.lemma.text == "saw" for e in result.entries)


def test_run_chapter_reports_progress_stages_in_order(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Auftragstext vom 02.09.2026, Bauschritt 1/2 der Konsolenausgabe: `run_chapter`
    meldet die vier Etappen aus `pipeline.ChapterStage` in Ablaufreihenfolge — je Kapitel
    des Buchs (`pipeline_epub` hat zwei) einmal `READING_BOOK`, danach einmal
    `ANALYZING_BOOK`, zuletzt je einmal `EXTRACTING_VOCABULARY` und
    `LOOKING_UP_DICTIONARY` mit `done == total == 0`. Der Zähler der Analyse-Etappe nennt
    dabei die Kapitelzahl des **Buchs** (2), nicht die des gewählten Kapitels.

    Verfälschungsprobe: den `on_progress`-Aufruf vor `dictionary.candidate_lists` entfernt
    ließ die Gleichheitsprüfung der vollständigen Etappenfolge rot werden — die letzte
    gemeldete Etappe blieb `EXTRACTING_VOCABULARY`, `LOOKING_UP_DICTIONARY` fehlte ganz."""
    reports: list[pipeline.ChapterProgress] = []
    pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
        on_progress=reports.append,
    )
    stages = [report.stage for report in reports]
    assert stages == (
        [pipeline.ChapterStage.READING_BOOK] * 2
        + [pipeline.ChapterStage.ANALYZING_BOOK] * 2
        + [pipeline.ChapterStage.EXTRACTING_VOCABULARY, pipeline.ChapterStage.LOOKING_UP_DICTIONARY]
    )
    analyzing_reports = [r for r in reports if r.stage is pipeline.ChapterStage.ANALYZING_BOOK]
    assert all(r.total == 2 for r in analyzing_reports)
    assert [r.done for r in analyzing_reports] == [1, 2]
    reading_reports = [r for r in reports if r.stage is pipeline.ChapterStage.READING_BOOK]
    assert all(r.total == 2 for r in reading_reports)
    assert [r.done for r in reading_reports] == [1, 2]
    assert reports[-2] == pipeline.ChapterProgress(
        stage=pipeline.ChapterStage.EXTRACTING_VOCABULARY, done=0, total=0
    )
    assert reports[-1] == pipeline.ChapterProgress(
        stage=pipeline.ChapterStage.LOOKING_UP_DICTIONARY, done=0, total=0
    )


def test_run_chapter_counts_only_chapters_with_text_when_reporting_the_analysis(
    pipeline_epub: Path,
    mini_dictionary_db: Path,
    profile_path: Path,
    nlp: Language,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 6, Durchsicht cf09744: Ein Kapitel ohne Fließtext (Vorspann, Impressum) wird
    beim Lesen übersprungen (`epub.read_chapter` bricht für es ab). `READING_BOOK` zählt es
    trotzdem mit — es steht im Inhaltsverzeichnis und wird angefasst —, `ANALYZING_BOOK`
    nicht mehr, weil es gar nicht erst in `all_chapters` landet. Die beiden Nenner sind
    deshalb verschieden; `cli.main` benennt den kleineren dafür ausdrücklich als Kapitel
    mit Text, damit die schrumpfende Zahl sich selbst erklärt.

    Geprüft an `tools/sherlock.epub` fällt genau ein Kapitel so weg (14 gegen 13); hier
    wird derselbe Fall am kleinen Test-EPUB erzwungen, statt eine Fremdquelle vorauszusetzen.

    Verfälschungsprobe: `ANALYZING_BOOK` mit `total_chapters` statt der Länge von
    `all_chapters` gemeldet (der Zustand, den Befund 6 für die Anzeige beschreibt) ließ die
    Zusicherung auf `[1]` rot werden — gemeldet wurde dann `[2]`, also auch das
    übersprungene Kapitel.

    Wirft seit bauplan-phase2.md AP 4 `epub.ChapterWithoutTextError` statt eines
    allgemeinen `ValueError` — `run_chapter` fängt seither genau diesen Typ, nicht mehr den
    Meldungstext (siehe `test_run_chapter_lets_other_value_errors_through_the_book_wide_
    reading` für den Gegenfall, ein anderer `ValueError`, der **nicht** gefangen wird)."""
    real_read_chapter = epub.read_chapter

    def _skip_the_second_chapter(path: Path, book: Book, chapter: epub.ChapterReference) -> Chapter:
        if chapter.number == 2:
            raise epub.ChapterWithoutTextError(
                f"{path}: Kapitel {chapter.number} besteht nur aus Vorspann bzw. Impressum.",
                skip_reason="besteht nur aus Vorspann bzw. Impressum",
            )
        return real_read_chapter(path, book, chapter)

    monkeypatch.setattr("libreverbum.pipeline.epub.read_chapter", _skip_the_second_chapter)

    reports: list[pipeline.ChapterProgress] = []
    pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
        on_progress=reports.append,
    )

    reading = [r for r in reports if r.stage is pipeline.ChapterStage.READING_BOOK]
    analyzing = [r for r in reports if r.stage is pipeline.ChapterStage.ANALYZING_BOOK]
    assert [r.total for r in reading] == [2, 2], "Die Lese-Etappe zählt jedes Kapitel mit."
    assert [r.total for r in analyzing] == [1], "Die Analyse-Etappe zählt nur Kapitel mit Text."
    assert [r.done for r in analyzing] == [1]


def test_run_chapter_lets_other_value_errors_through_the_book_wide_reading(
    pipeline_epub_with_a_missing_chapter_document: Path,
    mini_dictionary_db: Path,
    profile_path: Path,
    nlp: Language,
) -> None:
    """Bauplan-phase2.md AP 4, zweiter Prüfweg: Ein `ValueError`, der **kein**
    `ChapterWithoutTextError` ist — hier: ein Kapiteldokument fehlt im Archiv, ein echter
    Fehlschlagweg über eine eigens gebaute EPUB-Datei statt eines gepatchten
    `epub.read_chapter` wie im Test oben —, bleibt beim buchweiten Lesen sichtbar und
    bricht `run_chapter` ab, statt als „kein Fließtext" übersprungen zu werden (Regel 13).

    Verfälschungsprobe: den Fang in `run_chapter` von `except epub.ChapterWithoutTextError`
    auf `except ValueError` verbreitert ließ diesen Test rot werden — der fehlende
    Dokumentenfehler wurde dann ebenso stillschweigend übersprungen wie ein Kapitel ohne
    Fließtext, und `run_chapter` lief scheinbar erfolgreich durch."""
    with pytest.raises(ValueError, match="fehlt im Archiv"):
        pipeline.run_chapter(
            epub_path=pipeline_epub_with_a_missing_chapter_document,
            chapter_number=1,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
        )


def test_run_chapter_without_on_progress_behaves_as_before(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Auftragstext vom 02.09.2026: Ein Aufruf ohne `on_progress` verhält sich
    unverändert — Vorgabe `None` heißt kein Rückruf, kein Fehler."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    assert result.chapter.number == 1
    assert _entry(result, "bank").candidates


def test_run_chapter_marks_every_candidate_unknown_against_a_fresh_profile(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Bauplan.md T9/T15: Ohne jedes Ereignis im Profil ist jede Bedeutung `UNKNOWN` —
    kein Kandidat gilt fälschlich als bereits bekannt, nur weil das Profil noch leer ist."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    bank = _entry(result, "bank")
    assert bank.status
    for entry in result.entries:
        assert all(status == profile.VocabularyStatus.UNKNOWN for status in entry.status.values())


def test_run_chapter_with_profile_read_only_does_not_create_a_missing_profile(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: `profile_read_only=True` reicht
    unverändert an `profile.open_profile(read_only=True)` durch (`run_chapter`s
    Docstring) — `assess_book` setzt das Flag, weil sein eigener, vorangestellter
    Lesezugriff die Profildatei schon geprüft hat und der interne `run_chapter`-Aufruf sie
    nicht zusätzlich schreibend anfassen soll. Ohne Profildatei bricht der Aufruf deshalb
    ab, statt (wie im Vorgabe-Schreibzugriff) eine neue anzulegen.

    Verfälschungsprobe (Bericht): `profile_read_only=profile_read_only` im internen
    `profile.open_profile`-Aufruf durch das feste `profile_read_only=False` ersetzt ließ
    diesen Test rot werden — statt der erwarteten `FileNotFoundError` lief der Aufruf
    durch und legte die Profildatei klaglos an."""
    assert not profile_path.is_file()

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        pipeline.run_chapter(
            epub_path=pipeline_epub,
            chapter_number=1,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
            profile_read_only=True,
        )

    assert not profile_path.is_file(), (
        "run_chapter hat trotz profile_read_only=True eine Profildatei angelegt"
    )


def test_run_chapter_reflects_a_known_event_recorded_before_the_run(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """konzept.md, „Der Kernablauf": Der Abgleich gegen das Profil
    läuft nach dem Nachschlagen, gegen die aufgelöste Bedeutung. Ein vorab eingetragenes
    `known`-Ereignis zur Straßen-Bedeutung muss beim nächsten Durchlauf als `KNOWN`
    zurückkommen — Abnahmekriterium 6: bekannte Wörter werden nicht erneut abgefragt."""
    first_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    street_sense = _entry(first_pass, "street").candidates[0]

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, street_sense, first_pass.chapter.book, chapter_number=1)
    finally:
        con.close()

    second_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    street_entry = _entry(second_pass, "street")
    assert street_entry.status[street_entry.candidates[0]] == profile.VocabularyStatus.KNOWN

    other_entry = _entry(second_pass, "watch")
    assert all(status == profile.VocabularyStatus.UNKNOWN for status in other_entry.status.values())


def test_run_chapter_flags_the_sibling_sense_as_a_new_meaning_of_a_known_word(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """konzept.md §5, „Mehrdeutigkeit": Ist die Geldinstitut-Bedeutung von "bank" bereits
    bekannt, muss die Ufer-Bedeutung als `NEW_MEANING_OF_KNOWN_WORD` erscheinen, nicht als
    `UNKNOWN` — sonst verstünde der Nutzer in der Triage nicht, warum ein scheinbar
    bekanntes Wort erneut auftaucht."""

    first_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    bank_candidates = _entry(first_pass, "bank").candidates
    institution = next(s for s in bank_candidates if s.wikdict_trans_list == "Bank")
    edge_of_river = next(s for s in bank_candidates if s.wikdict_trans_list == "Ufer")

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, institution, first_pass.chapter.book, chapter_number=1)
    finally:
        con.close()

    second_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    bank_entry = _entry(second_pass, "bank")
    assert bank_entry.status[institution] == profile.VocabularyStatus.KNOWN
    assert bank_entry.status[edge_of_river] == profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD


def test_run_chapter_attaches_dictionary_matches_to_expression_candidates(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Befund 1 (Review T15): Die Mehrwortausdruck-Kandidaten aus T4
    (`extraction.extract_particle_verb_candidates`, `extract_contiguous_candidates`)
    werden gegen das Wörterbuch abgeglichen, nicht nur im Docstring erwähnt —
    `ChapterVocabulary.expressions` trägt „gave up" (Mini-Wörterbuch-Stichwort „give up",
    bauplan.md T2) mit der vollen Auswahlliste wie ein einzelner Aufruf von
    `dictionary.particle_verb_candidates`.

    mittel 5 (Abnahme T17, 25.08.2026): Beide Wege aus T4 finden dieselbe Wortfolge — den
    Verb-Partikel-Weg (`Lemma.pos == "VERB"`) und den n-Gramm-Weg (`Lemma.pos == ""`) —,
    „gave up" steht danach aber nur **einmal** in `expressions`, mit der informativeren
    Partikelverb-Fassung (`Lemma.pos == "VERB"`), nicht zweimal wie vor dieser Behebung."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )

    give_up_entries = _expressions(result, "give up")
    assert len(give_up_entries) == 1
    entry = give_up_entries[0]
    assert entry.occurrence.lemma.pos == "VERB"
    assert {s.wikdict_trans_list for s in entry.candidates} == {
        "aufgeben | kapitulieren",
        "aufgeben | ergeben",
    }
    assert all(sense.uncertain is False for sense in entry.candidates)
    # Wie bei entries: der Kenntnisstand jeder Bedeutung ist gegen das Profil
    # abgeglichen, nicht nur die Auswahlliste beschafft.
    assert all(status == profile.VocabularyStatus.UNKNOWN for status in entry.status.values())


def _build_prefix_test_epub(path: Path, *, text: str) -> None:
    """Ein-Kapitel-EPUB für `test_run_chapter_drops_a_shorter_expression_dominated_by_a_
    longer_one` — eigens aufgebaut statt über `_build_pipeline_epub`, weil dessen Text und
    `mini_dictionary_db` auf einen anderen Fall abgestimmt sind (mittel 4, Abnahme T17,
    zweiter Anlauf, 26.08.2026)."""
    container_xml = _CONTAINER_XML
    opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:prefix-test</dc:identifier>
    <dc:title>Präfix-Testbuch</dc:title>
    <dc:creator>Testautorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="chap1"/></spine>
</package>"""
    nav = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc"><ol><li><a href="chapter1.xhtml">Erstes Kapitel</a></li></ol></nav>
</body>
</html>"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container_xml)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", text))
        archive.writestr("OEBPS/nav.xhtml", nav)


def _build_prefix_test_dictionary(path: Path) -> None:
    """Wörterbuch für denselben Test: „in front" und „in front of" mit `score ≥ 50`
    (bauplan.md T7), Werte aus `tools/en-de.sqlite3` abgelesen (dort 60,0 respektive
    90,4) — „give up" und „give up on" wie in `mini_dictionary_db`, ergänzt um „give up
    on"."""
    con = sqlite3.connect(path)
    try:
        con.execute(
            "CREATE TABLE translation("
            "lexentry, sense_num, sense, written_rep TEXT, trans_list, score, is_good, importance"
            ")"
        )
        con.executemany(
            "INSERT INTO translation VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "eng/in_front_of__Prepositional_phrase__1",
                    None,
                    "positioned ahead of",
                    "in front of",
                    "vor",
                    90.4,
                    1,
                    1.0,
                ),
                (
                    "eng/in_front__Phrase__1",
                    None,
                    "in a position ahead",
                    "in front",
                    "vorne",
                    60.0,
                    1,
                    1.0,
                ),
                (
                    "eng/give_up__Verb__1",
                    None,
                    "admit defeat",
                    "give up",
                    "aufgeben",
                    120.0,
                    1,
                    1.73,
                ),
                (
                    "eng/give_up_on__Verb__1",
                    None,
                    "stop believing in",
                    "give up on",
                    "aufgeben",
                    100.0,
                    1,
                    1.0,
                ),
            ],
        )
        con.commit()
    finally:
        con.close()


def test_run_chapter_drops_a_shorter_expression_dominated_by_a_longer_one(
    tmp_path: Path, nlp: Language
) -> None:
    """mittel 4 (Abnahme T17, zweiter Anlauf, 26.08.2026): „in front" und „in front of"
    trugen bislang denselben Belegsatz und standen beide in `expressions`, weil die
    Entdopplung aus mittel 5 (07be96c) nur identische Wortfolgen vergleicht — jedes
    Vorkommen von „in front of" erzeugt in `extraction.extract_contiguous_candidates`
    zugleich ein Vorkommen seines Präfixes „in front", beide also mit derselben Häufigkeit
    und denselben Textstellen. `pipeline._drop_prefix_dominated_expressions` lässt die
    kürzere Fassung jetzt fallen, wenn eine längere Wendung ihr Wortfolge-Präfix ist und
    dieselbe Häufigkeit trägt.

    Gegenprobe im selben Durchlauf: „give up" (dreimal, davon einmal als „give up on")
    bleibt neben „give up on" (einmal) bestehen — unterschiedliche Häufigkeit heißt, „give
    up" hat eigenständige Vorkommen außerhalb von „give up on" und darf nicht verschwinden
    (Auftragstext, „give up gegen give up on wäre so ein Fall")."""
    text = (
        "The heavy curtains hung in front of the window. A tall vase stood in front of "
        "the door. He walked in front of the mirror without looking. He finally gave up. "
        "She tried hard, but she also gave up. In the end, she gave up on the whole idea."
    )
    epub_path = tmp_path / "prefix.epub"
    _build_prefix_test_epub(epub_path, text=text)
    dictionary_path = tmp_path / "en-de.sqlite3"
    _build_prefix_test_dictionary(dictionary_path)
    dictionary.ensure_index(dictionary_path)

    result = pipeline.run_chapter(
        epub_path=epub_path,
        chapter_number=1,
        dictionary_path=dictionary_path,
        profile_path=tmp_path / "profil.sqlite3",
        nlp=nlp,
    )

    lemma_texts = {e.occurrence.lemma.text for e in result.expressions}
    assert "in front" not in lemma_texts
    in_front_of = _expressions(result, "in front of")
    assert len(in_front_of) == 1
    assert in_front_of[0].occurrence.frequency == 3

    give_up = _expressions(result, "give up")
    give_up_on = _expressions(result, "give up on")
    assert len(give_up) == 1
    assert len(give_up_on) == 1
    assert give_up[0].occurrence.frequency == 3
    assert give_up_on[0].occurrence.frequency == 1


def test_run_chapter_checks_the_dictionary_file_before_extracting_any_vocabulary(
    pipeline_epub: Path,
    profile_path: Path,
    nlp: Language,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 3 (Review T15), Regel 13 (dokumentation.md §4): Die Wörterbuchdatei wird
    geprüft, bevor überhaupt extrahiert wird. Vor dieser Behebung steckte die Prüfung
    allein in `dictionary.candidates`, das nie aufgerufen wurde, sobald
    `extraction.extract_vocabulary` kein einziges Vorkommen fand (etwa bei einem Kapitel
    aus lauter Eigennamen) — `run_chapter` lieferte dann ein leeres, aber scheinbar
    erfolgreiches Ergebnis, statt sichtbar abzubrechen.

    `extraction.extract_vocabulary` wird hier durch eine Attrappe ersetzt, die bei jedem
    Aufruf abbricht: `pytest.raises(FileNotFoundError)` besteht nur, wenn `run_chapter`
    die Wörterbuchprüfung erreicht, **bevor** diese Attrappe je aufgerufen wird — würde
    stattdessen zuerst extrahiert, schlüge der Test mit der Attrappen-Ausnahme fehl, nicht
    mit `FileNotFoundError`."""

    def _must_not_be_called(*args: object, **kwargs: object) -> list[object]:
        raise AssertionError(
            "extraction.extract_vocabulary wurde vor der Wörterbuchprüfung aufgerufen"
        )

    monkeypatch.setattr(extraction, "extract_vocabulary", _must_not_be_called)
    missing_dictionary = tmp_path / "fehlt.sqlite3"

    with pytest.raises(FileNotFoundError):
        pipeline.run_chapter(
            epub_path=pipeline_epub,
            chapter_number=1,
            dictionary_path=missing_dictionary,
            profile_path=profile_path,
            nlp=nlp,
        )


# --------------------- Zwischenspeicher für den buchweiten Eigennamenanteil (15.09.2026)


class _FakeNlp:
    """Steht für ein geladenes spaCy-Modell, soweit `_proper_noun_ratio_cache_key` es
    braucht — nur `.meta`, kein echtes Sprachmodell. Ein echtes `nlp` liefe für jede
    Kennungsvariante erneut eine Sekunde Ladezeit ein, ohne dass diese Tests je ein Token
    verarbeiten (technik.md §5)."""

    def __init__(self, meta: dict[str, str]) -> None:
        self.meta = meta


def _fake_nlp(meta: dict[str, str]) -> Language:
    """Tarnt `_FakeNlp` als `Language` für den Typprüfer — dieselbe Bauart wie
    `cast("Language", None)` in `tests/test_cli_main.py`: Die Attrappe erfüllt nur den
    Ausschnitt der Schnittstelle, den `_proper_noun_ratio_cache_key` tatsächlich anfasst
    (`.meta`), nicht die volle `Language`-Schnittstelle.

    Führt `spacy_version` als festen Anforderungsbereich mit (wie ihn ein echtes `nlp.meta`
    trägt, „>=3.8.0,<3.9.0" bei `en_core_web_md` 3.8.0) — sonst prüfte
    `test_proper_noun_ratio_cache_key_differs_for_a_different_installed_spacy_version` die
    Falle aus dem Auftragstext gar nicht sauber isoliert: Läse `_proper_noun_ratio_cache_key`
    versehentlich `nlp.meta['spacy_version']` statt `spacy.about.__version__`, bliebe dieser
    Wert hier über beide Aufrufe hinweg gleich, während jeder andere Test in diesem
    Abschnitt unverändert bestünde, weil er eine andere Zutat der Kennung variiert."""
    full_meta = {"spacy_version": ">=3.8.0,<3.9.0", **meta}
    return cast("Language", _FakeNlp(full_meta))


def test_proper_noun_ratio_cache_key_differs_for_a_different_epub_file(tmp_path: Path) -> None:
    """Auftragstext vom 15.09.2026, Punkt 2: Eine geänderte EPUB-Datei ergibt einen anderen
    Dateinamen — die Kennung trägt den SHA-256 der vollen Bytes, nicht nur den Dateinamen
    oder die Dateigröße."""
    file_a = tmp_path / "a.epub"
    file_b = tmp_path / "b.epub"
    file_a.write_bytes(b"erster Buchinhalt")
    file_b.write_bytes(b"zweiter Buchinhalt")
    fake_nlp = _fake_nlp({"name": "core_web_md", "version": "3.8.0"})

    assert pipeline._proper_noun_ratio_cache_key(
        file_a, fake_nlp
    ) != pipeline._proper_noun_ratio_cache_key(file_b, fake_nlp)


def test_proper_noun_ratio_cache_key_is_stable_for_unchanged_input(tmp_path: Path) -> None:
    """Gegenprobe zum vorigen Test: dieselbe Datei, dasselbe `nlp.meta` ergibt zweimal
    dieselbe Kennung — sonst träfe ein Zwischenspeicher nie, selbst beim unveränderten
    Buch."""
    epub_path = tmp_path / "buch.epub"
    epub_path.write_bytes(b"unveraenderter Inhalt")
    fake_nlp = _fake_nlp({"name": "core_web_md", "version": "3.8.0"})

    assert pipeline._proper_noun_ratio_cache_key(
        epub_path, fake_nlp
    ) == pipeline._proper_noun_ratio_cache_key(epub_path, fake_nlp)


def test_proper_noun_ratio_cache_key_differs_for_a_different_installed_spacy_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auftragstext vom 15.09.2026, Punkt 2: eine andere installierte spaCy-Fassung ergibt
    einen anderen Dateinamen. Geprüft über `spacy.about.__version__` — dieselbe Fassung,
    die `spacy.__version__` nach außen reicht (`spacy/__init__.py`, `from .about import
    __version__`) —, **nicht** `nlp.meta['spacy_version']`: Letzteres ist bei
    `en_core_web_md` der Anforderungsbereich `'>=3.8.0,<3.9.0'` der Modelldatei, ändert
    sich mit einer neuen spaCy-Fassung also gerade nicht (die Falle aus dem Auftragstext)."""
    import spacy.about

    epub_path = tmp_path / "buch.epub"
    epub_path.write_bytes(b"Inhalt")
    fake_nlp = _fake_nlp({"name": "core_web_md", "version": "3.8.0"})

    key_before = pipeline._proper_noun_ratio_cache_key(epub_path, fake_nlp)
    monkeypatch.setattr(spacy.about, "__version__", "9.9.9")
    key_after = pipeline._proper_noun_ratio_cache_key(epub_path, fake_nlp)

    assert key_before != key_after


def test_proper_noun_ratio_cache_key_differs_for_a_different_model_name_or_version(
    tmp_path: Path,
) -> None:
    """Auftragstext vom 15.09.2026, Punkt 2: ein anderer Modellname oder eine andere
    Modellfassung (`nlp.meta['name']`/`nlp.meta['version']`) ergibt je einen anderen
    Dateinamen."""
    epub_path = tmp_path / "buch.epub"
    epub_path.write_bytes(b"Inhalt")

    key_md = pipeline._proper_noun_ratio_cache_key(
        epub_path, _fake_nlp({"name": "core_web_md", "version": "3.8.0"})
    )
    key_lg = pipeline._proper_noun_ratio_cache_key(
        epub_path, _fake_nlp({"name": "core_web_lg", "version": "3.8.0"})
    )
    key_newer_version = pipeline._proper_noun_ratio_cache_key(
        epub_path, _fake_nlp({"name": "core_web_md", "version": "3.9.0"})
    )

    assert len({key_md, key_lg, key_newer_version}) == 3


def test_write_proper_noun_ratio_cache_is_read_back_unchanged(tmp_path: Path) -> None:
    """Auftragstext vom 15.09.2026, Punkt 6: geschrieben wird mit `encoding='utf-8'`
    (CLAUDE.md) — die Umlaute in `café` prüfen das — und atomar: Nach dem Schreiben bleibt
    keine `.part`-Nebendatei liegen (dieselbe Bauart wie `dictionary.fetch_dictionary`).

    Befund 3 (Durchsicht 8e3d054): `json.dump`s Vorgabe `ensure_ascii=True` hätte `café`
    als `caf\\u00e9` abgelegt — auf dem Umweg über den Rücklesetest nicht von einer echten
    UTF-8-Datei zu unterscheiden. Geprüft wird deshalb zusätzlich der rohe Dateiinhalt:
    `é` muss dort als das eine UTF-8-Zeichen stehen, nicht als sechsstellige Escape-Folge."""
    path = tmp_path / "cache" / "book_proper_noun_ratios_test.json"
    ratios = {"street": 0.42, "bank": 0.0, "café": 0.75}

    pipeline._write_proper_noun_ratio_cache(path, ratios)

    assert pipeline._read_proper_noun_ratio_cache(path) == ratios
    raw = path.read_text(encoding="utf-8")
    assert "café" in raw
    assert "\\u00e9" not in raw
    # (Befund 4, Durchsicht 8e3d054): Der Temporärname trägt seit der Behebung zusätzlich
    # die Prozesskennung (`os.getpid()`) statt nur der Kennung im Dateinamen — die Prüfung
    # sucht deshalb per Muster, nicht mehr nach dem einen früheren Namen.
    assert not list(path.parent.glob(f"{path.name}.*.part"))


def test_write_proper_noun_ratio_cache_leaves_an_existing_file_untouched_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 3 (Durchsicht 8e3d054): Der Docstring behauptet „atomar", ungeprüft blieb
    bislang, was das bedeutet — die Verfälschung „ohne Temporärdatei direkt in die
    Zieldatei schreiben" wäre bei den bisherigen Tests grün geblieben, weil keiner von
    ihnen einen Fehlschlag *während* des Schreibens auslöst. Zusicherung: Scheitert
    `json.dump` mitten im Schreiben, bleibt eine bereits vorhandene Zieldatei mit ihrem
    alten Inhalt unverändert liegen — ein direktes Schreiben in die Zieldatei hätte sie
    stattdessen halb überschrieben oder geleert."""
    path = tmp_path / "cache" / "book_proper_noun_ratios_test.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"street": 0.5}', encoding="utf-8")

    def _broken_dump(*args: object, **kwargs: object) -> None:
        raise RuntimeError("absichtlicher Fehlschlag mitten im Schreiben")

    monkeypatch.setattr(json, "dump", _broken_dump)

    with pytest.raises(RuntimeError):
        pipeline._write_proper_noun_ratio_cache(path, {"bank": 0.9})

    assert path.read_text(encoding="utf-8") == '{"street": 0.5}'
    assert not list(path.parent.glob(f"{path.name}.*.part"))


def test_write_proper_noun_ratio_cache_uses_a_process_specific_temporary_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 4 (Durchsicht 8e3d054): Der Temporärname war bislang je Kennung geteilt, nicht
    je Prozess (`<Kennung>.part`) — zwei gleichzeitige Läufe über dasselbe Buch schrieben
    dadurch in dieselbe Temporärdatei, reproduziert in 3 von 3 Runden, einmal mit einer
    Bytemischung beider Schreiber in der Zieldatei. Zusicherung: Der Temporärname trägt die
    eigene Prozesskennung (`os.getpid()`), geprüft am tatsächlich geöffneten Pfad, nicht nur
    am fertigen Dateinamen — sonst bestünde der Test auch dann, wenn die Kennung irgendwo
    im Pfad, aber nicht im Temporärnamen selbst stünde."""
    path = tmp_path / "cache" / "book_proper_noun_ratios_test.json"
    opened_paths: list[Path] = []
    real_open = Path.open

    def _spying_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        opened_paths.append(self)
        return cast("Any", real_open)(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _spying_open)
    monkeypatch.setattr(os, "getpid", lambda: 424242)

    pipeline._write_proper_noun_ratio_cache(path, {"street": 0.5})

    assert len(opened_paths) == 1
    assert opened_paths[0].name == f"{path.name}.424242.part"


def test_write_proper_noun_ratio_cache_raises_a_german_message_when_the_directory_is_blocked(
    tmp_path: Path,
) -> None:
    """Befund 5 (Durchsicht 8e3d054): Liegt an der Stelle des Zwischenspeicherverzeichnisses
    bereits eine Datei, bricht `Path.mkdir` mit einem `OSError` ab (unter Windows
    `FileExistsError [WinError 183]`) — ein `OSError`, den `cli.main.main`s Fang
    (`except (ValueError, FileNotFoundError)`) nicht kennt und deshalb als nackten,
    englischen Traceback durchließe (Bruch der Sprachregel, dokumentation.md §1). Der
    `OSError` wird deshalb hier an der Quelle in einen `ValueError` mit deutscher Meldung
    umgewandelt, die den vollen Pfad nennt und sagt, dass die Berechnung gelungen ist und
    nur die Ablage gescheitert ist."""
    blocked_cache_dir = tmp_path / "cache"
    blocked_cache_dir.write_text("blockiert das Verzeichnis", encoding="utf-8")
    path = blocked_cache_dir / "book_proper_noun_ratios_test.json"

    with pytest.raises(ValueError, match="Berechnung") as error:
        pipeline._write_proper_noun_ratio_cache(path, {"street": 0.5})
    assert str(path) in str(error.value)


def test_read_proper_noun_ratio_cache_returns_none_when_the_file_is_missing(tmp_path: Path) -> None:
    """Eine fehlende Datei ist der Normalfall beim ersten Lauf über ein Buch — `None`,
    keine Meldung, keine Ausnahme (Auftragstext vom 15.09.2026, Punkt 7)."""
    missing = tmp_path / "book_proper_noun_ratios_missing.json"

    assert pipeline._read_proper_noun_ratio_cache(missing) is None


def test_read_proper_noun_ratio_cache_raises_and_names_the_path_for_broken_json(
    tmp_path: Path,
) -> None:
    """Auftragstext vom 15.09.2026, Punkt 7: Eine Datei, deren Name trifft, die sich aber
    nicht lesen lässt, bricht sichtbar ab (Regel 13) und nennt den vollen Pfad der Datei,
    die zu löschen ist — statt sie stillschweigend zu übergehen oder zu überschreiben."""
    path = tmp_path / "book_proper_noun_ratios_broken.json"
    path.write_text("das ist kein JSON {{{", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        pipeline._read_proper_noun_ratio_cache(path)
    assert str(path) in str(error.value)


def test_read_proper_noun_ratio_cache_raises_and_names_the_path_for_the_wrong_shape(
    tmp_path: Path,
) -> None:
    """Wie der vorige Test, aber für gültiges JSON in der falschen Form (eine Liste statt
    einer Grundform-Anteil-Tabelle) — auch das ist kein Normalfall, sondern ein Befund
    (Auftragstext vom 15.09.2026, Punkt 7)."""
    path = tmp_path / "book_proper_noun_ratios_wrong_shape.json"
    path.write_text('["street", "bank"]', encoding="utf-8")

    with pytest.raises(ValueError) as error:
        pipeline._read_proper_noun_ratio_cache(path)
    assert str(path) in str(error.value)


def test_read_proper_noun_ratio_cache_matches_a_fresh_computation(
    pipeline_epub: Path, nlp: Language, tmp_path: Path
) -> None:
    """Auftragstext vom 15.09.2026: ein Treffer im Zwischenspeicher liefert dieselbe
    Tabelle wie `extraction.book_proper_noun_ratios` selbst — geschrieben wird die volle
    Tabelle, nicht nur die Werte oberhalb von `extraction._PROPER_NOUN_RATIO_THRESHOLD`
    (Auftragstext, Punkt 3)."""
    structure = epub.read_structure(pipeline_epub)
    chapters = [
        epub.read_chapter(pipeline_epub, structure.book, reference)
        for reference in structure.chapters
    ]
    computed = extraction.book_proper_noun_ratios(chapters, nlp)

    cache_path = tmp_path / "cache" / "book_proper_noun_ratios_test.json"
    pipeline._write_proper_noun_ratio_cache(cache_path, computed)

    assert pipeline._read_proper_noun_ratio_cache(cache_path) == computed


def test_run_chapter_does_not_recompute_proper_noun_ratios_on_a_cache_hit(
    pipeline_epub: Path,
    mini_dictionary_db: Path,
    profile_path: Path,
    nlp: Language,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auftragstext vom 15.09.2026: Ein Treffer im Zwischenspeicher ruft
    `extraction.book_proper_noun_ratios` nicht erneut auf — geprüft an einer Attrappe, die
    bei jedem Aufruf abbricht (dokumentation.md §5, „Woran geprüft wird"). Bestünde
    `run_chapter` trotz Treffer weiterhin auf dem vollen Buchlauf, schlüge dieser Test mit
    der Attrappen-Ausnahme fehl, statt mit dem erwarteten Ergebnis durchzulaufen.

    Prüft nur, dass kein erneuter Buchlauf stattfindet — nicht, dass der Treffer dasselbe
    Ergebnis liefert wie ein kalter Lauf (Befund 1, Durchsicht 8e3d054: Das synthetische
    Mini-EPUB hier hat dafür zu wenige Eigennamen, siehe
    `test_run_chapter_returns_the_same_vocabulary_on_a_cache_hit_as_cold` weiter unten, die
    das an `tools/sherlock.epub` zusichert)."""
    cache_dir = tmp_path / "cache"
    cache_key = pipeline._proper_noun_ratio_cache_key(pipeline_epub, nlp)
    cache_path = pipeline._proper_noun_ratio_cache_path(cache_dir, cache_key)
    pipeline._write_proper_noun_ratio_cache(cache_path, {"street": 0.5})

    def _must_not_be_called(*args: object, **kwargs: object) -> dict[str, float]:
        raise AssertionError(
            "extraction.book_proper_noun_ratios wurde trotz Zwischenspeicher-Treffer "
            "erneut aufgerufen"
        )

    monkeypatch.setattr(extraction, "book_proper_noun_ratios", _must_not_be_called)

    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )

    assert result.chapter.number == 1


def test_run_chapter_writes_the_proper_noun_ratio_cache_on_a_cold_run(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language, tmp_path: Path
) -> None:
    """Befund 2 (Durchsicht 8e3d054): Bislang prüfte kein Test über `run_chapter` selbst,
    dass ein kalter Lauf mit `cache_dir` überhaupt eine Zwischenspeicherdatei anlegt — nur
    `_write_proper_noun_ratio_cache` direkt aufgerufen war geprüft. Ein abgeschalteter
    Schreibaufruf in `run_chapter` (etwa `if False: _write_proper_noun_ratio_cache(...)`)
    hätte alle bisherigen Tests unverändert grün gelassen: Der Zwischenspeicher träfe nie,
    das Merkmal wäre wirkungslos. Zusicherung: Nach einem kalten Lauf mit `cache_dir` liegt
    unter dem von `_proper_noun_ratio_cache_key`/`_proper_noun_ratio_cache_path` berechneten
    Namen eine lesbare Datei mit der buchweiten Eigennamen-Tabelle."""
    cache_dir = tmp_path / "cache"
    cache_key = pipeline._proper_noun_ratio_cache_key(pipeline_epub, nlp)
    cache_path = pipeline._proper_noun_ratio_cache_path(cache_dir, cache_key)
    assert not cache_path.exists()

    pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )

    written = pipeline._read_proper_noun_ratio_cache(cache_path)
    assert written is not None
    assert written  # nicht-leere Tabelle: das Mini-EPUB trägt Vorkommen bei


def test_run_chapter_token_count_is_correct_even_with_a_stale_ratio_cache_entry(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language, tmp_path: Path
) -> None:
    """bauplan-phase2.md AP 6, „Die Falle": Der Zwischenspeicher unter `cache_dir` enthält
    ausschließlich `extraction.book_proper_noun_ratios` (Grundform → Anteil, technik.md
    §5) — nie `ChapterVocabulary.token_count`. Ein Eintrag von **vor** diesem Feld sieht
    im Dateiformat nicht anders aus als einer von heute (dasselbe `dict[str, float]`,
    `_write_proper_noun_ratio_cache` und `_read_proper_noun_ratio_cache` sind durch AP 6
    unverändert) — es gibt also gar keinen alten, token_count-losen Eintrag, vor dem
    `token_count` sich schützen müsste. `token_count` entsteht bei jedem Aufruf frisch aus
    `extraction.extract_vocabulary` für das gewählte Kapitel (`pipeline.run_chapter`), ganz
    unabhängig davon, ob der Ratio-Zwischenspeicher trifft oder nicht.

    Zusicherung: Eine von Hand schon vor dem Lauf angelegte Zwischenspeicherdatei (eine
    beliebige, nicht aus dem echten Kapitel abgeleitete Ratio-Tabelle — genau das Format,
    das auch vor AP 6 dort lag) ändert `token_count` gegenüber einer frischen Berechnung
    ohne Zwischenspeicher nicht. Verfälschungsprobe: Würde `token_count` versehentlich aus
    dem Zwischenspeicher gelesen statt aus `extraction.extract_vocabulary` neu berechnet,
    läge hier `0` (das Attrappen-Objekt „book_proper_noun_ratios" trägt keinen
    Tokenzähler) statt der echten Wortzahl des Mini-Kapitels — dieser Test bestünde dann
    nicht mehr."""
    structure = epub.read_structure(pipeline_epub)
    chapter = epub.read_chapter(pipeline_epub, structure.book, structure.chapters[0])
    expected_token_count = extraction.extract_vocabulary(chapter, nlp).token_count

    cache_dir = tmp_path / "cache"
    cache_key = pipeline._proper_noun_ratio_cache_key(pipeline_epub, nlp)
    cache_path = pipeline._proper_noun_ratio_cache_path(cache_dir, cache_key)
    # Eine "alte" Zwischenspeicherdatei — von Hand geschrieben, im selben Format wie vor
    # AP 6: eine Ratio-Tabelle ohne jeden Bezug zu token_count.
    pipeline._write_proper_noun_ratio_cache(cache_path, {"street": 0.5})

    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )

    assert result.token_count == expected_token_count
    assert result.token_count > 0


def test_run_chapter_without_a_cache_dir_behaves_as_before(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """`cache_dir=None` (Vorgabe) heißt ausdrücklich kein Zwischenspeicher — unverändertes
    Verhalten gegenüber dem Durchlauf vor dieser Behebung."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    assert result.chapter.number == 1


def test_run_chapter_raises_for_a_profile_file_with_a_foreign_table(
    pipeline_epub: Path, mini_dictionary_db: Path, tmp_path: Path, nlp: Language
) -> None:
    """Befund 5 (Review T15), Regel 13 (dokumentation.md §4): Eine Profildatei mit einer
    fremden Tabelle bricht sichtbar mit `ValueError` ab (`profile.open_profile`), statt
    dass `run_chapter` den Fehlschlag verschluckt — der Docstring von `run_chapter`
    behauptet ausdrücklich, dass eine ungültige Profildatei durchreicht."""
    foreign_profile = tmp_path / "profil.sqlite3"
    con = sqlite3.connect(foreign_profile)
    con.execute("CREATE TABLE unrelated(id INTEGER)")
    con.commit()
    con.close()

    with pytest.raises(ValueError, match="Schemaversion"):
        pipeline.run_chapter(
            epub_path=pipeline_epub,
            chapter_number=1,
            dictionary_path=mini_dictionary_db,
            profile_path=foreign_profile,
            nlp=nlp,
        )


@pytest.mark.needs_epub
@pytest.mark.needs_dictionary
def test_run_chapter_processes_a_real_chapter_with_the_real_dictionary(
    tmp_path: Path, real_epub_paths: dict[str, Path], real_dictionary_path: Path, nlp: Language
) -> None:
    """dokumentation.md §5, „Woran geprüft wird": Was über den Inhalt einer Fremdquelle
    behauptet wird, wird zusätzlich gegen das echte Gegenüber geprüft — hier, dass der
    Durchstich an einem echten Kapitel mit dem echten Wörterbuch überhaupt durchläuft und
    Auswahllisten liefert, nicht nur an der handgebauten Vorrichtung.

    Arbeitet auf einer **Kopie** von `tools/en-de.sqlite3` mit angelegtem Index
    (Auftragstext, „Achtung Laufzeit"): Ohne Index kostet ein Kapitel dieser Größe Minuten
    (technik.md §3, „Der Engpass ist das Nachschlagen, nicht das Modell"), und die
    Nutzerdatei bleibt unverändert.

    Befund 6 (Review T15): Die Schwellen `> 500` / `> 100` blieben weit unter dem
    tatsächlichen Bestand (1.410 Vorkommen, 91,6 % mit Auswahlliste, gemessen am 2. Kapitel
    „A Scandal in Bohemia") und hätten selbst einen Verlust von neun Zehnteln der
    Auswahllisten — etwa durch einen wieder eingebauten Wortartfehler — nicht bemerkt. Dazu
    eine Aussage über den Inhalt selbst, wie `test_dictionary.py` sie gegen die echte Datei
    trifft: „woman" ist im Kapitel unzweideutig und liefert in `tools/en-de.sqlite3` genau
    eine Zeile, deren Übersetzung „Frau" enthält.
    """
    dictionary_copy = tmp_path / "en-de.sqlite3"
    shutil.copyfile(real_dictionary_path, dictionary_copy)
    dictionary.ensure_index(dictionary_copy)

    structure = epub.read_structure(real_epub_paths["sherlock"])
    # Kapitel 2 ("A Scandal in Bohemia") statt Kapitel 1 (nur ein Inhaltsverzeichnis mit
    # sechs Vorkommen) — ein echtes Erzählkapitel, an dem eine leere Auswahlliste über die
    # ganze Länge etwas verschwiege.
    chapter_number = structure.chapters[1].number

    result = pipeline.run_chapter(
        epub_path=real_epub_paths["sherlock"],
        chapter_number=chapter_number,
        dictionary_path=dictionary_copy,
        profile_path=tmp_path / "profil.sqlite3",
        nlp=nlp,
    )

    assert len(result.entries) > 1300
    # (Befund mittel, zweite T16-Durchsicht): Eine leere Auswahlliste trägt seither den
    # Platzhalter Sense(uncertain=True) statt einer leeren Liste (Moduldocstring
    # `pipeline.py`) — "mit Kandidaten" heißt hier deshalb "mit einem echten
    # Wörterbucheintrag", nicht nur "candidates nicht leer".
    entries_with_real_candidates = [
        entry
        for entry in result.entries
        if entry.candidates and not (len(entry.candidates) == 1 and entry.candidates[0].uncertain)
    ]
    assert len(entries_with_real_candidates) / len(result.entries) > 0.8
    assert all(
        status == profile.VocabularyStatus.UNKNOWN
        for entry in result.entries
        for status in entry.status.values()
    )

    # Befund 6 (Review T15): Aussage über den Inhalt, nicht nur über die Menge — "woman"
    # ist im Kapitel unzweideutig (Lemma-Vorrichtungshelfer _entry erzwingt das ohnehin,
    # sonst schlüge er mit mehr als einem Treffer fehl).
    woman = _entry(result, "woman")
    assert woman.occurrence.lemma.pos == "NOUN"
    assert any("Frau" in (sense.wikdict_trans_list or "") for sense in woman.candidates)


@pytest.mark.needs_epub
@pytest.mark.needs_dictionary
def test_run_chapter_returns_the_same_vocabulary_on_a_cache_hit_as_cold(
    tmp_path: Path, real_epub_paths: dict[str, Path], real_dictionary_path: Path, nlp: Language
) -> None:
    """Befund 1 (Durchsicht 8e3d054): `test_run_chapter_does_not_recompute_proper_noun_
    ratios_on_a_cache_hit` sicherte bislang nur zu, dass der Treffer-Lauf überhaupt
    durchläuft (`result.chapter.number == 1`) — nicht, dass er dasselbe Ergebnis liefert
    wie der kalte. Die Verfälschung „die geladene Tabelle beim Treffer durch `{}` ersetzen"
    ließ jene Attrappen-Vorrichtung unverändert grün, veränderte aber das echte Ergebnis: An
    `tools/sherlock.epub` Kapitel 2 stehen kalt 1410 Einträge, mit einer leeren Tabelle an
    der Cache-Hit-Stelle nur 1409 — der buchweite Eigennamenfilter (technik.md §5) verhält
    sich anders, sobald die tatsächlich geladene Tabelle nicht ankommt. Das synthetische
    Mini-EPUB der übrigen Tests trägt zu wenige Eigennamen, um diesen Unterschied zu zeigen
    (dokumentation.md §5, „Woran geprüft wird" — die Vorrichtung zeigt Laufen, nicht
    Stimmen); nur der Vergleich am echten Buch deckt ihn auf.

    Arbeitet wie `test_run_chapter_processes_a_real_chapter_with_the_real_dictionary` auf
    einer Kopie von `tools/en-de.sqlite3` mit angelegtem Index."""
    dictionary_copy = tmp_path / "en-de.sqlite3"
    shutil.copyfile(real_dictionary_path, dictionary_copy)
    dictionary.ensure_index(dictionary_copy)

    structure = epub.read_structure(real_epub_paths["sherlock"])
    chapter_number = structure.chapters[1].number  # Kapitel 2, "A Scandal in Bohemia"
    cache_dir = tmp_path / "cache"

    cold_result = pipeline.run_chapter(
        epub_path=real_epub_paths["sherlock"],
        chapter_number=chapter_number,
        dictionary_path=dictionary_copy,
        profile_path=tmp_path / "profil_kalt.sqlite3",
        nlp=nlp,
        cache_dir=cache_dir,
    )
    warm_result = pipeline.run_chapter(
        epub_path=real_epub_paths["sherlock"],
        chapter_number=chapter_number,
        dictionary_path=dictionary_copy,
        profile_path=tmp_path / "profil_treffer.sqlite3",
        nlp=nlp,
        cache_dir=cache_dir,
    )

    assert warm_result == cold_result


# ------------------------------------------------------- list_chapters (bauplan-phase2.md AP 4)


def test_list_chapters_reports_normal_chapters_without_a_skip_reason(pipeline_epub: Path) -> None:
    """Ein Kapitel mit Fließtext bekommt seinen echten Wortumfang und `skip_reason=None`."""
    listings = pipeline.list_chapters(pipeline_epub)

    assert [listing.number for listing in listings] == [1, 2]
    assert all(listing.skip_reason is None for listing in listings)
    assert all(
        isinstance(listing.word_count, int) and listing.word_count > 0 for listing in listings
    )


def test_list_chapters_matches_the_titles_from_the_navigation(pipeline_epub: Path) -> None:
    """`ChapterListing.title` stammt aus derselben Navigation wie `ChapterReference.title`
    (`epub.read_structure`) — keine zweite, unabhängig zu pflegende Quelle."""
    structure = epub.read_structure(pipeline_epub)

    listings = pipeline.list_chapters(pipeline_epub)

    assert [listing.title for listing in listings] == [c.title for c in structure.chapters]


def test_list_chapters_sets_the_skip_reason_for_a_chapter_without_text(
    pipeline_epub_with_a_chapter_without_text: Path,
) -> None:
    """Bauplan-phase2.md AP 4, erster Prüfweg (an der handgebauten Vorrichtung statt der
    Fremdquelle erzwungen): Ein Kapitel, das nach dem Aussteuern von Vorspann/Impressum
    keinen Fließtext mehr trägt, bekommt `skip_reason` — denselben Wortlaut wie
    `epub.ChapterWithoutTextError` ihn wirft — und den echten Wortumfang `0`, nicht
    `unbekannt`.

    Verfälschungsprobe: `list_chapters`s Fang von `epub.ChapterWithoutTextError` auf ein
    einfaches `pass` ohne den `try`/`except` entfernt (`skip_reason` bliebe dann immer
    `None`) ließ diesen Test rot werden — der Vorspann-Test ist damit tatsächlich an die
    Zusicherung gebunden, nicht nur an eine Zufallsübereinstimmung."""
    listings = {
        listing.number: listing
        for listing in pipeline.list_chapters(pipeline_epub_with_a_chapter_without_text)
    }

    assert listings[1].skip_reason is None
    assert listings[1].word_count and listings[1].word_count > 0

    assert listings[2].word_count == 0
    assert listings[2].skip_reason is not None
    assert "Vorspann" in listings[2].skip_reason

    with pytest.raises(epub.ChapterWithoutTextError) as error:
        structure = epub.read_structure(pipeline_epub_with_a_chapter_without_text)
        epub.read_chapter(
            pipeline_epub_with_a_chapter_without_text, structure.book, structure.chapters[1]
        )
    assert listings[2].skip_reason == error.value.skip_reason


def test_list_chapters_leaves_the_skip_reason_unset_for_a_different_read_failure(
    pipeline_epub_with_a_missing_chapter_document: Path,
) -> None:
    """Ein Kapitel, das aus einem anderen Grund unlesbar ist (hier: ein Dokument fehlt im
    Archiv), bekommt keinen `skip_reason` — es bleibt wählbar und schlägt erst beim
    tatsächlichen Lesen sichtbar fehl (Regel 13), statt hier ein zweites Mal auf Verdacht
    abgefangen zu werden. Sein Wortumfang ist `None` (`epub.count_chapter_words`), nicht
    `0` — `0` sähe wie ein leeres, aber lesbares Kapitel aus."""
    listings = {
        listing.number: listing
        for listing in pipeline.list_chapters(pipeline_epub_with_a_missing_chapter_document)
    }

    assert listings[2].word_count is None
    assert listings[2].skip_reason is None


def test_list_chapters_never_loads_a_spacy_model(
    pipeline_epub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bauplan-phase2.md AP 4 verlangt ausdrücklich „ohne spaCy" — nachgewiesen statt nur
    behauptet: `extraction.load_nlp` bricht ab, sobald es aufgerufen wird, und
    `list_chapters` läuft trotzdem ohne Fehler durch, ruft es also nie auf."""

    def _fail_if_called() -> Language:
        raise AssertionError("list_chapters darf extraction.load_nlp nie aufrufen (ohne spaCy).")

    monkeypatch.setattr("libreverbum.extraction.load_nlp", _fail_if_called)

    pipeline.list_chapters(pipeline_epub)  # wirft nicht, obwohl load_nlp abbräche


@pytest.mark.needs_epub
def test_list_chapters_reports_the_real_gutenberg_license_chapter_as_skipped(
    real_epub_paths: dict[str, Path],
) -> None:
    """Bauplan-phase2.md AP 4, erster Prüfweg gegen die echte Datei (dokumentation.md §5,
    „Was über den Inhalt einer Fremdquelle behauptet wird, wird zusätzlich gegen das echte
    Gegenüber geprüft"): Gegen `tools/sherlock.epub` erscheint genau Sherlocks
    Gutenberg-Lizenzkapitel („THE FULL PROJECT GUTENBERG™ LICENSE", dasselbe Kapitel wie in
    tests/test_epub.py, `_LICENSE_ONLY_REAL_CHAPTER_TITLE`) mit gesetztem `skip_reason` und
    Wortumfang `0`; jedes andere Kapitel bleibt ohne `skip_reason`.

    `run_chapter` behandelt dasselbe Kapitel bereits heute als übersprungen statt als
    Fehler — mitgeprüft durch die ohnehin laufenden `needs_epub`+`needs_dictionary`-Tests
    (`test_run_chapter_processes_a_real_chapter_with_the_real_dictionary` und der
    Cache-Vergleich daneben), die einen vollständigen `run_chapter`-Lauf gegen dieselbe
    Datei fahren: Bräche das buchweite Lesen an diesem einen Kapitel ab, schlügen sie
    ebenfalls fehl. Ein eigener, ebenso teurer Lauf (voller spaCy-Durchgang über das ganze
    Buch, rund 15 bis 29 s, technik.md §3) käme deshalb ohne neuen Erkenntnisgewinn."""
    listings = pipeline.list_chapters(real_epub_paths["sherlock"])

    skipped = [listing for listing in listings if listing.skip_reason is not None]
    assert len(skipped) == 1
    assert skipped[0].title == "THE FULL PROJECT GUTENBERG™ LICENSE"
    assert skipped[0].word_count == 0


# ---------------------------------------- resolve_triage_entries (zweite T16-Durchsicht)
#
# Handgebaute VocabularyEntry-Vorrichtungen statt des vollen Wegs über EPUB und spaCy
# (schneller, und resolve_triage_entries importiert ohnehin nur entities-Objekte) — die
# Ausnahme ist der Platzhalter-Test, der genau die Injektion in run_chapter selbst prüft
# und deshalb den echten Durchlauf braucht.

_TRIAGE_BOOK = Book(title="Triage-Testbuch", author="Autorin")


def _triage_occurrence(word: str, pos: str, frequency: int) -> Occurrence:
    return Occurrence(
        book=_TRIAGE_BOOK,
        chapter_number=1,
        lemma=Lemma(text=word, pos=pos),
        word_form=word,
        example_sentence=f"An example sentence with {word} in it.",
        frequency=frequency,
        proper_noun_frequency=0,
    )


def _triage_sense(word: str, pos: str, translation: str) -> Sense:
    return Sense(
        lemma=Lemma(text=word, pos=pos),
        wikdict_sense="a meaning",
        wikdict_trans_list=translation,
        wikdict_lexentry=f"eng/{word}__{pos.title()}__1",
    )


def test_resolve_triage_entries_drops_an_ambiguous_entry_whose_meant_sense_is_known(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Abnahmekriterium 6 (konzept.md, „Abnahmekriterien"): „Beim zweiten Durchlauf
    desselben Kapitels werden die als bekannt markierten Wörter nicht erneut abgefragt —
    das Profil greift." Hier an einem **mehrdeutigen** Wort (`bank`, zwei Kandidaten,
    Befund schwer 1 aus dem Auftrag): Der Vorfilter allein kann den Eintrag nicht
    herausnehmen, weil nicht *jede* Bedeutung bekannt ist — erst nachdem das Modell im
    Belegsatz die bereits bekannte Bedeutung (Geldinstitut) auflöst, fällt er weg.

    Zählt dabei in `resolution.resolved_known`, nicht in `resolution.known` (Befund mittel,
    Durchsicht 46ef37b): Der Vorfilter selbst hat den Eintrag nicht verworfen, das geschah
    erst nach der Auflösung."""
    institution = _triage_sense("bank", "NOUN", "Bank")
    edge_of_river = _triage_sense("bank", "NOUN", "Ufer")
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("bank", "NOUN", frequency=3),
        candidates=[institution, edge_of_river],
        status={
            institution: profile.VocabularyStatus.KNOWN,
            edge_of_river: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
        },
    )
    model_server_double.choice = 1  # erster Listenplatz: institution ("Bank")

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, institution, _TRIAGE_BOOK, chapter_number=1)
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[entry],
            limit=10,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    assert resolution.entries == []
    assert resolution.resolved_known == 1
    assert resolution.known == 0
    assert len(model_server_double.requests) == 1


def test_resolve_triage_entries_marks_a_newly_resolved_sense_of_a_known_word(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """konzept.md §5, „Mehrdeutigkeit": Meint das Kapitel bei einem mehrdeutigen Wort eine
    **andere** Bedeutung als die bereits bekannte, bleibt der Eintrag in der Triage und
    trägt `NEW_MEANING_OF_KNOWN_WORD` — hier ist „Bank" (Geldinstitut) bekannt, der
    Belegsatz meint aber „Ufer"."""
    institution = _triage_sense("bank", "NOUN", "Bank")
    edge_of_river = _triage_sense("bank", "NOUN", "Ufer")
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("bank", "NOUN", frequency=3),
        candidates=[institution, edge_of_river],
        status={
            institution: profile.VocabularyStatus.KNOWN,
            edge_of_river: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
        },
    )
    model_server_double.choice = 2  # zweiter Listenplatz: edge_of_river ("Ufer")

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, institution, _TRIAGE_BOOK, chapter_number=1)
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[entry],
            limit=10,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    assert len(resolution.entries) == 1
    resolved = resolution.entries[0]
    assert resolved.sense.wikdict_trans_list == "Ufer"
    assert resolved.status == profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD


def test_resolve_triage_entries_does_not_ask_again_for_a_known_word_without_a_dictionary_entry(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Befund mittel, zweite T16-Durchsicht: Ein Wort ganz ohne Wörterbucheintrag
    ("sunset", im Mini-Wörterbuch nicht geführt) muss ebenso „bekannt" werden können wie
    ein Wort mit Eintrag — derselbe Platzhalter steht dafür auf Schreib- **und**
    Leseseite (Moduldocstring `pipeline.py`). `get_model_name` bricht ab, wenn er
    überhaupt aufgerufen wird: Es gibt nichts, worüber das Modell entscheiden könnte."""
    first_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    sunset_entry = _entry(first_pass, "sunset")
    assert len(sunset_entry.candidates) == 1
    assert sunset_entry.candidates[0].uncertain is True

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, sunset_entry.candidates[0], first_pass.chapter.book, chapter_number=1)
    finally:
        con.close()

    second_pass = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )
    sunset_entry_2 = _entry(second_pass, "sunset")

    def _never_needed() -> str:
        raise AssertionError("Modellserver wurde angefragt, obwohl 'sunset' bereits bekannt war.")

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[sunset_entry_2],
            limit=10,
            url="http://unerreichbar.invalid",
            get_model_name=_never_needed,
        )
    finally:
        con.close()

    assert resolution.entries == []
    assert resolution.known == 1


def test_resolve_triage_entries_never_calls_the_model_for_a_word_without_a_dictionary_entry(
    profile_path: Path,
) -> None:
    """Regel 11 (dokumentation.md §4, „Kandidaten ohne Wörterbucheintrag werden uncertain
    markiert") und der Auftragstext: „Kein Modellaufruf für solche Einträge — es gibt
    nichts zu wählen." Anders als der vorige Test (bereits bekannt, vom Vorfilter
    herausgenommen) ist dieses Wort hier **neu** — der Vorfilter allein kann `_resolve_sense`
    also nicht umgehen, nur die eigene Ausweichregel für einen einzelnen `uncertain`-
    Platzhalter (`pipeline.py`, `_resolve_sense`) tut das. `get_model_name` bricht ab, wenn
    er aufgerufen wird."""
    placeholder = Sense(lemma=Lemma(text="obscure", pos="NOUN"), uncertain=True)
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("obscure", "NOUN", frequency=1),
        candidates=[placeholder],
        status={},
    )

    def _never_needed() -> str:
        raise AssertionError("Modellserver wurde angefragt, obwohl es nichts zu wählen gab.")

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[entry],
            limit=10,
            url="http://unerreichbar.invalid",
            get_model_name=_never_needed,
        )
    finally:
        con.close()

    assert len(resolution.entries) == 1
    assert resolution.entries[0].sense.uncertain is True
    assert resolution.entries[0].status == profile.VocabularyStatus.UNKNOWN


def test_resolve_triage_entries_stops_once_the_limit_of_kept_entries_is_reached(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Zeitbudget aus technik.md §3 („eine halbe Minute" bei höchstens 25 neuen Wörtern):
    Für ein Kapitel mit sehr vielen Grundformen werden nicht alle beim Modell vorgelegt —
    hier 1.000 synthetische, unzweideutige Wörter gegen ein `limit` von 25. Ohne den
    Abbruch aus Schritt 5 (`resolve_triage_entries`) wären das 1.000 Modellanfragen statt
    25, rund 17 statt einer halben Minute (technik.md §3)."""
    total = 1000
    limit = 25
    entries = [
        pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(f"word{i}", "NOUN", frequency=total - i),
            candidates=[_triage_sense(f"word{i}", "NOUN", f"Übersetzung{i}")],
            status={},
        )
        for i in range(total)
    ]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=limit,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    assert len(resolution.entries) == limit
    assert len(model_server_double.requests) == limit
    assert len(resolution.remaining) == total - limit


def test_resolve_triage_entries_followup_call_continues_where_the_previous_call_stopped(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """technik.md §12, „Blockweise Triage mit Vorladen — entschieden", Abschnitt „Der Kern
    liefert den Rest mit, statt ihn wegzuwerfen": Ein Folgeaufruf von
    `resolve_triage_entries` mit `entries=resolution.remaining` liefert die nächsten
    Einträge in Häufigkeitsreihenfolge, wiederholt keinen bereits gelieferten Eintrag, und
    die Zählzusicherung gilt für jeden der beiden Aufrufe für sich (jeweils gegen die
    Größe seiner eigenen Eingabemenge).

    Verfälschungsprobe: `remaining=[entries_by_occurrence[o] for o in ordered[examined + 1 :]]`
    statt `ordered[examined:]` lässt beim ersten Aufruf einen Eintrag zwischen `entries`
    und `remaining` durchfallen — dieser Test war daran rot, weil `word10` dann weder in
    `first.entries` noch in `first.remaining` (und damit auch nicht in `second.entries`)
    auftauchte und die Zählzusicherung des ersten Aufrufs `total - 1` statt `total` ergab."""
    total = 30
    limit = 10
    entries = [
        pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(f"word{i}", "NOUN", frequency=total - i),
            candidates=[_triage_sense(f"word{i}", "NOUN", f"Übersetzung{i}")],
            status={},
        )
        for i in range(total)
    ]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        first = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=limit,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
        second = pipeline.resolve_triage_entries(
            con=con,
            entries=first.remaining,
            limit=limit,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    first_words = [entry.occurrence.lemma.text for entry in first.entries]
    second_words = [entry.occurrence.lemma.text for entry in second.entries]

    assert first_words == [f"word{i}" for i in range(0, 10)]
    assert second_words == [f"word{i}" for i in range(10, 20)]
    assert set(first_words).isdisjoint(second_words)
    assert len(first.remaining) == total - limit
    assert {entry.occurrence.lemma.text for entry in second.remaining} == {
        f"word{i}" for i in range(20, 30)
    }
    assert len(model_server_double.requests) == 2 * limit

    for resolution, input_size in ((first, total), (second, len(first.remaining))):
        summed = (
            resolution.known
            + resolution.resolved_known
            + resolution.skipped
            + len(resolution.remaining)
            + len(resolution.entries)
        )
        assert summed == input_size


def test_resolve_triage_entries_remaining_is_empty_once_the_limit_exceeds_the_input(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """technik.md §12: `remaining` ist das Ende-Signal für die Blockschleife des nächsten
    Bauschritts — ist `limit` größer als die Zahl der Einträge, wurde jeder Eintrag
    angefasst, und `remaining` muss leer sein, nicht bloß klein.

    Verfälschungsprobe: `remaining=[entries_by_occurrence[o] for o in ordered]` statt
    `ordered[examined:]` (die Schnitt-Stelle vergessen, jeder Eintrag landet unabhängig
    von `examined` in `remaining`) lässt hier alle fünf Einträge in `remaining`
    auftauchen, obwohl jeder von ihnen auch in `resolution.entries` steht — dieser Test
    war an `resolution.remaining == []` rot. Ein reines Off-by-one an der Abbruchbedingung
    (`len(resolved) > limit` statt `>=`) besteht diesen Test dagegen zufällig auch, weil
    `limit=100` hier nie erreicht wird — dafür steht der nicht-leere Fall oben in
    `test_resolve_triage_entries_stops_once_the_limit_of_kept_entries_is_reached`."""
    entries = [
        pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(f"word{i}", "NOUN", frequency=10 - i),
            candidates=[_triage_sense(f"word{i}", "NOUN", f"Übersetzung{i}")],
            status={},
        )
        for i in range(5)
    ]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=100,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    assert resolution.remaining == []
    assert len(resolution.entries) == len(entries)


def test_resolve_triage_entries_skips_and_never_lets_a_no_match_reach_the_profile(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Befund schwer 1, Durchsicht 46ef37b: Wählt das Modell „keine passt", obwohl `bank`
    zwei echte Wörterbuchkandidaten hat, darf weder der Platzhalter in die Triage gelangen
    noch — geht das Ergebnis unverändert an `cli.interaction.run_triage_pass` weiter —
    jemals eine Bedeutungszeile ohne jeden `wikdict_`-Wert im Profil landen. Genau das tat
    die vorige Fassung: Der Platzhalter erschien in der Triage als „kein
    Wörterbucheintrag — unsicher", eine Buchung von dort (etwa „kenne ich") schrieb ihn
    dauerhaft ins Profil, und jede echte Bedeutung von `bank` galt danach fälschlich als
    „neue Bedeutung eines bekannten Wortes" (Auftragstext, `bank`-Beispiel).

    Verfälschungsprobe: Lässt `_resolve_sense` weiterhin `chosen` statt `None`
    zurückgeben, steht nach diesem Testlauf eine `sense`-Zeile für „bank" mit allen drei
    `wikdict_`-Feldern `NULL` in der Profildatei — der Test war an dieser Fassung rot,
    schon an `resolution.entries == []`, spätestens aber an der Datenbankprüfung am Ende
    (dort bricht `read_line` sonst mit einer eigenen `AssertionError` ab, weil
    `run_triage_pass` für den Platzhalter tatsächlich eine Frage stellt)."""
    institution = _triage_sense("bank", "NOUN", "Bank")
    edge_of_river = _triage_sense("bank", "NOUN", "Ufer")
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("bank", "NOUN", frequency=3),
        candidates=[institution, edge_of_river],
        status={
            institution: profile.VocabularyStatus.UNKNOWN,
            edge_of_river: profile.VocabularyStatus.UNKNOWN,
        },
    )
    # option_count = len(candidates) + 1 = 3 — die Nummer der Ausweichantwort „keine passt"
    # (translation.py, „Regeln"), kein Sonderwert außerhalb von 1..N+1.
    model_server_double.choice = 3

    def _no_question_expected(prompt: str) -> str:
        raise AssertionError(
            f"run_triage_pass hat trotz leerer resolution.entries gefragt: {prompt!r}"
        )

    con = profile.open_profile(profile_path)
    try:
        interaction.ensure_chapter_row(con, _TRIAGE_BOOK, 1, "Testkapitel")
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[entry],
            limit=10,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
        assert resolution.entries == []
        assert resolution.skipped == 1
        assert resolution.known == 0
        assert resolution.resolved_known == 0
        assert len(model_server_double.requests) == 1

        cards = interaction.run_triage_pass(
            con=con,
            book=_TRIAGE_BOOK,
            chapter_number=1,
            resolution=resolution,
            label="Wörter",
            card_direction=CardDirection.EN_DE,
            read_line=_no_question_expected,
            write_line=lambda _line: None,
        ).cards
        assert cards == []

        placeholder_rows = con.execute(
            "SELECT COUNT(*) FROM sense s JOIN lemma l ON l.id = s.lemma_id "
            "WHERE l.text = ? AND s.wikdict_lexentry IS NULL AND s.wikdict_sense IS NULL "
            "AND s.wikdict_trans_list IS NULL",
            ("bank",),
        ).fetchone()[0]
        assert placeholder_rows == 0
    finally:
        con.close()


def test_resolve_triage_entries_counts_add_up_to_the_input_size(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Befund mittel, Durchsicht 46ef37b: `known + resolved_known + skipped +
    len(resolution.remaining) + len(resolution.entries)` muss wieder die Zahl der
    übergebenen Einträge ergeben — sonst verschwindet ein Teil unbeziffert aus jeder
    Meldung, wie im Auftragsbeispiel („4" statt „25" bereits bekannt: 4 + 1.360 + 25 =
    1.389 statt 1.410).

    Eine Häufigkeitskaskade mit je einem Eintrag für jede der drei Zählungen, die
    Restliste und die behaltene Liste: `alpha` (Vorfilter bekannt, kein Modellaufruf), `vault`
    (mehrdeutig, wie der `bank`-Fall erst nach Auflösen als bekannt erkannt), `spring`
    (mehrdeutig, Modell wählt „keine passt" trotz echter Kandidaten, Befund schwer 1),
    `pen` (bleibt in der Triage) und `quiz` (mit `limit=1` nie erreicht — die
    Abbruchbedingung selbst bleibt unangetastet, siehe Auftrag). Dieselbe `choice`-Zahl
    ergibt an einem Eintrag mit einem echten Kandidaten die Auswahl dieses Kandidaten und
    an einem mit zweien die Ausweichantwort — ausgenutzt über eine Warteschlange, die
    `get_model_name` bei jedem Aufruf weiterschaltet (Aufrufreihenfolge = Häufigkeits-
    reihenfolge, `triage.sort_by_frequency`).

    Verfälschungsprobe: Der `continue` für einen erst nach dem Auflösen bekannten Eintrag
    ohne `resolved_known += 1` (der Stand vor dieser Behebung) lässt die Summe um genau 1
    hinter der Eingabemenge zurück — dieser Test war daran rot."""
    alpha_sense = _triage_sense("alpha", "NOUN", "Alpha")
    known_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("alpha", "NOUN", frequency=1),
        candidates=[alpha_sense],
        status={alpha_sense: profile.VocabularyStatus.KNOWN},
    )

    vault_known = _triage_sense("vault", "NOUN", "Gewoelbe")
    vault_other = _triage_sense("vault", "NOUN", "Sprung")
    vault_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("vault", "NOUN", frequency=40),
        candidates=[vault_known, vault_other],
        status={
            vault_known: profile.VocabularyStatus.UNKNOWN,
            vault_other: profile.VocabularyStatus.UNKNOWN,
        },
    )

    spring_a = _triage_sense("spring", "NOUN", "Fruehling")
    spring_b = _triage_sense("spring", "NOUN", "Feder")
    spring_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("spring", "NOUN", frequency=30),
        candidates=[spring_a, spring_b],
        status={
            spring_a: profile.VocabularyStatus.UNKNOWN,
            spring_b: profile.VocabularyStatus.UNKNOWN,
        },
    )

    pen_sense = _triage_sense("pen", "NOUN", "Stift")
    pen_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("pen", "NOUN", frequency=20),
        candidates=[pen_sense],
        status={pen_sense: profile.VocabularyStatus.UNKNOWN},
    )

    quiz_sense = _triage_sense("quiz", "NOUN", "Quiz")
    quiz_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("quiz", "NOUN", frequency=10),
        candidates=[quiz_sense],
        status={quiz_sense: profile.VocabularyStatus.UNKNOWN},
    )

    all_entries = [known_entry, vault_entry, spring_entry, pen_entry, quiz_entry]

    # 1 wählt bei vault (zwei Kandidaten) die erste, bekannte Bedeutung und bei pen (ein
    # Kandidat) dessen einzige Bedeutung; 3 ist bei spring (zwei Kandidaten, option_count
    # 3) die Nummer der Ausweichantwort. quiz erreicht die Warteschlange nie — die
    # Obergrenze schlägt vorher zu.
    choices = iter([1, 3, 1])

    def _get_model_name() -> str:
        model_server_double.choice = next(choices)
        return model_server_double.model_name

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, vault_known, _TRIAGE_BOOK, chapter_number=1)
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=all_entries,
            limit=1,
            url=model_server_double.url,
            get_model_name=_get_model_name,
        )
    finally:
        con.close()

    assert resolution.known == 1
    assert resolution.resolved_known == 1
    assert resolution.skipped == 1
    assert [entry.occurrence.lemma.text for entry in resolution.remaining] == ["quiz"]
    assert [entry.occurrence.lemma.text for entry in resolution.entries] == ["pen"]
    assert len(model_server_double.requests) == 3

    total = (
        resolution.known
        + resolution.resolved_known
        + resolution.skipped
        + len(resolution.remaining)
        + len(resolution.entries)
    )
    assert total == len(all_entries)


# ------------------------------------ zweistufige Auswahl, order, Rückruf (Auftrag 25.08.2026)


def test_resolve_triage_entries_needs_at_most_limit_model_calls_when_enough_certain_entries_exist(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Auftragstext vom 25.08.2026, Abschnitt 1: Auf der Vorgabe (`order =
    "new_words_first"`) kostet ein Kapitel, in dem genug sichere Treffer vorhanden sind
    (kein Kandidat `KNOWN`), höchstens `limit` Modellaufrufe — die teilweise bekannten
    Einträge (`partial`) werden nie angefasst, weil die sicheren Treffer den Deckel schon
    allein füllen.

    Verfälschungsprobe (dokumentation.md §5, „Ein Test gilt erst als Test..."): Ein Test,
    in dem jeder betrachtete Eintrag auch behalten wird, bleibt grün, wenn man die
    Abbruchbedingung von „behalten >= limit" auf „betrachtet >= limit" vertauscht — genau
    das hat die vorige Durchsicht an `test_resolve_triage_entries_stops_once_the_limit_
    of_kept_entries_is_reached` bemängelt. Die Vorrichtung enthält deshalb `discard`: der
    Platzhalter ohne Wörterbucheintrag (`uncertain=True`) als einziger Kandidat, mit der
    höchsten Häufigkeit — `_resolve_sense` liefert ihn ohne jeden Modellaufruf zurück
    (Regel 11), ein vorab eingetragenes `known`-Ereignis lässt der frische Profilabgleich
    ihn danach aber als `resolved_known` verwerfen: **betrachtet und dann verworfen**,
    ohne die Modellaufruf-Zählung zu belasten. Unter der falschen Abbruchbedingung würde
    dieser kostenlose Fehlschlag trotzdem einen der `limit` „betrachteten" Plätze
    verbrauchen, und `len(resolution.entries)` bliebe bei `limit - 1` stehen, statt bei
    `limit` — an dieser Zusicherung war der Test bei der Verfälschung tatsächlich rot."""
    limit = 5
    discard_sense = Sense(lemma=Lemma(text="discard", pos="NOUN"), uncertain=True)
    discard_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("discard", "NOUN", frequency=1000),
        candidates=[discard_sense],
        status={},
    )
    kept_entries = [
        pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(f"keep{i}", "NOUN", frequency=900 - i),
            candidates=[_triage_sense(f"keep{i}", "NOUN", f"Übersetzung{i}")],
            status={},
        )
        for i in range(limit)
    ]
    partial_entries = []
    for i in range(3):
        matched = _triage_sense(f"partial{i}_known", "NOUN", "Bekannt")
        other = _triage_sense(f"partial{i}_other", "NOUN", "Andere")
        partial_entries.append(
            pipeline.VocabularyEntry(
                occurrence=_triage_occurrence(f"partial{i}", "NOUN", frequency=400 - i),
                candidates=[matched, other],
                status={
                    matched: profile.VocabularyStatus.KNOWN,
                    other: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
                },
            )
        )
    all_entries = [discard_entry, *kept_entries, *partial_entries]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, discard_sense, _TRIAGE_BOOK, chapter_number=1)
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=all_entries,
            limit=limit,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
        )
    finally:
        con.close()

    assert len(resolution.entries) == limit
    assert len(model_server_double.requests) == limit
    assert resolution.resolved_known == 1
    assert resolution.skipped == 0
    assert resolution.known == 0
    assert len(resolution.remaining) == len(partial_entries)
    assert {entry.occurrence.lemma.text for entry in resolution.remaining} == {
        entry.occurrence.lemma.text for entry in partial_entries
    }
    assert {entry.occurrence.lemma.text for entry in resolution.entries} == {
        f"keep{i}" for i in range(limit)
    }
    total = (
        resolution.known
        + resolution.resolved_known
        + resolution.skipped
        + len(resolution.remaining)
        + len(resolution.entries)
    )
    assert total == len(all_entries)


def test_resolve_triage_entries_new_words_first_certain_before_partial_but_sorted_by_frequency(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Auftragstext, Abschnitt 1: Unter `order = "new_words_first"` legt
    `resolve_triage_entries` zuerst die sicheren Treffer vor (hier niedrigere Häufigkeit:
    "yankee", "xray"), erst danach die teilweise bekannten (hier höhere Häufigkeit: "papa",
    "quebec") — die Verarbeitungsreihenfolge ist also **nicht** die Häufigkeitsreihenfolge.
    Die **Anzeigereihenfolge** (`resolution.entries`) bleibt trotzdem Häufigkeit, weil sie
    am Ende erneut sortiert wird (Auftragstext: „damit die Auswahlstrategie nicht in die
    Triage durchschlägt").

    Verfälschungsprobe: Lässt man die abschließende Sortierung nach `triage.
    sort_by_frequency` weg und liefert `resolved` stattdessen in Verarbeitungsreihenfolge
    zurück, ergibt sich `resolution.entries` „yankee, xray, papa, quebec" statt „papa,
    quebec, yankee, xray" — an dieser Zusicherung war der Test rot."""
    partial_specs = [("papa", 90), ("quebec", 80)]
    certain_specs = [("yankee", 20), ("xray", 10)]

    def _partial(word: str, freq: int) -> pipeline.VocabularyEntry:
        matched = _triage_sense(f"{word}_known", "NOUN", "Bekannt")
        other = _triage_sense(f"{word}_other", "NOUN", "Andere")
        return pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(word, "NOUN", frequency=freq),
            candidates=[other, matched],  # "other" zuerst: choice=1 wählt die nicht bekannte
            status={
                matched: profile.VocabularyStatus.KNOWN,
                other: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
            },
        )

    def _certain(word: str, freq: int) -> pipeline.VocabularyEntry:
        return pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(word, "NOUN", frequency=freq),
            candidates=[_triage_sense(word, "NOUN", "Übersetzung")],
            status={},
        )

    entries = [_partial(w, f) for w, f in partial_specs] + [
        _certain(w, f) for w, f in certain_specs
    ]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=4,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
            order="new_words_first",
        )
    finally:
        con.close()

    processed_words = [
        word
        for request in model_server_double.requests
        for word in ("yankee", "xray", "papa", "quebec")
        if f'"{word}"' in request["messages"][0]["content"]
    ]
    assert processed_words == ["yankee", "xray", "papa", "quebec"]
    assert [entry.occurrence.lemma.text for entry in resolution.entries] == [
        "papa",
        "quebec",
        "yankee",
        "xray",
    ]


def test_resolve_triage_entries_under_frequency_order_interleaves_both_groups(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Auftragstext, Abschnitt 2: `order = "frequency"` ist „genau das heutige Verhalten:
    sichere Treffer und teilweise bekannte gemeinsam in Häufigkeitsreihenfolge" — die
    Verarbeitungsreihenfolge mischt beide Gruppen, statt sie wie bei `"new_words_first"`
    zu trennen.

    Verfälschungsprobe: Ignoriert `resolve_triage_entries` den Wert von `order` und
    gruppiert immer nach `"new_words_first"`, ergäbe sich die Reihenfolge „alpha, charlie,
    echo, bravo, delta" (erst alle sicheren, dann alle teilweise bekannten Treffer) statt
    der erwarteten strikten Häufigkeitsreihenfolge „alpha, bravo, charlie, delta, echo" —
    an dieser Zusicherung war der Test rot."""

    def _partial(word: str, freq: int) -> pipeline.VocabularyEntry:
        matched = _triage_sense(f"{word}_known", "NOUN", "Bekannt")
        other = _triage_sense(f"{word}_other", "NOUN", "Andere")
        return pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(word, "NOUN", frequency=freq),
            candidates=[other, matched],
            status={
                matched: profile.VocabularyStatus.KNOWN,
                other: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
            },
        )

    def _certain(word: str, freq: int) -> pipeline.VocabularyEntry:
        return pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(word, "NOUN", frequency=freq),
            candidates=[_triage_sense(word, "NOUN", "Übersetzung")],
            status={},
        )

    entries = [
        _certain("alpha", 100),
        _partial("bravo", 90),
        _certain("charlie", 80),
        _partial("delta", 70),
        _certain("echo", 60),
    ]
    model_server_double.choice = 1

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=10,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
            order="frequency",
        )
    finally:
        con.close()

    expected = ["alpha", "bravo", "charlie", "delta", "echo"]
    processed_words = [
        word
        for request in model_server_double.requests
        for word in expected
        if f'"{word}"' in request["messages"][0]["content"]
    ]
    assert processed_words == expected
    assert [entry.occurrence.lemma.text for entry in resolution.entries] == expected


def test_resolve_triage_entries_rejects_an_unknown_order_value(profile_path: Path) -> None:
    """Auftragstext, Abschnitt 2: Ein unzulässiger Wert von `order` bricht sichtbar ab und
    nennt die zulässigen Werte (Regel 13, dokumentation.md §4) — statt still auf die
    Vorgabe `new_words_first` zurückzufallen."""
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("whatever", "NOUN", frequency=1),
        candidates=[_triage_sense("whatever", "NOUN", "Irgendwas")],
        status={},
    )

    def _never_needed() -> str:
        raise AssertionError("Modellserver wurde trotz ungültigem order-Wert angefragt.")

    con = profile.open_profile(profile_path)
    try:
        with pytest.raises(ValueError, match="new_words_first"):
            pipeline.resolve_triage_entries(
                con=con,
                entries=[entry],
                limit=10,
                url="http://unerreichbar.invalid",
                get_model_name=_never_needed,
                order="alphabetical",
            )
    finally:
        con.close()


@pytest.mark.parametrize("limit", [0, -1])
def test_resolve_triage_entries_rejects_a_non_positive_limit(
    profile_path: Path, limit: int
) -> None:
    """Befund 8, Durchsicht d4f10fc: `limit <= 0` bricht sichtbar ab und nennt den
    unzulässigen Wert (Regel 13, dokumentation.md §4), statt die Schleife sofort mit
    `remaining == entries` zu verlassen — ab Bauschritt 2 der blockweisen Triage sonst
    eine stille Endlosschleife, weil `remaining` bei einem solchen `limit` nie schrumpft."""
    entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("whatever", "NOUN", frequency=1),
        candidates=[_triage_sense("whatever", "NOUN", "Irgendwas")],
        status={},
    )

    def _never_needed() -> str:
        raise AssertionError("Modellserver wurde trotz ungültigem limit angefragt.")

    con = profile.open_profile(profile_path)
    try:
        with pytest.raises(ValueError, match=str(limit)):
            pipeline.resolve_triage_entries(
                con=con,
                entries=[entry],
                limit=limit,
                url="http://unerreichbar.invalid",
                get_model_name=_never_needed,
            )
    finally:
        con.close()


def test_resolve_triage_entries_reports_ascending_progress_through_the_callback(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Auftragstext, Abschnitt 3: `resolve_triage_entries` bekommt einen Rückruf, den die
    Kommandozeile bedient. Die übrigen Tests dieser Datei übergeben `on_progress` nicht
    und belegen damit bereits, dass sich die Funktion ohne Rückruf wie bisher verhält;
    hier wird geprüft, dass der Rückruf tatsächlich aufgerufen wird und die gemeldeten
    Zahlen (geprüft, behalten) über einen Lauf hinweg nur wachsen."""
    total = 30
    limit = 10
    entries = [
        pipeline.VocabularyEntry(
            occurrence=_triage_occurrence(f"word{i}", "NOUN", frequency=total - i),
            candidates=[_triage_sense(f"word{i}", "NOUN", f"Übersetzung{i}")],
            status={},
        )
        for i in range(total)
    ]
    model_server_double.choice = 1
    reports: list[tuple[int, int, int, int]] = []

    con = profile.open_profile(profile_path)
    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=limit,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
            on_progress=lambda examined, total_to_check, kept, limit_: reports.append(
                (examined, total_to_check, kept, limit_)
            ),
        )
    finally:
        con.close()

    assert len(resolution.entries) == limit
    assert reports  # Rückruf wurde mindestens einmal aufgerufen
    assert all(total_to_check == total for _, total_to_check, _, _ in reports)
    assert all(limit_ == limit for _, _, _, limit_ in reports)
    examined_values = [examined for examined, _, _, _ in reports]
    kept_values = [kept for _, _, kept, _ in reports]
    assert examined_values == sorted(examined_values)
    assert kept_values == sorted(kept_values)
    assert examined_values == list(range(1, len(reports) + 1))
    assert reports[-1][2] == limit


def test_resolve_triage_entries_reports_progress_for_skipped_and_resolved_known_entries(
    profile_path: Path, model_server_double: ModelServerDouble
) -> None:
    """Befund leicht 2 (Durchsicht T16/T17): Die vorherige Vorrichtung
    (`test_resolve_triage_entries_reports_ascending_progress_through_the_callback`) enthält
    ausschließlich behaltene Einträge — genau der `frequency`-Fall mit reifem Profil, für
    den die Anzeige gebaut wurde, bliebe damit ungeprüft. Hier laufen alle drei Zweige der
    zweistufigen Auswahl (Schritt 3/4) durch dieselbe Statuszeile: ein behaltener, ein vom
    Modell übersprungener (`skipped`, „keine passt") und ein nachträglich als bekannt
    aufgelöster (`resolved_known`) Eintrag, per Häufigkeit in dieser Reihenfolge verarbeitet.

    Verfälschungsprobe: `_report_progress()` aus den beiden `continue`-Zweigen entfernt
    (wie im Auftragstext vorgegeben) ließ `len(reports) == 3` rot werden — nur der
    behaltene Eintrag meldete sich noch, `reports` hatte danach genau ein Element.

    `model_server_double.choice` bleibt über den ganzen Lauf **fest** bei 2 — die drei
    Ausgänge entstehen allein aus der Kandidatenzahl je Eintrag, nicht aus einer
    Zustandsänderung während des Laufs: Bei `wordkept` und `wordknown` trifft Listenplatz 2
    den zweiten von zwei echten Kandidaten, bei `wordskip` liegt Listenplatz 2 außerhalb der
    einzigen echten Bedeutung (N=1) und ist damit „keine passt" (Regel 11). Eine
    Zustandsänderung im `on_progress`-Rückruf selbst hinge am genau geprüften Mechanismus
    und verfälschte damit die Probe."""
    kept_filler = _triage_sense("wordkept", "NOUN", "Fülleintrag")
    kept_sense = _triage_sense("wordkept", "VERB", "behalten")
    kept_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("wordkept", "NOUN", frequency=30),
        candidates=[kept_filler, kept_sense],
        status={},
    )
    skipped_sense = _triage_sense("wordskip", "NOUN", "übersprungen")
    skipped_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("wordskip", "NOUN", frequency=20),
        candidates=[skipped_sense],
        status={},
    )
    known_filler = _triage_sense("wordknown", "NOUN", "Fülleintrag")
    known_sense = _triage_sense("wordknown", "VERB", "bekannt")
    known_entry = pipeline.VocabularyEntry(
        occurrence=_triage_occurrence("wordknown", "NOUN", frequency=10),
        candidates=[known_filler, known_sense],
        status={},
    )

    reports: list[tuple[int, int, int, int]] = []
    model_server_double.choice = 2  # zweiter Listenplatz, unverändert über den ganzen Lauf

    con = profile.open_profile(profile_path)
    try:
        _record_known(con, known_sense, _TRIAGE_BOOK, chapter_number=1)
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=[kept_entry, skipped_entry, known_entry],
            limit=10,
            url=model_server_double.url,
            get_model_name=lambda: model_server_double.model_name,
            on_progress=lambda examined, total_to_check, kept, limit_: reports.append(
                (examined, total_to_check, kept, limit_)
            ),
        )
    finally:
        con.close()

    assert len(resolution.entries) == 1
    assert resolution.entries[0].sense.wikdict_trans_list == "behalten"
    assert resolution.skipped == 1
    assert resolution.resolved_known == 1
    assert len(reports) == 3, reports


# ------------------------------------------ write_vocabulary_preset (Bauschritt 3/5 der
# ------------------------------------------ Vorbelegung, 31.08.2026)
#
# Läuft gegen die echte, im Paket ausgelieferte wordfreq_en_5000.txt (Programmbestandteil,
# technik.md §9) und `mini_dictionary_db` — kein eigenes Wegwerf-Wörterbuch, weil
# write_vocabulary_preset den Ort der Liste nicht als Argument entgegennimmt. Innerhalb
# der ersten 500 Ränge der echten Liste treffen genau drei der sieben Stichwörter aus
# mini_dictionary_db: watch (Rang 368, Substantiv **und** Verb), red (Rang 384, Adjektiv
# **und** Substantiv), street (Rang 431, Substantiv) — macht 5 (Grundform, Wortart)-Paare,
# 6 Bedeutungen; nachgerechnet mit dictionary.pos_variant_lists/contiguous_candidates vor
# dem Schreiben dieser Tests. bank und draw liegen erst jenseits von Rang 500, saw und
# give up stehen gar nicht in der Liste (keine dieser vier Formen verfälscht also A1).


def test_write_vocabulary_preset_books_every_dictionary_sense_not_only_the_best_scored(
    mini_dictionary_db: Path, profile_path: Path
) -> None:
    """Auftragstext: gebucht wird alle Wörterbuchbedeutungen einer vorbelegten Grundform.
    watch als Substantiv trägt im Mini-Wörterbuch zwei Bedeutungen (Uhr, Wache mit
    niedrigerem score) — beide werden gebucht, nicht nur die bestbewertete. Die 5
    (Grundform, Wortart)-Paare aus dem Kommentar oben (watch NOUN, watch VERB, red ADJ,
    red NOUN, street NOUN) stehen ebenso in `PresetResult.lemma_pos_pairs`."""
    result = pipeline.write_vocabulary_preset(
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        cefr_level=CefrLevel.A1,
        timestamp=datetime.now(UTC),
    )

    assert result.lemma_pos_pairs == 5
    assert result.senses == 6
    # (Befund leicht c, Durchsicht ee34796): drei Grundformen mit Treffer (watch, red,
    # street) von den 500 angefragten A1-Grundformen — unabhängig davon, dass watch und
    # red je zwei Wortarten und damit zwei lemma_pos_pairs beisteuern.
    assert result.covered_lemmas == 3
    assert result.total_lemmas == 500

    con = profile.open_profile(profile_path)
    watch_noun_translations = {
        row[0]
        for row in con.execute(
            "SELECT s.wikdict_trans_list FROM sense s JOIN lemma l ON l.id = s.lemma_id "
            "WHERE l.text = 'watch' AND l.pos = 'NOUN'"
        )
    }
    assert watch_noun_translations == {"Uhr | Armbanduhr", "Wache"}


def test_write_vocabulary_preset_word_class_matches_what_the_dictionary_actually_has(
    mini_dictionary_db: Path, profile_path: Path
) -> None:
    """Fortsetzung von Bauschritt 3/5, Auftragstext: eine feste Wortart zu schreiben wäre
    der stille Fehlschlag. red bekommt hier sowohl ein Adjektiv- als auch ein
    Substantiv-Ereignis, street nur ein Substantiv-Ereignis — eine feste Wortart, gleich
    welche, träfe mindestens eines der beiden falsch oder gar keines."""
    pipeline.write_vocabulary_preset(
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        cefr_level=CefrLevel.A1,
        timestamp=datetime.now(UTC),
    )

    con = profile.open_profile(profile_path)
    red_pos = {
        row[0]
        for row in con.execute(
            "SELECT l.pos FROM lemma l WHERE l.text = 'red' AND EXISTS "
            "(SELECT 1 FROM sense s WHERE s.lemma_id = l.id)"
        )
    }
    street_pos = {
        row[0]
        for row in con.execute(
            "SELECT l.pos FROM lemma l WHERE l.text = 'street' AND EXISTS "
            "(SELECT 1 FROM sense s WHERE s.lemma_id = l.id)"
        )
    }
    assert red_pos == {"ADJ", "NOUN"}
    assert street_pos == {"NOUN"}


def test_write_vocabulary_preset_vocabulary_is_recognized_as_known_in_a_later_lookup(
    mini_dictionary_db: Path, profile_path: Path
) -> None:
    """Abnahmekriterium 6: Eine vorbelegte Grundform muss beim späteren Kapitelabgleich
    als bekannt erkannt werden — nicht nur als roh geschriebene sense-Zeile.
    profile._find_sense_id vergleicht Grundform, Wortart und alle drei wikdict_-Felder;
    eine Vorbelegung, die nur die Wortart aus dem Wörterbuch nimmt, aber keine
    vollständige Sense schreibt, erzeugte eine andere Bedeutungsidentität als der spätere
    echte Fund — der Nutzer würde trotz Vorbelegung erneut gefragt, nur unter dem Etikett
    neue Bedeutung eines bekannten Wortes statt bekannt."""
    pipeline.write_vocabulary_preset(
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        cefr_level=CefrLevel.A1,
        timestamp=datetime.now(UTC),
    )

    # Dieselbe Bedeutung, wie sie ein echter Kapiteldurchlauf über dictionary.candidates
    # fände (run_chapter tut für ein Einzelwort-Vorkommen nichts anderes).
    street_candidates = dictionary.candidates(mini_dictionary_db, Lemma(text="street", pos="NOUN"))
    assert len(street_candidates) == 1
    street_sense = street_candidates[0]

    con = profile.open_profile(profile_path)
    sense_id = profile.ensure_sense(con, street_sense)
    assert profile.current_knowledge_state(con, sense_id) == KnowledgeState.KNOWN

    status = profile.compare_chapter_vocabulary(con, [street_sense])
    assert status[street_sense] == profile.VocabularyStatus.KNOWN


def test_write_vocabulary_preset_does_not_book_a_lemma_without_a_dictionary_entry(
    tmp_path: Path, profile_path: Path
) -> None:
    """Auftragstext: Was der Kern beim Nachschlagen findet, wird vorbelegt; was er nicht
    findet, wird nicht vorbelegt. Ein Wörterbuch ohne einen einzigen Eintrag lässt keine
    der 500 Grundformen aus A1 ein Ereignis erzeugen — und keinen uncertain-Platzhalter:
    sense bekäme sonst Zeilen mit drei NULL-Feldern, die technik.md §4 als kein
    Wörterbucheintrag liest, nicht als vorbelegtes Wissen."""
    empty_dictionary = tmp_path / "leer.sqlite3"
    con = sqlite3.connect(empty_dictionary)
    con.execute(
        "CREATE TABLE translation("
        "lexentry, sense_num, sense, written_rep TEXT, trans_list, score, is_good, importance)"
    )
    con.commit()
    con.close()

    result = pipeline.write_vocabulary_preset(
        dictionary_path=empty_dictionary,
        profile_path=profile_path,
        cefr_level=CefrLevel.A1,
        timestamp=datetime.now(UTC),
    )

    assert result.lemma_pos_pairs == 0
    assert result.senses == 0
    # (Befund leicht c, Durchsicht ee34796): angefragt wurden trotzdem alle 500
    # A1-Grundformen — covered_lemmas bleibt 0, total_lemmas nicht.
    assert result.covered_lemmas == 0
    assert result.total_lemmas == 500
    reader = profile.open_profile(profile_path)
    assert reader.execute("SELECT count(*) FROM event").fetchone()[0] == 0
    assert reader.execute("SELECT count(*) FROM sense").fetchone()[0] == 0
    # Das Niveau selbst wurde trotzdem gewählt (anders als „keine Angabe" unten) und bleibt
    # gesetzt, auch wenn kein einziges Wort einen Wörterbucheintrag hatte.
    assert profile.get_cefr_level(reader) == CefrLevel.A1


def test_write_vocabulary_preset_with_no_answer_writes_nothing(
    mini_dictionary_db: Path, profile_path: Path
) -> None:
    """keine Angabe (cefr_level=None) schreibt keine Ereignisse und setzt kein Niveau —
    hier sogar noch früher sichtbar: Das Profil wird gar nicht erst geöffnet, die
    Profildatei bleibt ganz ungeschrieben."""
    result = pipeline.write_vocabulary_preset(
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        cefr_level=None,
        timestamp=datetime.now(UTC),
    )

    assert result.lemma_pos_pairs == 0
    assert result.senses == 0
    assert result.covered_lemmas == 0
    assert result.total_lemmas == 0
    assert not profile_path.exists()


def test_write_vocabulary_preset_rejects_a_naive_timestamp_before_touching_the_profile(
    mini_dictionary_db: Path, profile_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 7, Nachbesserung Durchsicht 3b1e201: Ein Zeitstempel ohne Zeitzone bricht ab,
    **bevor** `profile.open_profile` die Profildatei überhaupt anlegt — sonst bliebe eine
    leere, aber existierende Profildatei liegen (`profile.open_profile`s Schreibzweig
    committet das Schema, bevor `record_preset` beginnt), und der nächste normale Lauf
    erkennt ein vorhandenes Profil nur an seiner Dateiexistenz, fragt also nie wieder nach
    Niveau und Vorbelegung. Über den einzigen echten Aufrufer
    (`cli.main._apply_vocabulary_preset`, immer `datetime.now(UTC)`) ist das nicht
    erreichbar — dieser Test ruft die Funktion direkt auf, wie es ein Messskript ohne
    diesen Schutz täte (Kaltstart-Hinweis dieser Nachbesserung: `make_profile.py` „braucht
    einen Zeitstempel mit Zeitzone, sonst bleibt ein leeres Profil liegen").

    Beide Nachschlagewege werden hier durch eine Attrappe ersetzt, die bei jedem Aufruf
    abbricht — der erwartete `ValueError` tritt nur ein, wenn die Zeitstempelprüfung sie
    nie erreicht.

    Verfälschungsprobe (Bericht): die neue `if timestamp.tzinfo is None: raise …`-Prüfung
    aus `write_vocabulary_preset` entfernt ließ diesen Test rot werden — statt der
    erwarteten Ausnahme lief der Aufruf durch (`profile.record_event`s eigene, spätere
    Prüfung hätte zwar auch noch abgebrochen, aber erst nach dem Anlegen der Profildatei,
    siehe oben) und `profile_path.exists()` traf zu."""

    def _must_not_be_called(*args: object, **kwargs: object) -> list[object]:
        raise AssertionError("nachgeschlagen, bevor der Zeitstempel geprüft war")

    monkeypatch.setattr(dictionary, "pos_variant_lists", _must_not_be_called)
    monkeypatch.setattr(dictionary, "contiguous_candidates", _must_not_be_called)
    naive_timestamp = datetime(2026, 9, 23, 12, 0)
    assert naive_timestamp.tzinfo is None, "Testvoraussetzung: der Zeitstempel ist naiv"

    with pytest.raises(ValueError, match="keine Zeitzone"):
        pipeline.write_vocabulary_preset(
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            cefr_level=CefrLevel.A1,
            timestamp=naive_timestamp,
        )

    assert not profile_path.exists(), (
        "write_vocabulary_preset hat trotz der Ausnahme eine Profildatei angelegt"
    )


def test_preset_word_count_covers_every_cefr_level() -> None:
    """(Befund a, Durchsicht d8d5954), Regel 13: `write_vocabulary_preset` greift
    ungeschützt auf `PRESET_WORD_COUNT[cefr_level]` zu — fehlte dort ein Niveau, bräche
    der Lauf mit einem nackten englischen `KeyError` ab statt mit einer deutschen Meldung.
    Die Tabelle führt deshalb jedes Niveau der Aufzählung, und jedes Kontingent liegt
    innerhalb der eingefrorenen Liste. Geprüft wird gegen `CefrLevel` und gegen die Liste
    selbst, nicht gegen die Tabelle: A2, B2 und C1 kommen in keinem anderen Test vor."""
    assert set(pipeline.PRESET_WORD_COUNT) == set(CefrLevel)

    for level in CefrLevel:
        count = pipeline.PRESET_WORD_COUNT[level]
        assert len(pipeline._load_wordfreq_lemmas(count)) == count


def test_write_vocabulary_preset_checks_the_profile_directory_before_the_lookup(
    mini_dictionary_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(Befund b, Durchsicht d8d5954), Regel 13: Die billige Prüfung läuft vor der teuren
    Arbeit — dasselbe Muster wie `run_chapter` für die Wörterbuchdatei (Befund 3, Review
    T15). Vor dieser Behebung liefen erst `dictionary.pos_variant_lists` und
    `dictionary.contiguous_candidates` vollständig durch (bei C1 rund 0,3 s und gut 15.000
    Ereignisse im Speicher), bevor `profile.open_profile` das fehlende Profilverzeichnis
    meldete.

    Beide Nachschlagewege werden hier durch eine Attrappe ersetzt, die bei jedem Aufruf
    abbricht: Der erwartete `ValueError` tritt nur ein, wenn die Verzeichnisprüfung sie nie
    erreicht — würde stattdessen zuerst nachgeschlagen, schlüge der Test mit der
    Attrappen-Ausnahme fehl."""

    def _must_not_be_called(*args: object, **kwargs: object) -> list[object]:
        raise AssertionError("nachgeschlagen, bevor das Profilverzeichnis geprüft war")

    monkeypatch.setattr(dictionary, "pos_variant_lists", _must_not_be_called)
    monkeypatch.setattr(dictionary, "contiguous_candidates", _must_not_be_called)

    with pytest.raises(ValueError, match="Profilverzeichnis"):
        pipeline.write_vocabulary_preset(
            dictionary_path=mini_dictionary_db,
            profile_path=tmp_path / "fehlt" / "profil.sqlite3",
            cefr_level=CefrLevel.A1,
            timestamp=datetime.now(UTC),
        )


@pytest.mark.needs_dictionary
def test_write_vocabulary_preset_against_the_real_dictionary(
    real_dictionary_path: Path, profile_path: Path
) -> None:
    """dokumentation.md §5, Woran geprüft wird: Was über den Inhalt einer Fremdquelle
    behauptet wird, wird gegen das echte Gegenüber geprüft. Schreibt die Zahl fest, die
    dieser Bau tatsächlich gegen tools/en-de.sqlite3 liefert.

    Abweichung vom Auftragstext, geklärt (Befund 1, Durchsicht d8d5954): Der Auftrag nennt
    für B1 (N=2.000) 2.663 Paare und 8.045 Bedeutungen aus einer Messung vom 31.08.2026,
    diese Umsetzung liefert reproduzierbar 2.662 und 8.044. Die Differenz ist genau eine
    Zeile — `go to`, Rang 410 der Liste und damit in jedem Kontingent enthalten, weshalb
    die Abweichung bei jedem Niveau dieselbe ist. Das Messskript schickte **jeden**
    Listeneintrag durch den Einzelwortweg, auch die neun Mehrworteinträge; dieser Weg kennt
    die Schwelle `score ≥ 50` nicht (technik.md, „Messung: Mehrwortausdrücke"). `go to` hat
    im Wörterbuch genau eine Zeile mit `lexentry`, und die trägt `score = 0.0` und die
    Übersetzung „fahren ajoneuvo" (das zweite Wort ist Finnisch); der Wendungsweg dieser
    Umsetzung (`dictionary.contiguous_candidates`) wirft sie an der Schwelle weg —
    richtigerweise, denn ein echter Kapiteldurchlauf findet `go to` ebenfalls nur über
    `contiguous_candidates` und verwirft sie dort genauso. Gebucht wäre sie eine
    Profilzeile, die kein Kapiteldurchlauf je einlöst. Nachgestellt: Schickt man alle 2.000
    Grundformen über `dictionary.pos_variant_lists`, kommen genau die 2.663 und 8.045 des
    Auftrags heraus. **8.044 ist die richtige Zahl, 8.045 war der Messfehler.**"""
    result = pipeline.write_vocabulary_preset(
        dictionary_path=real_dictionary_path,
        profile_path=profile_path,
        cefr_level=CefrLevel.B1,
        timestamp=datetime.now(UTC),
    )

    assert result.lemma_pos_pairs == 2662
    assert result.senses == 8044
    # (Befund leicht c, Durchsicht ee34796): 1.743 der 2.000 B1-Grundformen (87,2 %) haben
    # einen Wörterbucheintrag, 257 (12,8 %) nicht — gemessen gegen tools/en-de.sqlite3,
    # dieselbe Vorrichtung wie oben für lemma_pos_pairs/senses.
    assert result.covered_lemmas == 1743
    assert result.total_lemmas == 2000


# --------------------------------------------------------------------- export_cards (AP 2)
#
# bauplan-phase2.md AP 2: Der Dreischritt Anki-Deck schreiben → Druckseite schreiben →
# profile.record_card je Karte liegt in pipeline.export_cards (technik.md §7, „Die
# Importregel"), weil nur `pipeline` mehrere Schrittmodule zugleich kennen darf. Geprüft
# wird hier die Verkettung selbst, nicht nur mittelbar über app.export.write_exports
# (tests/test_app_export.py).

_EXPORT_BOOK = Book(title="Exportbuch", author="Autorin")


def _export_occurrence(lemma_text: str = "watch") -> Occurrence:
    return Occurrence(
        book=_EXPORT_BOOK,
        chapter_number=1,
        lemma=Lemma(text=lemma_text, pos="NOUN"),
        word_form=lemma_text,
        example_sentence=f"He checked his {lemma_text} before leaving.",
        frequency=2,
        proper_noun_frequency=0,
    )


def _export_card(occurrence: Occurrence) -> Card:
    # wikdict_lexentry ist Teil der GUID (anki.new_card_guid), zwei Karten mit
    # verschiedener Grundform brauchen deshalb auch verschiedene Lexeintrag-Kennungen —
    # sonst wiese anki.export_deck sie als Dublette zurück (Befund 2, Review T13).
    sense = Sense(
        lemma=occurrence.lemma,
        translation="Uhr",
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry=f"eng/{occurrence.lemma.text}__Noun__1",
    )
    direction = CardDirection.EN_DE
    guid = anki.new_card_guid(occurrence, sense, direction)
    return Card(sense=sense, occurrence=occurrence, card_direction=direction, guid=guid)


def test_export_cards_writes_a_card_row_for_each_card(tmp_path: Path) -> None:
    """AP 2 (bauplan-phase2.md), Prüfung: Nach `export_cards` steht je Karte eine
    `card`-Zeile (Regel 6, dokumentation.md §4) — geprüft an der Verkettung selbst, nicht
    nur mittelbar über `app.export.write_exports`.

    Verfälschungsprobe: den `profile.record_card`-Aufruf aus `export_cards` entfernt →
    dieser Test rot (`card_guids` bleibt leer)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _EXPORT_BOOK, 1, "Testkapitel")
    cards = [_export_card(_export_occurrence()), _export_card(_export_occurrence("bank"))]

    pipeline.export_cards(
        con,
        cards,
        anki_path=tmp_path / "export.apkg",
        printout_path=tmp_path / "export.html",
        deck_name="Exportbuch - Kapitel 1",
    )

    card_guids = {row[0] for row in con.execute("SELECT guid FROM card").fetchall()}
    assert card_guids == {card.guid for card in cards}


def test_export_cards_writes_the_anki_deck_and_the_printout(tmp_path: Path) -> None:
    """`export_cards` schreibt beide Exportdateien, nicht nur die Profilzeilen — dieselbe
    Verkettung, die `app.export.write_exports` nur noch aufruft."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _EXPORT_BOOK, 1, "Testkapitel")
    anki_path = tmp_path / "export.apkg"
    printout_path = tmp_path / "export.html"

    pipeline.export_cards(
        con,
        [_export_card(_export_occurrence())],
        anki_path=anki_path,
        printout_path=printout_path,
        deck_name="Exportbuch - Kapitel 1",
    )

    assert anki_path.is_file()
    assert "watch" in printout_path.read_text(encoding="utf-8")


def test_export_cards_raises_on_an_empty_card_list_without_booking_anything(tmp_path: Path) -> None:
    """`export_cards` mit einer leeren Kartenliste bricht sichtbar ab (Regel 13, über
    `anki.export_deck`s eigene Prüfung) und bucht dabei keine Karte im Profil.

    Sichert **keine** Reihenfolge zu (Befund 1, Durchsicht 82441bb): Bei leerer Liste ist
    ohnehin keine Karte zu buchen, eine vertauschte Reihenfolge in `export_cards` bliebe
    hier unbemerkt. Das leistet erst
    `test_export_cards_does_not_book_a_card_when_the_anki_export_fails` unten."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _EXPORT_BOOK, 1, "Testkapitel")

    with pytest.raises(ValueError, match="ohne Karten"):
        pipeline.export_cards(
            con,
            [],
            anki_path=tmp_path / "export.apkg",
            printout_path=tmp_path / "export.html",
            deck_name="Exportbuch - Kapitel 1",
        )

    assert con.execute("SELECT count(*) FROM card").fetchone()[0] == 0


def test_export_cards_does_not_book_a_card_when_the_anki_export_fails(tmp_path: Path) -> None:
    """Bricht `anki.export_deck` bei einer **nicht-leeren** Kartenliste ab (hier: zwei
    Karten mit identischer GUID — siehe `_export_card` —, die `anki.export_deck` als
    Dublette innerhalb desselben Exports zurückweist), bucht `export_cards` keine der
    beiden Karten im Profil: Das Deck wird vor jeder Buchung geschrieben.

    Der Leerlisten-Test oben (`test_export_cards_raises_on_an_empty_card_list_...`)
    sichert diese Reihenfolge nicht zu — bei leerer Liste gibt es nichts zu buchen, eine
    vertauschte Reihenfolge bliebe dort unbemerkt (Befund 1, Durchsicht 82441bb).

    Verfälschungsprobe: `export_cards` mit `profile.record_card` **vor**
    `anki.export_deck` umgebaut → dieser Test rot (zwei `card`-Zeilen stehen trotz
    Fehlschlags), der Leerlisten-Test bleibt grün."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _EXPORT_BOOK, 1, "Testkapitel")
    duplicate_cards = [_export_card(_export_occurrence()), _export_card(_export_occurrence())]

    with pytest.raises(ValueError, match="mehrfach"):
        pipeline.export_cards(
            con,
            duplicate_cards,
            anki_path=tmp_path / "export.apkg",
            printout_path=tmp_path / "export.html",
            deck_name="Exportbuch - Kapitel 1",
        )

    assert con.execute("SELECT count(*) FROM card").fetchone()[0] == 0


def test_export_cards_does_not_book_a_card_when_the_printout_fails(tmp_path: Path) -> None:
    """Scheitert `printout.write_printout` bei einer **nicht-leeren** Kartenliste (hier:
    der Zielpfad ist ein Verzeichnis statt einer Datei — ein echter Fehlschlagweg, kein
    nachgestellter), steht danach ebenfalls keine `card`-Zeile im Profil: Die Buchung
    kommt nach **beiden** Exportdateien, nicht nur nach dem Deck (entschieden 16.09.2026,
    `libreverbum/pipeline.py`, `export_cards`) — das Profil darf nie mehr behaupten, als
    tatsächlich exportiert wurde.

    Verfälschungsprobe: `export_cards` auf die vorherige Reihenfolge zurückgebaut
    (`profile.record_card` gleich nach `anki.export_deck`, vor `printout.write_printout`)
    → dieser Test rot (die `card`-Zeile steht trotz gescheiterter Druckseite)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _EXPORT_BOOK, 1, "Testkapitel")
    printout_path = tmp_path / "export.html"
    printout_path.mkdir()

    with pytest.raises(OSError):
        pipeline.export_cards(
            con,
            [_export_card(_export_occurrence())],
            anki_path=tmp_path / "export.apkg",
            printout_path=printout_path,
            deck_name="Exportbuch - Kapitel 1",
        )

    assert con.execute("SELECT count(*) FROM card").fetchone()[0] == 0


# ------------------------------------------------------------- coverage (bauplan-phase2.md AP 6)
#
# `coverage` ist eine reine Rechnung über `ChapterVocabulary.token_count` und
# `VocabularyEntry.status` (E5, bauplan-phase2.md Abschnitt 1) — kein Datenbank- und kein
# Modellzugriff. Die Vorrichtung unten baut `ChapterVocabulary` deshalb von Hand aus
# Datenklassen zusammen, ohne `run_chapter`, `dictionary` oder `profile` aufzurufen: Es gibt
# nichts, worauf `coverage` zugreifen könnte, selbst wenn es wollte — `coverage` nimmt
# weder ein `sqlite3.Connection` noch eine Modell-URL entgegen (dokumentation.md §5, „Woran
# geprüft wird": eine bei Zugriff abbrechende Attrappe wäre hier der billigere, nicht
# nötige Weg).

_COVERAGE_BOOK = Book(title="Abdeckungstestbuch", author="Test Autorin")
_COVERAGE_CHAPTER = Chapter(book=_COVERAGE_BOOK, number=1, title="Testkapitel", text="")


def _coverage_entry(
    lemma_text: str,
    *,
    pos: str = "NOUN",
    frequency: int,
    proper_noun_frequency: int = 0,
    statuses: list[profile.VocabularyStatus],
) -> pipeline.VocabularyEntry:
    """Baut einen `VocabularyEntry` mit `len(statuses)` Kandidaten, je einer Bedeutung ein
    eigener `Sense` derselben Grundform — nur die Kombination der Status zählt für
    `coverage`, nicht die genauen Bedeutungstexte."""
    occurrence = Occurrence(
        book=_COVERAGE_BOOK,
        chapter_number=1,
        lemma=Lemma(text=lemma_text, pos=pos),
        word_form=lemma_text,
        example_sentence=f"Ein Beispielsatz mit {lemma_text}.",
        frequency=frequency,
        proper_noun_frequency=proper_noun_frequency,
    )
    candidates = [
        Sense(lemma=occurrence.lemma, wikdict_sense=f"{lemma_text} Bedeutung {index}")
        for index in range(len(statuses))
    ]
    return pipeline.VocabularyEntry(
        occurrence=occurrence,
        candidates=candidates,
        status=dict(zip(candidates, statuses, strict=True)),
    )


def _mini_chapter_vocabulary() -> pipeline.ChapterVocabulary:
    """Das handgerechnete Mini-Kapitel aus dem Auftrag zu AP 6: alle drei Fälle aus E5
    (bekannt, teilweise bekannt, unbekannt), dazu Funktionswörter und ein Eigenname — siehe
    die Rechnung in `test_coverage_matches_the_hand_calculated_mini_chapter`."""
    entries = [
        # bekannt: „cat" — die einzige Bedeutung ist KNOWN.
        _coverage_entry("cat", frequency=3, statuses=[profile.VocabularyStatus.KNOWN]),
        # teilweise bekannt: „bank" trägt hier **nur** NEW_MEANING_OF_KNOWN_WORD, kein
        # einziges KNOWN — E5 Festlegung 2 verlangt trotzdem „verstanden", weil schon eine
        # andere Bedeutung derselben Grundform bekannt ist.
        _coverage_entry(
            "bank", frequency=2, statuses=[profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD]
        ),
        # unbekannt: „xylophone" — keine Bedeutung bekannt.
        _coverage_entry("xylophone", frequency=4, statuses=[profile.VocabularyStatus.UNKNOWN]),
        # unbekannt, mit Eigennamenanteil: „doctor" kommt einmal gewöhnlich vor (unbekannt)
        # und zweimal als Teil eines Namens („Doctor Watson") — die beiden eigennamigen
        # Vorkommen bleiben nach E5 Festlegung 1 verstanden, unabhängig vom Kenntnisstand
        # der gewöhnlichen Bedeutung.
        _coverage_entry(
            "doctor",
            frequency=1,
            proper_noun_frequency=2,
            statuses=[profile.VocabularyStatus.UNKNOWN],
        ),
    ]
    # 10 Funktionswörter (the, a, and, of, in, to, …) — kein eigener Occurrence-Eintrag
    # (Regel: nur die fünf Inhaltswortarten kommen in `extract_vocabulary`s Wortliste,
    # technik.md §5), zählen aber zu `token_count` und bleiben nach E5 Festlegung 1
    # automatisch verstanden.
    function_word_tokens = 10
    token_count = sum(e.occurrence.frequency + e.occurrence.proper_noun_frequency for e in entries)
    token_count += function_word_tokens
    return pipeline.ChapterVocabulary(
        chapter=_COVERAGE_CHAPTER,
        notice=None,
        entries=entries,
        expressions=[],
        token_count=token_count,
    )


def test_coverage_matches_the_hand_calculated_mini_chapter() -> None:
    """bauplan-phase2.md AP 6, Prüfung „Handgerechnetes Mini-Kapitel".

    Rechnung (siehe `_mini_chapter_vocabulary`):
        token_count = (3+0) [cat] + (2+0) [bank] + (4+0) [xylophone] + (1+2) [doctor]
                       + 10 [Funktionswörter]
                     = 3 + 2 + 4 + 3 + 10 = 22
        understood_tokens = token_count - frequency(xylophone) - frequency(doctor)
                           = 22 - 4 - 1 = 17
            („cat" und „bank" bleiben unangetastet: beide verstanden — „bank" trotz
            ausschließlich NEW_MEANING_OF_KNOWN_WORD, E5 Festlegung 2. Die zwei
            eigennamigen „doctor"-Vorkommen zählen mit, nur das eine gewöhnliche nicht,
            E5 Festlegung 1.)
        unknown_lemma_count = 2  (xylophone, doctor)
        share = 17 / 22
    """
    vocabulary = _mini_chapter_vocabulary()

    result = pipeline.coverage(vocabulary)

    assert result.token_count == 22
    assert result.understood_tokens == 17
    assert result.unknown_lemma_count == 2
    assert result.share == pytest.approx(17 / 22)
    # Ohne `learned` (Vorgabe `()`) ändert sich nichts gegenüber `share`.
    assert result.share_after_learning == pytest.approx(17 / 22)


def test_coverage_share_after_learning_adds_back_only_the_learned_lemma() -> None:
    """E5 Festlegung 3: „Lerne diese N" sind die in diesem Durchgang auf `learning`
    gebuchten Grundformen — `share_after_learning` zeigt die Abdeckung, als wäre
    „xylophone" bereits gelernt.

    Rechnung: understood_after_learning = understood_tokens(17) + frequency(xylophone)(4)
    = 21, share_after_learning = 21 / 22. Eine zweite, im Kapitel gar nicht vorkommende
    Grundform in `learned` (hier „submarine") bleibt wirkungslos — es gibt keinen Eintrag,
    dessen Abzug sie rückgängig machen könnte."""
    vocabulary = _mini_chapter_vocabulary()

    result = pipeline.coverage(
        vocabulary,
        learned=[Lemma(text="xylophone", pos="NOUN"), Lemma(text="submarine", pos="NOUN")],
    )

    assert result.understood_tokens == 17  # unverändert: "jetzt", vor dem Lernen
    assert result.unknown_lemma_count == 2  # unverändert: zählt den Stand vor dem Lernen
    assert result.share_after_learning == pytest.approx(21 / 22)


def test_coverage_share_after_learning_ignores_a_learned_lemma_with_the_wrong_pos() -> None:
    """Befund 5 (Durchsicht 3e71fb8): `Lemma` ist `(text, pos)` — der Treffer in `learned`
    verlangt beide Felder gleich. „xylophone" steht im Kapitel als NOUN
    (`_mini_chapter_vocabulary`); ein `learned`-Eintrag mit derselben Wortform, aber der
    Wortart VERB, trifft deshalb keinen Eintrag und lässt `share_after_learning` **still**
    gleich `share` — kein Fehler, keine Markierung, nur ein wirkungsloses „Lernen". Für
    AP 17 (die Triage bucht `learning`) ist das die wahrscheinlichste Stolperstelle, wenn
    die Buchung die Wortart nicht mitgibt oder falsch mitgibt.

    Verfälschungsprobe: `coverage` auf einen Vergleich nur über `lemma.text` umgestellt
    (`entry.occurrence.lemma.text in {lemma.text for lemma in learned}`) lässt diesen Test
    fehlschlagen, weil `share_after_learning` dann wie im Test oberhalb auf 21/22 stiege."""
    vocabulary = _mini_chapter_vocabulary()

    result = pipeline.coverage(vocabulary, learned=[Lemma(text="xylophone", pos="VERB")])

    assert result.share_after_learning == result.share == pytest.approx(17 / 22)


def test_coverage_of_a_chapter_without_a_single_alphabetic_token_is_fully_understood() -> None:
    """Randfall: `token_count == 0` (ein Kapitel ganz ohne alphabetisches Token) teilte
    sonst durch null. Hier gibt es nichts zu verstehen, also gilt beides als vollständig
    verstanden (`1.0`) statt undefiniert."""
    vocabulary = pipeline.ChapterVocabulary(
        chapter=_COVERAGE_CHAPTER, notice=None, entries=[], expressions=[], token_count=0
    )

    result = pipeline.coverage(vocabulary)

    assert result.token_count == 0
    assert result.understood_tokens == 0
    assert result.unknown_lemma_count == 0
    assert result.share == 1.0
    assert result.share_after_learning == 1.0


# --------------------------------------------------------- assess_book (bauplan-phase2.md AP 7)


def test_assess_book_reports_the_same_coverage_as_run_chapter_per_chapter(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """bauplan-phase2.md AP 7: `assess_book` erfindet keine zweite Extraktions- oder
    Nachschlagelogik (Moduldocstring `assess_book`: „kein zweiter Weg dorthin") — je
    Kapitel mit Fließtext liefert es dieselbe `Coverage` wie ein eigener `run_chapter`-
    plus `coverage`-Aufruf auf dasselbe Kapitel, mit demselben (leeren) Profil."""
    structure = epub.read_structure(pipeline_epub)
    expected = {
        chapter.number: pipeline.coverage(
            pipeline.run_chapter(
                epub_path=pipeline_epub,
                chapter_number=chapter.number,
                dictionary_path=mini_dictionary_db,
                profile_path=profile_path,
                nlp=nlp,
            )
        )
        for chapter in structure.chapters
    }

    result = pipeline.assess_book(
        epub_path=pipeline_epub,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )

    assert [chapter.number for chapter in result.chapters] == [1, 2]
    assert result.skipped == []
    for chapter in result.chapters:
        assert chapter.coverage == expected[chapter.number]
        assert chapter.token_count == expected[chapter.number].token_count
        assert chapter.unknown_lemma_count == expected[chapter.number].unknown_lemma_count


def test_assess_book_skips_a_chapter_without_text_and_reports_it(
    pipeline_epub_with_a_chapter_without_text: Path,
    mini_dictionary_db: Path,
    existing_profile_path: Path,
    nlp: Language,
) -> None:
    """bauplan-phase2.md AP 7: Ein Kapitel ohne Fließtext (hier Kapitel 2, reiner
    Vorspann/Impressum) fehlt in `chapters`, steht aber mit seinem Grund in `skipped` —
    sichtbar gemeldet, nicht still weggelassen (Regel 13, dokumentation.md §4). Der
    Buchwert entspricht dann genau dem einen verbliebenen Kapitel, nicht verdünnt durch
    ein textloses.

    Verfälschungsprobe (dokumentation.md §5, „Ein Test gilt erst als Test, wenn er einmal
    rot war"; siehe Bericht zu diesem Auftragspaket): Die Bedingung in `assess_book`
    umgekehrt (`if listing.skip_reason is None: skipped.append(listing); continue`) —
    also das Vorspann-Kapitel verarbeitet und das Kapitel mit Text übersprungen — ließ
    diesen Test rot werden, aber anders als erwartet: `run_chapter` wirft für das dann
    „verarbeitete" Vorspann-Kapitel selbst `epub.ChapterWithoutTextError` (`assess_book`
    fängt sie nicht ab, Regel 13), der Test schlägt also mit dieser Ausnahme fehl statt
    mit einer Assertion — ebenfalls rot, nur lauter als vermutet."""
    result = pipeline.assess_book(
        epub_path=pipeline_epub_with_a_chapter_without_text,
        dictionary_path=mini_dictionary_db,
        profile_path=existing_profile_path,
        nlp=nlp,
    )

    assert [chapter.number for chapter in result.chapters] == [1]
    assert [listing.number for listing in result.skipped] == [2]
    assert result.skipped[0].skip_reason is not None
    assert result.token_count == result.chapters[0].token_count
    assert result.unique_unknown_lemma_count == result.chapters[0].unknown_lemma_count


def test_assess_book_aggregates_over_word_forms_not_as_average_of_chapter_shares(
    pipeline_epub: Path, mini_dictionary_db: Path, existing_profile_path: Path, nlp: Language
) -> None:
    """Auftragstext AP 7: „Die Buchzahl aggregiert über Wortformen (Summe der
    token_count), nicht als Mittel der Kapitelquoten." Kapitel 1 und 2 aus `pipeline_epub`
    tragen unterschiedlich viele Wortformen — ein ungewichtetes Mittel der beiden
    Kapitelquoten weicht deshalb messbar vom `token_count`-gewichteten Buchwert ab, den
    `coverage`s eigener Docstring unter „Vorbehalt für bauplan-phase2.md AP 7" verlangt.

    Verfälschungsprobe (Bericht): `book_share` in `assess_book` auf das ungewichtete
    Mittel der Kapitelquoten umgestellt (`sum(c.coverage.share for c in chapters) /
    len(chapters)` statt `Summe understood_tokens / Summe token_count`) ließ diesen Test
    rot werden — die beiden Werte fielen dabei nicht mehr zusammen."""
    result = pipeline.assess_book(
        epub_path=pipeline_epub,
        dictionary_path=mini_dictionary_db,
        profile_path=existing_profile_path,
        nlp=nlp,
    )

    assert len(result.chapters) == 2
    total_token_count = sum(chapter.token_count for chapter in result.chapters)
    total_understood = sum(chapter.coverage.understood_tokens for chapter in result.chapters)
    assert result.token_count == total_token_count
    assert result.coverage.understood_tokens == total_understood
    assert result.coverage.share == pytest.approx(total_understood / total_token_count)

    naive_average = sum(chapter.coverage.share for chapter in result.chapters) / len(
        result.chapters
    )
    assert result.coverage.share != pytest.approx(naive_average), (
        "Testvoraussetzung verletzt: Buchwert und ungewichtetes Mittel der Kapitelquoten "
        "fallen bei pipeline_epub zusammen - dieser Test prüft dann nicht die verlangte "
        "Gewichtung."
    )


def test_assess_book_raises_for_a_missing_dictionary_file(
    pipeline_epub: Path, tmp_path: Path, profile_path: Path, nlp: Language
) -> None:
    """Regel 13 (dokumentation.md §4): Bricht sichtbar ab, geprüft vor dem ersten
    `run_chapter`-Aufruf — dieselbe Zusicherung wie bei `run_chapter` selbst (siehe dessen
    Test `test_run_chapter_checks_the_dictionary_file_before_extracting_any_vocabulary`
    weiter oben)."""
    with pytest.raises(FileNotFoundError, match="Wörterbuch nicht lesbar"):
        pipeline.assess_book(
            epub_path=pipeline_epub,
            dictionary_path=tmp_path / "fehlt.sqlite3",
            profile_path=profile_path,
            nlp=nlp,
        )


def test_assess_book_raises_for_a_missing_profile_file_and_creates_none(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Befund 1, Durchsicht c6f3875, Entscheidung Dominiks 23.09.2026: `assess_book`
    öffnet das Profil nur lesend und legt nie eine Datei an — gegen ein leeres, gerade erst
    angelegtes Profil käme immer „zu schwer" heraus (`tools/sherlock.epub` ohne Profil:
    58,4 % Abdeckung, Bericht zu dieser Nachbesserung). `profile_path` (anders als
    `existing_profile_path`) zeigt hier bewusst auf eine noch nicht vorhandene Datei.

    Verfälschungsprobe (Bericht): die neue Prüfung `if not profile_path.is_file(): raise
    …` aus `assess_book` entfernt ließ diesen Test rot werden — statt der erwarteten
    Ausnahme legte `run_chapter` (über `profile.open_profile`) klaglos eine leere
    Profildatei an, und `pytest.raises` schlug fehl."""
    assert not profile_path.is_file()

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        pipeline.assess_book(
            epub_path=pipeline_epub,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
        )

    assert not profile_path.is_file(), (
        "assess_book hat trotz der Ausnahme eine Profildatei angelegt"
    )


def test_assess_book_leaves_a_zero_byte_profile_file_untouched_and_aborts(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """Befund 2, Nachbesserung Durchsicht 3b1e201: Eine vorhandene, aber 0 Byte große
    Profildatei bestand die frühere `profile_path.is_file()`-Prüfung — `assess_book`
    öffnete das Profil vor dieser Behebung erst beim ersten `run_chapter`-Aufruf, und
    dessen eigener, schreibender `profile.open_profile`-Zugriff legte gegen `user_version
    == 0` klaglos das volle Schema an (Bericht zu dieser Nachbesserung: 65.536 Byte,
    `user_version = 2`, Abdeckung „zu schwer" statt eines Abbruchs). Seit dieser Behebung
    öffnet `assess_book` das Profil **vor** jedem `run_chapter`-Aufruf selbst, wirklich nur
    lesend (`profile.open_profile(read_only=True)`) — eine 0-Byte-Datei gilt dabei als
    dasselbe „kein Profil" wie eine fehlende Datei, und bleibt unangetastet.

    Verfälschungsprobe (Bericht): Die Vorprüfung selbst (`profile.open_profile(profile_
    path, read_only=True).close()`) durch die frühere `if not profile_path.is_file():
    raise …` ersetzt ließ diesen Test **grün bleiben** — die Zusicherung war zu schwach:
    `run_chapter`s eigenes `profile_read_only=True` (siehe unten,
    `test_run_chapter_with_profile_read_only_does_not_create_a_missing_profile`) schützt
    dieselbe Datei ein zweites Mal, also bleibt das Endergebnis (Ausnahme, Datei bleibt 0
    Byte) auch bei entfernter Vorprüfung richtig. Geschärft in
    `test_assess_book_checks_the_profile_before_calling_run_chapter` unten, die
    `run_chapter` durch eine Attrappe ersetzt, die bei jedem Aufruf abbricht — nur so wird
    sichtbar, dass die Vorprüfung selbst greift, nicht erst der zweite, nachgelagerte
    Schutz."""
    profile_path.touch()
    assert profile_path.stat().st_size == 0

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        pipeline.assess_book(
            epub_path=pipeline_epub,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
        )

    assert profile_path.stat().st_size == 0, (
        "assess_book hat die 0-Byte-Profildatei still mit Schema gefüllt"
    )


def test_assess_book_checks_the_profile_before_calling_run_chapter(
    pipeline_epub: Path,
    mini_dictionary_db: Path,
    profile_path: Path,
    nlp: Language,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 2, Nachbesserung Durchsicht 3b1e201: `assess_book`s eigener Lesezugriff
    prüft das Profil, **bevor** `list_chapters`/`run_chapter` überhaupt aufgerufen werden
    (`assess_book`s Docstring: „vor jedem Aufruf von list_chapters/run_chapter"). Isoliert
    die Vorprüfung von `run_chapter`s eigenem, nachgelagertem Schutz (siehe die schärfere
    Verfälschungsprobe bei `test_assess_book_leaves_a_zero_byte_profile_file_untouched_
    and_aborts` oben) — `run_chapter` wird hier durch eine Attrappe ersetzt, die bei jedem
    Aufruf abbricht.

    Verfälschungsprobe (Bericht): Die Vorprüfung durch `if not profile_path.is_file():
    raise …` ersetzt ließ diesen Test rot werden — statt der erwarteten
    `FileNotFoundError` (aus der Vorprüfung) griff die Attrappe, weil `assess_book` bis zum
    ersten `run_chapter`-Aufruf durchlief."""
    profile_path.touch()

    def _must_not_be_called(**kwargs: object) -> None:
        raise AssertionError("run_chapter aufgerufen, bevor das Profil geprüft war")

    monkeypatch.setattr(pipeline, "run_chapter", _must_not_be_called)

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        pipeline.assess_book(
            epub_path=pipeline_epub,
            dictionary_path=mini_dictionary_db,
            profile_path=profile_path,
            nlp=nlp,
        )


def test_assess_book_does_not_modify_an_existing_valid_profile_file(
    pipeline_epub: Path, mini_dictionary_db: Path, existing_profile_path: Path, nlp: Language
) -> None:
    """Befund 2, Nachbesserung Durchsicht 3b1e201: `assess_book` öffnet ein bestehendes,
    gültiges Profil ebenfalls nur lesend — bytegleich vor und nach dem Lauf, keine
    `-journal`/`-wal`-Datei daneben. Ergänzt den 0-Byte-Test oben: Der dort geprüfte
    Randfall (Version 0, keine Tabelle) ist nicht derselbe Codepfad wie der hier geprüfte
    Regelfall (Version 2, alle Tabellen vorhanden) — `_check_existing_schema_version`
    (`libreverbum/profile.py`) läuft für Letzteren, für Ersteren gerade nicht."""
    before_hash = hashlib.sha256(existing_profile_path.read_bytes()).hexdigest()

    pipeline.assess_book(
        epub_path=pipeline_epub,
        dictionary_path=mini_dictionary_db,
        profile_path=existing_profile_path,
        nlp=nlp,
    )

    after_hash = hashlib.sha256(existing_profile_path.read_bytes()).hexdigest()
    assert after_hash == before_hash, "assess_book hat ein bestehendes Profil verändert"
    sibling_names = {p.name for p in existing_profile_path.parent.iterdir()}
    assert f"{existing_profile_path.name}-journal" not in sibling_names
    assert f"{existing_profile_path.name}-wal" not in sibling_names


def test_assess_book_counts_a_lemma_unknown_in_two_chapters_only_once(
    pipeline_epub_sharing_a_word: Path,
    mini_dictionary_db: Path,
    existing_profile_path: Path,
    nlp: Language,
) -> None:
    """Befund 3, Durchsicht c6f3875: `unique_unknown_lemma_count` ist die Vereinigung der
    im ganzen Buch unbekannten Grundformen, keine Summe der Kapitelzahlen — eine Grundform,
    die in zwei Kapiteln unbekannt ist (hier „watch" als Substantiv, `pipeline_epub_sharing
    _a_word`), zählt fürs Buch nur einmal. Vorher: 16.427 statt 5.919 tatsächlich
    verschiedener unbekannter Grundformen an `tools/sherlock.epub` ohne Profil (Bericht zu
    dieser Nachbesserung).

    Verfälschungsprobe (Bericht): `unique_unknown_lemmas` in `assess_book` durch die frühere
    Summe der Kapitel-`unknown_lemma_count` ersetzt ließ diesen Test rot werden — die
    Buchzahl war dann 2 statt 1 höher als die tatsächliche Vereinigung."""
    result = pipeline.assess_book(
        epub_path=pipeline_epub_sharing_a_word,
        dictionary_path=mini_dictionary_db,
        profile_path=existing_profile_path,
        nlp=nlp,
    )

    assert len(result.chapters) == 2
    naive_sum = sum(chapter.unknown_lemma_count for chapter in result.chapters)
    assert naive_sum - result.unique_unknown_lemma_count == 1, (
        f"Testvoraussetzung oder Behebung verletzt: naive Summe {naive_sum}, "
        f"Vereinigung {result.unique_unknown_lemma_count} — erwartet ist genau ein "
        'kapitelübergreifend geteiltes unbekanntes Wort ("watch").'
    )


def test_assess_book_computes_the_proper_noun_ratio_cache_only_once_per_run(
    pipeline_epub: Path,
    mini_dictionary_db: Path,
    existing_profile_path: Path,
    nlp: Language,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bauplan-phase2.md AP 7: `assess_book` ruft `run_chapter` für jedes Kapitel mit
    Fließtext auf — ohne den Zwischenspeicher aus technik.md §5 (`cache_dir`) läge darin
    ein voller Buchdurchgang je Kapitel. Mit gesetztem `cache_dir` trifft ab dem zweiten
    Kapitel derselbe Zwischenspeicher, den der erste Aufruf gerade erst geschrieben hat
    (`pipeline_epub` trägt zwei Kapitel mit Text): `extraction.book_proper_noun_ratios`
    läuft deshalb genau einmal, nicht zweimal — geprüft an einer zählenden Attrappe, die
    den echten Aufruf durchreicht (dokumentation.md §5, „Woran geprüft wird").

    Verfälschungsprobe (Bericht): Im Aufruf von `run_chapter` innerhalb von `assess_book`
    `cache_dir=cache_dir` durch `cache_dir=None` ersetzt ließ diesen Test mit zwei statt
    einem Aufruf rot werden."""
    cache_dir = tmp_path / "cache"
    calls = 0
    real_book_proper_noun_ratios = extraction.book_proper_noun_ratios

    def _counting(
        chapters: Sequence[Chapter],
        nlp_arg: Language,
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, float]:
        nonlocal calls
        calls += 1
        return real_book_proper_noun_ratios(chapters, nlp_arg, on_progress=on_progress)

    monkeypatch.setattr(extraction, "book_proper_noun_ratios", _counting)

    result = pipeline.assess_book(
        epub_path=pipeline_epub,
        dictionary_path=mini_dictionary_db,
        profile_path=existing_profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )

    assert len(result.chapters) == 2
    assert calls == 1


@pytest.mark.needs_dictionary
@pytest.mark.needs_epub
def test_assess_book_against_the_real_dictionary_and_book_shows_higher_coverage_with_a_b1_preset(
    real_dictionary_path: Path, real_epub_paths: dict[str, Path], tmp_path: Path
) -> None:
    """dokumentation.md §5, „Woran geprüft wird": Was über den Inhalt einer Fremdquelle
    behauptet wird, wird zusätzlich gegen das echte Gegenüber geprüft — bisher liefen alle
    assess-Tests nur mit leerem Profil (Befund 4, Durchsicht c6f3875). Hier gegen
    `tools/sherlock.epub` und `tools/en-de.sqlite3`, einmal mit leerem und einmal mit
    B1-vorbelegtem Profil: Die Vorbelegung muss die Abdeckung sichtbar anheben.

    Rezept (Bericht zu dieser Nachbesserung): `pipeline.assess_book` gegen
    `tools/sherlock.epub`/`tools/en-de.sqlite3`, `.venv/Scripts/python.exe`, 23.09.2026 —
    leeres Profil 58,36 % Abdeckung, B1-Profil 87,34 % (13 Kapitel mit Text, Kapitel 14
    übersprungen). Die Schranken unten liegen großzügig um diese beiden Werte, damit der
    Test nicht bei jeder Rundungsdifferenz kippt, aber jede grobe Regression (etwa eine
    vertauschte Vorbelegung) auffängt."""
    nlp = extraction.load_nlp()
    cache_dir = tmp_path / "cache"  # geteilt: der buchweite Eigennamenanteil ist vom
    # Profil unabhängig (technik.md §5) — der zweite Aufruf unten trifft ihn und liest das
    # Buch kein zweites Mal vollständig ein.

    empty_profile_path = tmp_path / "empty" / "profil.sqlite3"
    empty_profile_path.parent.mkdir()
    profile.open_profile(empty_profile_path).close()

    b1_profile_path = tmp_path / "b1" / "profil.sqlite3"
    b1_profile_path.parent.mkdir()
    pipeline.write_vocabulary_preset(
        dictionary_path=real_dictionary_path,
        profile_path=b1_profile_path,
        cefr_level=CefrLevel.B1,
        timestamp=datetime.now(UTC),
    )

    empty_result = pipeline.assess_book(
        epub_path=real_epub_paths["sherlock"],
        dictionary_path=real_dictionary_path,
        profile_path=empty_profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )
    b1_result = pipeline.assess_book(
        epub_path=real_epub_paths["sherlock"],
        dictionary_path=real_dictionary_path,
        profile_path=b1_profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
    )

    assert b1_result.coverage.share > empty_result.coverage.share
    assert 0.50 < empty_result.coverage.share < 0.65, empty_result.coverage.share
    assert 0.80 < b1_result.coverage.share < 0.92, b1_result.coverage.share
