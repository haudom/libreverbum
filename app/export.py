"""Export nach Anki und als Druckseite — der letzte Schritt eines Durchlaufs.

Aufgabe
-------
Wählt die Zielpfade für einen Kapitelexport (`export_paths`) und ruft darauf
`libreverbum.pipeline.export_cards` auf, das die Verkettung der Kernschritte selbst trägt
(Anki-Deck schreiben, Druckseite schreiben, je Karte die Anki-GUID ins Profil buchen —
technik.md §7, „Die Importregel": „Wer mehrere Schritte kennt, ist `pipeline` — und sonst
niemand"). Dieses Modul kennt deshalb selbst weder `anki` noch `printout` noch
`profile.record_card` — es leitet `Card.sense`/`Card.occurrence` nur in das von
`printout.write_printout` erwartete Tupelpaar um, mittelbar über `pipeline.export_cards`.

Liegt in `app/`, nicht mehr in `cli/` (bauplan-phase2.md AP 3): Was hier bleibt, ist die
Namensbildung (`export_paths`, `_2`/`_3`, `_teilexport`) — Sache des Aufrufers, nicht des
Kerns (technik.md §7). Die Verkettung der Kernschritte selbst wanderte bereits mit AP 2
nach `pipeline.export_cards`; dieses Modul ruft sie nur noch auf. `gui/` bekommt beides mit
diesem Umzug geschenkt, statt es nachzubauen (technik.md §14, E4).

Voraussetzungen
---------------
`cards` stammt aus **einem** Kapitel (dieselbe Annahme wie in `anki.export_deck` und
`printout.write_printout` selbst, die beide sichtbar abbrechen, wenn das verletzt ist).
`con` ist eine bereits geöffnete Profilverbindung (`libreverbum.profile.open_profile`) mit
bereits angelegter Kapitelzeile (Sache des Aufrufers — in `cli/` `interaction.
ensure_chapter_row`) — dieselbe Voraussetzung wie bei `profile.record_card`.

Liefert
-------
`export_paths` legt aus Buchtitel und Kapitelnummer einen dateisystemtauglichen
Namensstamm an und sucht dazu das erste Namenspaar, das noch frei ist — ein zweiter Lauf
über dasselbe Kapitel überschreibt nichts. `write_exports` ruft `pipeline.export_cards`
mit diesen Pfaden auf und liefert sie zurück.

`partial=True` (technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf
exportiert, was er hat") kennzeichnet einen **Teilexport** — geschrieben, wenn der
Aufrufer nach einem Fehlschlag mitten in der Triage die bereits entschiedenen Karten
sichert (heute `cli.main._run`, künftig ebenso aus `gui/`). Der Dateiname trägt dafür
den Zusatz `_teilexport`, der Deckname
(`f"{book_title} - Kapitel {chapter_number}"`) bleibt **unverändert**: `anki.
new_card_guid` liefert für dieselben Einträge dieselbe GUID, unabhängig von `partial` — ein
abweichender Deckname schöbe die Notizen eines späteren, vollständigen Laufs über dasselbe
Kapitel in ein zweites Deck, obwohl die GUIDs übereinstimmen (Abschnitt 8b).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import NamedTuple

from libreverbum import pipeline
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


def export_paths(
    output_dir: Path, book_title: str, chapter_number: int, *, partial: bool = False
) -> ExportPaths:
    """Die beiden **freien** Zielpfade für einen Export: `<Buch>_kapitel<N>.apkg` und
    `.html`, beim nächsten Lauf über dasselbe Kapitel `…_2`, dann `…_3`.

    `partial=True` hängt vor dieser Zählung `_teilexport` an den Namensstamm (technik.md
    §12, „Entschieden 15.09.2026 …") — der Teilstand steht damit im Dateinamen, nicht im
    Deck. Die Suche nach dem freien Namenspaar läuft unverändert auf dem so verlängerten
    Stamm: Auch für einen Teilexport müssen Deck und Druckseite beide frei sein.

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
    if partial:
        stem += "_teilexport"
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
    partial: bool = False,
) -> ExportPaths:
    """Wählt die Zielpfade (`export_paths`) und ruft darauf `pipeline.export_cards` auf,
    das den Export als Anki-Deck und als Druckseite samt der Anki-GUID-Buchung im Profil
    verkettet (bauplan-phase2.md AP 2; vor AP 2 lag diese Verkettung hier, technik.md §7).

    Erwartet `cards` nichtleer — eine leere Triage-Ausbeute ist kein Fehlschlag
    (Regel 13 gilt für Fehler, nicht für eine gültige Nutzerentscheidung „nichts
    lernen"), aber auch keine sinnvolle Exportanfrage; das prüft und meldet der Aufrufer
    (heute `cli.main`, künftig ebenso `gui/`), bevor diese Funktion aufgerufen wird —
    `pipeline.export_cards` bräche sonst mit derselben Meldung ab wie bei einem echten
    Fehler (`anki.export_deck`).

    `partial=True` (technik.md §12, „Entschieden 15.09.2026 …") ist derselbe Export, nur
    mit weniger Karten und einem anderen Dateinamen (`export_paths`) — der Deckname bleibt
    unverändert, die GUID-Buchung läuft unverändert je Karte.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = export_paths(output_dir, book_title, chapter_number, partial=partial)
    pipeline.export_cards(
        con,
        cards,
        anki_path=paths.anki_path,
        printout_path=paths.printout_path,
        deck_name=f"{book_title} - Kapitel {chapter_number}",
    )
    return paths
