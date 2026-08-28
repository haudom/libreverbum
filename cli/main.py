"""Einstiegspunkt — ein vollständiger Kapiteldurchlauf (bauplan.md T16).

Aufgabe
-------
Verkettet, was `cli.config`, `libreverbum.epub`, `libreverbum.extraction`,
`libreverbum.pipeline`, `cli.interaction` und `cli.export` je für sich liefern, zu einem
Aufruf von der Kommandozeile: Wörterbuch beziehen oder indizieren
(`libreverbum.dictionary`), EPUB wählen, Kapitel wählen, `pipeline.run_chapter`,
je Decksel `pipeline.resolve_triage_entries` (Bedeutung vor der Triage auflösen, Befund
schwer 1, zweite T16-Durchsicht), Triage über die Tastatur (Wörter, dann Wendungen),
Export nach Anki und als Druckseite.

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
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from cli import config, export, interaction, model
from cli.display import finish_progress_line, safe_print, safe_print_progress
from cli.interaction import ReadLine, WriteLine
from libreverbum import dictionary, epub, extraction, pipeline, profile
from libreverbum.entities import CardDirection

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable


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
    `0` wäre genau der stille Fehlschlag, den Regel 13 verbietet (technik.md §8, Nachtrag
    28.08.2026, „Was die Kapitelliste zusätzlich zeigt")."""
    if count is None:
        return "unbekannt"
    return f"{count:,}".replace(",", ".")


def _choose_chapter(
    epub_path: Path, structure: epub.BookStructure, read_line: ReadLine, write_line: WriteLine
) -> int:
    """Zeigt die Kapitelliste mit Wortumfang je Kapitel und fragt so lange nach, bis eine
    darin vorhandene Kapitelnummer eingegeben wird (technik.md §8, Nachtrag 28.08.2026,
    „Was die Kapitelliste zusätzlich zeigt"): Der Umfang steht vor dem Titel in einer
    eigenen, rechtsbündigen Spalte, damit die Zahlen untereinander vergleichbar bleiben —
    ein 80 Zeichen langer Kapiteltitel zerschießt die Ausrichtung damit nicht."""
    write_line(f"„{structure.book.title}“ von {structure.book.author}")
    word_counts = epub.count_chapter_words(epub_path, structure.chapters)
    formatted_counts = {
        chapter.number: _format_word_count(word_counts.get(chapter.number))
        for chapter in structure.chapters
    }
    column_width = max((len(value) for value in formatted_counts.values()), default=0)
    for chapter in structure.chapters:
        count_column = formatted_counts[chapter.number]
        write_line(f"  {chapter.number}. Wörter: {count_column:>{column_width}}  {chapter.title}")
    while True:
        answer = read_line("Kapitel wählen: ").strip()
        try:
            number = int(answer)
        except ValueError:
            write_line("Bitte eine Zahl eingeben.")
            continue
        if any(chapter.number == number for chapter in structure.chapters):
            return number
        write_line("Diese Kapitelnummer gibt es nicht.")


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
    fort und wird nur dann abgeschlossen (`finish_progress_line`), wenn tatsächlich
    mindestens einmal berichtet wurde — ein Decksel ohne zu prüfende Einträge (etwa
    „Wendungen" in einem Kapitel ohne Wendungen) soll keine leere Zeile hinterlassen.
    Der Abschluss läuft in `finally` (Befund leicht 1, Durchsicht T16/T17): Bricht der
    Modellserver mitten im Kapitel ab, klebte die Fehlermeldung sonst an der noch
    offenen Statuszeile, statt in einer eigenen Zeile zu erscheinen."""
    started = False

    def _on_progress(examined: int, total: int, kept: int, limit_: int) -> None:
        nonlocal started
        started = True
        # (Befund leicht 4, Durchsicht T16/T17): total ist die Obergrenze der Einträge
        # (Vorfilter aus resolve_triage_entries, Schritt 1, hat schon abgezogen), nicht die
        # Zahl der tatsächlich geprüften — der Lauf endet spätestens bei `limit` Treffern,
        # meist weit vor total. „möglichen" macht das im Nenner sichtbar.
        safe_print_progress(
            f"Bedeutungen werden aufgelöst: {examined} von {total} möglichen geprüft, "
            f"{kept} von {limit_} behalten."
        )

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


def _run(args: argparse.Namespace, *, read_line: ReadLine, write_line: WriteLine) -> int:
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
        # 44 s statt 1,1 s (technik.md §3, „Nachtrag 17.08.2026") — lautlos.
        dictionary.ensure_index(cfg.dictionary_path)

    if not _confirm_new_profile(cfg.profile_path, read_line, write_line):
        write_line("Abgebrochen — kein Profil angelegt.")
        return 1

    structure = epub.read_structure(args.epub_path)
    if structure.notice:
        write_line(structure.notice)
    chapter_number = (
        args.chapter
        if args.chapter is not None
        else _choose_chapter(args.epub_path, structure, read_line, write_line)
    )

    write_line("Lade Sprachmodell …")
    nlp = extraction.load_nlp()

    result = pipeline.run_chapter(
        epub_path=args.epub_path,
        chapter_number=chapter_number,
        dictionary_path=cfg.dictionary_path,
        profile_path=cfg.profile_path,
        nlp=nlp,
    )
    if result.notice:
        write_line(result.notice)

    card_direction = CardDirection(args.card_direction)
    get_model_name = model.cached_resolver(cfg.model_url, cfg.model_name)

    con = profile.open_profile(cfg.profile_path)
    try:
        interaction.ensure_chapter_row(
            con, result.chapter.book, result.chapter.number, result.chapter.title
        )

        # (Befund schwer 1, zweite T16-Durchsicht): Die Bedeutung wird vor der Triage
        # aufgelöst (`pipeline.resolve_triage_entries`, je Decksel einmal) — Wörter und
        # Wendungen bleiben dabei getrennte Durchläufe mit eigener Obergrenze (`cli.
        # interaction`, „Festlegung: getrennte Decksel").
        write_line("== Wörter ==")
        word_resolution = _resolve_with_progress(
            con=con,
            entries=result.entries,
            limit=interaction.WORD_LIMIT,
            url=cfg.model_url,
            get_model_name=get_model_name,
            order=cfg.triage_order,
        )
        word_cards = interaction.run_triage_pass(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            resolution=word_resolution,
            label="Wörter",
            card_direction=card_direction,
            read_line=read_line,
            write_line=write_line,
        )
        write_line("== Wendungen ==")
        expression_resolution = _resolve_with_progress(
            con=con,
            entries=result.expressions,
            limit=interaction.EXPRESSION_LIMIT,
            url=cfg.model_url,
            get_model_name=get_model_name,
            order=cfg.triage_order,
        )
        expression_cards = interaction.run_triage_pass(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            resolution=expression_resolution,
            label="Wendungen",
            card_direction=card_direction,
            read_line=read_line,
            write_line=write_line,
        )

        cards = word_cards + expression_cards
        if not cards:
            write_line("Keine Wörter zum Lernen ausgewählt — kein Export.")
            return 0

        # (Befund mittel, Durchsicht T16): profile.record_card schreibt die Anki-GUID
        # jeder Karte ins Profil (Regel 6) und braucht dafür dieselbe, noch offene
        # Profilverbindung wie die Triage — der Export bleibt deshalb innerhalb dieses
        # try-Blocks, statt `con` vorher zu schließen.
        output_dir = args.output_dir or Path.cwd()
        paths = export.write_exports(
            con,
            output_dir,
            cards,
            book_title=result.chapter.book.title,
            chapter_number=result.chapter.number,
        )
        write_line(f"Anki-Deck: {paths.anki_path}")
        write_line(f"Druckseite: {paths.printout_path}")
        return 0
    finally:
        con.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    read_line: ReadLine = input,
    write_line: WriteLine = safe_print,
) -> int:
    """Ein vollständiger Kapiteldurchlauf (bauplan.md T16) — der Bericht zu T16 nennt die
    Aufrufreihenfolge im Einzelnen unter „Wie ein vollständiger Durchlauf aussieht".

    `read_line`/`write_line` sind austauschbar (Vorgabe `input`/`cli.display.safe_print`):
    Tests ersetzen beide, statt eine echte Konsole zu bedienen.
    """
    args = _parse_args(argv)
    try:
        return _run(args, read_line=read_line, write_line=write_line)
    except (ValueError, FileNotFoundError) as error:
        # REGEL (dokumentation.md §4 Regel 13, „Kein except, das nur protokolliert und
        # weiterläuft"): Dieser Fang meldet und **beendet** den Lauf (exit-Code 1), er
        # läuft nicht weiter. Jede andere Ausnahme — ein echter Programmfehler statt
        # eines der hier durchgereichten, bereits deutschen Kernfehlschläge — bleibt
        # unabgefangen und zeigt ihren vollen Verlauf.
        write_line(f"Fehler: {error}")
        return 1
