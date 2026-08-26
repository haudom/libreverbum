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

**Wie tief vorher angereichert wird, ist eine Einstellung** (17.08.2026), weil die zwei Stufen
aus Abschnitt 5 sehr verschieden viel kosten:

| Stellung | was in der Triage steht | Kosten je Kapitel |
|---|---|---|
| **Wörterbuch** | die Liste der möglichen Bedeutungen — „watch — Uhr / Wache / beobachten" | rund **1,1 s**, kein Modellaufruf |
| **Wörterbuch + Modell** | zusätzlich ist die im Kontext gemeinte Bedeutung markiert | rund **1 s je Wort** bei 1.592 Grundformen |

Standard ist die erste Stellung, aus demselben Grund, aus dem Abschnitt 5 die Cloud-Gegenstelle
zuschaltbar statt vorgegeben macht: Der Regelfall läuft schnell und offline, die teurere
Genauigkeit wird bewusst gewählt. Ein Schalter ist das trotz Regel 14 (dokumentation.md §4)
zulässig, weil er zwei echte Anwendungsfälle trennt und nicht einen vermuteten zweiten vorbaut.

*Offen:* Was „kenne ich" in der ersten Stellung bei einem **mehrdeutigen** Wort bucht — dort
steht eine Liste, keine einzelne Bedeutung. Ob das ein Randfall oder der Normalfall ist,
entscheidet die Messung, wie viele Grundformen eines Kapitels überhaupt mehr als eine
Bedeutung haben; ebenso offen ist, wie stark **Bündeln** die zweite Stellung verbilligt.

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
  Zu klären ist die Verzahnung mit Abnahmekriterium 5: Die Druckseite fasst gemessen 36
  Einträge ([technik.md](technik.md) §8c), „weiter" sprengt sie irgendwann — entweder
  darf sie ein zweites Blatt bekommen, oder sie nimmt weiterhin die ersten 36, während
  die Karten darüber hinauswachsen

**Die vier ursprünglichen Fragen sind entschieden**; die technischen Festlegungen samt
Begründung und Messwerten stehen in [technik.md](technik.md). Die drei Punkte darüber sind
am 26.08.2026 aus der Abnahme T17 und dem Gespräch darüber neu hinzugekommen und **nicht**
entschieden — sie werden erst besprochen, dann gebaut.

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
