"""Prüft `libreverbum/pipeline.py` — bauplan.md T15, Durchstich für ein Kapitel."""

from __future__ import annotations

import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cli import interaction
from libreverbum import dictionary, epub, extraction, pipeline, profile
from libreverbum.entities import (
    Book,
    CardDirection,
    Event,
    KnowledgeState,
    Lemma,
    Occurrence,
    Origin,
    Sense,
)
from libreverbum.extraction import load_nlp

if TYPE_CHECKING:
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


@pytest.fixture(scope="module")
def nlp() -> Language:
    """Lädt das spaCy-Modell einmal für alle Tests dieser Datei (technik.md §5, rund eine
    Sekunde) — genau die Voraussetzung, die `pipeline.run_chapter` an den Aufrufer stellt."""
    return load_nlp()


@pytest.fixture
def profile_path(tmp_path: Path) -> Path:
    return tmp_path / "profil.sqlite3"


def _entry(result: pipeline.ChapterVocabulary, lemma_text: str) -> pipeline.VocabularyEntry:
    matches = [e for e in result.entries if e.occurrence.lemma.text == lemma_text]
    assert len(matches) == 1, f"{lemma_text!r} genau einmal erwartet, {len(matches)}-mal gefunden"
    return matches[0]


def _expressions(
    result: pipeline.ChapterVocabulary, lemma_text: str
) -> list[pipeline.VocabularyEntry]:
    """`expressions` enthält denselben Wortlaut über zwei Wege zugleich (Befund 1, Review
    T15): den Verb-Partikel-Weg (`Lemma.pos == "VERB"`) und den n-Gramm-Weg
    (`Lemma.pos == ""`) — beide sind nicht zusammengeführt, deshalb keine Eindeutigkeit
    wie bei `_entry`."""
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


def test_run_chapter_reflects_a_known_event_recorded_before_the_run(
    pipeline_epub: Path, mini_dictionary_db: Path, profile_path: Path, nlp: Language
) -> None:
    """konzept.md, Nachtrag 18.08.2026 beim Kernablauf: Der Abgleich gegen das Profil
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
    bauplan.md T2) über beide Wege aus T4 zugleich: den Verb-Partikel-Weg (`Lemma.pos ==
    "VERB"`) und den n-Gramm-Weg (`Lemma.pos == ""`), beide mit derselben vollen
    Auswahlliste wie ein einzelner Aufruf von `dictionary.particle_verb_candidates`."""
    result = pipeline.run_chapter(
        epub_path=pipeline_epub,
        chapter_number=1,
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        nlp=nlp,
    )

    give_up_entries = _expressions(result, "give up")
    assert len(give_up_entries) == 2
    assert {e.occurrence.lemma.pos for e in give_up_entries} == {"VERB", ""}
    for entry in give_up_entries:
        assert {s.wikdict_trans_list for s in entry.candidates} == {
            "aufgeben | kapitulieren",
            "aufgeben | ergeben",
        }
        assert all(sense.uncertain is False for sense in entry.candidates)
        # Wie bei entries: der Kenntnisstand jeder Bedeutung ist gegen das Profil
        # abgeglichen, nicht nur die Auswahlliste beschafft.
        assert all(status == profile.VocabularyStatus.UNKNOWN for status in entry.status.values())


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
    (technik.md §3, „Nachtrag 17.08.2026"), und die Nutzerdatei bleibt unverändert.

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
    """Zeitbudget aus konzept.md §4 („eine halbe Minute" bei höchstens 25 neuen Wörtern):
    Für ein Kapitel mit sehr vielen Grundformen werden nicht alle beim Modell vorgelegt —
    hier 1.000 synthetische, unzweideutige Wörter gegen ein `limit` von 25. Ohne den
    Abbruch aus Schritt 4 (`resolve_triage_entries`) wären das 1.000 Modellanfragen statt
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
    assert resolution.deferred == total - limit


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
        )
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
    """Befund mittel, Durchsicht 46ef37b: `known + resolved_known + skipped + deferred +
    len(resolution.entries)` muss wieder die Zahl der übergebenen Einträge ergeben — sonst
    verschwindet ein Teil unbeziffert aus jeder Meldung, wie im Auftragsbeispiel
    („4" statt „25" bereits bekannt: 4 + 1.360 + 25 = 1.389 statt 1.410).

    Eine Häufigkeitskaskade mit je einem Eintrag für jede der vier Zählungen und der
    behaltenen Liste: `alpha` (Vorfilter bekannt, kein Modellaufruf), `vault`
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
    assert resolution.deferred == 1
    assert [entry.occurrence.lemma.text for entry in resolution.entries] == ["pen"]
    assert len(model_server_double.requests) == 3

    total = (
        resolution.known
        + resolution.resolved_known
        + resolution.skipped
        + resolution.deferred
        + len(resolution.entries)
    )
    assert total == len(all_entries)
