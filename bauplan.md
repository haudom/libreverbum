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
| **E8b** | Anki-Erzeugung | T13 | offen. Ausschlusskriterium: Die Bibliothek muss die **GUID zugänglich** machen, sonst ist Regel 6 nicht erfüllbar |
| **E8c** | Druckausgabe | T14 | offen. Erzeugtes HTML im Browser drucken wäre die abhängigkeitsfreie Möglichkeit |
| **E10** | Reihenfolge und Anreicherungstiefe | T11, T15, T16 | **entschieden am 17.08.2026** (konzept.md, Nachtrag beim Kernablauf): Bedeutungen **vor** der Triage, die Tiefe als Einstellung. Zwei Messungen stehen noch aus, siehe unten |

**Damit ist Tor 0 für Tor 1 und Tor 2 offen.** E8b und E8c bleiben liegen bis kurz vor T13
und T14 — dann ist bekannt, welche Felder eine Karte wirklich trägt.

**E10 ist entschieden, aber zwei Zahlen fehlen**, und beide ändern, *was* gebaut wird — nicht
nur wie:

- **Wie viele Grundformen eines Kapitels sind überhaupt mehrdeutig?** Davon hängt ab, ob eine
  Triage-Entscheidung je Wort genügt oder bei manchen Wörtern je Bedeutung getroffen werden
  muss. Deckt sich mit dem Messauftrag, der ohnehin in T18 steht (Wirkung der Wortart als
  Vorfilter auf lange Auswahllisten)
- **Skaliert das Bündeln beim Modell?** technik.md §3 hat „12 Sekunden für alle 16 in einer
  einzigen Anfrage" gemessen. Gilt das auch für 64, ist die teure Stellung der Einstellung
  bezahlbar; wächst die Zeit überproportional oder bricht die Antwortform, ist sie es nicht

Solange die zwei Zahlen fehlen, sind **T11 und T15 nicht anzufangen** — T11 müsste sonst raten,
ob es einzeln oder gebündelt fragt, und T15 müsste die Reihenfolge raten.

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
| **T4** | Mehrwortausdrücke: zusammenhängende Kandidatenfolgen **und** getrennte Verb-Partikel-Paare aus der Abhängigkeitsanalyse — die gemessenen 21 %. Liefert Kandidaten und schlägt nicht nach | getrennter Fall (`gave the idea up`) wird gefunden |

### Strang B — `dictionary`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T5** | Auswahlliste je Grundform und Wortart. Regel 1: Zeilen ohne `sense`-Text bleiben drin, nach `score` absteigend, beschriftet als „Hauptbedeutung, ohne nähere Angabe". Die Abfrage steht in `tools/sense_check.py` bereits richtig | `watch` und `draw` liefern ihre Hauptbedeutung |
| **T6** | Erstbezug: Herunterladen, Prüfsumme, von Hand hinterlegte Datei, Hinweis auf Herkunft und Lizenz beim ersten Start (technik.md §2, „Warum nicht mitgeliefert"). Dabei den **Index auf `translation(written_rep)`** anlegen — die Datei bringt keinen mit, und ohne ihn kostet ein Kapitel 32 bis 44 s statt 1,1 s (technik.md §3, „Nachtrag 17.08.2026") | fehlende Datei ergibt einen sichtbaren Fehlschlag, kein leeres Ergebnis |
| **T7** | Abgleich der Kandidaten aus T4 gegen die Wendungen, Filter `score ≥ 50` und Wortart nicht `Proper_noun`. Ohne Eintrag: `uncertain` statt verwerfen | Regeln 10 und 11 |

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
| **T12b** | Fließtext mit `html.parser`, Vorspann und Impressum aussteuern. Die drei Ablehnfälle melden statt leer zurückgeben: kein ZIP-Archiv, Bildband ohne Text, verschlüsselt | Regel 13 an allen drei Fällen |

`tools/epub_check.py` hat beide Schritte an zwölf Dateien vorgeführt — es ist die Vorlage,
nicht der Kern: Es misst, T12 baut.

### Strang F — `anki` und `printout`

| # | Teilaufgabe | Prüfung |
|---|---|---|
| **T13** | Deck mit Wort, Grundform, Übersetzung, Wortart, Belegsatz, Buch und Kapitel; Verschlagwortung; Kartenrichtung je Export wählbar; GUID **zurückgeben** — geschrieben wird sie in `profile`, sonst kennt `anki` zwei Schritte | Regel 6, Abnahmekriterium 4 |
| **T14** | Kapitelliste als Druckseite, zweispaltig, auf ein Blatt | Abnahmekriterium 5 |

Brauchen E8b und E8c. Bei T14 fällt der offene Punkt aus technik.md §7 an, wohin die Liste
„Figuren & Orte" gehört.

---

## Tor 3 — Verkettung, seriell

| # | Teilaufgabe |
|---|---|
| **T15** | `pipeline`: ein Durchlauf für ein Kapitel. Sinnvollerweise als Durchstich angelegt, sobald T3, T5 und T8 stehen — dann zeigt sich früh, ob `entities` trägt |
| **T16** | Kommandozeilenzugang, Triage über die Tastatur. Hier liegen die Vorgaben aus technik.md §9: Verzeichnis bestimmen, `config.toml` mit `tomllib` lesen, fehlende Datei einmalig aus einer Vorlage anlegen — der Kern bekommt nur fertige Pfade und Adressen |

---

## Tor 4 — Abnahme

| # | Teilaufgabe |
|---|---|
| **T17** | Durchlauf an einem echten, DRM-freien EPUB. Kriterien 1 bis 6, davon 3 als Handstichprobe über zwanzig Wörter mit mindestens drei mehrdeutigen und zwei Redewendungen, 4 als echter Import in Anki |
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
- **E8b und E8c sind offen** und stehen oben in Tor 0
