# LibreVerbum — Nacharbeit

> Stand: 17.08.2026 · Befunde aus dem Bau von T3, T4, T5 und T8, die **nicht** in die
> jeweilige Teilaufgabe gehören. Zwei Arten: Änderungen an den Regeln und der Arbeitsweise
> (Teil A), Nachträge an den Dokumenten aus gemessenen Ergebnissen (Teil B).
>
> Dieses Dokument ist eine Arbeitsliste, kein Entscheidungsdokument. Es begründet nichts
> neu, sondern verweist. Ist ein Punkt abgearbeitet, wird er hier gestrichen; ist die Liste
> leer, fällt die Datei weg.
>
> **Nichts hiervon ist entschieden.** Teil A sind Vorschläge, die eine Zustimmung brauchen,
> weil sie die Hausordnung ändern. Teil B ist unstrittig und nur noch nicht getan.

## Gewichtung

Die Stufe beantwortet **eine** Frage: *Was wäre passiert, wenn es niemand bemerkt hätte?*

| Stufe | Folge, wenn unbemerkt |
|---|---|
| **schwer** | Ein falsches Ergebnis geht durch, ohne aufzufallen — der leise Fehlschlag. Oder es geht etwas verloren, das nicht wiederherstellbar ist |
| **mittel** | Das Ergebnis stimmt, kostet aber spürbar: verdoppelte Arbeit, zwei Bearbeiter lösen dasselbe verschieden, oder es dauert unzumutbar lange |
| **leicht** | Reibung ohne Folge |

Dahinter steht `· schnell`, wo ein Punkt in einer Viertelstunde erledigt ist. Innerhalb
einer Stufe wird das Schnelle zuerst gemacht — A3 ist der Fall, der das lohnt.

**Die Stufe vergibt die kuratierende Stelle, nicht der Melder.** Wer eine Beobachtung
meldet, nennt zwei Tatsachen, die er wirklich kennt: was es ihn gekostet hat, und ob dabei
ein falsches Ergebnis hätte durchgehen können. Wie schwer das für das Projekt wiegt, zeigt
sich erst, wenn mehrere Berichte nebeneinander liegen — dokumentation.md §9.

---

# Teil A — Regeln und Arbeitsweise

## A6 — leicht · Parallelität erzeugt Phantomfehler

**Beobachtet.** Der T3-Bearbeiter meldete zwei repoweite Fehlschläge, die es nicht gab — er
hatte den Zwischenstand des gleichzeitig arbeitenden T5-Bearbeiters erwischt. Kein Schaden,
aber verbrannter Kontext; im schlechteren Fall repariert ein Agent etwas, das gerade ein
anderer korrekt baut.

**Erledigt ohne Dokumentänderung.** Bauende prüfen ab jetzt torscharf nur ihre eigenen
Dateien; den vollständigen Lauf macht die verkettende Stelle zwischen den Runden. Steht hier
nur zur Kenntnis.

---

# Teil B — Nachträge an den Dokumenten

Unstrittig, nur noch nicht getan. Jeweils mit der Messung, auf die sie sich stützen.

## B4 — leicht · technik.md §3: Zeilen ohne `lexentry`

**Gemessen:** **46.933 von 157.801 Zeilen (29,7 %)** haben `lexentry = NULL`. Sie können die
Wortart-Zuordnung nicht passieren — über alle betroffenen Zeilen geprüft: **0** hätten es
getan. Das Verhalten ist vertretbar (alle diese Zeilen haben `score ≤ 48`, T7 verwirft sie
ohnehin) und steht seit T5 ausdrücklich in der Abfrage statt als Nebenwirkung.

Zum Umfang, nicht als Fehler: **45.260 von 124.751 Stichwörtern (36,3 %)** haben überhaupt
keine `lexentry`-Zeile und liefern eine leere Liste. Ob eine leere Liste `uncertain` werden
muss, entscheidet **T11**.

## B5 — leicht · technik.md §5: der Inhaltswortfilter ist neu

Seit dem 17.08.2026 kommen nur noch `NOUN`, `VERB`, `ADJ`, `ADV`, `INTJ` in die Wortliste;
`PROPN` wird weiterhin gesondert **je Vorkommen** behandelt (Regel 12). Vorher wurde nur
`AUX` ausgesteuert, wodurch `the`, `his` und `by` in der Triage standen.

**Gemessen an `tools/sherlock.txt`:** 111 Grundformen fallen weg, angeführt von `the` (178),
`of` (125), `and` (102), `a` (96), `to` (91). Betroffene Wortarten: `PRON` 548, `ADP` 407,
`DET` 340, `CCONJ` 134, `SCONJ` 99, `PART` 80, `NUM` 31, `X` 1. Stichprobe der seltensten
Wegfälle (`nothing`, `anything`, `herself`, `another`, `fifty`, `outside`): nur Funktions-
und Zahlwörter, nichts Lernbares.

Der Filter ist zugleich der Grund, warum **T4 auf der Abhängigkeitsanalyse arbeiten muss**
und nicht auf der Wortliste: Die Partikel der getrennten Verb-Partikel-Paare sind `ADP` und
`PART` und damit aus der Liste verschwunden.
