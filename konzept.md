# LibreVerbum — Produktkonzept

> Die technische Umsetzung — Programmiersprache, Bibliotheken, Bedienoberfläche,
> Modellwahl — ist entschieden; siehe [technik.md](technik.md) für das Wie.

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
      →  Bedeutungen beschaffen (Wörterbuch + LLM)  →  gegen Profil filtern
      →  Triage durch Nutzer  →  Export (Anki / Druck)
```

Kenntnis wird pro Bedeutung geführt, nicht pro Grundform (technik.md §4, „Kernentscheidung:
Kenntnis pro Bedeutung, nicht pro Wort") — sonst ließe sich „neue Bedeutung eines bekannten
Wortes" gar nicht erkennen. Der Abgleich gegen das Profil vergleicht deshalb auf Ebene der
Bedeutung und setzt bereits aufgelöste Bedeutungen voraus: Er läuft **nach** „Bedeutungen
beschaffen", nicht davor. Im Code ist es ebenso — `libreverbum/pipeline.py`, Abschnitt
„Regeln" des Moduldocstrings: „Der Abgleich gegen das Profil in `run_chapter` läuft nach
dem Nachschlagen im Wörterbuch". Aus demselben Grund läuft auch die Triage erst, nachdem
die Bedeutungen feststehen: Der zweite Eintrag eines mehrdeutigen Wortes wird dort als
„neue Bedeutung eines bekannten Wortes" gekennzeichnet, was voraussetzt, dass die Bedeutung
bereits feststeht.

Ausschlaggebend ist dabei nicht die Datenhaltung, sondern der Nutzerfall: Wer `watch` ohne
Bedeutungsangabe sieht, drückt „kenne ich" für die Uhr, während der Text die Wache meint —
und lernt das Wort nie. Der Belegsatz allein trägt das nicht; in einer zügigen Triage wird
er überflogen.

**Die Abschnittsnummern unten folgen weiterhin der ursprünglichen Reihenfolge**, nicht dem
tatsächlichen Ablauf, damit die Verweise aus technik.md gültig bleiben: Abschnitt 5
(„Übersetzen") läuft vor Abschnitt 4 („Triage"). Geändert hat sich nur die Reihenfolge,
nicht die Sache — Abschnitt 5 beschreibt weiterhin denselben Hybrid, er läuft nur früher.

### 1. Buch einlesen
EPUB öffnen, Metadaten (Titel, Autor) und die Kapitelstruktur auslesen. Fließtext von
Inhaltsverzeichnis, Impressum, Widmung und Fußnoten trennen. Fehlt der Datei eine
Kapitelstruktur, tritt die Lesereihenfolge an ihre Stelle — mit sichtbarem Hinweis.

Dass ein EPUB seine Kapitel kennt, ist dabei eine Annahme, keine Eigenschaft des Formats:
Von acht geprüften Büchern enthält eines weder Inhaltsverzeichnis noch Überschriften — ein
Konvertat, dessen Text in vier Blöcken zu je 30.000 Wörtern liegt. Geprüft und verworfen:
der naheliegende Rückfall auf Überschriften, denn jede Datei, die Überschriften hat, hat
auch ein Inhaltsverzeichnis. Einzelheiten in [technik.md](technik.md) §8, „Neuer Befund:
manchen Dateien fehlen die Kapitelgrenzen ganz".

Auch ein vorhandenes Inhaltsverzeichnis heißt nicht, dass ein Kapitel in einem Dokument
liegt. Bei „Dune" — Kapitelliste vollständig, Abnahmekriterium 1 erfüllt — waren 63 % des
Buchtexts unerreichbar, weil die Navigation nur auf das erste von drei zusammengehörenden
Dokumenten zeigt. Ein Kapitel reicht deshalb von seinem Navigationsziel bis zum nächsten,
und die Kapitelliste nennt je Kapitel den **Umfang in Wörtern**: Sie ist damit selbst die
Stelle, an der ein 78.000-Wörter-„Kapitel" auffällt. Einzelheiten in
[technik.md](technik.md) §8, „Ein Kapitel ist nicht ein Dokument".

*Nur DRM-freie Dateien.* Kopierschutz wird nicht umgangen.

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
- **Blockweise Triage mit Fortsetzungsfrage** — 25 Wörter bilden eine Portion, keine
  Obergrenze: Ist der Block durchgeklickt, wird gefragt, ob weitergemacht wird, und der
  nächste Block ist zu diesem Zeitpunkt bereits im Hintergrund aufgelöst, weil ein
  Modellaufruf je Eintrag in die Zeit fällt, in der der Nutzer ohnehin liest. Die Triage
  endet damit, wenn der Nutzer aufhören will, nicht wenn eine Zahl erreicht ist. Wie viel
  er durchgeht, bestimmt der Nutzer; eine harte Obergrenze gibt es nicht. Technische Seite:
  [technik.md](technik.md) §12

Eine harte Grenze bei 25 verbirgt genau den Wortschatz, der ein Kapitel schwer macht:
`listlessly`, `tawdry`, `lurid` stehen weit hinten in der Häufigkeitsliste und würden von
einer solchen Grenze nie erreicht ([technik.md](technik.md) §11, „Was die Vorbelegung nicht
löst"). Die Zahl 25 bleibt deshalb, bedeutet aber eine Portion, keine Schranke.

Beurteilt wurde die Zahl selbst beim ersten echten Durchlauf; der hat gezeigt, dass nicht
sie das Problem ist, sondern der Anfangszustand des Profils. **Der erste Durchlauf je Buch
ist ein Kalibrierdurchlauf, kein Lerndurchlauf:** Bei leerem Profil sind die 25 häufigsten
unbekannten Grundformen ausnahmslos A1/A2-Wortschatz (`life`, `had`, `said`, `made`); erst
nach einer Sammelaktion erscheinen `portrait`, `tragedy`, `dreadful`, `lad`, `afraid`. Eine
höhere Grenze verlängerte nur diesen Kalibrierdurchlauf — was ihn abkürzt, ist ein
Tastendruck und die Vorbelegung des Grundwortschatzes ([technik.md](technik.md) §11). Die
Obergrenze bleibt deshalb bei 25.

**In der Triage steht die gemeinte Bedeutung**, nicht bloß die Liste der möglichen. Sie wird
dafür **vor** der Triage aufgelöst, und „kenne ich" bucht auf sie — Kenntnis wird pro
Bedeutung geführt ([technik.md](technik.md) §4, „Kernentscheidung: Kenntnis pro Bedeutung,
nicht pro Wort"). Das kostet einen Modellaufruf je gezeigtem Eintrag und ist trotzdem nicht
verhandelbar: Zwei Drittel der Grundformen eines Kapitels sind mehrdeutig
([technik.md](technik.md) §3, „Zwei Drittel der Grundformen eines Kapitels sind
mehrdeutig"), und wer `watch` ohne Bedeutungsangabe sieht, drückt „kenne ich"
für die Uhr, während der Text die Wache meint.

Geprüft und verworfen ist dagegen eine Stellung ohne Modellaufruf, nur Wörterbuch: Sie zeigt
in der Triage eine Liste statt einer Bedeutung, und die Triage-Entscheidung hätte dann
keinen Gegenstand, auf den sie buchen kann — die Kostenrechnung dahinter leuchtet zwar ein
(gemessen sind die Kosten der Auflösung klein: rund 0,48 s je Wort bei höchstens 25 Wörtern,
[technik.md](technik.md) §3, „Trefferquote und Zeit bei fester Temperatur — 40 echte
Einträge über `pipeline.run_chapter`"), ändert aber nichts an der fehlenden Bedeutung.
Mehrdeutigkeit ist dabei der Normalfall (65,8 %), und **Bündeln** lohnt nicht
([technik.md](technik.md) §3, „Bündeln lohnt nicht — eine Anfrage je Wort").

*Später erweiterbar durch:* adaptiven Vokabeltest zur Erstschätzung und Import bestehender
Anki-Decks. Die **Angabe des Sprachniveaus** ist seit dem 01.09.2026 gebaut — A1 bis C1,
C2 wird nicht angeboten ([technik.md](technik.md) §11, „Warum C2 nicht angeboten wird").
Die Datenstruktur muss diese Quellen aufnehmen können, ohne umgebaut zu werden; für die
Niveau-Angabe hat sie es getragen: Die Ereignisfolge selbst blieb unangetastet, es genügte
eine neue Herkunft (`Origin.PRESET`) neben zwei nullbaren Spalten und einer achten Tabelle
([technik.md](technik.md) §4, „Fassung 2").

### 5. Übersetzen — der Hybrid-Ansatz

Dieser Schritt läuft **vor** Abschnitt 4, damit die Triage die Bedeutung anzeigen kann — die
Begründung steht beim Kernablauf oben. Die Nummer bleibt, die Sache auch.

Ein rein generatives Modell erfindet gelegentlich Übersetzungen, und der Nutzer bemerkt es
nicht — er kennt das Wort ja gerade nicht. Falsch gelernte Vokabeln sind schlimmer als gar
keine. Deshalb zweistufig:

1. **Offline-Wörterbuch** liefert die tatsächlich existierenden Bedeutungen eines Worts
2. **LLM** wählt anhand des Belegsatzes die **im Kontext passende** aus, formuliert die
   Kurzübersetzung und ergänzt Wortart und ggf. Anmerkungen

Das Modell **entscheidet**, statt zu **erfinden** — auch bei Redewendungen und Wendungen,
die kein Wörterbuch führt: Lässt man das Modell sie *frei benennen*, erfindet es — es nannte
Ausdrücke, die im Text gar nicht vorkommen. Wendungen ohne Wörterbucheintrag sind deshalb
stets als *unsicher* zu markieren, nicht dem Modell allein überlassen. Einzelheiten in
[technik.md](technik.md), Abschnitt „Messung: Mehrwortausdrücke".

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
([technik.md](technik.md) §3, „Zwei Drittel der Grundformen eines Kapitels sind
mehrdeutig"), und wer auf dem Blatt eine Grundform ohne Wortart liest, hängt die
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
- **Das Sprachniveau** — die Selbsteinschätzung beim Anlegen, aus der die einmalige
  Vorbelegung des Grundwortschatzes folgt (siehe „Bewusst offen" unten). Die einzige Angabe
  über den Nutzer selbst, nicht über ein Wort oder ein Buch

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

> **Abgenommen am 26.08.2026.** Der Durchlauf an einem echten, DRM-freien EPUB hat alle
> sieben Abnahmekriterien erfüllt — einschließlich des Anki-Imports und des geprüften
> Ausdrucks. Was die Abnahme an Fragen aufgeworfen hat, steht unter „Bewusst offen"; die
> Reihenfolge, in der Phase 1 gebaut wurde, hat ihren Zweck erfüllt und steht in `git log`.

### Phase 2 — Ausbau der Kernidee

Die **Qt-Oberfläche** aus [technik.md](technik.md) §1 gehört hierher und ist der erste
Schritt: Kapitelauswahl, Triage-Liste, Fortschritt — dieselbe Bedienung, die Phase 1 über
die Tastatur abgenommen hat ([technik.md](technik.md) §7, „Die Oberfläche liegt neben dem
Kern, nicht darunter").

- **Ganzes Buch auf einmal** verarbeiten, Kapitel einzeln oder in Blöcken
- **Abdeckungsanzeige**: „Lerne diese 34 Wörter und du verstehst 97 % von Kapitel 3." Rechnerisch
  einfach, weil alle Häufigkeiten vorliegen — und psychologisch das stärkste Motivationsmittel
  im ganzen Konzept
- **Buch-Schwierigkeitscheck**: ganzes Buch gegen das Profil halten → „ca. 14 unbekannte Wörter
  pro Seite, zu schwer für dich". Eigenständig nützlich, auch als Entscheidungshilfe vor dem Kauf
- **Lesezeichen-Druck** und weitere Druckvarianten, dazu die **PDF-Ausgabe ohne den Umweg
  über den Browser**, mit der Druckseite aus Phase 1 als Quelle — siehe
  [technik.md](technik.md) §8c, „Eine direkte PDF-Ausgabe ist Phase 2"
- Bootstrapping der Bekannt-Liste: adaptiver Vokabeltest und Import bestehender Anki-Decks.
  Die **Niveau-Angabe** ist seit dem 01.09.2026 gebaut ([technik.md](technik.md) §11); was
  von ihr hierher gehört, ist der adaptive Test — er schätzt denselben Wert, statt ihn zu
  erfragen, und verfeinert damit eine Selbsteinschätzung

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

- ~~**Woher der Nutzer seinen Grundwortschatz bekommt**~~ — **entschieden am 31.08.2026**,
  siehe [technik.md](technik.md) §11. Beim Anlegen des Profils wird nach dem Sprachniveau
  gefragt (A1 bis C1 oder ausdrücklich „keine Angabe"); die häufigsten N englischen
  Grundformen gelten dann als bekannt, gebucht mit der eigenen Herkunft `Origin.PRESET`.
  Datenquelle ist `wordfreq`, ausgeliefert als eingefrorene Liste im Paket — WikDicts
  `importance` wurde gemessen und verworfen, weil es die Belegdichte in Wiktionary misst
  und nicht die Texthäufigkeit. Die damals mitgenannte Lücke aus T16 war schon vorher
  geschlossen: `cli.main._confirm_new_profile` fragt seit dem 21.08.2026 nach, bevor ein
  Profil angelegt wird.

  **Gelöst ist damit die erste Hälfte des T17-Befunds, nicht die zweite.** Der
  Kernwortschatz besetzt die 25 Plätze nicht mehr — an `dorian_gray.epub` Nr. 10 gemessen
  sind bei B1 481 der 940 Grundformen und 1.584 der 2.240 Vorkommen vorbelegt. Der
  Wortschatz, der das Kapitel schwer macht (`listlessly`, `tawdry`, `lurid`,
  `courteously`), erreicht die Triage trotzdem nicht: Drei davon kommen genau einmal vor,
  wie 553 der 940 Einträge, und ein N, das bis zu ihnen reichte, belegte sie selbst vor.
  Das ist ein Rangproblem, kein Filterproblem, und hängt an den beiden folgenden Punkten
- ~~**Nachrücken in der Triage** und **Fortsetzungsfrage nach der Wortobergrenze**~~ —
  beide aufgeworfen am 26.08.2026, **entschieden am 01.09.2026** als **eine** Sache, siehe
  §4, „Blockweise Triage mit Fortsetzungsfrage" und [technik.md](technik.md) §12. Gebaut
  wird nicht das damals skizzierte Nachrücken Platz für Platz, sondern die **blockweise
  Triage**: 25 Einträge am Stück, danach die Fortsetzungsfrage, dann der nächste Block —
  der beim Fragen bereits im Hintergrund aufgelöst ist. Das erreicht dasselbe Ziel (der
  Wortschatz hinter Platz 25 wird erreichbar) und löst zugleich die Bremsfrage: Die
  Sammelaktion sieht in jedem Block wieder eine vollständige, nummerierte Liste, statt zum
  Laufband zu werden. Die Verzahnung mit Abnahmekriterium 5 war schon am 26.08.2026
  entschieden — die Druckseite fasst gedruckt gemessen 33 Einträge
  ([technik.md](technik.md) §8c, „Echt gedruckt statt gerechnet: MAX_ENTRIES auf 33
  korrigiert") und **darf mehrere Blätter belegen**; der Kriterientext ist mit dem Bau
  nachgezogen
- ~~**Ob jenseits der Wortobergrenze etwas ins Profil geschrieben wird**~~ — **entschieden
  am 01.09.2026: nichts.** Mit der blockweisen Triage gibt es keine Grenze mehr, hinter der
  etwas ohne Zutun des Nutzers verfiele: Wer aufhört, hat auf die Fortsetzungsfrage
  geantwortet, und diese Antwort ist keine Aussage über die einzelnen Wörter dahinter. Ein
  Vermerk „diesmal nicht gezeigt" bedeutet etwas anderes als das „Überspringen" aus
  Schritt 4, und hunderte Ereigniszeilen je Kapitel ohne eine Nutzerentscheidung dahinter
  wären der teurere Fehler. `Origin.WORD_LIMIT` und `KnowledgeState.DEFERRED` bleiben
  deshalb im Schema stehen, ohne dass die Obergrenze sie schreibt
  ([technik.md](technik.md) §4); `triage.defer_beyond_word_limit` behält seine Aufgabe für
  den einzelnen Block
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
Nacharbeitsliste neu hinzugekommen. Vier davon sind inzwischen entschieden — die
Vorbelegung am 31.08.2026, die drei zur Wortobergrenze am 01.09.2026. Offen ist allein der
letzte; er wird erst besprochen, dann gebaut.

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
   (Schritt 1)
2. Für ein mittleres Kapitel entsteht eine Wortliste, in der **Beugungsformen zusammengefasst**
   sind und **keine Figurennamen** als Lernvokabeln auftauchen
3. Die Übersetzungen passen zum Kontext: Stichprobe von zwanzig Wörtern, darunter mindestens drei
   mehrdeutige und zwei Redewendungen, wird manuell gegengeprüft
4. Das erzeugte Deck importiert sich in Anki fehlerfrei, Felder und Verschlagwortung sitzen richtig
5. Die Druckseite bricht sauber auf so viele Blätter um, wie nötig, und ist ohne
   Nachbearbeitung lesbar — die frühere Fassung „passt auf ein Blatt" folgte aus der
   inzwischen aufgehobenen harten Wortobergrenze (§4, „Blockweise Triage mit
   Fortsetzungsfrage")
6. Beim zweiten Durchlauf desselben Kapitels werden die als *bekannt* markierten Wörter **nicht
   erneut** abgefragt — das Profil greift
7. (Optional - Wäre schön muss aber am anfang noch nicht sein) Die Triage lässt sich in unter zehn Minuten durchlaufen — inklusive Sammelaktion und
   Fortsetzungsfrage, gemessen an **einem** Block (§4, „Blockweise Triage mit
   Fortsetzungsfrage"); wie viele Blöcke er durchgeht, entscheidet seither der Nutzer
