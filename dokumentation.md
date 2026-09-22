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
| `lernender` | `learner` |

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
| Lernender (die Person, deren Profil geführt wird) | `learner` — so heißt die Tabelle mit dem Sprachniveau; **nicht** `profile`, das ist bereits Modul, Begriff und Dateiname |
| bekannt / lernt / zurückgestellt / vergessen | `known` / `learning` / `deferred` / `forgotten` |
| Herkunft und Zeitpunkt (einer Kenntnisangabe) | `origin`, `timestamp` |
| Vorbelegung (Grundwortschatz als bekannt vorbelegen) | `preset` |
| Sprachniveau (nach GER, A1–C1, für die Vorbelegung) | `cefr_level` (`CefrLevel`) — **nicht** `level`, das ist die Gliederungsebene der Navigation |
| unbekannt / bekannt / neue Bedeutung eines bekannten Wortes (Abgleich Kapitelwortschatz ↔ Profil) | `unknown` / `known` / `new_meaning_of_known_word` (`VocabularyStatus`, in `libreverbum/profile.py` — **nicht** `entities.py`, wo `KnowledgeState`, `Origin`, `CardDirection` und `CefrLevel` liegen) |
| Triage, Sammelaktion, Wortobergrenze | `triage`, `bulk_mark`, `word_limit` |
| Block (eine Portion der Triage), Blockgröße | `block`, `block_size` — die Zahl, nach der die Fortsetzungsfrage kommt (konzept.md §4, „Blockweise Triage mit Fortsetzungsfrage"); **nicht** `limit`, das im Kern weiterhin die Obergrenze **eines** Aufrufs ist |
| Fortsetzungsfrage (nach jedem Block) | `ask_continue` |
| Vorladen (des nächsten Blocks, während der Nutzer entscheidet) | `prefetch` |
| noch nicht geprüfte Einträge (der Rest nach einem Block) | `remaining` |
| noch unentschiedene Einträge (der Rest nach dem kostenlosen Vorfilter) | `undetermined_entries` — **nicht** `remaining`, das im selben Ablauf schon den Rest nach der Blockgrenze meint (Befund 7, Durchsicht d4f10fc) |
| Wörterbuch, Nachschlagen | `dictionary`, `lookup` |
| Auswahlliste, Kandidat | `candidate` |
| Übersetzung | `translation` |
| Karte, Deck, Kartenrichtung, Lückentext | `card`, `deck`, `card_direction`, `cloze` |
| Kartenvorlage (genankis `Model` — „Modell" bleibt dem Sprachmodell vorbehalten, technik.md §3) | `note_model` |
| Druckausgabe | `printout` |
| Teilexport (unvollständiger, aber gültiger Export nach einem Abbruch, technik.md §12) | `partial` (`app.export.export_paths`/`write_exports`, bauplan-phase2.md AP 3), Dateizusatz `_teilexport` |
| Blattzählung („Blatt n von m", nur bei mehr als einem Blatt) | `sheet_label` |
| unsicher (markierter Eintrag) | `uncertain` |
| Ausgabestil (Fähigkeiten des Ziels: Farbe, Sonderzeichen, Breite, einmal je Lauf ermittelt) | `style` (`Style`) |
| Fettdruck | `bold` |
| gedimmt | `dim` |
| hervorgehoben (farbig) | `highlight` |
| Trennlinie (vor einem Eintrag, mit Zähler) | `rule` (`entry_rule`) |
| Deckel-Banner | `cover` |
| Kopfzeile (Wortform + Übersetzung eines Eintrags, umgebrochen und eingefärbt) | `headline` |
| Umbrechen mit gleichbleibender Einrückung | `wrap_indented` |
| Lernzähler (wie viele Einträge in diesem Kapitel bereits „lernen" bekommen haben, Stand **vor** der anstehenden Entscheidung) | `chosen`, `chosen_before` (`display.entry_rule`, `cli.interaction`) — **nicht** `learning`: das ist der Kenntnisstand einer einzelnen Bedeutung, `chosen`/`chosen_before` zählen, wie oft dieser Zustand in diesem Kapitel bereits vergeben wurde (Befund 6, Durchsicht e537273) |
| Blockbilanz (was ein Block bei seinem Ende gebracht hat: gelernt / bekannt gebucht / übersprungen, dazu der Kapitelstand) | `_write_block_summary` (Befund 6, Durchsicht e537273) |
| Gegenstand des Kernablaufs | `entity` |
| Durchlauf, Verkettung der Schritte | `pipeline` |
| Etappe (eines `run_chapter`-Durchlaufs: Buch lesen, Buch analysieren, Wortschatz ermitteln, nachschlagen) | `stage` (`ChapterStage`) — **nicht** „Phase", das ist die Phase des Phasenplans (konzept.md), und **nicht** „Schritt", das sind die sechs Schritte des Kernablaufs |
| Fortschritt (Rückruf aus einem langen Lauf an die Oberfläche) | `progress`, `on_progress` |
| Lesereihenfolge, Manifest (EPUB) | `spine`, `manifest` |
| Inhaltsverzeichnis einer Datei | `navigation` |
| Gliederungsebene (in der Navigation) | `level` |
| Hinweis (z. B. bei fehlender Navigation) | `notice` |
| Datenverzeichnis | `data_dir` |
| Zwischenspeicher (Wegwerfwert, ohne Nutzerwert selbst neu berechenbar — bisher nur für den buchweiten Eigennamenanteil, technik.md §5, „Entschieden 15.09.2026") | `cache`, `cache_dir` |
| Einstellungen | `config` |
| Ausgangssprache (die Sprache, die gelernt wird: des Buchs, der Grundform; Kürzel nach ISO 639-1, heute nur `en`) | `language` (Spalte an `book` und `lemma`, beschlossen 15.09.2026, kommt mit der nächsten Schemafassung — technik.md §4, „Entschieden 15.09.2026: Mehrsprachigkeit bleibt möglich") — **nicht** `lang`, und nicht die Zielsprache: die ist Deutsch und hat keine Spalte |
| Anwendungsschicht (was beide Oberflächen teilen und der Kern nicht kennt) | `app` (technik.md §14) |
| Qt-Oberfläche | `gui` |
| Ansichtsmodell (Zustand und Übergänge eines Bildschirms, ohne QML) | `view_model` |
| Arbeiter, Hintergrundfaden der Oberfläche | `worker` |
| Gestaltungsvorgaben, Token | `theme` (`Theme.qml`) |
| Gestaltungsrichtung (die **eine** Ästhetik der Oberfläche) | „Lesetisch" — ein Name, kein Bezeichner, und deshalb nicht übersetzt (technik.md §14, E11); das Verzeichnis, das sie vorführt, heißt `tools/design_mockup/` |
| Ebene L0, der Tisch (Fensterhintergrund) | `ground` |
| Ebene L1, das Blatt (Karte, Liste, Formular) | `surface` |
| Ebene L2, die laufende oder gewählte Zeile | `marked` — **nicht** `highlight`, das ist die farbige Hervorhebung der Konsolen- und Druckausgabe (`display`) |
| Trennlinie, ein Pixel | `hairline` — **nicht** `border`, das wäre die Kontur eines Bedienelements, und die gibt es in dieser Richtung nicht |
| Schriftfarbe in drei Rängen (voll / gedämpft / ruhend) | `ink` / `inkSoft` / `inkFaint` — drei Ränge, damit kein Bildschirm zu `opacity` greift (technik.md §14, E11) |
| Akzent (hier bist du gerade / das ist die Antwort) | `accent` (Schrift und Linie), `accentFill` (Fläche), `inkOnAccent` (Schrift darauf) |
| Farbe für „zum Lernen gewählt" | `chosen` — dasselbe Wort wie der Lernzähler oben und dieselbe Sache, einmal als Zahl, einmal als Farbe |
| Farbe des Fehlschlags im Wortlaut | `warn` (Schrift), `warnFill` (Fläche) |
| Schriftrolle: Sprachmaterial gegen Programmstimme | `Theme.fonts.book` (Literata: Wortform, Belegsatz, Titel) / `Theme.fonts.ui` (Inter: Beschriftung, Zähler, Schaltfläche) |
| Rastereinheit und Abstandsskala | `unit` (8) und `space.xs…xxl` |
| Bildschirm, Ansicht | `screen` |
| Abdeckung (Anteil der vom Leser bereits verstandenen Wortformen, Anzeige der Oberfläche) | `coverage` — **nicht** zu verwechseln mit der Wörterbuchabdeckung aus technik.md §2, „Abdeckung — empirisch geprüft" (dort `remaining`/`undetermined_entries`: Anteil der Grundformen mit Wörterbucheintrag) |
| Rückgabe von `extraction.extract_vocabulary` (Vorkommen und Nenner für die Abdeckung) | `VocabularyExtraction` |
| Nenner der Abdeckung (jedes alphabetische Token des Kapitels, `token.is_alpha`, bauplan-phase2.md AP 6, E5 Festlegung 1) | `token_count` |
| Zähler der Abdeckung (`token_count` abzüglich der nicht verstandenen Vorkommen) | `understood_tokens` |
| Anzahl der Grundformen aus `entries`, die dabei nicht verstanden sind (Grundformenzahl, keine Häufigkeit) | `unknown_lemma_count` |
| Abdeckung jetzt (`understood_tokens / token_count`) beziehungsweise nach dem Lernen der in diesem Durchgang auf `learning` gebuchten Grundformen | `share` / `share_after_learning` |
| Schwierigkeit (eines Buchs) | `difficulty` |
| Lesezeichen (Druckformat) | `bookmark` |
| Figuren & Orte | `proper_noun_list` |
| Sicherung / Ausleiten | `backup` / `dump` |
| Einstufungstest | `placement_test` |
| Anki-Import | `anki_import`, Herkunft `Origin.IMPORT` |
| Kapitelbereich | `chapter_range` |
| Einrichtung, Erstlauf | `setup` |
| Kapitel ohne Fließtext (Vorspann, Impressum, Bildband) | `ChapterWithoutTextError`, `skip_reason` |
| Kapitelübersicht für die Kapitelauswahl (Nummer, Titel, Wortumfang, `skip_reason`, ohne spaCy) | `ChapterListing` (`pipeline.list_chapters`, bauplan-phase2.md AP 4) |
| Schwierigkeitscheck-Ergebnis für ein Kapitel mit Fließtext (Zeile der Kapiteltabelle) | `ChapterDifficulty` (`pipeline.assess_book`, bauplan-phase2.md AP 7) |
| Schwierigkeitscheck-Ergebnis fürs ganze Buch (`assess_book`, je Kapitel eine `ChapterDifficulty`, dazu dieselben vier Größen aggregiert) | `BookDifficulty` |
| Maßzahl des Schwierigkeitschecks (`unknown_lemma_count / token_count * 1000`, E12) | `unknown_per_thousand` |
| Einordnung des Schwierigkeitschecks in eine von drei Stufen (Schwellenworte, ausdrücklich als Vermutung markiert, E12, liegt in `app/`, nicht im Kern) | `DifficultyLevel`, `classify_difficulty` (`app.difficulty`) |

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
acht Tabellen anlegen, aber nur die Zugriffsfunktionen schreiben, die die Phase verlangt.

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

**Eine Verfälschung wird nie mit `git checkout` zurückgenommen — auch an einer
versionierten Datei nicht.** Der Stand ist zur Zeit der Probe **immer** uncommittet, das
Tor ist ja noch nicht durch; die Falle steckt damit im vorgeschriebenen Vorgehen selbst.
Beleg: Bei der Nachbesserung `aa90722` rief ein Bauagent `git checkout --
cli/interaction.py` auf, um allein die Verfälschung zurückzunehmen. Die Datei ging damit
auf `HEAD`, und der ganze noch uncommittete Befund — Hilfsfunktion, vier Meldungen, ein
Docstring-Absatz — war mit weg; die Wiederherstellung lief aus dem Gedächtnis. Stufe
`schwer` (Verlust, der nicht wiederherstellbar ist).

> **Regel:** Zurückgenommen wird mit einem gezielten Edit, der genau die verfälschte
> Stelle wiederherstellt — oder aus einer Kopie, die **vor** der Probe im Scratchpad
> angelegt wurde. Im Wegwerfordner der Durchsicht (§10) ist das ohnehin der einzige Weg: Er
> ist kein Repository, `git checkout` steht dort nicht zur Verfügung. `git checkout` ist
> nur zulässig, wenn der Arbeitsbaum sonst nachweislich sauber ist.

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

### Wer eine Zahl in ein Dokument schreibt, schreibt das Rezept daneben

Belege: Das Rezept der `importance`-Rangliste stand nirgends — vier Varianten
durchprobiert, rund ein Viertel der Messzeit, bevor ein Befund belastbar war statt bloß ein
Rezeptunterschied. Welches Kapitel die Abnahme T17 gemessen hat, stand nirgends; es musste
über vier in konzept.md genannte Wörter gesucht werden, und eine falsche Kapitelwahl hätte
sämtliche Zahlen verschoben, ohne aufzufallen. Die Zahlen „ohne Wörterbucheintrag" hängen an
mindestens drei verschiedenen Abfragen, und technik.md §11 benutzte zwei davon in
aufeinanderfolgenden Sätzen (8,0 % und 12,8 %), ohne sie zu unterscheiden — beinahe ein
falscher Befund. Ein Messlauf nahm das falsche Modell, weil die Modellfestlegung in §3
steht und nicht bei der Messung in §11.

> **Regel:** Rezept heißt Abfrage, Modell, Kapitel, Datum — so viel, dass die Zahl
> nachrechenbar ist. Der Messstand selbst überlebt die Sitzung nicht; das Dokument ist der
> einzige Ort, an dem er bleibt.

## 6. Nicht dokumentiert wird

Keine erzeugte Schnittstellenreferenz (Sphinx, pdoc) — Pflege ohne Leser. Keine
Wiederholung von Typannotationen, keine Änderungshistorie in Dateiköpfen (dafür ist Git
da), keine Kommentare, die die Zeile darunter nacherzählen. Ersetzt ein Kommentar einen
guten Namen, wird stattdessen umbenannt.

---

## 7. Korrigieren: überschreiben oder Nachtrag

Zwei Fälle, die auseinanderzuhalten sind.

**Nachtrag bei Erkenntnis.** War die alte Aussage plausibel und schlüge sie jemand sonst
erneut vor, bleibt sie stehen und bekommt einen datierten Nachtrag. Der Musterfall war
der Nachtrag zum LLM-Ansatz bei Wendungen (konzept.md, Abschnitt 5): „Wendungen ohne
Wörterbucheintrag bleiben dem LLM allein überlassen" klang einleuchtend — ohne die Notiz,
dass die Messung genau daran gescheitert ist, wäre es wieder so gebaut worden. Der
Nachtrag kostete acht Zeilen und sparte einen Messdurchlauf; mit dem Einfalten der
Phase-1-Nachträge (15.09.2026) ist die Aussage in den Fließtext gewandert, im alten
Wortlaut nachzulesen mit `git show b663678:konzept.md`.

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

### Ein verteiltes Einfalten braucht eine verbindliche Umbenennungstabelle

Ein Einfalten, das auf mehrere Teilaufträge oder mehrere Commits verteilt wird, erzeugt
**tote Verweise auf Zeit**: Ein Verweis auf eine neue Überschrift zeigt ins Leere, solange
der Teilauftrag, der sie einträgt, noch nicht committet hat — und keiner der beiden
Bauenden kann das im eigenen Diff sehen. Beleg: `konzept.md` trug die neue §8c-Überschrift
bereits seit `0b09b7d`; zwischen `0b09b7d` und `8f87838` lief ein Verweis darauf ins Leere,
bis der zugehörige Teilauftrag selbst committet hatte.

> **Regel:** Ein verteiltes Einfalten nennt im Auftrag eine **verbindliche
> Umbenennungstabelle** — sie ist die einzige Prüfgrundlage, an der der Durchsehende einen
> Übergangszustand von einem toten Verweis unterscheiden kann. Die Tabelle nennt die
> **verschachtelte Gruppe** von Überschriften, nicht nur die einzelne Überschrift:
> Binnenverweise wie „siehe oben" oder „stand unter …" zwischen zusammenhängenden
> Abschnitten benutzen das gesuchte Stichwort oft gar nicht, und kein `grep` findet sie
> dann.

Zwei Prüffragen gehören beim Einfalten dazu, aus derselben Fehlerfamilie:

- **Nicht „ist alles noch da?", sondern „steht jede erhaltene Messreihe unter der Regel,
  unter der sie gemessen wurde?"** Beleg: Nach dem Verschmelzen zweier Nachträge stand die
  Messreihe einer verworfenen Regel im Präsens unter der Überschrift der geltenden — alle
  Zahlen waren da, der Abschnitt las sich trotzdem falsch.
- **Eine neu geschriebene Zusammenfassung ist die gefährlichste Zeile eines Einfaltens.**
  Ein Satz, der wie eine Zusammenfassung der Tabelle darunter klingt, ihr aber
  widerspricht, sieht im Diff richtig aus.

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
- **PowerShell: `… | Select-Object -First N` beendet die Pipeline** und damit das laufende
  Skript (Exit 255) — ein sauberer Lauf sieht danach wie ein Fehlschlag aus (passt zu §10,
  „Nach jedem Prüfpunkt ein Zwischenergebnis in eine Datei"). Lange Ausgaben stattdessen in
  eine Datei umleiten und dann lesen

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

### Wo die Beobachtungen liegen: `beobachtungen/`

**Keine gemeinsame Datei, in die alle schreiben.** Es laufen regelmäßig zwei Bearbeiter
gleichzeitig; beim Anhängen an dieselbe Datei gehen Einträge verloren, ohne dass es jemand
merkt. Deshalb **eine Datei je Bericht** im Verzeichnis `beobachtungen/`: Jeder
Schreibvorgang legt eine Datei an, statt an eine bestehende anzuhängen, und damit ist diese
Fehlerklasse weg statt verwaltet.

**Der Bericht bleibt der Kanal** — wer baut oder durchsieht, legt selbst nichts ab und
bekommt keine zweite Pflicht, die er vergessen kann. Abgelegt wird von der **kuratierenden
Stelle**: Sie nimmt den Bericht entgegen und schreibt seine Beobachtungen weg, **bevor sie
etwas anderes tut**. So schreibt genau einer, und der Zeitpunkt ist eindeutig. Wer das auf
später verschiebt, hat sie faktisch nur im Sitzungsprotokoll — und das liegt außerhalb des
Repositoriums, ist nicht versioniert und an einen Rechner gebunden.

**Das ist keine Neuerfindung, sondern die Fortsetzung von `nacharbeit.md`.** In Phase 1 lief
dieselbe Sache als **eine** Datei, gefüllt aus den Berichten von T3 bis T15 und bei T18
aufgelöst — jeder Punkt eingefaltet, gestrichen oder weitergeführt, die Datei danach
gelöscht (`git show abe42cf^:nacharbeit.md`). Der Weg hat getragen; übernommen sind
daraus die Gewichtung durch die kuratierende Stelle und das Auflösen am Tor. Zweierlei ist
neu: die Ablage **je Bericht** statt in einer Datei — nicht, weil eine Datei nicht ginge,
sondern weil das Anlegen nichts überschreiben kann — und der **Zeitpunkt**. `nacharbeit.md`
verlangte beim Ablegen bereits die Einordnung in Teil A oder B samt Vorschlag; das ist
Arbeit des Tors, und wer sie an den Eingang legt, verschiebt das Ablegen. Abgelegt wird
deshalb **roh und ungewichtet**, sobald der Bericht ankommt.

**Je Bericht, nicht je Beobachtung.** Eine Beobachtung ohne die Teilaufgabe, aus der sie
stammt, ist nicht zu bewerten: „hat zwei Läufe gekostet" sagt nichts, solange offen bleibt,
welche. Konfliktfrei ist das eine wie das andere; beisammen bleibt nur das erste.

Der Name nennt Datum und Sache, die Rolle unterscheidet Bau von Durchsicht — aus derselben
Teilaufgabe kommen beide:

```
beobachtungen/2026-09-15-teilexport-bei-abbruch-durchsicht.md
```

```markdown
# Teilexport bei Abbruch — Durchsicht

Datum: 15.09.2026 · Commit: b91a56e · Rolle: Durchsicht

- Die Verfälschungsprobe ließ sich nicht mit `git checkout` zurücknehmen, ohne die
  uncommittete echte Arbeit mitzuverwerfen.
  Kosten: eine Stunde Wiederherstellung. Hätte durchgehen können: nein.
```

**Beide Angaben stehen in jeder Zeile**, auch wo sie „keine" und „nein" lauten. Ein Feld,
das freibleiben darf, macht die oben eng gestellte Frage wieder weit.

Drei Dinge gehören **nicht** hinein:

- **keine Stufe** — gewichtet wird am Tor, nicht vom Bauenden (siehe oben und die Tabelle
  unten)
- **kein Befund** — der geht an die Teilaufgabe zurück und ist dort erledigt (§10, „Befund
  und Beobachtung sind zweierlei")
- **kein roter Lauf** — welcher Test bei welcher Verfälschung fiel, gehört in den Bericht
  und zur Teilaufgabe, nicht zum Ablauf

**Eingefaltet wird an den Toren einer Phase** — dort, wo ein Bündel von Teilaufgaben
abgeschlossen ist und der nächste Abschnitt beginnt: Die gesammelte Liste wird
durchgegangen, was ein Dokument berichtigt, wandert hinein, was die Hausordnung ändert,
wird entschieden. Der Punkt, an dem ein solcher Rückweg gewöhnlich stirbt, ist nicht das
Sammeln, sondern das Einfalten — dieselbe Vorsichtsmaßnahme wie „Am Phasenende einfalten"
in §7.

**Das Einfalten löscht die Dateien**, im selben Commit, der die Nachträge in die Dokumente
trägt. `beobachtungen/` ist damit zwischen zwei Toren gefüllt und danach leer — und ein
nicht-leeres Verzeichnis **ist** die Erinnerung ans Einfalten. Ein Verzeichnis, das nur
wächst, stirbt leise; eines, das leer sein soll, meldet sich. Verloren geht dabei nichts:
Die Historie hat Git, genau wie bei `bauplan.md` (§7, „Überschreiben bei ersetzter
Festlegung").

**Beim Einfalten ist die Suchmenge „alles außer `beobachtungen/`", nie die im Auftrag
aufgezählten geänderten Verzeichnisse.** Ein Auftrag, der die zu durchsuchenden Orte
aufzählt, verengt damit ungewollt die Suche nach dem alten Wortlaut. Beleg: Eine
Kurzfassung der Nachtragsregel aus §7 stand weiterhin unverändert in CLAUDE.md — einer
Datei, die keiner der aufgezählten Teilaufträge als eigene führte — und wurde nur
gefunden, weil `grep` über den ganzen Wegwerfordner lief statt über die im Auftrag
benannten Verzeichnisse. Die Stelle stand als Prosa, nicht im Diff der Teilaufgabe.

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

### Der Auftrag trennt Belegtes von Vermutetem

Belege (alle aus Berichten seit dem 31.08.2026, je einer eine eigene Teilaufgabe):

- `extract_expression_candidates` — ein Funktionsname, den es nicht gibt. Er stand in
  einem Durchsichtsbericht, wurde in drei Aufträge übernommen und landete in einer
  **ausgelieferten Datei** (`libreverbum/wordfreq_en_5000.txt`, Dateikopf) *und* in einem
  Test, der ihn einfror. Gefunden nur, weil ein Agent beim Prüfen einer *anderen*
  Behauptung zufällig darüber stolperte
- „suche den zweiten `JOIN`" — als Tatsache formuliert; es gibt keinen. Rund fünfzehn
  Minuten vollständige SQL-Inventur, um „es gibt keinen" belegen statt behaupten zu können
- „vorhandene Testattrappen von `pipeline.run_chapter` in `tests/test_cli_main.py`
  durchsehen" — es gibt keine
- Der Auftrag verortete den zweiten Bearbeiter in `cli/`; tatsächlich stand er in den
  beiden Dateien des Beauftragten. Kosten: rund eine Stunde Umweg über einen
  Wegwerfordner samt einem Verfahren, am fremden Stand vorbeizucommitten
- Die Bilanzformel im Auftrag war um zwei Summanden zu kurz; der vermeintliche Fehlbetrag
  von 934 Einträgen galt eine Weile als Befund
- Die genannte Wegwerfumgebung hieß anders und lag im Scratchpad einer anderen Sitzung;
  zehn Minuten Suche über alle Sitzungsordner

Folge, wenn es niemand bemerkt: Ein Name oder eine Zahl aus einem Bericht wird in Code und
Test **eingefroren** und gilt danach als belegt — vier grüne Befehle sehen das nicht.
Stufe `schwer`.

Schließt an §5 an, „Womit zu verfälschen sei, ist eine Vermutung und kein Auftrag" —
dieselbe Wurzel, eine Ebene höher:

> **Regel:** Was ein Auftrag aus einem Bericht übernimmt — Funktionsname, Dateiname, Zahl,
> Ort des zweiten Bearbeiters —, wird als **Vermutung gekennzeichnet** und mit der Stelle
> genannt, aus der es stammt. Wer eine gekennzeichnete Vermutung antrifft, prüft sie am
> Bestand, bevor er darauf baut; bestätigt oder widerlegt gehört sie in den Bericht
> zurück.

Die Kennzeichnung kostet den Auftraggeber einen Halbsatz und erspart dem Beauftragten die
Wahl zwischen Glauben und Nachmessen.

### Ein „nicht selbst entscheiden"-Punkt braucht die Antwort rechtzeitig

Die beiden Regeln oben regeln, was der Auftrag **sagt**. Eine dritte, denselben Ursprungs,
regelt den **Zeitpunkt**: Ein ausdrücklich als „nicht selbst entscheiden" markierter Punkt
braucht eine Antwort, bevor der Bearbeiter die Stelle erreicht — nicht erst danach, wenn er
längst davor steht und entweder wartet oder doch selbst entscheidet.

> **Regel:** Markiert ein Auftrag einen Punkt ausdrücklich als „nicht selbst entscheiden",
> liegt die Antwort vor, wenn der Bearbeiter die Stelle erreicht.

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

**Bei einem reinen Dokumentationscommit ist das Tor nicht nur unvollständig, sondern
stumm** — aber nur, wenn der Diff **keine ausführbare Zeile und keine `.py`-Datei**
berührt. Kein Testlauf berührt Prosa — `grep` und der Augenschein sind dort der ganze
Prüfapparat. Beleg: In einer Durchsicht der Phase-1-Nachträge waren fünf von sechs
Befunden von einer Art, die kein Testlauf je angefasst hätte. Dieselbe stille Fehlerklasse
wie bei Code, nur ohne die vier Befehle, die überhaupt etwas melden könnten. Docstrings und
Regel-Kommentare sind dagegen Prosa **in** Code: Ein Einfalten in `tools/*.py` erzeugte
dort einmal an kollidierenden Anführungszeichen einen Syntaxfehler, den `ruff check`
gemeldet hätte. Der Verzicht auf die vier Befehle ist deshalb **begründungspflichtig** —
mit dem Diff als Begründung: keine ausführbare Zeile, keine `.py`-Datei.

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

**Ein Vorbefund ist ein Befund mit ausgewiesener Herkunft.** Bestand der Fehler schon vor
dem durchgesehenen Commit, gehört er dennoch in den Bericht — gesondert von den Befunden
am Commit ausgewiesen als „vor diesem Commit entstanden". Der Gegenstand der Durchsicht
ist der Commit, aber ein Durchsehender ist oft der Einzige, der die Stelle überhaupt
ansieht; bei strenger Auslegung „nur der Commit zählt" fiele ein solcher Vorbefund unter
den Tisch, ohne dass ihn je jemand sonst bemerkt.

### Die Durchsicht bedient die Kommandozeile wirklich

Beleg: In einer Durchsicht kamen drei von neun Befunden allein aus dem echten Durchlauf —
darunter der falsche „alles durchgesehen"-Ruf und der Durchsatzdiebstahl des verworfenen
Vorladefadens. Aus dem Quelltext waren sie plausibel, aber nicht sicher.

> **Regel:** Die Durchsicht ruft den Kern wirklich auf, statt nur den Quelltext zu lesen.
> Der billige Einstieg ist `cli.main.main(argv, read_line=…, write_line=…)`: keine Konsole
> zu füttern, kein Unterprozess. Er steht im Docstring von `cli/main.py`.

### Woran sie prüft: gegen den Commit, nicht gegen den Arbeitsbaum

Es laufen regelmäßig zwei Bearbeiter gleichzeitig (CLAUDE.md, „Aktueller Stand"). Wer im
Arbeitsbaum prüft, sieht deshalb fremde Änderungen mit, und ein rotes Ergebnis lässt sich
nicht zuordnen — hängt es am durchgesehenen Commit oder an der Arbeit des anderen? „Nur die
betroffenen Testdateien laufen lassen" verkleinert das Problem, löst es aber nicht.

> **Regel:** Die Durchsicht prüft gegen `git archive <commit>` in einem Wegwerfordner, nicht
> gegen den Arbeitsbaum. `tools/en-de.sqlite3` und `tools/*.epub` werden dorthin
> mitkopiert. Die **Gegenprobe** dafür ist die Schlusszeile von `pytest`: Sie muss mit
> installiertem PySide6 genau **drei** Übersprungene nennen — `needs_model` und
> `needs_wordfreq`, die einzigen beiden Marken, die nicht an `tools/` hängen (`addopts =
> ["-rs"]` in `pyproject.toml` nennt jeden Skip namentlich, ohne Zusatzaufwand), dazu der
> `pytest.skip()` im Rumpf von `test_gui_does_not_import_cli`
> (`tests/test_architecture.py`), solange `gui/` noch **kein Python-Modul** enthält —, und
> **vier** ohne PySide6, weil dann `needs_gui` als weitere Marke dazukommt. Meldet der Lauf
> stattdessen rund fünfunddreißig Übersprungene, ist die Kopie missraten — `tools/en-de.sqlite3`
> oder ein EPUB fehlt —, und die Durchsicht hält für grün, was gar nicht gelaufen ist. Zur
> Einordnung: rund 33 der über 560 Tests hängen an `tools/` (`needs_dictionary`,
> `needs_epub`, `needs_calibre_split_epub`) — diese Größenordnung darf danebenstehen, ist
> aber nicht die Prüfgröße; geprüft wird die Zahl **drei** (bzw. ohne PySide6: **vier**).
> Meldet der Lauf einen weniger als hier genannt, hängt in der Umgebung
> `LIBREVERBUM_MODEL_URL` oder `LIBREVERBUM_WORDFREQ_PYTHON` (`tests/conftest.py`) —
> falscher Alarm, kein falsches Grün; die betreffende Variable vor dem Lauf löschen.
>
> Zwischen AP 1 und AP 3 kam ein anderer, von PySide6 unabhängiger Übersprungener dazu —
> `pytest.skip()` im Rumpf von `test_rule_9_app_package_does_not_import_the_interfaces`
> (`tests/test_architecture.py`), solange das Paket `app/` noch nicht existierte. AP 3 hat
> `app/` angelegt (`421cb95`); seither ist dieser Skip weg. Sein Nachfolger ist der oben
> genannte `gui`-Skip — und der hängt **nicht am Verzeichnis**: AP 14 (`b2d5cab`) hat
> `gui/qml/Theme.qml` und `gui/fonts/` angelegt, das Verzeichnis gibt es also seither, aber
> Python bekommt `gui/` erst mit AP 15. Bedingung des Tests ist deshalb das **erste
> Python-Modul** darunter, nicht der Ordner; bis AP 15 bleibt es folglich bei
> **drei**/**vier**, danach gilt wieder **zwei**/**drei**.
>
> *Warum das hier steht:* Bis zur Nachbesserung von AP 14 stand an dieser Stelle „solange
> das Paket `gui/` noch nicht existiert" und „sobald `gui/` entsteht, fällt auch er weg".
> Beides war seit `b2d5cab` falsch, und CLAUDE.md verweist für die Begründung ausdrücklich
> hierher: Wer dem Verweis folgte, erwartete zwei Übersprungene, fand drei und hielt seine
> Wegwerfkopie für missraten — falscher Alarm an genau der Vorrichtung, mit der sich die
> Durchsicht selbst absichert (Befund B3, Durchsicht `b2d5cab`).

**Das Vergleichspaar einer Durchsicht ist der Commit selbst — `git show <commit>`,
gleichwertig `git diff <unmittelbarer Vorgänger> <commit>`.** Die Falle ist eine
**ältere Basis**: ein von Hand gewähltes „Vorher", das mehr als einen Commit
zurückliegt, zieht die dazwischenliegende fremde Arbeit in den Diff und droht als Befund
gegen den falschen Bauenden auszufallen. Beleg: `git diff b663678 0b09b7d` schloss den
dazwischenliegenden Commit `29e137d` (fremde README-Arbeit, 23 Zeilen) mit ein, aus denen
beinahe ein Befund gegen den falschen Bauenden entstanden wäre; entdeckt nur, weil die
Zuordnung vor dem Formulieren noch einmal geprüft wurde.

**Ein eigenes Prüfskript meldet seine Trefferzahl und wird gegen eine unabhängig bekannte
Größe gehalten, bevor sein Ergebnis zählt.** Beleg: Ein Verweisskript beim Einfalten von
Nachträgen suchte das typografische Anführungszeichenpaar `„…"` und meldete zwei Treffer,
weil der Bestand öffnend `„` (U+201E), schließend aber ASCII `"` verwendet — die
tatsächliche Zahl lag bei 518. Gerettet hat nur, dass der Auftrag „rund 160 Stellen"
nannte und zwei dagegen absurd war: genau das falsche Grün, das die Durchsicht sucht —
null tote Verweise, weil überhaupt keine Verweise gefunden wurden.

**Ein Verfälschungslauf im Wegwerfordner wird in `timeout` gewickelt** (etwa
`timeout 900 pytest …`, **in Git Bash** — dort ist `timeout` das GNU-Werkzeug), damit eine
falsche Umsetzung **rot** wird, statt zu hängen — der Hänger ist sonst die einzige
Fehlerform, die überhaupt kein Ergebnis liefert. **Unter PowerShell heißt derselbe Name
etwas anderes**: `timeout` löst dort auf Windows' Pausenbefehl auf, und `timeout 900
pytest …` bricht sofort mit „Ungültige Syntax" und Exit 1 ab, **ohne `pytest` je
auszuführen** — ein Exit ≠ 0 sähe dann wie eine bestandene Verfälschungsprobe aus, obwohl
keine stattgefunden hat. Ein Verfälschungslauf gehört deshalb in Git Bash. Begründung und
die drei Anlässe für die Zeitschranke selbst: technik.md §6, „Zeitschranke: Hängeschutz
über die Shell, nicht über `pytest-timeout`".

**Die eigenen Messskripte der Durchsicht liegen dagegen außerhalb dieses Ordners.** Sonst
prüft das Tor sie mit — und ihr Rot sieht aus wie Rot des durchgesehenen Commits: Am
01.09.2026 machten 18 Meldungen aus dem Prüfcode selbst `ruff format --check .` und
`ruff check .` rot, in einem Commit, der beide bestanden hatte.

**`PYTHONUTF8=1` bzw. `PYTHONIOENCODING=utf-8` für jedes eigene Prüfskript der
Durchsicht, und Textvergleiche über `repr()` statt über das Auge.** Belege: Ein
Prüfskript, das mit `print` protokolliert, starb beim Wort `iodoform` an einem `₃` in der
WikDict-Übersetzung, weil `print` gegen cp1252 schrieb — ein vollständiger
Wiederholungslauf. Der Kern selbst fängt das ab (`cli.display.safe_print`), das
Prüfskript nicht. Und: Die Windows-Konsole zerstört in jeder Werkzeugausgabe Umlaute und
typografische Zeichen, sodass `anki._UNCERTAIN_TEXT` und `printout._UNCERTAIN_MARK` samt
Zusatz identisch aussahen, obwohl sich Halbgeviertstrich und Bindestrich unterschieden —
hier hätte ein falsches Ergebnis durchgehen können.

Das Vorgehen hat sich in drei Durchsichten und drei Abnahmeläufen im August 2026 bewährt und
kostet einen Befehl. Es ersetzt nicht das Tor auf der Seite des Bauenden (CLAUDE.md, „Prüfen
vor »fertig«"), sondern beantwortet dessen offene Frage: woran „grün" bei zwei Bearbeitern
überhaupt gemessen ist.

### Nach jedem Prüfpunkt ein Zwischenergebnis in eine Datei

Die Durchsicht läuft mehrere Prüfpunkte hintereinander ab und kann mittendrin abbrechen.
Beleg: Zwei Durchsichten starben mitten in den Verfälschungsproben — eine am
Sitzungslimit, eine an einem Serverfehler. Beim Serverfehler rettete genau diese, im
Einzelfall zugerufene Anweisung rund eine Stunde Messarbeit; im anderen Fall war der
erhaltene Stand Glück.

> **Regel:** Die Durchsicht schreibt nach jedem Prüfpunkt ein Zwischenergebnis in eine
> Datei — nicht erst am Ende. Das gehört ins Vorgehen, nicht in einen Zuruf im Einzelfall.

### Befund und Beobachtung sind zweierlei

Ein **Befund** betrifft **das Gebaute**. Er geht an die Teilaufgabe zurück und ist erledigt,
wenn die Stelle behoben ist; bleibt er dort als Begründung stehen, trägt er die Marke aus
§4. Eine **Beobachtung** betrifft **den Ablauf**, geht in den Bericht (§9) und wird an einem
Tor eingefaltet. Wer beides in denselben Kanal wirft, verliert die Beobachtung — die
Teilaufgabe ist danach zu, der Ablauf bleibt derselbe.
