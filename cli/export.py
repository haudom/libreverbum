"""Export nach Anki und als Druckseite — der letzte Schritt eines Durchlaufs.

Aufgabe
-------
Formt die aus der Triage entstandenen `Card`-Objekte (`cli.interaction.run_triage_pass`)
zu Aufrufen von `libreverbum.anki.export_deck` und `libreverbum.printout.write_printout`.
Beide Kernfunktionen bekommen dabei nur, was sie laut ihren eigenen Voraussetzungen
verlangen — dieses Modul wählt nur die Zielpfade und leitet `Card.sense`/`Card.occurrence`
für die Druckseite in das dort erwartete Tupelpaar um (`printout.py`, „Voraussetzungen").

Voraussetzungen
---------------
`cards` stammt aus **einem** Kapitel (dieselbe Annahme wie in `anki.export_deck` und
`printout.write_printout` selbst, die beide sichtbar abbrechen, wenn das verletzt ist).

Liefert
-------
`export_paths` legt aus Buchtitel und Kapitelnummer einen dateisystemtauglichen
Namensstamm an, `write_exports` ruft beide Kernexporte auf und liefert die beiden
geschriebenen Pfade zurück.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from libreverbum import anki, printout
from libreverbum.entities import Card

# Alles außer Buchstaben, Ziffern, Bindestrich und Unterstrich wird zu „_" — ein Buchtitel
# trägt oft Doppelpunkt, Anführungszeichen oder Schrägstrich, die auf Windows-Dateisystemen
# ungültig oder auf anderen zumindest verwirrend sind.
_UNSAFE_CHARS = re.compile(r"[^\w-]+", re.UNICODE)


def safe_filename_stem(text: str) -> str:
    """Ein dateisystemtauglicher Namensstamm aus `text` — nicht leer, solange `text`
    mindestens ein alphanumerisches Zeichen enthält."""
    stem = _UNSAFE_CHARS.sub("_", text).strip("_")
    return stem or "kapitel"


class ExportPaths(NamedTuple):
    anki_path: Path
    printout_path: Path


def export_paths(output_dir: Path, book_title: str, chapter_number: int) -> ExportPaths:
    """Die beiden Zielpfade für einen Export — deterministisch aus Buchtitel und
    Kapitelnummer, damit ein zweiter Lauf über dasselbe Kapitel dieselbe Datei trifft
    (dasselbe Verhalten wie `anki._deck_id` auf Ebene des Decks)."""
    stem = f"{safe_filename_stem(book_title)}_kapitel{chapter_number}"
    return ExportPaths(
        anki_path=output_dir / f"{stem}.apkg", printout_path=output_dir / f"{stem}.html"
    )


def write_exports(
    output_dir: Path, cards: list[Card], *, book_title: str, chapter_number: int
) -> ExportPaths:
    """Schreibt `cards` als Anki-Deck und als Druckseite (bauplan.md T16).

    Erwartet `cards` nichtleer — eine leere Triage-Ausbeute ist kein Fehlschlag
    (Regel 13 gilt für Fehler, nicht für eine gültige Nutzerentscheidung „nichts
    lernen"), aber auch keine sinnvolle Exportanfrage; das prüft und meldet der Aufrufer
    (`cli.main`), bevor diese Funktion aufgerufen wird — `anki.export_deck` und
    `printout.write_printout` brächen sonst mit derselben Meldung ab wie bei einem
    echten Fehler.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = export_paths(output_dir, book_title, chapter_number)
    anki.export_deck(paths.anki_path, cards, deck_name=f"{book_title} - Kapitel {chapter_number}")
    printout.write_printout(paths.printout_path, [(card.occurrence, card.sense) for card in cards])
    return paths
