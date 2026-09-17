# Kritik der Gestaltungsrichtung „Lesetisch" (Runde 3)

> **Rolle im Bestand.** Dies ist die zweite der beiden Durchsichten aus AP 14
> (bauplan-phase2.md), geführt an der angenommenen Richtung „Lesetisch". `C1` bis `C11`
> sind die **Herkunftsangaben** der Regelkommentare in `gui/qml/Theme.qml` und in
> `tools/design_mockup/qml/*.qml` — siehe den Kopf von `review_round1.md`. Was dauerhaft
> gilt, steht in technik.md §14.
>
> Pfade der Arbeitskopie, übersetzt: `lesetisch/Mock/Theme.qml` → `gui/qml/Theme.qml`,
> `lesetisch/` → `tools/design_mockup/qml/`, `entscheidungen.md` → aufgegangen in
> technik.md §14, `kritik/kritik_runde1.md` → `review_round1.md` daneben.

Beurteilt wurde `scratchpad/design/v1_entwurf/`: die dreißig Renderings in `png/`, die
Token in `lesetisch/Mock/Theme.qml`, der Bauteilsatz in `lesetisch/` und die Begründungen
in `entscheidungen.md`. Zum Vergleich herangezogen: `v0_ausgang/png/` („Glashaus") und
`kritik/kritik_runde1.md`.

**Angesehen wurde am Bild**, alle vier Bildschirme hell und dunkel, bei 1280×800 und bei
900×600, dazu der Bewegungsstreifen `png/_bewegung_hell.png`. Nachgemessen wurde nur dort,
wo das Auge gezweifelt hat; die Skripte dazu liegen in `kritik/r3/`
(`leere.py`, `fl.py`), Ausschnitte als `kritik/r3/z_*.png`. Datum: 17.09.2026.

---

## 1. Urteil

Der Entwurf ist handwerklich eine andere Liga als „Glashaus": Die Flächenhierarchie
stimmt und ist in beiden Themen mit **1,30:1 gleich** (selbst nachgemessen, nicht dem
Werkzeug geglaubt), die drei Textränge haben `opacity` auf Text überflüssig gemacht, die
Liste ist eine echte Tabelle mit Nummern, Wortartspalte und Bildlauf, und der Belegsatz
läuft bei 900×600 nicht mehr aus dem Fenster — die schweren Befunde aus Runde 1 sind
**tatsächlich** abgearbeitet, nicht nur behauptet. Die eine tragende Gestaltungsidee —
**Serif ist Sprachmaterial, Sans ist Programmstimme** — ist im Bild sofort ablesbar und
gibt dem Programm mehr Charakter als jede Farbwahl es könnte. Was fehlt, ist die
**Komposition**: Alle vier Bildschirme sind auf 900×600 gebaut und bei 1280×800 nur
auseinandergezogen — das Eintragsblatt der Triage steht dort zu 40 bis **51 %** leer, der
Fortschrittsbildschirm ist eine halbhohe Karte zwischen zwei Löchern, und in der
Kapitelliste liegen zwischen Titel und Wortzahl **900 px Nichts**. Diese Leere rahmt
nichts, sie ist übrig geblieben; sie ist der Grund, warum der Entwurf bei der Größe, in
der der Nutzer arbeitet, nach Formular aussieht und nicht nach Lesetisch. Zweitens ist der
Charakter auf das helle Thema beschränkt: Hell ist warmes Papier auf einem beigen Tisch,
dunkel ist kühles Blaugrau — strukturell ein Entwurf, in der Stimmung zwei.

---

## 2. Abarbeitung der Kritik aus Runde 1

### Wirklich behoben (am Bild geprüft)

| Befund | Prüfung | Ergebnis |
|---|---|---|
| **B1** Belegsatz sprengt die Karte | `triage_lang_900_hell/dunkel`, 473-Zeichen-Satz | Der volle Satz steht **im** Blatt, nichts ist abgeschnitten, nichts läuft über den Rand. Auch im ungünstigsten Fall (`triage_kette_900_dunkel`: sechsgliedrige Übersetzungskette + Marke + Satz) passt alles. **Behoben.** |
| **B2** Fortschritt verliert die Schaltfläche | `fortschritt_anfang_900_hell/dunkel` | „Esc Abbrechen" steht in beiden Themen im Bild, in einer festen Fußzeile. **Behoben.** |
| **B3** Sieben Textstellen unter 4,5:1 | `lauf.txt`, 30 Bilder, schlechtestes Paar 4,73:1 | Der Befund war nicht die Zahl, sondern das **falsche Grün** des Werkzeugs. `messen.py` geht jetzt den Objektbaum durch und misst im PNG an jeder Textstelle; `opacity` auf Text ist als Regel im Token-Kommentar verboten, und es gibt drei Textränge statt zwei. Das ist die richtige Antwort auf die Ursache, nicht auf das Symptom. **Behoben.** |
| **B4/B16** Flächenhierarchie invertiert, hell ≠ dunkel | eigene Messung in `kritik/r3/fl.py` | L1 zu L0 = **1,30:1 in beiden Themen**, gemessen im gerenderten PNG, nicht aus den Token gerechnet. Es gibt keine vierte Fläche mehr. **Behoben** — mit einem Vorbehalt zur Stimmung, siehe C5. |
| **B5** Bauteilsatz trägt fünf Bildschirme nicht | `lesetisch/` | Bildlauf, Tabellenzeile, Auswahlknopf, Schaltfläche in zwei Rängen mit Zustand „unbedienbar", Balken mit zwei Zahlen, Meldungsfeld, Marke, Fokusring, Zustandszeichen sind gebaut **und stehen in Bildern**. Zwei zusätzliche Bildschirme (Einrichtung, Kapitelwahl) sind der Beweis. **Behoben.** |
| **B6** Spiegelung unter dem Kopfwort | `triage_*` | Ersatzlos weg, die Übersetzung steht unmittelbar unter der Wortform. **Behoben.** |
| **B7** Angaben über drei Orte verstreut | `triage_kette_1280_hell` | Eine Metazeile, ein Trennzeichen, genau drei Angaben; die Marke „neue Bedeutung eines bekannten Wortes" steht auf eigener Zeile und im Wortlaut. **Behoben** — die *Form* der Marke ist neu zu kritisieren (C6). |
| **B9/B10/B11** Wortartpunkte, fehlende Nummern, falscher Nenner | `triage_*` | Vier Spalten mit linker und rechter Kante, Nummer und Häufigkeit in **jeder** Zeile, Wortart als Text. Der zweite Nenner ist durch Wegfall erledigt: Die Liste zeigt alle Einträge und rollt. **Behoben.** |
| **B12** dauerhaft hervorgehobene Taste | `triage_*` | Keine Taste ist gefüllt. Der Fokus liegt sichtbar auf der Liste. **Behoben, und es ist die richtige Wahl.** |
| **B14** 96 px Tastenleiste, „beenden" gleichrangig | `kritik/r3/z_fuss_rechts.png` | 56 px (schmal 40), Tastenkappen nie gefüllt, „Q beenden" rechts abgesetzt in `inkFaint`. **Behoben.** |
| **B15** kein Maßsystem | `Theme.qml` | Rastereinheit 8, sechs benannte Schriftstufen, zwei Gewichte, zwei Familien mit **einer** Regel. Das ist ein System, kein Zahlenvorrat. **Behoben.** |
| **B17** Segmentreihe im Kopf | `triage_*` | Weg; „8 / 25" steht über der Liste. **Behoben.** |
| **B18** Roboterdrehung | `png/_bewegung_hell.png` | Der gesichtslose Abschnitt kommt nicht mehr vor: In keinem Streifenbild ist der Kopf leer, an den Umkehrpunkten bleibt ein Auge als Sichel stehen. Vier unvereinbare Perioden sind die richtige Antwort auf „wiederholt sich ermüdend". **Behoben.** |
| **B24** Mockup zeigt den günstigen Fall | `rendere_alles.py`, 30 Bilder | Der ungünstigste Fall ist zur Regel des Werkzeugs gemacht — alle Etappen offen, längster Satz, Fehlschlag im Wortlaut, Liste mit Bildlauf. Das ist mehr, als der Befund verlangt hat. **Behoben.** |

### Behauptet, aber im Bild nicht eingelöst

- **B14, Teilaussage.** `entscheidungen.md` schreibt, „beenden" sei „getrennt durch eine
  Linie". **Im Bild ist keine Linie**, und im QML (`Triage.qml`, Fußzeile) gibt es auch
  keine — getrennt wird durch Abstand und Schriftfarbe. Die Sache selbst ist in Ordnung,
  die Zeile im Bericht ist es nicht. Für sich `leicht`, als Gewohnheit nicht: Genau so
  entsteht die Liste, die alles besteht und nichts beweist.
- **B8, „`accent` heißt genau eines".** Der Satz steht im Token-Kommentar, das Bild zeigt
  etwas anderes — siehe C6.
- **B16, „hell und dunkel sind ein Entwurf".** Strukturell ja, in der Stimmung nein —
  siehe C5.

### Ausdrücklich nicht gelöst, und zu Recht

Schwebe- und Druckzustand (nicht im Standbild nachweisbar), die drei ungebauten
Bildschirme, der zweite Auftritt des Roboters. Die Begründungen in `entscheidungen.md §8`
tragen; die Selbstauskunft ist ehrlicher als die meisten Berichte dieser Art. **Das bleibt
so und kostet in der letzten Runde keine Minute.**

---

## 3. Was trägt

Das Folgende ist nicht zu verbessern, sondern zu schützen. Wer in der letzten Runde daran
rührt, macht den Entwurf schlechter.

**3.1 Die Schriftregel.** *Serif ist Sprachmaterial, Sans ist Programmstimme.* Sie ist in
einem Satz sagbar, im Bild ohne Erklärung ablesbar und sie ist der ganze Charakter dieses
Entwurfs: `Bohemian`, `unkonventionell`, die Wörter der Liste, der Belegsatz und die
Kapiteltitel stehen in Literata, jede Beschriftung und jeder Zähler in Inter. Der
Unterschied ist bei 14 px **sichtbar** — das war der Vorwurf gegen Cabin/Quicksand, und er
ist erledigt. Diese Regel ist mehr wert als jede Farbe.

**3.2 Das Kopfwort.** 60 px, eine Größe, links an der Kante des Satzspiegels, Zeilenkasten
auf 0,92 gesetzt. Es ist auf jedem der acht Triage-Bilder das Erste, was das Auge findet,
und es ist das Richtige. Der Verzicht auf Spiegelung, Sprechblase und Schmuck hat es
stärker gemacht, nicht schwächer.

**3.3 Die Blockliste.** Vier Spalten, linke und rechte Kante, Nummer rechtsbündig,
Wortart in kleinen Versalien, Wortform in der Buchschrift, Häufigkeit rechts. Der laufende
Eintrag steht immer an derselben Stelle (`preferredHighlightBegin` = 2 × Zeilenhöhe), und
die Begründung im Kommentar — ein angeschnittener Buchstabe sieht aus wie ein
Zeichenfehler — ist genau die Art Detail, die ein Werkzeug von einem Formular
unterscheidet.

**3.4 Die zweite Ebene trägt besser, als der Entwerfer selbst glaubt.** Er hat die
laufende Zeile als schwach eingeräumt. Gemessen ist sie es: L2 zu L1 = 1,17:1 hell und nur
**1,07:1 dunkel**. Im Bild ist sie es **nicht** — weil der Unterschied im Dunklen kein
Helligkeits-, sondern ein **Farbtonunterschied** ist (warmes Braun gegen kühles Blaugrau),
und den misst kein Luminanzverhältnis. Der Ausschnitt `kritik/r3/z_zeile_dunkel.png` zeigt
eine eindeutig markierte Zeile. Dazu kommen Akzentbalken und Fettung. **Hier ist nichts zu
tun**, und die Zeit, die in eine Verstärkung ginge, fehlt anderswo.

**3.5 Der Fehlschlag im Wortlaut.** `warn`/`warnFill` sind neu, und beide
Fehlerbildschirme zeigen die vollständige Meldung samt `<urlopen error [Errno 11001]>` —
nicht „Ein Fehler ist aufgetreten". Dazu der Satz darunter: „Es wurde nichts ins Profil
geschrieben." Das ist Regel 13 des Projekts, gestalterisch umgesetzt.

**3.6 Keine vorausgewählte Taste, Fokus auf der Liste.** Die Oberfläche legt bei keiner
der dreihundert Entscheidungen eine Antwort nahe. Das ist eine inhaltliche Entscheidung,
die richtig getroffen wurde.

**3.7 Die Marke statt des Punktes.** „Eine Marke trägt immer den Text, den sie meint"
(`Tag.qml`) — die Haltung stimmt, nur der Kasten drumherum nicht (C6).

**3.8 Die Bewegung des Roboters.** Umsehen mit Halten an den Enden, Atmen, Blinzeln,
wandernde Zeilen im Brustfenster, vier Perioden ohne gemeinsames Vielfaches. Im Streifen
ist zu sehen, dass der Kopf nie leer ist. Die Figur hat jetzt einen Körper und steht auf
einer Sockellinie statt zu schweben. Das ist besser als in Runde 1 — nur zu klein und am
falschen Ort (C2).

---

## 4. Befunde

### schwer

---

**C1 — Bei 1280×800 ist das Eintragsblatt zur Hälfte leer, und die Leere rahmt nichts.**

*Ort:* `Triage.qml`, das `ColumnLayout` im Eintragsblatt; sichtbar in allen vier
1280er-Triage-Bildern.

*Gemessen* (`kritik/r3/leere.py`, letzte Bildzeile mit Inhalt gegen die Blattunterkante):

| Bild | Inhalt endet | Blatt endet | leer |
|---|---|---|---|
| `triage_kette_1280_hell` | y = 394 | y = 738 | **344 px von 668 — 51 %** |
| `triage_lang_1280_hell` | y = 468 | y = 738 | **270 px von 668 — 40 %** |
| `triage_kette_900_hell` | y = 559 | y = 560 | 1 px — das Blatt ist voll |

*Problem:* Der Bildschirm ist für 900×600 komponiert und bei 1280×800 nur
auseinandergezogen. Der Belegsatz ist zwar `Layout.fillHeight`, aber er füllt die Höhe
nicht, er *darf* sie nur einnehmen — bei einem zweizeiligen Satz steht der ganze Inhalt im
oberen Drittel, und darunter steht ein leeres weißes Feld von einem halben Blatt Größe.
Dieselbe Krankheit an drei weiteren Stellen desselben Bildes: zwischen Buchtitel links und
Kapitelangabe rechts liegen rund 700 px Kopfzeile, zwischen „S überspringen" und „Q
beenden" rund 750 px Fußzeile.

Dazu die Kehrseite der Breite: Der Belegsatz läuft bei 1280 über **rund 90 Zeichen je
Zeile** („My own complete happiness, and the home-centred interests which rise up around
the man who" = 90). Bei 900 sind es 57 — deshalb liest sich das kleine Fenster besser als
das große. Ein Fließtext, den der Nutzer bei jeder von dreihundert Entscheidungen liest,
gehört auf 60 bis 70 Zeichen.

*Wirkung auf den Nutzer:* Das große Fenster — dasjenige, in dem gearbeitet wird — ist das
schlechtere. Das Auge springt nach dem Kopfwort nach unten in ein Loch, und der Satz, der
die Entscheidung begründet, ist am breitesten und damit am langsamsten zu lesen. Leere
trägt nur, wenn sie etwas rahmt; hier rahmt sie nichts, sie ist der Rest einer
Höhenrechnung. Genau das unterscheidet „bestanden" von „gut".

*Schwere:* `schwer`.

---

**C2 — Der Fortschrittsbildschirm ist der leerste des Entwurfs, obwohl er der einzige Ort
ist, an dem Charme erlaubt wäre.**

*Ort:* `Progress.qml`; `fortschritt_lauf_1280_hell`, `fortschritt_anfang_1280_dunkel`,
`fortschritt_fehler_1280_hell`.

*Problem:* Bei 1280×800 steht die Überschrift oben links, darunter **124 px Nichts**, dann
eine 393 px hohe Karte, darunter **143 px Nichts**, dann unten rechts die einzige
Schaltfläche. Drei Ecken, kein Zusammenhang. Innerhalb der Karte liegen zwischen dem
Etappennamen und seinem Zähler rund 550 px Leere; der Roboter — die einzige Figur des
Programms — ist rund 120 px groß, in die rechte Kartenhälfte geschoben und steht neben dem
Hinweissatz statt irgendwo, wo er etwas bedeutet. Im Fehlerfall
(`fortschritt_fehler_1280_hell`) ist das Ergebnis ein 175 px hoher Streifen in einem 800
px hohen Fenster, mit über 600 px Leerraum darum: Das Bild sieht aus, als sei es nicht
fertig geladen.

*Gegenprobe im Verworfenen:* `v0_ausgang/png/fortschritt_hell.png` ist handwerklich
schlechter (Glas, Schatten, Kontraste unter der Schwelle) und **kompositorisch deutlich
besser**: eine mittige Spalte, der Roboter groß obenauf als Bekrönung, darunter die
Etappen, der Balken, die Schaltfläche. Man sieht sofort, worauf man wartet. Der neue
Bildschirm ist an dieser Stelle ein Rückschritt, und das ist der ehrlichste Punkt der
Frage „was ging gegenüber Glashaus verloren".

*Wirkung auf den Nutzer:* Dieser Bildschirm steht Minuten. Er ist das Einzige, was der
Nutzer vom Programm sieht, während es arbeitet, und er sieht dabei aus wie ein Dialogfeld,
das jemand auf einem leeren Schreibtisch vergessen hat. Die Wartezeit fühlt sich länger an,
und die Figur, für die der Auftraggeber ausdrücklich Platz gemacht hat, kommt nicht zur
Wirkung.

*Schwere:* `schwer` (nicht wegen eines Fehlers, sondern weil hier der meiste
Gestaltungsertrag pro investierter Minute liegt).

---

### mittel

---

**C3 — In der Kapitelliste liegen 900 px zwischen dem Titel und seiner Zahl.**

*Ort:* `Chapters.qml` / `ChapterRow.qml`; `kapitel_lang_1280_hell`,
`kapitel_kurz_1280_dunkel`.

*Problem:* „V. THE FIVE ORANGE PIPS" endet bei x ≈ 296, „7.338" steht rechtsbündig bei
x ≈ 1204. Dazwischen: nichts, vierzehnmal untereinander. Bei 900 px Fensterbreite beträgt
derselbe Abstand rund 500 px, und das Bild wirkt prompt deutlich besser
(`kapitel_kurz_900_hell`). Eine Tabelle, die über die volle Fensterbreite gespreizt wird,
zwingt das Auge zu einer Wanderung, für die es keinen Führungsstrich gibt — die klassische
Falle der breiten Tabelle, und der Grund, warum der Bildschirm nach Datenbankmaske
aussieht und nicht nach Inhaltsverzeichnis.

*Wirkung auf den Nutzer:* Die Zuordnung Kapitel → Wortzahl ist die eine Entscheidung
dieses Bildschirms („welches Kapitel bereite ich vor, und wie groß ist es"). Sie ist bei
der Arbeitsgröße am schwersten zu treffen.

*Schwere:* `mittel`.

---

**C4 — Auf dem Fortschritt ist der Fokusring von „Abbrechen" das lauteste Element des
Bildschirms.**

*Ort:* `Progress.qml` mit `FocusRing`; am deutlichsten
`fortschritt_anfang_900_dunkel` und `fortschritt_lauf_1280_hell`.

*Problem:* Das Ringpaar um „Esc Abbrechen" ist ein 2 px starkes Rechteck in `accent` um
eine ohnehin umrandete Schaltfläche. Es ist das größte zusammenhängende Akzentgebilde des
Bildes; die laufende Etappe dagegen wird von einem 16 px kleinen Ring und einer Fettung
getragen. Der Akzent zeigt damit auf **Abbrechen** statt auf *was gerade läuft*.

*Wirkung auf den Nutzer:* Auf einem reinen Wartebildschirm führt die Oberfläche das Auge
zur Abbruchtaste. Das ist die Umkehrung dessen, was `accent` laut Token bedeuten soll
(„hier bist du gerade"), und es macht den Bildschirm unruhig, obwohl nichts zu tun ist.

*Schwere:* `mittel`.

---

**C5 — Hell ist warmes Papier, dunkel ist kühles Blaugrau: ein Entwurf, zwei Stimmungen.**

*Ort:* `Theme.qml`, `ground` / `surface` / `robotShell`.

*Gemessen und im Bild bestätigt:*

| | hell | dunkel |
|---|---|---|
| Grund L0 | `#E3DFD6` — warmes Beige | `#0B0E12` — Blauschwarz |
| Blatt L1 | `#FDFCFA` — warmes Weiß | `#222831` — Blaugrau |
| Gehäuse des Roboters | `#ECE7DE` — Elfenbein | `#39434F` — Stahlgrau |

*Problem:* Das Verhältnis stimmt (1,30:1 in beiden), der **Farbton** nicht. Hell ist der
Name „Lesetisch" eingelöst: ein beiger Tisch, ein cremefarbenes Blatt, eine Lesetype, ein
sepiabraun gedruckter Akzent. Dunkel ist derselbe Aufbau in den Farben einer
Entwicklungsumgebung, und der Akzent kippt von Sepia (`#8F4906`) auf Bernsteingelb
(`#F0A852`). Am deutlichsten am Roboter: hell eine Elfenbeinfigur mit Gesicht, dunkel ein
Stahlklotz, der in der Karte fast verschwindet. Die Entscheidung, den hellen Akzent
dunkler zu nehmen, ist kontrastrichtig und nicht zu kritisieren — die kühle Grundstimmung
des dunklen Themas ist eine freie Wahl, und sie kostet den Charakter.

*Wirkung auf den Nutzer:* Wer dunkel arbeitet — bei einem Werkzeug für abends vor dem
Lesen der wahrscheinliche Fall —, bekommt das charakterlose der beiden Themen.

*Schwere:* `mittel`. Der Aufwand ist gering: Es sind vier Token.

---

**C6 — Die Marke „neue Bedeutung eines bekannten Wortes" sieht aus wie eine Schaltfläche,
und `accent` trägt wieder fünf Bedeutungen.**

*Ort:* `Tag.qml` in `Triage.qml`; `triage_kette_1280_hell`, `triage_kette_900_dunkel`.

*Problem:* Die Marke ist ein abgerundetes Rechteck mit 1-px-Kontur in `accent`, gefüllt
mit 12-px-Halbfettschrift in `accent` — dieselbe Bauform wie `ActionButton` sekundär und
wie die Tastenkappe. Auf einem Bildschirm, der **keine** Maus braucht, steht damit das
einzige klickbar aussehende Ding genau dort, wo etwas zu lesen und nichts zu tun ist.

Dazu der Rückfall in B8: `Theme.qml` schreibt, `accent` bedeute „genau eines". Im Bild
`triage_kette_1280_hell` bedeutet es fünf Dinge gleichzeitig — den Rahmen um die
Seitenliste (Fokus), den Balken und die Tönung der laufenden Zeile, die Übersetzung, die
hervorgehobene Wortform im Satz und diese Marke. Die Übersetzung als „die Antwort" ist
verteidigbar, der Fokusrahmen auch; die Marke ist es nicht — sie sagt nicht „hier bist du
gerade", sondern „achtung, dieses Wort ist anders". Dafür ist `accent` nicht zuständig.

*Wirkung auf den Nutzer:* Die eine Angabe, die eine Entscheidung wirklich ändern kann,
wird als Bedienelement gelesen und deshalb übersprungen — und der Akzent verliert genau
die Schärfe zurück, die Runde 2 ihm gegeben hat.

*Schwere:* `mittel`.

---

**C7 — Der Fokusring um die Seitenliste ist ein dauerhafter Rahmen, der nie etwas Neues
sagt.**

*Ort:* `Triage.qml`, `FocusRing { shown: true; inset: 0 }` um `listSheet`.

*Problem:* Auf dem Triage-Bildschirm kann der Fokus nirgendwo anders hin — es gibt kein
zweites fokussierbares Element. Der Ring ist damit auf jedem der acht Triage-Bilder ein
permanenter bernsteinfarbener Rahmen um das *linke* Blatt, während das rechte, auf das
geschaut wird, nur eine Haarlinie hat. Die Entscheidung dahinter (Fokus auf der Liste, nicht
auf einer Taste) ist **richtig** und bleibt; die Frage ist nur, ob sie jede Sekunde
wiederholt werden muss.

*Wirkung auf den Nutzer:* Der stärkste Rahmen des Bildes umschließt das Nebensächliche und
zieht den Blick nach links weg vom Eintrag. Nach dreihundert Entscheidungen ist der Ring
gelernte Tapete — und damit ist der Fokusring als Mittel verbraucht, bevor ein Bildschirm
kommt, auf dem der Fokus wirklich wandert (Einrichtung).

*Schwere:* `mittel`.

---

### leicht

---

**C8 — Neunzehnmal „3×" untereinander.**
`triage_lang_*`: Die Häufigkeitsspalte ist in der Prüfliste verlangt (4.5) und bleibt —
aber sie steht in derselben Größe und Farbe wie die Nummernspalte, und im Normalfall
(der Block ist nach Häufigkeit sortiert, der Schwanz ist konstant) ist sie eine Säule
identischer Zeichen. Vorschlag ohne Verstoß gegen 4.5: das „×" weglassen oder die Spalte
eine Stufe leiser setzen als die Wortform. `leicht`.

**C9 — Ein Trennzeichen beginnt eine Zeile.**
`triage_kette_900_dunkel`: Die Übersetzungskette bricht als „… Seelenhirt / · Seelenhirte"
um; das Mittelpunktzeichen steht allein am Zeilenanfang. Ein schmales geschütztes
Leerzeichen vor dem Trenner verhindert das. `leicht` — aber es ist genau die Art Detail,
an der ein Leser sieht, ob jemand hingesehen hat.

**C10 — Der Balken läuft weiter, während daneben der Fehlschlag steht.**
`einrichtung_fehler_1280_hell`: Über dem Balken steht „Bezug … fehlgeschlagen", der Balken
zeigt 8,4 von 20,1 MB, und die Schaltfläche heißt „Herunterladen". Dass der Balken in
`warn` eingefärbt ist, rettet die Aussage gerade so; eindeutig ist sie nicht. Ein
„angehalten bei 8,4 von 20,1 MB" wäre es. `leicht`.

**C11 — Der Bericht behauptet eine Linie, die es nicht gibt.**
`entscheidungen.md`, Zeile zu B14. Siehe Abschnitt 2. `leicht`.

---

## 5. Die Arbeitsliste für die letzte Runde

Die nächste Runde ist die letzte, und danach sieht der Auftraggeber das Ergebnis. **Es
sind fünf Punkte, und sie sind in dieser Reihenfolge zu machen.** C1 und C2 allein machen
mehr Unterschied als die anderen neun Befunde zusammen, weil sie das betreffen, was man
sieht, bevor man etwas liest.

**1. C1 — Das Eintragsblatt bei 1280×800 komponieren.** *(der teuerste und der wichtigste
Punkt)*
Zwei Handgriffe, beide klein:
- **Den Belegsatz auf ein Maß setzen:** `Layout.maximumWidth` rund 640 px (bei 18 px
  Literata ≈ 62 Zeichen). Er beginnt weiter nicht bei der linken Kante zu laufen, sondern
  hört früher auf. Der freie Streifen rechts ist dann **Rand**, nicht Rest — und bei
  900×600 ändert sich nichts, weil das Maß dort ohnehin nicht erreicht wird.
- **Aus einem Stapel zwei Gruppen machen:** Kopfwort, Übersetzung, Metazeile und Marke
  bleiben oben verankert; „SO STEHT ES IM KAPITEL" samt Satz wird **nach unten verankert**
  (der Satz wächst nach oben in die Lücke hinein). Dann ist die Leere dazwischen ein
  Abstand zwischen zwei Gruppen und kein abgeschnittenes Ende. Eine Alternative, falls das
  Springen stört: Die Gruppe optisch mittig in das Restfeld setzen (etwa bei 40 % der
  Resthöhe) statt bündig oben.

Bitte bei der Gelegenheit die Kopfzeile schließen: Buchtitel und Kapitelangabe stehen 700
px auseinander; beide linksbündig mit einem Trennzeichen, und die Kapitelangabe rechts nur
dann, wenn sie dort etwas begrenzt.

**2. C2 — Den Fortschrittsbildschirm als eine Spalte setzen und dem Roboter Platz geben.**
Die Etappenkarte auf ein Maß von rund 640 px begrenzen und mittig setzen; die Zähler
**dicht hinter** die Etappennamen statt an den rechten Kartenrand; den Roboter mindestens
verdoppeln (240 px) und ihm einen Ort geben — über der Etappenliste als Bekrönung, wie in
`v0_ausgang/png/fortschritt_hell.png`, oder unten mittig auf seiner Sockellinie, sodass die
Spalte auf ihm endet. Auf diesem Bildschirm darf die Figur groß sein: Sie ist das Einzige,
was hier zu sehen ist, und hier wird nichts entschieden. Das ist der Punkt, der die
verlorene Wärme aus „Glashaus" zurückholt, ohne eine einzige Scheibe.

**3. C5 — Die vier dunklen Token wärmen.** `ground`, `surface`, `hairline`, `robotShell`
vom Blaugrau in Richtung eines warmen Dunkelbraungrau ziehen (etwa `#12100C` / `#26231D` /
`#453F35` / `#3C362C`), 1,30:1 halten und `messen.py` einmal laufen lassen. Zehn Minuten,
und das dunkle Thema heißt danach auch „Lesetisch". **Nicht** die Akzentfarben anfassen —
die sind kontrastrichtig gewählt.

**4. C6 + C4 — Den Akzent wieder schärfen.** Die Marke „neue Bedeutung eines bekannten
Wortes" entkasten: kein Rechteck, sondern ein 3-px-Akzentbalken links und der Text in
`inkSoft` — oder Versalien in `inkSoft` mit dem Balken in `accent`. Sie darf nicht
aussehen wie etwas, das man drückt. Auf dem Fortschritt den Fokusring der Abbruchtaste auf
1 px zurücknehmen oder ganz weglassen (niemand tabbt auf einem Wartebildschirm), damit die
laufende Etappe das stärkste Akzentgebilde des Bildes ist.

**5. C3 — Die Kapitelliste auf ein Maß bringen.** Die Tabelle auf rund 800 px begrenzen
und im Blatt zentrieren, oder die Spalte „WÖRTER" direkt hinter die längste vorkommende
Titelbreite legen. Ein Handgriff, und der Bildschirm sieht bei 1280 so gut aus wie bei 900.

### Was liegen bleibt

Ausdrücklich **nicht** anfassen, auch wenn Zeit übrig ist:

- **Schwebe- und Druckzustand** (B13, Rest) — in einem Standbild nicht beurteilbar, für
  ein Tastaturwerkzeug zweitrangig, und die Begründung des Entwerfers trägt.
- **Die drei ungebauten Bildschirme** — der Bauteilsatz ist der Nachweis, vier Bildschirme
  sind genug für eine Gestaltungsentscheidung.
- **Die laufende Zeile verstärken** — sie trägt (3.4). Eine „Verbesserung" hier macht die
  Liste unruhig.
- **C8 bis C11** — echt, aber klein. Wenn nach den fünf Punkten noch Zeit ist: C9 (das
  geschützte Leerzeichen vor dem Trennzeichen) und C11 (die Zeile im Bericht korrigieren)
  kosten je zwei Minuten. Alles andere nicht.
- **Weitere Messungen.** `lauf.txt` mit 30 Bildern und 0 Befunden reicht. Nach den
  Token-Änderungen genügt ein Durchlauf zur Gegenprobe; neue Prüfskripte sind in der
  letzten Runde vergeudete Zeit.

---

## 6. Was gegenüber „Glashaus" verloren ging — und was nicht

**Verloren, und es ist ein echter Verlust:** der farbige Grund. „Glashaus" hatte einen
blaugrünen Verlauf über dem ganzen Fenster; das war handwerklich falsch (er machte jeden
Flächenkontrast von der Zufallsposition abhängig), aber er gab dem Programm einen **Ort**.
Der neue Grund ist hell ein warmes, ruhiges Beige — das trägt — und dunkel ein neutrales
Blauschwarz, das nichts sagt (C5). Zweitens verloren: die **Komposition** des
Fortschrittsbildschirms, die im alten Entwurf besser war als im neuen (C2).

**Nicht verloren, sondern gewonnen:** Der Charakter steckt jetzt in der Typografie statt
im Material. Ein 60-px-Literata-Wort über einer sepiafarbenen Übersetzung, mit einer
Sans-Metazeile darunter, ist mehr eigener Charakter als ein Glasrahmen, und er hält auch
bei der fünfhundertsten Wiederholung. Die Behauptung des Auftrags — „Glashaus hatte Wärme"
— stimmt für das helle Thema von „Lesetisch" genauso; sie stimmt nur für das dunkle nicht.

**Nicht zurückzuholen:** der Roboter auf dem Triage-Bildschirm. Die Entscheidung aus Runde
1 war richtig und der Entwerfer hat sie richtig umgesetzt. Die Figur gehört dorthin, wo
gewartet wird — und dort gehört sie **groß**.
