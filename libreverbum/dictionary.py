"""Wörterbuch — Auswahlliste je Grundform und Wortart aus WikDict.

Aufgabe
-------
Schritt 5 des Kernablaufs (konzept.md §5), erste Hälfte: der einzige Zugriff auf
`en-de.sqlite3` (technik.md §7, Modulkarte). Liefert die Kandidaten, aus denen
`translation` — Schritt 5, zweite Hälfte — die im Kontext passende Bedeutung wählt.

Voraussetzungen
---------------
Erwartet die Grundform bereits wortartbestimmt (`Lemma.pos`, spaCys `token.pos_`): Die
Reihenfolge Wortart → Grundform → Nachschlagen ist zwingend (technik.md, „Warum die
Reihenfolge zwingend ist"). Der Erstbezug der Datenbank — Herunterladen, Prüfsumme, von
Hand hinterlegte Datei — ist T6 und liegt außerhalb dieses Moduls; hier wird nur eine
vorhandene Datei gelesen.

Liefert
-------
Je Grundform und Wortart eine nach `score` absteigend sortierte Liste von `Sense`
(bauplan.md T5). Zeilen ohne `sense`-Text bleiben darin (Regel 1); `label` liefert für sie
die vorgeschriebene Beschriftung. Wählt selbst keine Bedeutung aus und übersetzt nichts
frei — das bleibt `translation` vorbehalten.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from libreverbum.entities import Lemma, Sense

# REGEL (dokumentation.md §4 Regel 1, technik.md §3 „Datenfalle: Einträge ohne
# Bedeutungstext"): Zeilen ohne sense-Text nicht wegfiltern. 36 % aller Zeilen, systematisch
# die Hauptbedeutungen (watch → „Uhr", draw → „zeichnen"). Wer sie entfernt, erzeugt
# scheinbare Wörterbuchlücken. `entities.Sense` hält `wikdict_sense` für diese Zeilen
# bewusst auf `None` — die Beschriftung unten ist reine Anzeige, kein gespeicherter Wert.
NO_SENSE_LABEL = "Hauptbedeutung, ohne nähere Angabe"

# REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): Wortart vor Grundform vor
# Nachschlagen — `saw` als Verb darf nicht die Säge liefern. WikDicts `lexentry` trägt die
# Wortart als eigenes Segment (`eng/<wort>__<Wortart>__<n>`) unter deren eigenem Namen.
# Nur die fünf Wortarten, die T3s Inhaltswortfilter dieser Phase überhaupt vorlegt (Regel 14,
# kein Vorrat auf Vorrat): Substantiv, Verb, Adjektiv, Adverb, Interjektion. `PROPN` fehlt
# bewusst — T3 setzt `chosen_pos` nie darauf, und T7 filtert `Proper_noun` ohnehin weg.
_WIKDICT_POS = {
    "NOUN": "Noun",
    "VERB": "Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "INTJ": "Interjection",
}


def label(sense: Sense) -> str:
    """Beschriftung für die Auswahlliste: `wikdict_sense`, oder — fehlt er — Regel 1s feste
    Beschriftung `NO_SENSE_LABEL`."""
    return sense.wikdict_sense or NO_SENSE_LABEL


def _wikdict_pos(lexentry: str | None) -> str | None:
    """Die Wortart aus WikDicts `lexentry`-Kennung (`eng/<wort>__<Wortart>__<n>`)."""
    if lexentry is None or "__" not in lexentry:
        return None
    return lexentry.split("__")[1]


def candidates(dictionary_path: Path, lemma: Lemma) -> list[Sense]:
    """Auswahlliste für eine Grundform und Wortart, nach `score` absteigend.

    Regel 1 (dokumentation.md §4): Zeilen ohne `sense`-Text bleiben in der Liste — sie sind
    systematisch die Hauptbedeutungen, keine Lücken. Die Wortart ist Teil der Abfrage: `saw`
    als Verb liefert nur „sägen", nie die Säge (technik.md, „Warum die Reihenfolge zwingend
    ist"). Eine fehlende oder unlesbare Wörterbuchdatei bricht sichtbar ab (Regel 13) statt
    eine leere Liste zurückzugeben, die wie „kein Eintrag gefunden" aussähe.
    """
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    try:
        wikdict_pos = _WIKDICT_POS[lemma.pos]
    except KeyError as error:
        raise ValueError(f"Keine WikDict-Wortart für {lemma.pos!r} hinterlegt.") from error

    con = sqlite3.connect(dictionary_path)
    try:
        # REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): lexentry IS NOT NULL ist
        # eine ausdrückliche Entscheidung, keine Nebenwirkung. 29,7 % der Zeilen in
        # tools/en-de.sqlite3 haben lexentry = NULL und tragen damit keine Wortart —
        # _wikdict_pos gäbe für sie still None zurück, das nie einer WikDict-Wortart gleicht,
        # und die Zeile verschwände unbemerkt aus jeder Auswahlliste. Vertretbar, weil alle
        # betroffenen Zeilen bei score <= 48 liegen, deutlich unter den Hauptbedeutungen —
        # aber das gehört sichtbar in die Abfrage, nicht als stiller Filterausfall.
        rows: list[tuple[str | None, str | None, str | None]] = con.execute(
            "SELECT lexentry, sense, trans_list FROM translation "
            "WHERE written_rep = ? AND lexentry IS NOT NULL ORDER BY score DESC",
            (lemma.text,),
        ).fetchall()
    finally:
        con.close()

    return [
        Sense(
            lemma=lemma,
            wikdict_sense=wikdict_sense,
            wikdict_trans_list=trans_list,
            wikdict_lexentry=lexentry,
        )
        for lexentry, wikdict_sense, trans_list in rows
        if _wikdict_pos(lexentry) == wikdict_pos
    ]
