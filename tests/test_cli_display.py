"""Prüft `cli/display.py` — Bildschirmausgabe auf einer eingeschränkten Konsole
(bauplan.md T16; CLAUDE.md, „Dateien immer mit encoding=utf-8 öffnen")."""

from __future__ import annotations

import io

from cli.display import finish_progress_line, safe_print, safe_print_progress


def test_safe_print_does_not_crash_on_a_restricted_console_codepage() -> None:
    """Ein Belegsatz mit typografischen Anführungszeichen darf die Triage auf einer
    Konsole mit eingeschränkter Kodierung nicht mit `UnicodeEncodeError` abbrechen
    lassen (dokumentation.md §4 Regel 13).

    `cp850` statt `cp1252`: cp1252 enthält „ “ und — bereits (Microsofts ANSI-Codepage
    ist für westeuropäische Typografie ausgelegt); `cp850`, die klassische
    DOS-/conhost-OEM-Codepage älterer Windows-Konsolen, dagegen nicht — an ihr greift
    die Gefahr, vor der dieser Test schützt, tatsächlich."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp850", errors="strict")

    safe_print(
        "„Curiouser and curiouser!“ cried Alice — a dash and typographic quotes.", stream=stream
    )

    stream.flush()  # löst einen zurückgehaltenen UnicodeEncodeError erst hier aus


def test_safe_print_writes_the_original_text_on_a_capable_console() -> None:
    """Auf einer Konsole, die das Zeichen darstellen kann, wird nichts verändert."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")

    safe_print("„Test“", stream=stream)
    stream.flush()

    stream.seek(0)
    assert stream.buffer.getvalue().decode("utf-8").strip() == "„Test“"


def test_safe_print_progress_does_not_crash_on_a_restricted_console_codepage() -> None:
    """Auftragstext vom 25.08.2026, Abschnitt 3: Die Fortschrittszeile muss auf einer
    cp850-Konsole überleben, genau wie `safe_print` (Regel 13, dokumentation.md §4) —
    dieselbe Bauart wie
    `test_safe_print_does_not_crash_on_a_restricted_console_codepage`."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp850", errors="strict")

    safe_print_progress(
        "Bedeutungen werden aufgelöst: 37 von 412 geprüft, 12 von 25 behalten.", stream=stream
    )

    stream.flush()  # löst einen zurückgehaltenen UnicodeEncodeError erst hier aus


def test_safe_print_progress_writes_a_carriage_return_instead_of_a_newline() -> None:
    """Eine sich fortschreibende Statuszeile schreibt sich per Wagenrücklauf (`\\r`) selbst
    über sich — kein Zeilenumbruch, sonst entstünden „keine 400 Zeilen Protokoll", sondern
    eine wachsende Anzahl echter Zeilen (Auftragstext, Abschnitt 3)."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")

    safe_print_progress("1 von 10 geprüft, 0 von 5 behalten.", stream=stream)
    safe_print_progress("2 von 10 geprüft, 0 von 5 behalten.", stream=stream)
    stream.flush()

    stream.seek(0)
    written = stream.buffer.getvalue().decode("utf-8")
    assert written == "\r1 von 10 geprüft, 0 von 5 behalten.\r2 von 10 geprüft, 0 von 5 behalten."
    assert "\n" not in written


def test_finish_progress_line_closes_the_line_before_the_next_regular_output() -> None:
    """Ohne diesen Aufruf verstümmelt der fehlende Zeilenumbruch die erste reguläre
    Ausgabe danach (etwa die erste Triage-Frage) — der Wagenrücklauf setzt den Cursor nur
    zurück, er löscht nichts (Auftragstext, Abschnitt 3, „sauber abschließen, bevor die
    erste Frage kommt")."""
    # newline="": ohne Übersetzung von "\n" in os.linesep — sonst hinge das erwartete
    # Ergebnis unten vom Betriebssystem ab (Windows übersetzt sonst in "\r\n").
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")

    safe_print_progress("5 von 10 geprüft, 2 von 5 behalten.", stream=stream)
    finish_progress_line(stream=stream)
    safe_print("== Wörter ==", stream=stream)
    stream.flush()

    stream.seek(0)
    written = stream.buffer.getvalue().decode("utf-8")
    assert written == "\r5 von 10 geprüft, 2 von 5 behalten.\n== Wörter ==\n"
