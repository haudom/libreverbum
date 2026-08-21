# LibreVerbum — Bauplan für Phase 1

> Stand: 12.08.2026 · Ergänzt [konzept.md](konzept.md) (*was*), [technik.md](technik.md)
> (*womit*) und [dokumentation.md](dokumentation.md) (*wie geschrieben wird*). Hier steht,
> **in welcher Reihenfolge** gebaut wird — und was gleichzeitig gebaut werden darf.

Dieses Dokument ist **auf Phase 1 begrenzt**. Ist der Durchlauf abgenommen, fällt es weg;
was daraus dauerhaft gilt, wandert vorher in die drei anderen (dokumentation.md §7, „Am
Phasenende einfalten"). Es begründet nichts neu, sondern verweist.

## Was die Reihenfolge bestimmt

Drei bereits gefallene Festlegungen geben die Struktur vollständig vor:

- **Die Importregel** (technik.md §7): Jeder Schritt kennt nur `entities`, verkettet wird
  allein in `pipeline`. Das ist der Grund, warum acht Module gleichzeitig entstehen dürfen,
  sobald `entities` steht — und warum `entities` die einzige echte Engstelle ist
- **Die zwingende Reihenfolge** Wortart → Grundform → Nachschlagen (technik.md, „Warum die
  Reihenfolge zwingend ist") ist eine **Laufzeit**reihenfolge, keine Bau-Reihenfolge.
  `extraction` und `dictionary` dürfen deshalb nebeneinander entstehen; sie importieren
  einander nicht
- **Regel 14** (dokumentation.md §4) schneidet den Umfang: kein JSON-Ausleiten des Profils,
  kein Lesezeichendruck, keine Cloud-Gegenstelle, kein ganzes Buch. Alles das steht im
  Phasenplan weiter hinten

**Jede Teilaufgabe unten ist ein Commit**, der die vier Befehle aus technik.md §6 besteht.

**Jedes Tor endet mit dem Einfalten** (dokumentation.md §9): Die Beobachtungen aus den
Berichten der abgeschlossenen Teilaufgaben werden durchgegangen — Nachträge wandern
vollständig in die Dokumente, Vorschläge zur Hausordnung nach Stufe: `schwer` und `mittel`
werden entschieden, `leicht` bleibt liegen. **Bei T18** wird jeder verbliebene Punkt
eingefaltet oder gestrichen. Solange die Liste nicht leer ist, steht sie in `nacharbeit.md`.

**Verlangt eine Teilaufgabe zwei Wege, nennt die Prüfspalte beide.** Die Prüfspalte wird als
Auftragsumfang gelesen — das ist die naheliegende Lesart und keine Nachlässigkeit. Nennt sie
nur einen der beiden Wege, entsteht folgerichtig die Hälfte, ohne Fehler und ohne Meldung.
Bei T4 ist genau das passiert.

## Festlegung dieses Plans: die Triage läuft zuerst über die Kommandozeile

Phase 1 wird über den Kommandozeilenzugang abgenommen, die Qt-Oberfläche kommt danach
(Tor 5). Begründung: Regel 14 und technik.md §1, wonach der Zugang „praktisch geschenkt"
ist, sobald der Kern die Oberfläche nicht kennt. Abnahmekriterium 7 — Triage in unter zehn
Minuten — ist damit erreichbar, aber spartanisch; es ist im Konzept ausdrücklich optional.

Die Kommandozeile **ist eine Oberfläche** und gehört damit nicht in den Kern, sondern
daneben. Die Modulkarte deckt das nicht ab, weil sie nur den Kern beschreibt.

---

## Tor 0 — Vorentscheidungen, die Code blockieren

Kein Code. Regel 15 verlangt die Lizenzprüfung **vor** der Aufnahme.

| # | Entscheidung | blockiert | Stand |
|---|---|---|---|
| **E8a** | EPUB-Leser | T12 | **entschieden am 12.08.2026** (technik.md §8): keine Bibliothek, Standardbibliothek genügt — gemessen an zwölf Dateien |
| **E9** | Ablage und Konfiguration | T5, T8, T11 | **entschieden am 12.08.2026** (technik.md §9): plattformübliches Verzeichnis, Pfade als Argument, `config.toml` |
| **E8b** | Anki-Erzeugung | T13 | **entschieden am 21.08.2026** (technik.md §8b): `genanki`, MIT. Ausschlusskriterium erfüllt — `Note.guid` ist les- und setzbar; die GUID vergibt LibreVerbum trotzdem selbst |
| **E8c** | Druckausgabe | T14 | **entschieden am 21.08.2026** (technik.md §8c): keine Bibliothek — erzeugtes HTML mit Druck-CSS, gedruckt im Browser |
| **E10** | Reihenfolge und Anreicherungstiefe | T11, T15, T16 | **entschieden am 17.08.2026** (konzept.md, Nachtrag beim Kernablauf): Bedeutungen **vor** der Triage, die Tiefe als Einstellung. Beide Messungen liegen vor (18. und 19.08.2026), siehe unten |

**Tor 0 ist damit vollständig.** E8b und E8c sind wie vorgesehen erst kurz vor T13 und T14
gefallen — da stand fest, welche Felder eine Karte wirklich trägt.

**E10 ist entschieden. Die zwei Zahlen, die ändern, *was* gebaut wird — nicht nur wie —,
liegen seit dem 18. und 19.08.2026 vor:**

- **Wie viele Grundformen eines Kapitels sind überhaupt mehrdeutig? — gemessen**
  (technik.md §3, „Nachtrag 18.08.2026: zwei Drittel der Grundformen eines Kapitels sind
  mehrdeutig", `tools/ambiguity_check.py`): **65,8 %** und **66,0 %** über 32 Kapitel zweier
  Romane, Median 3 Bedeutungen unter den mehrdeutigen. Antwort auf die Frage: **eine
  Triage-Entscheidung je Wort genügt** — je Bedeutung wäre der Faktor 3,0, rund 4.000
  Einträge je Kapitel, und Abnahmekriterium 7 nicht mehr erreichbar. Die gewählte Bedeutung
  gehört aber in die **Anzeige** der Triage, nicht bloß das Wort
- **Skaliert das Bündeln beim Modell? — gemessen** (technik.md §3, „Nachtrag 19.08.2026:
  Bündeln lohnt nicht", `tools/bundle_check.py`): Bündeln ist je nach Modell bis zu
  2,4-fach schneller, wählt aber bei **23 bis 37 %** der Wörter eine andere Bedeutung als
  der Einzellauf. Antwort: **T11 fragt je Wort einzeln**, ein Bündelmechanismus entfällt
  ersatzlos. Nebenbefund mit Betriebswirkung: Der Server kürzt Prompts über 4.096 Token
  still und meldet die gekürzte Größe

Damit sind **T15 und T11 frei**: Die Reihenfolge steht seit Entscheidung 10, die Einheit
der Triage ist das Wort, und T11 weiß nun, dass es je Wort einzeln fragt.

---

## Tor 1 — Fundament, streng seriell

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T1** | `entities`: die sieben Gegenstände aus technik.md §4 als Datenklassen, dazu die Aufzählungen `known` / `learning` / `deferred` / `forgotten`, `origin`, `card_direction`, `uncertain`. Kein I/O, importiert nichts aus dem Kern. Dabei den Docstring in `libreverbum/__init__.py` nachziehen — „Aufteilung noch nicht festgelegt" stimmt seit Entscheidung 7 nicht mehr | `mypy` streng, `test_architecture` bleibt grün |
| **T2** | Testgrundlage: ein Mini-Wörterbuch im WikDict-Schema, das der Test selbst anlegt (`watch`, `draw`, `saw`, `bank`, `give up`, `red`, `street`), ein Mini-EPUB, das der Test selbst als ZIP zusammensetzt — einmal mit und einmal ohne Navigation —, eine Attrappe für den Modellserver, dazu die Marken `needs_dictionary` und `needs_model` | Ohne T2 hängt die halbe Testsuite an unversionierten Dateien und einem laufenden Modellserver |

T2 darf neben T1 laufen: Die Wörterbuch-Vorrichtung braucht WikDicts Schema, nicht
`entities`.

---

## Tor 2 — sechs Stränge, untereinander parallel

Alle hängen an T1 und an sonst nichts. Innerhalb eines Strangs wird nacheinander gebaut,
weil dieselbe Datei betroffen ist.

### Strang A — `extraction`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T3** | Tokenisierung, Wortart, Lemmatisierung, Eigennamenfilter **je Vorkommen** (Regel 12), Hilfsverbformen aussteuern (technik.md §5, offener Punkt `could`/`having`), Häufigkeit je Kapitel, Belegsatz | Regel 2 (`He saw her…` ergibt *see*), Regel 12 (`red` bleibt Lernvokabel), Abnahmekriterium 2 |
| **T4** | Mehrwortausdrücke auf **zwei** Wegen: zusammenhängende Kandidatenfolgen (n-Gramme gegen das Wörterbuch, dann Filter) **und** getrennte Verb-Partikel-Paare (spaCys Abhängigkeitsanalyse) — die gemessenen 21 %. Liefert Kandidaten und schlägt nicht nach | **beide** Wege: zusammenhängender Fall (`out of the way`) wird gefunden **und** getrennter Fall (`gave the idea up`) wird gefunden |

### Strang B — `dictionary`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T5** | Auswahlliste je Grundform und Wortart. Regel 1: Zeilen ohne `sense`-Text bleiben drin, nach `score` absteigend, beschriftet als „Hauptbedeutung, ohne nähere Angabe". Die Abfrage steht in `tools/sense_check.py` bereits richtig | `watch` und `draw` liefern ihre Hauptbedeutung |
| **T6** | Erstbezug: Herunterladen, Prüfsumme, von Hand hinterlegte Datei, Hinweis auf Herkunft und Lizenz beim ersten Start (technik.md §2, „Warum nicht mitgeliefert"). Dabei den **Index auf `translation(written_rep)`** anlegen — die Datei bringt keinen mit, und ohne ihn kostet ein Kapitel 32 bis 44 s statt 1,1 s (technik.md §3, „Nachtrag 17.08.2026") | fehlende Datei ergibt einen sichtbaren Fehlschlag, kein leeres Ergebnis |
| **T7** | Abgleich der Kandidaten aus T4 gegen die Wendungen, Filter `score ≥ 50` und Wortart nicht `Proper_noun`. Ohne Eintrag entscheidet die Herkunft des Kandidaten: Der Verb-Partikel-Weg markiert `uncertain`, der n-Gramm-Weg **verwirft** — dort ist der Filter genau das Mittel, das `of the` wieder aussortiert (`dictionary.py`, „Liefert") | Regeln 10 und 11 |

### Strang C — `profile`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T8** | Schema anlegen, `PRAGMA user_version` (Regel 5), Kenntnis **pro Bedeutung**, Ereignisfolge statt überschreibbarem Zustand (technik.md §4) | Regel 4 (Profilzugriff öffnet nie `en-de.sqlite3`), Regel 5 |
| **T9** | Kenntnisstand als Sicht auf die Ereignisse, Abgleich gegen den Kapitelwortschatz, Kennzeichnung „neue Bedeutung eines bekannten Wortes" | Abnahmekriterium 6 |

### Strang D — `triage` und `translation`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T10** | `triage`: Häufigkeitssortierung, Wortobergrenze, Sammelaktion. Reine Rechnung ohne I/O — der leichteste Einstieg und vollständig prüfbar | Sammelaktion markiert alle häufigeren Wörter, Obergrenze stellt den Rest zurück |
| **T11** | `translation`: Aufruf über die OpenAI-kompatible Schnittstelle, `reasoning_effort: "none"` (Regel 7), Antwortform per JSON-Schema, Auswahl aus der Liste (Regel 11), Ausweichantwort „keine passt" (technik.md §3, offener Punkt), Fehlschlag sichtbar (Regel 13). Dabei entscheiden, was eine **leere Auswahlliste** wird: 3,3 % davon sind kein fehlender Eintrag, sondern ein Wortartunterschied (technik.md §3, offener Punkt „Die Wortart als Filter") | Regel 7, Regel 13 gegen die Attrappe aus T2 |

Die Ausweichantwort ist kein Beiwerk: Ohne sie hat das Modell kein Mittel, einen Fehler der
Vorstufe zu melden — der `saw`-Fall aus technik.md §3.

### Strang E — `epub`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T12** | Struktur: `container.xml` → OPF → Metadaten, `spine`, Navigation. Kapitelliste nach **eindeutigen Zielen**; fehlt die Navigation, gilt jedes Dokument als Kapitel — mit Hinweis (technik.md §8) | Abnahmekriterium 1; Datei ohne Navigation ergibt Kapitel **und** Hinweis |
| **T12b** | Fließtext mit `html.parser`, Vorspann und Impressum aussteuern — über die Project-Gutenberg-Textmarken aus `tools/coverage_check.py`; Dateien ohne diese Marken bleiben unverändert, auch die T17-Datei. Die drei Ablehnfälle melden statt leer zurückgeben: kein ZIP-Archiv, Bildband ohne Text, verschlüsselt | Regel 13 an allen drei Fällen |

`tools/epub_check.py` hat beide Schritte an zwölf Dateien vorgeführt — es ist die Vorlage,
nicht der Kern: Es misst, T12 baut.

### Strang F — `anki` und `printout`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T13** | Deck mit Wort, Grundform, Übersetzung, Wortart, Belegsatz, Buch und Kapitel; Verschlagwortung; Kartenrichtung je Export wählbar; GUID **zurückgeben** — geschrieben wird sie in `profile`, sonst kennt `anki` zwei Schritte | Regel 6, Abnahmekriterium 4 |
| **T14** | Kapitelliste als Druckseite, zweispaltig, auf ein Blatt | Abnahmekriterium 5 |

Beide hängen an E8b und E8c, seit dem 21.08.2026 entschieden (Tor 0). Bei T14 fällt der
offene Punkt aus technik.md §7 an, wohin die Liste
„Figuren & Orte" gehört.

---

## Tor 3 — Verkettung, seriell

| # | Teilaufgabe |
|---|---|
| **T15** | `pipeline`: ein Durchlauf für ein Kapitel. Sinnvollerweise als Durchstich angelegt, sobald T3, T5 und T8 stehen — dann zeigt sich früh, ob `entities` trägt |
| **T16** | Kommandozeilenzugang, Triage über die Tastatur. Hier liegen die Vorgaben aus technik.md §9: Verzeichnis bestimmen, `config.toml` mit `tomllib` lesen, fehlende Datei einmalig aus einer Vorlage anlegen — der Kern bekommt nur fertige Pfade und Adressen. Zwei Entscheidungen fallen hier mit: wie `entries` und `expressions` aus `pipeline.run_chapter` in der Triage-Liste zueinanderstehen — 213 Wendungen je Kapitel, keine davon als Einzelwort erfasst, und T17 braucht daraus zwei Redewendungen für Abnahmekriterium 3 —, und ob ein noch nicht vorhandenes Profil bestätigt werden muss, statt wortlos leer angelegt zu werden |

---

## Tor 4 — Abnahme

| # | Teilaufgabe |
|---|---|
| **T17** | Durchlauf an einem echten, DRM-freien EPUB. Kriterien 1 bis 6, davon 3 als Handstichprobe über zwanzig Wörter mit mindestens drei mehrdeutigen und zwei Redewendungen, 4 als echter Import in Anki. Dabei die **Wortobergrenze beurteilen** (konzept.md, Schritt 4): Am 21.08.2026 erwogen zu streichen und unverändert gelassen — ob „maximal 25 neue Wörter" trägt, zeigt erst der erste echte Durchlauf. Mitzudenken: Abnahmekriterium 5 ruht auf der Grenze (technik.md §8c, „Gemessene Ergebnisse: »passt auf ein Blatt« ist gedeckt"); `Origin.WORD_LIMIT` steht bereits im Profilschema, ersatzloses Streichen wäre also eine Schemaänderung mit `user_version`-Sprung (Regel 5); erwogen und nicht gewählt wurde, die Grenze zur Einstellung mit zulässigem Wert „aus" zu machen — Präzedenzfall ist Entscheidung 10 vom 17.08.2026 (konzept.md, Schritt 4, Anreicherungstiefe) |
| **T18** | Dokumente nachziehen: Schemaspalten festhalten, „Figuren & Orte" verorten, Wirkung der Wortart als Vorfilter auf lange Auswahllisten **messen** statt vermuten (technik.md §3, `run` mit 48 Bedeutungen), Stand in CLAUDE.md. Dazu die letzte Auflösung von `nacharbeit.md`: jeder verbliebene `leicht`-Punkt wird eingefaltet oder gestrichen, dann fällt die Datei weg |

## Tor 5 — Oberfläche, nach der Abnahme

Qt Quick: Kapitelauswahl, Triage-Liste, Fortschritt. Regel 9 gilt hier zum ersten Mal in
ihrer nicht prüfbaren Hälfte — NLP- und Modellaufrufe nie im Oberflächen-Thread.

---

## Abhängigkeiten auf einen Blick

```
E9  ─┐
E8a ─┼──────────────┐
E8b ─┼──────────┐   │
E8c ─┼──────┐   │   │
     │      │   │   │
T1 entities ┴───┴───┴───┐              T2 Vorrichtungen (neben T1)
 │                      │
 ├─ T3 → T4   extraction ┐
 ├─ T5 → T6, T7 dictionary
 ├─ T8 → T9   profile    ├→ T15 pipeline → T16 CLI → T17 Abnahme → T18 Doku
 ├─ T10       triage     │
 ├─ T11       translation┤
 ├─ T12       epub       │
 └─ T13, T14  anki/print ┘
```

**Zwingend nacheinander:** T1 vor allem übrigen · innerhalb jedes Strangs · E8a vor T12,
E8b vor T13, E8c vor T14 · T15 nach den Schritten · T17 zuletzt.

**Frei parallel:** die sechs Stränge untereinander, T2 neben T1, T10 neben T11.

**Grenze der Parallelität:** Jeder Strang schreibt Typen nach `entities`. Fehlt dort etwas,
kollidieren gleichzeitig laufende Stränge an derselben Datei. Tragfähig sind etwa drei
Stränge; begonnen wurde mit A und B, weil sie die Unsicherheit trugen und die Gegenstände
am stärksten festlegen. Die Unsicherheit ist ausgeräumt: `mypy --strict` trägt die
spaCy-Typen (technik.md §6, „Nachtrag 17.08.2026").

## Offene Punkte

- **Wo die Kommandozeile liegt** — `libreverbum/__main__.py` als dünner Aufruf oder ein
  eigenes Paket daneben. Zu entscheiden bei T16, nicht vorher
- **Ob der Durchstich in T15 genügt** oder `pipeline` je Schritt eine Zwischenablage
  braucht (technik.md §7, offener Punkt). Erst messen, dann bauen
