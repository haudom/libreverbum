# LibreVerbum — Produktkonzept

> Stand: 11.08.2026 · Phase: Konzeption. Die technische Umsetzung
> (Programmiersprache, Bibliotheken, Bedienoberfläche, Modellwahl) ist bewusst
> noch **nicht** entschieden und wird separat besprochen.

## Kontext

Wer ein englisches Buch im Original liest, ohne den Wortschatz dafür zu haben, wird ständig
aus dem Lesefluss gerissen: nachschlagen, Faden verlieren, weiterlesen, wieder nachschlagen.
Bestehende Werkzeuge (Kindle-Wörterbuch, Übersetzer-Apps) setzen alle **beim** Lesen an und
verstärken damit genau diese Unterbrechung.

LibreVerbum dreht die Reihenfolge um: Die Vokabeln eines Kapitels werden **vorher** gelernt.
Danach lässt sich das Kapitel am Stück lesen — im Idealfall ganz ohne Hilfsmittel, auf Papier,
offline.

Der zweite Kerngedanke ist ein **mitwachsendes Nutzerprofil**: Das Programm merkt sich, welche
Wörter der Nutzer bereits kennt, und fragt sie nie wieder ab. Über mehrere Bücher hinweg wird
die Vorbereitung dadurch immer kürzer, obwohl die Bücher schwerer werden dürfen.

---

## Getroffene Entscheidungen

| Thema | Entscheidung |
|---|---|
| Sprachrichtung | Englisch → Deutsch zuerst, aber als **austauschbare Konfiguration** gebaut, nicht fest verdrahtet |
| Übersetzung | **Hybrid**: Offline-Wörterbuch liefert Bedeutungen, lokales LLM wählt kontextabhängig aus. Cloud-KI optional zuschaltbar |
| Bekannt-Liste | Startet mit **einfachem Durchklicken**; Bootstrapping-Verfahren (adaptiver Test, Anki-Import, Niveau-Angabe) als spätere Erweiterung vorgesehen |
| Kartenrichtung | **Pro Export wählbar** (EN→DE, DE→EN, Lückentext) |
| Bildmodus | **Erst englische Comics**, japanische Manga als eigener späterer Block |
| Erste Version | **Kompletter Durchlauf für ein Kapitel** — schmal, aber Ende-zu-Ende nutzbar |
| Oberfläche | **Desktop-Anwendung** für Windows und Linux — Einzelheiten in [technik.md](technik.md) |

---

## Der Kernablauf

```
EPUB einlesen  →  Kapitel wählen  →  Wortschatz extrahieren
      →  gegen Profil filtern  →  Bedeutungen beschaffen (Wörterbuch + LLM)
      →  Triage durch Nutzer  →  Export (Anki / Druck)
```

> **Nachtrag 17.08.2026 — die Triage kommt nach dem Beschaffen der Bedeutungen.** Bis heute
> stand hier `Triage → Übersetzen`. Das widersprach dem eigenen Abschnitt 5,
> „Mehrdeutigkeit": Dort wird der zweite Eintrag eines mehrdeutigen Wortes **in der Triage**
> als „neue Bedeutung eines bekannten Wortes" gekennzeichnet — was voraussetzt, dass die
> Bedeutung dort bereits feststeht. Der Widerspruch fiel beim Bau von T10 auf, wo eine
> Triage-Entscheidung mangels Bedeutung keinen Gegenstand hatte, an dem das Profil sie
> festmachen konnte (technik.md §4, „Kenntnis pro Bedeutung, nicht pro Wort").
>
> Ausschlaggebend ist aber nicht die Datenhaltung, sondern der Nutzerfall: Wer `watch` ohne
> Bedeutungsangabe sieht, drückt „kenne ich" für die Uhr, während der Text die Wache meint —
> und lernt das Wort nie. Der Belegsatz allein trägt das nicht; in einer zügigen Triage wird
> er überflogen.
>
> **Die Abschnittsnummern bleiben**, damit die Verweise aus technik.md gültig bleiben.
> Geändert hat sich die Reihenfolge, nicht die Sache: Abschnitt 5 beschreibt weiterhin
> denselben Hybrid, er läuft nur früher.
>
> **Nachtrag 18.08.2026 — Folge für „Gegen das Profil filtern".** Der Abgleich gegen das
> Profil (technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort")
> vergleicht auf Ebene der Bedeutung, nicht der Grundform — sonst könnte er „neue Bedeutung
> eines bekannten Wortes" gar nicht erkennen. Er setzt damit bereits aufgelöste Bedeutungen
> voraus und läuft folglich **nach** „Bedeutungen beschaffen", nicht davor, wie es das
> Diagramm oben suggeriert. Das ist mit dem Nachtrag vom 17.08.2026 verträglich (die
> Bedeutungen stehen ohnehin vor der Triage fest) und wurde bei dessen Formulierung nicht
> ausgesprochen; festgehalten bei T9 (bauplan.md), Befund 5, Review T9, damit T15 die
> Reihenfolge nicht neu entscheidet.

### 1. Buch einlesen
EPUB öffnen, Metadaten (Titel, Autor) und die Kapitelstruktur auslesen. Fließtext von
Inhaltsverzeichnis, Impressum, Widmung und Fußnoten trennen. Fehlt der Datei eine
Kapitelstruktur, tritt die Lesereihenfolge an ihre Stelle — mit sichtbarem Hinweis.

*Nur DRM-freie Dateien.* Kopierschutz wird nicht umgangen.

> **Nachtrag 12.08.2026 aus der Messung:** Dass ein EPUB seine Kapitel kennt, ist eine
> Annahme, keine Eigenschaft des Formats. Von acht geprüften Büchern enthält eines weder
> Inhaltsverzeichnis noch Überschriften — ein Konvertat, dessen Text in vier Blöcken zu je
> 30.000 Wörtern liegt. Festgehalten, weil der naheliegende Rückfall auf Überschriften
> ebenfalls gemessen und verworfen wurde: Jede Datei, die Überschriften hat, hat auch ein
> Inhaltsverzeichnis. Einzelheiten in [technik.md](technik.md) §8, „Neuer Befund: manchen
> Dateien fehlen die Kapitelgrenzen ganz".

### 2. Wortschatz extrahieren
Der wichtigste und unterschätzteste Schritt. Aus dem Rohtext entsteht eine saubere Wortliste:

- **Lemmatisierung**: `running`, `ran`, `runs` → **ein** Eintrag `run`. Ebenso `mice → mouse`.
  Ohne diesen Schritt ist die Liste unbrauchbar und das Profil lernt nie richtig.
- **Eigennamen aussortieren**: Figuren- und Ortsnamen dominieren sonst jede Häufigkeitsliste.
  Sie landen in einer **separaten Liste „Figuren & Orte"** — für den Leser nützlich, aber
  keine Lernvokabeln.
- **Mehrwortausdrücke erkennen**: Redewendungen (`beat around the bush`), Phrasal Verbs
  (`give up`), feste Wendungen. Diese sind die eigentliche Stärke des LLM-Ansatzes, weil ein
  Wörterbuch sie im Fließtext nicht findet.
- **Häufigkeit zählen** — pro Kapitel und fürs ganze Buch.
- **Belegsatz merken**: zu jedem Wort der Originalsatz aus dem Buch, in dem es vorkommt.

### 3. Gegen das Profil filtern
Alles, was im Profil als *bekannt* markiert ist, fällt raus. Beim ersten Buch ist das Profil
leer — deshalb muss Schritt 4 auch bei großen Listen erträglich bleiben.

### 4. Triage durch den Nutzer
Die verbleibenden Wörter werden durchgegangen, jeweils mit Belegsatz **und Bedeutung** als
Kontexthilfe. Drei Antworten:

- **Kenne ich** → wandert dauerhaft ins Profil, wird nie wieder gefragt
- **Will ich lernen** → wird übersetzt und zur Karte
- **Überspringen** → diesmal nicht, aber beim nächsten Mal wieder fragen

Die Liste wird **nach Häufigkeit sortiert** präsentiert, häufigste zuerst. So sind die
wichtigsten Entscheidungen früh gefallen, und man kann jederzeit abbrechen, ohne das Wichtigste
zu verpassen.

**Zwei Erleichterungen von Anfang an**, weil das der kritische Punkt für die Nutzbarkeit ist:
- **Sammelaktion „ab hier kenne ich alles"** — markiert alle häufigeren Wörter auf einen Schlag
- **Obergrenze pro Kapitel** — „maximal 25 neue Wörter", der Rest wird zurückgestellt

> **Nachtrag 26.08.2026 — die Obergrenze bleibt bei 25.** Beurteilt werden sollte sie beim
> ersten echten Durchlauf; der hat gezeigt, dass nicht die Zahl das Problem ist, sondern der
> Anfangszustand des Profils: **Der erste Durchlauf je Buch ist ein Kalibrier-, kein
> Lerndurchlauf.** Bei leerem Profil sind die 25 häufigsten unbekannten Grundformen
> ausnahmslos A1/A2-Wortschatz (`life`, `had`, `said`, `made`); erst nach einer Sammelaktion
> erscheinen `portrait`, `tragedy`, `dreadful`, `lad`, `afraid`. Eine höhere Grenze
> verlängerte nur diesen Kalibrierdurchlauf — was ihn abkürzt, ist ein Tastendruck und die
> Vorbelegung des Grundwortschatzes („Bewusst offen" unten).

**In der Triage steht die gemeinte Bedeutung**, nicht bloß die Liste der möglichen. Sie wird
dafür **vor** der Triage aufgelöst, und „kenne ich" bucht auf sie — Kenntnis wird pro
Bedeutung geführt ([technik.md](technik.md) §4, „Kernentscheidung: Kenntnis pro Bedeutung,
nicht pro Wort"). Das kostet einen Modellaufruf je gezeigtem Eintrag und ist trotzdem nicht
verhandelbar: Zwei Drittel der Grundformen eines Kapitels sind mehrdeutig
([technik.md](technik.md) §3, „Nachtrag 18.08.2026: zwei Drittel der Grundformen eines
Kapitels sind mehrdeutig"), und wer `watch` ohne Bedeutungsangabe sieht, drückt „kenne ich"
für die Uhr, während der Text die Wache meint.

> **Nachtrag 26.08.2026 — hier stand eine Einstellung für die Anreicherungstiefe.** Am
> 17.08.2026 waren zwei Stellungen vorgesehen: „Wörterbuch" (rund 1,1 s je Kapitel, kein
> Modellaufruf, in der Triage die Liste der möglichen Bedeutungen) und „Wörterbuch + Modell"
> (zusätzlich die im Kontext gemeinte markiert), Standard die erste. Der Umbau vom
> 25.08.2026 hat die erste Stellung ersatzlos gestrichen: Sie zeigt eine Liste statt einer
> Bedeutung, und die Triage-Entscheidung hätte dann keinen Gegenstand, auf den sie buchen
> kann. Festgehalten, weil die Kostenrechnung der ersten Stellung einleuchtet und sie sonst
> erneut vorgeschlagen wird — gemessen sind die Kosten inzwischen klein: rund 0,48 s je Wort
> bei höchstens 25 Wörtern ([technik.md](technik.md) §3, „Nachtrag 26.08.2026"). Die beiden
> Fragen, die hier offen standen, sind damit beantwortet: Mehrdeutigkeit ist der Normalfall
> (65,8 %), und **Bündeln** lohnt nicht ([technik.md](technik.md) §3, „Nachtrag 19.08.2026:
> Bündeln lohnt nicht").

*Später erweiterbar durch:* adaptiven Vokabeltest zur Erstschätzung, Import bestehender
Anki-Decks, Angabe des Sprachniveaus (A1–C2). Die Datenstruktur muss diese Quellen aufnehmen
können, ohne umgebaut zu werden.

### 5. Übersetzen — der Hybrid-Ansatz

> Seit 17.08.2026 läuft dieser Schritt **vor** Abschnitt 4, damit die Triage die Bedeutung
> anzeigen kann; siehe den Nachtrag beim Kernablauf. Die Nummer bleibt, die Sache auch.

Ein rein generatives Modell erfindet gelegentlich Übersetzungen, und der Nutzer bemerkt es
nicht — er kennt das Wort ja gerade nicht. Falsch gelernte Vokabeln sind schlimmer als gar
keine. Deshalb zweistufig:

1. **Offline-Wörterbuch** liefert die tatsächlich existierenden Bedeutungen eines Worts
2. **LLM** wählt anhand des Belegsatzes die **im Kontext passende** aus, formuliert die
   Kurzübersetzung und ergänzt Wortart und ggf. Anmerkungen

Das Modell **entscheidet**, statt zu **erfinden**. Redewendungen und Wendungen, die kein
Wörterbuch führt, bleiben dem LLM allein überlassen — dort ist es unersetzlich.

> **Nachtrag 11.08.2026 aus der Messung:** Das gilt eingeschränkt. Lässt man das Modell
> Wendungen *frei benennen*, erfindet es — es nannte Ausdrücke, die im Text gar nicht
> vorkommen. Wendungen ohne Wörterbucheintrag sind deshalb stets als *unsicher* zu
> markieren. Einzelheiten in [technik.md](technik.md), Abschnitt „Messung:
> Mehrwortausdrücke".

Findet das Wörterbuch nichts oder ist das Modell unsicher, wird der Eintrag **markiert** statt
still durchgereicht. Der Nutzer kann jede Übersetzung korrigieren; Korrekturen werden gespeichert
und künftig bevorzugt.

**Cloud-KI optional**: Dieselbe Schnittstelle, andere Gegenstelle. Standard bleibt vollständig
offline; wer bessere Qualität will, schaltet sie bewusst zu. Hinweis dabei: Die Buchtexte
verlassen dann den Rechner.

**Mehrdeutigkeit**: Taucht `bank` in Kapitel 2 als Geldinstitut und in Kapitel 9 als Flussufer
auf, entstehen **zwei Einträge**. Der zweite wird in der Triage als *„neue Bedeutung eines
bekannten Wortes"* gekennzeichnet, damit der Nutzer versteht, warum ein scheinbar bekanntes Wort
noch einmal auftaucht.

### 6. Export

**Anki-Deck** — direkt importierbare Datei, keine Bastelei mit CSV-Spalten.
Kartentypen **pro Export wählbar**:
- EN → DE (Erkennen — für das Leseziel der Regelfall)
- DE → EN (Produzieren)
- Lückentext mit dem Originalsatz aus dem Buch

Jede Karte trägt: Wort, Grundform, Übersetzung, Wortart, Belegsatz, Buch, Kapitel.
Verschlagwortung nach Buch, Autor und Kapitel, damit sich in Anki später sauber filtern lässt.

**Druckausgabe** — für das Lesen ohne jedes Gerät:
- **Kapitelliste** als Blatt, zweispaltig, in Reihenfolge des Vorkommens oder alphabetisch
- **Lesezeichen-Format**: schmaler Streifen im Buchformat mit den Vokabeln des aktuellen
  Kapitels, der physisch im Buch liegt — genau dort, wo er gebraucht wird
- Optionaler Anhang **„Figuren & Orte"** aus den aussortierten Eigennamen

Die Kapitelliste trägt je Zeile **Wortform, Wortart und Übersetzung** (Wendungen haben keine
Einzelwortart und bekommen keine), Buch und Kapitel stehen als Überschrift darüber. Die
Wortart ist dort kein Beiwerk, sondern der Grund, warum die Felder hier ebenso benannt sind
wie die der Karte: Zwei Drittel der Grundformen eines Kapitels sind mehrdeutig
([technik.md](technik.md) §3, „Nachtrag 18.08.2026: zwei Drittel der Grundformen eines
Kapitels sind mehrdeutig"), und wer auf dem Blatt eine Grundform ohne Wortart liest, hängt die
Übersetzung an die falsche Lesart — der stille Fehler, gegen den Abschnitt 5 gebaut ist, und
bemerken kann der Leser ihn nicht. Belegsatz und Verschlagwortung bleiben dagegen der Karte
vorbehalten: Auf das Blatt kommt, was in eine 85-mm-Spalte passt
([technik.md](technik.md) §8c).

---

## Was das Profil speichert

Konzeptionell, unabhängig von der späteren Technik:

- **Bekannte Wörter** — auf Ebene der Grundform, mit Herkunft der Information (selbst markiert,
  importiert, geschätzt) und Zeitpunkt
- **Lernwörter** — aktuell in Arbeit, mit Buch- und Kapitelbezug
- **Zurückgestellte Wörter** — übersprungen, werden erneut gefragt
- **Eigene Korrekturen** an Übersetzungen
- **Bücher und Kapitel**, die bereits verarbeitet wurden

Das Profil ist **buchübergreifend** und der eigentliche langfristige Wert des Programms. Es muss
exportierbar und sicherbar sein.

---

## Phasenplan

### Phase 1 — Erste nutzbare Version
Ein vollständiger Durchlauf für **ein Kapitel**: EPUB einlesen → Kapitel wählen → Wortschatz mit
Lemmatisierung und Eigennamenfilter extrahieren → Triage mit Häufigkeitssortierung und
Sammelaktion → Hybrid-Übersetzung → Anki-Deck **und** Druckseite.

Fertig, wenn ein echtes Buch von Anfang bis Ende durchläuft und das erzeugte Deck in Anki
importierbar ist.

### Phase 2 — Ausbau der Kernidee
- **Ganzes Buch auf einmal** verarbeiten, Kapitel einzeln oder in Blöcken
- **Abdeckungsanzeige**: „Lerne diese 34 Wörter und du verstehst 97 % von Kapitel 3." Rechnerisch
  einfach, weil alle Häufigkeiten vorliegen — und psychologisch das stärkste Motivationsmittel
  im ganzen Konzept
- **Buch-Schwierigkeitscheck**: ganzes Buch gegen das Profil halten → „ca. 14 unbekannte Wörter
  pro Seite, zu schwer für dich". Eigenständig nützlich, auch als Entscheidungshilfe vor dem Kauf
- **Lesezeichen-Druck** und weitere Druckvarianten, dazu die **PDF-Ausgabe ohne den Umweg
  über den Browser**, mit der Druckseite aus Phase 1 als Quelle — siehe
  [technik.md](technik.md) §8c, „Eine direkte PDF-Ausgabe ist Phase 2"
- Bootstrapping der Bekannt-Liste: adaptiver Vokabeltest, Import bestehender Anki-Decks,
  Niveau-Angabe

### Phase 3 — Rückkanal und weitere Quellen
- **Anki-Rückkanal**: Karten, die dauerhaft falsch beantwortet werden, wandern im Profil zurück
  auf *unbekannt* und tauchen im nächsten Buch wieder auf. Das Profil lernt damit in **beide**
  Richtungen
- **Lesetempo-Planung**: „ein Kapitel pro Tag ab Montag" → Karten werden so terminiert, dass die
  Vokabeln jeweils **vor** dem passenden Kapitel fällig sind
- **Weitere Eingabeformate**: Untertiteldateien (.srt) für Serien — mit Abstand am einfachsten zu
  verarbeiten und bei Lernenden sehr beliebt. Dazu Kindles Nachschlage-Datenbank als
  Startbestand für „das kenne ich noch nicht", sowie PDF und reiner Text
- **Weitere Sprachpaare** aktivieren

### Phase 4 — Bildmodus
- **Englische Comics und Graphic Novels**: Sprechblasen finden, Text auslesen, in dieselbe
  Pipeline geben. Handlettering und durchgehende Großschreibung sind die Hauptschwierigkeiten
- **Japanische Manga**: bewusst abgetrennt. Vertikaler Text, Furigana, keine Wortgrenzen und eine
  völlig andere Sprachrichtung machen daraus faktisch ein eigenes Projekt mit eigenen
  Spezialmodellen

---

## Bewusst offen (später separat zu entscheiden)

- ~~Bedienoberfläche, Programmiersprache und Bibliotheken~~ — **entschieden am 11.08.2026**,
  siehe [technik.md](technik.md)
- ~~Herkunft der Wörterbuch- und Häufigkeitsdaten samt deren Lizenzlage~~ — **entschieden
  am 11.08.2026**, siehe [technik.md](technik.md)
- ~~Wahl des lokalen Modells und dessen Betriebsart~~ — **entschieden am 11.08.2026**,
  siehe [technik.md](technik.md)
- ~~Ablage des Profils (Datenbankform)~~ — **entschieden am 11.08.2026**,
  siehe [technik.md](technik.md)

- **Woher der Nutzer seinen Grundwortschatz bekommt** — aufgeworfen am 26.08.2026 durch
  die Abnahme T17: Bei 941 Worteinträgen und 25 Plätzen zeigt die Triage ausschließlich
  Kernwortschatz (`life`, `had`, `said`, `made`, `things`), während der Wortschatz, der
  das Kapitel tatsächlich schwer macht (`listlessly`, `tawdry`, `lurid`, `courteously`),
  sie in keinem Durchlauf erreicht. Das verletzt kein Abnahmekriterium und trotzdem den
  Zweck aus dem Kontext oben. Vorgesehene Richtung: Beim **Anlegen des Profils** wird
  gefragt, ob leer begonnen wird oder die häufigsten englischen Grundformen einmalig als
  bekannt eingetragen werden — die Frage füllt zugleich die Lücke, die bauplan.md in der
  T16-Zeile offen hält. Die Vorbelegung braucht eine eigene `Origin`, damit
  unterscheidbar bleibt, was der Nutzer selbst entschieden hat. Datenquelle ist
  voraussichtlich **kein** fremder Bestand: WikDicts `importance` liegt bereits vor
  ([technik.md](technik.md) §2, „Häufigkeitsdaten — unkritisch"); ob es trägt, ist zu
  messen, Rückfall wäre `wordfreq`
- **Nachrücken in der Triage** — aufgeworfen am 26.08.2026: Wird ein Wort als bekannt
  gebucht, rückt das nächsthäufigste Wort des Kapitels nach, statt den Platz verfallen zu
  lassen. Technisch heißt das, den Auflöser als Iterator zu führen, aus dem die Oberfläche
  nachzieht, statt eine fertige Liste zu übergeben; ein Modellaufruf je Nachrücker fällt in
  die Zeit, in der der Nutzer ohnehin liest. **Ändert die Bedeutung der Wortobergrenze**
  von „25 gezeigte" zu „25 nicht abgelehnte" und braucht deshalb eine Bremse — sonst
  entsteht mit der Sammelaktion ein Laufband. Kein Ersatz für die Vorbelegung, sondern
  deren Ergänzung
- **Fortsetzungsfrage nach der Wortobergrenze** — aufgeworfen am 26.08.2026: Nach 25
  Wörtern wird gefragt, ob weitergemacht oder aufgehört wird. Das ist die menschliche
  Bremse für das Nachrücken und legt die Entscheidung dorthin, wo die Information ist.
  Die Verzahnung mit Abnahmekriterium 5 ist **entschieden am 26.08.2026**: Die Druckseite
  fasst gemessen 36 Einträge ([technik.md](technik.md) §8c) und **darf im Zweifel mehrere
  Blätter belegen**. Solange Nachrücken und Fortsetzungsfrage nicht gebaut sind, ändert
  das nichts — die Wortobergrenze hält die Ausgabe unter der Kapazität eines Blattes, und
  Abnahmekriterium 5 gilt unverändert. **Mit** ihnen ist der Kriterientext nachzuziehen:
  „passt auf ein Blatt" wird dann zu „bricht sauber auf so viele Blätter um, wie nötig" —
  lesbar ohne Nachbearbeitung bleibt die Anforderung
- **Ob jenseits der Wortobergrenze etwas ins Profil geschrieben wird** — `Origin.WORD_LIMIT`
  und `KnowledgeState.DEFERRED` stehen für genau diesen Fall im Schema
  ([technik.md](technik.md) §4), gebucht wird heute nichts: Die Obergrenze wirkt allein
  lesend in `pipeline.resolve_triage_entries`, `triage.defer_beyond_word_limit` hat außerhalb
  der Tests keinen Aufrufer. Beides ist vertretbar — ein Vermerk „diesmal nicht gezeigt"
  bedeutet etwas anderes als das „Überspringen" aus Schritt 4 —, aber es ist nicht
  entschieden, sondern nebenbei entstanden. Hängt am Nachrücken oben, das die Bedeutung der
  Grenze ohnehin verschiebt
- **Ob Einträge ohne Wörterbucheintrag Vorrang haben sollen** — gemessen an einem echten
  Kapitel führen 119 von 1.410 Wort- und 33 von 212 Wendungseinträgen **nur** den
  `uncertain`-Platzhalter. Sie kosten keinen Modellaufruf und stehen unter
  `[triage] order = "new_words_first"` ([technik.md](technik.md) §9) damit immer vorn: In
  einem gemessenen Durchlauf waren **5 der 25 gezeigten Wörter** „kein Wörterbucheintrag —
  unsicher", also eine Frage ohne Bedeutung; unter `frequency` 4 von 25. Die Reihenfolge ist
  billig zu ändern, die Frage dahinter nicht: Ein Eintrag ohne Bedeutung ist für die Triage
  weniger wert als einer mit — er kostet aber auch nichts

**Die vier ursprünglichen Fragen sind entschieden**; die technischen Festlegungen samt
Begründung und Messwerten stehen in [technik.md](technik.md). Die fünf Punkte darüber sind
am 26.08.2026 aus der Abnahme T17, dem Gespräch darüber und der Auflösung der
Nacharbeitsliste neu hinzugekommen und **nicht** entschieden — sie werden erst besprochen,
dann gebaut.

---

## Abgrenzung — was LibreVerbum nicht ist

- **Kein Lesegerät.** Das Buch wird woanders gelesen: auf Papier, E-Reader oder Tablet
- **Keine Lern-App.** Das Wiederholen übernimmt Anki. LibreVerbum liefert das Material
- **Kein Kopierschutz-Werkzeug.** Nur DRM-freie Dateien
- **Kein Volltextübersetzer.** Es geht um Vokabeln und Wendungen, nicht um Übersetzung von Prosa

---

## Abnahmekriterien für Phase 1

Das Konzept ist bestätigt, wenn folgender Ablauf an einem echten, DRM-freien EPUB gelingt:

1. Buch wird eingelesen; die Kapitelliste stimmt mit dem Inhaltsverzeichnis der Datei überein.
   Enthält die Datei keines, wird das gemeldet und die Lesereihenfolge tritt an seine Stelle
   — siehe Nachtrag bei Schritt 1
2. Für ein mittleres Kapitel entsteht eine Wortliste, in der **Beugungsformen zusammengefasst**
   sind und **keine Figurennamen** als Lernvokabeln auftauchen
3. Die Übersetzungen passen zum Kontext: Stichprobe von zwanzig Wörtern, darunter mindestens drei
   mehrdeutige und zwei Redewendungen, wird manuell gegengeprüft
4. Das erzeugte Deck importiert sich in Anki fehlerfrei, Felder und Verschlagwortung sitzen richtig
5. Die Druckseite passt auf ein Blatt und ist ohne Nachbearbeitung lesbar
6. Beim zweiten Durchlauf desselben Kapitels werden die als *bekannt* markierten Wörter **nicht
   erneut** abgefragt — das Profil greift
7. (Optional - Wäre schön muss aber am anfang noch nicht sein) Die Triage lässt sich in unter zehn Minuten durchlaufen — inklusive Sammelaktion und
   Wortobergrenze
