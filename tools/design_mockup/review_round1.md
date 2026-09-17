# Kritik der Gestaltungsrichtung „Glashaus" (Runde 1)

> **Rolle im Bestand.** Dies ist die erste der beiden Durchsichten aus AP 14
> (bauplan-phase2.md). `B1` bis `B24` sind die **Herkunftsangaben**, auf die sich die
> Regelkommentare in `gui/qml/Theme.qml` und in `tools/design_mockup/qml/*.qml` berufen —
> wie `bauplan.md T13` (CLAUDE.md, „Die Dokumente und ihre Zuständigkeit"). Was aus ihnen
> **dauerhaft gilt**, steht in technik.md §14 und in `Theme.qml`; diese Datei sagt nur, wo
> es herkommt, und fällt mit dem Mockup weg.
>
> Die Pfade unten stammen aus der Arbeitskopie im Scratchpad: `v0_ausgang/glashaus/` ist
> die verworfene Richtung „Glashaus" (nicht im Repositorium, technik.md §14, „Warum
> »Glashaus« gescheitert ist"), `messen.py` heißt heute
> `tools/design_mockup/contrast_check.py`.

Beurteilt wurde die Arbeitskopie in `scratchpad/design/v0_ausgang/`: die Renderings in
`png/`, der QML-Bestand in `glashaus/`, die Token in `glashaus/Mock/Theme.qml` und die
funktionale Wahrheit in `wireframes_und_pruflisten.md`.

Alle Zahlen in diesem Dokument sind **im gerenderten Bild gemessen**, nicht aus den Token
gerechnet — Skripte daneben (`messen.py`, `messen2.py`, `flaechen.py`, `crop.py`),
Gegenproben in `probe_png/`. Wo eine Zahl ein Kontrastverhältnis ist, ist es WCAG 2.1;
die Schwelle für Text unter 24 px ist 4,5:1, für Bedienelemente 3:1.

---

## 1. Urteil

Die Richtung trägt nicht: Sie ist als **Materialstudie** gebaut — Glas, Glanz, Schatten,
Spiegelung, Gel — und nicht als **Gestaltungssystem**, und deshalb bricht sie überall dort,
wo etwas anderes verlangt wird als die zwei Schaubilder, die gerendert wurden. Beide
umgesetzten Bildschirme fallen bei der Mindestgröße 900×600 auseinander, und zwar
**lautlos**: der Belegsatz läuft aus dem Fenster, die Schaltfläche „Abbrechen" verschwindet
ganz, und `shot.py` meldet dabei null Warnungen — genau der stille Fehlschlag, den die
Durchsicht dieses Projekts suchen soll. Im hellen Thema liegen sieben Textelemente unter
4,5:1 (bis hinunter zu 2,41:1), während das hauseigene `kontrast.py` „0 Paare unter 4,5:1"
meldet, weil es die `opacity:`-Faktoren im QML nicht kennt: ein Prüfwerkzeug, das falsches
Grün liefert. Die Flächenhierarchie ist messbar invertiert — die wichtigste Fläche
(die Karte, L=0,616) ist dunkler als der Grund, auf dem sie liegt (L=0,607), während die
unwichtigste (das Zitatfeld, L=0,828) und eine Zierblase (L=0,912) die hellsten Flächen des
Bildes sind. Und von den Bauteilen, die die fünf ungebauten Bildschirme brauchen —
Bildlauf, Tabellenzeile, Textfeld, Auswahlknopf, Schaltfläche ohne Tastenkappe,
Meldungsfeld, Fokusring — existiert **keines**, weshalb die Richtung an genau der Stelle
endet, an der sie gerade steht.

---

## 2. Was trägt

Diese neun Dinge sind gut und dürfen nicht verlorengehen. Sie sind einzeln benannt, damit
die nächste Runde sie nicht mit dem Glas zusammen wegwirft.

**2.1 Die Zusammenlegung von Wireframe 4 und 5.** Die Blockliste steht dauerhaft links,
der Eintrag rechts — ein Bildschirm statt zweier Modi. Das ist besser als der Wireframe und
gehört in den Bauplan übernommen: Wer dreihundertmal hintereinander entscheidet, muss
jederzeit sehen, wo im Block er steht, ohne umzuschalten. Die Liste muss dafür allerdings
Nummern, eine Wortartspalte und einen Bildlauf bekommen (B10, B5).

**2.2 Das Kopfwort als das eine große Ding.** 88 px, eigene Schrift, Leichtschnitt,
`letterSpacing: -1` — das ist messbar das stärkste Element des Bildschirms (11,6:1 hell /
17,4:1 dunkel) und beantwortet Prüfzeile 5.1 ohne Diskussion. Die Idee bleibt; nur die
Größenstaffel wird geordnet (B15) und die Spiegelung fällt weg (B6).

**2.3 Die Hervorhebung der Wortform im Belegsatz, in derselben Beugungsform.**
`drawing`, nicht `draw`, in der Akzentfarbe, 7,34:1 hell und 10,59:1 dunkel. Prüfzeile 5.6
ist damit erfüllt, und es ist die einzige Stelle, an der der Akzent wirklich etwas sagt.

**2.4 Zustand als Form, nicht nur als Farbe.** Auf dem Fortschritt: gefüllt = erledigt,
Ring mit Kern = läuft, leerer Ring = offen. Diese Entscheidung steht als Kommentar im Code
und ist richtig. Sie überlebt jede Gestaltungswahl.

**2.5 Das Häkchen als Pfad statt als Zeichen U+2713.** Begründung im Code: ein Zeichen wäre
eine Wette darauf, dass die mitgelieferte Schrift es führt. Diese Haltung — kein stilles
Ersatzglyph — gehört zur Hausordnung und soll Gewohnheit bleiben.

**2.6 Der Roboter als Wartezeichen.** Das Verfahren ist klug und billig: gedreht wird nicht
das Bild, sondern das Gesicht auf dem Zylinder (x = R·sin φ, Breite ∝ cos φ). Der
Fortschrittsbildschirm ist Wartezeit und der einzige Ort, an dem das Programm Charakter
zeigen darf. Bleibt — mit ruhigerer Bewegung (B18).

**2.7 Die Tastenkappe.** Ein kleines Tastensymbol vor der Beschriftung sagt in einem
Bauteil, dass dieselbe Sache über die Tastatur geht. Das ist die richtige Lösung für
Prüfzeile 5.9 und für einen Nutzer, der das Werkzeug lange benutzt. Nur der Behälter
drumherum ist zu groß (B14).

**2.8 `accent` und `accentFill` getrennt, `inkOnAccent` als Literal.** Eine Farbe, die als
**Schrift** 4,5:1 schaffen muss, kann nicht dieselbe sein, die als **Fläche** leuchten
soll; und ein Rechenausdruck (`Qt.darker(accentFill, 2.4)`) ist weder prüfbar noch war er
hell genug (3,78:1). Beides steht mit Begründung in `Theme.qml`. Das ist
Gestaltungssystem-Denken der richtigen Art — es fehlt nur der Rest des Systems.

**2.9 Die Prüfhaltung der Werkzeuge.** `shot.py` wertet jede QML-Warnung als Fehlschlag und
rendert bewusst mit echtem Fenster, weil `MultiEffect` im Software-Szenengraph **still**
ausfällt; `kontrast.py` misst den Grund im gerenderten PNG, statt die Malerei ein zweites
Mal zu rechnen. Beide Instinkte sind richtig. Was fehlt, ist die Abdeckung (B1, B2, B3).

---

## 3. Befunde

### schwer

---

**B1 — Der Belegsatz sprengt die Karte; bei 900×600 läuft er aus dem Fenster.**

*Ort:* `glashaus/Triage.qml`, das Zitatfeld am Ende des `ColumnLayout` (Zeilen 381–414),
in Verbindung mit `card.height: list.height`.

*Problem:* Das Zitatfeld bekommt `Layout.preferredHeight: quote.implicitHeight + …`, also
die Höhe, die der Satz braucht — die Karte hat aber eine feste Höhe. Wächst der Satz, wächst
das Feld über die Karte hinaus, ohne dass irgendetwas begrenzt oder warnt. Gegenprobe in
`probe_png/`: derselbe Bildschirm mit einem 384 Zeichen langen Satz aus demselben Kapitel
(„It was not that he felt any emotion akin to love for Irene Adler …").

- bei 1280×800: passt knapp, vier Zeilen, Feld bis 2 px an den Kartenrand
- bei 900×600: das Feld läuft **unter die Tastenleiste** und über den unteren Fensterrand
  hinaus; die letzten zwei Zeilen stehen hinter „S überspringen" und „Q beenden"
- `shot.py` meldet in beiden Fällen **0 Warnungen**

Schon mit dem *kurzen* Beispielsatz (100 Zeichen) steht das Feld bei 900×600 über der
Rundung der Kartenunterkante — siehe `c_klein_unten.png`, die Kartenecke liegt hinter dem
Feld.

*Wirkung:* Der Belegsatz ist die Begründung der Entscheidung — er sagt, in welchem Sinn das
Wort im Kapitel vorkommt. Er ist unlesbar, sobald er länger ist als das Beispiel. Prüfzeile
5.5 („bei einem 400 Zeichen langen Satz ist **kein** Wort abgeschnitten") und 5.10 fallen
durch, und zwar ohne jedes Signal.

*Schwere:* `schwer`.

---

**B2 — Der Fortschrittsbildschirm verliert bei 900×600 seine einzige Schaltfläche.**

*Ort:* `glashaus/Progress.qml`, `card.height: Math.min(parent.height - section*2,
content.implicitHeight + section*2)` bei `content` mit `anchors.fill: parent`.

*Problem:* Wird die Höhe gedeckelt, läuft der `ColumnLayout` einfach aus der Karte heraus;
nichts schneidet, nichts warnt. Gegenprobe `probe_png/fortschritt_900_hell.png`: Der
Gelbalken liegt **außerhalb** der Karte auf dem Grund, und „Esc Abbrechen" ist vollständig
unterhalb des Fensterrands verschwunden. 0 Warnungen.

*Wirkung:* Bei der Mindestgröße gibt es keine Möglichkeit mehr, einen laufenden Kapitellauf
abzubrechen. Prüfzeile 3.6 lässt sich nicht einmal fotografieren. Bei 1280×800 fällt das
nicht auf, weil das Mockup nur diese Größe zeigt.

*Schwere:* `schwer`.

---

**B3 — Sieben Textelemente unter 4,5:1 im hellen Thema — und `kontrast.py` meldet null.**

*Ort:* durchgehend; Ursache in `Theme.qml` (nur zwei Textfarben) und in den
`opacity:`-Faktoren, die die Bildschirme darauf legen.

*Gemessen* (heller Modus, gerendertes PNG, Textpixel gegen die lokale Fläche):

| Element | Größe | gemessen | Soll |
|---|---|---|---|
| offene Etappe „Buch lesen" (`opacity: 0.6`) | 17 px | **2,41 : 1** | 4,5 |
| Häufigkeit „21×" (`opacity: 0.7`) | 12 px | **2,86 : 1** | 4,5 |
| „… 10 weitere im Block" (`opacity: 0.7`) | 12 px | **3,01 : 1** | 4,5 |
| Zähler „14 von 14 Kapiteln" (`opacity: 0.8`) | 14 px | **3,42 : 1** | 4,5 |
| „SO STEHT ES IM KAPITEL" (`opacity: 0.85`) | 12 px | **3,79 : 1** | 4,5 |
| Marke „unsicher" | 10 px | **4,07 : 1** | 4,5 |
| Marke „Verb" | 13 px | **4,13 : 1** | 4,5 |
| Marke „3 zum Lernen" | 12 px | **4,32 : 1** | 4,5 |
| Marke „neue Bedeutung" | 10 px | **4,45 : 1** | 4,5 |
| leerer Ring einer offenen Etappe | Bedienelement | **1,63 : 1** | 3,0 |
| Kopfzeile Buchtitel | 15 px | 4,90 : 1 | knapp |

Das dunkle Thema ist in Ordnung (schlechtester Wert 4,81:1).

*Warum das Werkzeug es nicht sieht:* `kontrast.py` liest die Token aus `Theme.qml` und
blendet sie über den gemessenen Grund. Es kennt aber (a) die `opacity:`-Faktoren nicht, die
das QML auf einzelne Texte legt, (b) die getönten Chip-Füllungen nicht (`rgba(tone, 0.15)`),
(c) den Glanzstreifen von `Glass` nicht. Es meldet deshalb „0 Paare unter 4,5:1" und als
schlechtestes Paar 4,57:1 — während im Bild 2,41:1 steht.

*Wirkung:* Zwei Schäden. Erstens ist die gesamte zweite Informationsebene des hellen Themas
— Häufigkeiten, Zähler, Marken, offene Etappen — grenzwertig bis unlesbar; das trifft
ausgerechnet die Zahlen, nach denen der Nutzer die Reihenfolge seiner Entscheidungen
richtet. Zweitens, und schlimmer: das Werkzeug, das genau das verhindern soll, gibt grünes
Licht. Die Ursache ist systematisch, nicht schlampig: `Theme.qml` hat zwei Textfarben, aber
die Bildschirme brauchen drei Ränge — also greift jeder Bildschirm zu `opacity` und fällt
dabei jedes Mal unbemerkt unter die Schwelle.

*Schwere:* `schwer`.

---

**B4 — Die Flächenhierarchie ist invertiert; die unwichtigste Fläche ist die hellste.**

*Ort:* `Glass.qml` (`tint`, `elevation`) und ihre Verwendung in `Triage.qml`.

*Gemessen* (Relativluminanz leerer Flächenstellen, hell / dunkel):

| Fläche | hell | dunkel |
|---|---|---|
| Grund | 0,607 | 0,021 |
| **Karte (`elevation: 3`, der wichtigste Ort)** | **0,616** | **0,014** |
| Tastenleiste | 0,617 | 0,008 |
| Liste (`tint: 0.9`) | 0,687 | 0,005 |
| Kopfleiste | 0,703 | 0,009 |
| Zitatfeld | 0,828 | 0,009 |
| **Blase der Übersetzung (`tint: 1.22`)** | **0,912** | 0,014 |

*Problem:* Hell liegen fünf Flächen auf fünf verschiedenen Helligkeitsstufen, und die
Reihenfolge ist die falsche. Die Karte ist gegenüber dem Grund um 1,4 % heller —
Verhältnis 1,01:1, also als Fläche unsichtbar; sie wird allein von der 1px-Kante und dem
Schlagschatten getragen. Die hellste Fläche des ganzen Bildes ist eine Sprechblase, die
zweithellste das Zitatfeld: die beiden Elemente, die *in* der Karte liegen, sind heller als
die Karte. Damit liest sich keine Fläche als die wichtigste.

Dunkel liegen **alle** Flächen und der Grund zwischen L=0,005 und L=0,021 — ein Abstand von
1,6 Prozentpunkten. Die Karte ist dort sogar dunkler als der Grund. Das heißt: Der ganze
Aufwand der Richtung (Verlaufsfüllung, Glanzstreifen, Lichtkante, gemalter
Unschärfe-Ersatz, Schatten) erzeugt im dunklen Thema einen Flächenunterschied von 0,7
Prozentpunkten. Das Glas leistet dort nichts; es bleiben Haarlinien.

*Wirkung:* Der Blick hat keinen Eintrittspunkt. Auf einem Bildschirm mit vierzehn
abgerundeten Behältern (4 Scheiben, 2 Blasen, 3 Marken, 1 hervorgehobene Zeile, 4
Tastenpillen) sagt die Helligkeit nichts über den Rang, und die Form auch nicht, weil alles
dieselbe Pillenform hat.

*Schwere:* `schwer`.

---

**B5 — Der Bestand trägt fünf der sieben Bildschirme nicht; die nötigen Bauteile fehlen
vollständig.**

*Ort:* `glashaus/` insgesamt.

*Vorhanden:* Scheibe (`Glass`), Grund (`Ground`), Blase (`Bubble`), Marke (`Chip`), Taste
mit Tastenkappe (`KeyButton`), Balken (`GelBar`), Schatten (`Shadowed`), Roboter.

*Gebraucht, aber nicht vorhanden:*

| Bildschirm | fehlt |
|---|---|
| 1 Einrichtung | Auswahlknopf (sechs Niveaustufen), Textzeile mit Pfad, Schaltfläche **ohne** Tastenkappe in zwei Rängen, Balken **mit** zwei Zahlen und Beschriftung, Meldungsfeld für den Fehlschlag im Wortlaut |
| 2 Buch/Kapitel | Bildlauf, Tabellenzeile mit drei Spalten, rechtsbündige Zahlenspalte, Einrückung für `level > 0`, gedimmte Zeile mit `skip_reason`, unbedienbarer Zustand einer Schaltfläche |
| 4 Triage-Liste | Bildlauf, Nummernspalte, Wortartspalte, Zahleneingabe, Meldung bei ungültiger Eingabe |
| 6 Blockende | Zahlenbilanz (drei Zeilen, rechtsbündig), Warnfeld, bedingtes Verschwinden von „Weiter" |
| 7 Abschluss | Auswahlknopf, Dateiliste, Pfad zum Kopieren, zwei gleichrangige Schaltflächen |

Dazu **querschnittlich fehlend:** ein Fokusring (die gemeinsame Prüfliste verlangt
ausdrücklich „Tastaturfokus im Screenshot sichtbar, gezeichnet in `accent`"), ein
Schwebe- und ein Druckzustand, eine Trennlinie, ein Fehlerrot.

*Besonders hart:* **Nirgends im Bestand gibt es einen Bildlauf.** Die Blockliste löst das
Problem, indem sie die Zeilenzahl aus der Panelhöhe rechnet und den Rest mit „… N weitere im
Block" abschneidet. Für Bildschirm 2 (ein Roman hat leicht 60 Kapitel) und Bildschirm 4
(alle Einträge des Blocks, durchnummeriert, Prüfzeile 4.1) ist das kein Ersatz. Und ein
Bildlauf ist in dieser Richtung teuer: Eine `Glass`-Scheibe hat 24 px Radius und oben einen
26 px hohen weißen Glanzstreifen — gescrollter Text verschwindet unter einem hellen Verlauf
und wird von der Rundung abgeschnitten.

*Wirkung:* Die nächste Runde kann nicht weiterbauen, sondern muss für jeden neuen
Bildschirm das Material neu erfinden — was in Runde 1 bereits einmal passiert ist (der
Kommentar in `KeyButton.qml` beschreibt, wie die Tasten „ihre eigene Sprache" hatten). Eine
Richtung, die nur bei zwei Schaubildern funktioniert, ist keine Richtung.

*Schwere:* `schwer`.

---

**B6 — Die Spiegelung unter dem Kopfwort liest sich als zweites, abgeschnittenes Wort — und
steht genau dort, wo die Prüfliste nichts erlaubt.**

*Ort:* `Triage.qml`, `mirrorBox` (Zeilen 287–306).

*Problem:* Der Kommentar begründet die Spiegelung an der Grundlinie damit, dass sie sonst
„wie ein zweites, abgeschnittenes Wort" aussähe. Genau so sieht sie aus. Die Klipphöhe
(`ascent * 0.22`) schneidet die gespiegelten Buchstaben an der Stelle, an der sie in
unzusammenhängende Striche zerfallen; im Bild steht unter „drawing" eine Folge von
Fragmenten, die wie ein Zeichenfehler wirkt (siehe `c_karte_hell.png`, hell wie dunkel
gleich).

Dazu kommt der Verstoß: Prüfzeile 5.2 verlangt, dass die Übersetzung **unmittelbar**
unter der Wortform steht, „ohne dass ein anderes Element dazwischen steht". Dazwischen
stehen heute die Spiegelung, ein Abstandselement und der Roboter.

*Wirkung:* Der Nutzer sieht dreihundertmal pro Kapitel einen scheinbaren Zeichenfehler unter
dem einen Wort, auf das er schauen soll. Effekt ohne Leistung, mit Kosten.

*Schwere:* `schwer` (wegen des Prüflistenverstoßes; für sich allein `mittel`).

---

**B7 — Die Angaben zum Wort sind über drei Orte verstreut, und die Marke „neue Bedeutung"
fehlt auf dem Eintragsbildschirm ganz.**

*Ort:* `Triage.qml`, Kopfzeile der Karte (Zeilen 230–270) und Blaseninhalt (Zeilen 352–360).

*Problem:* Prüfzeile 5.3 verlangt: „Wortart, Häufigkeit und Bedeutungsangabe stehen in
**einer Zeile** in `textMuted`, getrennt durch dasselbe Zeichen — genau drei Angaben, nicht
mehr." Tatsächlich stehen dort **vier** Angaben an **drei** Orten: die Marke „Verb" und
„Grundform draw" links oben, fünf Punkte und „5× im Kapitel" rechts oben, die
Bedeutungsangabe unten in der Sprechblase. Kein Trennzeichen, keine gemeinsame Zeile.

Prüfzeile 5.8 verlangt `[ neue Bedeutung eines bekannten Wortes ]` auf einer eigenen Zeile
des Eintrags. Im `Triage.qml` gibt es dafür **kein Element** — die Marke existiert nur in
der Liste links, klein und gekippt. Bei einem Wort mit neuer Bedeutung erfährt der Nutzer am
Ort der Entscheidung nicht, warum es ihm vorgelegt wird.

*Wirkung:* Der Blick muss die Karte absuchen, statt eine Zeile zu lesen; und die einzige
Angabe, die eine Entscheidung wirklich ändern kann („du kennst das Wort, aber nicht in
dieser Bedeutung"), fehlt an der Stelle, an der entschieden wird.

*Schwere:* `schwer`.

---

### mittel

---

**B8 — Die Akzentfarbe trägt sechs Bedeutungen gleichzeitig; für „Achtung" bleibt keine.**

*Ort:* `Theme.qml` (`accent`, `accentFill`, `accentGlow`, `posVerb` hell = `#8a4206`) und
alle Verwendungen.

Bernstein bedeutet derzeit: *hier stehst du gerade* (Zeile in der Liste, Strich im
Kopfbalken), *das hast du zum Lernen gewählt* (Marke „3 zum Lernen"), *diese Taste ist
hervorgehoben*, *die Maschine arbeitet* (Roboterauge, Lampe, Gelbalken), *neue Bedeutung*,
*dieses Wort ist im Satz gemeint*. Zusätzlich ist im hellen Thema die Wortart „Verb" ein
Braunton derselben Familie.

*Wirkung:* Eine Farbe mit sechs Bedeutungen hat keine. Vor allem aber: Regel 13 verlangt,
dass **jeder Fehlschlag mit Wortlaut im Fenster steht** — dafür gibt es keinen Farbrang. Das
einzige Rot in den Token ist `posAdj` (`#a01248`), und das ist an die Adjektive vergeben.
Die erste Fehlermeldung wird also entweder in Bernstein geschrieben (dieselbe Farbe wie
„gewählt") oder erfindet eine Farbe außerhalb der Token — was die gemeinsame Prüfzeile
ausdrücklich verbietet.

*Schwere:* `mittel`.

---

**B9 — Die Wortartpunkte sind ein Rätsel, dessen Lösung daneben steht.**

*Ort:* `Triage.qml`, Zeile 151–158 (Listenpunkt) und 250–262 (Häufigkeitspunkte).

*Problem:* 7 px große Punkte in vier Farben, ohne Legende, ohne Wiederholung der Zuordnung.
Im hellen Thema sind die vier Töne sämtlich dunkel und wenig gesättigt (`#8a4206` Braun,
`#0a6b62` Dunkeltürkis, `#a01248` Magenta, `#2348c4` Blau); bei 7 px unterscheiden sich
Braun und Dunkeltürkis kaum. Der Kommentar sagt, der Punkt spare ein Wort — die Wortart
steht aber auf der Karte daneben im Klartext („Verb"), und Prüfzeile 4.2 verlangt für die
Liste ausdrücklich eine **Wortartspalte gleicher Breite**, also Text.

Dieselbe Bauform noch einmal als Häufigkeitsanzeige: fünf Punkte neben „5× im Kapitel". Die
Punkte sind bei 8 gedeckelt (`Math.min(frequency, 8)`), sagen also bei 21× dasselbe wie bei
8× — und die Zahl steht ohnehin daneben.

*Wirkung:* Zwei Zierelemente, die Information vortäuschen, die sie nicht liefern, und die
Liste optisch unruhig machen, ohne den Text zu ersetzen.

*Schwere:* `mittel`.

---

**B10 — Die Blockliste hat keine Nummern; damit ist die Sammelaktion nicht bedienbar. Und
die Häufigkeit verschwindet, sobald eine Marke da ist.**

*Ort:* `Triage.qml`, Listendelegat (Zeilen 127–192).

*Problem:* Prüfzeile 4.1 verlangt „alle Einträge des Blocks, **durchnummeriert ab 1**",
Prüfzeile 4.6/4.7 hängen daran: Die Sammelaktion fragt „Bis zu welcher **Nummer** kennst du
alles?". Ohne Nummern in der Liste kann der Nutzer die Frage nicht beantworten. Es gibt sie
nicht.

Zweitens: `visible: parent.row[4] === ""` — die Häufigkeitszahl wird ausgeblendet, sobald
die Zeile eine Marke trägt. Im Bild steht „note" ohne seine 10×. Prüfzeile 4.5 verlangt die
Häufigkeitsspalte für jede Zeile. Marke und Zahl konkurrieren um dieselbe Position, weil es
keine Spalten gibt.

Drittens laufen die rechten Enden ausgefranst: Zahlen sitzen bei `rightMargin: 30`, Marken
bei `rightMargin: 14` und zusätzlich um −3° gekippt. Es gibt keine rechte Kante.

*Wirkung:* Eine der beiden Triage-Bedienungen (die Sammelaktion, die den Block überhaupt
erst erträglich macht) ist mit dieser Liste nicht baubar.

*Schwere:* `mittel`.

---

**B11 — „… N weitere im Block" rechnet falsch und zeigt eine Zahl, die lügt.**

*Ort:* `Triage.qml`, Zeile 200: `Content.total - list.visibleRows`.

*Problem:* Gerechnet wird gegen `Content.total` (25), angezeigt werden Zeilen aus
`Content.blockEntries` (20 Einträge). Bei 15 sichtbaren Zeilen steht „… 10 weitere im
Block", obwohl nur 5 weitere existieren; bei 900×600 steht „… 16 weitere" bei 11
tatsächlich vorhandenen. Der Nenner der Liste und der Nenner des Zählers sind zwei
verschiedene Größen.

*Wirkung:* Genau die Klasse von Fehler, die technik.md §13 benennt: eine Zahl, die
Fortschritt behauptet, den es nicht gibt. Hier ist es Mockup-Inkonsistenz — die Bauform
selbst (zwei Quellen für eine Zahl) wandert aber unverändert in die Umsetzung.

*Schwere:* `mittel`.

---

**B12 — „will ich lernen" ist dauerhaft hervorgehoben und sieht aus wie eine Vorauswahl.**

*Ort:* `Triage.qml`, Zeile 440: `highlighted: index === 1`; `KeyButton` mit
`glow: 0.55`.

*Problem:* Eine von vier gleichrangigen Entscheidungen ist bernsteinfarben gefüllt und mit
einem Leuchten unterlegt, das über die Nachbartasten und über den Rand der Tastenleiste
hinausläuft (sichtbar in `c_tasten_hell.png`). Es gibt keinen Zustand, den diese Markierung
bezeichnet: keine Vorauswahl, kein Fokus, kein zuletzt Gedrücktes.

*Wirkung:* Zweifach. Erstens legt die Oberfläche bei jeder einzelnen von dreihundert
Entscheidungen eine Antwort nahe — ein Werkzeug, das die Triage des Nutzers verzerrt, ist
schlechter als eines, das schweigt. Zweitens ist dies die einzige auffällige Markierung auf
dem Bildschirm; sobald ein echter Fokusring dazukommt (B5), konkurrieren beide, und der
Nutzer lernt, das Bernstein zu ignorieren.

*Schwere:* `mittel`.

---

**B13 — Kein Bauteil hat einen Fokus-, Schwebe- oder Druckzustand.**

*Ort:* `KeyButton.qml`, `Chip.qml`, Listendelegat — keiner davon kennt `activeFocus`,
`hovered` oder `pressed`.

*Wirkung:* Die gemeinsame Prüfzeile („Der Tastaturfokus ist im Screenshot sichtbar,
gezeichnet in `accent`, nicht in `border`") ist mit dem heutigen Bestand nicht erfüllbar.
Für eine Anwendung, deren Hauptbildschirm über die Tastatur bedient wird und deren
Einrichtungsbildschirm ein Formular ist, ist das keine Feinheit, sondern die
Grundvoraussetzung.

*Schwere:* `mittel`.

---

**B14 — Die Tastenleiste kostet 96 px Höhe für vier Beschriftungen, die auswendig sitzen —
und „beenden" steht gleichrangig neben den drei Entscheidungen.**

*Ort:* `Triage.qml`, `actions` (Höhe 78 + 18 Abstand), `KeyButton` (`implicitHeight: 54`).

*Problem:* 96 px sind 12 % der Fensterhöhe bei 1280×800 und **16 % bei 900×600** — also
genau der Platz, der dem Belegsatz dort fehlt (B1). Bezahlt wird er für vier statische
Beschriftungen, die ein Nutzer, der das Werkzeug regelmäßig benutzt, nach zehn Einträgen
kennt. Bei reiner Tastaturbedienung ist die Klickfläche der Pillen ohne Wert.

Dazu: `Q beenden` hat dieselbe Größe, dieselbe Form, dieselbe Farbe und denselben Abstand
wie die drei Entscheidungen. Die eine Taste, die den Durchgang abbricht, steht in der Reihe
der Tasten, die man dreihundertmal drückt.

*Wirkung:* Verschwendeter Raum am teuersten Ort und ein Fehlgriffrisiko bei der einzigen
folgenreichen Taste.

*Schwere:* `mittel`.

---

**B15 — Es gibt kein Maßsystem: keine Rastereinheit, keine Typo-Skala.**

*Ort:* `Theme.qml` (`space`) und beide Bildschirme.

*Abstände:* 4 / 10 / 18 / 30 / 48. Die Sprünge sind 2,5× / 1,8× / 1,67× / 1,6× — keine
Leiter, und vor allem keine Grundeinheit: 18 ist kein Vielfaches von 4 oder 10, 30 keines
von 18. Daneben stehen in `Triage.qml` allein: 58 (Kopfhöhe), 78 (Tastenleiste), 292 und 236
(Listenbreite), 32 (Zeilenhöhe), 22, 16, 7, 3, −4, 26, 54. Aus diesen Zahlen lässt sich kein
Rhythmus ableiten, und die nächste Runde kann keine neue Fläche „passend" bauen.

*Schriftgrößen:* 10, 12, 13, 14, 15, 16, 17, 18, 24, 26, 32, 54, 88 — dreizehn Größen für
zwei Bildschirme, davon vier (12/13/14/15) ohne unterscheidbare Rolle. Dazu zwei Familien
(Quicksand/Cabin), deren Unterschied bei 12–15 px nicht lesbar ist und die ohne Regel
gemischt werden: „7 von 25" steht in der Auszeichnungsschrift, der Buchtitel daneben in der
Brotschrift, ohne Grund.

*Wirkung:* Kein Rang ist durch Größe eindeutig belegt, und jede Änderung ist Handarbeit.
Das ist der Unterschied zwischen einem System und zwei gemalten Bildschirmen.

*Schwere:* `mittel`.

---

**B16 — Hell und dunkel sind nicht ein Entwurf in zwei Themen, sondern zwei Entwürfe.**

*Ort:* `Glass.qml`, `Bubble.qml` in Verbindung mit `Theme.glassAlpha` (0,54 hell / 0,42
dunkel) und `glassEdge` (Weiß 0,85 / Weiß 0,26).

*Problem:* Hell ist eine Scheibe ein mattiertes, deutlich helleres Panel mit sichtbarem
Glanzstreifen. Dunkel ist dieselbe Scheibe eine **Kontur** — die Fläche unterscheidet sich
um 0,7 Prozentpunkte Luminanz vom Grund (B4), sichtbar ist nur die Haarlinie. Die
Sprechblase der Übersetzung ist dunkel exakt so hell wie die Karte, auf der sie liegt; sie
existiert dort nur als Umriss.

*Wirkung:* Wer das helle Thema beurteilt, beurteilt nicht das dunkle. Änderungen an der
Fläche wirken in den beiden Themen verschieden stark, und jede Prüfung muss beide Bilder
einzeln ansehen — was der Entwurf zwar tut, aber um den Preis, dass keine Aussage über „die
Fläche" mehr gilt.

*Schwere:* `mittel`.

---

**B17 — Die Segmentreihe im Kopf sagt nichts, was daneben nicht steht, und skaliert nicht.**

*Ort:* `Triage.qml`, Zeilen 50–70.

*Problem:* 25 Striche à 3 px plus 3 px Abstand = rund 150 px Kopfleiste für eine Aussage,
die zwei Zentimeter weiter rechts als „7 von 25" steht. Die Breite wächst linear mit der
Blockgröße (bei 60 Wörtern 360 px), und unter 1100 px Fensterbreite fällt die Reihe
ersatzlos weg (`visible: !screen.narrow`).

*Wirkung:* Ein Element, das folgenlos verschwinden kann, ist Zierde. Hier kostet es die
Hälfte der Kopfleiste und drängt den Buchtitel — die einzige Angabe, die sagt, woran man
arbeitet — nach links in die Ecke.

*Schwere:* `mittel`.

---

**B18 — Die Roboterdrehung ist zu schnell, zu vollständig und pausenlos.**

*Ort:* `Robot.qml`, Zeilen 243–247: `NumberAnimation { from: 0; to: 2*Math.PI; duration:
2800 }`, dann 900 ms Pause, `loops: Animation.Infinite`.

*Problem:* Eine volle Umdrehung alle 3,7 Sekunden, endlos. Der Streifen
`robot_streifen_hell.png` zeigt, was dabei passiert: zwischen 135° und 225° ist das Gesicht
vollständig weg — der Kopf ist ein glatter Block mit einem dunklen Balken. Rund ein Drittel
jedes Zyklus zeigt also keinen Roboter, sondern ein Objekt.

*Wirkung:* Auf einem Bildschirm, der Minuten stehen kann, wirkt eine Dauerrotation
hektisch statt geduldig, und der gesichtslose Abschnitt liest sich als Aussetzer. Die Idee
ist gut (2.6), die Ausführung nervt bei der dritten Minute. Empfehlung: ein Umsehen von rund
±60° mit Halten an den Enden, deutlich langsamer, und die volle Umdrehung höchstens als
seltenes Ereignis.

*Schwere:* `mittel`.

---

### leicht

---

**B19 — Die Nase der Sprechblase schneidet in den Roboterkopf.**
`Triage.qml`, `Layout.leftMargin: -4`. Hell verschmilzt der graue Keil mit der Wange, dunkel
zieht die 1px-Kontur der Blase eine sichtbare Linie quer über den Kopf
(`c_robot_dunkel.png`). `leicht`.

**B20 — Die Bedeutungsangabe wird abgeschnitten.**
`Triage.qml`, Zeile 356: `elide: Text.ElideRight` auf einer einzeiligen `Text`. Prüfzeile
5.4 verlangt, dass dort auch `dictionary.NO_SENSE_LABEL` oder `UNCERTAIN_LABEL` **im
Wortlaut** steht; Regel 1 sagt, nichts fällt weg. Ein längerer Bedeutungstext endet mit „…".
`leicht` (wird `mittel`, sobald echte Daten laufen).

**B21 — Bei 900×600 schrumpft der Satz statt des Rands.**
`Triage.qml`: Belegsatz 18 → 16 px, Kopfwort 88 → 54 px, Übersetzung 32 → 24 px, Listenbreite
292 → 236. Prüfzeile 5.10 verlangt ausdrücklich das Gegenteil: „notfalls schrumpft der
Randabstand, nie der Satz." `leicht`.

**B22 — Die Überschrift des Fortschritts nennt die Kapitelnummer nicht.**
Wireframe 3: „Kapitel 2 wird vorbereitet — I. A Scandal in Bohemia". Der Entwurf zeigt
„Kapitel wird vorbereitet" und Titel/Buch in einer zweiten Zeile. `leicht`.

**B23 — Der Gelbalken hat weder Beschriftung noch Zahlen.**
`GelBar.qml`. Für den Fortschritt ist das hinnehmbar (die Zähler stehen in der Liste); für
Bildschirm 1 nicht — Prüfzeile 1.4 verlangt zwei Zahlen (geladen / gesamt) am Balken, die
sich zwischen zwei Screenshots unterscheiden. Bauteil fehlt (gehört zu B5). `leicht`.

**B24 — Das Mockup zeigt den günstigen Zustand.**
`Progress.qml` rendert fünf von sechs Etappen als erledigt und keine einzige als „offen".
Der Zustand, den der Nutzer als ersten sieht (eine läuft, fünf offen), war nie gerendert —
und fällt mit 2,41:1 durch (B3). Ein Mockup, das nur den schmeichelhaften Fall zeigt, prüft
nichts. Für die nächste Runde als Regel: jeder Bildschirm wird im **ungünstigsten**
Datenfall gerendert (längster Satz, leerste Liste, Fehlermeldung, alles offen). `leicht`.

---

## 4. Empfohlene Richtung

**Die Richtung „Glashaus" wird nicht überarbeitet, sondern ersetzt.** Sie ist nicht deshalb
zu verwerfen, weil Glas altmodisch wäre, sondern weil ihr tragendes Mittel —
Durchsichtigkeit — die zwei Dinge unmöglich macht, die dieses Programm braucht: eine Fläche,
die immer gleich aussieht (die Scheibe ändert ihren Kontrast je nachdem, über welchem Licht
des Grundes sie zufällig liegt, B3/B4), und eine Rangordnung von Flächen (fünf Stufen, in
der falschen Reihenfolge). Zwei der drei ursprünglichen Gründe für das Glas sind außerdem
weggefallen: `MultiEffect` ist seit dem 17.09.2026 erlaubt, und der Software-Renderer muss
nicht mehr getragen werden.

Vorschlag: **„Lesetisch"** — ein Leseinstrument, kein Schaufenster. Das Programm wird vor
dem Lesen benutzt, regelmäßig, jahrelang; es soll aussehen wie eine gut gesetzte Seite mit
ruhigem Rahmen und nicht wie eine Oberfläche, die sich vorstellt.

**Haltung.** Nichts glänzt, nichts spiegelt, nichts schwebt. Wirkung entsteht aus
Flächenhelligkeit, Weißraum, Schriftgröße und **einer** Akzentfarbe mit **einer** Bedeutung.
Dekoration gibt es an genau einem Ort: dem Fortschrittsbildschirm (siehe 5.).

**Ebenenmodell — drei Ebenen, deckend.**

| Ebene | was | hell | dunkel |
|---|---|---|---|
| L0 Grund | Fensterhintergrund, ein Vollton | `#eaeef2` | `#12161b` |
| L1 Fläche | die Arbeitsfläche: Karte, Seitenliste, Kopf, Fuß | `#ffffff` | `#1b2027` |
| L2 Hervorhebung | **nur** die laufende Zeile und der Fokusring | `#fff4e2` / Akzentkante | `#2a2118` / Akzentkante |

Zusicherung, die geprüft wird: L1 zu L0 mindestens **1,25:1** gemessen, damit eine Fläche
auch ohne Schatten eine Fläche ist. **Keine Verläufe auf Flächen, kein Glanzstreifen, keine
Durchsichtigkeit, keine Schlagschatten** (nichts in diesen sieben Bildschirmen schwebt
wirklich). Trennung durch Helligkeitsstufe und, wo nötig, eine 1px-Linie in `hairline`.

**Farbrollen — jede Farbe hat genau eine Aufgabe.**

| Token | Aufgabe | Zusicherung |
|---|---|---|
| `ink` | Kopfwort, Listenwort, Belegsatz | ≥ 12:1 auf L1 |
| `inkSoft` | Beschriftungen, Zähler, Metazeile | ≥ 4,5:1 auf L0 **und** L1 |
| `inkFaint` | Nummernspalte, „N weitere", übersprungene Zeilen | ≥ 4,5:1 auf L0 **und** L1 |
| `accent` | **nur:** „das hier ist gerade dran" — laufende Zeile, laufende Etappe, Fokusring, das Wort im Belegsatz | Schrift ≥ 4,5:1, Fläche ≥ 3:1 |
| `chosen` | „zum Lernen gewählt" (eigene Farbe, z. B. Grün) | ≥ 4,5:1 |
| `warn` | **Fehlschlag im Wortlaut** (Regel 13) — heute nicht vorhanden | ≥ 4,5:1 |

Ein dritter Textrang (`inkFaint`) ist die eigentliche Lehre aus B3: Es gab ihn nicht,
deshalb griff jeder Bildschirm zu `opacity` und fiel unbemerkt durch. Daraus folgt die harte
Regel: **`opacity` nie auf Text.** Wer einen schwächeren Rang braucht, nimmt ein Token.
Wortarten bekommen **Text in einer eigenen Spalte**, keine Farbpunkte (B9, Prüfzeile 4.2).

**Typo-Skala — fünf Stufen, zwei Schnitte.** Eine Textschrift mit brauchbaren Kleingrößen
(Inter, Source Sans 3 oder Segoe UI); eine Auszeichnungsschrift nur, wenn sie an **genau
einem** Ort steht — dem Kopfwort.

| Stufe | Größe | Gebrauch |
|---|---|---|
| Marke | 12 px, Versalien, `letterSpacing` 0,8 | „SO STEHT ES IM KAPITEL", Spaltenköpfe |
| Klein | 14 px | Zähler, Häufigkeit, Metazeile |
| Normal | 16 px | Listenzeilen, Belegsatz, Formulartext |
| Titel | 22 px | Bildschirmüberschrift, Übersetzung |
| Kopfwort | 60 px | nur die Wortform, **eine** Größe für alle Fenstergrößen |

Zwei Gewichte (400, 600). Betonung durch Gewicht und Farbe, nie durch Deckung.

**Rastereinheit: 8 px.** Abstände ausschließlich 8 / 16 / 24 / 32 / 48 / 64. Zeilenhöhe der
Listen 32. Seitenrand 24 (bei 900×600: 16). Radius 8 für Flächen, 4 für Marken, Pillenform
nur für die Tastenkappen. Jede Zahl im QML ist ein Token oder ein Vielfaches von 8 — das ist
mit einem Grep prüfbar und gehört in die Prüfschleife aus AP 15.

**Layoutregel gegen B1/B2:** Auf jedem Bildschirm bekommt **das dehnbare Element**
(Belegsatz, Kapitelliste, Dateiliste) `Layout.fillHeight` und alles andere feste Höhe — nicht
umgekehrt. Flächen mit gedeckelter Höhe bekommen `clip: true`, damit ein Überlauf sichtbar
abschneidet statt lautlos auszulaufen. Listen sind echte `ListView` mit Bildlaufleiste,
`currentIndex` und Tastaturnavigation.

**Bauteilsatz, der alle sieben Bildschirme trägt** (zu bauen, bevor der zweite Bildschirm
entsteht): Fläche · Trennlinie · Listenzeile · Tabellenzeile (Nummer rechtsbündig, Text,
Zahl rechtsbündig, Einrückung, gedimmter Zustand) · Textzeile mit kopierbarem Pfad ·
Textfeld · Auswahlknopfgruppe · Schaltfläche primär/sekundär **ohne** Tastenkappe ·
Tastenzeile (die vier Triage-Tasten) · Fortschrittsbalken mit Beschriftung und zwei Zahlen ·
Meldungsfeld (`warn`, Wortlaut, mehrzeilig) · Marke · Fokusring · Zahlenbilanz.

**Der Triage-Bildschirm in dieser Richtung** (die Zusammenlegung aus 2.1 bleibt):

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Sherlock Holmes · I. A Scandal in Bohemia          7 / 25 · 3 zum Lernen │
├──────────────┬───────────────────────────────────────────────────────────┤
│ BLOCK 1      │                                                           │
│  1 NOUN  pho…│   drawing                                    (60 px)      │
│  2 NOUN  note│   ziehen · blankziehen · herausziehen · zücken (22, accent)│
│  3 VERB  wat…│   Verb · 5× im Kapitel · to pull out, unsheath (14, soft) │
│ ▸7 VERB  dra…│   neue Bedeutung eines bekannten Wortes        (nur wenn) │
│  8 VERB  gla…│                                                           │
│  9 NOUN  bro…│   SO STEHT ES IM KAPITEL                                  │
│    (Bildlauf)│   │ They were admirable things … for drawing the veil …   │
│              │   │ (füllt die Resthöhe, bricht um, wird nie beschnitten) │
├──────────────┴───────────────────────────────────────────────────────────┤
│ K kenne ich   L will ich lernen   S überspringen            Q beenden    │
└──────────────────────────────────────────────────────────────────────────┘
```

Wesentlich daran: Übersetzung **unmittelbar** unter dem Wort (Prüfzeile 5.2), Metazeile als
**eine** Zeile mit einem Trennzeichen (5.3), eigene Zeile für „neue Bedeutung" (5.8),
Belegsatz als das dehnbare Element, Nummern- und Wortartspalte in der Liste (4.1, 4.2), und
eine schmale Fußzeile (rund 40 px statt 96) mit „beenden" **rechts abgesetzt** (B14).
Keine hervorgehobene Taste ohne Zustand (B12) — hervorgehoben wird nur, was Fokus hat.

**Prüfung.** `kontrast.py` wird ersetzt oder erweitert: gemessen wird **im gerenderten
PNG an den Textstellen** (wie in `messen.py` hier), in beiden Themen, in beiden Größen, und
im **ungünstigsten Datenfall** (B24) — längster Belegsatz, alle Etappen offen, Fehlermeldung
sichtbar, leere Liste. Erst dann heißt „0 Paare unter 4,5:1" etwas.

---

## 5. Der Roboter auf dem Triage-Bildschirm

**Entscheidung: Er kommt weg.** Auf dem Fortschritt bleibt er; auf dem Triage-Eintrag nicht.

Begründung, in der Reihenfolge ihres Gewichts:

1. **Er behauptet etwas, das er nicht leistet.** Der Kommentar im Code sagt, die Blase sei
   die Herkunftsangabe: Das Modell habe diese Bedeutung aus der Kandidatenliste des
   Wörterbuchs gewählt. Die Blase sieht aber identisch aus, ob die Bedeutung vom Modell
   kommt, direkt aus dem Wörterbuch stammt oder `uncertain` ist. Genau dort, wo die
   Herkunft zählt — kein Wörterbucheintrag, Regel „das Modell wählt aus einer Liste" —,
   hat der Entwurf keine Variante. Eine Herkunftsangabe, die bei allen Herkünften gleich
   aussieht, ist keine.
2. **Er kostet die zweitwichtigste Zeile ihren Platz.** Die Blase nimmt 80 px Kopf plus 16 px
   Nase; bei 900×600 bricht die Übersetzung dadurch auf zwei Zeilen um, und dieser Umbruch
   ist einer der Gründe, warum der Belegsatz dort aus der Karte läuft (B1). Messbare Kosten,
   kein Informationsgewinn.
3. **Er steht an der falschen Stelle im Ablauf.** Die Triage ist der Ort, an dem **der
   Nutzer** urteilt. Eine Maschine, die ihm die Antwort in einer Sprechblase zuruft, macht
   aus seiner Entscheidung eine Bestätigung — und schiebt sich zwischen Wortform und
   Übersetzung, was Prüfzeile 5.2 ausdrücklich verbietet.
4. **Charme, der sich dreihundertmal wiederholt, ist kein Charme mehr, sondern Möblierung.**
   Pro Kapitel sieht der Nutzer diese Blase mehrere hundert Mal. Beim zwanzigsten Mal ist
   sie ein Rahmen um Text; beim zweihundertsten ist sie der Grund, warum die Zeile nicht
   weiter links anfängt.
5. **Genau deshalb wirkt er auf dem Fortschritt.** Dort ist er einmalig sichtbar, es gibt
   nichts zu entscheiden, die Wartezeit ist echt, und Bewegung sagt etwas Wahres: es läuft
   noch. Ein Wartezeichen mit Gesicht ist die richtige Antwort auf eine Minute Stillstand.

Was an seine Stelle tritt: nichts. Die Übersetzung steht als Text unmittelbar unter dem
Kopfwort, in der Akzentfarbe — das ist, was die Prüfliste verlangt, und es ist die
schnellste Form, die es gibt. Wo die Herkunft wirklich etwas ändert (`uncertain`, kein
Wörterbucheintrag), tritt eine **Marke mit Wortlaut** an die Stelle der Blase, nicht ein
Gesicht.

Empfehlung darüber hinaus: Der Roboter darf ein zweites Mal auftreten, auf dem
**Abschluss**-Bildschirm (Wireframe 7) — einmal, als Punkt am Ende des Kapitels. Zwei
Auftritte, beide an Stellen ohne Entscheidung, machen ihn zur Figur des Programms. Auf jedem
Bildschirm zu stehen, macht ihn zur Tapete.
