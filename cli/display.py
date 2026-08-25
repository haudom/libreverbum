"""Bildschirmausgabe, die eine eingeschränkte Konsolenkodierung übersteht.

Aufgabe
-------
Ein Belegsatz aus dem Buchtext kann typografische Anführungszeichen und Gedankenstriche
tragen (dokumentation.md §1). Unter Windows ist die Konsolenkodierung oft `cp1252` und
kann solche Zeichen nicht darstellen — ein bloßes `print()` bräche die Triage dort mit
einem `UnicodeEncodeError` ab. CLAUDE.md verlangt `encoding="utf-8"` nur ausdrücklich für
Dateien; dieselbe Gefahr gilt aber für die Bildschirmausgabe, und Regel 13
(dokumentation.md §4) verbietet ohnehin einen stillen Absturz mitten in der Triage.

Voraussetzungen
---------------
Keine.

Liefert
-------
`safe_print` schreibt `text` auf `stream` (Vorgabe `sys.stdout`) und weicht bei einem
`UnicodeEncodeError` auf eine verlustbehaftete, aber abbruchfreie Kodierung desselben
Zeichensatzes aus (`errors="replace"`) — auf einer cp1252-Konsole erscheint ein
Gedankenstrich dann als `?`, die Triage läuft aber weiter.

`safe_print_progress` und `finish_progress_line` sind das Gegenstück für eine sich
fortschreibende Statuszeile (Auftragstext vom 25.08.2026, Abschnitt 3): Ein Lauf, der
minutenlang ohne jede Ausgabe rechnet — `pipeline.resolve_triage_entries` bei `[triage]
order = "frequency"` und reifem Profil —, ist der stille Fehlschlag, den Regel 13
verbietet. Der Kern selbst gibt nichts aus (technik.md §7, „Kern ohne Bezug zur
Oberfläche"); `resolve_triage_entries` bekommt dafür nur einen Rückruf, den `cli.main`
über diese beiden Funktionen bedient.
"""

from __future__ import annotations

import sys
from typing import TextIO


def safe_print(text: str, *, stream: TextIO | None = None) -> None:
    """Schreibt `text` als Zeile auf `stream` (Vorgabe `sys.stdout`), ohne bei einer
    Konsole mit eingeschränkter Kodierung abzubrechen.

    `stream` wird spät ausgewertet (`sys.stdout` erst beim Aufruf, nicht als
    Vorgabewert der Funktion), weil Tests `sys.stdout` mitunter ersetzen, nachdem dieses
    Modul bereits importiert wurde.
    """
    target = stream if stream is not None else sys.stdout
    try:
        print(text, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), file=target)


def _write_raw(text: str, *, stream: TextIO | None, end: str) -> None:
    """Gemeinsame Fehlerbehandlung für `safe_print_progress` und `finish_progress_line`
    — dieselbe Ausweichkodierung wie `safe_print`, nur ohne den erzwungenen
    Zeilenumbruch, damit sich die Statuszeile per Wagenrücklauf selbst überschreibt."""
    target = stream if stream is not None else sys.stdout
    try:
        print(text, end=end, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), end=end, file=target)


def safe_print_progress(text: str, *, stream: TextIO | None = None) -> None:
    """Schreibt `text` als sich selbst überschreibende Statuszeile: Wagenrücklauf (`\\r`)
    statt Zeilenumbruch, dieselbe Ausweichkodierung wie `safe_print` bei einer
    eingeschränkten Konsole.

    Aufeinanderfolgende Aufrufe innerhalb **eines** Laufs dürfen `text` nur wachsen
    lassen, nie kürzen — sonst blieben Reste der vorigen, längeren Zeile stehen, weil
    ein Wagenrücklauf nichts löscht, nur den Cursor zurücksetzt. Für
    `pipeline.resolve_triage_entries` ist das garantiert: Die geprüfte und die
    behaltene Zahl wachsen über einen Lauf hinweg nur, die Gesamtzahlen bleiben fest.
    `finish_progress_line` schließt die Zeile ab, bevor reguläre Ausgabe folgt — sonst
    verstümmelt der fehlende Zeilenumbruch die erste Triage-Frage danach."""
    _write_raw(f"\r{text}", stream=stream, end="")


def finish_progress_line(*, stream: TextIO | None = None) -> None:
    """Schließt eine mit `safe_print_progress` begonnene Zeile mit einem Zeilenumbruch
    ab — aufzurufen, sobald mindestens eine Statuszeile geschrieben wurde, bevor die
    nächste reguläre Ausgabe (etwa die erste Triage-Frage) folgt."""
    _write_raw("", stream=stream, end="\n")
