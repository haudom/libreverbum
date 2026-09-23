"""Einordnung des Buch-Schwierigkeitschecks — die drei Schwellenworte aus E12.

Aufgabe
-------
`libreverbum.pipeline.assess_book` liefert Zahlen (`unknown_per_thousand`, `coverage`),
keine Worte — „ca. 14 unbekannte Wörter pro Seite, zu schwer für dich" (konzept.md, „Phase
2") ist eine Einordnung, keine Messung, und liegt deshalb hier statt im Kern
(bauplan-phase2.md AP 7: „Schwellen liegen in `app/`, nicht im Kern"; technik.md §14, E4:
was der Kern nicht kennen darf, aber beide Oberflächen brauchen, gehört nach `app/`).

**Die Maßzahl der Einordnung ist die Abdeckung, nicht mehr „unbekannte Grundformen je
1.000"** (Nachbesserung der Durchsicht c6f3875, Befund 2, Entscheidung Dominiks
23.09.2026, E12): `unknown_per_thousand` fürs Buch ist eine Dichte über die Summe der
Kapitel-Token, `token_count` schwankt aber mit der Kapitelteilung desselben Buchs — kürzere
Kapitel drücken über die frühere Summenbildung die Buchzahl nach oben, ohne dass sich am
Buch selbst etwas ändert (`Dorian Gray` auf Sherlock-Kapitelgröße gebracht: 102,4 → 88,2 je
1.000; `Dune`, drei sehr lange Kapitel, kam mit 53,2 „angemessen" heraus, obwohl seine
Abdeckung mit 84,1 % unter Sherlocks 87,3 % liegt — Bericht zu dieser Nachbesserung).
`coverage.share` (E5, tokenbasiert) ist dagegen unabhängig davon, wie das Buch in Kapitel
geteilt ist, und deshalb die Grundlage seit dieser Behebung.

**Die drei Schwellen sind weiterhin eine Vermutung, keine Messung** (bauplan-phase2.md,
E12): „Für die Einordnung … werden vorläufig drei Schwellen gesetzt und als Vermutung
markiert — belastbar wird die Skala erst, wenn sie an drei gelesenen Büchern gegen das
eigene Empfinden gehalten wurde." Dieses Modul markiert sie entsprechend im Namen
(`_GUESSED_...`) und im `DifficultyLevel`-Docstring, nicht mit der REGEL-Marke aus
dokumentation.md §4 — die ist den fünfzehn Regeln vorbehalten, hier gilt keine von ihnen.

Voraussetzungen
---------------
`share` stammt aus `pipeline.BookDifficulty.coverage` oder `pipeline.
ChapterDifficulty.coverage` (`Coverage.share`, E5) — der Anteil bereits verstandener
Wortformen, nicht die Dichte unverstandener Grundformen.

Liefert
-------
`classify_difficulty` ordnet eine solche Abdeckung einer von drei `DifficultyLevel`-Stufen
zu. Wie die Stufe im Deutschen heißt, ist Sache der Oberfläche (`cli.main`, künftig
`gui/`), nicht dieses Moduls — `app/` liefert fertige Werte, keinen Oberflächentext
(Paket-Docstring, `app/__init__.py`, „Liefert").
"""

from __future__ import annotations

import enum


class DifficultyLevel(enum.Enum):
    """Die drei Einordnungsstufen des Schwierigkeitschecks (bauplan-phase2.md AP 7, E12) —
    Vermutung, nicht gemessen, siehe Moduldocstring. `EASY`: die Abdeckung ist hoch, das
    Buch liest sich weitgehend ohne Nachschlagen. `MODERATE`: spürbar Lücken, aber mit
    Vorbereitung machbar — der Regelfall, für den LibreVerbum gebaut ist, und der Bereich,
    in dem die drei gemessenen Bücher mit einer B1-Vorbelegung tatsächlich liegen (siehe
    unten). `HARD`: „zu schwer für dich" im Wortlaut von E12."""

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


# Vermutung, nicht gemessen (E12, siehe Moduldocstring) — ein Schnittpunkt für „leicht"
# oberhalb, einer für „zu schwer" darunter der gemessenen B1-Bandbreite, drei Stufen.
#
# Rezept: pipeline.assess_book gegen tools/sherlock.epub, tools/dorian_gray.epub und
# tools/dune.epub, je einmal mit leerem und einmal mit B1-vorbelegtem Profil
# (pipeline.write_vocabulary_preset(cefr_level=CefrLevel.B1)), .venv/Scripts/python.exe,
# 22./23.09.2026, Bericht zur Nachbesserung der Durchsicht c6f3875.
#
# Gemessene Abdeckung (coverage.share) mit B1-Vorbelegung: Sherlock 87,34 %, Dorian Gray
# 85,89 %, Dune 84,10 % — drei ganz verschiedene Bücher (Kapitelzahl 13/22/4, mittlere
# Kapitellänge 8.000/3.600/66.000 Wortformen) liegen trotzdem alle innerhalb weniger
# Prozentpunkte beieinander, weil B1 (2.000 häufigste Grundformen) in jedem von ihnen einen
# ähnlichen Anteil trifft. Mit leerem Profil liegt Sherlock bei 58,36 % — ein
# Kalibrierdurchlauf ohne jede Vorbelegung ist ohnehin nicht der Fall, für den die
# Einordnung gedacht ist (konzept.md, „Der erste Durchlauf je Buch ist ein
# Kalibrierdurchlauf, kein Lerndurchlauf").
#
# Die Leseforschung (Hu & Nation 2000, zusammengefasst in Nation 2006) nennt für
# fortlaufenden Text rund 95 % Abdeckung als „mit Hilfe lesbar" und rund 98 % als
# „flüssig/ohne Hilfe". Wörtlich übernommen wären diese Schwellen für LibreVerbum
# **praktisch nie erreichbar**: Jedes Buch trägt einen festen Boden an Wortformen ohne
# Wörterbucheintrag (Platzhalter, `uncertain`) — an den drei genannten Büchern 1.179 bis
# 1.876 verschiedene Grundformen, die kein Profil je als „bekannt" ausweisen kann, weil es
# keine Bedeutung gibt, die gebucht werden könnte. Eigens dafür gemessen (rein
# wörterbuchbedingte Deckenwerte, unabhängig vom Profil, `floor_check.py`, Bericht zu
# dieser Nachbesserung): Sherlock 98,07 %, Dorian Gray 97,64 % — selbst ein Leser, der
# **jedes** Wort mit Wörterbucheintrag kennt, käme über diese Werte nicht hinaus, und liegt
# damit knapp unter der „flüssig"-Schwelle der Literatur. Ein B1-Leser (84 bis 87 %) ist von
# dieser Decke so weit entfernt wie von den 95 %/98 % der Literatur selbst entfernt wäre —
# mit den wörtlichen Literaturschwellen fielen alle drei gemessenen Bücher, obwohl
# LibreVerbum genau für diesen Fall gebaut ist (`DifficultyLevel.MODERATE`s Dokstring:
# „der Regelfall"), unter „zu schwer". Die Einordnung wäre dann für den einzigen bisher
# gemessenen Anwendungsfall bedeutungslos.
#
# Die beiden Schnittpunkte unten sind deshalb bewusst niedriger als 95 %/98 % gesetzt —
# nicht an die drei gemessenen Werte selbst angepasst (kein stilles Fitten an die
# Testdaten): Beide Werte sind runde Zehnprozentschritte, die (a) die gesamte gemessene
# B1-Bandbreite (84,1 bis 87,3 %) in die Mitte von MODERATE legen, statt sie an einen ihrer
# Ränder zu drängen, (b) unterhalb der wörterbuchbedingten Deckenwerte (97,6/98,1 %) noch
# echten Spielraum für EASY lassen, und (c) den Kalibrierwert ohne Profil (58,4 %) klar in
# HARD einordnen. Ob sie zutreffen, bleibt offen, bis sie an drei **gelesenen** Büchern
# gegen das eigene Empfinden gehalten wurden (E12) — mit drei nur *gemessenen*, nicht
# gelesenen Büchern ist das hier nicht zu leisten.
_GUESSED_EASY_MIN_COVERAGE = 0.90
_GUESSED_MODERATE_MIN_COVERAGE = 0.75


def classify_difficulty(share: float) -> DifficultyLevel:
    """Ordnet eine Abdeckung (`pipeline.Coverage.share`, E5) einer der drei Stufen zu —
    Vermutung, siehe Moduldocstring und die REGEL-lose Begründung bei den beiden Schwellen
    oben. `>=` an beiden Schnittpunkten: Ein Buch genau auf der Schwelle zählt zur
    leichteren der beiden angrenzenden Stufen, nicht zur schwereren — dieselbe Richtung wie
    zuvor bei der je-1.000-Maßzahl (dort `<=`), hier gespiegelt, weil eine hohe Abdeckung
    „leicht" bedeutet, eine hohe Dichte unbekannter Grundformen dagegen „schwer"."""
    if share >= _GUESSED_EASY_MIN_COVERAGE:
        return DifficultyLevel.EASY
    if share >= _GUESSED_MODERATE_MIN_COVERAGE:
        return DifficultyLevel.MODERATE
    return DifficultyLevel.HARD
