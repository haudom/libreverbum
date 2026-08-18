# LibreVerbum — Nacharbeit

> Stand: 18.08.2026 · Befunde aus dem Bau von T3, T4, T5, T8 und T12, die **nicht** in die
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

Die Stufen und was beim Einfalten drankommt, stehen in dokumentation.md §9, „Die beiden
Arten werden verschieden behandelt". Kurz:

- **Teil A** trägt eine Stufe. Abgearbeitet werden `schwer` und `mittel`; `leicht` bleibt
  liegen und wird spätestens bei T18 eingefaltet oder gestrichen
- **Teil B** trägt keine, weil dort nichts zurückgestellt wird

**Die Stufe vergibt die kuratierende Stelle, nicht der Melder.** Wer eine Beobachtung
meldet, nennt zwei Tatsachen, die er wirklich kennt: was es ihn gekostet hat, und ob dabei
ein falsches Ergebnis hätte durchgehen können. Wie schwer das für das Projekt wiegt, zeigt
sich erst, wenn mehrere Berichte nebeneinander liegen — dokumentation.md §9.

---

# Teil A — Regeln und Arbeitsweise

## A7 — mittel · Die T4-Zeile im Bauplan ist zweideutig

**Beobachtet (Review T4, 17.08.2026).** „zusammenhängende Kandidatenfolgen **und** getrennte
Verb-Partikel-Paare aus der Abhängigkeitsanalyse" lässt sich als „beides aus der Analyse"
lesen, während technik.md §3, „Arbeitsteilung nach der Messung" die zusammenhängenden
ausdrücklich „Wörterbuch + n-Gramm + Filter" zuordnet. Die Prüfspalte nennt dann nur den
getrennten Fall — wer sie als Auftragsumfang liest, baut folgerichtig die Hälfte.

**Kosten:** eine vollständige Reviewrunde plus Nachbesserung. Ein falsches Ergebnis wäre
durchgegangen: 190 von 232 zusammenhängenden Wendungen eines Kapitels entstanden nie, rund
3 % des Mehrwortbestands waren erreichbar — ohne Fehler und ohne Meldung. T7 hätte die
fehlenden Kandidaten nicht vermissen können.

**Vorschlag:** Wo eine Teilaufgabe zwei Wege verlangt, nennt die Prüfspalte **beide**. Zu
entscheiden, ob die T4-Zeile zusätzlich in zwei Teilaufgaben getrennt wird.

## A8 — mittel · Das Tor ist auf den Bauenden geschrieben, nicht auf den Prüfenden

**Beobachtet (Review T8, 17.08.2026).** `ruff format .` und der volle `pytest`-Lauf sind für
einen Prüfer unbrauchbar, solange ein zweiter Bearbeiter im Arbeitsbaum steht: Das erste
formatiert fremde Arbeit mit, das zweite zeigt Rot, das dem anderen gehört — in derselben
Sitzung vorgeführt, vier rote Tests in `test_extraction.py`, Minuten später von selbst grün.
„Grün" ist bei zwei Bearbeitern nur je Datei eine Aussage.

**Vorschlag:** Im Tor aus CLAUDE.md festhalten, dass Prüfende `ruff format --check` und den
dateiweisen Testlauf nehmen; den vollständigen Lauf macht die verkettende Stelle zwischen den
Runden. Das ist die Dokumentfassung des gestrichenen A6, das dasselbe nur als Absprache hielt.

## A9 — leicht · Unversionierte Dateien haben beim Verfälschen kein Netz

**Beobachtet (Review T8, 17.08.2026).** Die Verfälschungsprobe nach dokumentation.md §5 setzt
voraus, dass der Ausgangsstand wiederherstellbar ist. Bei einer noch unversionierten Datei
gibt es dafür kein Git, und `Path.write_text` verwandelte beim Wiederherstellen unter Windows
LF in CRLF — gezeigt hat es allein der Hash-Vergleich, nicht der Augenschein.

**Vorschlag:** Ein Satz in dokumentation.md §5 — wer an einer unversionierten Datei
verfälscht, sichert sie binär und prüft die Wiederherstellung per Hash.

## A10 — leicht · Der EPUB-3-Zweig wird an keiner Fremdquelle geprüft

**Beobachtet (Review T12, 18.08.2026).** In `tools/` liegen nur `sherlock.epub` und
`dorian_gray.epub` — beide EPUB 2.0 mit `toc.ncx` und ohne `nav.xhtml` (nachgeprüft). Der
gesamte EPUB-3-Pfad in `libreverbum/epub.py` (`_read_nav`, `properties="nav"`,
`epub:type`) läuft deshalb nur gegen die selbstgebaute Vorrichtung, nie gegen ein echtes
Buch — genau die Konstellation, vor der dokumentation.md §5 warnt („Die Vorrichtung zeigt,
dass der Code läuft; die Fremdquelle zeigt, ob er stimmt").

**Vorschlag:** keine Codeänderung. Optional der Hinweis an den Nutzer, eine EPUB-3-Datei
aus seinem Bestand nach `tools/` zu legen (laut technik.md §8 sind die beiden dort
gemessenen Manga-Bände 3.0); die Marke `needs_epub` müsste dann um sie erweitert werden.

## A11 — leicht · `_text_of` nimmt nur den ersten Treffer

**Beobachtet (Review T12, 18.08.2026).** `_text_of` in `libreverbum/epub.py` liest mit
`root.find` nur das erste `dc:title` beziehungsweise `dc:creator`. Ist das erste `dc:title`
leer (kommt bei Konvertaten vor, die ein leeres `dc:title` voranstellen und den echten
Titel als zweites führen), bricht `read_structure` mit „nennt keinen Titel" ab, obwohl die
Datei einen hat. Bei mehreren `dc:creator` (Ko-Autoren, Übersetzer) fallen die weiteren
still weg.

**Vorschlag:** `findall` statt `find`, den ersten nichtleeren Text nehmen. Für
`dc:creator` genügt dasselbe — mehrere Autoren zusammenzuführen wäre Vorratsarbeit
(Regel 14), `entities.Book.author` ist ein einzelnes Feld.

> **A6 gestrichen am 17.08.2026** (Parallelität erzeugt Phantomfehler): als Absprache
> erledigt, der Dokumentteil ist in A8 aufgegangen.

---

# Teil B — Nachträge an den Dokumenten

Unstrittig, nur noch nicht getan. Jeweils mit der Messung, auf die sie sich stützen. Ohne
Stufe: Diese Liste wird bei jedem Einfalten auf null gebracht.

## B4 — technik.md §3: Zeilen ohne `lexentry`

**Gemessen:** **46.933 von 157.801 Zeilen (29,7 %)** haben `lexentry = NULL`. Sie können die
Wortart-Zuordnung nicht passieren — über alle betroffenen Zeilen geprüft: **0** hätten es
getan. Das Verhalten ist vertretbar (alle diese Zeilen haben `score ≤ 48`, T7 verwirft sie
ohnehin) und steht seit T5 ausdrücklich in der Abfrage statt als Nebenwirkung.

Zum Umfang, nicht als Fehler: **45.260 von 124.751 Stichwörtern (36,3 %)** haben überhaupt
keine `lexentry`-Zeile und liefern eine leere Liste. Ob eine leere Liste `uncertain` werden
muss, entscheidet **T11**.

## B5 — technik.md §5: der Inhaltswortfilter ist neu

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

## B6 — technik.md §2: `translation` hat keine Wortartspalte

**Gemessen (Review T4, 17.08.2026):** Die Wortart steckt allein im `lexentry`
(`eng/give_up__Verb__1`); die Tabelle `translation` führt keine eigene Spalte dafür, und
**29,7 %** der Zeilen haben `lexentry = NULL` — dieselbe Messung wie B4. Das steht im
Docstring von `dictionary.py`, aber nicht dort, wo technik.md §2 die Quelle beschreibt. Ein
Satz dort spart jedem Prüfer den ersten Fehlversuch.

## B7 — technik.md §3: der `prt`-Weg erreicht 3 % des Mehrwortbestands

**Gemessen (Review T4, 17.08.2026)** gegen `tools/en-de.sqlite3`: 956 verschiedene
Verb-Partikel-Stichwörter gegen 54.085 übrige Mehrwort-Stichwörter, mit `score ≥ 50` 652
gegen 18.709. An `tools/sherlock.txt` (ein Kapitel, 60.000 Zeichen): 232 zusammenhängende
Wörterbuch-Wendungen, davon 40 der Wortarten `Phrase` (691 Zeilen), `Prepositional_phrase`
(638) und `Proverb` (309) — `as a rule`, `at all`, `after all`, `out of the way`, `all right`.

Das ist die Zahl, die die Arbeitsteilung aus §3 belegt: Ohne den n-Gramm-Weg fehlen nicht
Randfälle, sondern der Bestand. Gegengemessen mit dem neuen Code hält der getrennte Anteil
dagegen: Sherlock 24 %, Dorian Gray 22 % — gegen die dokumentierten 21 % und 19 %.

## B9 — `entities.Sense`: was eine Bedeutung ohne `wikdict_`-Felder bedeutet

**Beobachtet (Review T10, 17.08.2026).** Der Docstring sagt, bei einer Wendung ohne
Wörterbucheintrag fehlten alle `wikdict_`-Werte und `uncertain` sei gesetzt. Nirgends steht,
dass das die **einzige** erlaubte Form einer Bedeutung ohne `wikdict_`-Werte ist — und genau
diese Lücke hat der T10-Bau gefüllt, mit einem Platzhalter, der von einer echten
Regel-10-Wendung nicht zu unterscheiden war (`uncertain` ist `compare=False` und hat keine
Schemaspalte, beide bekommen dieselbe `sense`-id).

**Nachzutragen** in technik.md §4 oder im `Sense`-Docstring, ein Satz: Eine `Sense` ohne
`wikdict_`-Felder bedeutet *kein Wörterbucheintrag*, nicht *noch nicht nachgeschlagen*.

## B8 — technik.md §3: die Maße des n-Gramm-Wegs

**Gemessen beim Bau von T4 (17.08.2026)** gegen `tools/en-de.sqlite3`: 22.840 mehrwortige
`written_rep` mit `score ≥ 50`, davon **99,12 % höchstens sechs Wörter** lang — 2 Wörter
18.196 · 3: 2.977 · 4: 1.011 · 5: 289 · 6: 167. Darüber fast nur noch vollständige
`Proverb`-Zeilen bis 26 Wörter, die als Zitat im Fließtext praktisch nicht vorkommen. Daraus
die Obergrenze sechs, die jetzt im Code steht.

**Kandidatenzahl je Kapitel** (60.000 Zeichen aus `tools/sherlock.txt`, echter Lauf):
zusammenhängend **23.437 verschiedene** Kandidaten (26.984 Vorkommen), getrennt 77
verschiedene (93 Vorkommen). Die n-Gramm-Seite bringt also rund **300-mal so viele**
Nachschlagevorgänge wie die `prt`-Seite.

**Folge für T7, offen:** Mit dem Index aus T6 (0,71 ms je Aufruf, technik.md §3, „Nachtrag
17.08.2026") wären 23.437 Einzelabfragen rund **17 s reine Wörterbuchzeit je Kapitel** — gegen
die 1,1 s, mit denen §3 heute rechnet. Einzelabfragen sind für diese Menge die falsche Form;
ob T7 stattdessen mengenweise abfragt, ist bei T7 zu entscheiden und **vorher zu messen**,
nicht zu vermuten.

Dazu ein Nebenbefund für **T7**: Sein Filter `score ≥ 50` löscht 86 der 232 Treffer in
Sherlock, darunter `bring back` (10 Vorkommen), `take up`, `keep out`, `light up` — also genau
die Einträge, die §3 („394 Vorkommen mit Partikel") als `uncertain` behalten will. Der Filter
gehört zum n-Gramm-Weg, nicht zum `prt`-Weg; die zwei Kandidatenarten sind in T7 getrennt zu
behandeln.
