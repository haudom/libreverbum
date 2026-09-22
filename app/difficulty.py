"""Einordnung des Buch-Schwierigkeitschecks — die drei Schwellenworte aus E12.

Aufgabe
-------
`libreverbum.pipeline.assess_book` liefert Zahlen (`unknown_per_thousand`, `coverage`),
keine Worte — „ca. 14 unbekannte Wörter pro Seite, zu schwer für dich" (konzept.md, „Phase
2") ist eine Einordnung, keine Messung, und liegt deshalb hier statt im Kern
(bauplan-phase2.md AP 7: „Schwellen liegen in `app/`, nicht im Kern"; technik.md §14, E4:
was der Kern nicht kennen darf, aber beide Oberflächen brauchen, gehört nach `app/`).

**Die drei Schwellen sind eine Vermutung, keine Messung** (bauplan-phase2.md, E12): „Für
die Einordnung … werden vorläufig drei Schwellen gesetzt und als Vermutung markiert —
belastbar wird die Skala erst, wenn sie an drei gelesenen Büchern gegen das eigene
Empfinden gehalten wurde." Dieses Modul markiert sie entsprechend im Namen
(`_GUESSED_...`) und im `DifficultyLevel`-Docstring, nicht mit der REGEL-Marke aus
dokumentation.md §4 — die ist den fünfzehn Regeln vorbehalten, hier gilt keine von ihnen.

Voraussetzungen
---------------
`unknown_per_thousand` stammt aus `pipeline.BookDifficulty` oder `pipeline.
ChapterDifficulty` — eine Dichte unverstandener Grundformen je 1.000 Wortformen, keine
Bestandsaufnahme des Wortschatzes (siehe `BookDifficulty`s Docstring, „Aggregiert wird über
Wortformen").

Liefert
-------
`classify_difficulty` ordnet eine solche Dichte einer von drei `DifficultyLevel`-Stufen zu.
Wie die Stufe im Deutschen heißt, ist Sache der Oberfläche (`cli.main`, künftig `gui/`),
nicht dieses Moduls — `app/` liefert fertige Werte, keinen Oberflächentext (Paket-Docstring,
`app/__init__.py`, „Liefert").
"""

from __future__ import annotations

import enum


class DifficultyLevel(enum.Enum):
    """Die drei Einordnungsstufen des Schwierigkeitschecks (bauplan-phase2.md AP 7, E12) —
    Vermutung, nicht gemessen, siehe Moduldocstring. `EASY`: die Dichte unbekannter
    Grundformen ist niedrig, das Buch liest sich weitgehend ohne Nachschlagen. `MODERATE`:
    spürbar, aber mit Vorbereitung machbar — der Regelfall, für den LibreVerbum gebaut ist.
    `HARD`: „zu schwer für dich" im Wortlaut von E12."""

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


# Vermutung, nicht gemessen (E12, siehe Moduldocstring) — zwei Schnittpunkte, drei Stufen.
# Rezept: pipeline.assess_book gegen tools/sherlock.epub und tools/dorian_gray.epub, je
# einmal mit leerem Profil und einmal nach pipeline.write_vocabulary_preset(cefr_level=
# CefrLevel.B1) (22.09.2026, Bericht zu diesem Auftragspaket, AP 7). Buchweites
# unknown_per_thousand: Sherlock leer 156,9, B1 83,8 · Dorian Gray leer 202,5, B1 102,5 —
# die Vorbelegung senkt die Zahl in beiden Büchern auf etwa die Hälfte (E12s
# Prüfvorgabe), bleibt aber deutlich über „leicht". Mit leerem Profil liegen beide Bücher
# weit über jeder sinnvollen oberen Schwelle (ein Kalibrierdurchlauf ohne jede
# Vorbelegung ist ohnehin nicht der Fall, für den die Einordnung gedacht ist, konzept.md,
# „Der erste Durchlauf je Buch ist ein Kalibrierdurchlauf, kein Lerndurchlauf"). Die
# beiden Schnittpunkte trennen deshalb an den B1-Werten: Sherlock (83,8) fällt knapp unter
# die zweite Schwelle, Dorian Gray (102,5) knapp darüber — plausibel für den spürbar
# dichteren, literarischeren Wortschatz Wildes gegenüber Doyles zugänglicherer Prosa, aber
# **ungeprüft** gegen echtes Leseempfinden (E12: „belastbar … erst, wenn sie an drei
# gelesenen Büchern gegen das eigene Empfinden gehalten wurde").
_GUESSED_EASY_MAX_UNKNOWN_PER_THOUSAND = 40.0
_GUESSED_MODERATE_MAX_UNKNOWN_PER_THOUSAND = 100.0


def classify_difficulty(unknown_per_thousand: float) -> DifficultyLevel:
    """Ordnet eine Dichte unbekannter Grundformen je 1.000 Wortformen einer der drei
    Stufen zu — Vermutung, siehe Moduldocstring und die REGEL-lose Begründung bei den
    beiden Schwellen oben. `<=` an beiden Schnittpunkten: Ein Buch genau auf der Schwelle
    zählt zur leichteren der beiden angrenzenden Stufen, nicht zur schwereren."""
    if unknown_per_thousand <= _GUESSED_EASY_MAX_UNKNOWN_PER_THOUSAND:
        return DifficultyLevel.EASY
    if unknown_per_thousand <= _GUESSED_MODERATE_MAX_UNKNOWN_PER_THOUSAND:
        return DifficultyLevel.MODERATE
    return DifficultyLevel.HARD
