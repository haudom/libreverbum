"""Export nach Anki und als Druckseite — der letzte Schritt eines Durchlaufs.

Aufgabe
-------
Formt die aus der Triage entstandenen `Card`-Objekte (`cli.interaction.run_triage_pass`)
zu Aufrufen von `libreverbum.anki.export_deck` und `libreverbum.printout.write_printout`.
Beide Kernfunktionen bekommen dabei nur, was sie laut ihren eigenen Voraussetzungen
verlangen — dieses Modul wählt nur die Zielpfade und leitet `Card.sense`/`Card.occurrence`
für die Druckseite in das dort erwartete Tupelpaar um (`printout.py`, „Voraussetzungen").
Nach einem erfolgreichen `anki.export_deck` schreibt es außerdem je Karte
`libreverbum.profile.record_card` — die Nachbesserung zum Befund mittel aus der
T16-Durchsicht: Ohne diesen Schritt landete `card.guid` nie im Profil, obwohl
`anki.new_card_guid` sie längst erzeugt (Regel 6, dokumentation.md §4).

Voraussetzungen
---------------
`cards` stammt aus **einem** Kapitel (dieselbe Annahme wie in `anki.export_deck` und
`printout.write_printout` selbst, die beide sichtbar abbrechen, wenn das verletzt ist).
`con` ist eine bereits geöffnete Profilverbindung (`libreverbum.profile.open_profile`) mit
bereits angelegter Kapitelzeile (`cli.interaction.ensure_chapter_row`) — dieselbe
Voraussetzung wie bei `profile.record_card`.

Liefert
-------
`export_paths` legt aus Buchtitel und Kapitelnummer einen dateisystemtauglichen
Namensstamm an und sucht dazu das erste Namenspaar, das noch frei ist — ein zweiter Lauf
über dasselbe Kapitel überschreibt nichts. `write_exports` ruft beide Kernexporte auf,
schreibt danach je Karte die Anki-GUID ins Profil und liefert die beiden geschriebenen
Pfade zurück.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import NamedTuple

from libreverbum import anki, printout, profile
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
    """Die beiden **freien** Zielpfade für einen Export: `<Buch>_kapitel<N>.apkg` und
    `.html`, beim nächsten Lauf über dasselbe Kapitel `…_2`, dann `…_3`.

    Bis zum 27.08.2026 war der Name allein aus Buchtitel und Kapitelnummer gebildet,
    „damit ein zweiter Lauf über dasselbe Kapitel dieselbe Datei trifft". Das überschrieb
    die Druckseite des ersten Laufs wortlos, und weil `profile.record_card` dessen Karten
    längst gebucht hat, kommen sie im zweiten Lauf nicht wieder: Wer das erste `.apkg`
    noch nicht importiert hatte, hatte die Karten verloren — der stille Fehlschlag aus
    Regel 13, hier als verschwundene Datei. Beim Anki-Deck ist die zweite Datei
    gefahrlos: Deck-Kennung und GUID sind stabil (technik.md §8b), Anki mischt sie in
    dasselbe Deck und aktualisiert dieselben Notizen, statt Dubletten anzulegen.

    Beide Namen tragen dieselbe Nummer, und frei sein müssen sie **beide**: Deck und
    Druckseite eines Laufs gehören zusammen, auch wenn nur eine der beiden Dateien schon
    existiert.

    Die Funktion beantwortet damit „wohin **jetzt** geschrieben wird", nicht „wo die
    Dateien dieses Kapitels liegen" — zweimal aufgerufen liefert sie zwei verschiedene
    Antworten, sobald der Export dazwischen geschrieben hat.
    """
    stem = f"{safe_filename_stem(book_title)}_kapitel{chapter_number}"
    counter = 1
    while True:
        suffix = "" if counter == 1 else f"_{counter}"
        anki_path = output_dir / f"{stem}{suffix}.apkg"
        printout_path = output_dir / f"{stem}{suffix}.html"
        if not anki_path.exists() and not printout_path.exists():
            return ExportPaths(anki_path=anki_path, printout_path=printout_path)
        counter += 1


def write_exports(
    con: sqlite3.Connection,
    output_dir: Path,
    cards: list[Card],
    *,
    book_title: str,
    chapter_number: int,
) -> ExportPaths:
    """Schreibt `cards` als Anki-Deck und als Druckseite (bauplan.md T16), danach je
    Karte die Anki-GUID ins Profil (Regel 6, Befund mittel Durchsicht T16).

    Erwartet `cards` nichtleer — eine leere Triage-Ausbeute ist kein Fehlschlag
    (Regel 13 gilt für Fehler, nicht für eine gültige Nutzerentscheidung „nichts
    lernen"), aber auch keine sinnvolle Exportanfrage; das prüft und meldet der Aufrufer
    (`cli.main`), bevor diese Funktion aufgerufen wird — `anki.export_deck` und
    `printout.write_printout` brächen sonst mit derselben Meldung ab wie bei einem
    echten Fehler.

    `profile.record_card` läuft erst **nach** einem erfolgreichen `anki.export_deck`:
    Bricht der Export ab (fehlende Übersetzung ohne die Marke `uncertain`, eine Karte, die
    in ihrer Kartenrichtung nicht bildbar ist — `anki.card_obstacle` —, doppelte GUID im
    selben Export; siehe `anki.export_deck`), steht im Profil nichts, was im Deck nicht
    ebenso fehlt.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = export_paths(output_dir, book_title, chapter_number)
    anki.export_deck(paths.anki_path, cards, deck_name=f"{book_title} - Kapitel {chapter_number}")
    for card in cards:
        profile.record_card(con, card)
    printout.write_printout(paths.printout_path, [(card.occurrence, card.sense) for card in cards])
    return paths
