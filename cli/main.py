"""Einstiegspunkt — ein vollständiger Kapiteldurchlauf (bauplan.md T16).

Aufgabe
-------
Verkettet, was `app.config`, `libreverbum.epub`, `libreverbum.extraction`,
`libreverbum.pipeline`, `cli.interaction` und `app.export` je für sich liefern, zu einem
Aufruf von der Kommandozeile: Wörterbuch beziehen oder indizieren
(`libreverbum.dictionary`), EPUB wählen, Kapitel wählen, `pipeline.run_chapter`,
je Decksel eine blockweise Triage über `interaction.run_triage_blocks` (Bedeutung vor der
Triage auflösen über `pipeline.resolve_triage_entries`, Befund schwer 1, zweite
T16-Durchsicht; Blockschleife samt Fortsetzungsfrage seit Bauschritt 2/4, Vorladen des
nächsten Blocks im Hintergrund seit Bauschritt 3/4, technik.md §12),
Triage über die Tastatur (Wörter, dann Wendungen), Export nach Anki und als Druckseite.
Scheitert die Triage mitten im Lauf (etwa ein wegbrechender Modellserver), exportiert
`_run` die bis dahin entschiedenen Karten als Teilexport und reicht die Ausnahme danach
unverändert weiter (technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf
exportiert, was er hat").

`--chapters 3-7`/`--chapters all` (bauplan-phase2.md AP 5, E6 (a), E3-Ausnahme): dasselbe
Kapitel-für-Kapitel wie `--chapter N`, nur mehrfach — Sprachmodell und Profilverbindung
werden dafür **einmal** geöffnet und über alle gewählten Kapitel hinweg benutzt (nicht je
Kapitel neu), damit die „kenne ich"-Buchungen eines Kapitels die Auswahlliste der
folgenden verkleinern; jedes Kapitel behält seinen eigenen Export. Kapitel ohne
Fließtext werden gemeldet und übersprungen, kein Abbruch (`pipeline.list_chapters`, AP 4).
Am Ende steht eine Bilanz über alle verarbeiteten und übersprungenen Kapitel.

Regel 9 (dokumentation.md §4), strukturelle Hälfte: Dieses Kommandozeilenprogramm hat
keine Ereignisschleife und keinen Oberflächen-Thread, den ein NLP- oder Modellaufruf
blockieren könnte — die prüfbare Hälfte der Regel ist hier **trivial erfüllt**, nicht
vergessen. Sie wird erst wieder relevant, sobald `cli` durch eine Qt-Oberfläche ersetzt
oder ergänzt wird (bauplan.md, Tor 5).

Voraussetzungen
---------------
Eine interaktive Konsole. `--data-dir` erlaubt, das Datenverzeichnis `data/` neben dem
Projekt (technik.md §9) für Tests durch ein Wegwerfverzeichnis zu ersetzen.

Liefert
-------
`main` einen Rückgabewert für `sys.exit` (0 Erfolg, 1 sichtbarer Abbruch nach Regel 13).
"""

from __future__ import annotations

import argparse
import re
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, assert_never

from app import config, export, model
from cli import display, interaction
from cli.display import finish_progress_line, safe_print, safe_print_progress
from cli.interaction import ReadLine, WriteLine
from libreverbum import dictionary, epub, extraction, pipeline, profile
from libreverbum.entities import Card, CardDirection, CefrLevel

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable

    from spacy.language import Language


def _build_parser() -> argparse.ArgumentParser:
    # (Befund mittel 3, Durchsicht T16): argparse.print_help()/format_help() schreiben
    # direkt auf sys.stdout beziehungsweise sys.stderr, an cli.display.safe_print vorbei
    # (dokumentation.md §4 Regel 13) — description und jeder help-Text unten meiden
    # deshalb Gedankenstrich und typografische Anführungszeichen, die einzigen Zeichen,
    # die cp850 (die klassische DOS-/conhost-Codepage, tests/test_cli_display.py nennt
    # sie als die gefährliche, nicht bloß cp1252) nicht darstellen kann
    # (test_help_text_survives_a_restricted_console_codepage in tests/test_cli_main.py
    # kodiert format_help() gegen genau diese Codepage). Umlaute und ß bleiben stehen —
    # cp850 stellt sie dar, und die Sprachregel (dokumentation.md §1) gilt für Hilfetexte
    # wie für jeden anderen Oberflächentext. Eine frühere Fassung dieser Behebung zwang
    # die Texte fälschlich auf reines ASCII und schrieb dabei Umlaute in
    # Ersatzschreibung ("ueber", "fuer") — unnötig und selbst ein Verstoß gegen die
    # Sprachregel, am 21.08.2026 korrigiert.
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="LibreVerbum: Kapiteldurchlauf mit Triage über die Tastatur (bauplan.md T16).",
    )
    parser.add_argument("epub_path", type=Path, help="Pfad zur EPUB-Datei")
    parser.add_argument(
        "--chapter", type=int, default=None, help="Kapitelnummer (fehlt sie, wird gefragt)"
    )
    parser.add_argument(
        "--chapters",
        type=str,
        default=None,
        help=(
            "Kapitelbereich statt einer einzelnen Nummer, z. B. 3-7 oder all für alle "
            "Kapitel (bauplan-phase2.md AP 5); schließt sich mit --chapter aus"
        ),
    )
    parser.add_argument(
        "--card-direction",
        choices=[direction.value for direction in CardDirection],
        default=CardDirection.EN_DE.value,
        help="Kartenrichtung des Exports (konzept.md §6), Vorgabe: Englisch nach Deutsch",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Zielverzeichnis für Anki-Deck und Druckseite (Vorgabe: aktuelles Verzeichnis)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Abweichendes Datenverzeichnis statt data/ neben dem Projekt (technik.md §9)",
    )
    return parser


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def _confirm_new_profile(profile_path: Path, read_line: ReadLine, write_line: WriteLine) -> bool:
    """Fragt vor dem ersten Anlegen einer Profildatei nach Bestätigung.

    Entscheidung zu T16 (siehe Bericht): `profile.open_profile` legt eine fehlende Datei
    sonst wortlos an (`profile.py`, Docstring zu `open_profile`: „Ob ein noch nicht
    vorhandenes Profil bestätigt werden muss, entscheidet der Aufrufer") — und ein Profil
    an der falschen Stelle sähe dann aus wie ein verlorenes (CLAUDE.md: „profil.sqlite3
    … der langfristige Wert des Programms, gehört nie ins Repository"). Vorgabe bei
    bloßem Enter ist Ablehnung, nicht Zustimmung: Ein falscher Pfad in `config.toml`
    (Tippfehler, ein noch nicht eingehängtes Laufwerk) soll nicht durch einen
    versehentlichen Tastendruck als „ja, neu anlegen" durchgehen.
    """
    if profile_path.is_file():
        return True
    write_line(f"Unter {profile_path} liegt noch kein Profil.")
    answer = read_line("Neu anlegen? [j/N] ").strip().lower()
    return answer in ("j", "ja")


def _format_count(count: int) -> str:
    """Deutsches Tausendertrennzeichen (`8.044`), wie `_format_word_count` unten — eigene,
    kleinere Funktion, weil hier nie ein unbekannter Wert vorkommt (anders als beim
    Wortumfang je Kapitel, der `None` kennt)."""
    return f"{count:,}".replace(",", ".")


def _ask_cefr_level(read_line: ReadLine, write_line: WriteLine) -> CefrLevel | None:
    """Fragt beim Anlegen eines neuen Profils nach dem Sprachniveau für die einmalige
    Vorbelegung des Grundwortschatzes (konzept.md, „Bewusst offen", „Woher der Nutzer
    seinen Grundwortschatz bekommt", Bauschritt 4/5, 31.08.2026).

    Leere oder ungültige Eingabe fragt erneut, statt stillschweigend eine Stufe zu wählen
    oder die Vorbelegung zu überspringen — Vorbild ist `cli.interaction._ask_action`.
    Genau das darf hier nicht passieren, was technik.md §9, „Offene Punkte" für den
    Triage-Prompt beschreibt: Eine Leereingabe, die als Antwort durchgeht, hat dort schon
    zwei Abnahmeläufe gekostet, bevor die Ursache feststand. „Keine Angabe" ist deshalb
    eine Antwort, die ausdrücklich eingegeben werden muss, keine Vorgabe für Enter — beide
    Antworten sind teuer und ungleich teuer: Eine gewählte Stufe trägt mit einem
    Tastendruck tausende ungesehene Behauptungen ins Profil, „keine Angabe" verzichtet
    ganz darauf und verlangt später einen Kalibrierdurchlauf von Hand.

    (Befund leicht b, Durchsicht ee34796): Die Stufenliste im Prompt baut sich aus
    `CefrLevel` auf, statt Hand gepflegt zu sein — käme `C2` hinzu oder fiele eine Stufe
    weg, zeigte eine von Hand geschriebene Aufzählung sonst still eine falsche Auswahl, und
    kein Test bemerkte es. Bei den Zahlen ist die Lage seit `PRESET_WORD_COUNT` schon
    sauber (`test_preset_word_count_covers_every_cefr_level`); hier zieht dieselbe
    Vorrichtung für die Stufennamen nach."""
    level_names = [level.value.upper() for level in CefrLevel]
    write_line("Beim Anlegen lässt sich der englische Grundwortschatz einmalig vorbelegen:")
    write_line("Die häufigsten Grundformen des gewählten Niveaus gelten dann als bekannt.")
    for level in CefrLevel:
        word_count = _format_count(pipeline.PRESET_WORD_COUNT[level])
        write_line(f"  {level.value.upper()} - rund {word_count} Grundformen")
    write_line("  keine Angabe - nichts wird vorbelegt, das Profil beginnt leer")
    # (Befund leicht c, Durchsicht ee34796): Nicht jede der „rund N" Grundformen hat
    # tatsächlich einen Wörterbucheintrag (bei A1 rund 16 %, bei C1 rund 18 %, gemessen
    # gegen tools/en-de.sqlite3) — die Abschlussmeldung in `_apply_vocabulary_preset` nennt
    # die tatsächliche Deckung, dieser Hinweis kündigt sie schon hier vorsichtig an.
    write_line(
        "Nicht jede Grundform hat einen Wörterbucheintrag - die Abschlussmeldung nennt "
        "die tatsächliche Deckung."
    )
    while True:
        answer = (
            read_line(f"Sprachniveau [{'/'.join(level_names)}] oder 'keine Angabe': ")
            .strip()
            .lower()
        )
        if answer in ("keine angabe", "keine"):
            return None
        try:
            return CefrLevel(answer)
        except ValueError:
            write_line(
                f"Ungültige Eingabe - {', '.join(level_names)} oder 'keine Angabe' erwartet."
            )


def _apply_vocabulary_preset(
    *, dictionary_path: Path, profile_path: Path, read_line: ReadLine, write_line: WriteLine
) -> None:
    """Fragt das Sprachniveau ab und schreibt die Vorbelegung (Bauschritt 4/5, 31.08.2026)
    — nur beim Anlegen eines neuen Profils aufzurufen, nie bei einem vorhandenen (der
    Aufrufer in `_run` entscheidet das, nicht diese Funktion).

    `pipeline.write_vocabulary_preset` bricht bei einem Fehlschlag sichtbar ab (Regel 13),
    und die Ausnahme läuft **unverändert** bis zu `main`s eigenem Fang durch — das `except`
    unten protokolliert nichts und läuft nicht weiter, es räumt nur eine Nebenwirkung auf,
    bevor es weiterreicht (siehe nächster Absatz).

    (Befund mittel 1, Durchsicht ee34796): `profile.record_preset` ist nur für die
    **Ereignisse** atomar — `pipeline.write_vocabulary_preset` ruft davor aber bereits
    `profile.open_profile` auf, das eine fehlende Profildatei anlegt und das volle Schema
    schreibt, **bevor** `record_preset` überhaupt beginnt. Scheitert `record_preset`
    danach, blieb bislang eine leere, aber existierende Profildatei zurück (65.536 Byte,
    `user_version = 2`, kein Ereignis) — und `_run` prüft beim nächsten Lauf allein die
    Dateiexistenz (`profile_is_new = not cfg.profile_path.is_file()`), fragt also nie
    wieder, das Profil bleibt für immer unvorbelegt. Diese Funktion merkt sich deshalb, ob
    die Datei **vor** dem Aufruf schon da war; scheitert der Aufruf und war sie es nicht,
    entfernt sie die gerade erst entstandene Datei wieder, bevor die Ausnahme
    weiterläuft — der nächste Lauf sieht dann wieder eine fehlende Datei und fragt erneut.
    Existierte die Datei schon vorher (dieser Fall tritt über den Aufrufer in `_run` heute
    nie ein, siehe oben), bleibt sie unangetastet: Gelöscht wird nur, was dieser Aufruf
    selbst angelegt hat.

    Bei „keine Angabe" bleibt es bei der Frage selbst — `write_vocabulary_preset` öffnet
    die Profildatei dann nicht einmal, also gibt es nichts zu melden."""
    cefr_level = _ask_cefr_level(read_line, write_line)
    profile_existed_before = profile_path.is_file()
    try:
        result = pipeline.write_vocabulary_preset(
            dictionary_path=dictionary_path,
            profile_path=profile_path,
            cefr_level=cefr_level,
            timestamp=datetime.now(UTC),
        )
    except Exception:
        # REGEL (dokumentation.md §4 Regel 13, „Kein except, das nur protokolliert und
        # weiterläuft"): Räumt nur die gerade erst angelegte Profildatei weg und läuft mit
        # `raise` unverändert weiter — es meldet nichts selbst und bricht den Lauf nicht
        # selbst ab, das bleibt `main`s eigenem Fang überlassen (Befund 3, Durchsicht
        # b91a56e).
        if not profile_existed_before and profile_path.is_file():
            profile_path.unlink()
        raise
    if cefr_level is not None:
        # (Befund leicht c, Durchsicht ee34796): Paare und Bedeutungen sind Zahlen, die
        # größer als das Kontingent aussehen — die Deckung (wie viele der angefragten
        # Grundformen überhaupt einen Wörterbucheintrag hatten) stand bisher nirgends.
        write_line(
            f"Vorbelegung Niveau {cefr_level.value.upper()}: "
            f"{_format_count(result.covered_lemmas)} von {_format_count(result.total_lemmas)} "
            f"Grundformen hatten einen Wörterbucheintrag, "
            f"{_format_count(result.lemma_pos_pairs)} (Grundform, Wortart)-Paare, "
            f"{_format_count(result.senses)} Bedeutungen als bekannt gebucht."
        )
        # (Befund leicht d, Durchsicht ee34796): Kein Rückweg — ein zweiter Aufruf hängt an
        # (technik.md, Docstring `write_vocabulary_preset`, „Für den einmaligen Aufruf …
        # gedacht"), einzige Korrektur heute ist `profil.sqlite3` von Hand zu löschen.
        # Bewusst offen (siehe Auftragstext); dieser Hinweis macht die Einmaligkeit
        # wenigstens sichtbar.
        write_line("Die Vorbelegung ist einmalig und lässt sich nicht zurücknehmen.")


def _confirm_dictionary_fetch(
    dictionary_path: Path, read_line: ReadLine, write_line: WriteLine
) -> bool:
    """Fragt vor dem Erstbezug des Wörterbuchs nach Bestätigung und zeigt dabei Herkunft
    und Lizenz.

    Vorgabe bei bloßem Enter ist hier **Zustimmung**, anders als bei
    `_confirm_new_profile`: Das Wörterbuch ist eine jederzeit wiederbeschaffbare
    Fremddatei von rund 20 MB, kein unwiederbringlicher Lernstand — der Grund für die
    Rückfrage ist nicht der Schutz vor einem Fehlgriff, sondern der Hinweis auf Herkunft
    und Lizenz (`dictionary.SOURCE_NOTICE`, technik.md §2, „Warum nicht mitgeliefert")
    und darauf, dass gleich ein Netzzugriff beginnt.
    """
    write_line(f"Wörterbuch nicht gefunden: {dictionary_path}")
    write_line(dictionary.SOURCE_NOTICE)
    answer = read_line("Jetzt beziehen? [J/n] ").strip().lower()
    return answer in ("", "j", "ja")


def _format_word_count(count: int | None) -> str:
    """Wortumfang für die Kapitelliste: deutsches Tausendertrennzeichen (`78.774`),
    unbekannter Umfang sichtbar als `unbekannt` statt als Zahl — die stille Falschaussage
    `0` wäre genau der stille Fehlschlag, den Regel 13 verbietet (technik.md §8, „Was die
    Kapitelliste zusätzlich zeigt")."""
    if count is None:
        return "unbekannt"
    return f"{count:,}".replace(",", ".")


def _indent_title(chapter: epub.ChapterReference) -> str:
    """Titel eingerückt nach Gliederungsebene (technik.md §8, „Was die Kapitelliste
    zusätzlich zeigt"): zwei Leerzeichen je Ebene, fest und ohne
    Konfigurationsschalter (Regel 14) — eine flache, durchlaufend nummerierte Liste bleibt
    es trotzdem, kein Aufklappbaum. Oberste Ebene (0) bleibt unverändert."""
    return f"{'  ' * chapter.level}{chapter.title}"


def _choose_chapter(
    epub_path: Path, structure: epub.BookStructure, read_line: ReadLine, write_line: WriteLine
) -> int:
    """Zeigt die Kapitelliste mit Wortumfang je Kapitel und fragt so lange nach, bis eine
    darin vorhandene, nicht übersprungene Kapitelnummer eingegeben wird. Titel vor Zahl,
    wie technik.md §8, „Was die Kapitelliste zusätzlich zeigt" es nennt („Book 1 DUNE —
    78.800 Wörter"): Nummer und Wortumfang stehen rechtsbündig in eigenen Spalten, der
    Titel linksbündig auf die Länge des längsten (eingerückten) Titels aufgefüllt
    dazwischen — erst die aufgefüllte Nummer hält beide Spalten auch ab Kapitel 10
    untereinander vergleichbar, ohne einen Titel zu kürzen (Regel 14: keine
    Terminalbreitenerkennung, keine Tabellenbibliothek). „unbekannt" bleibt dabei in
    derselben Spalte sichtbar wie eine Zahl. Die Einrückung (`_indent_title`) zeigt die
    Gliederungsebene der Navigation an, ohne die Nummerierung zu ändern — die Nummer
    zählt unverändert weiter in der Reihenfolge der `spine`, Elternzeilen bleiben wählbar.

    `pipeline.list_chapters` (bauplan-phase2.md AP 4) liefert dazu je Kapitel dessen
    `skip_reason`: Ein Kapitel ohne Fließtext (Vorspann, Impressum, Bildband) erscheint mit
    seinem Grund in einer eigenen Zeile darunter und lässt sich nicht wählen — der Nutzer
    sieht den Grund so schon vor der Wahl, statt nach dem Laden des Sprachmodells eine
    Fehlermeldung zu bekommen (technik.md §8, „Entschieden 16.09.2026: der Sweep über alle
    Kapitel eines Buchs"). `structure` bleibt trotzdem Parameter: Nur sie trägt `level` für
    die Einrückung, das `ChapterListing` nicht führt (Ablaufwert ohne diese Angabe,
    `pipeline.py`)."""
    write_line(f"„{structure.book.title}“ von {structure.book.author}")
    listings = {listing.number: listing for listing in pipeline.list_chapters(epub_path)}
    formatted_counts = {
        chapter.number: _format_word_count(listings[chapter.number].word_count)
        for chapter in structure.chapters
    }
    indented_titles = {chapter.number: _indent_title(chapter) for chapter in structure.chapters}
    number_header, title_header, count_header = "Nr.", "Kapitel", "Wörter"
    number_width = max(
        [len(number_header)] + [len(f"{chapter.number}.") for chapter in structure.chapters]
    )
    title_width = max([len(title_header)] + [len(value) for value in indented_titles.values()])
    count_width = max([len(count_header)] + [len(value) for value in formatted_counts.values()])
    write_line(
        f"  {number_header:>{number_width}}  {title_header:<{title_width}}  "
        f"{count_header:>{count_width}}"
    )
    for chapter in structure.chapters:
        number_column = f"{chapter.number}."
        title_column = indented_titles[chapter.number]
        count_column = formatted_counts[chapter.number]
        write_line(
            f"  {number_column:>{number_width}}  {title_column:<{title_width}}  "
            f"{count_column:>{count_width}}"
        )
        skip_reason = listings[chapter.number].skip_reason
        if skip_reason is not None:
            write_line(f"      → übersprungen, kein Fließtext: {skip_reason}")
    skipped_numbers = {
        number for number, listing in listings.items() if listing.skip_reason is not None
    }
    while True:
        answer = read_line("Kapitel wählen: ").strip()
        try:
            number = int(answer)
        except ValueError:
            write_line("Bitte eine Zahl eingeben.")
            continue
        if number in skipped_numbers:
            write_line("Dieses Kapitel enthält keinen Fließtext und lässt sich nicht wählen.")
            continue
        if any(chapter.number == number for chapter in structure.chapters):
            return number
        write_line("Diese Kapitelnummer gibt es nicht.")


_CHAPTER_RANGE_PATTERN = re.compile(r"(\d+)-(\d+)")


def _resolve_chapter_range(text: str, listings: Sequence[pipeline.ChapterListing]) -> list[int]:
    """Zerlegt `--chapters` (bauplan-phase2.md AP 5, E6 (a)) in die Liste der darin
    liegenden, im Buch tatsächlich vorhandenen Kapitelnummern, in Buchreihenfolge:
    `all` nimmt jede Nummer aus `listings`, `N-M` nur die darin liegenden — ein Kapitel
    ohne Fließtext bleibt in der zurückgegebenen Liste, dessen Ausschluss aus der
    Verarbeitung und Meldung ist Sache von `_split_skipped_chapters`.

    Ungültige Eingaben (falsches Format, erste Zahl größer als zweite, kein einziges
    vorhandenes Kapitel im Bereich) brechen mit `ValueError` sichtbar ab (Regel 13,
    dokumentation.md §4) statt eine geratene Auswahl zu treffen."""
    if text == "all":
        return [listing.number for listing in listings]
    match = _CHAPTER_RANGE_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"Ungültiger Kapitelbereich „{text}“ — erwartet wird z. B. 3-7 oder all.")
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise ValueError(
            f"Ungültiger Kapitelbereich „{text}“ — die erste Zahl darf nicht größer als "
            "die zweite sein."
        )
    numbers = [listing.number for listing in listings if start <= listing.number <= end]
    if not numbers:
        raise ValueError(f"Kapitelbereich „{text}“ enthält kein vorhandenes Kapitel dieses Buchs.")
    return numbers


@dataclass(frozen=True)
class _SkippedChapter:
    """Ein bei `--chapters` übersprungenes Kapitel ohne Fließtext — für die Bilanz am
    Ende (`_write_chapter_range_summary`), Ablaufwert wie `pipeline.ChapterListing`,
    deshalb hier und nicht in `entities`."""

    number: int
    skip_reason: str


def _split_skipped_chapters(
    numbers: Sequence[int], listings: Sequence[pipeline.ChapterListing], *, write_line: WriteLine
) -> tuple[list[int], list[_SkippedChapter]]:
    """Trennt die Nummern aus `_resolve_chapter_range` in verarbeitbare Kapitel und
    übersprungene (`pipeline.ChapterListing.skip_reason` gesetzt) — meldet jedes
    übersprungene sofort, nicht erst in der Bilanz (Regel 13, dokumentation.md §4): Bei
    einem Sweep über viele Kapitel soll nicht erst am Ende sichtbar werden, welche
    fehlten."""
    skip_reasons = {listing.number: listing.skip_reason for listing in listings}
    to_process: list[int] = []
    skipped: list[_SkippedChapter] = []
    for number in numbers:
        skip_reason = skip_reasons.get(number)
        if skip_reason is not None:
            write_line(f"Kapitel {number}: übersprungen, kein Fließtext — {skip_reason}.")
            skipped.append(_SkippedChapter(number=number, skip_reason=skip_reason))
        else:
            to_process.append(number)
    return to_process, skipped


@dataclass(frozen=True)
class _ChapterRunOutcome:
    """Das Ergebnis eines einzelnen Kapiteldurchlaufs innerhalb von `--chapters` — für
    die Bilanz am Ende (`_write_chapter_range_summary`), Ablaufwert wie `ChapterListing`,
    deshalb hier und nicht in `entities`."""

    chapter_number: int
    word_count: int
    expression_count: int
    card_count: int


def _write_chapter_range_summary(
    outcomes: Sequence[_ChapterRunOutcome],
    skipped: Sequence[_SkippedChapter],
    write_line: WriteLine,
) -> None:
    """Bilanz am Ende eines `--chapters`-Laufs (bauplan-phase2.md AP 5): je verarbeitetem
    Kapitel eine Zeile mit Wort-, Wendungs- und Kartenzahl, je übersprungenem eine mit
    seinem Grund, zuletzt eine Gesamtzeile."""
    write_line("Bilanz über den Kapitelbereich:")
    for outcome in outcomes:
        write_line(
            f"  Kapitel {outcome.chapter_number}: {_format_count(outcome.word_count)} Wörter, "
            f"{_format_count(outcome.expression_count)} Wendungen, "
            f"{_format_count(outcome.card_count)} Karten gelernt."
        )
    for skip in skipped:
        write_line(f"  Kapitel {skip.number}: übersprungen — {skip.skip_reason}.")
    total_cards = sum(outcome.card_count for outcome in outcomes)
    write_line(
        f"Insgesamt {_format_count(len(outcomes))} Kapitel verarbeitet, "
        f"{_format_count(len(skipped))} übersprungen, {_format_count(total_cards)} Karten gelernt."
    )


def _run_chapter_with_progress(
    *,
    epub_path: Path,
    chapter_number: int,
    dictionary_path: Path,
    profile_path: Path,
    nlp: Language,
    cache_dir: Path,
    write_line: WriteLine,
) -> pipeline.ChapterVocabulary:
    """Ruft `pipeline.run_chapter` mit einer Fortschrittsanzeige auf (Auftragstext vom
    02.09.2026, Bauschritt 1/2 der Konsolenausgabe): Ohne sie stand auf dem Bildschirm die
    ganze Zeit noch „Lade Sprachmodell …", während `run_chapter` tatsächlich 22 bis 29 s
    stumm das ganze Buch durch spaCy schickte (`extraction.book_proper_noun_ratios`,
    technik.md §5) — der stille Fehlschlag, den Regel 13 (dokumentation.md §4) verbietet.
    Der Kern gibt selbst keinen deutschen Text aus (technik.md §7); die Zuordnung
    Etappe → Satz macht allein diese Funktion.

    Die beiden zählenden Etappen (`READING_BOOK`, `ANALYZING_BOOK`) schreiben sich über
    `cli.display.safe_print_progress` per Wagenrücklauf fort, wie `_resolve_with_progress`
    es für die Bedeutungsauflösung schon tut. Vor jedem Etappenwechsel steht
    `finish_progress_line()`, sonst blieben Reste der vorigen, längeren Zeile stehen — der
    Wechsel wird an `progress.stage` erkannt, nicht an `done`, weil ein Buch mit nur einem
    Kapitel sonst keinen verlässlichen Umschlagpunkt hätte. Die beiden Etappen ohne Zähler
    (`EXTRACTING_VOCABULARY`, `LOOKING_UP_DICTIONARY`, `done == total == 0`) bekommen je
    eine einmalige Zeile, keine sich fortschreibende.

    Die Zuordnung läuft über ein `match` mit `assert_never` statt über eine Tabelle
    (Befund 8, Durchsicht cf09744): Eine fünfte `ChapterStage` ohne Satz fiel vorher erst
    zur Laufzeit auf — mit `KeyError` und englischem Traceback, nach den 22 bis 29 s
    Arbeit. So prüft `mypy` die Vollständigkeit, bevor der Lauf beginnt.

    Der Nenner der Analyse-Etappe ist kleiner als der der Lese-Etappe, sobald ein Kapitel
    ohne Fließtext übersprungen wurde (`pipeline.run_chapter`, Vorspann und Impressum) —
    bei `tools/sherlock.epub` 13 gegen 14. Die Zeile nennt ihn deshalb ausdrücklich als
    Kapitel **mit Text** (Befund 6, Durchsicht cf09744): Eine Zahl, die zwischen zwei
    aufeinanderfolgenden Zeilen unerklärt schrumpft, liest sich wie ein Fehler.

    `cache_dir` wird unverändert an `pipeline.run_chapter` weitergereicht (technik.md §5,
    „Entschieden 15.09.2026: Zwischenspeicher für den buchweiten Eigennamenanteil") — trifft
    dessen Zwischenspeicher, bleiben `READING_BOOK`/`ANALYZING_BOOK` ganz aus, weil es dann
    nichts mehr zu melden gibt."""
    progress_open = False
    last_stage: pipeline.ChapterStage | None = None

    def _on_progress(progress: pipeline.ChapterProgress) -> None:
        nonlocal progress_open, last_stage
        if progress.stage != last_stage and progress_open:
            finish_progress_line()
            progress_open = False
        last_stage = progress.stage
        match progress.stage:
            case pipeline.ChapterStage.READING_BOOK:
                safe_print_progress(
                    f"Buch wird gelesen: {progress.done} von {progress.total} Kapiteln."
                )
                progress_open = True
            case pipeline.ChapterStage.ANALYZING_BOOK:
                safe_print_progress(
                    f"Wortschatz des Buchs wird analysiert: {progress.done} von "
                    f"{progress.total} Kapiteln mit Text …"
                )
                progress_open = True
            case pipeline.ChapterStage.EXTRACTING_VOCABULARY:
                write_line("Wortschatz des Kapitels wird ermittelt …")
            case pipeline.ChapterStage.LOOKING_UP_DICTIONARY:
                write_line("Bedeutungen werden im Wörterbuch nachgeschlagen …")
            case _:
                assert_never(progress.stage)

    try:
        return pipeline.run_chapter(
            epub_path=epub_path,
            chapter_number=chapter_number,
            dictionary_path=dictionary_path,
            profile_path=profile_path,
            nlp=nlp,
            cache_dir=cache_dir,
            on_progress=_on_progress,
        )
    finally:
        if progress_open:
            finish_progress_line()


# (Befund 7, Durchsicht e537273): Ankündigung und Zählzeilen-Vorlage aus einer geteilten
# Quelle statt zweier von Hand gepflegter Literale — nur so lässt sich die Zusicherung
# unten (`safe_print_progress` darf den Text nur wachsen lassen, nie kürzen, siehe dessen
# Docstring) gegen den tatsächlichen Text führen, statt zwei Kopien nebeneinanderzustellen,
# die stillschweigend auseinanderlaufen könnten.
_RESOLVE_ANNOUNCEMENT = "Bedeutungen werden aufgelöst …"


def _resolve_progress_text(examined: int, total: int, kept: int, limit: int) -> str:
    # (Befund leicht 4, Durchsicht T16/T17): total ist die Obergrenze der Einträge
    # (Vorfilter aus resolve_triage_entries, Schritt 1, hat schon abgezogen), nicht die
    # Zahl der tatsächlich geprüften — der Lauf endet spätestens bei `limit` Treffern,
    # meist weit vor total. „möglichen" macht das im Nenner sichtbar.
    return (
        f"Bedeutungen werden aufgelöst: {examined} von {total} möglichen geprüft, "
        f"{kept} von {limit} behalten."
    )


def _resolve_with_progress(
    *,
    con: sqlite3.Connection,
    entries: Sequence[pipeline.VocabularyEntry],
    limit: int,
    url: str,
    get_model_name: Callable[[], str],
    order: str,
) -> pipeline.TriageResolution:
    """Ruft `pipeline.resolve_triage_entries` mit einer Fortschrittsanzeige auf
    (Auftragstext vom 25.08.2026, Abschnitt 3): Ohne Ausgabe wäre ein Lauf bei `[triage]
    order = "frequency"` und reifem Profil minutenlang stumm — der stille Fehlschlag, den
    Regel 13 (dokumentation.md §4) verbietet. Der Kern gibt selbst nichts aus (technik.md
    §7); die Zeile schreibt sich über `cli.display.safe_print_progress` per Wagenrücklauf
    fort und wird nur dann abgeschlossen (`finish_progress_line`), wenn überhaupt etwas zu
    prüfen war — ein Decksel ohne Einträge (etwa „Wendungen" in einem Kapitel ohne
    Wendungen) soll keine leere Zeile hinterlassen.
    Der Abschluss läuft in `finally` (Befund leicht 1, Durchsicht T16/T17): Bricht der
    Modellserver mitten im Kapitel ab, klebte die Fehlermeldung sonst an der noch
    offenen Statuszeile, statt in einer eigenen Zeile zu erscheinen.

    Die erste Zeile steht **vor** dem ersten Modellaufruf, nicht erst nach dem ersten
    aufgelösten Eintrag (zweite Nutzermeldung vom 02.09.2026): Genau davor liegt beim
    ersten Block der längste Halt, weil der Modellserver das Modell erst in den
    Grafikspeicher lädt — auf dem Bildschirm stand dort einige Sekunden nichts als die
    Deckelüberschrift. Derselbe stille Halt wie vor der Triage (technik.md §13,
    „Konsolenausgabe"), nur eine Ebene tiefer. Der Wagenrücklauf überschreibt sie mit der
    ersten Zählung; sie ist kürzer als jede Zählzeile und hinterlässt deshalb keinen
    Rest (siehe `display.safe_print_progress`, „nur wachsen lassen, nie kürzen") — geprüft
    in `tests/test_cli_main.py`,
    `test_resolve_progress_announcement_is_never_longer_than_the_shortest_count_line`
    (Befund 7, Durchsicht e537273): Vor dieser Behebung stand diese Zusicherung nirgends,
    nur die Reihenfolge (Ankündigung vor erster Zählzeile) war geprüft."""
    started = bool(entries)
    if started:
        safe_print_progress(_RESOLVE_ANNOUNCEMENT)

    def _on_progress(examined: int, total: int, kept: int, limit_: int) -> None:
        # (Befund 7, Durchsicht e537273): Kein `nonlocal started; started = True` mehr —
        # tot seit `started = bool(entries)` oben: `on_progress` läuft nur innerhalb der
        # Schleife über `ordered` in `pipeline.resolve_triage_entries`, und die ist leer,
        # sobald `entries` es ist. `started` ist an dieser Stelle also immer schon `True`.
        safe_print_progress(_resolve_progress_text(examined, total, kept, limit_))

    try:
        resolution = pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=limit,
            url=url,
            get_model_name=get_model_name,
            order=order,
            on_progress=_on_progress,
        )
    finally:
        if started:
            finish_progress_line()
    return resolution


class _PrefetchCancelled(Exception):
    """(Befund 4, Durchsicht 1cfb1e4): Signalisiert `_resolve_silently` selbst den
    eigenen Abbruch — geworfen aus `_stop_if_cancelled` unten, sobald das übergebene
    `cancelled`-Ereignis gesetzt ist. Erreicht `cli.interaction._BlockPrefetch._run`, das
    jede Ausnahme gleich behandelt und festhält; weil ein abbestellter Vorladeblock nie
    abgewartet wird (`_BlockPrefetch.join` läuft für ihn nicht mehr), erreicht diese
    Ausnahme nie den Nutzer. Kein Fehlschlag im Sinn von Regel 13 (dokumentation.md §4) —
    nur der reguläre Weg, einen Hintergrundlauf zu beenden, dessen Ergebnis niemand mehr
    ansieht."""


def _resolve_silently(
    *,
    profile_path: Path,
    entries: Sequence[pipeline.VocabularyEntry],
    limit: int,
    url: str,
    get_model_name: Callable[[], str],
    order: str,
    cancelled: threading.Event,
) -> pipeline.TriageResolution:
    """Löst einen **vorgeladenen** Block auf (technik.md §12, „Vorladen: der nächste Block
    entsteht, während der Nutzer entscheidet") — der Rückruf, den `interaction.
    run_triage_blocks` als `resolve_silent_block` im Hintergrundfaden aufruft, während der
    Hauptfaden den aktuellen Block noch durchentscheidet. Drei Unterschiede zu
    `_resolve_with_progress` oben, aus den bindenden Festlegungen in technik.md §12:

    - **Eigene Profilverbindung** (Festlegung 1): `libreverbum.profile.open_profile` öffnet
      mit `sqlite3.connect(path)`, **ohne** `check_same_thread=False` — eine Verbindung
      gehört also dem Faden, der sie erzeugt hat, nicht der Datei. Der Hauptfaden schreibt
      zur selben Zeit die Triage-Entscheidungen des laufenden Blocks über seine eigene
      Verbindung (`_run`s `con`) auf dieselbe Datei; eine geteilte Verbindung wäre hier kein
      Geschwindigkeitsproblem, sondern der in `sqlite3.ProgrammingError` sichtbare Fehler
      "SQLite objects created in a thread can only be used in that same thread". Geöffnet
      und wieder geschlossen wird deshalb **hier**, im Hintergrundfaden — `run_triage_blocks`
      bekommt nichts davon zu sehen, nur das fertige Ergebnis oder die durchgereichte
      Ausnahme (`cli.interaction._BlockPrefetch.join`). Geprüft in
      `tests/test_cli_main.py`, `test_prefetch_resolves_the_background_block_with_a_
      connection_of_its_own` (Befund 2, Durchsicht 1cfb1e4) — direkt an der Verbindung,
      die im Hintergrundfaden tatsächlich benutzt wird, nicht nur daran, dass diese
      Funktion existiert und `profile.open_profile` aufruft.
    - **Kein Fortschritt** (Festlegung 3): Die sich fortschreibende Statuszeile aus
      `_resolve_with_progress` (`safe_print_progress`, per Wagenrücklauf) schriebe aus
      diesem Faden mitten in die Triage-Anzeige, über der der Nutzer gerade entscheidet —
      sie gehört allein dem ersten Block, den der Nutzer tatsächlich abwartet.
      `on_progress` unten dient deshalb einzig der Abbestellung, nicht der Anzeige.
    - **Abbestellbar** (Befund 4, Durchsicht 1cfb1e4, Festlegung 4): `on_progress`
      (`_stop_if_cancelled`) läuft nach **jedem** von `pipeline.resolve_triage_entries`
      aufgelösten Eintrag und wirft `_PrefetchCancelled`, sobald `cancelled` gesetzt ist —
      `cli.interaction._BlockPrefetch.cancel` setzt es, sobald feststeht, dass niemand das
      Ergebnis mehr ansieht (nach `q` oder nach „nein"). Ohne diese Prüfung lief ein bereits
      gestarteter Vorladeblock einfach weiter und verbrauchte dabei Modellaufrufe für ein
      Ergebnis, das verworfen wird (gemessen: ein erster Wendungsblock brauchte dadurch
      7,39 s statt 3,85 s). Weder `_resolve_silently` noch `pipeline.resolve_triage_entries`
      müssen dafür wissen, was `_BlockPrefetch` ist — nur, dass ihnen ein `threading.Event`
      übergeben wird.

    Ein Fehlschlag (etwa der Modellserver, der mitten im Vorladen wegbricht) läuft
    unverändert durch (Regel 13, dokumentation.md §4 — kein `except`, das nur protokolliert
    und weiterläuft): `_BlockPrefetch` hält ihn im Hintergrundfaden fest und wirft ihn im
    Hauptfaden erneut, sobald `run_triage_blocks` auf den Block wartet (Festlegung 2). Eine
    Abbestellung ist davon ausdrücklich **kein** Fall (siehe `_PrefetchCancelled` oben)."""
    con = profile.open_profile(profile_path)

    def _stop_if_cancelled(_examined: int, _total: int, _kept: int, _limit: int) -> None:
        if cancelled.is_set():
            raise _PrefetchCancelled()

    try:
        return pipeline.resolve_triage_entries(
            con=con,
            entries=entries,
            limit=limit,
            url=url,
            get_model_name=get_model_name,
            order=order,
            on_progress=_stop_if_cancelled,
        )
    finally:
        con.close()


def _export_partial_run(
    *,
    con: sqlite3.Connection,
    partial_cards: list[Card],
    output_dir: Path,
    book_title: str,
    chapter_number: int,
    write_line: WriteLine,
) -> None:
    """Schreibt die bereits entschiedenen Karten eines abgebrochenen Laufs als Teilexport
    (technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf exportiert, was er
    hat") — aufzurufen aus dem `except`-Zweig in `_run` unten, **bevor** die ursprüngliche
    Ausnahme weiterläuft. Tut nichts bei einer leeren Liste: Ist noch keine Karte
    entschieden, gibt es nichts zu exportieren, nur die Fehlermeldung, die `main` gleich
    danach ausgibt.

    `export.write_exports` bekommt `partial=True` — der Dateiname trägt den Teilstand
    (`_teilexport`), der Deckname bleibt unverändert (`app/export.py`, „Liefert"). Scheitert
    der Teilexport seinerseits (etwa ein ungültiger `output_dir`), wirft diese Funktion die
    entstehende Ausnahme unverändert weiter — sie fängt selbst nichts ab. **Der Aufrufer**
    in `_run` fängt diesen zweiten Fehlschlag gesondert ab und meldet ihn zusätzlich, bevor
    die ursprüngliche Ausnahme unverändert weiterläuft: Ohne diesen zweiten Fang ersetzte
    die neue Ausnahme die ursprüngliche vollständig, und deren Ursache verschwände aus der
    Meldung (Befund 1, Durchsicht b91a56e)."""
    if not partial_cards:
        return
    paths = export.write_exports(
        con,
        output_dir,
        partial_cards,
        book_title=book_title,
        chapter_number=chapter_number,
        partial=True,
    )
    count = len(partial_cards)
    karten = (
        "einer bereits entschiedenen Karte"
        if count == 1
        else (f"{_format_count(count)} bereits entschiedenen Karten")
    )
    write_line(f"Abbruch — Teilexport aus {karten} geschrieben.")
    write_line(f"Anki-Deck (Teilexport): {paths.anki_path}")
    write_line(f"Druckseite (Teilexport): {paths.printout_path}")


def _run_one_chapter(
    *,
    con: sqlite3.Connection,
    epub_path: Path,
    chapter_number: int,
    dictionary_path: Path,
    profile_path: Path,
    nlp: Language,
    cache_dir: Path,
    card_direction: CardDirection,
    get_model_name: Callable[[], str],
    model_url: str,
    triage_order: str,
    output_dir: Path,
    style: display.Style,
    read_line: ReadLine,
    write_line: WriteLine,
) -> _ChapterRunOutcome:
    """Ein vollständiger Kapiteldurchlauf ab dem bereits geladenen Sprachmodell und der
    bereits offenen Profilverbindung: Wortschatz ermitteln, Triage über die Tastatur
    (Wörter, dann Wendungen), Export nach Anki und als Druckseite.

    Herausgelöst aus `_run` (bauplan-phase2.md AP 5), damit `--chapters` diesen Rumpf
    mehrfach durchläuft, ohne das Sprachmodell erneut zu laden oder je Kapitel eine neue
    Profilverbindung zu öffnen — `con` und `nlp` gehören dem Aufrufer und werden hier nur
    benutzt, nie geschlossen. Genau daran hängt Abnahmekriterium 2 (konzept.md,
    bauplan-phase2.md, Abschnitt 9): Nur eine **fortbestehende** Profilverbindung auf
    derselben Datei sieht die „kenne ich"-Buchungen eines früheren Kapitels, bevor sie das
    nächste nach ihnen filtert.

    Scheitert die Triage mitten im Lauf, exportiert diese Funktion die bis dahin
    entschiedenen Karten als Teilexport dieses einen Kapitels und reicht die Ausnahme
    danach unverändert weiter (technik.md §12, „Entschieden 15.09.2026: ein abgebrochener
    Lauf exportiert, was er hat") — `_run` fängt sie nicht ab, der ganze `--chapters`-Lauf
    bricht sichtbar ab (Regel 13, dokumentation.md §4: kein Fehlschlag in einem Kapitel
    verschwindet still in einer Bilanz, die ihn nie erwähnt)."""
    result = _run_chapter_with_progress(
        epub_path=epub_path,
        chapter_number=chapter_number,
        dictionary_path=dictionary_path,
        profile_path=profile_path,
        nlp=nlp,
        cache_dir=cache_dir,
        write_line=write_line,
    )
    write_line(
        f"Kapitel {result.chapter.number}: {_format_count(len(result.entries))} Wörter, "
        f"{_format_count(len(result.expressions))} Wendungen."
    )
    if result.notice:
        write_line(result.notice)

    interaction.ensure_chapter_row(
        con, result.chapter.book, result.chapter.number, result.chapter.title
    )

    # (Befund schwer 1, zweite T16-Durchsicht): Die Bedeutung wird vor der Triage
    # aufgelöst (`pipeline.resolve_triage_entries`, je Block einmal) — Wörter und
    # Wendungen bleiben dabei getrennte Blockschleifen mit eigener Blockgröße (`cli.
    # interaction`, „Festlegung: getrennte Decksel"). `run_triage_blocks` (Bauschritt
    # 2/4, blockweise Triage) macht aus jedem `resolve_triage_entries`-Aufruf über
    # `resolution.remaining` so lange den nächsten Block, bis der Nutzer aufhört —
    # jeden Folgeblock dabei bereits im Hintergrund vorgeladen (Bauschritt 3/4,
    # technik.md §12, „Vorladen …"): `resolve_visible_block` (mit Fortschrittsanzeige)
    # nur für den ersten Block, `resolve_silent_block` (eigene Profilverbindung, keine
    # Ausgabe) für jeden vorgeladenen — siehe `_resolve_with_progress`/`_resolve_silently`
    # oben.
    # (Befund mittel, Durchsicht T16): profile.record_card schreibt die Anki-GUID
    # jeder Karte ins Profil (Regel 6) und braucht dafür dieselbe, noch offene
    # Profilverbindung wie die Triage.

    # technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf exportiert, was
    # er hat": `partial_cards` sammelt die Karten jedes abgeschlossenen Blocks aus
    # beiden Deckeln — Wörter und Wendungen tragen bewusst in dieselbe Liste ein, damit
    # ein Fehlschlag im Wendungsteil die Wörterkarten mitnimmt. Scheitert einer der
    # beiden Aufrufe, exportiert der `except`-Zweig, was bis dahin entschieden ist, und
    # wirft die Ausnahme danach **unverändert** weiter (`raise` ohne Argument) — kein
    # `except`, das protokolliert und weiterläuft (Regel 13, dokumentation.md §4).
    # Gefangen wird `Exception`, nicht `BaseException`: Ein `KeyboardInterrupt` ist der
    # Nutzer, der sofort heraus will, kein Fehlschlag, der einen Teilexport verdient.
    partial_cards: list[Card] = []
    try:
        for line in display.cover("Wörter", style):
            write_line(line)
        word_cards = interaction.run_triage_blocks(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            entries=result.entries,
            resolve_visible_block=lambda block: _resolve_with_progress(
                con=con,
                entries=block,
                limit=interaction.WORD_BLOCK_SIZE,
                url=model_url,
                get_model_name=get_model_name,
                order=triage_order,
            ),
            resolve_silent_block=lambda block, cancelled: _resolve_silently(
                profile_path=profile_path,
                entries=block,
                limit=interaction.WORD_BLOCK_SIZE,
                url=model_url,
                get_model_name=get_model_name,
                order=triage_order,
                cancelled=cancelled,
            ),
            label="Wörter",
            card_direction=card_direction,
            style=style,
            read_line=read_line,
            write_line=write_line,
            partial_cards=partial_cards,
        )
        for line in display.cover("Wendungen", style):
            write_line(line)
        expression_cards = interaction.run_triage_blocks(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            entries=result.expressions,
            resolve_visible_block=lambda block: _resolve_with_progress(
                con=con,
                entries=block,
                limit=interaction.EXPRESSION_BLOCK_SIZE,
                url=model_url,
                get_model_name=get_model_name,
                order=triage_order,
            ),
            resolve_silent_block=lambda block, cancelled: _resolve_silently(
                profile_path=profile_path,
                entries=block,
                limit=interaction.EXPRESSION_BLOCK_SIZE,
                url=model_url,
                get_model_name=get_model_name,
                order=triage_order,
                cancelled=cancelled,
            ),
            label="Wendungen",
            card_direction=card_direction,
            # (Zweite Nutzermeldung vom 02.09.2026): Der Wendungs-Deckel zählt dort
            # weiter, wo der Wörter-Deckel aufgehört hat — die Zahl in der Trennlinie
            # ist damit das, was am Ende tatsächlich ins Anki-Deck und auf die
            # Druckseite geht, nicht der Stand eines einzelnen Deckels.
            chosen_before=len(word_cards),
            style=style,
            read_line=read_line,
            write_line=write_line,
            partial_cards=partial_cards,
        )
    except Exception:
        # REGEL (dokumentation.md §4 Regel 13, „Kein except, das nur protokolliert und
        # weiterläuft"): Dieser Fang schreibt den Teilexport und läuft danach mit
        # `raise` unverändert zur ursprünglichen Ausnahme weiter — er verschluckt sie
        # nicht, sondern hängt ihr eine Nebenwirkung voran. Scheitert `_export_partial_run`
        # selbst (etwa ein ungültiger `output_dir`), ersetzte diese zweite Ausnahme ohne
        # den inneren Fang unten die erste vollständig: `main` finge nur noch die zweite,
        # und die eigentliche Ursache erschiene in der Meldung nirgends (Befund 1,
        # Durchsicht b91a56e). Der innere Fang meldet den zweiten Fehlschlag deshalb
        # zusätzlich, statt ihn durchzureichen — das äußere `raise` bricht den Lauf davon
        # unabhängig weiterhin ab, nie mit Exit-Code 0.
        try:
            _export_partial_run(
                con=con,
                partial_cards=partial_cards,
                output_dir=output_dir,
                book_title=result.chapter.book.title,
                chapter_number=result.chapter.number,
                write_line=write_line,
            )
        except Exception as export_error:
            write_line(f"Teilexport zusätzlich fehlgeschlagen: {export_error}")
        raise

    cards = word_cards + expression_cards
    if not cards:
        write_line("Keine Wörter zum Lernen ausgewählt — kein Export.")
        return _ChapterRunOutcome(
            chapter_number=result.chapter.number,
            word_count=len(result.entries),
            expression_count=len(result.expressions),
            card_count=0,
        )

    paths = export.write_exports(
        con,
        output_dir,
        cards,
        book_title=result.chapter.book.title,
        chapter_number=result.chapter.number,
    )
    write_line(f"Anki-Deck: {paths.anki_path}")
    write_line(f"Druckseite: {paths.printout_path}")
    return _ChapterRunOutcome(
        chapter_number=result.chapter.number,
        word_count=len(result.entries),
        expression_count=len(result.expressions),
        card_count=len(cards),
    )


def _run(
    args: argparse.Namespace, *, read_line: ReadLine, write_line: WriteLine, style: display.Style
) -> int:
    if args.chapter is not None and args.chapters is not None:
        # Regel 13 (dokumentation.md §4): Eine der beiden Optionen still zu bevorzugen
        # wäre ein stiller Fehlschlag anderer Art — der Nutzer bekäme ein Kapitel oder
        # einen Bereich verarbeitet, ohne zu wissen, welche der beiden Angaben galt.
        raise ValueError(
            "--chapter und --chapters schließen sich aus — nur eine der beiden Optionen angeben."
        )
    data_dir = args.data_dir or config.default_data_dir()
    # Jeder Lauf nennt sein Datenverzeichnis: Wo Profil, Wörterbuch und config.toml
    # liegen, soll niemand suchen müssen (technik.md §9, „Wohin die Dateien gehören").
    write_line(f"Datenverzeichnis: {data_dir}")
    cfg, just_created = config.load_config(data_dir)
    if just_created:
        write_line(f"config.toml wurde neu angelegt: {data_dir / 'config.toml'}")
        write_line("Werte prüfen (insbesondere model.url) und den Befehl erneut ausführen.")
        return 0

    # Das Wörterbuch steht vor jeder anderen Rückfrage (etwa der Profilbestätigung
    # unten): Ein Lauf, der ohne es nicht weiterkommt, soll nicht erst nach einer
    # Bestätigung scheitern.
    if not cfg.dictionary_path.is_file():
        # REGEL (dokumentation.md §4 Regel 13): Der Erstbezug läuft über den Kern selbst
        # (`dictionary.fetch_dictionary`) statt über einen Verweis auf ein Messskript in
        # `tools/`. Lehnt der Nutzer ab oder schlägt der Bezug fehl, bricht der Lauf
        # sichtbar ab — `fetch_dictionary` räumt eine unvollständige Datei selbst weg und
        # wirft eine deutsche Meldung, die `main` unten fängt und meldet.
        if not _confirm_dictionary_fetch(cfg.dictionary_path, read_line, write_line):
            write_line("Abgebrochen — kein Wörterbuch bezogen.")
            return 1
        write_line("Wörterbuch wird bezogen, rund 20 MB — das dauert einen Moment …")
        dictionary.fetch_dictionary(cfg.dictionary_path)
        write_line(f"Wörterbuch bezogen: {cfg.dictionary_path}")
    else:
        # Nur der Index, nicht die ganze Bezugsprüfung: `fetch_dictionary` prüft eine
        # vorhandene Datei zusätzlich auf mindestens 100.000 Zeilen (`_validate_schema`),
        # und das ist eine Aussage über einen **Bezug**, nicht über jeden Start — ein
        # bewusst kleiner gehaltenes Wörterbuch fiele sonst bei jedem Aufruf durch.
        # `ensure_index` ist der Teil, der hier zählt: Eine von Hand hinterlegte Datei
        # bringt die beiden Indizes nicht mit, und ohne sie kostet jedes Kapitel 32 bis
        # 44 s statt 1,1 s (technik.md §3, „Der Engpass ist das Nachschlagen, nicht das
        # Modell") — lautlos.
        dictionary.ensure_index(cfg.dictionary_path)

    # Vor der Bestätigung festgehalten: Danach steht mit `_confirm_new_profile`s eigenem
    # `True` nicht mehr auseinander, ob die Datei schon da war oder gerade erst bestätigt
    # wurde — die Niveaufrage gehört aber nur zum zweiten Fall (Bauschritt 4/5, 31.08.2026).
    profile_is_new = not cfg.profile_path.is_file()
    if not _confirm_new_profile(cfg.profile_path, read_line, write_line):
        write_line("Abgebrochen — kein Profil angelegt.")
        return 1
    if profile_is_new:
        _apply_vocabulary_preset(
            dictionary_path=cfg.dictionary_path,
            profile_path=cfg.profile_path,
            read_line=read_line,
            write_line=write_line,
        )

    structure = epub.read_structure(args.epub_path)
    if structure.notice:
        write_line(structure.notice)

    # bauplan-phase2.md AP 5: `--chapters` löst hier eine **Liste** von Kapitelnummern
    # auf (Bereich oder `all`, Kapitel ohne Fließtext gesondert gemeldet und
    # ausgeschlossen); `--chapter`/die interaktive Auswahl bleiben unverändert eine Liste
    # mit einem einzigen Eintrag, keine Bilanz am Ende (E3: „`--chapter N` bleibt").
    skipped: list[_SkippedChapter] = []
    show_summary = args.chapters is not None
    if args.chapters is not None:
        listings = pipeline.list_chapters(args.epub_path)
        candidate_numbers = _resolve_chapter_range(args.chapters, listings)
        chapter_numbers, skipped = _split_skipped_chapters(
            candidate_numbers, listings, write_line=write_line
        )
        if not chapter_numbers:
            write_line("Kein Kapitel mit Fließtext im gewählten Bereich — nichts zu tun.")
            return 0
    else:
        chapter_numbers = [
            args.chapter
            if args.chapter is not None
            else _choose_chapter(args.epub_path, structure, read_line, write_line)
        ]

    write_line("Sprachmodell wird geladen …")
    nlp = extraction.load_nlp()
    write_line("Sprachmodell geladen.")

    card_direction = CardDirection(args.card_direction)
    get_model_name = model.cached_resolver(cfg.model_url, cfg.model_name)
    output_dir = args.output_dir or Path.cwd()

    # Eine Profilverbindung für den gesamten Kapitelbereich (bauplan-phase2.md AP 5,
    # Abnahmekriterium 2): Nur so sieht ein späteres Kapitel die „kenne ich"-Buchungen
    # eines früheren, bevor `_run_one_chapter` seine Auswahlliste bildet.
    con = profile.open_profile(cfg.profile_path)
    outcomes: list[_ChapterRunOutcome] = []
    try:
        for chapter_number in chapter_numbers:
            outcomes.append(
                _run_one_chapter(
                    con=con,
                    epub_path=args.epub_path,
                    chapter_number=chapter_number,
                    dictionary_path=cfg.dictionary_path,
                    profile_path=cfg.profile_path,
                    nlp=nlp,
                    cache_dir=data_dir / "cache",
                    card_direction=card_direction,
                    get_model_name=get_model_name,
                    model_url=cfg.model_url,
                    triage_order=cfg.triage_order,
                    output_dir=output_dir,
                    style=style,
                    read_line=read_line,
                    write_line=write_line,
                )
            )
    finally:
        con.close()

    if show_summary:
        _write_chapter_range_summary(outcomes, skipped, write_line)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    read_line: ReadLine = input,
    write_line: WriteLine = safe_print,
    style: display.Style | None = None,
) -> int:
    """Ein vollständiger Kapiteldurchlauf (bauplan.md T16) — der Bericht zu T16 nennt die
    Aufrufreihenfolge im Einzelnen unter „Wie ein vollständiger Durchlauf aussieht".

    `read_line`/`write_line` sind austauschbar (Vorgabe `input`/`cli.display.safe_print`):
    Tests ersetzen beide, statt eine echte Konsole zu bedienen. `style` folgt derselben
    Idee (Auftragstext vom 02.09.2026, Bauschritt 2/2 der Konsolenausgabe): fehlt er,
    ermittelt `display.detect_style()` ihn **einmal** an `sys.stdout` — dem tatsächlichen
    Ausgabeziel, unabhängig von einem in Tests injizierten `write_line`. Tests, denen der
    Ausgabestil nicht gleichgültig ist (etwa `cli.display.PLAIN_STYLE` für eine
    deterministische, plattformunabhängige Form), geben ihn stattdessen selbst vor.
    """
    args = _parse_args(argv)
    # (Befund 1, Durchsicht e537273): `detect_style()` steht bewusst außerhalb des
    # folgenden `try` — geprüft und entschieden, nicht übersehen. Ihr einziger dort
    # bekannter Fehlschlag (ein Ziel, das `isatty()` bejaht, aber kein `fileno()` hat) ist
    # an der Quelle behoben (`display._enable_windows_console_color` fängt jetzt auch
    # `AttributeError`) und liefert seither immer einen `Style`, nie eine Ausnahme. Eine
    # andere, hier nicht vorgesehene Ausnahme wäre ohnehin kein Kernfehlschlag mit
    # deutscher Meldung (die beiden `except`-Zweige unten fangen nur `EOFError` und
    # `ValueError`/`FileNotFoundError`) und liefe innerhalb wie außerhalb des `try`
    # gleichermaßen unabgefangen durch — die Verschiebung änderte also nichts.
    resolved_style = style if style is not None else display.detect_style()
    try:
        return _run(args, read_line=read_line, write_line=write_line, style=resolved_style)
    except EOFError:
        # (Befund leicht a, Durchsicht ee34796): Eine abgeschnittene Eingabe (Pipe-Ende,
        # umgeleitetes /dev/null) lässt `input()` — und damit jedes `read_line` der fünf
        # Rückfragen in `cli/` — `EOFError` werfen. Vor dieser Behebung lief das bis zum
        # nackten, englischen Traceback durch: Regel 13 (sichtbarer Abbruch) war erfüllt,
        # die Sprachregel (dokumentation.md §1) nicht. Ein Fang neben dem für
        # `ValueError`/`FileNotFoundError`, statt ihn dort einzureihen: EOF ist kein
        # Kernfehlschlag mit eigener deutscher Meldung, sondern eine Eigenschaft der
        # Konsole selbst, also eine eigene, generische Meldung.
        write_line("Abgebrochen — keine Eingabe mehr.")
        return 1
    except (ValueError, FileNotFoundError) as error:
        # REGEL (dokumentation.md §4 Regel 13, „Kein except, das nur protokolliert und
        # weiterläuft"): Dieser Fang meldet und **beendet** den Lauf (exit-Code 1), er
        # läuft nicht weiter. Jede andere Ausnahme — ein echter Programmfehler statt
        # eines der hier durchgereichten, bereits deutschen Kernfehlschläge — bleibt
        # unabgefangen und zeigt ihren vollen Verlauf.
        write_line(f"Fehler: {error}")
        return 1
