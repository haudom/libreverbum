# LibreVerbum — Nacharbeit

> Stand: 21.08.2026 · Befunde aus dem Bau von T3 bis T15, die **nicht** in
> die jeweilige Teilaufgabe gehören. Zwei Arten: Änderungen an den Regeln und der
> Arbeitsweise (Teil A), Nachträge an den Dokumenten aus gemessenen Ergebnissen (Teil B).
>
> Dieses Dokument ist eine Arbeitsliste, kein Entscheidungsdokument. Es begründet nichts
> neu, sondern verweist. Ist ein Punkt abgearbeitet, wird er hier gestrichen; ist die Liste
> leer, fällt die Datei weg.
>
> **Nichts hiervon ist entschieden.** Teil A sind Vorschläge, die eine Zustimmung brauchen,
> weil sie die Hausordnung ändern. Teil B ist unstrittig und nur noch nicht getan.

## Gewichtung

Die Stufen und was beim Einfalten drankommt, stehen in dokumentation.md §9, „Die beiden
Arten werden verschieden behandelt". Kurz:

- **Teil A** trägt eine Stufe. Abgearbeitet werden `schwer` und `mittel`; `leicht` bleibt
  liegen und wird spätestens bei T18 eingefaltet oder gestrichen
- **Teil B** trägt keine, weil dort nichts zurückgestellt wird

**Die Stufe vergibt die kuratierende Stelle, nicht der Melder.** Wer eine Beobachtung
meldet, nennt zwei Tatsachen, die er wirklich kennt: was es ihn gekostet hat, und ob dabei
ein falsches Ergebnis hätte durchgehen können. Wie schwer das für das Projekt wiegt, zeigt
sich erst, wenn mehrere Berichte nebeneinander liegen — dokumentation.md §9.

---

# Teil A — Regeln und Arbeitsweise

## A19 — mittel · Das Review steht in keiner Hausordnung

**Beobachtet (Sitzung 18./19.08.2026).** Sechs Teilaufgaben (T6, T7, T9, T12, T12b, T15)
wurden gebaut, jede mit **grünem Tor** — und jede Durchsicht danach fand Befunde, vier davon
`schwer`:

- **T6:** Fehlt der `Content-Length`-Kopf, entfiel die Längenprüfung ersatzlos; eine halb
  geladene Datei bestand die Schemaprüfung und wäre als gültiges Wörterbuch liegen geblieben
- **T7:** Nichttreffer wurden für beide Kandidatenwege als `uncertain` markiert — rund 23.500
  unsichere Einträge je Kapitel; zugleich war der Eigennamenfilter durch den binären
  Schreibungsvergleich toter Code
- **T12b:** Ein Kapitel kam nach dem Aussteuern **still leer** zurück, ohne Fehler
- **T15:** 213 Wendungen je Kapitel fehlten im Ergebnis; T4 und T7 hatten außerhalb der Tests
  keinen Aufrufer

Alle vier sind **stille** Fehler — genau die Art, gegen die Regel 13 geschrieben ist, und
genau die Art, die vier grüne Befehle nicht sehen. Das Tor prüft **Form** (Format, Regeln,
Typen, Tests laufen); ob das Gebaute das Richtige tut, prüft es nicht. In CLAUDE.md und
dokumentation.md kommt die Durchsicht als Arbeitsschritt gleichwohl **nicht vor** — sie fand
in dieser Sitzung nur statt, weil der Auftraggeber sie angeordnet hat.

**Kosten:** keine, solange jemand daran denkt. Ein falsches Ergebnis wäre in vier Fällen
durchgegangen — jedes davon in einem committeten, grünen Stand.

**Zweiter Beleg (Sitzung 21.08.2026).** T11, T13 und T14 gebaut, jede mit grünem Tor, und
**jede Durchsicht danach fand wieder Befunde** — bei T11 und T13 je einen `schwer`, bei T14
zwei `mittel`, davon einer, der bei jedem echten Lauf zugeschlagen hätte (A25). Damit stützt
sich A19 auf doppelt so viele Fälle wie am 19.08.2026.

**Vorschlag:** Zu entscheiden, ob „Prüfen vor »fertig«“ um die Durchsicht ergänzt wird — mit
dem Zusatz, dass sie **nicht derselbe Bearbeiter** macht, denn drei der vier Befunde lagen
in Annahmen, die der Bauende selbst getroffen und in seinen Tests wiederholt hatte. Das
berührt A8, das dasselbe von der Werkzeugseite her beschreibt.

## A21 — mittel · Gemischte Zeilenenden lassen Verfälschungsproben ins Leere laufen

**Beobachtet (Durchsicht A11/A15, 19.08.2026).** `libreverbum/profile.py` liegt mit CRLF im
Repository, `libreverbum/epub.py` und `tests/test_profile.py` mit LF. Wer für die
Verfälschungsprobe nach dokumentation.md §5 einen Textanker im Quelltext sucht, findet ihn
in der einen Datei und in der anderen nicht — der Prüfende verlor damit einen Durchgang.

**Kosten:** rund fünf Minuten und ein zweiter Anlauf. Ein falsches Ergebnis hätte
durchgehen können: Wer den Fehlschlag als „Anker falsch abgeschrieben" deutet statt als
Zeilenende-Unterschied, hält die Probe für erledigt und den Test für tragfähig, obwohl die
Verfälschung nie gegriffen hat. `git` meldet die Umstellung bei jedem `diff` als Warnung,
was den Unterschied eher verdeckt als zeigt.

**Vorschlag:** Zu entscheiden, ob eine `.gitattributes` mit `* text=auto eol=lf` die
Zeilenenden vereinheitlicht. Das ist eine einmalige Umstellung des ganzen Bestands und
berührt jede Datei — deshalb hier und nicht nebenbei.

## A22 — leicht · Die Skripte in `tools/` brauchen `PYTHONPATH=.`

**Beobachtet (Durchsicht A11/A15, 19.08.2026).** Das Paket `libreverbum` ist in der `.venv/`
nicht installiert. Wer ein Skript aufruft, das den Kern importiert — `ambiguity_check.py`
tut das laut CLAUDE.md ausdrücklich —, braucht `PYTHONPATH=.` und erfährt das erst am
`ModuleNotFoundError`.

**Kosten:** ein Fehlversuch je Bearbeiter. Kein falsches Ergebnis möglich, der Abbruch ist
laut.

**Vorschlag:** Entweder ein Satz in CLAUDE.md unter „`tools/` — die Messskripte", oder
`pip install -e .` in die Umgebung. Zweiteres berührt `pyproject.toml` und die Sperrdatei.

## A23 — mittel · Die Prüfspalte verlangt eine Schnittstelle, die es so nicht geben kann

**Beobachtet (Bau T13, 21.08.2026).** Die Prüfspalte nennt für T13 „GUID **zurückgeben**",
`entities.Card.guid` ist zugleich Pflichtfeld — eine Karte ohne GUID gibt es also nie, und
„zurückgeben" kann sich nicht auf eine fertige Karte beziehen. Die Auflösung — die GUID
entsteht **vor** dem `Card`-Bau, `anki` bietet dafür eine eigene öffentliche Funktion —
steht in keinem Dokument und musste aus der Importregel (technik.md §7) rückwärts abgeleitet
werden.

**Kosten:** eine Ableitung, die im Auftrag hätte stehen können. Ein falsches Ergebnis hätte
durchgehen können: Eine andere Auflösung — etwa die Vergabe innerhalb des Exports — hätte
die Schnittstelle zu T15/T16 anders geprägt, ohne dass ein Test der Teilaufgabe das als
falsch markiert hätte.

**Vorschlag:** Zu entscheiden, ob die Prüfspalte dort, wo sie eine Schnittstelle zwischen
zwei Teilaufgaben berührt, deren Form mitnennt — oder ausdrücklich sagt, dass die bauende
Teilaufgabe sie bestimmt. Dieselbe Wurzel wie A24, und dieselbe Lesart der Prüfspalte wie
A7 (eingefaltet am 19.08.2026).

## A24 — mittel · Zwei Teilaufgaben mussten die Datenform ihrer eigenen Eingabe erfinden

**Beobachtet (Bau T13 und T14, 21.08.2026).** Kein Dokument legt fest, was `anki` und
`printout` als Eingabe bekommen. T14 hat sich für `Sequence[tuple[Occurrence, Sense]]` statt
`Sequence[Card]` entschieden — eine Schnittstellenentscheidung, die sich aus keiner Regel
und keinem Test ableiten lässt.

**Kosten:** je Teilaufgabe eine eigene Festlegung. Ein falsches Ergebnis ginge in beide
Richtungen unbemerkt durch: T15 verkettet die Schritte (technik.md §7, „Die Importregel")
und findet dort zwei Module mit unvereinbaren Eingaben vor, ohne dass eine der beiden
Teilaufgaben je rot gewesen wäre.

**Vorschlag:** Zu entscheiden, wo die Form der Schrittgrenzen festgehalten wird. Die
Modulkarte nennt Zuständigkeiten und ausdrücklich keine Entwürfe (technik.md §7, „Warum eine
Karte und nicht mehr"), Regel 14 verbietet Vorratsarbeit — die Lücke ist also gewollt, ihre
Wirkung aber erst jetzt sichtbar.

## A25 — schwer · Welche Felder auf der Druckseite stehen, legt kein Dokument fest

**Beobachtet (Bau und Durchsicht T14, 21.08.2026).** Für den Anki-Export nennt konzept.md
sieben Felder ausdrücklich (Schritt 6, „Export"), für die Druckseite keines. T14 hat die
schmalste Zeile gewählt, die die Abnahmekriterien erfüllt; die Durchsicht meldete daraufhin
die fehlende **Wortart** als Befund — zwei Drittel der Grundformen eines Kapitels sind
mehrdeutig (technik.md §3, „Nachtrag 18.08.2026: zwei Drittel der Grundformen eines Kapitels
sind mehrdeutig").

**Kosten:** ein Befund und eine Nacharbeit. Ein falsches Ergebnis wäre durchgegangen, und
zwar das teuerste: Wer auf dem Blatt eine Grundform ohne Wortart liest, hängt die
Übersetzung an die falsche Lesart — der stille Fehler, gegen den der ganze Hybrid-Ansatz
gebaut ist (konzept.md, Schritt 5). Bemerken kann der Nutzer ihn nicht, er kennt das Wort ja
gerade nicht.

**Vorschlag:** Zu entscheiden, ob konzept.md die Felder der Druckseite ebenso benennt wie
die der Karte. Das ist eine Konzeptaussage und keine Berichtigung — deshalb Teil A.

## A26 — leicht · schnell · Eine Verfälschungsprobe erwies sich erst beim Ausführen als untauglich

**Beobachtet (Bau T13, 21.08.2026, Befund 4).** Für den Lückentext war als Verfälschung ein
naiver `\b`-Regex vorgesehen, die naheliegendste falsche Umsetzung. Ausgeführt trifft sie
`don't` **korrekt**, weil Python die Wortgrenze nur an den äußeren Rändern des Treffers
prüft; der Test wäre gegen sie nie rot geworden. Gefunden allein durch tatsächliches
Ausprobieren.

**Kosten:** ein Durchgang. Ein falsches Ergebnis hätte durchgehen können, wenn die Probe für
plausibel gehalten statt ausgeführt worden wäre — dann gälte ein Test als geprüft, der nie
rot war.

**Vorschlag:** Der Fall belegt die bestehende Regel, statt sie zu ändern — „Womit zu
verfälschen sei, ist eine Vermutung und kein Auftrag" (dokumentation.md §5, „Ein Test gilt
erst als Test, wenn er einmal rot war"). Zu entscheiden ist nur, ob er dort als Beispiel
danebentritt.

## A27 — mittel · Für die Blattkapazität gab es kein Werkzeug in der Umgebung

**Beobachtet (Durchsicht T14, 21.08.2026).** Die Messung zu Abnahmekriterium 5 brauchte
echte Schriftmetrik; in `.venv/` liegt weder PIL noch `fontTools`. Die Arial-Metrik musste
ein Wegwerfskript liefern.

**Kosten:** rund ein Drittel der Prüfzeit, und dasselbe noch einmal für jeden, der die Zahl
nachrechnet. Ein falsches Ergebnis hätte durchgehen können, weil die Werte in technik.md
§8c, „Gemessene Ergebnisse: »passt auf ein Blatt« ist gedeckt" als einzige nicht aus
`tools/` reproduzierbar sind — wogegen CLAUDE.md von den Messskripten ausdrücklich sagt, sie
reproduzierten die Messungen, auf die sich technik.md stützt.

**Vorschlag:** `tools/print_check.py` neben die anderen Messskripte. Für einen einzelnen
Befund war es nach Regel 14 nicht gerechtfertigt; zu entscheiden ist, ob die
Reproduzierbarkeit eines Messwerts der zweite Anwendungsfall ist.

> **Am 19.08.2026 eingefaltet und gestrichen:** A7 (die Prüfspalte nennt beide Wege —
> bauplan.md, „Was die Reihenfolge bestimmt", dazu die berichtigte T4-Zeile; nicht in zwei
> Teilaufgaben getrennt, weil T4 gebaut ist) · A8 (das Tor für Prüfende — CLAUDE.md,
> „Prüfen vor »fertig«") · A9 und A16 (die Verfälschungsprobe — dokumentation.md §5) ·
> A10 (der ungeprüfte EPUB-3-Zweig — technik.md §8, offener Punkt) · A12 (nachgemessen,
> betrifft nur das Vorspanndokument — keine Änderung) · A13 und A14 (bei T16 zu
> entscheiden — bauplan.md, T16-Zeile) · A17 (die Rohquelle bei Regel 15 —
> dokumentation.md §4) · A18 (die berichtigte Kurzfassung — dokumentation.md §7) ·
> A20 (beide Indizes liegen seit dem 19.08.2026 auf `tools/en-de.sqlite3`, ein
> Nachschlagevorgang 21,4 ms → 0,49 ms) · A11 und A15 (gebaut, durchgesehen und
> committet — `_text_of` nimmt den ersten nichtleeren Treffer, `open_profile` meldet
> das fehlende Verzeichnis deutsch).

> **A6 gestrichen am 17.08.2026** (Parallelität erzeugt Phantomfehler): als Absprache
> erledigt, der Dokumentteil ist in A8 aufgegangen.

---

# Teil B — Nachträge an den Dokumenten

**Leer.** B4 bis B9 sind am 19.08.2026 eingefaltet — nachzulesen in technik.md §2 („Warum
diese Quelle"), §3 („Zweite Datenfalle: Zeilen ohne `lexentry`"), §4 („Tabellen im
Überblick"), §5 („Nachtrag 17.08.2026: nur fünf Wortarten kommen in die Wortliste") und
„Messung: Mehrwortausdrücke" („Nachtrag 19.08.2026: die Maße beider Wege").

Drei der dort genannten Zahlen ließen sich beim Einfalten **nicht reproduzieren** und
wurden gegen `tools/en-de.sqlite3` und `tools/sherlock.txt` neu gemessen; die Schlüsse
haben sich dadurch nicht geändert. Die eingefaltete Fassung nennt jeweils Messdatum und
Abgrenzung mit, damit derselbe Fall nicht wiederkehrt.
