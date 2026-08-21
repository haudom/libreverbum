"""Einstiegspunkt — ein vollständiger Kapiteldurchlauf (bauplan.md T16).

Aufgabe
-------
Verkettet, was `cli.config`, `libreverbum.epub`, `libreverbum.extraction`,
`libreverbum.pipeline`, `cli.interaction` und `cli.export` je für sich liefern, zu einem
Aufruf von der Kommandozeile: EPUB wählen, Kapitel wählen, `pipeline.run_chapter`,
Triage über die Tastatur (Wörter, dann Wendungen), Export nach Anki und als Druckseite.

Regel 9 (dokumentation.md §4), strukturelle Hälfte: Dieses Kommandozeilenprogramm hat
keine Ereignisschleife und keinen Oberflächen-Thread, den ein NLP- oder Modellaufruf
blockieren könnte — die prüfbare Hälfte der Regel ist hier **trivial erfüllt**, nicht
vergessen. Sie wird erst wieder relevant, sobald `cli` durch eine Qt-Oberfläche ersetzt
oder ergänzt wird (bauplan.md, Tor 5).

Voraussetzungen
---------------
Eine interaktive Konsole. `--data-dir` erlaubt, das plattformübliche Verzeichnis
(technik.md §9) für Tests durch ein Wegwerfverzeichnis zu ersetzen.

Liefert
-------
`main` einen Rückgabewert für `sys.exit` (0 Erfolg, 1 sichtbarer Abbruch nach Regel 13).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from cli import config, export, interaction, model
from cli.display import safe_print
from cli.interaction import ReadLine, WriteLine
from libreverbum import epub, extraction, pipeline, profile
from libreverbum.entities import CardDirection


def _build_parser() -> argparse.ArgumentParser:
    # (Befund mittel 3, Durchsicht T16): argparse.print_help()/format_help() schreiben
    # direkt auf sys.stdout beziehungsweise sys.stderr, an cli.display.safe_print vorbei
    # (dokumentation.md §4 Regel 13) — description und jeder help-Text unten bleiben
    # deshalb reines ASCII, statt sich auf eine bestimmte eingeschränkte Konsolenkodierung
    # zu verlassen. Die frühere Fassung dieses Kommentars entfernte nur den Pfeil "→" aus
    # dem help-Text von --card-direction und hielt die Stelle fälschlich für erledigt: Der
    # Gedankenstrich "—" blieb dort **und** in description stehen und brach auf cp850 —
    # der klassischen DOS-/conhost-Codepage, die tests/test_cli_display.py als die
    # gefährliche nennt, nicht bloß cp1252 — mit demselben UnicodeEncodeError ab
    # (test_help_text_survives_a_restricted_console_codepage in tests/test_cli_main.py
    # kodiert format_help() jetzt gegen genau diese Codepage). Umlaute wären auf cp850
    # selbst unschädlich, aber ASCII macht die Zusicherung unabhängig davon, welche
    # eingeschränkte Codepage als Nächstes zuschlägt.
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="LibreVerbum - Kapiteldurchlauf mit Triage ueber die Tastatur (T16).",
    )
    parser.add_argument("epub_path", type=Path, help="Pfad zur EPUB-Datei")
    parser.add_argument(
        "--chapter", type=int, default=None, help="Kapitelnummer (fehlt sie, wird gefragt)"
    )
    parser.add_argument(
        "--card-direction",
        choices=[direction.value for direction in CardDirection],
        default=CardDirection.EN_DE.value,
        help="Kartenrichtung des Exports (konzept.md Paragraf 6), Vorgabe: Englisch nach Deutsch",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Zielverzeichnis fuer Anki-Deck und Druckseite (Vorgabe: aktuelles Verzeichnis)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Abweichendes Datenverzeichnis statt des plattformueblichen (technik.md Paragraf 9)",
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


def _choose_chapter(
    structure: epub.BookStructure, read_line: ReadLine, write_line: WriteLine
) -> int:
    """Zeigt die Kapitelliste und fragt so lange nach, bis eine darin vorhandene
    Kapitelnummer eingegeben wird."""
    write_line(f"„{structure.book.title}“ von {structure.book.author}")
    for chapter in structure.chapters:
        write_line(f"  {chapter.number}. {chapter.title}")
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


def _run(args: argparse.Namespace, *, read_line: ReadLine, write_line: WriteLine) -> int:
    data_dir = args.data_dir or config.default_data_dir()
    cfg, just_created = config.load_config(data_dir)
    if just_created:
        write_line(f"config.toml wurde neu angelegt: {data_dir / 'config.toml'}")
        write_line("Werte prüfen (insbesondere model.url) und den Befehl erneut ausführen.")
        return 0

    if not cfg.dictionary_path.is_file():
        # REGEL (dokumentation.md §4 Regel 13): fehlendes Wörterbuch bricht laut ab,
        # statt eines leeren oder scheinbar erfolgreichen Durchlaufs. Geprüft vor jeder
        # Rückfrage an den Nutzer (etwa der Profilbestätigung unten) — ein Lauf, der
        # ohnehin nicht weiterkommt, soll nicht erst nach einer Bestätigung scheitern.
        raise FileNotFoundError(
            f"Wörterbuch nicht gefunden: {cfg.dictionary_path}. Bezug etwa mit "
            "„python tools/coverage_check.py --fetch-dictionary“ (CLAUDE.md, „tools/ — die "
            "Messskripte“), danach unter paths.dictionary in config.toml eintragen oder ins "
            "Datenverzeichnis kopieren."
        )

    if not _confirm_new_profile(cfg.profile_path, read_line, write_line):
        write_line("Abgebrochen — kein Profil angelegt.")
        return 1

    structure = epub.read_structure(args.epub_path)
    if structure.notice:
        write_line(structure.notice)
    chapter_number = (
        args.chapter
        if args.chapter is not None
        else _choose_chapter(structure, read_line, write_line)
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
        write_line("== Wörter ==")
        word_cards = interaction.run_triage_pass(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            entries=result.entries,
            limit=interaction.WORD_LIMIT,
            label="Wörter",
            card_direction=card_direction,
            get_model_name=get_model_name,
            model_url=cfg.model_url,
            read_line=read_line,
            write_line=write_line,
        )
        write_line("== Wendungen ==")
        expression_cards = interaction.run_triage_pass(
            con=con,
            book=result.chapter.book,
            chapter_number=result.chapter.number,
            entries=result.expressions,
            limit=interaction.EXPRESSION_LIMIT,
            label="Wendungen",
            card_direction=card_direction,
            get_model_name=get_model_name,
            model_url=cfg.model_url,
            read_line=read_line,
            write_line=write_line,
        )
    finally:
        con.close()

    cards = word_cards + expression_cards
    if not cards:
        write_line("Keine Wörter zum Lernen ausgewählt — kein Export.")
        return 0

    output_dir = args.output_dir or Path.cwd()
    paths = export.write_exports(
        output_dir,
        cards,
        book_title=result.chapter.book.title,
        chapter_number=result.chapter.number,
    )
    write_line(f"Anki-Deck: {paths.anki_path}")
    write_line(f"Druckseite: {paths.printout_path}")
    return 0


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
