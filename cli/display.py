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
