# LibreVerbum — Nacharbeit

> Stand: 19.08.2026 · Befunde aus dem Bau von T3 bis T15, die **nicht** in
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

## A7 — mittel · Die T4-Zeile im Bauplan ist zweideutig

**Beobachtet (Review T4, 17.08.2026).** „zusammenhängende Kandidatenfolgen **und** getrennte
Verb-Partikel-Paare aus der Abhängigkeitsanalyse" lässt sich als „beides aus der Analyse"
lesen, während technik.md §3, „Arbeitsteilung nach der Messung" die zusammenhängenden
ausdrücklich „Wörterbuch + n-Gramm + Filter" zuordnet. Die Prüfspalte nennt dann nur den
getrennten Fall — wer sie als Auftragsumfang liest, baut folgerichtig die Hälfte.

**Kosten:** eine vollständige Reviewrunde plus Nachbesserung. Ein falsches Ergebnis wäre
durchgegangen: 190 von 232 zusammenhängenden Wendungen eines Kapitels entstanden nie, rund
3 % des Mehrwortbestands waren erreichbar — ohne Fehler und ohne Meldung. T7 hätte die
fehlenden Kandidaten nicht vermissen können.

**Vorschlag:** Wo eine Teilaufgabe zwei Wege verlangt, nennt die Prüfspalte **beide**. Zu
entscheiden, ob die T4-Zeile zusätzlich in zwei Teilaufgaben getrennt wird.

## A8 — mittel · Das Tor ist auf den Bauenden geschrieben, nicht auf den Prüfenden

**Beobachtet (Review T8, 17.08.2026).** `ruff format .` und der volle `pytest`-Lauf sind für
einen Prüfer unbrauchbar, solange ein zweiter Bearbeiter im Arbeitsbaum steht: Das erste
formatiert fremde Arbeit mit, das zweite zeigt Rot, das dem anderen gehört — in derselben
Sitzung vorgeführt, vier rote Tests in `test_extraction.py`, Minuten später von selbst grün.
„Grün" ist bei zwei Bearbeitern nur je Datei eine Aussage.

**Vorschlag:** Im Tor aus CLAUDE.md festhalten, dass Prüfende `ruff format --check` und den
dateiweisen Testlauf nehmen; den vollständigen Lauf macht die verkettende Stelle zwischen den
Runden. Das ist die Dokumentfassung des gestrichenen A6, das dasselbe nur als Absprache hielt.

## A9 — leicht · Unversionierte Dateien haben beim Verfälschen kein Netz

**Beobachtet (Review T8, 17.08.2026).** Die Verfälschungsprobe nach dokumentation.md §5 setzt
voraus, dass der Ausgangsstand wiederherstellbar ist. Bei einer noch unversionierten Datei
gibt es dafür kein Git, und `Path.write_text` verwandelte beim Wiederherstellen unter Windows
LF in CRLF — gezeigt hat es allein der Hash-Vergleich, nicht der Augenschein.

**Vorschlag:** Ein Satz in dokumentation.md §5 — wer an einer unversionierten Datei
verfälscht, sichert sie binär und prüft die Wiederherstellung per Hash.

## A10 — leicht · Der EPUB-3-Zweig wird an keiner Fremdquelle geprüft

**Beobachtet (Review T12, 18.08.2026).** In `tools/` liegen nur `sherlock.epub` und
`dorian_gray.epub` — beide EPUB 2.0 mit `toc.ncx` und ohne `nav.xhtml` (nachgeprüft). Der
gesamte EPUB-3-Pfad in `libreverbum/epub.py` (`_read_nav`, `properties="nav"`,
`epub:type`) läuft deshalb nur gegen die selbstgebaute Vorrichtung, nie gegen ein echtes
Buch — genau die Konstellation, vor der dokumentation.md §5 warnt („Die Vorrichtung zeigt,
dass der Code läuft; die Fremdquelle zeigt, ob er stimmt").

**Vorschlag:** keine Codeänderung. Optional der Hinweis an den Nutzer, eine EPUB-3-Datei
aus seinem Bestand nach `tools/` zu legen (laut technik.md §8 sind die beiden dort
gemessenen Manga-Bände 3.0); die Marke `needs_epub` müsste dann um sie erweitert werden.

## A11 — leicht · `_text_of` nimmt nur den ersten Treffer

**Beobachtet (Review T12, 18.08.2026).** `_text_of` in `libreverbum/epub.py` liest mit
`root.find` nur das erste `dc:title` beziehungsweise `dc:creator`. Ist das erste `dc:title`
leer (kommt bei Konvertaten vor, die ein leeres `dc:title` voranstellen und den echten
Titel als zweites führen), bricht `read_structure` mit „nennt keinen Titel" ab, obwohl die
Datei einen hat. Bei mehreren `dc:creator` (Ko-Autoren, Übersetzer) fallen die weiteren
still weg.

**Vorschlag:** `findall` statt `find`, den ersten nichtleeren Text nehmen. Für
`dc:creator` genügt dasselbe — mehrere Autoren zusammenzuführen wäre Vorratsarbeit
(Regel 14), `entities.Book.author` ist ein einzelnes Feld.

## A12 — leicht · `td` und `hr` fehlen in `_BLOCK_TAGS`

**Beobachtet (Review T12b, 18.08.2026).** Die Auswahl in `libreverbum/epub.py`
(`_BLOCK_TAGS`) entspricht exakt `tools/epub_check.py:73-76`, das ist gewollt und richtig.
Wirkung an den echten Dateien: Sherlocks Inhaltsverzeichnis steht in einer Tabelle mit zwei
Zellen je Zeile, deren Text zusammenläuft („I." + Titel). Das betrifft nur das
Vorspanndokument, keinen Erzähltext — Abnahmekriterium 2 ist nicht berührt. Absatzgrenzen
im Erzähltext sind sauber: 2.529 bzw. 1.504 `<p>`, alle mit Umbruch (nachgemessen).

**Vorschlag:** keine Codeänderung nötig. Falls doch angefasst, dann in
`tools/epub_check.py` mitziehen, damit Vorlage und Kern nicht auseinanderlaufen.

## A13 — mittel · Zusammenführen von Einzelwörtern und Wendungen ist offen (gehört zu T16/T17)

**Beobachtet (Review T15, 18.08.2026).** `pipeline.run_chapter` liefert seit der Behebung
von Befund 1 Einzelwörter (`entries`) und Mehrwortausdruck-Kandidaten (`expressions`)
nebeneinander, nicht zu einer gemeinsamen Liste zusammengeführt: Wie eine Wendung und die
Einzelwörter, aus denen sie besteht, bei Überschneidung zueinanderstehen sollen (`give up`
neben `give` und `up`) — Reihenfolge, Vorrang —, ist eine inhaltliche Frage, die Regel 14
hier nicht auf Vorrat entscheidet. Gemessen an Kapitel 13 (Sherlock, 52.801 Zeichen): 213
verschiedene Wendungen, keine davon als Einzelwort erfasst — ein Achtel des Wortschatzes,
das in der Triage (T16) sichtbar werden und bei der Abnahme (T17, Abnahmekriterium 3:
„mindestens … zwei Redewendungen") auffindbar sein muss.

**Vorschlag:** Bei **T16** entscheiden, wie `entries` und `expressions` in der
Triage-Liste zueinanderstehen; **T17** braucht daraus mindestens zwei Redewendungen in der
Handstichprobe für Abnahmekriterium 3.

## A14 — leicht · Tippfehler im Profilpfad legt wortlos ein leeres Profil an (gehört zu T16)

**Beobachtet (Review T15, 18.08.2026).** `profile.open_profile` legt für einen nicht
vorhandenen Pfad wortlos eine neue, leere Profildatei mit allen sieben Tabellen an
(geprüft). Ein Tippfehler im Profilpfad, den `pipeline.run_chapter` entgegennimmt, fiele
deshalb nicht auf — beim zweiten Durchlauf stünde wieder alles auf `UNKNOWN`, genau das
Bild, das Abnahmekriterium 6 als Fehlschlag beschreibt, nur ohne jede Meldung.

**Zuständig ist der Aufrufer** (technik.md §9, der Kern kennt keine Vorgabe), fällig also
erst bei **T16**: Der Pfad kommt aus `config.toml`, dort gehört die Entscheidung hin, ob
ein noch nicht vorhandenes Profil bestätigt werden muss.

## A15 — leicht · Fehlendes Profilverzeichnis meldet auf Englisch (gehört zu T8)

**Beobachtet (Review T15, 18.08.2026).** Ein Profilpfad in einem nicht vorhandenen
Verzeichnis ergibt in `profile.open_profile` `sqlite3.OperationalError: unable to open
database file` — sichtbar (Regel 13 erfüllt), aber eine englische Fremdmeldung entgegen
dokumentation.md §1. `dictionary.ensure_index` löst denselben Fall vorbildlich mit einer
deutschen Meldung.

**Vorschlag:** in `profile.open_profile` dieselbe Umhüllung wie in `ensure_index`. Gehört
zu **T8**, nicht zu T15 — `profile.py` ist dessen Modul.

## A16 — mittel · Eine grün gebliebene Verfälschungsprobe heißt: die Zusicherung ist zu schwach

**Beobachtet (Sitzung 18./19.08.2026, vier Fälle in vier Teilaufgaben).** Die Regel aus
dokumentation.md §5 verlangt, dass ein Test einmal gegen eine absichtlich falsche Umsetzung
rot war. Sie sagt nicht, was zu tun ist, wenn er dabei **grün bleibt** — und das ist keine
Ausnahme, sondern trat in dieser Sitzung viermal ein:

- **T9:** Das Streichen von `, e.id` aus `ORDER BY` blieb wirkungslos, weil SQLite bei
  Gleichstand faktisch in Einfügereihenfolge sortiert. Rot wurde der Test erst, als die
  Tie-Break-Richtung umgekehrt wurde
- **T12:** „fehlende Datei ergibt `FileNotFoundError`“ bestand auch ohne den eigenen Check,
  weil `zipfile.ZipFile` denselben Fehlertyp wirft — geschärft auf den Meldungstext
- **T12b:** Die Vorrichtung für die Absatzgrenzen trennte die beiden `<p>` bereits durch
  einen Zeilenumbruch im Quelltext und prüfte den Mechanismus damit gar nicht
- **T15:** Die Behebung des einen Befunds machte den Test eines anderen wirkungslos, weil
  der neue Aufrufpfad denselben Fehler vorher abfing

Dreimal wäre ein Test entstanden, der aussieht wie eine Zusicherung und keine ist.

**Kosten:** je Fall fünf bis fünfzehn Minuten. Ein falsches Ergebnis wäre **nicht** sofort
durchgegangen, aber die Prüfung wäre dauerhaft wirkungslos im Repository gelandet — und
genau das entdeckt später niemand mehr, weil ein grüner Test nicht auffällt.

**Vorschlag:** Ein Satz in dokumentation.md §5: Bleibt der Test bei der Verfälschung grün,
ist die **Zusicherung zu schwach**, nicht die Verfälschung falsch gewählt — dann wird die
Behauptung geschärft (Meldungstext statt Fehlertyp, unterscheidende Vorrichtung), nicht eine
andere Verfälschung gesucht. Zweiter Satz: Der Vorschlag eines Prüfenden, *womit* zu
verfälschen sei, ist eine Vermutung und kein Auftrag — der T9-Fall kam aus einem Review.

## A17 — schwer · Lizenzangaben nach Regel 15 nur aus der Rohabfrage

**Beobachtet (Vorbereitung E8b/E8c, 18.08.2026).** Beim Abrufen von Webseiten wurden Angaben
**erfunden**, wo sie im Auszug fehlten: ein Freigabedatum für eine Paketfassung und eine
angebliche Fehlermeldung zu einer Bibliothek, die das fragliche Paket gar nicht verwendet.
Aufgefallen ist es nur, weil der Bearbeiter beides per Rohabfrage (`curl` auf die
JSON-Schnittstelle) gegengeprüft hat.

**Kosten:** zwei Gegenprüfungen. Ein falsches Ergebnis hätte durchgehen können — und hier
wiegt das schwerer als anderswo: **Regel 15 ist eine harte Regel**, die Lizenzprüfung
entscheidet über Aufnahme oder Ausschluss einer Bibliothek. Eine erfundene Lizenzangabe ist
nicht auffällig, sie sieht aus wie jede andere. Der Prüffall dieser Sitzung war das
offizielle `anki`-Paket, dessen tatsächliche AGPL-3.0-Angabe zum Ausschluss führt.

**Vorschlag:** In dokumentation.md §5 oder bei Regel 15 festhalten: Für Lizenz-, Fassungs-
und Pflegeangaben ist die **maschinenlesbare Rohquelle** verbindlich (Paketverzeichnis-JSON,
Lizenzdatei im Ursprungsbestand), nicht die Zusammenfassung einer abgerufenen Seite. Was in
die Dokumente wandert, nennt die Quelle mit.

## A18 — mittel · Eine berichtigte Kurzfassung ist ganz zu prüfen, nicht nur an der gemeldeten Stelle

**Beobachtet (18./19.08.2026, zwei Anläufe).** Der Kernablauf-Satz in CLAUDE.md war nach
Entscheidung 10 an **zwei** Stellen falsch: die Triage stand vor dem Beschaffen der
Bedeutungen, und der Profilabgleich stand davor statt danach. Der erste Korrekturlauf
(`4cbeb40`) richtete nur die erste Stelle, weil nur sie gemeldet worden war. Die zweite
führte danach noch **zwei** Bearbeiter in die Irre — den T15-Bau und den Auftrag an ihn —
und wurde erst mit `95ca04b` gerichtet.

**Kosten:** rund zwanzig Minuten Dokumentenabgleich beim T15-Bau, dazu ein zweiter
Korrekturlauf. Ein falsches Ergebnis war nahe: Der Bearbeiter hätte die Reihenfolge aus dem
Auftrag übernehmen können statt aus konzept.md — sie wäre technisch nicht ausführbar gewesen,
der Fehler also aufgefallen, aber erst beim Programmieren.

**Vorschlag:** Zu dokumentation.md §7 („Korrigieren: Nachtrag oder überschreiben“) ein Satz:
Wird eine **Kurzfassung** berichtigt, die eine Entscheidung zusammenfasst, ist sie als Ganzes
gegen die Quelle zu prüfen — eine Kurzfassung fasst mehrere Festlegungen in einem Satz, und
wer nur die gemeldete Hälfte richtet, lässt die andere als Falle stehen.

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

**Vorschlag:** Zu entscheiden, ob „Prüfen vor »fertig«“ um die Durchsicht ergänzt wird — mit
dem Zusatz, dass sie **nicht derselbe Bearbeiter** macht, denn drei der vier Befunde lagen
in Annahmen, die der Bauende selbst getroffen und in seinen Tests wiederholt hatte. Das
berührt A8, das dasselbe von der Werkzeugseite her beschreibt.

## A20 — leicht · `tools/en-de.sqlite3` trägt keinen Index

**Beobachtet (18.08.2026, an fünf Stellen aufgelaufen).** Die Wörterbuchdatei im
Arbeitsverzeichnis hat **null** Indizes; eine Abfrage gegen `translation(written_rep)` kostet
dort einen vollen Scan (gemessen: 490 s für einen Kapitellauf, gegen 1,1 s mit Index —
technik.md §3, „Nachtrag 17.08.2026“). `dictionary.ensure_index` aus T6 legt ihn an, ist auf
dieser Datei aber nie gelaufen: Sie wurde von Hand hinterlegt, nicht über `fetch_dictionary`
bezogen.

**Kosten:** Jeder Bearbeiter, der gegen die echte Datei misst oder `needs_dictionary`-Tests
schreibt, musste sich eine indizierte **Kopie** anlegen — in dieser Sitzung fünfmal
unabhängig voneinander.

**Vorschlag:** Keine Regeländerung. Einmalig `dictionary.ensure_index` auf
`tools/en-de.sqlite3` laufen lassen; danach entfällt der Umweg. Die Entscheidung liegt beim
Auftraggeber, weil es seine Datei ist — der Index verändert sie (er wächst um einige MB),
und beide Indexnamen stehen seit T7 im Code.

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
