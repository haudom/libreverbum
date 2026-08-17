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
sich erst, wenn mehrere Berichte nebeneinander liegen — siehe A7.

---

# Teil A — Regeln und Arbeitsweise

## A1 — schwer · Die Testvorrichtung aus T2 ist systematisch zu sauber

**Beobachtet.** Drei der schwersten Befunde der Sitzung waren an der Vorrichtung aus T2
**strukturell unsichtbar** und fielen erst gegen `tools/en-de.sqlite3` auf:

| Befund | an der Vorrichtung | an der echten Datei |
|---|---|---|
| `Sense`-Identität allein aus `wikdict_lexentry` | jeder `lexentry` trug genau eine Bedeutung | 22,7 % der Zeilen mit `lexentry` fielen zusammen; `break`/VERB von 31 auf 1 |
| Zeilen ohne `lexentry` | keine vorhanden | 46.933 von 157.801 (29,7 %), still verworfen |
| Sortierung nach `score` | Zeilenreihenfolge entsprach zufällig schon der Sortierung | Test blieb ohne `ORDER BY score DESC` grün |

**Warum das eine Regellücke ist und keine Disziplinlücke.** T2 hat `real_dictionary_path`
und die Marke `needs_dictionary` **genau für diesen Fall gebaut**. T5 hat beides nicht
benutzt — und nichts in der Hausordnung verlangte es. dokumentation.md §5 sagt „wo eine
Regel prüfbar ist, ist sie zu prüfen", aber nirgends steht, *woran* geprüft wird.

**Der Mechanismus ist nicht „echte Daten sind besser".** Er ist: Eine Vorrichtung, die
derselbe Prozess baut wie den Code, trägt dieselben blinden Flecken. Das Mini-Wörterbuch
war sauber, weil sein Erbauer sich eine Wörterbuchzeile als „ein `lexentry`, eine
Bedeutung" vorstellte — und der Code, der darauf zugriff, stellte es sich genauso vor. Die
Vorrichtung hat die Annahme nicht geprüft, sondern bestätigt.

**Das gilt für alle drei Fremdquellen, nicht nur für das Wörterbuch** — belegt, nicht
vermutet: Beim EPUB ist es **schon passiert**. Das T2-Review fand eine Testnavigation, die
von der Lesereihenfolge nicht unterscheidbar war. Damit wäre die Kernregel aus technik.md
§8 — Kapitel kommen aus der Navigation, fehlt sie, gilt jedes Dokument der Lesereihenfolge
als Kapitel, mit Hinweis — an dieser Vorrichtung **nicht prüfbar** gewesen: Eine Umsetzung,
die die Navigation schlicht ignoriert, wäre grün durchgekommen. Dazu kommt, dass die
Entscheidungen 8 und 9 an zwölf echten Dateien gemessen wurden (570 von 570
Inhaltsdokumenten); wer T12 nur gegen die selbstgebaute Datei prüft, prüft nicht die
Entscheidung, auf der T12 beruht.

**Vorschlag.** Zusatz zu dokumentation.md §5, sinngemäß:

> Die Vorrichtung zeigt, dass der Code läuft; die Fremdquelle zeigt, ob er stimmt. Wer eine
> Aussage über den Inhalt einer Fremdquelle prüft, prüft sie zusätzlich gegen das echte
> Gegenüber.
>
> - **Wörterbuch** (`needs_dictionary`) und **EPUB**: feste Gegenstände. Gegen sie lässt
>   sich behaupten — „`watch` als Substantiv liefert vier unterscheidbare Bedeutungen",
>   „diese Datei hat so viele Kapitel". Die zwölf Dateien liegen in `tools/`
> - **Modellserver** (`needs_model`): kein fester Gegenstand. Gegen ein Sprachmodell lässt
>   sich keine Gleichheit behaupten, nur eine Trefferquote messen — und Messungen gehören
>   nach `tools/`, nicht in die Testsuite (`sense_check.py` lebt diese Rollenteilung
>   bereits). Gegen den echten Server gehört stattdessen der **Abgleich der Attrappe**:
>   dass sie in Antwortform, angenommenen Feldern und Fehlerverhalten noch dem echten
>   Server entspricht

**Warum der Modellserver gesondert steht.** Eine Attrappe, die `reasoning_effort: "none"`
klaglos annimmt, während der echte Server das Feld zurückweist, macht Regel 7 unprüfbar —
lautlos, weil alle Tests grün bleiben. Ohne diese Unterscheidung wird die Regel bei T11
falsch angewandt.

**Umfang.** Ein Absatz in dokumentation.md §5. Die betroffenen Tests in `test_dictionary.py`
haben inzwischen `needs_dictionary`-Gegenstücke; die EPUB-Seite ist bei **T12** fällig, der
Attrappenabgleich bei **T11**. Nachzuziehen ist die Regel selbst, damit die Übertragung
nicht jedes Modul neu erfunden wird — das wäre genau der Mechanismus, den A4 beklagt.

## A2 — schwer · „Ein Test gilt erst als Test, wenn er einmal rot war"

**Beobachtet.** Über alle vier Teilaufgaben derselbe wiederkehrende Befund: Tests, die
**auch bei falscher Umsetzung grün bleiben**. Beispiele:

- `assert not has_lemma(occurrences, "Sherlock")` — unerfüllbar, weil Grundformen
  kleingeschrieben werden. Die Zusicherung konnte gar nicht fehlschlagen
- der Sortiertest in T5 — grün ohne `ORDER BY score DESC`
- die Wortartauflösung in T3 — der einzige nichttriviale Zweig, von keinem Test erreicht

**Was nachweislich geholfen hat.** T4 und T8 bekamen den ausdrücklichen Auftrag, ihre
wichtigsten Tests **kaputtzumachen und den roten Lauf vorzuweisen**. Beide haben es getan
und berichtet, welcher Test bei welcher Verfälschung fällt. T4 hat dabei selbst entdeckt,
dass drei seiner Tests rot werden, wenn man die Umsetzung auf die gefilterte Wortliste
umstellt — die Falle, um die es ging. Die Befundlage dieser beiden Aufgaben sieht seitdem
anders aus als die von T3 und T5.

**Vorschlag.** Als Regel nach dokumentation.md §5: Ein neuer Test wird einmal gegen eine
absichtlich falsche Umsetzung gehalten; erst wenn er dabei rot war, gilt er als Test.

**Warum es sich lohnt.** Ersetzt einen Teil der Reviewarbeit durch Mechanik und kostet den
Bauenden wenige Minuten. Die vier Reviews dieser Sitzung haben in **vier von vier** Fällen
echte Defekte gefunden, keine Kosmetik — je mehr davon der Bauende selbst abfängt, desto
billiger wird die Kette.

## A4 — mittel · Regel 14 trennt Struktur nicht von Funktion

**Beobachtet an T8.** „Gebaut wird, was die aktuelle Phase verlangt" ist für Funktionen
eindeutig, für **Struktur** nicht. T8 hat alle sieben Tabellen angelegt, aber nur einen Teil
mit Zugriffsfunktionen versehen, und das so begründet: *„Regel 14 begrenzt den Zugriff,
nicht das Tabellenlayout."*

Die Begründung trägt — ein Schema ist nur als Ganzes stimmig, und Nachrüsten heißt
Migration. Aber sie steht nirgends, also musste der Bearbeiter sie sich selbst zurechtlegen.
Der nächste legt sie sich anders zurecht.

**Vorschlag.** Einen Satz in Regel 14 (dokumentation.md §4), der Struktur von Funktion
trennt: Datenstrukturen dürfen vollständig entstehen, wo Teilstücke später eine Migration
erzwingen würden; Verhalten entsteht erst, wenn es gebraucht wird.

## A5 — mittel · Die Marke `# REGEL` bekommt Konkurrenz

**Beobachtet.** `grep -rn REGEL .` soll die fünfzehn Regeln aus dokumentation.md §4
auflisten. Review-Befunde wollen aber ebenfalls im Code verankert werden. Ein Bearbeiter hat
von sich aus `# (Befund 4, Review Runde 1): …` erfunden — ausdrücklich, um die grep-Ausbeute
sauber zu halten.

Das war die richtige Entscheidung. Sie ist nur nirgends aufgeschrieben, also erfindet der
nächste `# REGEL (Review): …` und die Liste wird unbrauchbar.

**Vorschlag.** Die Form für Befund-Verweise in dokumentation.md §4 festhalten, zusammen mit
dem Satz, warum `REGEL` reserviert bleibt.

## A7 — mittel · schnell · Beobachtungen aus dem Bau haben keinen Rückweg

**Beobachtet.** Was den Bauenden aufhält, erfährt niemand außer der verkettenden Stelle —
und nur, wenn er es zufällig erwähnt. In dieser Sitzung haben **drei Bearbeiter unabhängig
voneinander** herausgefunden, dass `pytest` blank nicht läuft (siehe A3); keiner konnte das
irgendwo hinterlegen. Ein Bearbeiter legte eine `agent_status.json` im Projektverzeichnis
ab — aufgefallen ist das erst einem Reviewer, der zufällig `git status` las.

**Vorschlag.** Jeder Auftrag bekommt am Ende einen Pflichtabschnitt:

> ## Beobachtungen zum Ablauf
> Was hat dich aufgehalten, in die Irre geführt oder zu einer Entscheidung gezwungen, die
> eigentlich woanders hingehört? Je Punkt eine Zeile, dazu: was es dich gekostet hat, und ob
> dabei ein falsches Ergebnis hätte durchgehen können. Sonst „nichts".

Die Frage ist absichtlich eng gestellt. Offen gefragt („hast du Verbesserungsvorschläge?")
kommen allgemeine Ratschläge zurück, die niemand braucht.

**Keine gemeinsame Datei, in die alle schreiben.** Es laufen dauernd zwei Bearbeiter
parallel; beim Anhängen an dieselbe Datei gehen Einträge verloren, ohne dass es jemand
merkt. Der Bericht ist der Kanal, die Kuration faltet ein. Reicht das nicht, ist die
nächste Stufe ein **Verzeichnis** mit einer Datei je Beobachtung — konfliktfrei, weil jeder
in seine eigene schreibt — und kein zweiter Sammeltext.

**Der Punkt, an dem so etwas gewöhnlich stirbt**, ist nicht das Sammeln, sondern das
Einfalten. Deshalb an die **Tore** aus `bauplan.md` hängen: Beim Abschluss jedes Tors wird
diese Liste durchgegangen, Teil B eingefaltet, Teil A entschieden. Das ist dasselbe
Verfahren, das dokumentation.md §7 unter „Am Phasenende einfalten" für den Bauplan
vorsieht.

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

## B1 — mittel · technik.md §3: das Nachschlagen ist der Engpass

**Gemessen an `tools/en-de.sqlite3`:** **27,7 ms je Aufruf** von `candidates()`, davon 26 ms
Abfrage und 0,3 ms Verbindungsaufbau. Die Datei hat **keinen einzigen Index**
(`sqlite_master` liefert leer), der Abfrageplan ist `SCAN translation` +
`USE TEMP B-TREE FOR ORDER BY`. Ein Kapitel mit 1.592 Grundformen kostet damit rund
**44 Sekunden reine Wörterbuchzeit**.

Das ist der von Regel 14 verlangte **gemessene Anlass**. Die Abhilfe ist ein Index oder eine
Abfrage je Kapitel — **kein Zwischenspeicher**. Sie gehört zu **T6** (Erstbezug), weil dort
die Datei ohnehin einmalig angefasst wird, und nicht zu T5.

## B2 — mittel · technik.md §6: mypy geht streng mit den spaCy-Typen durch

Das war laut technik.md §6 ungeprüft und der ausdrückliche Grund, warum `bauplan.md` mit den
Strängen A und B beginnen wollte. **Antwort: ja.** spaCy liefert `py.typed` mit; `mypy`
löst `token.pos_`, `token.lemma_` und `sent.text` zu `str` und `token.is_alpha` zu `bool`
auf (mit `reveal_type` geprüft). `extraction.py` ist typrein.

**Folge:** Die Ausnahme `ignore_missing_imports` für `spacy.*` in `pyproject.toml` ist
gegenstandslos und kann entfernt werden — vor dem Entfernen einmal `mypy` laufen lassen.

## B3 — mittel · technik.md §3: spaCys Wortarten und WikDicts sind nicht deckungsgleich

**Gemessen:** **29 von 1.592 Grundformen (1,8 %)** stehen im Wörterbuch, bekommen aber eine
leere Auswahlliste, weil die Taxonomien auseinanderlaufen — WikDict führt `such`, `many`,
`few`, `least`, `less` als `Determiner`, spaCy als `ADJ`.

Der Nutzer sieht dann „kein Wörterbucheintrag" bei einem Wort, das drinsteht; T11 markiert
es `uncertain` und **verdeckt damit einen Zuordnungsfehler als Modellunsicherheit**. Als
offener Punkt festhalten, mit der Zahl.

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
