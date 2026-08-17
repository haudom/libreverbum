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
| Triage, Sammelaktion, Wortobergrenze | `triage`, `bulk_mark`, `word_limit` |
| Wörterbuch, Nachschlagen | `dictionary`, `lookup` |
| Auswahlliste, Kandidat | `candidate` |
| Übersetzung | `translation` |
| Karte, Deck, Kartenrichtung, Lückentext | `card`, `deck`, `card_direction`, `cloze` |
| Druckausgabe | `printout` |
| unsicher (markierter Eintrag) | `uncertain` |
| Gegenstand des Kernablaufs | `entity` |
| Durchlauf, Verkettung der Schritte | `pipeline` |
| Lesereihenfolge, Manifest (EPUB) | `spine`, `manifest` |
| Inhaltsverzeichnis einer Datei | `navigation` |
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
den Bericht (§9). Das kostet Minuten und ersetzt einen Teil der Durchsicht durch Mechanik —
wo es getan wurde, hat der Bauende die Falle selbst gefunden, um die es ging.

---

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

**Am Phasenende einfalten.** Ist eine Phase abgeschlossen, wandern die noch nützlichen
Nachträge in den Fließtext, der Rest fällt weg. Sonst wird aus einzelnen Nachträgen über
zwanzig Entscheidungen hinweg eine Sedimentschicht.

---

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

**Eingefaltet wird an den Toren** aus bauplan.md: Dort wird die gesammelte Liste
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

**Abgearbeitet werden `schwer` und `mittel`.** `leicht` bleibt liegen und wird von Hand
angestoßen, wo es sich lohnt — **spätestens am Phasenende** wird jeder verbliebene Punkt
eingefaltet oder ersatzlos gestrichen. Streichen ist dort oft die richtige Antwort, weil
die Reibung inzwischen weg ist. Ohne diesen Termin zeigt die Verfallsklausel der
Sammelliste ins Leere, und aus dem Rest wird die Sedimentschicht aus §7.
