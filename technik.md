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

Frage 5 stand anfangs nicht auf der Liste. Sie ist aus Frage 2 entstanden, deren Messung
mit der Folgerung endete, nicht die Datenquelle sei der Engpass, sondern die
Lemmatisierung — siehe Abschnitt 5.

Frage 6 ist von anderer Art als 1 bis 5: keine inhaltliche Vorfrage, sondern das Gerüst,
in dem gebaut wird. Sie kommt zuletzt, weil sie erst beantwortbar war, als die
Abhängigkeiten feststanden — und sie kommt überhaupt, weil der Code zum großen Teil
maschinell entsteht. Siehe Abschnitt 6.

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
- Konkrete Bibliotheken für EPUB, Anki-Export und Druckausgabe, jeweils **samt
  Lizenzprüfung**
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
- Prüfsumme gegen beschädigte Downloads

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

**Qwen 3.5 9B über Ollama, angesprochen über die OpenAI-kompatible Schnittstelle.
Denkschritt abgeschaltet. Antwortform per JSON-Schema erzwungen.**

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
Übersetzungsdauer eines Kapitels im Bereich **einer halben Minute**. Geschwindigkeit
ist damit kein Entscheidungskriterium mehr.

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

- **Ausweichantwort „keine passt"** in die Auswahlliste aufnehmen. Der `saw`-Fall zeigt,
  dass das Modell sonst kein Mittel hat, einen Fehler der Vorstufe zu melden. Mit dieser
  Möglichkeit wird aus einem stillen Fehler ein markierter Eintrag — das Konzept sieht
  Markierung bei Unsicherheit ohnehin vor
- **Sehr lange Auswahllisten**: `run` hat 48 Bedeutungen, `draw` 16, `light` 14. Ob das
  die Trefferquote drückt, ist noch nicht gemessen. Naheliegende Abhilfe: nach der von
  spaCy bestimmten Wortart vorfiltern, das halbiert die Liste oft
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
                      Häufigkeit)           dem Wörterbuch,
                                            eigene Korrektur)
                                                │
                         event ─────────────────┤   Verlauf: kennt / lernt /
                                                │   zurückgestellt / vergessen
                                                │   + Herkunft + Zeitpunkt
                         card ──────────────────┘   Anki-Kennung für den Rückkanal
```

| Tabelle | Zweck |
|---|---|
| `lemma` | Grundform + Wortart. Die Klammer, nicht die Kenntniseinheit |
| `sense` | Eine Bedeutung eines Lemmas. Trägt die Wörterbuch-Momentaufnahme und die eigene Korrektur |
| `event` | Der Verlauf. Art, Herkunft, Zeitpunkt, Bezug auf Buch/Kapitel |
| `occurrence` | Belegsatz und Häufigkeit je Kapitel — dasselbe Wort hat in Kapitel 2 einen anderen Belegsatz als in Kapitel 9 |
| `book`, `chapter` | Was bereits verarbeitet wurde |
| `card` | Exportierte Anki-Karten samt deren Kennung |

Die Namen sind englisch, die Prosa bleibt deutsch — Zuordnung und Begründung in
[dokumentation.md](dokumentation.md), Abschnitt 1.

> **Achtung, zwei Dinge namens `sense`:** Die eigene Tabelle ist die **Bedeutung als
> Gegenstand** — mit Verlauf, eigener Korrektur und Kartenbezug. WikDicts `sense` ist
> dagegen nur der **englische Kurztext**. Er wird als `wikdict_sense` mitgeführt. Das
> Präfix `wikdict_` markiert alle Momentaufnahmen aus der Fremdquelle und hält damit die
> Regel „keine Fremdschlüssel ins Wörterbuch" beim Abfragen sichtbar.

Der aktuelle Kenntnisstand ist eine **Sicht** auf die Ereignistabelle (jeweils
jüngstes Ereignis je Bedeutung), keine eigene Tabelle. Bei der zu erwartenden Größe —
Zehntausende Ereignisse — ist das für SQLite unproblematisch. Eine
materialisierte Zwischentabelle wäre verfrühte Optimierung.

### Jetzt billig, später teuer: die Anki-Kennung

> Beim Export jeder Karte wird deren **Anki-GUID** in `card` mitgespeichert.

Das kostet heute eine Spalte. Ohne sie lässt sich der Anki-Rückkanal aus Phase 3
später nicht anschließen, ohne alle bereits exportierten Decks neu zu erzeugen — was
beim Nutzer den Lernfortschritt in Anki zurücksetzen würde. Ein Fall, in dem eine
Fünf-Minuten-Entscheidung jetzt einen unreparierbaren Zustand später verhindert.

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

- Genaue Spalten und Datentypen — beim Bau festzulegen, nicht vorab
- Ob Eigennamen („Figuren & Orte") als `lemma` mit Wortart *Eigenname* geführt werden
  oder in einer eigenen Tabelle. Ersteres ist einfacher und vermutlich ausreichend
- Wie Mehrwortausdrücke als `lemma` dargestellt werden — dieselbe Tabelle mit
  Leerzeichen im Text, oder eine eigene Kennzeichnung
- Umgang mit gleichzeitigem Zugriff, falls später eine Weboberfläche hinzukommt
  (siehe Architekturregel in Abschnitt 1)

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

### Offene Punkte

- **`could`, `would`, `having`** und die übrigen Hilfsverbformen sollten vor dem
  Nachschlagen ausgesteuert werden, statt als Wörterbuchlücke zu erscheinen. Wortart
  `AUX` genügt dafür vermutlich
- Über-Lemmatisierung von Eigennamen (`Holmes` → `holme`) — harmlos, solange der Filter
  aus dem vorigen Abschnitt greift, aber beim Anlegen der Liste „Figuren & Orte" zu
  beachten
- Ob die Wortart als Vorfilter für lange Auswahllisten taugt (Abschnitt 3, `run` mit 48
  Bedeutungen) — die Wortart liegt jetzt vor, gemessen ist die Wirkung noch nicht

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
- **Ob `mypy --strict` trägt**, sobald spaCy-Typen im Spiel sind. Bisher sind nur eigene,
  triviale Dateien geprüft. `tools/` ist von der Typprüfung ausgenommen — Messskripte,
  reine Standardbibliothek
- **Auslieferung** (Nuitka, PyInstaller) bleibt offen wie in Abschnitt 1; sie berührt das
  Gerüst erst, wenn das Programm an Fremde geht

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

Der Eigennamen-Ausschluss ist nötig, weil `Sherlock Holmes` als `Proper_noun` im
Wörterbuch steht und sonst 101× als Lernvokabel erschiene.

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
