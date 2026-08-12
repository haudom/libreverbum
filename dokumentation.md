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

**Namen aus fremden Quellen werden nie übersetzt**: `token.lemma_`, `token.pos_` sowie die
WikDict-Spalten `sense`, `score`, `lexentry`, `written_rep`. Eine Übersetzung erzeugte zwei
Namen für dasselbe Ding — die Verwechslung, die laut `technik.md` §3 schon einmal zu
falschen Messergebnissen geführt hat.

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
| Profil, Kenntnisstand | `profile`, `knowledge_state` |
| bekannt / lernt / zurückgestellt / vergessen | `known` / `learning` / `deferred` / `forgotten` |
| Herkunft (einer Kenntnisangabe) | `origin` |
| Triage, Sammelaktion, Wortobergrenze | `triage`, `bulk_mark`, `word_limit` |
| Wörterbuch, Nachschlagen | `dictionary`, `lookup` |
| Karte, Deck, Kartenrichtung | `card`, `deck`, `card_direction` |
| unsicher (markierter Eintrag) | `uncertain` |

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
| 10, 11 unsichere Wendungen | Wendung ohne Wörterbucheintrag ist `uncertain` |
| 12 Eigennamen je Vorkommen | `red` bleibt Lernvokabel, obwohl es auch in einem Namen steht |
| 13 nichts scheitert leise | unerreichbarer Modellserver ergibt einen sichtbaren Fehlschlag, kein stilles Loch in der Wortliste |

Regeln 3, 8 und 9 sind Bauentscheidungen ohne sinnvollen Testpunkt — sie bleiben beim
Regel-Kommentar.

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
