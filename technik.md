# LibreVerbum — Technische Entscheidungen

> Stand: 12.08.2026 · Ergänzt [konzept.md](konzept.md), das die inhaltliche Seite
> beschreibt. Hier steht nur, **womit** gebaut wird — und warum.
> Wie geschrieben und dokumentiert wird, steht in [dokumentation.md](dokumentation.md).

## Entscheidungsreihenfolge

Die technischen Fragen hängen voneinander ab. In dieser Reihenfolge lösen sie sich
am saubersten auf:

| # | Frage | Stand |
|---|---|---|
| 1 | Programmiersprache und Oberflächentechnik | **entschieden** (11.08.2026) |
| 2 | Wörterbuch- und Häufigkeitsdaten samt Lizenzlage | **entschieden** (11.08.2026) |
| 3 | Lokales Modell und Betriebsart | **entschieden** (11.08.2026) |
| 4 | Ablage des Profils (Datenbankform) | **entschieden** (11.08.2026) |
| 5 | Lemmatisierung und Eigennamenerkennung (spaCy oder Stanza) | **entschieden** (12.08.2026) |
| 6 | Projektgerüst und Werkzeuge | **entschieden** (12.08.2026) |
| 7 | Modulaufteilung des Kerns und Importregel | **entschieden** (12.08.2026) |
| 8 | EPUB-Leser | **entschieden** (12.08.2026) |
| 8b | Anki-Erzeugung | **entschieden** (21.08.2026) |
| 8c | Druckausgabe | **entschieden** (21.08.2026) |
| 9 | Ablage und Konfiguration zur Laufzeit | **entschieden** (12.08.2026) |

Frage 5 stand anfangs nicht auf der Liste. Sie ist aus Frage 2 entstanden, deren Messung
mit der Folgerung endete, nicht die Datenquelle sei der Engpass, sondern die
Lemmatisierung — siehe Abschnitt 5.

Frage 6 ist von anderer Art als 1 bis 5: keine inhaltliche Vorfrage, sondern das Gerüst,
in dem gebaut wird. Sie kommt zuletzt, weil sie erst beantwortbar war, als die
Abhängigkeiten feststanden — und sie kommt überhaupt, weil der Code zum großen Teil
maschinell entsteht. Siehe Abschnitt 6.

Die Fragen 8b und 8c sind aus Frage 8 hervorgegangen — dieselbe Lizenzprüfung, aber für die
Ausgabe statt für die Eingabe. Sie sind zuletzt gefallen, weil erst mit T13 und T14
feststand, welche Felder eine Karte und eine Druckseite wirklich tragen. Der Bauplan der
Phase 1 führte die drei als E8a, E8b und E8c.

Frage 7 gehört zu 6 und steht unmittelbar vor der ersten Zeile Anwendungscode: nicht
womit gebaut wird, sondern wohin das Gebaute kommt. Sie wird vorab entschieden, weil eine
Aufteilung, die nebenbei entsteht, in jeder Sitzung neu entsteht — und sich nicht mehr
ändern lässt, sobald anderer Code auf ihr aufbaut. Siehe Abschnitt 7.

Frage 2 stand bewusst weit oben, weil sie das Konzept hätte kippen können: Ein freies,
offline nutzbares EN→DE-Wörterbuch mit sauberer Lizenz **und** Bedeutungsangaben ist
nicht selbstverständlich. Ohne eine solche Quelle hätte der Hybrid-Ansatz aus
Abschnitt 5 des Konzepts anders aussehen müssen. Die Recherche hat eine passende
Quelle gefunden — siehe Abschnitt 2.

---

## 1. Programmiersprache — entschieden

**Python als einzige Sprache. Oberfläche mit Qt Quick über PySide6.**

### Anforderungen, die zu dieser Wahl geführt haben

- Zielplattformen **Windows und Linux**, Desktop-Anwendung
- Lemmatisierung und Eigennamenerkennung müssen wirklich gut sein
  (→ Abnahmekriterien 2 und 6 im Konzept)
- Die Oberfläche soll sich flüssig anfühlen; später auch modern und reaktiv.
  Konkreter Anspruch: ein Schiebemenü soll **am Zeiger kleben**, statt eine
  Animation abzuspielen
- Lernaufwand für neue Techniken in Grenzen halten
- Zunächst Eigennutzung; eine spätere Veröffentlichung soll nicht verbaut werden

### Warum Python den Kern bildet

Alles, woran das Konzept technisch scheitern kann, hängt an Bibliotheken, die es
außerhalb von Python praktisch nicht in vergleichbarer Reife gibt:

- **Lemmatisierung, Wortarten und Eigennamenerkennung** — spaCy und Stanza sind hier
  der Stand der Technik. Ohne sauberes Lemma lernt das Profil dauerhaft falsch, und
  falsche Einträge im Profil sind schwer wieder herauszubekommen
- **EPUB-Verarbeitung, Anki-Deckerzeugung, Satz der Druckausgabe** — für alle drei
  existieren ausgereifte Pakete
- **Phase 4 (Comics)** — Sprechblasenerkennung und OCR laufen faktisch ausschließlich
  über Python-Werkzeuge. Diese Entscheidung hält also auch die letzte Ausbaustufe offen

Zum Vergleich die verworfenen Alternativen:

| Sprache | Warum nicht |
|---|---|
| **C# / .NET (Avalonia)** | Auslieferung wäre am angenehmsten, aber für NLP gibt es im Wesentlichen nur *Catalyst* — spürbar schwächer bei Lemmatisierung und Eigennamen |
| **TypeScript (Tauri/Electron)** | Beste Oberflächen-Werkzeuge, aber die NLP-Bibliotheken sind deutlich schwächer als spaCy |
| **Rust (Tauri)** | Beste Auslieferung, praktisch keine brauchbare NLP-Landschaft |

### Warum kein Zwei-Sprachen-Aufbau

Ein Hybrid (Python-Kern + Weboberfläche) war ausdrücklich erlaubt, **sofern er die
Qualität klar verbessert.** Genau das tut er nicht: Die Lemmatisierung käme in beiden
Fällen aus spaCy. Der Hybrid kauft Gestaltungsfreiheit bei der Oberfläche, nicht
bessere Ergebnisse — und kostet dafür zwei Werkzeugketten, zwei Laufzeitumgebungen und
eine Prozessgrenze quer durch die Anwendung. Nach dem eigenen Kriterium also: nein.

Wichtig: Diese Entscheidung ist **umkehrbar**, siehe die Architekturregel weiter unten.

### Warum Qt Quick den Oberflächenanspruch erfüllt

Das ist normalerweise die Schwachstelle von Python — hier aber nicht. Qt Quick
beschreibt Oberflächen in **QML** und rendert sie über einen C++-Szenengraph direkt auf
der Grafikkarte.

- Ein am Zeiger klebendes Schiebemenü ist dort kein Kunststück, sondern der Normalfall:
  Die Position wird direkt an die Zeigerposition gebunden, es läuft keine vorgefertigte
  Animation ab
- Federbasierte Übergänge, flüssiges Scrollen über sehr lange Listen und
  Zustandsübergänge sind eingebaut — für die **Triage**, wo hunderte Wörter schnell
  durchgeklickt werden, ist das die richtige Grundlage
- Der Einstieg bleibt überschaubar: QML ist eine kleine deklarative Sprache, das
  Denkmodell ähnelt XAML aus der C#-Welt

Am Anfang genügt trotzdem eine schlichte Oberfläche. Qt Quick ist die Wahl, damit
„später modern und reaktiv" nicht bedeutet, alles noch einmal neu zu bauen.

### Bekannte Kosten dieser Entscheidung

| Punkt | Einschätzung |
|---|---|
| **QML lernen** | Ein bis zwei Wochenenden bis zur Brauchbarkeit. Vorkenntnisse in C#/Java helfen |
| **Auslieferung an Fremde** | Der wunde Punkt von Python. Für Eigennutzung irrelevant; später mit Nuitka oder PyInstaller lösbar, aber mühsam — insbesondere wegen der mitzuliefernden Sprachmodelle |
| **Nebenläufigkeit** | Verbindliche Regel: NLP-Läufe und LLM-Aufrufe laufen **nie** im Oberflächen-Thread, sonst ruckelt die Oberfläche. Das ist Baudisziplin, keine technische Hürde |
| **Lizenz** | PySide6 steht unter LGPL — für eine spätere quelloffene Veröffentlichung unproblematisch. Bei jeder weiteren Bibliothek ist die Lizenz **vor** der Aufnahme zu prüfen, da einige verbreitete Pakete unter starkem Copyleft stehen |

### Architekturregel — hält alle Türen offen

> Der **Kern** — EPUB-Einlesen, Wortschatzextraktion, Profil, Übersetzung, Export —
> wird als eigenständiges Python-Paket **ohne jeden Bezug zur Oberfläche** gebaut.
> Die Oberfläche ruft ihn nur auf.

Das hat drei Folgen:

1. Der Hybrid bleibt jederzeit nachrüstbar. Wird später eine Weboberfläche gewünscht,
   kommt ein dünner HTTP-Dienst vor denselben Kern — die eigentliche Arbeit ist dann
   schon erledigt. Heute wird also nur der *Aufwand* des Hybrids abgelehnt, nicht die
   *Möglichkeit*
2. Der Kern wird automatisiert testbar. Das hilft besonders bei den Abnahmekriterien 2
   und 6, die sich sonst nur mühsam von Hand prüfen lassen
3. Ein Kommandozeilenzugang ist praktisch geschenkt — nützlich zum Ausprobieren, lange
   bevor die Oberfläche steht

### Noch nicht entschieden

Innerhalb dieser Festlegung bleibt bewusst offen und wird später bestimmt:

- ~~**spaCy oder Stanza**, und in welcher Modellgröße~~ — **entschieden am 12.08.2026**,
  siehe Abschnitt 5
- ~~Bibliothek für EPUB~~ — **entschieden am 12.08.2026**, siehe Abschnitt 8: keine
- ~~Konkrete Bibliotheken für Anki-Export und Druckausgabe~~ — **entschieden am
  21.08.2026**, siehe Abschnitte 8b und 8c: `genanki` für Anki, für den Druck keine
- Aufteilung zwischen Qt Quick und klassischen Qt-Widgets, falls einzelne Ansichten
  damit schneller fertig werden

---

## 2. Wörterbuch- und Häufigkeitsdaten — entschieden

**WikDict (Sprachpaar `en-de`) als einzige Wörterbuchquelle für Phase 1.
Nicht mitgeliefert, sondern beim ersten Start heruntergeladen.**

- Bezugsquelle: `https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3`
- Format: SQLite, rund **20 MB** · Datenstand geprüft: Juni 2026
- Herkunft: Wiktionary, extrahiert über das **DBnary**-Projekt, aufbereitet von WikDict
- Lizenz: **Creative Commons BY-SA** (genaue Versionsnummer noch zu prüfen, siehe
  „Offene Punkte" unten) · Erzeugungs-Quellcode von WikDict: MIT

### Warum diese Quelle

Entscheidend war nicht die Größe, sondern die **Struktur**. Der Hybrid-Ansatz aus dem
Konzept verlangt, dass das Wörterbuch die *tatsächlich existierenden* Bedeutungen
liefert, damit das LLM nur noch **auswählt** statt zu **erfinden**. WikDict liefert
genau das: pro Bedeutung eine englische Kurzdefinition plus deutsche Entsprechung.

Am Konzeptbeispiel `bank` überprüft:

```
eng/bank__Noun__1   "institution"                       → Bank
eng/bank__Noun__1   "device used to store coins"        → Sparschwein
eng/bank__Noun__2   "edge of river or lake"             → Ufer
eng/bank__Noun__2   "an underwater area … a sandbank"   → Bank
```

Die englische Kurzdefinition ist die ideale Eingabe für den LLM-Schritt: Das Modell
bekommt den Belegsatz und eine überschaubare Auswahlliste und muss nur noch die
passende Zeile bestimmen. Damit ist die zentrale Risikostelle des Konzepts — erfundene
Übersetzungen, die der Nutzer nicht bemerken kann — konstruktiv entschärft.

Auch **Mehrwortausdrücke** sind enthalten, was für Redewendungen und Phrasal Verbs
entscheidend ist:

| Ausdruck | Treffer in der Datenbank |
|---|---|
| `beat around the bush` | um den heißen Brei herumreden |
| `give up` | aufgeben / kapitulieren / ergeben |
| `run into` | jemandem über den Weg laufen |

**Die Wortart steckt allein im `lexentry`** (`eng/bank__Noun__1`) — die Tabelle
`translation` führt dafür keine eigene Spalte. Wer nach Wortart filtern will, zerlegt also
den `lexentry`, und **29,7 % der Zeilen tragen gar keinen**: 46.933 von 157.801 haben
`lexentry = NULL` (nachgemessen am 19.08.2026 an `tools/en-de.sqlite3`). Was daraus folgt,
steht in Abschnitt 3, „Zweite Datenfalle: Zeilen ohne `lexentry`". Der Satz steht hier, weil
hier die Quelle beschrieben wird — er spart jedem Prüfer den ersten Fehlversuch.

### Abdeckung — empirisch geprüft

Geprüft am 11.08.2026 an zwei gemeinfreien Romanen (*The Picture of Dorian Gray*,
*The Adventures of Sherlock Holmes*), roh und ohne Lemmatisierung:

| | Dorian Gray | Sherlock Holmes |
|---|---|---|
| Wortformen im Buch | 7.042 | 8.362 |
| Stichworttreffer (types) | 87,8 % | 89,6 % |
| Textabdeckung (tokens) | 94,7 % | 94,7 % |
| **Restlücke nach Lemmatisierung + Eigennamenfilter** | **≈ 1,1 %** | **≈ 1,0 %** |

Die Messung ist reproduzierbar: [`tools/coverage_check.py`](tools/coverage_check.py)
rechnet sie gegen beliebige Textdateien und einen beliebigen Datenstand nach.

Die Restlücke ist noch zu hoch angesetzt — das Skript verwendet bewusst nur eine grobe
Suffix-Heuristik statt echter Lemmatisierung. Was übrig bleibt, verteilt sich auf:

- **nicht zurückgeführte Formen** (`cried`→cry, `heard`→hear, `paid`→pay,
  `carried`→carry, `shown`→show, `larger`→large) — verschwinden mit echter
  Lemmatisierung vollständig
- **Bindestrich-Komposita**, die größte verbleibende Gruppe (`sitting-room`,
  `frock-coat`, `dog-cart`, `half-past`, `good-night`) — durchsichtig zusammengesetzt
  und meist aus den Bestandteilen erschließbar
- **echte Wörterbuchlücken**, selten und randständig: `hansom`, `flowerlike`,
  `gipsies`, `mantelshelf`

> **Folgerung:** Die Datenquelle ist nicht der Engpass — die **Lemmatisierung** ist es.
> Das bestätigt Entscheidung 1 nachträglich: Die Qualität des Programms hängt an
> spaCy/Stanza, nicht am Wörterbuch.

### Verworfene Alternativen

| Quelle | Umfang | Lizenz | Warum nicht |
|---|---|---|---|
| **dict.cc** | sehr groß | proprietär | **Weitergabe der Daten untersagt.** Ausschlusskriterium, sobald das Programm veröffentlicht wird |
| **Ding / TU Chemnitz** über FreeDict | 460.315 Stichwörter | GPL | Deutlich größer, aber **ohne englische Bedeutungsangaben** — trägt den LLM-Auswahlschritt nicht. Zudem Lizenzkonflikt, siehe unten |
| **Rohe Wiktionary-Auszüge** (wiktextract/kaikki) | 1,78 Mio. Bedeutungen | CC BY-SA / GFDL | Mächtiger, aber ~3 GB und erheblicher Aufbereitungsaufwand. WikDict nimmt genau diese Arbeit bereits ab |

### Lizenzfalle: nicht verschmelzen

WikDict steht unter **CC BY-SA**, Ding unter **GPL**. Diese beiden Lizenzen sind für
ein **verschmolzenes** Werk nicht kompatibel. Sollte später eine zweite Quelle
hinzukommen, gilt daher:

> Zusätzliche Wörterbuchquellen werden **getrennt gehalten und nacheinander abgefragt**,
> niemals zu einer gemeinsamen Datenbank zusammengeführt.

Für Phase 1 stellt sich die Frage nicht: Es bleibt bei einer einzigen Quelle.

### Warum nicht mitgeliefert

Die Datenbank wird **beim ersten Start heruntergeladen**, nicht dem Programm beigelegt.
Gründe:

1. **Lizenzpflichten bleiben schlank.** Die Weitergabe CC-BY-SA-lizenzierter Daten
   zieht Namensnennungs- und Weitergabepflichten nach sich. Wer die Daten selbst
   bezieht, verschiebt diese Frage zum Anbieter. Der Programmcode ist davon ohnehin
   nicht betroffen — die Lizenz erfasst nur die Daten
2. **Aktualität.** WikDict wird fortlaufend neu erzeugt; ein mitgeliefertes Abbild
   veraltet
3. **Auslieferungsgröße.** 20 MB weniger im Installationspaket

**Bewusst in Kauf genommen:** Das Konzept verspricht vollständigen Offline-Betrieb.
Der Erstbezug der Datenbank ist eine **einmalige** Ausnahme davon. Damit das nicht zur
Sperre wird, ist vorzusehen:

- Anzeige beim ersten Start, welche Daten von wo bezogen werden — samt Lizenzhinweis
  und Namensnennung
- Möglichkeit, eine **von Hand hinterlegte** Datenbankdatei zu verwenden, damit der
  Betrieb auf Rechnern ohne Internetzugang möglich bleibt
- Vollständigkeitsprüfung des Downloads statt einer Prüfsumme — siehe Nachtrag
  18.08.2026

### Nachtrag 18.08.2026: keine Prüfsumme, weil WikDict keine veröffentlicht

Der Bauplan verlangt für T6 eine Prüfsumme gegen beschädigte Downloads — so auch die
ursprüngliche Fassung der Liste oben. Geprüft am 17.08.2026: WikDict veröffentlicht zur
Datei keine Prüfsumme, weder als `.sha256`- oder `.md5`-Datei neben ihr noch als Hash im
HTTP-Header — nginx liefert nur eine `ETag`, die sich als Zeitstempel und Dateigröße
entpuppt. Ohne veröffentlichten Referenzwert prüft eine selbst mitgeführte Konstante
nichts; sie behauptete nur Sicherheit, ohne ein unabhängiges Gegenüber zu haben. Ein
Aufrufparameter dafür hätte auch nie einen echten Aufrufer bekommen — ein Schalter ohne
zweiten Anwendungsfall (Regel 14).

Abgesichert wird der Bezug stattdessen über zwei Prüfungen in `dictionary.py`:

- **Content-Length beim Download.** `_download` bricht sichtbar ab, wenn der Server keine
  Content-Length nennt oder weniger Bytes ankommen, als er angekündigt hat
- **Zeilenzahl nach dem Bezug.** `_validate_schema` verlangt mindestens 100.000 Zeilen in
  `translation`, deutlich unter den 157.801 Zeilen der echten Datei (Abschnitt 3), aber
  hoch genug, dass eine leere oder grob unvollständige, aber schemarichtige Tabelle nicht
  als gültig durchgeht — `PRAGMA table_info` allein liest nur das Schema, keinen Inhalt

Was das leistet: einen abgebrochenen, gekürzten oder leeren Download erkennen, bevor er
als gültiges Wörterbuch liegen bleibt. Was es nicht leistet: Schutz gegen eine
vollständige, aber absichtlich manipulierte Datei — dafür fehlt weiterhin ein
unabhängiges Gegenüber.

### Häufigkeitsdaten — unkritisch

Der Kernablauf zählt Häufigkeiten **im Buch selbst**; externe Listen werden erst für
den Buch-Schwierigkeitscheck in Phase 2 gebraucht. Zwei Punkte dazu:

- WikDict liefert bereits `importance`-Werte pro Eintrag. Für die Sortierung in der
  Triage genügt das voraussichtlich schon
- Falls doch externe Daten nötig werden: **`wordfreq`** (Code Apache 2.0, Daten
  CC BY-SA 4.0). Einschränkung: Der Datenstand endet bei etwa 2021 und wird nicht
  fortgeschrieben — der Autor hat das Projekt eingestellt, weil KI-erzeugte Texte das
  Web als Quelle verdorben haben. Für Buchvokabular ist dieser Stand eher ein Vorteil

### Offene Punkte

- **Genaue Version der CC-BY-SA-Lizenz** von WikDict/DBnary prüfen (3.0 oder 4.0).
  Relevant nur, falls später doch eine zweite Quelle hinzukommt — auf die getrennte
  Ablage oben hat es keinen Einfluss
- Form der **Namensnennung** im Programm festlegen (Wiktionary, DBnary, WikDict)
- Umgang mit **historischen Schreibweisen** (`to-night`, `arm-chair`) — Normalisierung
  beim Einlesen oder bewusst ignorieren
- Ob die deutsche Gegenrichtung für Kartentyp DE→EN aus denselben Paaren umgekehrt wird
  oder die separate `de-en`-Datenbank nötig ist

---

## 3. Lokales Modell und Betriebsart — entschieden

**Gemma 4 E4B über Ollama, angesprochen über die OpenAI-kompatible Schnittstelle.
Denkschritt abgeschaltet, Temperatur auf 0. Antwortform per JSON-Schema erzwungen. Eine
Anfrage je Wort.**

Bis zum 26.08.2026 stand hier Granite 4.1 8B; der Wechsel samt der neuen
Temperaturfestlegung ist im Nachtrag vom 26.08.2026 begründet. Betriebsart und übrige
Einstellungen bleiben unverändert.

### Hardware

| | |
|---|---|
| Grafikkarte | AMD RX 5700, 8 GB (gfx1010, RDNA1) |
| Prozessor | AMD Ryzen 5 3600 |
| Arbeitsspeicher | 32 GB |

Die Karte ist der bestimmende Faktor. **ROCm unterstützt RDNA1 offiziell nicht** —
unterstützt sind erst gfx1030 (RDNA2) und neuer. Der Betrieb wurde deshalb am
11.08.2026 praktisch geprüft, statt aus Papierlage geschlossen: Qwen 3.5 9B läuft auf
dieser Karte ohne Probleme und zügig.

### Gemessene Ergebnisse

Geprüft mit [`tools/sense_check.py`](tools/sense_check.py) — der
Umsetzung von Abnahmekriterium 3 aus dem Konzept:

| | |
|---|---|
| **Trefferquote** | **11 von 11** bewertbaren Fällen richtig |
| Vergleichswert „immer die erste Bedeutung" | 2 von 6 |
| Antwortzeit je Wort | rund **1 Sekunde** |
| Token je Anfrage | rund 200 Eingabe, 7 Ausgabe |

Geprüft wurden bewusst schwierige Paare, jeweils in beiden Richtungen:
`bank` (Ufer/Bank), `lie` (liegen/lügen), `spring` (Frühling/Feder),
`light` (Licht/leicht), `watch` (Uhr), `draw` (zeichnen).

Bei rund einer Sekunde je Wort und höchstens 25 neuen Wörtern pro Kapitel liegt die
Übersetzungsdauer eines Kapitels im Bereich **einer halben Minute**. Geschwindigkeit ist
damit kein Kriterium mehr für die **Wahl des Modells** — wohl aber im Schritt davor, siehe
den Nachtrag unten.

### Nachtrag 17.08.2026: der Engpass ist das Nachschlagen, nicht das Modell

Gemessen an `tools/en-de.sqlite3` mit `dictionary.candidates()`:

| | |
|---|---|
| je Aufruf | **20 bis 28 ms**, je nach Zustand des Dateisystem-Zwischenspeichers |
| davon Verbindungsaufbau | 0,3 ms — vernachlässigbar |
| Abfrageplan | `SCAN translation` über 157.801 Zeilen, dazu `USE TEMP B-TREE FOR ORDER BY` |
| Indizes in der Datei | **keiner** — `sqlite_master` liefert keine einzige Zeile |
| ein Kapitel mit 1.592 Grundformen | **32 bis 44 Sekunden** reine Wörterbuchzeit |

Das Nachschlagen kostet damit mehr als sämtliche Modellaufrufe zusammen, obwohl es nur eine
Abfrage je Grundform ist. Die Abhilfe ist gemessen und schmal: Ein Index auf
`translation(written_rep)` macht aus dem `SCAN` ein `SEARCH … USING INDEX` und senkt den
Aufruf auf **0,71 ms**, das Kapitel auf **1,1 Sekunden**. Er entsteht in 0,1 s und
vergrößert die Datei von 20,9 auf 23,9 MB.

Angelegt wird er bei **T6** (Erstbezug), wo die Datei ohnehin einmalig angefasst wird —
nicht bei T5. Und **kein Zwischenspeicher**: Regel 14 verlangt für einen solchen einen
gemessenen Anlass, und die Messung zeigt auf den fehlenden Index, nicht auf einen zweiten
Datenbestand.

### Nachtrag 18.08.2026: zwei Drittel der Grundformen eines Kapitels sind mehrdeutig

Die erste der beiden Zahlen, die Entscheidung 10 offen hielt. Gemessen mit
[`tools/ambiguity_check.py`](tools/ambiguity_check.py) an beiden Romanen, jedes Kapitel
einzeln — 32 Kapitel, 32.409 Grundformen — über `extraction.extract_vocabulary` (T3) und
`dictionary.candidates` (T5), also nach den dort geltenden Regeln samt Regel 1:

| je Kapitel | Sherlock Holmes (12 Kapitel) | Dorian Gray (20 Kapitel) |
|---|---|---|
| Grundformen im Mittel | 1.368 | 800 |
| ohne Wörterbucheintrag | 7,2 % | 7,6 % |
| eindeutig — genau eine Bedeutung | 26,9 % | 26,4 % |
| **mehrdeutig — mehr als eine** | **65,8 %** | **66,0 %** |
| Median aller Grundformen mit Eintrag | 2 | 2 |
| Median unter den mehrdeutigen | 3 | 3 |

Beide Bücher ergeben dieselbe Verteilung, und die dicken Enden sind schmal:

| Bedeutungen | Sherlock Holmes | Dorian Gray |
|---|---|---|
| 2 | 21,6 % | 20,5 % |
| 3 bis 5 | 31,2 % | 31,6 % |
| 6 bis 10 | 10,8 % | 11,1 % |
| über 10 | 2,2 % | 2,7 % |

Die längsten Listen sind in beiden Texten dieselben Wörter: `break` 31, `run` 25,
`right` 23, `get` 20, `line` 19, `head` 17. Die 48 Bedeutungen von `run` aus dem offenen
Punkt unten sind die Zahl **ohne** Wortartfilter — mit ihm bleiben 25.

> **Antwort auf die Frage aus E10: eine Triage-Entscheidung je Wort genügt.**

Nicht, weil die Mehrdeutigkeit selten wäre — sie ist der Normalfall —, sondern weil der
Kernablauf je Kapitel und Grundform ohnehin nur **eine** Bedeutung erzeugt:
`extract_vocabulary` liefert ein einziges `Occurrence` je Grundform mit einer gewählten
Wortart und einem Belegsatz, und `translation` wählt daraus genau eine Bedeutung. Eine
Entscheidung je Bedeutung hieße, dem Nutzer alle Zeilen des Stichworts vorzulegen: **97.416
statt 32.409** Einträgen, Faktor **3,0** (Sherlock) beziehungsweise **3,1** (Dorian) — für
Sherlock rund 4.000 statt 1.370 Einträge je Kapitel. Abnahmekriterium 7 (Triage in unter
zehn Minuten) ist so nicht mehr erreichbar, und der Zugewinn wäre gering: Über eine
Bedeutung, die im Kapitel gar nicht vorkommt, kann der Nutzer nichts sagen.

Was die Zahl **doch** verlangt: Die Triage darf nicht bloß das Wort zeigen. Bei zwei
Dritteln der Einträge entscheidet der Nutzer sonst über ein Stichwort, dessen gemeinte
Bedeutung er nicht sieht. Die gewählte Bedeutung samt Belegsatz gehört also in die
Anzeige — das ist Darstellung, keine zweite Entscheidung.

Offen bleibt davon unberührt der Fall, dass dieselbe Grundform **innerhalb eines Kapitels**
in zwei Bedeutungen vorkommt (`bank` als Ufer und als Geldhaus). `extract_vocabulary` fasst
ihn bewusst zu einem Eintrag zusammen (`extraction.py`, Moduldocstring „Regeln"); wie oft
das eintritt, sagt diese Messung nicht — dafür müsste das Modell je Vorkommen laufen.
Dauerhaft verloren geht dabei nichts: Das Profil führt Kenntnis je Bedeutung (Abschnitt 4),
die zweite Bedeutung erscheint im nächsten Kapitel als „neue Bedeutung eines bekannten
Wortes" (Abnahmekriterium 6).

### Nachtrag 19.08.2026: Bündeln lohnt nicht — T11 fragt je Wort einzeln

Die zweite der beiden Zahlen, die Entscheidung 10 offen hielt, und damit die Sperre
auf T11. Gemessen mit [`tools/bundle_check.py`](tools/bundle_check.py) an
`tools/sherlock.txt`: 64 mehrdeutige Grundformen über `extraction.extract_vocabulary` und
`dictionary.candidates`, dieselbe Stichprobe für jedes Modell und jede Bündelgröße,
Bündelgröße 1 als Grundlinie.

| Sekunden je Wort | einzeln | Bündel 8 | Bündel 16 |
|---|---|---|---|
| `granite4.1:8b` | 1,63 | 1,40 | 1,75 |
| `gemma4:e4b` | 1,82 | **0,96** | **0,77** |
| `qwen3.5:9b` | 6,29 | 4,45 | 4,33 |
| **Übereinstimmung mit dem Einzellauf** | Grundlinie | 70 / 77 / 70 % | 63 / 72 / 63 % |

> **Antwort auf die zweite Frage aus E10: T11 fragt je Wort einzeln.**

Nicht, weil Bündeln langsamer wäre — für `gemma4:e4b` ist es bis zu 2,4-fach schneller,
für `qwen3.5:9b` 1,4-fach, für `granite4.1:8b` gar nicht. Sondern weil es **bei 23 bis
37 % der Wörter eine andere Bedeutung wählt**. Was die Messung dabei *nicht* sagt: ob die
abweichende Wahl schlechter ist. Sie ist nur anders — ein Goldstandard fehlt. Genau
deshalb fällt die Entscheidung auf die Bedingung, unter der die 11 von 11 oben zustande
kamen: eine Anfrage je Wort. Ein Bündelmechanismus entfällt damit ersatzlos (Regel 14).

#### Datenfalle: der Server kürzt zu lange Prompts still

Ollama fährt die Modelle mit `context_length` **4096**, obwohl alle drei 131k oder mehr
könnten. Überschreitet ein Prompt das Fenster, kürzt der Server ihn auf rund **2.050
Token — und meldet in `usage.prompt_tokens` den gekürzten Wert.**

| gesendet | gemeldete `prompt_tokens` |
|---|---|
| 1.000 / 2.000 / 3.000 Token | 1.015 / 2.015 / 3.015 — korrekt |
| 5.000 und 9.000 Token | **2.050** — gekürzt |

Eine Prüfung, die sich auf diese Zahl verlässt, kann die Kürzung deshalb **nie sehen**;
die Promptgröße ist **vor** dem Senden zu schätzen. Bündelgröße 32 und 64 (4.278 und
8.088 geschätzte Token) sind dadurch gar nicht messbar — ihre Zeilen sind `UNBRAUCHBAR`
und tragen zur Antwort oben nichts bei. **Das gilt auch im Betrieb**, weil T11 denselben
Endpunkt anspricht; bei Einzelanfragen (rund 550 Token) ist der Abstand groß.

#### Warum die Festlegung von Qwen 3.5 auf Granite 4.1 wechselt

In der gewählten Betriebsart liegen `granite4.1:8b` (1,63 s/Wort) und `gemma4:e4b` (1,82)
gleichauf, `qwen3.5:9b` (6,29) ist rund viermal langsamer — ohne dafür etwas zu leisten:
In `sense_check.py` erreichen alle drei 11 von 11, und in der Übereinstimmung liegt Qwen
nicht vorn. Gewählt ist `granite4.1:8b`: schnellste Antwort bei Einzelanfragen,
ausdrücklich auf strukturierte JSON-Ausgabe hin gebaut, kleinste Datei.
**`gemma4:e4b` ist der dokumentierte Zweitplatzierte** — gleichauf einzeln, deutlich
besser, sobald gebündelt würde. Der Wechsel ist billig: Der Modellname steht in
`config.toml` (Abschnitt 9), nicht im Code.

Zwei weitere Kandidaten sind ausgeschieden: `gemma4:e2b` erreicht in `sense_check.py` nur
9 von 11, und `ornith:9b` ist ein agentisches Coding-Modell auf Qwen-3.5-Unterbau — das
langsamste im Feld und in der Redewendungsprobe unbrauchbar, weil es den
Gutenberg-Lizenzkopf als Wendungen ausgibt.

> **`sense_check.py` trennt nicht mehr.** Vier von fünf geprüften Modellen erreichen dort
> 11/11 — der Test ist zum Rauchtest geworden. Eine Aussage über die Trefferqualität
> zwischen Granite und Gemma braucht eine größere Stichprobe, sinnvollerweise **nach T11
> und über dessen echten Prompt**, nicht über einen nachgebauten. **Erledigt am
> 26.08.2026** — siehe unten, „Nachtrag 26.08.2026: Trefferquote und Zeit bei fester
> Temperatur, 40 echte Einträge über `pipeline.run_chapter`".

### Nachtrag 26.08.2026: Trefferquote und Zeit bei fester Temperatur, 40 echte Einträge über `pipeline.run_chapter`

Gemessen am 26.08.2026 an `tools/dorian_gray.epub` Kapitel 10 über `pipeline.run_chapter`:
40 echte Einträge (26 Wörter, 14 Wendungen), das Urteil richtig / falsche Bedeutung /
übervorsichtig einmal von Hand gefällt und unverändert auf alle Einstellungen unten
angewandt. Vergleichswert „immer die erste Bedeutung": 27/40. Die Wiederholbarkeitszahlen,
die zur Temperaturfestlegung geführt haben, stehen unten unter „Zwingende Einstellung:
Temperatur auf 0"; hier folgen Trefferquote, Zeit und die Modellempfehlung, die auf
derselben Stichprobe beruhen.

Median warmer Aufrufe, Kaltstart getrennt ausgewiesen:

| Einstellung | Treffer | falsche Bedeutung | übervorsichtig | s/Wort | Kaltstart |
|---|---|---|---|---|---|
| `granite4.1:8b` Vorgabe | 33–34/40 | 5 | 1–2 | 0,21 | ~15 s |
| `granite4.1:8b` T = 0 | 36/40 | 3 | 1 | 0,24 | ~15 s |
| **`gemma4:e4b` T = 0** | **37/40** | **1** | 2 | 0,48 | 28 s |
| `gemma4:26b` T = 0 | 36/40 | 4 | 0 | 1,28 | **61 s** |
| `qwen3.5:9b` T = 0 | 34/40 | 6 | 0 | 3,01 | 25 s |

„falsche Bedeutung" heißt: eine unpassende Zeile wird gebucht — die teure Fehlerrichtung.
„übervorsichtig" heißt: das Modell antwortet „keine passt", obwohl eine Zeile gepasst
hätte — der Eintrag wird dadurch nur übersprungen, nicht falsch gefüllt (die billige
Fehlerrichtung, `pipeline._resolve_sense`).

#### Warum die Empfehlung von Granite 4.1 auf Gemma 4 E4B wechselt

Bei fester Temperatur erreicht `gemma4:e4b` 37 von 40 Einträgen gegenüber 36/40 bei
`granite4.1:8b` — knapp, aber die Fehlerart wiegt schwerer als die Zahl: Von Gemmas drei
Fehlern ist nur **einer** eine falsch gebuchte Bedeutung, die übrigen zwei sind
übervorsichtige Auslassungen; bei Granite sind es **drei** falsch gebuchte Bedeutungen
gegenüber nur einer Auslassung. Der Preis ist gering: 0,48 statt 0,24 Sekunden je Wort —
bei höchstens 25 neuen Wörtern pro Kapitel (konzept.md, Schritt 4) also rund 12 statt 6
Sekunden, weit unter jedem Zeitbudget. `gemma4:26b` scheidet trotz derselben Trefferquote
wie Granite (36/40) aus: 1,28 s/Wort, 61 s Kaltstart — siehe unten zu
`translation.DEFAULT_TIMEOUT` — und mit 4 falsch gebuchten Bedeutungen die schlechteste
Fehlerart im ganzen Feld. `qwen3.5:9b` scheidet mit der niedrigsten Trefferquote (34/40)
bei gleichzeitig höchster Zeit (3,01 s/Wort) aus.

> **Damit ist Entscheidung 3 überarbeitet: `gemma4:e4b` statt `granite4.1:8b`.** Die
> vorherige Fassung stand oben unter „Warum die Festlegung von Qwen 3.5 auf Granite 4.1
> wechselt" und beruhte auf `sense_check.py` (11/11, keine Trennung mehr möglich); diese
> Messung liefert die dort angemahnte größere Stichprobe über den echten T11-Prompt.

#### Zeit: Nachtrag zu „rund eine Sekunde je Wort"

Die Messung unter „Gemessene Ergebnisse" oben datiert vom 11.08.2026 und lief nur an
wenigen bewertbaren Einzelfällen, ohne Kaltstart und Modell getrennt auszuweisen. Die
Tabelle oben ersetzt das für die vier hier verglichenen Einstellungen: 0,24 s/Wort
(`granite4.1:8b` T=0), 0,48 s/Wort (`gemma4:e4b` T=0), 1,28 s/Wort (`gemma4:26b` T=0),
3,01 s/Wort (`qwen3.5:9b` T=0), Kaltstart 15 bis 61 Sekunden je nach Modell.
`translation.DEFAULT_TIMEOUT` steht auf 120 s; bei `gemma4:26b` verbraucht allein der
Kaltstart mit rund 61 s bereits die halbe Frist, bevor die erste Antwort überhaupt
ankommt — ein weiterer Grund neben der Trefferquote, dieses Modell nicht zu empfehlen.

**Die Zeit je Aufruf hängt davon ab, wie oft derselbe Systemprompt vorher lief.** Über die
Abnahmeläufe zu T17 gemessen: **1,65 s** je Wort im allerersten Lauf gegen **0,25 s** in den
folgenden — Faktor **6,6** bei unverändertem Modell, Prompt und Kapitel. Der Kaltstart oben
ist davon nur die erste Hälfte; auch danach wird es noch schneller, weil der Server den
gleichbleibenden Promptkopf wiederverwendet. Folge für jede weitere Messung: **„Sekunden je
Wort" misst immer auch die Reihenfolge der Läufe.** Vergleichbar sind Zahlen nur, wenn
dieselbe Einstellung nicht als erste gemessen wurde — oder wenn Kaltstart und erster Lauf
wie in der Tabelle oben getrennt ausgewiesen sind.

#### Die „keine passt"-Quote bei Wendungen misst die Kandidatenbildung, nicht das Modell

Die im Abnahmebericht zu T17 schwankende Überspringquote bei Wendungen (21 % bis 40 %) ist
damit erklärt: reines Temperaturrauschen. Bei `temperature: 0` liegt sie fest bei 43 %
(6 von 14 Wendungen) — und das ist fast richtig: 7 der 14 Wendungen im gemessenen Kapitel
haben tatsächlich keine passende Wörterbuchbedeutung. Die Quote misst also die
**Kandidatenbildung aus T4** (welche Wendungen überhaupt eine Auswahlliste bekommen),
nicht die Qualität des Modells.

**Bekannte Grenze aus der bestandenen Abnahme (26.08.2026):** Bei sehr allgemeinen Verben
antwortet das Modell auch dann „keine passt", wenn eine Zeile gepasst hätte — beobachtet an
`make` und `do` mit vorliegenden, passenden Kandidaten. Das ist die billige Fehlerrichtung
(der Eintrag wird übersprungen, nicht falsch gefüllt, `pipeline._resolve_sense`) — dieselbe,
die die Tabelle oben „übervorsichtig" nennt; festgehalten, weil es genau die Wörter trifft, bei
denen eine lange Auswahlliste auf viele blasse Bedeutungen führt — derselbe Verdacht, dem der
offene Punkt „Sehr lange Auswahllisten" unten nachgeht.

### Nachtrag 26.08.2026: was der Wortartfilter kürzt — und was er kostet

Der Messauftrag aus T18: Bis hierher stand über die Wortart als Vorfilter eine Vermutung
(„halbiert lange Listen"), gestützt auf zwei Einzelwerte. Gemessen wurde sie am
26.08.2026 am Stand `87b0bbf` über `tools/en-de.sqlite3`, `tools/dorian_gray.epub` (22
Kapitel) und `tools/sherlock.epub` (13 Kapitel mit Fließtext), gelesen über
`epub.read_structure`/`read_chapter` und ausgewertet über
`extraction.extract_vocabulary` (mit buchweitem Eigennamenanteil wie
`pipeline.run_chapter`) gegen `dictionary` — **32.549 Vorkommen** (16.122 Dorian Gray,
16.427 Sherlock Holmes) über 35 Kapitel. Kreuzprobe gegen die bereits hier stehenden
Zahlen: `run` (48 ohne, 25 mit Filter) und die Mehrdeutigkeitsquote (65,8/66,0 % mit
Filter gegen 75,3/76,9 % ohne) reproduzieren sich exakt. Gerechnet hat ein Wegwerfskript
nach demselben Verfahren wie `tools/ambiguity_check.py`, nur je Vorkommen statt je
Kapitel — aus `tools/` reproduzierbar ist diese Messung damit **nicht**, dieselbe Lücke,
die Abschnitt 8c für die Druckkapazität festhält.

**Länge der Auswahlliste je Vorkommen** (Mittel / Median):

| | mit Filter | ohne Filter |
|---|---|---|
| Dorian Gray (16.122 Vorkommen) | 3,31 / 2 | 4,64 / 3 |
| Sherlock Holmes (16.427 Vorkommen) | 3,19 / 2 | 4,41 / 3 |
| **beide (32.549 Vorkommen)** | **3,25 / 2** | **4,53 / 3** |

| Verteilung, beide Bücher | kein Eintrag | eindeutig | 2 | 3–5 | 6–10 | über 10 |
|---|---|---|---|---|---|---|
| mit Filter | 7,4 % | 26,7 % | 21,1 % | 31,4 % | 11,0 % | 2,5 % |
| ohne Filter | 4,1 % | 19,8 % | 16,4 % | 32,5 % | 19,4 % | 7,8 % |

**Die Kürzung reicht von 0 % bis 48 %, nicht „halbiert".** Die sechs längsten Listen aus
dem Nachtrag 18.08.2026 oben, wörterbuchseitig und damit buchunabhängig:

| Wort | mit Filter | ohne Filter | WikDict nach Wortart |
|---|---|---|---|
| `break` (VERB) | 31 | 43 | Verb 31, Noun 12 |
| `run` (VERB) | 25 | 48 | Verb 25, Noun 23 |
| `right` (ADJ) | 23 | 24 | Adjective 23, Verb 1 |
| `get` (VERB) | 20 | 20 | Verb 20, keine andere Wortart |
| `line` (NOUN) | 19 | 21 | Noun 19, Verb 2 |
| `head` (NOUN) | 17 | 30 | Noun 17, Verb 11, Adjective 2 |

`get` kürzt um nichts, weil WikDict es nur als Verb führt; `run` um 48 %. Wo der Filter
greift, greift er auf den langen Listen am stärksten: Bei 2–5 Bedeutungen ohne Filter
(15.922 Vorkommen) bleibt der Median unverändert bei 3, bei über 10 Bedeutungen (2.525
Vorkommen) sinkt er von 13 auf 8 — auf 61 %.

**Der Modellaufruf entfällt dabei selten.** Von den 24.759 Vorkommen, die ohne Filter
mehrdeutig wären, werden durch ihn **2.618 (10,6 %)** eindeutig; die übrigen 21.460
bleiben mehrdeutig und brauchen die Auswahl durch das Modell weiterhin.

**Und der Filter kostet etwas: 1.076 von 32.549 Vorkommen (3,3 %)** bekommen eine
**leere** Auswahlliste, obwohl ihr Stichwort im Wörterbuch steht — nur unter einer
anderen Wortart als der von spaCy gewählten (`right` als NOUN oder ADV: 0 statt 24
Treffer, weil WikDict `right` als Adjective und Verb führt). Das deckt sich mit der
Differenz „kein Eintrag" 7,4 % gegen 4,1 % oben und bestätigt die Messung vom 17.08.2026
(3,3 % über ganz `tools/sherlock.txt`, siehe „Offene Punkte" unten) an einer anderen
Stichprobe.

> **Diese 3,3 % sind eine Untergrenze, kein Gesamtpreis.** Gezählt sind nur die *leeren*
> Listen. Der teurere Fall — eine nicht-leere, aber falsch-wortartige Liste, aus der das
> Modell dann eine falsche Bedeutung wählt, ohne dass eine Wörterbuchlücke sichtbar wird
> — lässt sich ohne Goldstandard je Beleg nicht seriös beziffern und **bleibt
> ausdrücklich offen**. Wer die Zahl zitiert, zitiert die billige Hälfte.

**Warum die Kapitelzahlen von der Messung vom 18.08.2026 abweichen** (22/13 statt 20/12,
32.549 statt 32.409 Vorkommen): Diese Messung liest die EPUBs über
`epub.read_structure`/`read_chapter` wie `pipeline.run_chapter`, die frühere über die
`.txt`-Fassungen mit einer Kapitelgrenze per regulärem Ausdruck. Dieselbe Größenordnung,
alle Kreuzproben stimmen — die Zahlen der beiden Messungen sind vergleichbar, aber nicht
deckungsgleich, und das liegt an der Kapitelaufteilung, nicht am Gemessenen.

### Zwingende Einstellung: Denkschritt abschalten

Qwen 3.5 denkt in Ollama standardmäßig mit. Ohne Gegenmaßnahme verbraucht das Modell
sein gesamtes Token-Budget mit Nachdenken und liefert **überhaupt keine Antwort**
(`finish_reason: length`). Gemessene Abhilfen:

| Verfahren | Dauer | Ausgabe-Token | Ergebnis |
|---|---|---|---|
| **`reasoning_effort: "none"`** | **1,0 s** | **7** | funktioniert |
| `/no_think` im Prompt | 11,7 s | 142 | funktioniert, aber langsam |
| `think: false` / `enable_thinking` | 28,3 s | 512 | **wirkungslos** |

Zu verwenden ist `reasoning_effort: "none"`. Die Aufgabe ist eine Auswahl aus einer
vorgegebenen Liste — Nachdenken bringt hier nichts und kostet das Achtundzwanzigfache.

> **Merksatz:** Bei jedem Modellwechsel ist zuerst zu prüfen, ob es einen Denkschritt
> mitbringt und wie er sich abschalten lässt. Das ist die erste Fehlerquelle, nicht die
> letzte.

Am 18.08.2026 an fünf Modellen nachgeprüft: `granite4.1:8b`, `gemma4:e2b`, `gemma4:e4b`,
`ornith:9b` und `qwen3.5:9b` denken alle standardmäßig mit (6 bis 42 s je Antwort) und
gehorchen alle `reasoning_effort: "none"` (0,2 bis 1,2 s). Die Einstellung überlebt einen
Modellwechsel also — nachzuprüfen ist sie trotzdem.

### Zwingende Einstellung: Temperatur auf 0

`translation._request_body` setzte bis zum 26.08.2026 keine Temperatur. Serverseitig
bringt `granite4.1:8b` dafür gar keine Modelfile-Parameter mit — Ollamas Vorgabe 0,8
greift bei diesem Modell unverändert; `gemma4:e4b`, `gemma4:26b` und `qwen3.5:9b` bringen
dagegen `temperature 1` mit. Dieselbe Auswahl aus derselben nummerierten Liste lief also
je nach Modell zwischen 0,8 und 1,0 — und die Abnahme zu T17 ist zweimal genau daran
gescheitert (oben, „Nachtrag 26.08.2026", „Die «keine passt»-Quote…").

Wiederholbarkeit gemessen am 26.08.2026 an `dorian_gray.epub` Kapitel 10
(`granite4.1:8b`, 8 Einträge × 10 Wiederholungen): Bei Ollamas Vorgabe blieben 4 von 8
Einträgen über alle zehn Wiederholungen stabil, bei `temperature: 0` **8 von 8**. Über die
volle Stichprobe von 40 Einträgen, drei Läufe: Vorgabe 31/40 stabil, `temperature: 0`
**40/40** — auch über einen Modellneuladevorgang hinweg.

> **Regel:** Jeder Modellaufruf setzt `temperature: 0`, neben `reasoning_effort: "none"`
> (Regel 7). Ohne diese Festlegung liefert dieselbe Eingabe verschiedene Antworten, und
> jede Messung an diesem Prompt — Trefferquote, Bündelvergleich, Reihenfolge — wird
> unbrauchbar, weil sich Modellwechsel und Zufallsstreuung nicht mehr auseinanderhalten
> lassen.

`temperature` ist dabei ein **Standardparameter der OpenAI-Schnittstelle**, keine
Ollama-Erweiterung — jeder OpenAI-kompatible Server nimmt ihn entgegen. Eine Ausnahme ist
absehbar: Reasoning-Modelle der o-Reihe und GPT-5 lehnen den Parameter teils ab oder
erlauben nur ihren Vorgabewert. Da `config.toml` jede Adresse zulässt (Abschnitt 9), wäre
das dort ein HTTP 400 — ein lauter Fehlschlag, kein stiller, und deshalb heute kein Grund
für eine Ausweichlösung (Regel 14).

### Datenfalle: Einträge ohne Bedeutungstext

Beim Bau des Prüfwerkzeugs ist ein Fehler aufgetreten, der sich in der eigentlichen
Umsetzung genauso wiederholen würde:

**36 % aller Zeilen in WikDict haben keinen `sense`-Text** — und es sind systematisch
die **Hauptbedeutungen** mit der höchsten Bewertung.

| Wort | Zeile ohne `sense` | Bewertung |
|---|---|---|
| `watch` | Uhr, Armbanduhr | 136,7 — höchste des Stichworts |
| `draw` | zeichnen, malen, skizzieren | 172,9 — höchste des Stichworts |

Wer diese Zeilen wegfiltert, verliert ausgerechnet die gebräuchlichste Bedeutung und
erzeugt so scheinbare Wörterbuchlücken. Im Prüfwerkzeug führte das zu zwei falschen
Ergebnissen, die fälschlich dem Modell angelastet wurden.

> **Regel:** Zeilen ohne `sense`-Text gehören **immer** in die Auswahlliste, mit einer
> Beschriftung wie „Hauptbedeutung, ohne nähere Angabe". Nach `score` absteigend
> sortieren, damit das Gebräuchliche oben steht.

### Zweite Datenfalle: Zeilen ohne `lexentry`

Die erste Datenfalle betrifft den fehlenden Bedeutungstext, diese die fehlende **Wortart**.
Nachgemessen am 19.08.2026 an `tools/en-de.sqlite3`: **46.933 von 157.801 Zeilen (29,7 %)**
haben `lexentry = NULL` und tragen damit keine Wortart (Abschnitt 2, „Warum diese Quelle").
Eine Zuordnung nach Wortart können sie nicht passieren — über alle betroffenen Zeilen
geprüft: **keine einzige** hätte es getan.

Anders als bei der ersten Datenfalle ist der Wegfall hier vertretbar: Der höchste `score`
unter diesen Zeilen ist **48**. Sie fallen also ohnehin sämtlich an der Schwelle
`score ≥ 50`, mit der T7 die Wendungen filtert. Seit T5 steht der Ausschluss ausdrücklich in
der Abfrage statt als Nebenwirkung eines Filters — wer ihn dort liest, sieht sofort, dass er
gewollt ist.

Zum Umfang, nicht als Fehler: **45.260 von 124.751 Stichwörtern (36,3 %)** haben überhaupt
keine Zeile mit `lexentry` und liefern damit eine leere Auswahlliste. Das ist ein anderer
Fall als der Wortartunterschied unter „Offene Punkte" (3,3 %): Hier fehlt die Wortart in der
Quelle, dort weicht sie von spaCys Bestimmung ab. Ob eine leere Auswahlliste `uncertain`
werden muss, entscheidet **T11**.

### Empirischer Beleg für die Lemmatisierungspflicht

Ein Testfall ist bewusst als Falle gebaut und zeigt das erwartete Verhalten:

```
Satz:      "He saw her standing at the window."
Ergebnis:  saw → (Noun) tool → Säge
```

`saw` ist hier die Vergangenheitsform von *see*. Das Wörterbuch kennt `saw` aber nur
als *Säge*, *sägen* und *Sprichwort* — die richtige Antwort **stand nicht zur Auswahl**.
Das Modell hat daraufhin die plausibelste falsche gewählt, ohne jedes Anzeichen von
Unsicherheit.

Das ist genau der stille Fehlschlag, den das Konzept fürchtet, und er lässt sich nicht
durch ein besseres Modell beheben — nur durch **Lemmatisierung vor dem Nachschlagen**.
Siehe Abschnitt „Warum die Reihenfolge zwingend ist".

### Offene Punkte

- **`candidates()` vergleicht Groß- und Kleinschreibung binär — ob das bleiben soll, ist
  nicht entschieden.** Gemessen beim Review zu T7 an `tools/en-de.sqlite3`: `'polish'`
  findet 6 Zeilen, case-insensitiv 8; `'german'` 3 gegen 12. **11,3 % der 84.167
  einwortigen Zeilen mit `lexentry` sind großgeschrieben** (`German`, `Polish`, `China`,
  …), und T3 schreibt jede Grundform klein (`token.lemma_.lower()`) — für `candidates`
  sind diese Zeilen damit unerreichbar. Anders als bei den Wendungen, wo `COLLATE NOCASE`
  entschieden ist (`dictionary._lookup_matches`, Befund 2 Review T7), trägt der Unterschied
  hier Bedeutung: `Polish` (die Nationalität, score 202,5) und `polish` (polieren, 135,0)
  sind **verschiedene Einträge**, nicht dieselbe Zeile in zwei Schreibungen. Wer stumpf
  case-insensitiv nachschlägt, mischt sie; wer es lässt, verliert die großgeschriebenen
  ganz. Zu entscheiden beim Einfalten
- **Ausweichantwort „keine passt"** in die Auswahlliste aufnehmen. Der `saw`-Fall zeigt,
  dass das Modell sonst kein Mittel hat, einen Fehler der Vorstufe zu melden. Mit dieser
  Möglichkeit wird aus einem stillen Fehler ein markierter Eintrag — das Konzept sieht
  Markierung bei Unsicherheit ohnehin vor
- **Sehr lange Auswahllisten**: `run` hat 48 Bedeutungen, `draw` 16, `light` 14. Ob das
  die Trefferquote drückt, ist noch nicht gemessen — das braucht den Modellserver und einen
  Goldstandard je Beleg. Die **Verkürzung** durch den Wortartfilter ist dagegen seit dem
  Nachtrag 26.08.2026 oben gemessen und keine Vermutung mehr: Sie reicht von 0 % (`get`) bis
  48 % (`run`), wirkt auf den langen Listen am stärksten (Median über 10 Bedeutungen: 13 auf
  8) und macht nur **10,6 %** der ohne Filter mehrdeutigen Vorkommen eindeutig. Der
  Modellaufruf entfällt also selten
- **Was der Wortartfilter jenseits der 3,3 % kostet, ist nicht beziffert.** Die 3,3 % leere
  Auswahllisten aus dem Nachtrag 26.08.2026 oben sind eine Untergrenze; der Fall einer
  nicht-leeren, aber falsch-wortartigen Liste — das Modell wählt daraus eine falsche
  Bedeutung, ohne dass eine Wörterbuchlücke sichtbar wird — ist darin **nicht** enthalten
  und ohne Goldstandard je Beleg nicht seriös zu messen. Der Punkt bleibt offen; erledigt ist
  er erst, wenn diese zweite Hälfte eine Zahl hat
- **Die Wortart als Filter schließt mehr aus als gedacht.** Gemessen am 17.08.2026 über
  ganz `tools/sherlock.txt` (5.544 Grundformen): **181 (3,3 %)** bekommen eine leere
  Auswahlliste, obwohl ihr Stichwort im Wörterbuch steht — gegenüber 480 Grundformen, die
  dort tatsächlich fehlen. Zwei Ursachen mit gleicher Wirkung: **24** sind echte
  Taxonomieunterschiede (WikDict führt `such`, `few`, `many`, `least` als `Determiner`,
  `ago` als `Postposition`, `thousand` als `Numeral`), **157** sind Wörter, die WikDict nur
  unter einer anderen der fünf abgebildeten Wortarten führt (`lead`, `spring`, `brim` haben
  dort keine Verbzeile) oder die spaCy anders bestimmt hat als das Wörterbuch (`summon`,
  `clothe` als `NOUN`). Der Nutzer sieht in allen Fällen „kein Wörterbucheintrag" bei einem
  Wort, das drinsteht, und T11 markiert es `uncertain` — **eine Modellunsicherheit verdeckt
  dann einen Zuordnungsfehler**. T11 hat den zweiten Versuch ohne Wortartfilter bewusst
  **nicht** gebaut (`translation.choose_sense`, Regel 14: kein Mechanismus ohne gemessenen
  Anlass). Der Anlass liegt seit dem Nachtrag 26.08.2026 oben vor — **1.076 Vorkommen** über
  35 Kapitel, an einer zweiten Stichprobe wieder 3,3 % —, die Entscheidung darüber steht aus
- **Redewendungserkennung** über Textfenster ist noch nicht geprüft. Der bisherige Test
  betrifft nur die Bedeutungsauswahl bei Einzelwörtern
- Ob **Ollama** dauerhaft die richtige Wahl ist oder `llama-server` mit Vulkan direkt.
  Ollama läuft nachweislich; ein Wechsel wäre nur nötig, wenn GBNF-Grammatiken feiner
  gesteuert werden sollen als per JSON-Schema

---

## 4. Ablage des Profils — entschieden

**SQLite in einer eigenen Datei, getrennt vom Wörterbuch. Kenntnis wird als
Ereignisfolge geführt, nicht als überschreibbarer Zustand.**

### Warum SQLite

Keine ernsthafte Alternative für diesen Zweck: eine Datei, kein laufender Dienst,
Transaktionssicherheit, in Python ohne Zusatzpaket verfügbar. Sichern heißt Datei
kopieren. Für Textdateien (JSON, CSV) spricht die Lesbarkeit, dagegen fehlende
Transaktionen und schlechtes Verhalten bei zehntausenden Einträgen — das Profil soll
über Jahre wachsen.

### Getrennte Datei — nicht mit dem Wörterbuch mischen

> Das Profil liegt in **`profil.sqlite3`**, das Wörterbuch in **`en-de.sqlite3`**.
> Niemals in derselben Datei.

Begründung: Das Wörterbuch wird heruntergeladen, ersetzt und aktualisiert. Das Profil
ist laut Konzept „der eigentliche langfristige Wert des Programms". Was ersetzt wird
und was jahrelang wachsen soll, gehört nicht in dieselbe Datei — sonst löscht ein
Wörterbuch-Update im schlimmsten Fall die Lernhistorie.

Aus demselben Grund gilt:

> **Keine Fremdschlüssel ins Wörterbuch.** WikDicts `lexentry` und `sense`-Texte werden
> als **Momentaufnahme** mitgespeichert, nie als Schlüssel verwendet.

Sonst zerbricht das Profil, sobald WikDict eine Bedeutungsformulierung ändert — und
das tut es, weil es aus Wiktionary erzeugt wird.

### Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort

Das Konzept verlangt zweierlei, das sich zu widersprechen scheint: bekannte Wörter „auf
Ebene der Grundform", aber `bank` als Geldinstitut und als Flussufer als **zwei**
Einträge, wobei der zweite als *„neue Bedeutung eines bekannten Wortes"* erscheint.

Auflösung: Die **Bedeutung** ist die Einheit, auf die sich Kenntnis bezieht. Die
Grundform ist nur die Klammer darum. „Kenne ich das Wort?" ist dann eine abgeleitete
Frage — nämlich ob mindestens eine seiner Bedeutungen bekannt ist.

Der Test zu Entscheidung 3 hat gezeigt, warum das nicht theoretisch ist: `watch` hat
sieben Bedeutungen, von denen *Uhr* und *Wache* nichts miteinander zu tun haben.

#### Wie sich das mit „eine Triage-Entscheidung je Wort genügt" verträgt

Beide Sätze stehen seit dem 18.08.2026 nebeneinander — „eine Triage-Entscheidung je Wort
genügt" (Abschnitt 3, „Nachtrag 18.08.2026") und „Kenntnis pro Bedeutung" hier —, ohne dass
gesagt war, wie sie zusammengehen. Sie waren die Bruchstelle, an der der schwere Befund vom
25.08.2026 lag; **aufgelöst ist sie seit dem Umbau vom selben Tag:**

> Die gemeinte Bedeutung wird **vor** der Triage aufgelöst, und die Entscheidung des Nutzers
> bucht auf **sie**. Der Nutzer entscheidet einmal je Wort, das Profil vermerkt eine
> Bedeutung.

Damit ist auch festgelegt, **wann** der Modellaufruf erfolgt — bis dahin stand das nur im
Moduldocstring: `pipeline.resolve_triage_entries` löst die Einträge auf, die die Triage
zeigen wird, ruft dafür `translation.choose_sense` (Abschnitt 7, der einzige Ort mit
Modellzugriff) und ist bewusst **nicht** Teil von `run_chapter`, damit ein Aufrufer, der nur
Auswahllisten braucht, ohne Modellserver auskommt. Zuvor buchte die Triage auf
`candidates[0]` — die erste Zeile der Auswahlliste, also die mit dem höchsten `score` und
nicht die im Kontext gemeinte. Wer die Triage anfasst, entscheidet das nicht neu.

### Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand

Nicht „Wort X hat Status *bekannt*", sondern „am 11.08.2026 wurde Wort X aus Grund Y
als *bekannt* eingestuft". Der aktuelle Stand ergibt sich aus dem jeweils letzten
Ereignis.

Das ist kein Selbstzweck, sondern die einzige Bauform, die **alle vier** einschlägigen
Konzeptforderungen ohne späteren Umbau erfüllt:

| Forderung aus dem Konzept | wird dadurch erfüllt |
|---|---|
| „mit Herkunft der Information und Zeitpunkt" | steht ohnehin in jedem Ereignis |
| Spätere Quellen (Anki-Import, Niveau, adaptiver Test) „ohne Umbau" aufnehmen | neue Herkunftsart, kein Schemawechsel |
| Phase 3: Anki-Rückkanal schiebt Wörter zurück auf *unbekannt* | ein weiteres Ereignis, die Vorgeschichte bleibt erhalten |
| „Das Profil lernt in **beide** Richtungen" | Richtungswechsel sind nachvollziehbar statt überschrieben |

Mit überschreibbaren Zeilen ginge bei jedem Rückkanal-Ereignis die Information
verloren, dass der Nutzer das Wort einmal als bekannt gemeldet hat — und genau diese
Vorgeschichte braucht Phase 3, um zu unterscheiden zwischen „nie gekonnt" und „wieder
vergessen".

### Tabellen im Überblick

```
book ──< chapter ──< occurrence >── lemma ──< sense
                          │                     │
                     (Belegsatz,           (Momentaufnahme aus
                      Häufigkeit)           dem Wörterbuch)
                                                │
                         event ─────────────────┤   Verlauf: kennt / lernt /
                                                │   zurückgestellt / vergessen
                                                │   + Herkunft + Zeitpunkt
                         card ──────────────────┘   Anki-Kennung für den Rückkanal
```

| Tabelle | Zweck |
|---|---|
| `lemma` | Grundform + Wortart. Die Klammer, nicht die Kenntniseinheit |
| `sense` | Eine Bedeutung eines Lemmas. Trägt die Wörterbuch-Momentaufnahme |
| `event` | Der Verlauf. Art, Herkunft, Zeitpunkt, Bezug auf Buch/Kapitel |
| `occurrence` | Belegsatz und Häufigkeit je Kapitel — dasselbe Wort hat in Kapitel 2 einen anderen Belegsatz als in Kapitel 9 |
| `book`, `chapter` | Was bereits verarbeitet wurde |
| `card` | Exportierte Anki-Karten samt deren Kennung |

Die Namen sind englisch, die Prosa bleibt deutsch — Zuordnung und Begründung in
[dokumentation.md](dokumentation.md), Abschnitt 1.

#### Die Spalten, wie sie seit T8 stehen

Festgehalten am 26.08.2026 nach der Abnahme; verbindlich ist `libreverbum/profile.py`,
`_SCHEMA`, nicht diese Tabelle. Jede Tabelle trägt zusätzlich `id INTEGER PRIMARY KEY`.
Die dritte Spalte nennt, **was eine Zeile identifiziert** — dort stecken die
Entwurfsentscheidungen, nicht in den Datentypen (alle Spalten `TEXT` oder `INTEGER`, alle
`NOT NULL` außer den drei `wikdict_`-Feldern).

| Tabelle | weitere Spalten | eine Zeile ist eindeutig über |
|---|---|---|
| `book` | `title`, `author` | `UNIQUE (title, author)` — ein Buch ist Titel und Autor, keine Datei und keine ISBN |
| `chapter` | `book_id`, `number`, `title` | `UNIQUE (book_id, number)` — die Nummer im Buch, nicht der Titel: „Chapter One" gibt es in jedem zweiten Buch |
| `lemma` | `text`, `pos` | `UNIQUE (text, pos)` — dieselbe Schreibung unter zwei Wortarten sind **zwei** Zeilen (der `saw`-Fall, „Warum die Reihenfolge zwingend ist") |
| `sense` | `lemma_id`, `wikdict_lexentry`, `wikdict_sense`, `wikdict_trans_list` | `UNIQUE INDEX sense_identity` über `lemma_id` und alle drei `wikdict_`-Felder, jedes durch `ifnull(…, '')` — ein gewöhnliches `UNIQUE` griffe nicht, weil SQLite jedes `NULL` von jedem anderen unterscheidet und `wikdict_sense` bei 36 % der Zeilen fehlt (Regel 1) |
| `occurrence` | `book_id`, `chapter_number`, `lemma_id`, `word_form`, `example_sentence`, `frequency`, `proper_noun_frequency` | `UNIQUE (book_id, chapter_number, lemma_id)` — je Kapitel **eine** Zeile je Grundform, mit eigenem Belegsatz |
| `event` | `sense_id`, `knowledge_state`, `origin`, `timestamp`, `book_id`, `chapter_number` | **keine** UNIQUE-Bedingung, und das ist die Entscheidung: Zeilen werden angehängt, nie geändert („Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand" unten) |
| `card` | `sense_id`, `occurrence_id`, `card_direction`, `guid` | `UNIQUE (guid)` — die Anki-Kennung, an der der Rückkanal aus Phase 3 hängt („Jetzt billig, später teuer" unten) |

- **Die `wikdict_`-Momentaufnahme steht ausschließlich in `sense`**, in genau diesen drei
  Spalten, und ist reiner Zeileninhalt zum Zeitpunkt der Abfrage — kein `rowid`, kein
  anderer Verweis in `en-de.sqlite3` (Regel 4, „Getrennte Datei" unten)
- **Eine eigene Korrektur der Übersetzung hat das Schema nicht.** `entities.Sense.translation`
  ist ein Ergebnisfeld des Durchlaufs und wird nicht geschrieben; die Karte trägt die
  Übersetzung, das Profil die Kenntnis
- Alle Fremdschlüssel zeigen innerhalb der Profildatei. `occurrence` und `event` verweisen
  zusätzlich als Paar auf `chapter(book_id, number)`; `open_profile` schaltet
  `PRAGMA foreign_keys = ON`
- `PRAGMA user_version` steht auf `profile.SCHEMA_VERSION`, heute **1**. `open_profile`
  prüft beim Öffnen zusätzlich, dass genau diese sieben Tabellen vorhanden sind —
  `user_version = 0` ist bei SQLite auch der Wert jeder fremden Datei
  („Schemaversion von Anfang an" unten)

> **Achtung, zwei Dinge namens `sense`:** Die eigene Tabelle ist die **Bedeutung als
> Gegenstand** — mit Verlauf, eigener Korrektur und Kartenbezug. WikDicts `sense` ist
> dagegen nur der **englische Kurztext**. Er wird als `wikdict_sense` mitgeführt. Das
> Präfix `wikdict_` markiert alle Momentaufnahmen aus der Fremdquelle und hält damit die
> Regel „keine Fremdschlüssel ins Wörterbuch" beim Abfragen sichtbar.

> **Eine `sense`-Zeile ohne `wikdict_`-Felder bedeutet *kein Wörterbucheintrag*, nicht
> *noch nicht nachgeschlagen*.** Das ist die einzige erlaubte Lesart — und sie muss
> ausgesprochen werden, weil beide Fälle sonst ununterscheidbar wären: Ein Platzhalter
> „wird später nachgeschlagen" trüge dieselben leeren Felder wie eine Wendung ohne
> Wörterbucheintrag nach Regel 10 und bekäme dieselbe Kennung. Wo eine Bedeutung noch
> fehlt, entsteht deshalb **keine** Zeile (Befund aus Review T10).

Der aktuelle Kenntnisstand ist eine **Sicht** auf die Ereignistabelle (jeweils
jüngstes Ereignis je Bedeutung), keine eigene Tabelle. Bei der zu erwartenden Größe —
Zehntausende Ereignisse — ist das für SQLite unproblematisch. Eine
materialisierte Zwischentabelle wäre verfrühte Optimierung.

**Eigennamen und Mehrwortausdrücke bekommen keine eigene Tabelle.** Ein Eigenname ist
dieselbe Klammer `lemma` mit `pos` gleich `PROPN`, ein Mehrwortausdruck dieselbe Klammer
mit Leerzeichen im Text (`give up`) — beides ohne eigene Kennzeichnung. Ob ein Vorkommen
als Eigenname zählt, entscheidet nicht `lemma`, sondern `occurrence` (Abschnitt 5, „Neuer
Befund: der Eigennamenfilter muss pro Vorkommen greifen").

### Jetzt billig, später teuer: die Anki-Kennung

> Beim Export jeder Karte wird deren **Anki-GUID** in `card` mitgespeichert.

Das kostet heute eine Spalte. Ohne sie lässt sich der Anki-Rückkanal aus Phase 3
später nicht anschließen, ohne alle bereits exportierten Decks neu zu erzeugen — was
beim Nutzer den Lernfortschritt in Anki zurücksetzen würde. Ein Fall, in dem eine
Fünf-Minuten-Entscheidung jetzt einen unreparierbaren Zustand später verhindert.

Woraus die Kennung gebildet wird, steht in Abschnitt 8b, „Befund: die vorgegebene GUID
bindet den Feldinhalt" — die Vorgabe der Bibliothek erfüllt Regel 6 nur dem Anschein nach.

### Sichern und Ausleiten

Zwei getrennte Dinge:

- **Sichern** = Datei kopieren. Zusätzlich ein Menüpunkt, der eine konsistente Kopie
  zieht, damit nicht mitten in einem Schreibvorgang kopiert wird
- **Ausleiten** = Export nach JSON. Das Konzept verlangt Exportierbarkeit; SQLite
  allein erfüllt das nur formal, weil die Datei ohne passendes Werkzeug undurchsichtig
  ist. Eine lesbare Textausgabe stellt sicher, dass die Daten den Nutzer überdauern,
  auch wenn das Programm es nicht tut

### Schemaversion von Anfang an

SQLites `PRAGMA user_version` wird ab der ersten Fassung gesetzt und bei jeder
Änderung erhöht. Ohne Versionsnummer ist eine spätere Migration Ratearbeit — und
Migrationen wird es geben, weil Phase 2 und 3 neue Felder brauchen.

### Offene Punkte

- ~~Genaue Spalten und Datentypen~~ — beim Bau festgelegt (T8) und am 26.08.2026 oben unter
  „Die Spalten, wie sie seit T8 stehen" festgehalten
- Umgang mit gleichzeitigem Zugriff, falls später eine Weboberfläche hinzukommt
  (siehe Architekturregel in Abschnitt 1)
- **Der Regel-Kommentar über `profile.record_card` begründet falsch.** Er nennt als Grund,
  „ein zweiter Lauf erzeugte in Anki stumm eine Doppelnotiz". Das trifft nicht zu und
  widerspricht Abschnitt 8b: Weil `anki.new_card_guid` stabil ist, aktualisiert Anki dieselbe
  Notiz. Der echte Grund steht oben unter „Jetzt billig, später teuer: die Anki-Kennung" —
  der Rückkanal aus Phase 3. Zu berichtigen ist der Kommentar, nicht die Zeile darunter
- **Die Profil-Identität einer Bedeutung umfasst `wikdict_trans_list`, die Anki-GUID
  bewusst nicht** (Abschnitt 8b, „Befund: die vorgegebene GUID bindet den Feldinhalt"). Zwei
  `sense`-Zeilen, die sich nur in der Übersetzungsliste unterscheiden, teilen sich damit
  still eine `card`-Zeile. Im heutigen Wörterbuch ist der Fall nirgends auslösbar (11.961
  Bedeutungen über 157.801 Zeilen geprüft); beim nächsten Wörterbuchbezug kann er entstehen,
  und dann ist er nicht mehr `leicht`
- **Die beiden Idempotenz-Tests prüfen nicht, was ihr Docstring behauptet**
  (`tests/test_profile.py`, `tests/test_cli_export.py`): Sie reichen **dasselbe**
  `Card`-Objekt zweimal hinein und prüfen damit SQLites `UNIQUE(guid)`, nicht die Stabilität
  von `anki.new_card_guid`. Zwei getrennt erzeugte Karten desselben Eintrags wären die
  Zusicherung, um die es geht (dokumentation.md §5)

---

## 5. Lemmatisierung und Eigennamenerkennung — entschieden

**spaCy mit `en_core_web_md`. Stanza und `en_core_web_trf` bleiben vorgemerkt, nicht
verworfen.**

Die letzte Entscheidung vor Phase 1.

### Gemessene Ergebnisse

Geprüft am 12.08.2026 mit [`tools/nlp_check.py`](tools/nlp_check.py) an denselben zwei
Romanen wie die Abdeckungsmessung, jeweils vollständig statt in Stichproben:

| | sm · Holmes | **md · Holmes** | sm · Dorian | **md · Dorian** |
|---|---|---|---|---|
| Restlücke | 0,85 % | **0,81 %** | 0,90 % | **0,86 %** |
| Reihenfolge (18 Fallen) | 17 | 17 | 17 | 17 |
| **stille Fehlschläge verhindert** | 4/5 | **5/5** | 4/5 | **5/5** |
| übersehene Eigennamen | 2 | 3 | 5 | 3 |
| getrennte Phrasal Verbs | 21 % | 21 % | 19 % | 19 % |
| Durchsatz | 4.350 W/s | 4.085 W/s | 4.305 W/s | 3.668 W/s |
| Platte | 15 MB | 54 MB | | |

Lizenz: spaCy MIT, Modelle `en_core_web_*` MIT. Unkritisch auch für eine spätere
Veröffentlichung.

### Der Unterschied liegt in der Fehlerart, nicht in der Trefferzahl

Beide Größen machen einen Fehler von achtzehn — aber nicht denselben, und das entscheidet:

```
sm:   wound (VERB)  →  wound    statt wind    „wound" steht im Wörterbuch
md:   geese (NOUN)  →  geese    statt goose   „geese" steht nicht drin
```

sm erzeugt damit genau die Fehlerart, die dieses Dokument unter „Die Falle: es scheitert
nicht laut, sondern leise" beschreibt: eine falsche Übersetzung ohne jedes Anzeichen von
Unsicherheit. mds Fehler dagegen läuft in eine erkennbare Wörterbuchlücke und wird als
solche gemeldet.

> Ausgewählt wird nach verhinderten **stillen** Fehlschlägen, nicht nach der
> Trefferquote. Der Unterschied 5/5 gegen 4/5 wiegt schwerer als 0,04 Prozentpunkte
> Restlücke.

Die 6 % geringere Geschwindigkeit und 39 MB mehr auf der Platte sind demgegenüber
gegenstandslos: Ein Kapitel dauert rund **eine Sekunde**, ein ganzes Buch 26.

### Die Restlücke ist kleiner als geschätzt

Die 0,81 % bestätigen die Schätzung von „≈ 1,0 %" aus Abschnitt 2 — und sind selbst noch
zu pessimistisch. Von den rund 820 verbleibenden Wörtern entfallen 335 auf `could` (287)
und `having` (48): spaCy führt Modalverben nicht auf `can` zurück, und WikDict führt
weder `could` noch `having` als Stichwort. Beides sind Funktionswörter, die nie
Lernvokabeln werden.

> **Bereinigt liegt die echte Lücke bei etwa 0,5 %.**

Was übrig bleibt, ist genau das, was Abschnitt 2 vorhergesagt hat: `hansom`, `gipsy`,
`reasoner`, `assize`, `brougham` — selten und randständig.

### Warum nicht Stanza

Stanza wurde **nicht gemessen**. Es hätte ein Ergebnis schlagen müssen, das die
selbstgesetzten Kriterien bereits nimmt, und dafür rund 650 MB samt PyTorch gekostet.
Diese Begründung ist ausdrücklich eine Aufwandsabwägung, keine Qualitätsaussage über
Stanza — deshalb bleibt es vorgemerkt.

Gleiches gilt für **`en_core_web_trf`**, die genaueste spaCy-Stufe. Beide kommen in
Frage, falls beim Bauen Lemmatisierungsfehler auffallen. `en_core_web_lg` dagegen
scheidet aus: Es unterscheidet sich von `md` im Wesentlichen durch mehr Wortvektoren, und
Wortvektoren braucht dieses Programm an keiner Stelle.

Zur Hardware: Der Zielrechner aus Abschnitt 3 (RX 5700, RDNA1) hat kein CUDA. Ein zweiter
Rechner mit NVIDIA MX450 hat es, dort aber mit 2 GB Grafikspeicher der Einsteigerklasse —
eine `trf`-Messung dort wäre nicht auf den Zielrechner übertragbar. Solange beide
Maschinen gelten, darf der Kern CUDA ohnehin nicht voraussetzen.

### Neuer Befund: der Eigennamenfilter muss pro Vorkommen greifen

Die Messung hat eine Falle aufgedeckt, die das Konzept so nicht vorgesehen hat.

In die eine Fehlerrichtung ist die Erkennung ausgezeichnet: Nur drei Wortformen wurden
übersehen, und alle drei sind Nationalitätsadjektive (`indian`, `british`, `bohemian`),
also ohnehin lernbare Vokabeln.

In die andere Richtung greift sie jedoch weit: **216 Wortformen gelten *manchmal* als
Eigenname, kommen aber auch als gewöhnliches Wort vor.**

| Wortform | als Eigenname / gesamt |
|---|---|
| `street` | 61 / 83 |
| `sir` | 38 / 78 |
| `red` | 10 / 51 |
| `doctor` | 16 / 39 |
| `orange` | 8 / 11 |

> **Regel:** Der Eigennamenfilter wirkt auf das **Vorkommen**, nie auf die Grundform.
> Ein Wort, das irgendwo im Buch als gewöhnliches Wort auftritt, bleibt Lernvokabel —
> auch wenn es anderswo Teil eines Namens ist.

Wer pro Grundform filtert, verliert `red` und `orange` vollständig aus der Triage. Das
passt zur Datenablage aus Abschnitt 4: Kenntnis hängt an der Bedeutung, und `occurrence`
ist ohnehin die Ebene, auf der Belegsatz und Häufigkeit geführt werden.

### Nachtrag 17.08.2026: nur fünf Wortarten kommen in die Wortliste

Vorher wurde allein `AUX` ausgesteuert, und damit standen `the`, `his` und `by` in der
Triage. Seit dem 17.08.2026 gilt eine **erlaubte Liste**: In die Wortliste kommen nur
`NOUN`, `VERB`, `ADJ`, `ADV` und `INTJ` (`extraction._CONTENT_POS`). `PROPN` bleibt davon
unberührt und wird weiterhin gesondert **je Vorkommen** behandelt (Regel 12).

**Nachgemessen am 19.08.2026** über ganz `tools/sherlock.txt` (108.922 Wörter, spaCy
`en_core_web_md`): Von 6.229 Grundformen fallen **114** weg, das sind **50.767 von 99.457**
Token — gut die Hälfte des Textes, aber nur 1,8 % der Grundformen. Nach Wortart: `PRON`
17.042 · `ADP` 12.196 · `DET` 10.566 · `CCONJ` 4.092 · `SCONJ` 3.822 · `PART` 2.202 · `NUM`
832 · `X` 15.

Die 114 weggefallenen Grundformen einzeln durchgesehen: **85 reine Funktionswörter**, **20
Zahlwörter** (`two`, `three`, `fifty`) und **9 fremdsprachige Einsprengsel**, die spaCy als
`X` führt (`bijou`, `cœur`, `métier`, `fait accompli`, `incognito`). Nur die letzte Gruppe
ist überhaupt ein Verlust — neun Wörter in einem ganzen Buch, sämtlich französisch und im
englisch-deutschen Wörterbuch ohnehin unsicher.

Der Filter ist zugleich der Grund, warum **T4 auf der Abhängigkeitsanalyse arbeiten muss**
und nicht auf der Wortliste: Die Partikel der getrennten Verb-Partikel-Paare sind `ADP` und
`PART` — aus der Wortliste sind sie damit verschwunden.

### Nachtrag 25.08.2026: Anteilsschwellwert statt striktem Kleiner-Zeichen

Der Filter aus dem Abschnitt „Neuer Befund" oben wirkt korrekt je Vorkommen, filterte aber
zu schwach: „Lernvokabel bleibt, was mindestens ein nicht-eigennamiges Vorkommen hat"
(`proper_noun_frequency < frequency`) ließ Titelfiguren durch, deren Grundform fast, aber
nicht ganz nur als Name auftritt. In `tools/dorian_gray.epub` Kapitel 16 stehen 25 von 26
Vorkommen von „Dorian" als PROPN (Anteil 0,96) — das eine übrige Vorkommen genügte, um die
Titelfigur selbst als Lernvokabel durchzulassen, bis auf Rang 4 der nach Häufigkeit
sortierten Triage. „Sibyl" in Kapitel 7 traf denselben Fall (26 von 28, 0,93).

**Regel 12 gilt jetzt mit einem Anteilsschwellwert:** Ein Vorkommen bleibt Lernvokabel,
solange der Anteil eigennamiger Belege am Gesamtvorkommen unter 0,90 bleibt
(`extraction._PROPER_NOUN_RATIO_THRESHOLD`). Gemessen über alle Kapitel von
`tools/dorian_gray.epub` und `tools/sherlock.epub` (36 Kapitel, 361 Grundformen mit
mindestens einem Eigennamen-Vorkommen, 25.08.2026): Bei 0,90 fallen neben „Dorian" und
„Sibyl" (Kapitel 7) sechs weitere Grundformen weg, die jeweils in einem einzelnen Kapitel
fast nur als Namensbestandteil auftreten — „baker" (Henry Baker, Sherlock Kap. 8, 16/17),
„hunter" (Violet Hunter, Kap. 13, 19/21), „king" (King of Bohemia, Kap. 2, 17/18),
„league" (Red-Headed League, Kap. 3, 15/16), „lord" (Lord St. Simon, Kap. 11, 36/37),
„miss" (Titel vor einem Namen, Kap. 9, 18/19). Echte Anredesubstantive bleiben davon
unberührt — höchster gemessener Anteil je Kapitel über beide Bücher: „lady" 0,88, „sir"
0,86, „street" 0,82, „charming" 0,88 (`Prince Charming`, korrekt kein Fund oberhalb der
Schwelle), „mother" 0,71, „duchess" 0,35 —, alle unter 0,90.

Zwei Nachbarwerte wurden mitgemessen: 0,80 risse zusätzlich „lady" mit (0,80 in Kapitel 17
erfüllt „≥"), 0,95 ließe „Sibyl" in Kapitel 7 (0,93) unberührt. 0,90 ist der Kompromiss,
den keiner der beiden Nachbarwerte bietet. **Der Filter wirkt seit dem 26.08.2026 auf den
buchweiten Anteil** (Nachtrag unten), nicht mehr auf den Anteil des einzelnen Kapitels —
die Vermutung, ein buchweiter Wert risse „lady" mit herein, hat sich beim Nachmessen nicht
bestätigt.

### Nachtrag 26.08.2026: Buchweiter Anteil statt je Kapitel angewendet

Sibyls zweites Vorkommen (Kapitel 10, 13 von 16, Anteil 0,81) blieb unter der Schwelle und
damit Lernvokabel, mit dem Belegsatz „Sibyl dead!" — spaCy vertaggt drei elliptische
Ausrufe dieses Kapitels („Sibyl dead!", „Did Sibyl—?", „Sibyl!") als NOUN statt PROPN,
Tagger-Fehler in Ein-Wort-Ausrufen, kein Sprachbefund. Der Anteil **je Kapitel** kann
diesen Fall nicht lösen: Ein einzelnes Kapitel mit wenigen Vorkommen kippt durch drei
Fehltaggings vollständig.

**Regel 12 wendet den Schwellwert jetzt auf den Anteil über das ganze Buch an**
(`extraction.book_proper_noun_ratios`, angewendet in `extract_vocabulary`), nicht mehr auf
den Anteil des einzelnen Kapitels — der Schwellwert selbst bleibt 0,90. Gemessen an
`tools/dorian_gray.epub` und `tools/sherlock.epub` (36 Kapitel, mit `extract_vocabulary`
selbst statt einer nachgebauten Näherung, 26.08.2026): Buchweit steht „Sibyl" bei 80 von 85
Vorkommen als PROPN (0,94) und fällt jetzt in **jedem** Kapitel weg, auch in Kapitel 10.
Über beide Bücher hinweg fällt **sonst kein einziges** zusätzliches Wort weg, das unter der
Je-Kapitel-Regel noch Lernvokabel war — insbesondere bleiben „lady" (60/74 = 0,81
buchweit), „sir" (0,55 Dorian / 0,49 Sherlock), „street", „mother", „duchess", „uncle" in
jedem Kapitel erhalten, in dem sie keine Namensbestandteile sind. Zwei Wörter werden durch
den buchweiten Wert sogar **zusätzlich** als Lernvokabel gehalten, die die Je-Kapitel-Regel
verloren hatte: „king" (Sherlock Kap. 2, „A Scandal in Bohemia", 17 von 18 Vorkommen lokal
PROPN, buchweit aber nur 24 von 27 = 0,89, unter der Schwelle) und „miss" (Sherlock Kap. 9,
18 von 19 lokal, buchweit 79 von 101 = 0,78) — beides Wörter mit echter, wenn auch seltener
gewöhnlicher Verwendung im jeweiligen Kapitel, die vorher hinter der Namenshäufung
verschwand.

Notwendige Zusatzbedingung, ohne die die Prüfung selbst fehlschlägt: Der buchweite Wert
wird nur angewendet, wenn das **Kapitel selbst** mindestens ein PROPN-Vorkommen der
Grundform hat (`proper_count`), und **nie**, wenn im Kapitel ausschließlich
eigennamige Vorkommen stehen (`proper_count == frequency`) — dann gibt es keinen Beleg für
die gewöhnliche Verwendung, den ein buchweiter Wert rechtfertigen könnte. Ohne diese zweite
Bedingung hätte ein Wort wie „frank" (Sherlock, in einer Kurzgeschichte fast nur der Name
„Frank Moulton", buchweit 19 von 20 = 0,95) auch in Kapitel 5 verloren gehen können, wo es
ausschließlich als gewöhnliches Adjektiv vorkommt („His frank acceptance…", 0 von 1 lokal
PROPN) — genau der Fall, den die Prüfung an beiden Büchern verhindern soll. An zwölf
gezielt beobachteten Wörtern über beide Bücher (`lady`, `sir`, `street`, `mother`,
`duchess`, `uncle`, `king`, `miss`, `lord`, `baker`, `hunter`, `league`) und an der
vollständigen Differenz aller 36 Kapitel geprüft (Bericht zur Abnahme T17, zweiter Anlauf).

Kosten: Der buchweite Wert braucht einen vollen spaCy-Lauf über **jedes** Kapitel des
Buchs, nicht nur das gewählte — `pipeline.run_chapter` liest dafür alle Kapitel des Buchs
vorab ein. Gemessen an den beiden EPUBs unter `tools/`: rund 22 s (`dorian_gray.epub`, 22
Kapitel) beziehungsweise 29 s (`sherlock.epub`, 13 Kapitel mit Fließtext) — gegenüber den
rund 1,1 s, die `run_chapter` zuvor für Nachschlagen und Profilabgleich allein brauchte
(„Nachtrag 17.08.2026" oben). Ein Kapitel, das nur aus Vorspann, Impressum oder — bei einem
reinen Bildband — ganz ohne Fließtext besteht, trägt nichts zur Statistik bei und wird
übersprungen (dieselbe Meldung, die `epub.read_chapter` dafür schon liefert).

### Offene Punkte

- Über-Lemmatisierung von Eigennamen (`Holmes` → `holme`) — harmlos, solange der Filter
  aus dem vorigen Abschnitt greift, aber beim Anlegen der Liste „Figuren & Orte" zu
  beachten
- **Ob der buchweite Eigennamenanteil zwischengespeichert wird.** Er kostet je
  Kapiteldurchlauf einen vollen spaCy-Lauf über **alle** Kapitel des Buchs — 22 s
  (`dorian_gray.epub`) beziehungsweise 29 s (`sherlock.epub`) gegenüber rund 1,1 s vorher
  (Nachtrag 26.08.2026 oben). Regel 14 verlangt für einen Zwischenspeicher einen gemessenen
  Anlass; der liegt damit vor, und er ist der erste im Projekt. Naheliegend ist, den Wert je
  Buch im Profil zu halten (`book`-Tabelle, Abschnitt 4) — zu entscheiden ist dabei vor
  allem, **wann er verfällt**: bei geänderter Datei und bei neuer spaCy- oder
  Modellfassung, denn beide ändern die Vertaggung, aus der der Anteil entsteht
- ~~Ob die Wortart als Vorfilter für lange Auswahllisten taugt~~ — **gemessen am
  26.08.2026** (Abschnitt 3, „Nachtrag 26.08.2026: was der Wortartfilter kürzt — und was er
  kostet"): Sie taugt dafür, aber schwächer als angenommen. Was daran offen bleibt, steht in
  den Offenen Punkten von Abschnitt 3, nicht mehr hier

---

## 6. Projektgerüst und Werkzeuge — entschieden

**Python 3.12. `uv` für Umgebung und Abhängigkeiten, `ruff` zum Formatieren und Prüfen,
`pytest` für Tests, `mypy` für Typen. `pyproject.toml` ist die einzige Quelle.**

### Warum das eine Entscheidung ist und keine Formsache

Die Abschnitte 1 bis 5 beantworten, *womit* gebaut wird. Dieser beantwortet, *woran sich
das Gebaute messen lassen muss* — und das ist hier keine Nebensache, weil der Code zum
großen Teil maschinell entsteht. Dabei verschiebt sich der Engpass vom Schreiben zum
**Prüfen**: Code fällt schneller an, als ein Mensch ihn lesen kann.

Ein Tor, das jede Änderung passieren muss, wirkt darum stärker als jede Regel, die nur
gelesen wird. Es ist zugleich die Anwendung des Maßstabs aus dokumentation.md §5 auf die
Werkzeugfrage:

> Was eine Maschine prüfen kann, gehört in ein Werkzeug und nicht in ein Dokument.
> Eine Regel, die niemand prüft, ist eine Absichtserklärung.

Der Nebengewinn ist konkret: Die Kleinigkeit „Dateien immer mit `encoding="utf-8"`
öffnen" (dokumentation.md §8) steht bisher in einer Aufzählung, die man beim Schreiben
gelesen haben muss. Sie ist maschinell prüfbar — siehe „Offene Punkte".

### Python 3.12 — Messgrundlage, nicht bloß zulässige Fassung

Beide Kernabhängigkeiten lassen einen breiten Bereich zu:

| Paket | zulässig |
|---|---|
| spaCy 3.8.15 | `>=3.9,<3.15` |
| PySide6 6.11.1 | `>=3.10,<3.15` |

3.10 bis 3.14 wären also möglich. Festgelegt wird **3.12**, weil die Messumgebung unter
`.venv/` auf 3.12.10 läuft und die Zahlen aus Abschnitt 5 dort entstanden sind. Eine
andere Fassung zöge die Grundlage einer bereits getroffenen Entscheidung weg, ohne dafür
etwas einzubringen. `requires-python` ist entsprechend eng auf `>=3.12,<3.13` gesetzt;
3.13 und 3.14 bleiben später offen, keine Abhängigkeit blockiert sie.

### Die Werkzeuge und ihre Lizenzlage

Geprüft am 12.08.2026, wie in Abschnitt 1 gefordert **vor** der Aufnahme:

| Zweck | Werkzeug | Fassung | Lizenz |
|---|---|---|---|
| Formatieren und Linten | ruff | 0.16.2 | MIT |
| Tests | pytest | 9.1.1 | MIT |
| Typprüfung | mypy | 2.3.0 | MIT |
| Umgebung und Abhängigkeiten | uv | 0.12.3 | MIT oder Apache-2.0 |

Kein starkes Copyleft, keine Einschränkung für eine spätere quelloffene Veröffentlichung.

Nachtrag zu Abschnitt 1: PySide6 wird auf PyPI nicht schlicht „unter LGPL" angeboten,
sondern als Wahl aus `LGPL-3.0-only`, `GPL-2.0-only` und `GPL-3.0-only`. LGPL ist davon
eine — die Aussage dort bleibt richtig, sie beschreibt nur eine von drei Möglichkeiten.

### Warum diese und keine anderen

- **ruff statt black + isort + flake8.** Ein Werkzeug, eine Konfiguration, ein Aufruf.
  Drei Werkzeuge, die sich in Randfällen widersprechen, sind für ein Projekt dieser
  Größe reiner Verwaltungsaufwand
- **mypy statt pyright.** pyright ist schneller und schließt besser, bringt aber Node.js
  als zweite Laufzeit mit. Das widerspräche Abschnitt 1, „Python als einzige Sprache" —
  und die Einsprachigkeit ist dort mit Bedacht gewählt worden, nicht aus Bequemlichkeit
- **uv statt pip.** Entscheidend ist `uv.lock`: Sie hält die vollständige Auflösung aller
  60 Pakete fest. Erst damit ist die Messgrundlage aus Abschnitt 5 wiederherstellbar und
  nicht nur ungefähr beschrieben. Die Sperrdatei gehört deshalb **ins Repository**
- **Das spaCy-Modell hängt an seiner Prüfsumme.** `en_core_web_md` liegt nicht auf PyPI;
  in `pyproject.toml` steht die Wheel-Adresse samt `sha256`. Abschnitt 5 gilt für dieses
  Artefakt, nicht für „irgendein `md`-Modell"

### Die Architekturregel steht jetzt in der Umgebung

Die Regel aus Abschnitt 1 — der Kern kennt die Oberfläche nicht — ist bisher eine
Absicht. In `pyproject.toml` wird sie zum Zustand: **PySide6 steht nicht bei
`dependencies`, sondern in einer eigenen Gruppe `gui`.** Wer nur den Kern installiert,
hat Qt gar nicht zur Verfügung; ein versehentlicher Import scheitert dann sofort und
nicht erst im Gespräch über die Architektur.

### Falle: `uv sync` beschneidet die Messumgebung

`uv sync` bringt die Umgebung auf genau den Stand von `pyproject.toml` — und entfernt,
was dort nicht steht. In `.venv/` liegt aber neben `en_core_web_md` auch
`en_core_web_sm` aus dem Vergleich in Abschnitt 5.

> **Regel:** Die Werkzeuge wurden mit `pip` in die bestehende `.venv/` gelegt, nicht mit
> `uv sync`. Wer die Umgebung synchronisiert, verliert das Vergleichsmodell und muss es
> nachladen, bevor `nlp_check.py` wieder läuft.

### Zwei Prüfregeln arbeiten gegen die Hausordnung

Beim ersten Lauf über den Bestand haben sich zwei Regeln als unbrauchbar erwiesen. Beide
sind mit Begründung in `pyproject.toml` abgeschaltet:

| Regel | Warum sie hier stört |
|---|---|
| `RUF001`–`RUF003` | halten Gedankenstrich und typografische Anführungszeichen für verwechselbare Zeichen. In deutschen Kommentaren (dokumentation.md §1) meldet die Regel als Fehler, was die Sprachregel verlangt |
| `SIM905` | will `"""be am is are …""".split()` zum Listenliteral machen — aus einem überschaubaren Wortblock würden mehrere hundert Zeilen |

Dazu eine Formatiereinstellung: `skip-magic-trailing-comma`. Ohne sie sprengt ein
abschließendes Komma jede mehrzeilige Sammlung in eine Zeile je Eintrag, was die
kompakten Wortlisten in `tools/` unlesbar macht.

`E501` bleibt dagegen **an**, obwohl der Formatierer die Zeilenlänge schon regelt: Er
bricht Code um, aber keine Prosa. Die langen deutschen Docstrings aus dokumentation.md §3
liefen sonst ungeprüft.

### Nachtrag 17.08.2026: `mypy --strict` trägt die spaCy-Typen

Ob die strenge Typprüfung mit spaCy im Spiel noch trägt, stand hier als offener Punkt und
war der Grund, warum Phase 1 mit `extraction` und `dictionary` begonnen hat. Mit dem ersten Modul ist
die Frage beantwortet: **ja**. spaCy liefert `py.typed` mit, mypy löst `token.pos_`,
`token.lemma_` und `sent.text` zu `str` auf und `token.is_alpha` zu `bool`;
`extraction.py` besteht `strict` ohne eine einzige Ausnahme.

**Folge:** Die Ausnahme `ignore_missing_imports` für `spacy.*` und `en_core_web_md.*` ist
aus `pyproject.toml` entfernt. Das Modellpaket bringt zwar kein `py.typed` mit, wird aber
nirgends importiert — `spacy.load("en_core_web_md")` lädt es über seinen Namen, und
`test_environment.py` prüft es mit `importlib.util.find_spec`. Wer es doch einmal
importiert, holt die Ausnahme mit dieser Begründung zurück.

### Der Bestand ist nachgezogen

Das ganze Repository besteht das Tor: `ruff format`, `ruff check`, `mypy` und `pytest`
laufen sauber durch. Der erste Lauf hatte 13 Verstöße und rund 500 Zeilen Umformatierung
ergeben, sämtlich in `tools/`; beides ist am 12.08.2026 nachgezogen worden — aus
demselben Grund wie `werkzeuge/` → `tools/`: Ein Bestand, der der Regel widerspricht,
setzt die Regel außer Kraft (dokumentation.md §1).

Inhaltlich behoben wurden: zweimal `SIM115` (Datei ohne Kontextverwalter geöffnet),
zweimal `B904` (`raise` im `except` ohne `from`), je einmal `SIM105`, `UP035`, `I001`,
dazu sechs zu lange Zeilen.

**Die Messwerte in diesem Dokument sind davon nicht berührt** — und das ist nicht
angenommen, sondern nachgemessen: `coverage_check.py` und `nlp_check.py` wurden vor und
nach dem Eingriff an `sherlock.txt` laufen gelassen. Die Ausgaben sind bis auf die
Laufzeitzeilen (Ladezeit, Durchsatz, Hochrechnung) zeichengleich; Restlücke 0,98 %,
17/18 und 21 % stehen unverändert.

Zwei Wortlisten — `CONTRACTIONS` und `PARTICLES` — hat der Formatierer dabei in eine
Zeile je Eintrag zerlegt. Sie stehen jetzt in derselben Blockschreibweise wie
`IRREGULAR_FORMS` daneben. Dass die Mengen dabei unverändert geblieben sind, ist gegen
den Stand in Git geprüft.

### Offene Punkte

- **`encoding="utf-8"` maschinell erzwingen.** ruff kennt dafür `PLW1514`; ob die Regel
  ohne `preview` verfügbar ist, ist noch nicht geprüft. Gelänge es, wanderte eine
  Kleinigkeit aus dokumentation.md §8 aus der Prosa in das Tor
- **Ob eine `.gitattributes` die Zeilenenden festnagelt.** Im Index liegt inzwischen jede
  verfolgte Datei mit LF (geprüft am 26.08.2026 mit `git ls-files --eol`), im **Arbeitsbaum**
  dagegen 18 mit CRLF und 37 mit LF: `core.autocrlf` steht auf `true` und wandelt beim
  Auschecken um, während ein Werkzeug, das eine Datei neu schreibt, sie mit LF hinterlässt.
  Wer für eine Verfälschungsprobe (dokumentation.md §5) einen mehrzeiligen Textanker im
  Quelltext sucht, findet ihn deshalb in der einen Datei und in der anderen nicht — und
  deutet den Fehlschlag leicht als „Anker falsch abgeschrieben" statt als
  Zeilenende-Unterschied. `* text=auto eol=lf` würde das beenden, berührt aber als einmalige
  Umstellung jede Datei und gehört deshalb entschieden, nicht nebenbei gemacht
- `tools/` bleibt von der Typprüfung ausgenommen — Messskripte, reine Standardbibliothek.
  Ob das so bleibt, ist offen; berührt wird es erst, wenn ein Messskript in den Kern wandert
- **Auslieferung** (Nuitka, PyInstaller) bleibt offen wie in Abschnitt 1; sie berührt das
  Gerüst erst, wenn das Programm an Fremde geht

---

## 7. Modulaufteilung des Kerns und Importregel — entschieden

**Zehn Module entlang der sechs Schritte des Kernablaufs. Jeder Schritt kennt nur
`entities`; verkettet werden die Schritte allein in `pipeline`.**

### Warum eine Karte und nicht mehr

Abschnitt 1 fordert den Kern „ohne jeden Bezug zur Oberfläche", nennt aber weder die
Module noch die erlaubten Importe. Die Karte schließt diese Lücke und tut sonst nichts:
ein Satz je Modul, dazu die Importrichtung. Sie sagt, **wo** etwas hingehört, nicht wie es
auszusehen hat — Entwürfe für Code, der noch nicht geschrieben ist, wären genau die
Vorratsarbeit, die Regel 14 untersagt.

### Die Module

| Modul | Zuständigkeit |
|---|---|
| `entities` | Die Gegenstände des Kernablaufs — `book`, `chapter`, `lemma`, `sense`, `occurrence`, `event`, `card` aus Abschnitt 4. Importiert selbst nichts aus dem Kern |
| `epub` | Schritt 1: EPUB öffnen, Metadaten und Kapitelstruktur lesen, Fließtext von Inhaltsverzeichnis, Impressum und Fußnoten trennen |
| `extraction` | Schritt 2: Kapiteltext zu Grundformen — Tokenisierung, Wortart, Lemmatisierung, Eigennamenfilter, Häufigkeit, Belegsatz. Schlägt **nicht** nach |
| `profile` | Schritt 3: der einzige Zugriff auf `profil.sqlite3` — Ereignisfolge, daraus abgeleiteter Kenntnisstand, Abgleich gegen den Kapitelwortschatz |
| `triage` | Schritt 4, soweit er im Kern liegt: Häufigkeitssortierung, Wortobergrenze, Sammelaktion. Die Entscheidung selbst trifft der Nutzer |
| `dictionary` | Schritt 5, erste Hälfte: der einzige Zugriff auf `en-de.sqlite3` samt dessen Erstbezug — liefert je Grundform die Auswahlliste |
| `translation` | Schritt 5, zweite Hälfte: der einzige Ort, an dem das Modell angesprochen wird — Auswahl aus der vorgelegten Liste |
| `anki` | Schritt 6: Anki-Deck samt GUID je Karte |
| `printout` | Schritt 6: Kapitelliste als Druckseite |
| `pipeline` | Verkettet die Schritte zu einem Durchlauf für ein Kapitel — dem Abnahmeziel der Phase 1 |

Vier dieser Grenzen sind keine Geschmacksfrage. Sie machen Regeln aus den Abschnitten 1
bis 5 zu Modulgrenzen, und das ist ihr eigentlicher Zweck: Eine Regel, die auf einer
Dateigrenze liegt, wird nicht versehentlich verletzt, sondern nur absichtlich.

- **`extraction` und `dictionary` getrennt**, weil die Reihenfolge Wortart → Grundform →
  Nachschlagen zwingend ist („Warum die Reihenfolge zwingend ist"). Ein Modul, das beides
  täte, könnte den Schritt dazwischen überspringen — und der `saw`-Fall scheitert leise
- **`profile` und `dictionary` getrennt**, weil die Dateien es sind (Abschnitt 4). Damit
  ist Regel 4 an der Datei ablesbar und nicht erst am Verhalten
- **`translation` als einziger Ort mit Modellzugriff.** Sonst verteilt sich
  `reasoning_effort: "none"` (Regel 7) über den Kern und fehlt irgendwann an einer Stelle
- **`triage` liegt größtenteils nicht im Kern.** Sortierung, Obergrenze und Sammelaktion
  sind Rechenschritte; die Triage selbst ist Bedienung

### Die Importregel

> **Oberfläche → Kern, nie umgekehrt.** Innerhalb des Kerns importiert jeder Schritt nur
> `entities`. Wer mehrere Schritte kennt, ist `pipeline` — und sonst niemand.

Der erste Satz ist die Architekturregel aus Abschnitt 1. Der zweite ist neu und zahlt
zweifach: Solange die Schritte einander nicht aufrufen, lässt sich jeder für sich prüfen —
`translation` bekommt seine Auswahlliste als Argument und braucht dafür keine
Wörterbuchdatei. Und der Ablauf steht an einer Stelle statt verteilt in der Oberfläche,
womit der Kommandozeilenzugang aus Abschnitt 1 wirklich geschenkt ist, statt nachgebaut zu
werden.

Die äußere Hälfte der Regel setzt `pyproject.toml` bereits durch (Abschnitt 6, „Die
Architekturregel steht jetzt in der Umgebung"). Geprüft wird sie in
`tests/test_architecture.py`; damit verlässt Regel 9 zur Hälfte die Liste der
Bauentscheidungen ohne Testpunkt (dokumentation.md §5).

### Die Oberfläche liegt neben dem Kern, nicht darunter

Die Karte oben beschreibt **nur den Kern**. Eine Oberfläche steht nicht darin, und zwar
absichtlich: Sie ruft ihn auf, er kennt sie nicht (Abschnitt 1, „Architekturregel"). Die
Kommandozeile ist eine Oberfläche wie jede andere — der Zugang, über den Phase 1
abgenommen wurde, weil er nach Abschnitt 1 „praktisch geschenkt" ist, sobald der Kern die
Oberfläche nicht kennt.

Sie liegt deshalb als eigenes Paket `cli/` **neben** `libreverbum/`, nicht darunter
(entschieden bei T16, 21.08.2026; die erwogene Alternative war ein dünnes
`libreverbum/__main__.py`, das die Oberfläche in den Kern gelegt hätte). Die Importregel
gilt nur innerhalb von `libreverbum/`: `cli` darf beliebig viele Kernmodule zugleich
importieren, der Kern importiert `cli` nie — `tests/test_architecture.py` prüft die
Richtung.

**Für die Qt-Oberfläche gilt dasselbe** — und dort gilt Regel 9 zum ersten Mal in ihrer
nicht prüfbaren Hälfte: NLP- und Modellaufrufe nie im Oberflächen-Thread. Bei der
Kommandozeile war das gegenstandslos, weil sie keinen hat.

### Warum `entities` und nicht `model`

Der naheliegende Name wäre `model` — er ist vergeben. „Das Modell" bezeichnet in diesem
Projekt durchgehend das LLM (Abschnitt 3). Ein `model.py` neben `translation.py` erzeugte
genau die Doppelbedeutung, gegen die die Begriffstabelle in dokumentation.md §2 angelegt
ist.

### Die Liste „Figuren & Orte" ist Phase 2

Entschieden am 21.08.2026 mit dem Bau der Druckausgabe (T14). konzept.md §6, „Export"
führt sie unter „Druckausgabe" als *optionalen* Anhang, in derselben Aufzählung wie das
„Lesezeichen-Format" — und der Phasenplan zählt „Lesezeichen-Druck und weitere
Druckvarianten" ausdrücklich zu Phase 2; der Phase-1-Satz und Abnahmekriterium 5 nennen
nur die eine Kapitelliste. In Phase 1 entsteht sie deshalb nicht (Regel 14).

Würde sie gebaut, gehörte das Zusammenstellen nach `printout` und nicht nach `extraction`:
`extraction` liefert je Vorkommen bereits, wie oft es ein Eigenname war
(`Occurrence.proper_noun_frequency`, Regel 12) — mehr braucht die Liste nicht, und eine
zweite Ausgabeliste daraus ist Ausgabe, keine Extraktion.

### Offene Punkte

- **Ob `pipeline` je Schritt eine eigene Zwischenablage braucht** oder ein Durchlauf am
  Stück genügt. Für ein Kapitel von einer Sekunde Rechenzeit (Abschnitt 5) genügt er
  vermutlich; gemessen ist es nicht
- **Die Oberfläche ist nicht aufgeteilt.** Sie liegt außerhalb des Kernpakets, ihre
  Gliederung wird entschieden, wenn sie gebaut wird
- **Das Zurückschreiben der Anki-GUID hängt an der Kommandozeile** (`cli/export.py`),
  obwohl „verkettet wird allein in `pipeline`" oben etwas anderes verlangt. Unter Regel 14
  ist das heute vertretbar — es gibt genau einen Aufrufer. **Beim Bau der Qt-Oberfläche muss
  der Schritt mitwandern:** Eine zweite Oberfläche, die exportiert, ohne ihn nachzubauen,
  verletzt Regel 6 lautlos, und bemerkt wird das erst am Anki-Rückkanal in Phase 3
  (Abschnitt 4, „Jetzt billig, später teuer")
- **Der einzige Ende-zu-Ende-Test prüft die Druckseite, nicht das Profil.** Eine Zusicherung
  auf die `card`-Zeilen war in der Verfälschungsprobe zu T16 der wirksamste fehlende Zusatz:
  Ein Durchlauf, der exportiert, ohne im Profil etwas zu hinterlassen, kommt heute grün durch

---

## 8. EPUB-Leser — entschieden

**Keine Bibliothek. `zipfile` und `xml.etree` für die Struktur, `html.parser` für den
Fließtext. Kapitel kommen aus der Navigation; fehlt sie, gilt jedes Dokument der
Lesereihenfolge als Kapitel — mit sichtbarem Hinweis.**

### Zuerst die Lizenzfrage

Geprüft am 12.08.2026 über die PyPI-Metadaten, wie Regel 15 es **vor** der Aufnahme
verlangt:

| Paket | Fassung | Lizenz |
|---|---|---|
| EbookLib | 0.20 | **AGPL-3.0 or later**, zieht `lxml` und `six` nach |
| beautifulsoup4 | 4.15.0 | MIT (`soupsieve` MIT, `typing-extensions` PSF) |

EbookLib ist die verbreitete Wahl und scheidet damit aus: AGPL färbt auf das ganze
Programm ab und verbaute die spätere Veröffentlichung, die Abschnitt 1 offenhalten soll.

Damit stand die eigentliche Frage: Braucht es überhaupt eine Bibliothek? Ein EPUB ist ein
ZIP-Archiv mit XML darin, und beides kennt die Standardbibliothek.

### Gemessene Ergebnisse

Geprüft am 12.08.2026 mit [`tools/epub_check.py`](tools/epub_check.py) an zwölf Dateien:
den beiden gemeinfreien Romanen der übrigen Messungen und zehn Dateien aus dem Bestand des
Nutzers — Calibre-Konvertate, ein Fachbuch, zwei Manga. Zwei davon sind keine ZIP-Archive;
die verbleibenden zehn ergeben acht verschiedene Bücher mit **570 Inhaltsdokumenten**.

| | |
|---|---|
| Inhaltsdokumente | 570 |
| davon mit `xml.etree` gelesen | **570 (100 %)** |
| Fließtext Sherlock ohne Vorspann und Lizenzdokument | 105.027 Wörter |
| dieselbe Zahl aus der Textfassung der Abschnitte 2 und 5 | 105.111 Wörter |
| **Abweichung** | **0,08 %** |

Die letzten drei Zeilen sind die eigentliche Rechtfertigung: Der Wortschatz, der aus dem
EPUB kommt, ist derselbe, auf dem die Entscheidungen 2 und 5 beruhen. Die dortigen
Messwerte tragen über den Formatwechsel hinweg und müssen nicht wiederholt werden.

Die befürchtete Bruchstelle — HTML-Entitäten wie `&nbsp;`, die in XML nicht erklärt sind —
trat in keiner der Dateien auf. `beautifulsoup4` bliebe nach dieser Messung ohne Aufgabe
und wird nach Regel 14 nicht aufgenommen. Die Lizenzlage oben steht trotzdem fest, falls
später doch ein toleranter Parser nötig wird.

### Neuer Befund: `epub:type` gibt es in der Praxis nicht

konzept.md verlangt in Schritt 1, Fließtext von Inhaltsverzeichnis, Impressum, Widmung und
Fußnoten zu trennen. Die Norm hielte dafür `epub:type` bereit. **In keiner der zwölf
Dateien kommt es vor** — zehn sind EPUB 2.0, und die beiden EPUB-3-Dateien zeichnen nichts
aus.

> **Folgerung:** Die Trennung ist eine Heuristik, keine Strukturabfrage. Bei Gutenberg
> trägt sie leicht (Vorspann 239 Wörter, Lizenzdokument am Schluss); allgemein bleibt sie
> unsicher und gehört im Zweifel gemeldet, nicht still entschieden (Regel 13).

### Neuer Befund: manchen Dateien fehlen die Kapitelgrenzen ganz

| Datei | EPUB | Navigation | Dokumente | h1–h3 | Wörter |
|---|---|---|---|---|---|
| Entwurfsmuster (Fachbuch) | 2.0 | 25 | 34 | 460 | 85.490 |
| Dorian Gray | 2.0 | 22 | 23 | 26 | 82.939 |
| Sherlock Holmes | 2.0 | 14 | 15 | 20 | 108.176 |
| Calibre-Kurzanleitung | 2.0 | 13 | 14 | 24 | 4.693 |
| Lehrbuch | 2.0 | 4 | 6 | 1 | 28.117 |
| **Roman, Calibre-Konvertat** | 2.0 | **0** | 6 | **0** | 121.315 |
| Manga (2 Bände) | 3.0 | 1 | 207 / 225 | 0 | **0** |

Zwei Beobachtungen daraus:

- **Die rohe Navigationsliste ist nicht die Kapitelliste.** Sherlock hat 18 Einträge auf 14
  eindeutige Ziele: „Contents", die Unterpunkte `I./II./III.` einer Erzählung und die
  Gutenberg-Lizenz stehen mit drin. Gezählt werden die eindeutigen Ziele
- **Jede Datei mit Überschriften hat auch ein Inhaltsverzeichnis.** Ein Rückfall auf
  `h1`–`h3` war vorgesehen und ist nach dieser Messung verworfen: Er griffe in keinem der
  Fälle, in denen er gebraucht würde. Das Calibre-Konvertat hat weder Überschriften noch
  Seitenumbruchmarken noch das Wort „chapter" im Text — nur nichtssagende `calibre1`-Klassen

> **Regel:** Kapitel kommen aus der Navigation (`nav.xhtml` oder `toc.ncx`), gezählt nach
> eindeutigen Zielen. Fehlt sie, gilt jedes Dokument der Lesereihenfolge als ein Kapitel —
> zusammen mit einem sichtbaren Hinweis, dass die Grenzen nicht aus dem Buch stammen.

Beim Calibre-Konvertat heißt das vier „Kapitel" zu je rund 30.000 Wörtern. Die Triage
bleibt dank Wortobergrenze (konzept.md, Schritt 4) benutzbar; die Zusage des Konzepts,
danach ein Kapitel am Stück zu lesen, wird sie nicht. Der saubere Weg führt über die
Quelle: Calibre kann für solche Dateien ein Inhaltsverzeichnis erzeugen. Der Nachtrag zu
Abnahmekriterium 1 in konzept.md hält das fest.

### Befund 18.08.2026: wie viel Vorspann die Heuristik wegnimmt

Beim Bau von `epub` (T12b) beantwortet: Die Trennung nutzt dieselben
Project-Gutenberg-Textmarken wie `tools/coverage_check.py` (GUTENBERG_START, GUTENBERG_END).
Bei Gutenberg-Dateien greift sie sauber — Vorspann und Lizenzdokument fallen weg. Außerhalb
von Project Gutenberg, etwa bei der DRM-freien Verlagsdatei aus T17, fehlen die Marken, und
die Trennung bleibt aus: eine allgemeine Schwelle ist durch keine Messung belegt (Regel 14).
Das Inhaltsverzeichnis bleibt auch bei Gutenberg im Fließtext stehen, weil es nach der
Startmarke steht, nicht davor (`entities.Chapter`, Docstring zu `text`).

### Was gemeldet und nicht verarbeitet wird

Drei Fälle sind kein Fall für den Kernablauf und müssen als solche erkennbar sein statt als
leeres Ergebnis (Regel 13):

| Fall | in der Messung | Verhalten |
|---|---|---|
| kein ZIP-Archiv | 2 Dateien | Meldung „keine gültige EPUB-Datei" |
| Bildband ohne Text | 2 Manga, 207 und 225 Dokumente, **0 Wörter** | Meldung; Bilder sind Phase 4 |
| verschlüsselt (`META-INF/encryption.xml`) | keine | Meldung; Kopierschutz wird nicht umgangen |

### Offene Punkte

- **Der EPUB-3-Zweig läuft gegen keine Fremdquelle.** In `tools/` liegen nur
  `sherlock.epub` und `dorian_gray.epub` — beide EPUB 2.0 mit `toc.ncx` und ohne
  `nav.xhtml` (nachgeprüft). `_read_nav`, `properties="nav"` und `epub:type` in
  `libreverbum/epub.py` prüft deshalb allein die selbstgebaute Vorrichtung, und genau davor
  warnt dokumentation.md §5: Die Vorrichtung zeigt, dass der Code läuft, die Fremdquelle
  zeigt, ob er stimmt. Geschlossen wäre der Punkt, sobald eine EPUB-3-Datei in `tools/`
  liegt (die beiden hier gemessenen Manga-Bände sind 3.0) und `needs_epub` sie einschließt
- **Anker innerhalb eines Dokuments.** Bei allen zwölf Dateien gilt ein Kapitel gleich ein
  Dokument. Ob Navigationsziele mit `#anker` als eigene Kapitel zu behandeln sind, ist
  offen — der Fall kam nicht vor
- **Bindestrich- und Sonderzeichen der Verlagsdateien** gegenüber Gutenberg sind nicht
  gesondert geprüft; die Abweichung von 0,08 % ist an einer Gutenberg-Datei gemessen

---

## 8b. Anki-Erzeugung — entschieden

**`genanki`. Die GUID vergibt LibreVerbum selbst, nicht die Bibliothek.**

### Zuerst die Lizenzfrage

Geprüft am 21.08.2026 an den maschinenlesbaren Rohquellen, wie Regel 15 es **vor** der
Aufnahme verlangt (dokumentation.md §4, „Zu Regel 15: die Rohquelle entscheidet"):

| Paket | Lizenz |
|---|---|
| **genanki 0.13.1** | **MIT** — dreifach belegt: PyPI-Metadaten, `LICENSE.txt` im Quellbaum, GitHubs Lizenz-API |
| `cached-property` | BSD |
| `chevron` | MIT |
| `pyyaml` | MIT |
| `frozendict` | **LGPL-3.0** — schwaches Copyleft |

LGPL ist kein Ausschluss: Regel 15 zielt auf **starkes** Copyleft, und der Präzedenzfall im
Projekt ist PySide6 (Abschnitt 1, „Bekannte Kosten dieser Entscheidung").

**Ankis eigene AGPL schlägt nicht durch.** `genanki` hängt nicht vom Paket `anki` ab und
übernimmt allein dessen Dateiformat, keinen Quelltext. Das Paket `anki` selbst bleibt
ausgeschlossen (dokumentation.md §4, „Zu Regel 15: die Rohquelle entscheidet").

### Das Ausschlusskriterium ist erfüllt

Entscheidung 8b verlangt eine zugängliche GUID, sonst ist Regel 6 nicht erfüllbar. Am
Quelltext geprüft: `Note.guid` ist eine Property mit Getter **und** Setter, dazu ein
Konstruktorparameter.

### Warum die Handvariante hier verliert — anders als bei E8a

Die abhängigkeitsfreie Gegenkandidatin wäre, die `.apkg`-Datei über SQLite und ZIP selbst zu
schreiben. Bei E8a (Abschnitt 8) hat genau diese Variante gewonnen. Der Unterschied ist
nicht Geschmack:

- E8a ist ein **Lesefall** in einem offen beschriebenen Format — was falsch gelesen wird,
  zeigt der Text
- E8b ist ein **Schreibfall** in eine fremde interne Datenbank, deren einziger Prüfer Ankis
  Importer ist

Dafür müsste die Handvariante 350 bis 450 Zeilen Konstanten übernehmen — entweder aus
`genanki` (MIT) oder aus Anki selbst (AGPL, nach Regel 15 ausgeschlossen). Die Lizenzlage
kehrt sich damit gegen sie: Der abhängigkeitsfreie Weg führt zur schlechteren Lizenz.

### Gegenrede: genanki wird kaum noch gepflegt

Letzte Freigabe 12.11.2023, letzter Commit 30.12.2024. Dagegen steht das Format selbst:
Ankis heutiger Importer nimmt `collection.anki2` weiterhin als `Legacy1` an — die
geschriebene Datei ist also nicht veraltet, nur die Bibliothek ruht.

### Befund: die vorgegebene GUID bindet den Feldinhalt

`genanki` bildet die GUID vorgabemäßig aus einem Hash **aller Feldwerte** der Notiz. Eine
korrigierte Übersetzung erzeugte damit eine neue GUID; Anki legte beim nächsten Import eine
zweite Notiz an, statt die bestehende zu aktualisieren. **Regel 6 wäre formal erfüllt** —
eine Spalte `guid` stünde in `card` — **und faktisch verletzt**, unbemerkt bis zum
Anki-Rückkanal in Phase 3.

> **Deshalb vergibt LibreVerbum die GUID selbst.** Schlüssel sind Buch, Kapitel, Grundform
> samt Wortart, Kartenrichtung sowie `wikdict_lexentry` und `wikdict_sense`. `translation`,
> `wikdict_trans_list` und `uncertain` bleiben draußen.

Der Preis ist bewusst in Kauf genommen: Ein neu bezogenes Wörterbuch mit geändertem
`sense`-Text erzeugt für dieselbe Bedeutung eine zweite Notiz. Die Doppelkarte ist sichtbar
und korrigierbar — der still überschriebene Lernfortschritt der Gegenseite wäre es nicht
(Abschnitt 4, „Jetzt billig, später teuer: die Anki-Kennung").

---

## 8c. Druckausgabe — entschieden

**Keine Bibliothek. Erzeugtes HTML mit eingebettetem Druck-CSS; gedruckt wird im Browser,
und wer ein PDF will, speichert es dort.**

Damit bleibt es bei der Standardbibliothek: keine Lizenzfrage, keine Systemabhängigkeit —
und kein Browser im Prüftor, weil das erzeugte HTML geprüft wird und nicht sein Ausdruck.

### Geprüft und verworfen

Am 21.08.2026 an den Rohquellen geprüft (Regel 15):

| Kandidat | Fassung | Lizenz | Warum nicht |
|---|---|---|---|
| weasyprint | 69.0 | BSD | verlangt unter Windows Pango über MSYS2 — eine Systembibliothek außerhalb von `uv.lock` und damit außerhalb der Messgrundlage aus Abschnitt 6; harte Abhängigkeit `Pyphen` tri-lizenziert |
| fpdf2 | 2.8.8 | LGPL-3.0-only | Kernschriften nur Latin-1 — die Schriftfalle greift genau bei den typografischen Zeichen aus dem Buchtext (dokumentation.md §8, „Kleinigkeiten") |
| reportlab | 5.0.1 | BSD | eine Werkbank für ein Blatt |
| Qts Druckweg | | | `printout` liegt im Kern, und der Kern kennt die Oberfläche nicht (Abschnitt 1, „Architekturregel — hält alle Türen offen") |

### Gemessene Ergebnisse: „passt auf ein Blatt" ist gedeckt

Gemessen am 21.08.2026 mit echter Arial-Metrik gegen alle 157.801 `trans_list`-Werte aus
`tools/en-de.sqlite3`, gerechnet gegen das Druck-CSS von `printout`:

| | |
|---|---|
| Satzspiegel | 180 × 267 mm, Spalte 85 mm |
| nutzbare Gesamtspaltenlänge | **491 mm** |
| je Eintrag | Zeilenhöhe 4,66 mm, dazu 4 mm Abstand |
| **zweites Blatt** | **ab durchschnittlich vier Zeilen je Eintrag** |
| 25 Einträge mit den jeweils längsten real vorkommenden Übersetzungen | **56 %** des Blattes |
| dieselben auf p99-Länge | **68 %** |

`trans_list`-Längen über den ganzen Bestand: Median 12 Zeichen, p90 32, p95 45, p99 76,
Maximum 199.

> **Damit trägt Abnahmekriterium 5 eine Messung.** Bis hierher war „passt auf ein Blatt"
> eine Ableitung aus der Wortobergrenze von 25 Wörtern (konzept.md, Schritt 4). Die Grenze
> trägt das Kriterium weiterhin — beurteilt wurde sie bei der Abnahme T17 (konzept.md,
> Schritt 4, Nachtrag 26.08.2026: sie bleibt bei 25).

### Eine direkte PDF-Ausgabe ist Phase 2

Ein PDF ohne den Handgriff im Browser verlangte eine der oben verworfenen Bibliotheken oder
einen mitgelieferten Browser. Gebaut wird, was die Phase verlangt (Regel 14); der Bedarf
selbst ist als Phase-2-Punkt festgehalten (konzept.md, „Phase 2 — Ausbau der Kernidee"),
mit dem HTML aus Phase 1 als Quelle.

### Offene Punkte

- **Die Gestaltung der Druckseite.** Funktional ist sie abgenommen (26.08.2026, Ausdruck
  geprüft, Abnahmekriterium 5 erfüllt), „könnte aber etwas schöner sein" — Gestaltung, nicht
  Kapazität. Bewusst zurückgestellt, bis eine erste vollständig funktionierende Fassung
  steht; die steht jetzt
- **Für die Kapazitätsprüfung fehlt ein Werkzeug in `tools/`.** Die Zahlen oben brauchen
  echte Schriftmetrik, und in `.venv/` liegt weder PIL noch `fontTools` — gerechnet hat sie
  ein Wegwerfskript, und **zwei Abnahmeläufe haben dafür je einen minimalen TrueType-Leser
  neu geschrieben**. Sie sind damit die einzigen Messwerte dieses Dokuments, die sich nicht
  aus `tools/` reproduzieren lassen, wogegen CLAUDE.md von den Messskripten ausdrücklich
  sagt, sie reproduzierten die Messungen, auf die sich technik.md stützt. Der dritte
  Anwendungsfall liegt damit vor, Regel 14 steht also nicht mehr entgegen: Die richtige
  Ablage wäre ein `tools/print_fit_check.py` derselben Bauart wie die übrigen Messskripte —
  Standardbibliothek, Schriftdatei aus dem System, Rechnung gegen das Druck-CSS von
  `printout`

---

## 9. Ablage und Konfiguration zur Laufzeit — entschieden

**Profil, Wörterbuch und Einstellungen liegen im plattformüblichen Nutzerverzeichnis. Der
Kern bekommt jeden Pfad als Argument; die Vorgabe setzt der Aufrufer. Einstellungen stehen
in `config.toml`, gelesen mit `tomllib` aus der Standardbibliothek.**

### Wohin die Dateien gehören

| Plattform | Verzeichnis |
|---|---|
| Windows | `%LOCALAPPDATA%\LibreVerbum\` |
| Linux | `$XDG_DATA_HOME/libreverbum/`, ersatzweise `~/.local/share/libreverbum/` |

Darin `profil.sqlite3`, `en-de.sqlite3` und `config.toml`. Das Profil ist laut konzept.md
der langfristige Wert des Programms und soll jedes Programmverzeichnis überleben; ein
Ordner neben dem Programm ist unter Windows nicht verlässlich beschreibbar, sobald es
einmal in `Program Files` liegt.

Die Trennung aus Abschnitt 4 bleibt unberührt: gemeinsames Verzeichnis, **getrennte
Dateien**.

### Der Kern kennt keine Vorgabe

> Jede Stelle des Kerns, die eine Datei braucht, bekommt den **Pfad als Argument**. Welches
> Verzeichnis vorgegeben ist, weiß nur der Aufrufer.

Das ist die Datei-Hälfte der Architekturregel aus Abschnitt 1 und zahlt zweifach: Tests
fassen nie das echte Profil an, sondern bekommen ein Wegwerfverzeichnis; und die
Oberfläche muss die Vorgabe später nicht beim Kern erfragen, sondern setzt ihre eigene.

### Einstellungen: `config.toml`

| Schlüssel | Zweck | Vorgabe |
|---|---|---|
| `model.url` | Adresse des Modellservers | `http://localhost:11434/v1` |
| `model.name` | Modellname | `gemma4:e4b` — die Empfehlung aus Abschnitt 3, Entscheidung 3 (Nachtrag 26.08.2026); leer lassen nimmt stattdessen das erste, das der Server nennt |
| `paths.dictionary`, `paths.profile` | abweichende Ablage | leer — dann das Verzeichnis oben |
| `triage.order` | Reihenfolge, in der `pipeline.resolve_triage_entries` Einträge vor der Triage auflöst (`"new_words_first"` oder `"frequency"`) — seit dem 25.08.2026, weil Regel 14 (dokumentation.md §4) einen zweiten Anwendungsfall verlangt und der vorliegt: Der Nutzer will die teilweise bekannten Wörter wahlweise gleichberechtigt neben den neuen sehen, statt sie grundsätzlich zurückzustellen. Gemessen am echten Server (`granite4.1:8b`, `sherlock.epub` Kapitel 2, 1410 Wort- und 212 Wendungseinträge, vier Durchläufe je Einstellung, wachsendes Profil, 25.08.2026): `new_words_first` 39 bis 44 Modellaufrufe je Kapitel (44 bis 64 s), `frequency` 39 bis 112 (21 bis 37 s). Bei 1410 Worteinträgen und `limit = 25` erreicht `new_words_first` die Gruppe der teilweise bekannten Einträge dabei praktisch nie — „neue Bedeutung eines bekannten Wortes" (konzept.md §5) erschien in den vier Läufen 0-mal, unter `frequency` 0-, 5-, 1- und 8-mal. Wer die Vorgabe belässt, schaltet den `bank`-Fall aus konzept.md §5 also faktisch ab | `new_words_first` |

Warum eine Datei und nicht bloß ein Aufrufargument: Der Modellserver dieses Projekts läuft
**nicht** auf `localhost`, sondern auf einer festen Adresse im Heimnetz. Eine Einstellung,
die bei jedem Aufruf zu wiederholen wäre, ist keine — das ist der zweite Anwendungsfall,
den Regel 14 verlangt, bevor ein Schalter entsteht. Die Autosuche aus `tools/` ist
ausdrücklich **nicht** das Vorbild: Sie findet diesen Server nicht und nähme im
Zweifelsfall stillschweigend einen anderen (Regel 13).

`tomllib` liest TOML seit Python 3.11 in der Standardbibliothek — keine neue Abhängigkeit.
Geschrieben wird die Datei nicht: Fehlt sie, legt der Aufrufer sie einmalig aus einer
Vorlage an und ändert sie danach der Nutzer von Hand. Damit bleibt es beim Lesen, wofür die
Standardbibliothek reicht.

**`reasoning_effort` steht nicht darin.** Regel 7 ist eine Regel, keine Einstellung — sie
gehört nach Abschnitt 7 in `translation` und nirgendwo sonst hin.

### Zwei Fallen beim Eintragen von Hand

**`model.url` trägt `/v1`, die Messskripte in `tools/` nicht.** In `config.toml` steht die
volle Adresse des OpenAI-Endpunkts (`http://…:11434/v1`), weil `translation` sie unverändert
verwendet; `tools/sense_check.py` und `tools/mwe_check.py` hängen `/v1` selbst an und
erwarten deshalb `--url http://…:11434`. Wer dieselbe Adresse von der einen Seite zur anderen
kopiert, bekommt HTTP 404 aus `…/v1/v1/chat/completions`.

**BOM und einfache Backslashes brechen `tomllib` mit einer englischen Meldung ab**, die die
Datei nicht nennt — nachgemessen am 26.08.2026:

| in `config.toml` | Meldung von `tomllib` |
|---|---|
| UTF-8-BOM am Dateianfang (Windows-Editoren erzeugen ihn) | `Invalid statement (at line 1, column 1)` |
| `dictionary = "C:\Users\…"` — einfacher Backslash | `Invalid hex value`, weil `\U` in TOML ein Escape ist |
| `dictionary = "C:\\Users\\…"` oder `'C:\Users\…'` | richtig gelesen |

Beide Meldungen zeigen auf eine Zeile, nicht auf die Datei, und stehen englisch zwischen
deutschen Ausgaben (dokumentation.md §1). Wer die Datei gerade von Hand angelegt hat, sucht
den Fehler deshalb zuerst woanders.

### Offene Punkte

- Ob Kartenrichtung und Wortobergrenze in die Datei gehören oder Aufrufargumente bleiben.
  Erst zu beantworten, wenn die Kommandozeile steht
- Der Menüpunkt für eine konsistente Sicherung (Abschnitt 4) braucht das Verzeichnis oben,
  ist aber selbst noch nicht gebaut
- **Ob ein Lesefehler in `config.toml` eine eigene deutsche Meldung samt Dateinamen
  bekommt** statt der `tomllib`-Meldung aus der Falle oben. Regel 13 ist erfüllt — es bricht
  laut ab —, die Sprachregel und der Hinweis auf die Datei sind es nicht
- **Die Eingabeprüfung der Kommandozeile fragt nicht überall nach.** Sie ist in Phase 1 die
  einzige Oberfläche, und zwei Stellen darin sind still:
  - Der Triage-Prompt lautet `[k]enne ich  [l]ernen  [s]kip  [q]uit >`, und `_ACTIONS` legt
    eine **Leereingabe als `skip`** aus. Eine Vorrichtung, die versehentlich leere Zeilen
    schickt, bucht dadurch nichts und der Lauf sieht trotzdem plausibel aus — **zwei
    Abnahmeläufe sind daran verlorengegangen**, bevor die Ursache feststand. Das ist der
    stille Fehlschlag aus Regel 13 an der Eingabe statt an der Ausgabe
  - Eine vertippte Antwort auf die Sammelaktionsfrage („1O" statt „10") überspringt die
    Sammelaktion **ganz**, statt nachzufragen; `_ask_action` daneben fragt bei ungültiger
    Eingabe erneut. Für den Nutzer bedeutet der Vertipper 25 Einzelfragen statt eines
    Tastendrucks — und beim ersten Durchlauf je Buch ist genau dieser Tastendruck der ganze
    Zweck (konzept.md, Schritt 4, Nachtrag 26.08.2026)

---

## Warum die Reihenfolge zwingend ist

Dieser Abschnitt gehört zu keiner einzelnen Entscheidung, sondern verbindet 1, 2 und 3.
Er hält fest, warum die Verarbeitungsschritte **nicht** vertauscht oder zusammengefasst
werden dürfen — das ist beim Bauen leicht zu vergessen und dann teuer.

### Das Wörterbuch kennt nur Grundformen

Geprüft an der WikDict-Datenbank:

| gesucht | vorhanden | | gesucht | vorhanden |
|---|---|---|---|---|
| `run` | ja | | `go` | ja |
| `ran` | **nein** | | `went` | **nein** |
| `mouse` | ja | | `child` | ja |
| `mice` | **nein** | | `children` | **nein** |
| `be` | ja | | `see` | ja |
| `was`, `were` | **nein** | | `seen` | **nein** |

Beugungsformen sind nicht enthalten. Das allein wäre harmlos — ein Fehlschlag beim
Nachschlagen ließe sich melden.

### Die Falle: es scheitert nicht laut, sondern leise

```
saw  →  (Noun) tool               →  Säge
        (Noun) saying or proverb  →  Sprichwort
        (Verb) cut with a saw     →  sägen
```

`saw` **steht** im Wörterbuch — nur als *Säge*, nicht als Vergangenheitsform von *see*.
Nachschlagen ohne vorherige Grundformbestimmung liefert hier keine Fehlermeldung,
sondern eine **falsche Übersetzung ohne jedes Anzeichen von Unsicherheit**. Im Test zu
Entscheidung 3 ist genau das eingetreten.

Der Nutzer kann den Fehler nicht bemerken — er kennt das Wort ja gerade nicht. Das ist
der Schaden, den das Konzept mit „Falsch gelernte Vokabeln sind schlimmer als gar
keine" beschreibt.

Gleiches gilt für `running`, `gone`, `better`, `runs`: alle im Wörterbuch, alle als
eigenständige Einträge mit eigener Bedeutung.

### Die verbindliche Reihenfolge

```
Rohtext
   │
   ├─ 1. Tokenisierung        "He saw the banks of the river."
   │                          → He | saw | the | banks | of | the | river
   │
   ├─ 2. Wortartbestimmung    saw = VERB  (nicht NOUN)
   │      ↑ ergibt sich erst aus dem Satzbau
   │
   ├─ 3. Lemmatisierung       saw  + VERB → see
   │                          banks + NOUN → bank
   │
   ├─ 4. Nachschlagen         bank → Bedeutungen mit engl. Kurzdefinition
   │
   └─ 5. LLM wählt aus        Belegsatz nennt "river"
                              → "edge of river or lake" → Ufer
```

Schritt 2 und 3 hängen zusammen: Die Grundform von `saw` ist *see* **oder** *saw*, je
nach Wortart — und die Wortart ergibt sich erst aus dem Satzzusammenhang. Deshalb
lässt sich das nicht durch eine Endungstabelle ersetzen. Das Skript
[`tools/coverage_check.py`](tools/coverage_check.py) versucht genau das und
scheitert nachweislich an `went`, `paid`, `heard`.

### Warum die Wortart trotzdem nicht genügt

Sie grenzt ein, entscheidet aber nicht:

```
lie  →  (Verb) be in horizontal position    →  liegen
        (Verb) tell an intentional untruth  →  lügen
```

Beide sind Verben. Nur der Belegsatz klärt den Fall. Daraus folgt die Arbeitsteilung
des Hybrid-Ansatzes:

| Stufe | beantwortet |
|---|---|
| **spaCy** | *Welches Wort ist das überhaupt?* — Form → Grundform + Wortart |
| **Wörterbuch** | *Welche Bedeutungen gibt es?* — die Liste der Möglichkeiten |
| **LLM** | *Welche gilt hier?* — Auswahl anhand des Belegsatzes |

Keine Stufe kann die Arbeit einer anderen übernehmen. Ein besseres Modell behebt einen
Lemmatisierungsfehler nicht, und ein größeres Wörterbuch auch nicht.

### Mehrwortausdrücke brauchen einen eigenen Weg

**54.903 der 124.751 Stichwörter (44 %) enthalten ein Leerzeichen** — Redewendungen,
Phrasal Verbs, feste Wendungen. Nachschlagen darf deshalb nicht Wort für Wort laufen,
sondern muss **Wortfolgen** prüfen.

Ungelöst ist dabei der auseinandergerissene Fall: `he gave the idea up` findet man
nicht, wenn nur zusammenhängende Folgen geprüft werden. Wie viel das ausmacht, ist
inzwischen gemessen — siehe nächster Abschnitt.

---

## Messung: Mehrwortausdrücke

Geprüft am 11.08.2026 mit [`tools/mwe_check.py`](tools/mwe_check.py) an
*The Adventures of Sherlock Holmes* (108.163 Wörter), Modell Qwen 3.5 9B.

Das Konzept nennt Redewendungen „die eigentliche Stärke des LLM-Ansatzes". Die Messung
bestätigt das **nur teilweise** und verschiebt die Arbeitsteilung deutlich.

### Finden: das Wörterbuch genügt, der Filter ist entscheidend

| | Vorkommen | verschiedene |
|---|---|---|
| n-Gramm-Abgleich roh | 6.202 | 1.209 |
| nach Filter | 2.958 | 659 |

Roh ist das Ergebnis unbrauchbar: `of the` (667×), `in the` (414×), `to the` (255×)
überdecken alles. Zwei Filter räumen das auf und **entfernen 52 % der Vorkommen**:

> **Filter:** `score ≥ 50` und Wortart nicht `Proper_noun`.

Die Schwelle trennt sauber, weil grammatisches Rauschen und echte Wendungen weit
auseinanderliegen:

| Ausdruck | score |
|---|---|
| `in the` | 2,0 |
| `of the` | 4,0 |
| `beat around the bush` | 102,5 |
| `give up` | 120,0 |
| `of course` | 128,6 |

Der Eigennamen-Ausschluss ist nötig, weil Eigennamen wie `New York` (`Proper_noun`,
score 163,6), `Great Britain` (210,0) oder `United States` (131,1) sonst als Lernvokabel
erschienen — gemessen an `tools/en-de.sqlite3`: 1.864 mehrwortige `Proper_noun`-Zeilen mit
`score ≥ 50`.

> **Nachtrag 18.08.2026 — falsches Beispiel `Sherlock Holmes`.** Hier stand zuvor,
> `Sherlock Holmes` stehe als `Proper_noun` im Wörterbuch und erschiene ohne den Filter
> 101× als Lernvokabel. Das ist falsch: `Sherlock Holmes` hat in `tools/en-de.sqlite3`
> genau eine Zeile, ohne `lexentry` (also ohne Wortart) und mit `score = 2,0` — der
> Eintrag fällt bereits an der Schwelle `score ≥ 50`, der `Proper_noun`-Filter kommt gar
> nicht zum Zug (Befund 6, Review T7). Festgehalten, weil die Behauptung plausibel klingt
> und sonst erneut als Beleg für den Filter angeführt würde; der Filter selbst bleibt
> richtig und nötig, nur das Beispiel trug nicht.

### Grenze: rund ein Fünftel der Phrasal Verbs steht getrennt

Gemessen am 12.08.2026 mit [`tools/nlp_check.py`](tools/nlp_check.py) über spaCys
Abhängigkeitsanalyse, an denselben zwei Romanen:

| | Sherlock Holmes | Dorian Gray |
|---|---|---|
| zusammenhängend (`gave up the idea`) | 391 | 238 |
| auseinandergerissen (`gave the idea up`) | 101 | 57 |
| **Anteil getrennt** | **21 %** | **19 %** |

Dem reinen n-Gramm-Abgleich entgeht dieses Fünftel vollständig. Der
Abhängigkeitsanalyse nicht: Sie findet `„work it out"`, `„shut the business up"`,
`„settling himself down"` samt Einschub.

> **Folgerung:** Phrasal Verbs brauchen spaCys Abhängigkeitsanalyse, nicht nur
> Wortfolgenabgleich. Mit Entscheidung 5 (Abschnitt 5) steht sie zur Verfügung, der
> Punkt ist damit erledigt.

> **Nachtrag 19.08.2026 — mit dem gebauten Code gegengemessen.** Die Anteile oben stammen
> aus `tools/nlp_check.py`. Der Code aus T4 zählt an denselben zwei Romanen **24 %**
> (Sherlock) und **22 %** (Dorian Gray) statt 21 % und 19 %. Die Überschrift trägt also
> weiterhin — der getrennte Anteil ist eher größer als kleiner geworden.

Offen bleibt ein anderer: **394 Vorkommen mit Partikel haben keinen
Wörterbucheintrag** — `take up`, `throw down`, `bring in`, `start off`. Sie gehören
nach Regel 10 als `uncertain` markiert, nicht verworfen.

> **Nachtrag 12.08.2026 — warum hier vorher 51 % stand.** Die erste Messung vom
> 11.08.2026 zählte 196 zusammenhängend gegen 205 getrennt und schloss auf „rund 51 %,
> etwa die Hälfte, nicht ein Randfall". Das war mehr als doppelt zu hoch. Ursache ist
> die Schwäche, die `mwe_check.py` an sich selbst schon vermerkt hatte: Es sucht Verb
> und Partikel ohne Wortartbestimmung im Satzzusammenhang und zählt Wortpaare mit, die
> gar kein Phrasal Verb bilden. Festgehalten, weil derselbe Fehler bei jedem künftigen
> Wortfolgen-Detektor genauso entstünde — eine Zahl aus einem Detektor ohne
> Wortartbestimmung ist eine Obergrenze, keine Messung.

### Das LLM darf Wendungen nicht frei suchen

Die aufschlussreichste Messung. Aufforderung an das Modell, die Redewendungen in einem
Textabschnitt zu **benennen** — also frei zu erzeugen statt auszuwählen:

| Ausgabe des Modells | Bewertung |
|---|---|
| `drop a line` | echte Wendung |
| `must be confessed`, `very possible`, `rather puzzled`, `looks exceedingly grave` | keine Wendungen, nur gewöhnliche Wortfolgen |
| `indeed the culprit`, `lock up in my strong box` | **stehen so nicht im Text** |
| `of considerably more value than if it were made of solid gold` | ganzer Nebensatz |

Von dreizehn genannten Ausdrücken waren zwei nicht wörtlich im Text und die Mehrzahl
keine Wendungen. **Freies Erzeugen holt die Halluzination zurück**, die der
Auswahlansatz bei Einzelwörtern gerade beseitigt hatte — aus demselben Grund: Es gibt
keine Liste, aus der gewählt wird.

> **Regel:** Dasselbe Prinzip wie bei der Bedeutungsauswahl gilt auch hier. Das
> Wörterbuch liefert die Kandidaten, das Modell **beurteilt** sie. Es sucht sie nicht.

### Beurteilen statt erzeugen — besser, aber kein Ersatz für die Triage

Gegenprobe mit 16 vorgelegten Kandidaten: „lernenswert oder trivial?" Ergebnis in
**12 Sekunden für alle 16 in einer einzigen Anfrage**, jeder Eintrag echt, keine
Erfindungen.

Die Urteile selbst sind aber nur mittelmäßig:

| Urteil des Modells | |
|---|---|
| richtig | `the man`, `there is`, `to go` → trivial · `beat around the bush`, `give up`, `out of the way`, `at last` → lernenswert |
| **falsch** | `so that` → lernenswert (schlichte Grammatik) |
| strittig | `of course`, `at once`, `no doubt` → trivial · `a few`, `very much` → lernenswert |

Das ist weniger ein Modellversagen als eine **schlecht gestellte Frage**: Ob ein
Ausdruck lernenswert ist, hängt vom Kenntnisstand des Lesers ab — und dafür sieht das
Konzept bereits ein Verfahren vor, nämlich die **Triage durch den Nutzer**.

> **Folgerung:** Das Modell entscheidet nicht über Lernwürdigkeit. Kandidaten kommen
> gefiltert aus dem Wörterbuch, die Auswahl trifft der Nutzer in der Triage —
> unterstützt durch Häufigkeitssortierung und Sammelaktion, die das Konzept ohnehin
> vorsieht.

### Nachtrag 19.08.2026: die Maße beider Wege

Die Arbeitsteilung unten ist inzwischen mit Zahlen unterlegt. Gemessen beim Bau von T4 am
17.08.2026, die Wörterbuchzahlen am 19.08.2026 gegen `tools/en-de.sqlite3` nachgeprüft;
„mehrwortig" heißt dabei: `written_rep` enthält ein Leerzeichen.

**Wie lang eine Wendung höchstens wird.** 21.145 mehrwortige Stichwörter erreichen
`score ≥ 50`, und davon sind **99,07 % höchstens sechs Wörter lang** — 2 Wörter: 16.754 ·
3: 2.788 · 4: 960 · 5: 281 · 6: 165. Darüber stehen fast nur noch vollständige
`Proverb`-Zeilen bis 26 Wörter, die als Zitat im Fließtext praktisch nicht vorkommen. Daraus
die **Obergrenze sechs**, die im n-Gramm-Weg steht.

**Wie klein der `prt`-Weg gegen den n-Gramm-Weg ist.** Nach dem vollen Filter (`score ≥ 50`
und nicht `Proper_noun`) bleiben 19.325 mehrwortige Stichwörter. Die zweiwortigen
Verb-Stichwörter darunter — die Obergrenze dessen, was ein Verb-Partikel-Weg überhaupt
treffen kann — sind 1.026, also **rund 5 %**; mit einer echten Partikelliste blieben beim
Bau von T4 davon 652 übrig, **3,4 %**. Das ist die Zahl, die die Arbeitsteilung belegt: Ohne
den n-Gramm-Weg fehlen nicht Randfälle, sondern der Bestand. An `tools/sherlock.txt` (ein
Kapitel, 60.000 Zeichen) sind es 232 zusammenhängende Wörterbuch-Wendungen, davon 40 aus den
eigenen Wendungs-Wortarten `Phrase` (691 Zeilen), `Prepositional_phrase` (638) und `Proverb`
(309) — `as a rule`, `at all`, `after all`, `out of the way`, `all right`.

**Wie viele Kandidaten je Kapitel anfallen** (echter Lauf über 60.000 Zeichen aus
`tools/sherlock.txt`): zusammenhängend **23.437 verschiedene** Kandidaten (26.984
Vorkommen), getrennt **77 verschiedene** (93 Vorkommen). Die n-Gramm-Seite bringt also rund
**300-mal so viele** Nachschlagevorgänge wie die `prt`-Seite. Wie T7 damit umgeht, ist dort
entschieden und gemessen: Einzelabfragen über **eine geteilte Verbindung**, 14,3 s je
eigener Verbindung gegen 1,7 s geteilt (`dictionary._lookup_matches`, Befund 5 Review T7).
Ein Bündelmechanismus war dafür nicht nötig.

Ein Nebenbefund derselben Messung ist in T7 eingegangen: Der Filter `score ≥ 50` löscht 86
der 232 Sherlock-Treffer, darunter `bring back` (10 Vorkommen), `take up`, `keep out` und
`light up` — also genau die Einträge, die unten als „394 Vorkommen mit Partikel" nach
Regel 10 `uncertain` bleiben sollen. Der Filter gehört deshalb zum n-Gramm-Weg, nicht zum
`prt`-Weg; T7 behandelt die beiden Kandidatenarten seither getrennt.

### Bekannte Grenze: Wortstellungsvarianten belegen zwei Plätze

Aus der bestandenen Abnahme vom 26.08.2026, festgehalten als Grenze und **bewusst nicht
behoben**: `There was` und `Was there` sind für die Kandidatenbildung zwei verschiedene
Wendungen und belegen zwei der wenigen Wendungsplätze der Triage; gemessen sind **27 solcher
Paare** über die beiden EPUBs unter `tools/`. Entdoppelt wird über die **Wortfolge** — das
fängt die echten Dubletten („clear up", „look up") samt Präfixpaaren. Eine Entdopplung, die
zusätzlich über die Wortmenge ginge, führe zu weit: In `dorian_gray.epub` Kapitel 17 fielen
darunter „there is no pleasure" und „was to be there" zusammen, und damit eine echte
Bedeutung weg. Zwei Plätze für eine Wortstellungsvariante sind der billigere Fehler.

### Arbeitsteilung nach der Messung

| Aufgabe | zuständig | Stand |
|---|---|---|
| zusammenhängende Wendungen finden | Wörterbuch + n-Gramm + Filter | **gemessen, funktioniert** |
| getrennte Phrasal Verbs finden | spaCy-Abhängigkeitsanalyse | **gemessen, funktioniert** — betrifft 21 % |
| Bedeutung im Kontext wählen | LLM, Auswahl aus Liste | **gemessen, 11/11** |
| Lernwürdigkeit entscheiden | **Nutzer**, nicht Modell | Konzept sieht es vor |
| Wendungen ohne Wörterbucheintrag | LLM, frei erzeugend | **unzuverlässig** — nur mit Markierung „unsicher" verwenden |

Die letzte Zeile ist die eigentliche Korrektur am Konzept: Wendungen, die kein
Wörterbuch führt, „bleiben dem LLM allein überlassen — dort ist es unersetzlich".
Unersetzlich ist es dort weiterhin, aber nicht verlässlich. Solche Einträge gehören
markiert, wie es das Konzept für unsichere Fälle ohnehin vorsieht.
