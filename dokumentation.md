# LibreVerbum — Dokumentation und Schreibweise

> Stand: 12.08.2026 · Ergänzt [konzept.md](konzept.md) (*was*) und
> [technik.md](technik.md) (*womit*). Hier steht, **wie** geschrieben und dokumentiert wird.

## Grundsatz

> Die Dokumente beantworten **warum**. Der Code beantwortet **was und wie**.
> Wo der Code das Warum braucht, **verweist** er darauf — er schreibt es nicht ab.

Ein Verweis wie `# siehe technik.md §3, „Datenfalle"` bleibt richtig, wenn die Begründung
dort überarbeitet wird. Ein abgeschriebener Absatz wird still falsch.

---

## 1. Sprachregel

> **Was der Übersetzer liest, ist englisch. Was ein Mensch in Sätzen liest, ist deutsch.**

| Englisch | Deutsch |
|---|---|
| Bezeichner, Dateinamen, Tabellen- und Spaltennamen | Docstrings, Kommentare, Commit-Nachrichten |
| | Oberflächentexte, Fehlermeldungen, Protokollausgaben |

**Namen aus fremden Quellen werden nie übersetzt**: `token.lemma_`, `token.pos_`, die
WikDict-Spalten `sense`, `score`, `lexentry`, `written_rep` sowie die Begriffe der
EPUB-Norm (`spine`, `manifest`, `epub:type`). Eine Übersetzung erzeugte zwei Namen für
dasselbe Ding — die Verwechslung, die laut `technik.md` §3 schon einmal zu falschen
Messergebnissen geführt hat.

> Eigene Felder mit einer **Momentaufnahme** aus WikDict tragen das Präfix `wikdict_`
> (`wikdict_sense`, `wikdict_score`). So bleibt sichtbar, was eigener Bestand ist und was
> aus einer austauschbaren Fremdquelle stammt — vgl. Regel 3.

**Keine Ausnahmen.** Der Ordner `werkzeuge/` widersprach dieser Regel und heißt ab dem
12.08.2026 `tools/`, die Skripte darin ebenso englisch. Grund: Wer nach vorhandenem
Bestand arbeitet — Mensch wie Modell — folgt dem, was im Repository steht, nicht dem,
was hier gefordert wird. Eine vom eigenen Bestand widerlegte Regel gilt faktisch nicht.

### Folge für das Schema

Die Tabellen heißen im Schema englisch. Die deutschen Namen bleiben die Begriffe der
Prosa und gelten unverändert weiter:

| Prosa | Code und Schema |
|---|---|
| `buch`, `kapitel` | `book`, `chapter` |
| `lemma` | `lemma` |
| `bedeutung` | `sense` |
| `vorkommen` | `occurrence` |
| `ereignis` | `event` |
| `karte` | `card` |

Achtung bei `sense`: Die eigene Tabelle ist die **Bedeutung als Gegenstand**, WikDicts
`sense` nur ein **englischer Kurztext** — deshalb `wikdict_sense` für dessen Feld.

---

## 2. Begriffe

Verbindlich, damit nicht „Grundform", „Lemma" und „Basisform" nebeneinander entstehen.

| Deutsch | Code |
|---|---|
| Grundform, Lemma | `lemma` |
| Wortart | `pos` |
| Wortform, Beugungsform | `word_form` |
| Bedeutung | `sense` |
| Belegsatz | `example_sentence` |
| Vorkommen, Häufigkeit | `occurrence`, `frequency` |
| Eigenname | `proper_noun` |
| Mehrwortausdruck, Wendung | `multiword_expression` / `mwe` |
| Wortschatzextraktion | `extraction` |
| Profil, Kenntnisstand | `profile`, `knowledge_state` |
| bekannt / lernt / zurückgestellt / vergessen | `known` / `learning` / `deferred` / `forgotten` |
| Herkunft und Zeitpunkt (einer Kenntnisangabe) | `origin`, `timestamp` |
| unbekannt / bekannt / neue Bedeutung eines bekannten Wortes (Abgleich Kapitelwortschatz ↔ Profil) | `unknown` / `known` / `new_meaning_of_known_word` (`VocabularyStatus`) |
| Triage, Sammelaktion, Wortobergrenze | `triage`, `bulk_mark`, `word_limit` |
| Wörterbuch, Nachschlagen | `dictionary`, `lookup` |
| Auswahlliste, Kandidat | `candidate` |
| Übersetzung | `translation` |
| Karte, Deck, Kartenrichtung, Lückentext | `card`, `deck`, `card_direction`, `cloze` |
| Kartenvorlage (genankis `Model` — „Modell" bleibt dem Sprachmodell vorbehalten, technik.md §3) | `note_model` |
| Druckausgabe | `printout` |
| unsicher (markierter Eintrag) | `uncertain` |
| Gegenstand des Kernablaufs | `entity` |
| Durchlauf, Verkettung der Schritte | `pipeline` |
| Lesereihenfolge, Manifest (EPUB) | `spine`, `manifest` |
| Inhaltsverzeichnis einer Datei | `navigation` |
| Gliederungsebene (in der Navigation) | `level` |
| Hinweis (z. B. bei fehlender Navigation) | `notice` |
| Datenverzeichnis | `data_dir` |
| Einstellungen | `config` |

Neue Begriffe kommen hierher, **bevor** der erste Bezeichner damit entsteht.

---

## 3. Modul-Docstring

**Verbindlich sind zwei Abschnitte: „Voraussetzungen" und „Liefert".** *Aufgabe* und
*Regeln* sind freiwillig und nur zu schreiben, wenn sie etwas sagen, das nicht schon aus
Modulname und Signaturen hervorgeht. Ein Gerüst mit Pflichtabschnitten wird gefüllt,
auch wenn nichts zu sagen ist — die kürzere Pflicht ist deshalb die wirksamere.

```python
"""Wortschatzextraktion — Kapiteltext zu Grundformen.

Aufgabe
-------
Schritt 2 des Kernablaufs (konzept.md): Tokenisierung, Wortart, Lemmatisierung,
Eigennamenfilter, Häufigkeiten, Belegsätze.

Voraussetzungen
---------------
Erwartet Fließtext ohne Inhaltsverzeichnis, Impressum und Fußnoten. Das trennt
der EPUB-Leser, nicht dieses Modul.

Liefert
-------
Grundformen mit Wortart und Belegsatz. Im Wörterbuch wird hier **nicht**
nachgeschlagen — das tut `dictionary.py`.

Regeln
------
Reihenfolge Wortart → Grundform → Nachschlagen ist verbindlich. Begründung:
technik.md, „Warum die Reihenfolge zwingend ist".
"""
```

**Voraussetzungen** ist der wichtigste Abschnitt — der `saw`-Fehler ist eine verletzte
Vorbedingung. **Liefert** sagt auch, was das Modul *nicht* tut; nur so hält die
Architekturregel aus §1 (Kern ohne Bezug zur Oberfläche).

Funktions-Docstrings: ein Satz, dann nur, was nicht aus der Signatur hervorgeht —
Vorbedingungen, Randfälle, Begründungen. Keine Parameterlisten, die Typannotationen
abschreiben. Für `tools/` gilt weiter das dortige Muster *Hintergrund / Verfahren /
Aufruf*.

---

## 4. Regel-Kommentare

Die einzige bewusste Redundanz zum Dokument — dort, wo die Verletzung verlockend und der
Schaden unsichtbar ist. Marker, Quelle, zwei bis vier Zeilen Begründung:

```python
# REGEL (technik.md §3, „Datenfalle"): Zeilen ohne sense-Text nicht wegfiltern.
# 36 % aller Zeilen, systematisch die Hauptbedeutungen (watch → Uhr).
# Wer sie entfernt, erzeugt scheinbare Wörterbuchlücken.
rows = cursor.fetchall()  # bewusst ungefiltert
```

`grep -rn REGEL .` listet damit alle heiklen Stellen auf.

Quellenangaben ohne Dateinamen meinen technik.md.

**Die Marke `REGEL` ist für die fünfzehn Regeln reserviert.** Auch ein Befund aus einer
Durchsicht will im Code verankert werden — bekäme er dieselbe Marke, listete `grep` bald
alles auf und damit nichts. Er trägt deshalb seine eigene Form, im Kommentar wie am Anfang
eines Test-Docstrings:

```python
# (Befund 4, Review Runde 1): Grundformen werden kleingeschrieben (Regel 12), eine
# Zusicherung auf „Sherlock" könnte also gar nicht fehlschlagen.
```

Der Unterschied ist nicht Formalie: Eine Regel gilt für das ganze Projekt, ein Befund
erklärt **diese eine Stelle** und wird mit ihr hinfällig.

| # | Regel | Quelle |
|---|---|---|
| 1 | Zeilen ohne `sense`-Text gehören **immer** in die Auswahlliste, nach `score` absteigend | §3 |
| 2 | Lemmatisierung **vor** dem Nachschlagen; Wortart vor Grundform | „Warum die Reihenfolge…" |
| 3 | Keine Fremdschlüssel ins Wörterbuch — nur Momentaufnahmen | §4 |
| 4 | Profil und Wörterbuch in **getrennten Dateien** | §4 |
| 5 | `PRAGMA user_version` ab der ersten Fassung, bei jeder Schemaänderung erhöhen | §4 |
| 6 | Anki-GUID beim Export in `card` mitschreiben | §4 |
| 7 | Bei jedem Modellaufruf `reasoning_effort: "none"` | §3 |
| 8 | Wörterbuchquellen getrennt halten, nie verschmelzen (CC BY-SA / GPL) | §2 |
| 9 | NLP- und Modellaufrufe nie im Oberflächen-Thread | §1 |
| 10 | Wendungen ohne Wörterbucheintrag als `uncertain` markieren | „Messung: Mehrwortausdrücke" |
| 11 | Das Modell **wählt aus einer Liste**, es erzeugt nie frei | §3, „Messung…" |
| 12 | Eigennamenfilter wirkt auf das **Vorkommen**, nie auf die Grundform | §5 |
| 13 | Kein `except`, das nur protokolliert und weiterläuft — Abbruch mit Meldung oder `uncertain` | „Die Falle: es scheitert…" |
| 14 | Gebaut wird, was die Phase verlangt — kein Schalter, keine Abstraktion, kein Zwischenspeicher auf Vorrat | konzept.md, „Phasenplan" |
| 15 | Keine neue Abhängigkeit ohne vorherige Lizenzprüfung | §1, „Bekannte Kosten" |

**Zu Regel 14: Struktur ist nicht Funktion.** Die Regel begrenzt, was das Programm *tut* —
nicht, wie vollständig eine Datenstruktur angelegt wird. Ein Schema ist nur als Ganzes
stimmig, und ein nachgereichtes Teilstück heißt Migration; es entsteht deshalb vollständig,
sobald es überhaupt entsteht. Verhalten dagegen entsteht erst, wenn es gebraucht wird: alle
sieben Tabellen anlegen, aber nur die Zugriffsfunktionen schreiben, die die Phase verlangt.

**Zu Regel 15: die Rohquelle entscheidet.** Für Lizenz-, Fassungs- und Pflegeangaben ist die
**maschinenlesbare Rohquelle** verbindlich — das JSON eines Paketverzeichnisses, die
Lizenzdatei im Ursprungsbestand —, nicht die Zusammenfassung einer abgerufenen Seite. Was
davon in die Dokumente wandert, nennt die Quelle mit. Anlass ist ein Fall vom 18.08.2026:
Beim Abrufen von Webseiten wurden fehlende Angaben **erfunden** — ein Freigabedatum und eine
Fehlermeldung zu einer Bibliothek, die das fragliche Paket gar nicht verwendet; aufgefallen
ist es allein durch eine Gegenprüfung per `curl`. Eine erfundene Lizenzangabe ist nicht
auffällig, sie sieht aus wie jede andere — und Regel 15 entscheidet über Aufnahme oder
Ausschluss einer Bibliothek. Beim offiziellen `anki`-Paket führte die tatsächliche Angabe
(AGPL-3.0) zum Ausschluss.

---

## 5. Tests als ausführbare Dokumentation

Abnahmekriterien und Regeln werden zu Tests — Name englisch, Docstring im Wortlaut:

```python
def test_acceptance_6_known_words_are_not_asked_again():
    """Abnahmekriterium 6: Beim zweiten Durchlauf desselben Kapitels werden als
    bekannt markierte Wörter nicht erneut abgefragt — das Profil greift."""
```

Dokumentation, die lügen kann, lügt irgendwann; ein Test kann es nicht.

**Das gilt für die Regeln aus §4 genauso wie für die Abnahmekriterien.** Ein
Regel-Kommentar sagt nur, was gelten *soll*; ob es gilt, prüft niemand. Wo eine Regel
prüfbar ist, ist sie zu prüfen — sonst bleibt sie eine Absichtserklärung:

| Regel | Prüfung |
|---|---|
| 1 Zeilen ohne `sense` | `watch` und `draw` liefern ihre Hauptbedeutung in der Auswahlliste |
| 2 Lemmatisierung vor Nachschlagen | `He saw her…` ergibt *see*, nicht *Säge* |
| 4 getrennte Dateien | Profilzugriff öffnet nie `en-de.sqlite3` |
| 5 `PRAGMA user_version` | ist gesetzt und passt zum erwarteten Stand |
| 6 Anki-GUID | nach dem Export steht zu jeder Karte eine Kennung in `card` |
| 7 `reasoning_effort` | jeder Modellaufruf setzt `"none"` |
| 9 Kern ohne Oberfläche | unter `libreverbum/` wird keine Oberflächenbibliothek importiert |
| 10, 11 unsichere Wendungen | Wendung ohne Wörterbucheintrag ist `uncertain` |
| 12 Eigennamen je Vorkommen | `red` bleibt Lernvokabel, obwohl es auch in einem Namen steht |
| 13 nichts scheitert leise | unerreichbarer Modellserver ergibt einen sichtbaren Fehlschlag, kein stilles Loch in der Wortliste |

Regeln 3, 8, 14 und 15 sind Bauentscheidungen ohne sinnvollen Testpunkt — sie bleiben beim
Regel-Kommentar.

Regel 9 zerfällt dagegen in zwei Hälften, und nur eine davon ist Baudisziplin: Dass NLP-
und Modellaufrufe nicht im Oberflächen-Thread laufen, lässt sich nicht sinnvoll prüfen —
dass der Kern die Oberfläche überhaupt nicht kennt, sehr wohl. Die strukturelle Hälfte
steht deshalb in der Tabelle und ist damit keine Absichtserklärung mehr.

### Woran geprüft wird: die Vorrichtung zeigt Laufen, die Fremdquelle Stimmen

Eine selbstgebaute Testvorrichtung prüft die Annahmen ihres Erbauers nicht, sie bestätigt
sie. Das Mini-Wörterbuch war sauber, weil sein Erbauer sich eine Wörterbuchzeile als „ein
`lexentry`, eine Bedeutung" vorstellte — und der Code, der darauf zugriff, stellte es sich
genauso vor. In der echten Datei fallen 22,7 % der Zeilen mit `lexentry` zusammen, und die
Auswahlliste für `break` als Verb schrumpfte von 31 Einträgen auf 1.

> **Regel:** Wer eine Aussage über den **Inhalt einer Fremdquelle** prüft, prüft sie
> zusätzlich gegen das echte Gegenüber. Die Vorrichtung zeigt, dass der Code läuft; die
> Fremdquelle zeigt, ob er stimmt.

Die drei Fremdquellen verhalten sich dabei nicht gleich:

- **Wörterbuch** (`needs_dictionary`, `tools/en-de.sqlite3`) und **EPUB** (`tools/*.epub`)
  sind feste Gegenstände. Gegen sie lässt sich etwas behaupten — „`watch` als Substantiv
  liefert diese Bedeutungen", „diese Datei hat so viele Kapitel"
- **Modellserver** (`needs_model`) ist keiner. Gegen ein Sprachmodell lässt sich keine
  Gleichheit behaupten, nur eine Trefferquote messen, und Messungen gehören nach `tools/`,
  nicht in die Testsuite — `sense_check.py` lebt diese Rollenteilung bereits. Gegen den
  echten Server gehört stattdessen der **Abgleich der Attrappe**: dass sie in Antwortform,
  angenommenen Feldern und Fehlerverhalten noch dem echten Server entspricht. Eine
  Attrappe, die `reasoning_effort: "none"` klaglos annimmt, während der echte Server das
  Feld zurückwiese, macht Regel 7 lautlos unprüfbar

Beim EPUB wäre es beinahe schon passiert: Die Testnavigation war von der Lesereihenfolge
nicht unterscheidbar. Eine Umsetzung, die die Navigation ignoriert, wäre damit grün
durchgekommen — und genau sie ist die Kernregel aus technik.md §8.

### Ein Test gilt erst als Test, wenn er einmal rot war

Ein Test, der auch bei falscher Umsetzung grün bleibt, ist keine Prüfung, sondern eine
Zeile. `assert not has_lemma(occurrences, "Sherlock")` konnte gar nicht fehlschlagen, weil
Grundformen kleingeschrieben sind; ein Sortiertest blieb grün, obwohl das `ORDER BY score
DESC` fehlte.

> **Regel:** Ein neuer Test wird einmal gegen eine absichtlich falsche Umsetzung gehalten.
> Erst wenn er dabei rot war, gilt er als Test.

Verfälscht wird die **Umsetzung**, nicht der Test: Bedingung umdrehen, Sortierung
entfernen, Filter weglassen. Welcher Test bei welcher Verfälschung gefallen ist, gehört in
den Bericht (§9). Das kostet Minuten, und wo es getan wurde, hat der Bauende die Falle
selbst gefunden, um die es ging. Es ist damit der Teil der Prüfung, den der Bauende allein
leisten kann — **die Durchsicht ersetzt es nicht und wird davon nicht ersetzt** (§10).

**Bleibt der Test bei der Verfälschung grün, ist die Zusicherung zu schwach** — nicht die
Verfälschung falsch gewählt. Dann wird die Behauptung geschärft: Meldungstext statt
Fehlertyp, eine Vorrichtung, die den Mechanismus überhaupt erzwingt. Wer stattdessen eine
andere Verfälschung sucht, bis endlich eine rot wird, dreht die Probe um und lässt genau
den Test stehen, um den es geht — einen, der aussieht wie eine Zusicherung und keine ist.
Das ist kein Randfall: In einer einzigen Sitzung (18./19.08.2026) trat er viermal ein — eine
Sortierung, die SQLite bei Gleichstand ohnehin richtig herum lieferte; ein
`FileNotFoundError`, den `zipfile` selbst wirft; zwei `<p>`, die schon im Quelltext durch
einen Zeilenumbruch getrennt waren; ein Test, den ein neuer Aufrufpfad wirkungslos machte.

**Womit zu verfälschen sei, ist eine Vermutung und kein Auftrag** — auch dann nicht, wenn
der Vorschlag aus einer Durchsicht kommt. Wer verfälscht, prüft zuerst, ob die
vorgeschlagene Änderung überhaupt etwas bewirkt; sonst prüft er den Vorschlag und nicht den
Code. Der Musterfall stammt aus T13: Für den Lückentext war als Verfälschung ein naiver
`\b`-Regex vorgesehen, die naheliegendste falsche Umsetzung. Ausgeführt trifft sie `don't`
**korrekt**, weil Python die Wortgrenze nur an den äußeren Rändern des Treffers prüft — der
Test wäre gegen sie nie rot geworden. Gefunden allein durch das Ausprobieren; für plausibel
gehalten hätte man sie ohne Weiteres.

**An einer noch unversionierten Datei gibt es kein Netz.** Git holt den Ausgangsstand dort
nicht zurück. Sie wird deshalb vorher **binär** gesichert und die Wiederherstellung per
**Hash** verglichen — der Augenschein genügt nicht: Unter Windows verwandelte
`Path.write_text` beim Zurückschreiben LF in CRLF, und die Datei sah unverändert aus.

---

### Hängt ein Ergebnis an einem Modell, wird derselbe Lauf zweimal gefahren

Eine Abnahme, die einen Modellaufruf enthält, prüft zuerst, ob sie **überhaupt etwas
prüft**: derselbe Lauf, frisches Profil, gleiche Argumente, zweimal — und die Protokolle
müssen sich nach Abzug von Zeitstempeln und Pfaden zu **nichts** unterscheiden.

Der Grund steht in technik.md §3, „Zwingende Einstellung: Temperatur auf 0". Bevor die
Temperatur festgelegt war, lieferte dieselbe Eingabe in 9 von 40 Fällen eine andere
Antwort. Zwei Abnahmeläufe sind daran gescheitert, ohne dass es jemandem auffiel: Ein
Kriterium, das in etwa jedem fünften Lauf reißt, sieht in einem einzelnen Lauf entweder
erfüllt oder gefallen aus — beides überzeugend, beides wertlos. Erst zehn Wiederholungen
desselben Aufrufs machten daraus eine Aussage (8/10 gegen 2/10).

Die Probe kostet einen zweiten Lauf und ist die billigste Zusicherung im Bestand: Sie
bewacht die Temperaturfestlegung von außen, ohne etwas über sie zu wissen. Schlägt sie an,
ist **nicht** das Ergebnis der Befund, sondern dass es keines gibt.

## 6. Nicht dokumentiert wird

Keine erzeugte Schnittstellenreferenz (Sphinx, pdoc) — Pflege ohne Leser. Keine
Wiederholung von Typannotationen, keine Änderungshistorie in Dateiköpfen (dafür ist Git
da), keine Kommentare, die die Zeile darunter nacherzählen. Ersetzt ein Kommentar einen
guten Namen, wird stattdessen umbenannt.

---

## 7. Korrigieren: überschreiben oder Nachtrag

Zwei Fälle, die auseinanderzuhalten sind.

**Nachtrag bei Erkenntnis.** War die alte Aussage plausibel und schlüge sie jemand sonst
erneut vor, bleibt sie stehen und bekommt einen datierten Nachtrag. Der Musterfall ist
der Nachtrag zum LLM-Ansatz bei Wendungen (konzept.md, Abschnitt 5): „Wendungen ohne
Wörterbucheintrag bleiben dem LLM allein überlassen" klingt einleuchtend — ohne die
Notiz, dass die Messung genau daran gescheitert ist, wird es wieder so gebaut. Der
Nachtrag kostet acht Zeilen und spart einen Messdurchlauf.

**Überschreiben bei ersetzter Festlegung.** Benennungen, Formalia und abgelöste
Entscheidungen werden im Text geändert. Die Historie hat Git. Niemand wird `bedeutung`
zurückholen wollen, und falls doch, steht die Begründung in Abschnitt 1.

> **Prüffrage:** Träfe jemand, der die alte Fassung nie zu sehen bekommt, eine
> schlechtere Entscheidung? Ja → Nachtrag. Nein → überschreiben.

**Der gültige Stand steht immer oben.** Auch wo ein Nachtrag bleibt, wird der Text
darüber mitkorrigiert; der Nachtrag erklärt dann nur noch, *warum* die frühere Annahme
falsch war. Sonst liest man zuerst die überholte Fassung — und wer die Datei stückweise
oder per `grep` liest, erreicht den Nachtrag womöglich nie. Das ist derselbe Mechanismus
wie in Abschnitt 1: Was im Bestand steht, gilt faktisch, auch wenn weiter unten etwas
anderes gefordert wird.

**Eine berichtigte Kurzfassung wird als Ganzes gegen die Quelle geprüft, nicht an der
gemeldeten Stelle.** Eine Kurzfassung fasst mehrere Festlegungen in einem Satz; wer nur die
gemeldete Hälfte richtet, lässt die andere als Falle stehen. Der Kernablauf-Satz in
CLAUDE.md war nach Entscheidung 10 an **zwei** Stellen falsch. Der erste Korrekturlauf
richtete nur die gemeldete — die zweite führte danach noch zwei Bearbeiter in die Irre und
wurde erst im zweiten Anlauf gerichtet.

**Am Phasenende einfalten.** Ist eine Phase abgeschlossen, wandern die noch nützlichen
Nachträge in den Fließtext, der Rest fällt weg. Sonst wird aus einzelnen Nachträgen über
zwanzig Entscheidungen hinweg eine Sedimentschicht.

---

### Vor dem Löschen einer Datei: nachsehen, wer auf sie zeigt

Eine Datei, die planmäßig wegfällt — `bauplan.md` mit der Abnahme der Phase 1,
`nacharbeit.md` mit ihrer Auflösung —, hinterlässt Verweise, die ins Leere zeigen. Am
26.08.2026 waren es sieben im Quelltext auf `nacharbeit.md` und rund 140 auf `bauplan.md`.
Kein Prüfbefehl merkt das: Ein toter Verweis in einem Docstring ist syntaktisch tadellos.

Also `grep -rn <dateiname> .` **vor** dem Löschen, und je Treffer entscheiden. Dabei sind
zweierlei zu unterscheiden: ein **Wegweiser**, dem ein Leser folgen soll — der wird auf das
Dokument umgebogen, das die Sache jetzt trägt —, und eine **Herkunftsangabe** wie
`bauplan.md T13`, die nur sagt, woher eine Zeile stammt. Die bleibt stehen: Sie ist über
`git show <commit>:<datei>` weiterhin auflösbar, und verkürzt man sie auf `T13`, geht genau
diese Spur verloren.

## 8. Kleinigkeiten

- **Dateien immer mit `encoding="utf-8"` öffnen.** Unter Windows liest Python sonst in der
  Kodierung der Systemumgebung und zerstört still typografische Anführungszeichen und
  Gedankenstriche im Buchtext
- Verweisform: `technik.md §3, „Datenfalle"` — Nummer und Überschrift, nie eine Zeilennummer

---

## 9. Aufträge und Berichte

Wer eine Teilaufgabe baut, startet kalt aus den Dokumenten und gibt am Ende einen Bericht
zurück. Was er dabei über den **Ablauf** gelernt hat, ist danach weg, wenn er es nicht
erwähnt — der Bericht ist der einzige Rückweg. Deshalb steht am Ende **jedes** Auftrags
dieser Abschnitt, wörtlich:

> ## Beobachtungen zum Ablauf
> Was hat dich aufgehalten, in die Irre geführt oder zu einer Entscheidung gezwungen, die
> eigentlich woanders hingehört? Je Punkt eine Zeile, dazu: was es dich gekostet hat, und
> ob dabei ein falsches Ergebnis hätte durchgehen können. Sonst „nichts".

Die Frage ist absichtlich eng gestellt. Offen gefragt — „hast du Verbesserungsvorschläge?"
— kommen allgemeine Ratschläge zurück, die niemand braucht. Gefragt sind die zwei
Tatsachen, die der Bauende wirklich kennt: seine eigenen Kosten und ob etwas hätte
durchgehen können. **Wie schwer eine Beobachtung wiegt, entscheidet er nicht** — das zeigt
sich erst, wenn mehrere Berichte nebeneinander liegen. Zum Bericht gehört außerdem der
rote Lauf aus §5: welcher Test bei welcher Verfälschung gefallen ist.

**Keine gemeinsame Datei, in die alle schreiben.** Es laufen regelmäßig zwei Bearbeiter
gleichzeitig; beim Anhängen an dieselbe Datei gehen Einträge verloren, ohne dass es jemand
merkt. Der Bericht ist der Kanal; das Sammeln und Einfalten macht die kuratierende Stelle.
Reicht das nicht mehr, ist die nächste Stufe ein **Verzeichnis mit einer Datei je
Beobachtung** — konfliktfrei, weil jeder in seine eigene schreibt — und kein zweiter
Sammeltext.

**Eingefaltet wird an den Toren einer Phase** — dort, wo ein Bündel von Teilaufgaben
abgeschlossen ist und der nächste Abschnitt beginnt: Die gesammelte Liste wird
durchgegangen, was ein Dokument berichtigt, wandert hinein, was die Hausordnung ändert,
wird entschieden. Der Punkt, an dem ein solcher Rückweg gewöhnlich stirbt, ist nicht das
Sammeln, sondern das Einfalten — dieselbe Vorsichtsmaßnahme wie „Am Phasenende einfalten"
in §7.

### Die beiden Arten werden verschieden behandelt

**Was ein Dokument berichtigt, wird bei jedem Einfalten vollständig abgearbeitet.** Es ist
unstrittig, kostet Minuten und entscheidet, ob der nächste Kaltstart einen richtigen Stand
liest — ein solcher Punkt wird deshalb weder gewichtet noch zurückgestellt. Ein Nachtrag,
der liegen bleibt, macht aus einem behobenen Fehler eine falsche Anleitung.

**Was die Hausordnung ändert, braucht eine Entscheidung** und wird dafür gewichtet. Die
Stufe beantwortet **eine** Frage: *Was wäre passiert, wenn es niemand bemerkt hätte?*

| Stufe | Folge, wenn unbemerkt |
|---|---|
| **schwer** | Ein falsches Ergebnis geht durch, ohne aufzufallen — der leise Fehlschlag. Oder es geht etwas verloren, das nicht wiederherstellbar ist |
| **mittel** | Das Ergebnis stimmt, kostet aber spürbar: verdoppelte Arbeit, zwei Bearbeiter lösen dasselbe verschieden, oder es dauert unzumutbar lange |
| **leicht** | Reibung ohne Folge |

Dahinter steht `· schnell`, wo ein Punkt in einer Viertelstunde erledigt ist; innerhalb
einer Stufe wird das Schnelle zuerst gemacht.

### Der Auftrag nennt die Form jeder Schnittstelle, die er berührt

Zwei Teilaufgaben mussten am 21.08.2026 die Datenform ihrer eigenen Eingabe erfinden: Kein
Dokument legte fest, was `anki` und `printout` bekommen, und T14 entschied sich für
`Sequence[tuple[Occurrence, Sense]]` statt `Sequence[Card]` — ableitbar war das aus keiner
Regel und keinem Test. Dieselbe Wurzel bei T13, wo der Auftrag „GUID **zurückgeben**"
verlangte, während `entities.Card.guid` Pflichtfeld ist: Die Auflösung — die GUID entsteht
**vor** dem `Card`-Bau — stand nirgends und musste aus der Importregel rückwärts erschlossen
werden.

Das ist teurer als es aussieht, weil es in beide Richtungen unbemerkt durchgeht: Die
verkettende Teilaufgabe findet danach zwei Module mit unvereinbaren Eingaben vor, ohne dass
eine der beiden je rot gewesen wäre.

> **Regel:** Berührt eine Teilaufgabe die Grenze zu einer anderen, nennt der Auftrag deren
> **Form** — oder sagt ausdrücklich, dass die bauende Teilaufgabe sie bestimmt. Beides ist
> zulässig, das Schweigen nicht.

Ein Dokument schließt die Lücke nicht: Die Modulkarte (technik.md §7, „Warum eine Karte und
nicht mehr") nennt Zuständigkeiten und ausdrücklich keine Entwürfe, und Regel 14 verbietet
Vorratsarbeit. Die Lücke ist gewollt — sie gehört deshalb in den Auftrag.

### Verlangt eine Teilaufgabe zwei Wege, nennt die Prüfung beide

Aus Phase 1, an T4 gelernt: Was der Auftrag als Prüfung nennt, wird als **Auftragsumfang**
gelesen. Das ist die naheliegende Lesart und keine Nachlässigkeit — nennt die Prüfung nur
einen von zwei verlangten Wegen, entsteht folgerichtig die Hälfte, ohne Fehler und ohne
Meldung. Bei T4 (zusammenhängende Kandidatenfolgen **und** getrennte Verb-Partikel-Paare)
ist genau das passiert.

> **Regel:** Verlangt eine Teilaufgabe zwei Wege, nennt die Prüfung **beide** — je einen
> Fall, an dem der eine ohne den anderen rot wird.

**Abgearbeitet werden `schwer` und `mittel`.** `leicht` bleibt liegen und wird von Hand
angestoßen, wo es sich lohnt — **spätestens am Phasenende** wird jeder verbliebene Punkt
eingefaltet oder ersatzlos gestrichen. Streichen ist dort oft die richtige Antwort, weil
die Reibung inzwischen weg ist. Ohne diesen Termin zeigt die Verfallsklausel der
Sammelliste ins Leere, und aus dem Rest wird die Sedimentschicht aus §7.

---

## 10. Die Durchsicht

Das Tor aus CLAUDE.md, „Prüfen vor »fertig«" beantwortet **eine** Frage: Stimmt die Form —
Format, Regeln, Typen, laufen die Tests? Ob das Gebaute das Richtige tut, beantwortet es
nicht. Auf das grüne Tor folgt deshalb die **Durchsicht**, bei jeder Teilaufgabe und
**nicht durch denselben Bearbeiter**, der gebaut hat.

**Der Beleg** (entschieden am 21.08.2026): neun Teilaufgaben, neun grüne Tore, neun
Durchsichten mit Befunden — T6, T7, T9, T12, T12b und T15 (18./19.08.2026, vier davon
`schwer`), T11, T13 und T14 (21.08.2026, zwei `schwer`, dazu einer, der bei jedem echten
Kapiteldurchlauf zugeschlagen hätte). Alle vom **stillen** Typ: Etwas kam leer, unmarkiert
oder unbemerkt falsch zurück, und alle vier Torbefehle blieben grün — genau die Art
Fehlschlag, gegen die Regel 13 geschrieben ist. Neun von neun sind keine Nachlässigkeit,
sondern die Bauart des Tors. Und **nicht derselbe Bearbeiter**, weil drei der vier
`schwer`-Befunde der ersten Sitzung in Annahmen lagen, die der Bauende selbst getroffen
und in seinen eigenen Tests wiederholt hatte — dieselbe Wurzel wie bei der selbstgebauten
Vorrichtung in §5, „Woran geprüft wird". Wer prüft, muss die Annahme nicht teilen.

### Wonach sie sucht, und was herauskommt

Nicht nach Formfehlern, die hat das Tor. Gesucht wird der **stille Fehlschlag**: ein
Ergebnis, das leer zurückkommt, ohne dass etwas meldet; ein Eintrag, der falsch ist und
nicht `uncertain` trägt; ein Zweig, der außerhalb der Tests keinen Aufrufer hat; ein Test,
der grün ist, weil er nichts zusichert. Gegengehalten wird dem, was verlangt war —
Abnahmekriterium, Regel, Auftrag —, und dem echten Gegenüber (§5, „Woran geprüft wird").

**Das Ergebnis sind Befunde**, je Befund drei Angaben:

| Angabe | Inhalt |
|---|---|
| **Ort** | Datei und Stelle |
| **Wirkung** | was falsch herauskommt, wenn es so bleibt |
| **Schwere** | `schwer` / `mittel` / `leicht` nach der Tabelle in §9 |

`schwer` und `mittel` werden nachgebessert, `leicht` nur, wo es sich lohnt. **Die Stufe
vergibt hier der Durchsehende selbst** — anders als bei einer Beobachtung: Die Wirkung
eines Befunds ist örtlich und jetzt sichtbar, sie zeigt sich nicht erst, wenn mehrere
Berichte nebeneinander liegen.

### Woran sie prüft: gegen den Commit, nicht gegen den Arbeitsbaum

Es laufen regelmäßig zwei Bearbeiter gleichzeitig (CLAUDE.md, „Aktueller Stand"). Wer im
Arbeitsbaum prüft, sieht deshalb fremde Änderungen mit, und ein rotes Ergebnis lässt sich
nicht zuordnen — hängt es am durchgesehenen Commit oder an der Arbeit des anderen? „Nur die
betroffenen Testdateien laufen lassen" verkleinert das Problem, löst es aber nicht.

> **Regel:** Die Durchsicht prüft gegen `git archive <commit>` in einem Wegwerfordner, nicht
> gegen den Arbeitsbaum. `tools/en-de.sqlite3` und `tools/*.epub` werden dorthin mitkopiert
> — ohne sie überspringt `pytest` 32 Tests (`needs_dictionary`, `needs_epub`,
> `needs_calibre_split_epub`) stillschweigend, und die Durchsicht hält für grün, was gar
> nicht gelaufen ist.

Das Vorgehen hat sich in drei Durchsichten und drei Abnahmeläufen im August 2026 bewährt und
kostet einen Befehl. Es ersetzt nicht das Tor auf der Seite des Bauenden (CLAUDE.md, „Prüfen
vor »fertig«"), sondern beantwortet dessen offene Frage: woran „grün" bei zwei Bearbeitern
überhaupt gemessen ist.

### Befund und Beobachtung sind zweierlei

Ein **Befund** betrifft **das Gebaute**. Er geht an die Teilaufgabe zurück und ist erledigt,
wenn die Stelle behoben ist; bleibt er dort als Begründung stehen, trägt er die Marke aus
§4. Eine **Beobachtung** betrifft **den Ablauf**, geht in den Bericht (§9) und wird an einem
Tor eingefaltet. Wer beides in denselben Kanal wirft, verliert die Beobachtung — die
Teilaufgabe ist danach zu, der Ablauf bleibt derselbe.
