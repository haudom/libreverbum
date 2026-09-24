"""Einordnung des Buch-Schwierigkeitschecks — die drei Schwellenworte aus E12, dazu die
Umrechnung der Abdeckung in „unbekannte Wörter je Seite" (Entscheidung B, E12).

Aufgabe
-------
`libreverbum.pipeline.assess_book` liefert Zahlen (`coverage`), keine Worte — „ca. 14
unbekannte Wörter pro Seite, zu schwer für dich" (konzept.md, „Phase 2") ist eine
Einordnung und eine Umrechnung für die Anzeige, keine Messung, und liegt deshalb hier statt
im Kern (bauplan-phase2.md AP 7: „Schwellen liegen in `app/`, nicht im Kern"; technik.md
§14, E4: was der Kern nicht kennen darf, aber beide Oberflächen brauchen, gehört nach
`app/`).

**Die Maßzahl der Einordnung ist die Abdeckung, nicht mehr „unbekannte Grundformen je
1.000"** (Nachbesserung der Durchsicht c6f3875, Befund 2, Entscheidung Dominiks
23.09.2026, E12): Die frühere Dichte war eine Rechnung über die Summe der Kapitel-Token
und schwankte deshalb mit der Kapitelteilung desselben Buchs — kürzere Kapitel drückten
über die frühere Summenbildung die Buchzahl nach oben, ohne dass sich am Buch selbst etwas
änderte (`Dorian Gray` auf Sherlock-Kapitelgröße gebracht: 102,4 → 88,2 je 1.000; `Dune`,
drei sehr lange Kapitel, kam mit 53,2 „angemessen" heraus, obwohl seine Abdeckung mit
84,1 % unter Sherlocks 87,3 % liegt — Bericht zur Nachbesserung der Durchsicht c6f3875).
Eine zweite, unabhängige Abhängigkeit derselben Dichte — diesmal von der **Buchlänge**,
nicht von der Kapitelteilung — fiel erst in der folgenden Durchsicht auf (mittel-Befund 1,
Durchsicht 3b1e201): Kumulativ an `tools/sherlock.epub` gemessen (B1-Vorbelegung, Bericht
zu dieser Nachbesserung) fällt der Wert von 88,2 (nach dem ersten Kapitel mit Text) über
77,0, 69,8 … auf 41,9 (nach allen 13); die Vereinigung unbekannter Grundformen wächst mit
jedem weiteren Kapitel unterproportional (spätere Kapitel wiederholen überwiegend schon
gesehene Grundformen), `token_count` dagegen linear. `coverage.share` (E5, tokenbasiert)
ist von beidem unabhängig und deshalb die Grundlage seit der ersten dieser beiden
Behebungen.

**Die drei Schwellen sind weiterhin eine Vermutung, keine Messung** (bauplan-phase2.md,
E12): „Für die Einordnung … werden vorläufig drei Schwellen gesetzt und als Vermutung
markiert — belastbar wird die Skala erst, wenn sie an drei gelesenen Büchern gegen das
eigene Empfinden gehalten wurde." Dieses Modul markiert sie entsprechend im Namen
(`_GUESSED_...`) und im `DifficultyLevel`-Docstring, nicht mit der REGEL-Marke aus
dokumentation.md §4 — die ist den fünfzehn Regeln vorbehalten, hier gilt keine von ihnen.
Dieselbe Markierung trägt die Seitenlänge unten, aus demselben Grund.

Voraussetzungen
---------------
`share` stammt aus `pipeline.BookDifficulty.coverage` oder `pipeline.
ChapterDifficulty.coverage` (`Coverage.share`, E5) — der Anteil bereits verstandener
Wortformen, nicht die Dichte unverstandener Grundformen.

Liefert
-------
`classify_difficulty` ordnet eine solche Abdeckung einer von drei `DifficultyLevel`-Stufen
zu. `unknown_words_per_page` rechnet dieselbe Abdeckung in eine Anzeigezahl um — „ca. N
unbekannte Wörter je Seite" (konzept.md, „Phase 2"), an einer geschätzten Seitenlänge
gemessen, nicht an einer echten EPUB-Seite (die es dort nicht gibt, E12, „Schwierigkeitscheck:
welche Maßzahl, welche Worte?"). Wie die Stufe und die Umrechnung im Deutschen heißen, ist
Sache der Oberfläche (`cli.main`, künftig `gui/`), nicht dieses Moduls — `app/` liefert
fertige Werte, keinen Oberflächentext (Paket-Docstring, `app/__init__.py`, „Liefert").
"""

from __future__ import annotations

import enum


class DifficultyLevel(enum.Enum):
    """Die drei Einordnungsstufen des Schwierigkeitschecks (bauplan-phase2.md AP 7, E12) —
    Vermutung, nicht gemessen, siehe Moduldocstring. `EASY`: die Abdeckung ist hoch, das
    Buch liest sich weitgehend ohne Nachschlagen. `MODERATE`: spürbar Lücken, aber mit
    Vorbereitung machbar — der Regelfall, für den LibreVerbum gebaut ist. `HARD`: „zu
    schwer für dich" im Wortlaut von E12.

    Mit den Schnittpunkten unten (92 %/86 %, seit der Nachbesserung der Durchsicht
    3b1e201, Entscheidung A) liegt von den drei gemessenen Büchern nur Sherlock mit einer
    B1-Vorbelegung in `MODERATE` (87,34 %) — Dorian Gray (85,89 %) und Dune (84,10 %)
    fallen knapp darunter in `HARD` (siehe unten, „Warum 90 %/75 % nicht taugte")."""

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


# Vermutung, nicht gemessen (E12, siehe Moduldocstring) — ein Schnittpunkt für „leicht"
# oberhalb, einer für „zu schwer" darunter, drei Stufen.
#
# Rezept: pipeline.assess_book gegen tools/sherlock.epub, tools/dorian_gray.epub und
# tools/dune.epub, je einmal mit leerem und einmal mit vorbelegtem Profil
# (pipeline.write_vocabulary_preset), .venv/Scripts/python.exe, 22./23.09.2026 und
# 23.09.2026 (Nachbesserung Durchsicht 3b1e201), Berichte zu beiden Nachbesserungen.
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
# Wörterbucheintrag (Platzhalter, `uncertain`) — Vereinigung, nicht Summe über Kapitel
# (Befund 5, Nachbesserung Durchsicht 3b1e201; die frühere Zahl „1.179 bis 1.876" war eine
# fehlerhafte Kapitelsumme derselben Fehlerfamilie wie Befund 3, Durchsicht c6f3875):
# Sherlock 742, Dorian Gray 714, Dune 1.593 verschiedene Grundformen, die keine Vorbelegung
# je als „bekannt" ausweisen kann — `pipeline.write_vocabulary_preset` bucht nur echte
# Wörterbuchbedeutungen, nie den `uncertain`-Platzhalter (dessen eigener Docstring: „ein
# uncertain-Eintrag darf nie als bekannt gebucht werden").
#
# Nachtrag 24.09.2026 (Nachbesserung Durchsicht 79b4479, Befund D2, dokumentation.md §7 —
# die vorige Fassung dieses Absatzes behauptete das allgemeiner: "die kein Profil je als
# 'bekannt' ausweisen kann". Das stimmt nur für die Vorbelegung, nicht fürs Profil
# insgesamt, und wurde deshalb oben schon berichtigt statt nur ergänzt (dokumentation.md §7:
# "der gültige Stand steht immer oben"). Über die Triage ist es anders: `pipeline.
# _resolve_sense` liefert für einen Eintrag, dessen `candidates` nur aus dem Platzhalter
# besteht, genau diesen Platzhalter als "aufgelöste" Bedeutung zurück, ohne Modellaufruf
# (`_resolve_sense`s Docstring); markiert der Nutzer ihn in der Triage als "kenne ich",
# bucht `cli.interaction` (`ensure_chapter_row`/`_record`, `Origin.TRIAGE`) ihn wie jede
# andere Bedeutung — derselbe Vorfilter (`_all_candidates_known`) erkennt ihn danach als
# bekannt, wie `run_chapter`s Moduldocstring, letzter Absatz, es für genau diesen Fall
# vorsieht. Die Deckenwerte unten (98,07 % usw.) gelten deshalb nur für ein Profil ohne
# jede Triage-Buchung dieser Platzhalter, nicht für ein gelesenes Buch: Gemessen an
# Sherlock Kapitel 2 (Bericht zu dieser Nachbesserung) hebt das Buchen aller dort
# auftretenden Platzhalter als "kenne ich" die Abdeckung von 86,86 % auf 89,09 %, die
# unbekannten Grundformen sinken von 763 auf 644 — nach einigen Triage-Durchläufen wächst
# die Abdeckung jedes gemessenen Buchs um rund zwei Prozentpunkte (Dorian Gray kippt damit
# von `HARD` nach `MODERATE`). Die Schwellen unten bleiben trotzdem unverändert
# (Entscheidung Dominiks, Nachbesserung Durchsicht 79b4479): Sie sind Vermutung und werden
# erst an gelesenen, nicht nur gemessenen Büchern kalibriert — diese künftige Kalibrierung
# muss die Triage-Verschiebung mit einrechnen, nicht die hier genannten Werte selbst.
#
# Eigens dafür gemessen (rein wörterbuchbedingte Deckenwerte, unabhängig vom Profil,
# Bericht zur Nachbesserung der Durchsicht 3b1e201): Sherlock 98,07 %, Dorian Gray 97,64 %,
# Dune 97,43 % — selbst ein Leser, der **jedes** Wort mit Wörterbucheintrag kennt, käme
# über diese Werte nicht hinaus, und liegt damit knapp unter der „flüssig"-Schwelle der
# Literatur. Ein B1-Leser (84 bis 87 %) ist von dieser Decke so weit entfernt wie von den
# 95 %/98 % der Literatur selbst entfernt wäre — mit den wörtlichen Literaturschwellen
# fielen alle drei gemessenen Bücher, obwohl LibreVerbum genau für diesen Fall gebaut ist
# (`DifficultyLevel.MODERATE`s Dokstring: „der Regelfall"), unter „zu schwer". Die
# Einordnung wäre dann für den einzigen bisher gemessenen Anwendungsfall bedeutungslos.
#
# Warum 90 %/75 % nicht taugte (Entscheidung Dominiks 23.09.2026, Nachbesserung der
# Durchsicht 3b1e201): Mit diesen Schwellen unterschied die Einordnung das **Profil**, nicht
# das **Buch** — alle drei gemessenen Bücher (87,34 %/85,89 %/84,10 %) fielen bei einer
# B1-Vorbelegung unter `MODERATE`, weil B1 selbst so viel Boden mitbringt, dass jedes der
# drei Bücher komfortabel darüberlag; ein Nutzer hätte aus der Einordnung also gelernt,
# welches Sprachniveau er sich vorbelegt hat, nicht, ob das konkrete Buch für ihn angemessen
# ist. Zur Probe wurde Sherlock zusätzlich mit den vier übrigen Vorbelegungsstufen gemessen
# (Rezept oben): A1 77,58 %, A2 82,18 %, B1 87,34 %, B2 90,80 %, C1 92,52 % — eine
# Einordnung, die selbst diese Spannweite eines einzigen Buchs nicht in mehr als eine Stufe
# auflöst, sagt wenig über das Buch.
#
# Die Schnittpunkte unten (92 %/86 %) sind bewusst so gewählt, dass sie diese Spannweite
# auflösen — nicht an die drei Buchmessungen selbst gefittet, sondern an Sherlocks eigener
# Stufenleiter über die fünf Vorbelegungen: 86 % liegt zwischen Sherlocks A2 (82,18 %) und
# B1 (87,34 %), 92 % zwischen dessen B1 und C1 (92,52 %), sodass B1 (der für LibreVerbum
# namengebende Regelfall) knapp in `MODERATE` fällt, B2 (90,80 %) ebenfalls, C1 dagegen in
# `EASY` kippt. Damit ergibt sich an den drei gemessenen Büchern mit B1-Vorbelegung: nur
# Sherlock `MODERATE`, Dorian Gray und Dune `HARD` — ein Ergebnis, das zwischen den drei
# Büchern unterscheidet, wo 90 %/75 % es nicht tat. Ob die Schwellen selbst zutreffen,
# bleibt offen, bis sie an drei **gelesenen** Büchern gegen das eigene Empfinden gehalten
# wurden (E12) — mit nur *gemessenen*, nicht gelesenen Büchern ist das hier nicht zu
# leisten; die Schwellen werden deshalb ausdrücklich nicht an diese Messung selbst
# angepasst (siehe Bericht zu dieser Nachbesserung, „Passe die Schwellen nicht an die
# Messung an").
_GUESSED_EASY_MIN_COVERAGE = 0.92
_GUESSED_MODERATE_MIN_COVERAGE = 0.86


def classify_difficulty(share: float) -> DifficultyLevel:
    """Ordnet eine Abdeckung (`pipeline.Coverage.share`, E5) einer der drei Stufen zu —
    Vermutung, siehe Moduldocstring und die REGEL-lose Begründung bei den beiden Schwellen
    oben. `>=` an beiden Schnittpunkten: Ein Buch genau auf der Schwelle zählt zur
    leichteren der beiden angrenzenden Stufen, nicht zur schwereren — dieselbe Richtung wie
    zuvor bei der je-1.000-Maßzahl (dort `<=`), hier gespiegelt, weil eine hohe Abdeckung
    „leicht" bedeutet, eine hohe Dichte unbekannter Grundformen dagegen „schwer".

    **Gerundet auf dieselbe Stelle wie die Anzeige, bevor eingeordnet wird** (Befund D5,
    Nachbesserung Durchsicht 79b4479, 24.09.2026): Ohne diese Rundung widersprechen sich
    Anzeige und Einordnung an der Schwelle — `cli._format_decimal(share * 100, ndigits=1)`
    zeigt 0,85996 als „86,0 %", `classify_difficulty` ordnete den ungerundeten Wert bisher
    aber unter `_GUESSED_MODERATE_MIN_COVERAGE` (0,86) als `HARD` ein: „86,0 % — zu schwer
    für dich" auf derselben Zeile. Gerundet wird auf ein Zehntelprozent (`round(share * 100,
    1) / 100`), exakt die Stelle, auf die `_format_decimal` rundet — nicht auf die Schwelle
    selbst, die ihre volle Genauigkeit behält, und nicht in der Anzeige (die bleibt
    unverändert), sondern hier, einmal, bevor verglichen wird."""
    rounded_share = round(share * 100, 1) / 100
    if rounded_share >= _GUESSED_EASY_MIN_COVERAGE:
        return DifficultyLevel.EASY
    if rounded_share >= _GUESSED_MODERATE_MIN_COVERAGE:
        return DifficultyLevel.MODERATE
    return DifficultyLevel.HARD


# Vermutung zur Seitengröße, nicht gemessen (E12, Entscheidung B, Nachbesserung der
# Durchsicht 3b1e201, 23.09.2026) — eine Normseite (Manuskriptseite) trägt grob 250 bis
# 300 Wörter; das EPUB kennt keine Seite (E12, „Schwierigkeitscheck: welche Maßzahl, welche
# Worte?"), diese Zahl ist deshalb eine Umrechnungsgröße für die Anzeige, keine Messung an
# einem echten Layout — dieselbe Lage wie bei den beiden Schwellen oben, dieselbe
# REGEL-lose Markierung im Namen statt der REGEL-Marke aus dokumentation.md §4.
_GUESSED_PAGE_LENGTH_WORD_FORMS = 300


def unknown_words_per_page(share: float) -> float:
    """Rechnet eine Abdeckung (`pipeline.Coverage.share`, E5 — Kapitel wie Buch) in
    „unbekannte Wörter je Seite" um: `(1 − share) × _GUESSED_PAGE_LENGTH_WORD_FORMS`
    (Entscheidung B, E12, Nachbesserung der Durchsicht 3b1e201) — ersetzt die vorherige
    Maßzahl „unbekannte Grundformen je 1.000 Wortformen"
    (`pipeline.ChapterDifficulty`/`BookDifficulty`, früher `unknown_per_thousand`), die
    sowohl an der Kapitelteilung (Befund 2, Durchsicht c6f3875) als auch an der Buchlänge
    (mittel-Befund 1, Durchsicht 3b1e201) hing. `share` selbst hängt an keinem von beidem
    (`Coverage`s Docstring, E5), die Umrechnung erbt diese Eigenschaft, weil sie nur mit
    einer Konstante multipliziert.

    Bei Sherlock mit B1-Vorbelegung (87,34 % Abdeckung, Bericht zu dieser Nachbesserung)
    ergibt das rund 38 unbekannte Wörter je Seite — dieselbe Größenordnung wie die im
    Konzept genannten „ca. 14 unbekannte Wörter pro Seite" (konzept.md, „Phase 2"), auf
    derselben geschätzten Seitenlänge, nicht auf einer gemessenen.

    Kapitel und Buch benutzen dieselbe Umrechnung (Auftragstext: „Einheitlich ist besser
    als zwei Maßzahlen nebeneinander") — der Aufrufer übergibt `chapter.coverage.share`
    beziehungsweise `book.coverage.share`, diese Funktion unterscheidet beide nicht."""
    return (1 - share) * _GUESSED_PAGE_LENGTH_WORD_FORMS
