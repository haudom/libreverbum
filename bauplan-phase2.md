# LibreVerbum — Bauplan Phase 2

> Arbeitsdokument für Phase 2 („Ausbau der Kernidee", [konzept.md](konzept.md),
> „Phasenplan"). Es zerlegt die Phase in Arbeitspakete, die je ein bauender Agent (Sonnet)
> kalt aus den Dokumenten heraus umsetzen kann, und sagt, was nacheinander und was
> nebeneinander laufen darf. Wie `bauplan.md` in Phase 1 fällt es am Tor der Phase weg; was
> dauerhaft gilt, wandert vorher in konzept.md, technik.md und dokumentation.md.
>
> **Stand: 15.09.2026.** E1 bis E4 aus Abschnitt 1 sind entschieden (Datum je Punkt dort;
> Begründung in technik.md §14) — der Plan ist damit Auftrag.

Herkunftsangabe im Quelltext: `bauplan-phase2.md AP 7` — nach dem Muster `bauplan.md T13`
(CLAUDE.md, „Die Dokumente und ihre Zuständigkeit"). Die Nummern der Phase 1 (T1 bis T18)
werden nicht fortgesetzt, damit keine Herkunftsangabe auf die falsche Datei zeigt.

---

## 0. Wie dieses Dokument benutzt wird

- **Ein Arbeitspaket (AP) ist ein Auftrag.** Ein Sonnet-Agent baut, lässt das Tor laufen
  (CLAUDE.md, „Prüfen vor »fertig«"), committet nur die eigenen Dateien; ein Opus-Agent sieht
  gegen `git archive <commit>` durch (dokumentation.md §10); Befunde `schwer` und `mittel`
  bessert ein Sonnet-Agent als eigenen Commit nach. Die Hauptsitzung legt die
  Beobachtungen jedes Berichts sofort unter `beobachtungen/` ab (dokumentation.md §9).
- **Der Auftrag entsteht aus dem AP-Text plus der Vorlage in Abschnitt 6.** Der AP-Text
  nennt Ziel, Form der berührten Schnittstellen, Dateien und Prüfung; die Vorlage trägt die
  Hausordnung bei. Beides zusammen muss für einen Kaltstart genügen.
- **Ein AP berührt höchstens eine Handvoll Dateien** und ist in einer Sitzung eines
  Sonnet-Agenten zu schaffen (Größe S = wenige Stunden, M = eine Sitzung, L = an der Grenze,
  wird im Zweifel geteilt). Was hier L heißt, ist bereits geteilt.
- **Höchstens zwei Agenten zugleich, davon höchstens ein Opus** — und zwei Bauende nur auf
  disjunkten Dateien (CLAUDE.md, „Aktueller Stand"). Abschnitt 5 nennt für jedes AP, womit
  es sich verträgt.

---

## 1. Entscheidungen vor der ersten Zeile Code

Je Punkt: die Frage, die Wahlmöglichkeiten, die Empfehlung samt Begründung. **E1 bis E4
blockieren den Start**; die übrigen haben eine Vorgabe, mit der gebaut wird, falls nichts
anderes entschieden wird. Was entschieden ist, wandert mit Datum in technik.md (neuer
Abschnitt 14 ff.), nicht hierher.

### E1 — Oberflächentechnik: Qt Quick beibehalten oder Web-Hybrid?

**Entschieden 15.09.2026: Qt Quick über PySide6 bleibt.** Begründung und was verworfen
wurde: technik.md §14.

technik.md §1 hat am 11.08.2026 **Qt Quick über PySide6** entschieden und den
Web-Hybrid ausdrücklich nur nach Aufwand, nicht nach Möglichkeit abgelehnt („Warum kein
Zwei-Sprachen-Aufbau"). Die Recherche vom 15.09.2026 (`recherche_hochwertige_UIs_mit_
Claude.md`) bringt ein Argument, das damals nicht auf dem Tisch lag: **Die Werkzeuge, mit
denen Claude gute Oberflächen baut, sind für Web-Frontends (React, Tailwind, shadcn,
Browser-MCP) am dichtesten; für Desktop-Oberflächen ist die Erfahrung „spürbar
schlechter".** Qt/QML kommt in der Recherche gar nicht vor.

| | Qt Quick (Stand) | Web-Hybrid (Kern + lokaler HTTP-Dienst + React) |
|---|---|---|
| Übernahme aus der Recherche | **Stufe 1 vollständig**: Gestaltungsrichtung und Token-System sind technikneutral; die Screenshot-Schleife läuft über Qts eigenes `grabWindow()` nach PNG, das der Agent ansieht. Stufe 2/3 (shadcn, Storybook, Figma) entfällt | Stufe 1 bis 3 wörtlich; Browser-Werkzeug dieser Sitzung direkt nutzbar |
| Was es kostet | Sonnet kennt QML schlechter als React → mehr Durchsichtsrunden; keine Komponentenbibliothek, Controls sind selbst zu gestalten | zweite Werkzeugkette (Node ist auf diesem Rechner **nicht** installiert), Prozessgrenze quer durch die Anwendung, Auslieferung als Desktop-App wird ein eigenes Projekt (pywebview/Tauri), Umkehr einer dokumentierten Entscheidung |
| Was es hält | „Python als einzige Sprache", offline, Desktop für Windows und Linux, das am Zeiger klebende Schiebemenü (§1) | Gestaltungsfreiheit, dichteste KI-Werkzeuge |

**Empfehlung: Qt Quick beibehalten** und die Stufe-1-Empfehlungen der Recherche
übernehmen (Abschnitt 7). Begründung: Alles, was die Recherche als *wirksamsten Hebel*
nennt — explizite Gestaltungsrichtung, Token statt Zufall, Screenshot-Prüfschleife,
Bau/Prüf-Trennung — ist mit Qt zu haben; was fehlt, ist Komfort, nicht Qualität. Der
Hybrid kaufte diesen Komfort mit einer zweiten Laufzeitumgebung und einer neuen
Auslieferungsfrage. Die Tür bleibt offen wie bisher: Der Kern kennt die Oberfläche nicht,
und die Anwendungsschicht aus E4 wäre auch für einen HTTP-Dienst die richtige Stelle.

Wer hier anders entscheidet, ersetzt Block C (Abschnitt 4) — Block B, das Fundament und
die Abnahmekriterien bleiben unverändert. Genau dafür ist der Plan so geschnitten.

### E2 — Ein eigener Zweig für Phase 2

**Entschieden 15.09.2026: Zweig `phase-2`, kein Push.** Begründung: technik.md §14.

Wunsch vom 15.09.2026: ein Zweig, damit die funktionierende Kommandozeile der Phase 1 auf
`main` leicht verfügbar bleibt. Das ist sinnvoll, weil Block A die Kommandozeile
**umbaut** (Export-Verkettung in den Kern, Anwendungsschicht herauslösen) und Block B den
Kern erweitert — beides berührt `cli/`.

**Vorgabe:** Zweig `phase-2`, alle Commits der Phase dorthin, kein Push. `main` bleibt bis
zum Tor der Phase 2 der abgenommene Stand der Phase 1 und wird dort per Fast-Forward
nachgezogen. CLAUDE.md, „Arbeitsweise" („Auf `main` und ohne zu pushen") wird in AP 0
entsprechend geändert; die Durchsicht gegen `git archive <commit>` funktioniert auf jedem
Zweig unverändert. Der alte Zweig `language-rule-rollout` (12.08.2026, vollständig in
`main` enthalten) kann bei der Gelegenheit gelöscht werden.

### E3 — Rolle der Kommandozeile in Phase 2

**Entschieden 15.09.2026: eingefroren, mit den Ausnahmen `--chapters` und `--assess`.**
Begründung: technik.md §14.

Bekommt `cli/` jede neue Funktion ebenfalls, oder bleibt sie der Zugang der Phase 1, der
nur weiter **funktioniert**?

**Empfehlung: eingefroren, mit zwei Ausnahmen.** Die Kommandozeile bleibt lauffähig (alle
ihre Tests bleiben grün, Kernänderungen werden dort nachgezogen), neue Bedienung entsteht
in `gui/`. Ausnahmen, wo die Kommandozeile das billigere Prüfgeschirr für eine Kernfunktion
ist: `--chapters` (AP 5) und `--assess` (AP 7). Alles andere doppelt gebaut hieße, jede
Bedienentscheidung zweimal zu treffen.

### E4 — Eine gemeinsame Anwendungsschicht `app/`

**Entschieden 15.09.2026: drittes Paket `app/` neben `cli/` und `gui/`.** Begründung:
technik.md §14.

Mit `gui/` gibt es zum ersten Mal **zwei** Oberflächen. Was beide brauchen und der Kern
nach technik.md §9 nicht kennen darf — Vorgabe des Datenverzeichnisses, `config.toml`,
Auflösung des Modellnamens, Dateinamen der Exporte, Buchung einer Triage-Entscheidung,
Vorladefaden — liegt heute in `cli/`. Eine Oberfläche, die die andere importiert, ist
möglich, aber schief.

**Vorgabe:** ein drittes Paket `app/` neben `cli/` und `gui/` — ohne Qt, ohne Konsole;
importiert den Kern, wird von beiden Oberflächen importiert, vom Kern nie
(`tests/test_architecture.py` prüft nur die beiden Verbotsrichtungen — dass `app/` von
beiden Oberflächen tatsächlich benutzt wird, ist damit nicht geprüft, nur so gebaut).
Regel 14 ist erfüllt: Der zweite
Anwendungsfall liegt vor. Was dagegen **Verkettung von Kernschritten** ist — Anki-Deck
schreiben, Druckseite schreiben, GUID buchen —, gehört nach technik.md §7 in `pipeline`
und wandert dorthin (AP 2); das schließt den offenen Punkt „Zurückschreiben der Anki-GUID
hängt an der Kommandozeile". Begriffe für dokumentation.md §2 stehen in Abschnitt 3.

### E5 — Was „Abdeckung" bedeutet

„Lerne diese 34 Wörter und du verstehst 97 % von Kapitel 3." Drei Festlegungen nötig:

1. **Nenner:** alle Wortformen des Kapitels (jedes alphabetische Token), nicht nur die
   Inhaltswörter der fünf Wortarten. Funktionswörter und Eigennamen zählen als verstanden.
   So entspricht die Zahl dem, was der Leser auf der Seite erlebt.
2. **Ein Wort gilt als verstanden**, wenn mindestens eine seiner Bedeutungen im Profil
   `known` ist — die teilweise bekannten Einträge (`new_meaning_of_known_word`) zählen
   also mit. Die genaue Bedeutung je Vorkommen aufzulösen kostete einen Modellaufruf je
   Grundform (rund 1.000 je Kapitel, technik.md §3) und ist für eine Anzeige nicht
   vertretbar.
3. **„Lerne diese N"** = die im laufenden Durchgang auf `learning` gebuchten Einträge; die
   Zahl steigt mit jeder Entscheidung. Angezeigt wird Abdeckung *jetzt* und Abdeckung
   *nach dem Lernen*.

**Vorgabe:** so. Wer die Inhaltswörter als Nenner will, ändert eine Zeile in AP 6.

### E6 — „Ganzes Buch auf einmal, Kapitel einzeln oder in Blöcken"

Zwei Lesarten: (a) ein Lauf über einen Kapitelbereich, jedes Kapitel wie bisher — eigene
Triage, eigenes Deck, eigene Druckseite —, das Profil greift zwischen den Kapiteln und
macht spätere kürzer; (b) mehrere Kapitel als **eine** Einheit — Häufigkeiten
zusammengeführt, ein Deck, eine Druckseite mit Kapitelbereich in der Überschrift.

**Vorgabe: (a) zuerst.** (b) verlangt ein Vorkommen über mehrere Kapitel
(`entities.Occurrence` ist je Kapitel, `triage._ensure_single_chapter` und
`printout._ensure_single_chapter` erzwingen das heute ausdrücklich) — ein Schemathema, das
erst mit echtem Bedarf entschieden wird. Der Dune-Fall (technik.md §8, „Ein Kapitel ist
nicht ein Dokument") zeigt, dass große Einheiten der Zusage „danach ein Kapitel am Stück
lesen" eher schaden. Vorladen über Kapitelgrenzen (technik.md §12, offener Punkt) bleibt
Regel 14: erst messen, ob die rund zwölf Sekunden vor dem ersten Block je Kapitel stören.

### E7 — PDF ohne Handgriff

technik.md §8c hat weasyprint, fpdf2 und reportlab am 21.08.2026 verworfen und Qts
Druckweg nur deshalb, weil `printout` im Kern liegt. Mit `gui/` ist PySide6 ohnehin
vorhanden, und ein Druckweg **neben** dem Kern verletzt die Architekturregel nicht.

| Weg | Was er kann | Was er kostet |
|---|---|---|
| (a) `QTextDocument` + `QPdfWriter` | leicht, deterministisch, Unicode über Systemschriften | kennt kein `columns`-CSS — die Druckseite bräuchte eine zweite Satzvorschrift (Tabelle oder `QPainter`), zwei Quellen für dasselbe Layout |
| (b) `QtWebEngine.printToPdf` | rendert das **bestehende** HTML samt Druck-CSS 1:1, auch das Lesezeichen aus AP 9; eine Layoutquelle | Chromium im Paket (rund 150 MB, in `PySide6-Addons` bereits enthalten — zu belegen an der Rohquelle, Regel 15); `MAX_ENTRIES = 33` ist mit Edge gemessen und mit `tools/print_fit_check.py` gegen diesen Renderer nachzumessen |
| (c) Edge/Chrome headless wie `print_fit_check.py` | null Abhängigkeiten, heute schon im Werkzeug | braucht einen installierten Browser; unter Linux nicht selbstverständlich |

**Empfehlung: (b)**, in `app/pdf.py` mit dem PySide6-Import **innerhalb** der Funktion,
damit die Kommandozeile ohne installiertes Qt weiter startet; der Architekturtest führt
diese eine Datei als erlaubte Ausnahme. Wer die 150 MB scheut, nimmt (c) als Zwischenweg —
der Umbau von (c) auf (b) ist eine Funktion.

### E8 — Anki-Import: wie weit?

Ein fremdes Deck enthält Wortformen, keine WikDict-Bedeutungen. **Vorgabe:** Der Nutzer
wählt das Feld mit dem englischen Wort; jede Wortform wird kleingeschrieben im Wörterbuch
über alle Wortarten nachgeschlagen (`dictionary.pos_variants`), **alle** gefundenen
Bedeutungen werden mit einer neuen Herkunft `Origin.IMPORT` als `known` gebucht — dieselbe
Pauschalität wie die Vorbelegung (technik.md §11, „Die Vorbelegung erzeugt keine teilweise
bekannten Einträge"). Wörter ohne Wörterbucheintrag werden **gemeldet**, nicht still
verworfen (Regel 13). Keine Lemmatisierung importierter Wörter (`running` bleibt
unauffindbar und erscheint in der Meldung) — der Schritt ist billig nachzurüsten, wenn die
Meldung ihn verlangt. Eigene LibreVerbum-Decks bringen nichts Neues und werden nicht
gesondert behandelt.

### E9 — Einstufungstest: welche Form?

technik.md §11 nennt die Zuordnung Niveau → N „geliehen, nicht gemessen"; der Test soll N
schätzen statt erfragen. **Vorgabe:** rund 30 Grundformen aus `wordfreq_en_5000.txt`,
logarithmisch über die Ränge verteilt, je Wort die Frage „kenne ich / kenne ich nicht"
(nur das englische Wort samt Wortart, keine Übersetzung — sie verriete die Antwort). N ist
der größte Rang, unterhalb dessen mindestens vier von fünf Wörtern bekannt waren; das
Verfahren steht mit Datum in technik.md, weil es eine eigene Festlegung ist. Der Test
**bucht nichts einzeln** — er ist Schätzung, keine Triage — und mündet in dieselbe
Vorbelegung wie die Niveauangabe, jetzt mit gemessenem N. Dafür braucht `learner` eine
Spalte für das vorbelegte N neben `cefr_level` (Fassung 3, Regel 5; ein Altbestand ist
nicht zu wandern, das Profil ist bisher nur auf der Entwicklungsmaschine). Oberhalb von
Rang 5.000 kann der Test nichts messen — dieselbe Grenze wie bei C2 (technik.md §11).

### E10 — Erstlauf in der Oberfläche: schreibt sie `config.toml`?

Bisher: „Geschrieben wird die Datei nicht" (technik.md §9) — die Kommandozeile legt eine
Vorlage an und beendet sich, der Nutzer ändert sie von Hand. In einer Oberfläche ist ein
Dialog, der auf einen Texteditor verweist, ein Bruch. **Vorgabe:** Der Einstellungsdialog
schreibt die Datei aus derselben Vorlage mit eingesetzten Werten — kein TOML-Schreiber als
Abhängigkeit (`tomllib` liest nur), sondern die Vorlage mit Platzhaltern; gelesen wird
weiter mit `tomllib`. Die Kommandozeile behält ihr Verhalten.

### E11 — Gestaltungsrichtung: wer entscheidet, und woran?

Die Recherche verlangt, sich auf **eine** Ästhetik festzulegen, statt „modern" zu sagen.
Das ist keine Entscheidung eines Agenten. **Vorgabe (AP 14):** Ein Opus-Agent legt **drei**
Richtungen vor — je als gerenderter Screenshot des Triage-Bildschirms (der meistgenutzte),
mit Namen der Richtung, 4 bis 6 Farbtoken, zwei Schriftrollen, Abstandsskala und einem
Signaturelement —, Dominik wählt eine, und erst danach entsteht Code. Was Dominik vorab
beisteuern kann und sollte: Vorbilder (Screenshots von Programmen, deren Anmutung passt),
hell oder dunkel, und ob das am Zeiger klebende Schiebemenü aus technik.md §1 gesetzt
bleibt. Mitgebrachte Schriften brauchen je eine Lizenzprüfung an der Rohquelle (Regel 15;
OFL-Schriften sind unproblematisch und kommen mit Namensnennung in `NOTICE`, wie die
Wortliste).

### E12 — Schwierigkeitscheck: welche Maßzahl, welche Worte?

„Ca. 14 unbekannte Wörter pro Seite" setzt eine Seite voraus, die es im EPUB nicht gibt.
**Vorgabe:** gemessen werden **unbekannte Grundformen je 1.000 Wortformen** und die
Abdeckung nach E5, je Kapitel und fürs Buch; der Kern liefert Zahlen, die Oberfläche die
Worte. Für die Einordnung („zu schwer für dich") werden vorläufig drei Schwellen gesetzt
und als Vermutung markiert — belastbar wird die Skala erst, wenn sie an drei gelesenen
Büchern gegen das eigene Empfinden gehalten wurde. Der Lauf kostet einen spaCy-Durchgang
über das ganze Buch (22 bis 29 s, technik.md §5) mit Fortschrittsanzeige; kein zweiter
Zwischenspeicher ohne gemessenen Anlass (Regel 14).

### E13 — `beobachtungen/` ist nicht leer

Neun Dateien vom 15.09.2026 liegen dort, alle aus dem Einfalten am Tor der Phase 1. Nach
CLAUDE.md, „Arbeitsweise" heißt ein nicht-leeres Verzeichnis beim Kaltstart: ein Einfalten
steht aus. Mehrere tragen Ableitungen für dokumentation.md §10 (Trefferzahl eines
Prüfskripts gegen eine bekannte Größe halten; Vergleichspaar ist `git show <commit>`;
Suchmenge beim Einfalten ist alles außer `beobachtungen/`). **Vorgabe:** AP 0b faltet sie
ein, bevor Phase 2 neue dazulegt.

### E14 — Wohin mit der Recherche-Datei

**Entschieden 16.09.2026: Die Datei fällt am Tor der Phase 2 weg** — wie `bauplan.md` und
`nacharbeit.md` in Phase 1. Begründung: technik.md §14.

`recherche_hochwertige_UIs_mit_Claude.md` liegt als datiertes Arbeitsmaterial versioniert
im Wurzelverzeichnis (seit `5af0e86`) und passt in keine der drei Dokumentrollen. Was
daraus gilt, steht in Abschnitt 7 dieses Plans und ist mit E1/E11 nach technik.md §14
gewandert — mit dem Datum und dem Hinweis, dass die Recherche Web-Frontends meinte. Bis
zum Tor bleibt die Datei liegen — nicht löschen; die Löschung selbst steht in Block D. Was
daraus dauerhaft gilt, bewahrt danach Git (`git show
5af0e86:recherche_hochwertige_UIs_mit_Claude.md`).

> **Nachtrag, 15.09.2026 (Durchsicht c3584dc, Befund 1):** Die Vorgabe „nicht
> versionieren" oben war überholt, bevor sie geschrieben wurde — die Datei war zu diesem
> Zeitpunkt bereits committet (`5af0e86`, vor `c3584dc`). Wer sich auf „unversioniert"
> verließ, hätte sie fälschlich gelöscht oder aus der Versionierung genommen. Die
> Rollenfrage bleibt offen, nur die Tatsachenbehauptung ist berichtigt.

---

## 2. Was Phase 2 umfasst — Abgleich mit den Dokumenten

| Vorhaben | Quelle | Arbeitspakete |
|---|---|---|
| Qt-Oberfläche: Kapitelauswahl, Triage, Fortschritt, Export | konzept.md, „Phase 2", erster Schritt | AP 14 bis 19, 24 |
| Ganzes Buch, Kapitel einzeln oder in Blöcken | konzept.md, „Phase 2" | AP 4, 5, 20 |
| Abdeckungsanzeige | konzept.md, „Phase 2" | AP 6, 19 |
| Buch-Schwierigkeitscheck | konzept.md, „Phase 2" | AP 7, 21 |
| Lesezeichen-Druck, weitere Druckvarianten, PDF ohne Browser | konzept.md, „Phase 2"; technik.md §8c | AP 9, 10, 22 |
| Liste „Figuren & Orte" | konzept.md §6; technik.md §7, „Die Liste »Figuren & Orte« ist Phase 2" | AP 8, 22 |
| Anki-Import, adaptiver Vokabeltest | konzept.md, „Phase 2" | AP 11, 12, 23 |
| Vorspann-Kapitel im Sweep | technik.md §8, offener Punkt „`epub.read_chapter` wirft `ValueError` …" | AP 4 |
| Anki-GUID-Buchung wandert mit | technik.md §7, offener Punkt | AP 2 |
| Regel 9 in ihrer nicht prüfbaren Hälfte | technik.md §7, „Die Oberfläche liegt neben dem Kern" | AP 15 (macht sie prüfbar) |
| Sicherung und Ausleiten | technik.md §4, „Sichern und Ausleiten"; §9, offener Punkt | AP 13, 23 |
| Zwei falsch begründete Stellen im Profil | technik.md §4, offene Punkte (Regel-Kommentar `record_card`, Idempotenz-Tests) | AP 2 |

**Nicht in Phase 2** (bleibt offen oder ist Phase 3): Anki-Rückkanal, Lesetempo-Planung,
weitere Eingabeformate, weitere Sprachpaare, Auslieferung (Nuitka/PyInstaller), der offene
Punkt „Einträge ohne Wörterbucheintrag mit Vorrang" (konzept.md, „Bewusst offen" — kann
nebenbei entschieden werden, ist aber kein Arbeitspaket).

---

## 3. Neue Begriffe (vor dem ersten Bezeichner in dokumentation.md §2 einzutragen)

| Deutsch | Code |
|---|---|
| Anwendungsschicht (was beide Oberflächen teilen und der Kern nicht kennt) | `app` |
| Qt-Oberfläche | `gui` |
| Ansichtsmodell (Zustand und Übergänge eines Bildschirms, ohne QML) | `view_model` |
| Arbeiter, Hintergrundfaden der Oberfläche | `worker` |
| Gestaltungsvorgaben, Token | `theme` (`Theme.qml`) |
| Bildschirm, Ansicht | `screen` |
| Abdeckung | `coverage` |
| Schwierigkeit (eines Buchs) | `difficulty` |
| Lesezeichen (Druckformat) | `bookmark` |
| Figuren & Orte | `proper_noun_list` |
| Sicherung / Ausleiten | `backup` / `dump` |
| Einstufungstest | `placement_test` |
| Anki-Import | `anki_import`, Herkunft `Origin.IMPORT` |
| Kapitelbereich | `chapter_range` |
| Einrichtung, Erstlauf | `setup` |
| Kapitel ohne Fließtext (Vorspann, Impressum, Bildband) | `ChapterWithoutTextError`, `skip_reason` |

---

## 4. Die Arbeitspakete

Je AP: **Ziel** · **Form** der berührten Schnittstellen (fest, oder ausdrücklich „bestimmt
der Bauende") · **Dateien** · **Prüfung** (wo zwei Wege verlangt sind, je ein Fall, an dem
der eine ohne den anderen rot wird) · **Größe** · **nach** (Voraussetzungen).

### Block A — Fundament (streng nacheinander)

#### AP 0 — Zweig, Hausordnung, Begriffe · S · Dokumente

**Ziel.** `phase-2` anlegen (E2). CLAUDE.md: Zweigregel unter „Arbeitsweise"; unter „Prüfen
vor »fertig«" die Ergänzung für die Oberfläche (`QT_QPA_PLATFORM=offscreen` im Test, die
Screenshot-Regel aus Abschnitt 7); unter „Architektur" die drei Pakete `app/`, `cli/`,
`gui/` und ihre Importrichtung. dokumentation.md §2: die Begriffe aus Abschnitt 3.
technik.md: neuer Abschnitt 14 „Oberfläche — Aufteilung und Anwendungsschicht" mit E1 bis
E4 (Datum, Begründung, was verworfen wurde), und die Entscheidungstabelle am Kopf um
Zeile 14 ergänzt. **Form.** entfällt. **Prüfung.** `grep` über alles außer
`beobachtungen/`, dass keine Stelle mehr „auf `main`" verlangt; tote Verweise geprüft wie in
dokumentation.md §7. **nach** E1 bis E4.

#### AP 0b — `beobachtungen/` einfalten · S · Dokumente

**Ziel.** Die neun Dateien vom 15.09.2026 nach dokumentation.md §9 abarbeiten: was ein
Dokument berichtigt, vollständig; was die Hausordnung ändert, gewichtet und entschieden;
Dateien im selben Commit gelöscht. **Prüfung.** `git show <commit>` enthält die Löschung
und je übernommener Ableitung eine Stelle in dokumentation.md §10; Suchmenge ist alles
außer `beobachtungen/`. **nach** AP 0 (beide berühren dokumentation.md).

#### AP 1 — Umgebung und Prüftor für die Oberfläche · S–M · `pyproject.toml`, `tests/conftest.py`, `tests/test_architecture.py`, `tests/test_environment.py`, `uv.lock`

**Ziel.** PySide6 (`>=6.11,<7`, Gruppe `gui`) mit `pip` in `.venv/` installieren, danach
`uv lock` — **nicht** `uv sync` (technik.md §6, „Falle"). Neue Marke `needs_gui`
(Registrierung in `pyproject.toml`, Skip in `conftest.py`, wenn `PySide6` nicht importierbar);
`conftest.py` setzt für diese Tests `QT_QPA_PLATFORM=offscreen` und stellt genau **eine**
`QGuiApplication` je Testlauf bereit. `test_architecture.py`: `FORBIDDEN_IN_CORE` (vormals
`GUI_PACKAGES`, umbenannt in der Durchsicht von 907ab02, Befund 5 — `app/` ist selbst keine
Oberfläche) um `gui` und `app` erweitert; neue Prüfung, dass `app/` weder `cli`, `gui` noch
`PySide6` importiert (Ausnahme `app/pdf.py`, falls E7 (b)). Ein erster `needs_gui`-Test lädt
ein leeres QML offscreen und schlägt bei jeder QML-Warnung fehl — auch bei einer, die nur
über den Qt-Meldungs-Handler läuft (`qInstallMessageHandler`), nicht nur über
`QQmlEngine.warnings` (Durchsicht von 907ab02, Befund 1). **Keine** weitere Abhängigkeit:
`PySide6.QtTest` (`QSignalSpy`, `QTest.qWait`) genügt; sollte der Bauende `pytest-qt`
brauchen, vorher Regel 15 (MIT laut PyPI-JSON — zu belegen). **Prüfung.** Mit deinstalliertem
PySide6 nennt die Schlusszeile **vier** Übersprungene, mit installiertem **drei**
(dokumentation.md §10, „Gegenprobe" — der dritte bzw. vierte ist der vorübergehende
`app/`-Skip aus `test_rule_9_app_package_does_not_import_the_interfaces`, der erst mit AP 3
wegfällt, siehe dort) — beide Läufe im Bericht. Verfälschung: QML mit absichtlichem
Bindungsfehler laden → Test rot; eine zweite Verfälschung nur über `console.warn` (kein
`QQmlEngine.warnings`-Eintrag) prüft die Meldungs-Handler-Hälfte gesondert. **nach** AP 0.

#### AP 2 — Export-Verkettung in den Kern · M · `libreverbum/pipeline.py`, `libreverbum/profile.py`, `cli/export.py`, `tests/test_pipeline.py`, `tests/test_cli_export.py`, `tests/test_profile.py`

**Ziel.** Der Dreischritt Anki-Deck schreiben → Druckseite schreiben → `profile.record_card`
je Karte verlässt `cli.export.write_exports` und wird `pipeline.export_cards` — die
Verkettung von Kernschritten gehört nach technik.md §7 nur dorthin; die zweite Oberfläche
bekommt die GUID-Buchung damit geschenkt statt nachgebaut (Regel 6). Dateinamen, `_2`/`_3`
und `_teilexport` bleiben Sache des Aufrufers (`cli.export.export_paths`). Nebenbei die
beiden offenen Punkte aus technik.md §4: der Regel-Kommentar über `profile.record_card`
wird richtig begründet (Rückkanal, nicht Doppelnotiz), und die Idempotenz-Tests reichen
zwei **getrennt erzeugte** Karten desselben Eintrags hinein. **Form (fest).**
`pipeline.export_cards(con, cards: Sequence[Card], *, anki_path: Path, printout_path: Path,
deck_name: str) -> None`; `cli.export.write_exports` behält Signatur und Rückgabe,
`cli/main.py` bleibt unberührt. **Prüfung.** Nach `export_cards` steht je Karte eine
`card`-Zeile (Regel 6); Verfälschung: `record_card`-Aufruf entfernen → rot. Der
Ende-zu-Ende-Test aus technik.md §7 (offener Punkt „prüft die Druckseite, nicht das
Profil") bekommt die fehlende Zusicherung auf `card`. **nach** AP 1.

#### AP 3 — Anwendungsschicht `app/` · M · `app/` (neu), `cli/config.py` → `app/config.py`, `cli/model.py` → `app/model.py`, `cli/export.py` (Namensbildung) → `app/export.py`, `cli/main.py`, `cli/__init__.py`, Tests entsprechend

**Ziel.** Verschieben per `git mv`, Importe nachziehen, Docstrings auf die neue Rolle
(„von beiden Oberflächen benutzt"). `cli/export.py` bleibt als dünne Hülle oder entfällt —
bestimmt der Bauende, `cli/main.py` ruft danach `app.export`. **Form (fest).** Signaturen
unverändert; `app/__init__.py` trägt den Paket-Docstring nach dokumentation.md §3 mit dem
Satz „importiert `libreverbum`, nie `cli`, `gui` oder Qt". **Prüfung.** Architekturtest
aus AP 1 rot, sobald `app/` eines der drei importiert (Verfälschung: `import cli` in
`app/config.py`). Alle CLI-Tests unverändert grün. **Zur Abnahme gehört außerdem** (Durchsicht
von 907ab02, Befund 6): Die Schlusszeile von `pytest` nennt den `app/`-Skip aus
`test_rule_9_app_package_does_not_import_the_interfaces` nicht mehr — er greift nur,
solange `app/` fehlt —, und die Zahl der Übersprungenen fällt um einen zurück: **zwei** mit
installiertem PySide6, **drei** ohne (dokumentation.md §10, „Woran sie prüft").
**nach** AP 2 (beide berühren `cli/export.py`).

### Block B — Kern und Kommandozeile (läuft neben Block C; untereinander nach Dateien geordnet)

#### AP 4 — Kapitel ohne Fließtext sichtbar machen · M · `libreverbum/epub.py`, `libreverbum/pipeline.py`, `cli/main.py`, Tests

**Ziel.** `epub.read_chapter` bricht bei Vorspann, Impressum und Bildband mit `ValueError`
ab; `pipeline.run_chapter` erkennt diese Fälle heute am **Meldungstext** — brüchig, und ein
Sweep über alle Kapitel (AP 5, AP 7, AP 20) stolpert daran (technik.md §8, offener
Punkt). Neu: `epub.ChapterWithoutTextError(ValueError)` mit `skip_reason`; `run_chapter`
fängt den Typ statt den Text; `pipeline.list_chapters(epub_path) -> list[ChapterListing]`
liefert je Kapitel Nummer, Titel, Wortzahl und `skip_reason: str | None`, ohne spaCy. Die
Kapitelauswahl der Kommandozeile zeigt übersprungene Kapitel mit Grund und lehnt ihre Wahl
ab. **Form (fest)** wie genannt; `ChapterListing` ist `frozen` und liegt in `pipeline`, nicht
in `entities` (Ablaufwert, keine Fachlichkeit — wie `ChapterProgress`). **Prüfung.** Gegen
`tools/sherlock.epub`: das Gutenberg-Vorspann-Kapitel erscheint mit Grund; jeder **andere**
`ValueError` (kaputtes Archiv) läuft weiter durch — zwei Wege, je ein Fall. **nach** AP 3.

#### AP 5 — Kapitelbereich in der Kommandozeile · M · `cli/main.py`, `tests/test_cli_main.py`

**Ziel.** `--chapters 3-7` und `--chapters all` (E6 (a)): Sprachmodell einmal laden,
Kapitel nacheinander mit unveränderter Triage und je eigenem Export, übersprungene Kapitel
gemeldet, am Ende eine Bilanz über alle. `--chapter N` bleibt. **Form.** bestimmt der
Bauende innerhalb von `_run`; kein neues Modul. **Prüfung.** Zwei Kapitel nacheinander mit
Attrappen: die „kenne ich"-Buchungen des ersten reduzieren die Einträge des zweiten
(Abnahmekriterium 2 unten). Verfälschung: Profilverbindung je Kapitel neu aus einer
Kopie → rot. **nach** AP 4. Nur, falls E3 die Ausnahme bestätigt.

#### AP 6 — Abdeckung · M · `libreverbum/extraction.py`, `libreverbum/pipeline.py`, Tests

**Ziel.** `ChapterVocabulary` erhält `token_count` (alphabetische Wortformen des Kapitels,
aus `extraction.extract_vocabulary` mitgezählt). `pipeline.coverage(vocabulary,
learned: Collection[Lemma] = ()) -> Coverage` mit `token_count`, `understood_tokens`,
`unknown_lemma_count`, `share` und `share_after_learning` nach E5 — reine Rechnung über
`VocabularyEntry.status`, kein Datenbank- und kein Modellzugriff. **Form (fest)** wie
genannt. **Prüfung.** Handgerechnetes Mini-Kapitel; gegen `tools/sherlock.epub` Kapitel 2
gilt `sum(frequency) <= token_count` und die Zahl steht mit Rezept im Bericht
(dokumentation.md §5, „Wer eine Zahl … schreibt das Rezept daneben"). Verfälschung: Nenner
und Zähler vertauscht → rot. **nach** AP 4 (beide `pipeline.py`).

#### AP 7 — Schwierigkeitscheck · M–L · `libreverbum/pipeline.py`, `cli/main.py`, Tests

**Ziel.** `pipeline.assess_book(*, epub_path, dictionary_path, profile_path, nlp,
cache_dir, on_progress) -> BookDifficulty` — je Kapitel mit Text: `token_count`,
`unknown_lemma_count`, `unknown_per_thousand`, `coverage`; fürs Buch dasselbe aggregiert.
Läuft Extraktion und Wörterbuchabgleich je Kapitel (nutzt den Zwischenspeicher aus
technik.md §5), meldet Fortschritt wie `run_chapter`, kein Modellaufruf. Die Kommandozeile
bekommt `--assess` (E3-Ausnahme): Tabelle je Kapitel, eine Zeile fürs Buch, drei
Schwellenworte als Vermutung markiert (E12). **Form (fest)** wie genannt; Schwellen liegen in
`app/`, nicht im Kern. **Prüfung.** Gegen `tools/sherlock.epub` und `tools/dorian_gray.epub`
mit leerem und mit B1-vorbelegtem Profil: die Vorbelegung senkt die Zahl; Zahlen mit Rezept
im Bericht. Verfälschung: Vorspann-Kapitel nicht übersprungen → Zähler falsch → rot.
**nach** AP 6.

#### AP 8 — Figuren & Orte · M · `libreverbum/extraction.py`, `libreverbum/pipeline.py`, `libreverbum/printout.py`, Tests

**Ziel.** `extraction.extract_proper_noun_list(chapter, nlp) -> list[ProperNounEntry]` über
spaCys Entitäten (`ent_type_` in PERSON, GPE, LOC, FAC — Vermutung, am Bestand zu prüfen)
mit **Oberflächenform** und Häufigkeit, mehrwortig („Sherlock Holmes"), nie über die
Grundform (technik.md §5, offener Punkt „Über-Lemmatisierung von Eigennamen");
`ChapterVocabulary.proper_nouns`; `printout.write_printout(..., proper_nouns=None)` hängt
bei Angabe den Anhang „Figuren & Orte" an (konzept.md §6). Das Zusammenstellen liegt in
`printout`, nicht in `extraction` (technik.md §7). **Form (fest)** wie genannt;
`ProperNounEntry` in `entities` (Fachlichkeit). **Prüfung.** Gegen `tools/sherlock.epub`
Kapitel 2: „Sherlock Holmes"/„Holmes", „Irene Adler", „Bohemia" enthalten, „Miss" nicht
(Regel 12, `miss` ist Lernvokabel). Verfälschung: Grundform statt Oberflächenform → „holme"
→ rot. **nach** AP 7 (`pipeline.py`).

#### AP 9 — Lesezeichen-Druck · M · `libreverbum/printout.py`, `tools/print_fit_check.py`, `tests/test_printout.py`

**Ziel.** `printout.write_bookmark(path, entries)`: schmale Streifen im Buchformat
(konzept.md §6, „Lesezeichen-Format"), mehrere je Blatt mit Schnittmarken, je Zeile
Wortform, Kurzwortart und Übersetzung — die Wortart bleibt, aus dem Grund in konzept.md
§6. Streifenbreite und Kapazität werden **gedruckt gemessen** wie `MAX_ENTRIES`
(technik.md §8c, „Echt gedruckt statt gerechnet"), `print_fit_check.py --bookmark`.
**Form (fest)** wie genannt, Eingabe wie `write_printout`. **Prüfung.** Kapazität mit Rezept
im Bericht; Umbruch auf mehrere Streifen; Verfälschung: Schnittmarken entfernt → Test auf
das HTML rot. **nach** AP 8 (`printout.py`).

#### AP 10 — PDF ohne Handgriff · M · `app/pdf.py` (neu), `tests/test_app_pdf.py`, `tools/print_fit_check.py`, technik.md §8c

**Ziel.** Nach E7. `app.pdf.write_pdf(html_path, pdf_path)`; bei (b) Lizenz und Paket von
QtWebEngine an der Rohquelle belegt (Regel 15), `MAX_ENTRIES` und die Lesezeichenkapazität
gegen diesen Renderer nachgemessen, Abweichungen in technik.md §8c mit Datum. **Prüfung
(`needs_gui`).** Die Druckseite mit 33 Einträgen ergibt ein PDF mit genau einer Seite, 34
zwei (Seitenzahl aus dem PDF gelesen, nicht gerechnet). Verfälschung: Druck-CSS entfernt →
Seitenzahl ändert sich → rot. **nach** AP 9, AP 1.

#### AP 11 — Anki-Import · M · `libreverbum/anki.py`, `libreverbum/entities.py`, `libreverbum/pipeline.py`, Tests

**Ziel.** Nach E8. `anki.read_deck(path) -> DeckContents(field_names, notes)` liest
`.apkg` (ZIP, darin `collection.anki2`/`.anki21`, `notes.flds` an `\x1f` getrennt,
Feldnamen aus `col.models`) — Standardbibliothek. `pipeline.import_known_words(con,
dictionary_path, words) -> ImportResult(matched, unmatched)` bucht `Origin.IMPORT`
(neuer Enum-Wert, keine Schemaänderung). **Form (fest)** wie genannt. **Prüfung.** Ein mit
`genanki` erzeugtes Deck wird zurückgelesen (Vorrichtung); gegen `tools/en-de.sqlite3`:
„watch" bucht alle Bedeutungen, „xyzzy" landet in `unmatched`. Verfälschung: `unmatched`
verschluckt → rot (Regel 13). **nach** AP 7 (`pipeline.py`).

#### AP 12 — Einstufungstest · M–L · `libreverbum/pipeline.py`, `libreverbum/profile.py`, `libreverbum/entities.py`, Tests, technik.md §11

**Ziel.** Nach E9. `pipeline.placement_test_items(count=30)`, `pipeline.estimate_preset_
count(answers)`, `pipeline.write_vocabulary_preset` um eine Variante mit `count` statt
`CefrLevel`; `learner` bekommt `preset_word_count` (Schema Fassung 3, `PRAGMA
user_version` erhöht, Fassung 2 wird wie bisher Fassung 1 laut abgewiesen — technik.md §4,
„Schemaversion von Anfang an"). Verfahren mit Datum in technik.md §11; der offene Punkt
„geliehen, nicht gemessen" wird dort umformuliert. **Prüfung.** Schätzer an Hand konstruierter
Antwortmuster (alles bekannt → 5.000; nichts → 0; Sprung bei 1.700 → 1.700); Ränge
logarithmisch verteilt (Verfälschung: linear → rot). **nach** AP 11.

#### AP 13 — Sicherung und Ausleiten · S · `libreverbum/profile.py`, `tests/test_profile.py`

**Ziel.** `profile.backup(con, target)` über `sqlite3.Connection.backup` (konsistent
während des Betriebs, technik.md §4, „Sichern") und `profile.dump(con, target)` als JSON über
alle acht Tabellen („Ausleiten"). **Form (fest)** wie genannt. **Prüfung.** Sicherung ist
byteweise ein gültiges Profil derselben Fassung; JSON enthält jedes Ereignis; Verfälschung:
eine Tabelle ausgelassen → rot. **nach** AP 3. Verträgt sich mit jedem anderen AP
(nur `profile.py`), außer AP 12.

### Block C — Oberfläche (Qt Quick, streng nacheinander; Umsetzung von E1)

#### AP 14 — Gestaltungsrichtung · M · **Opus**, Ergebnis wählt Dominik

**Ziel.** Nach E11: drei Richtungen als offscreen gerenderte QML-Mockups des
Triage-Bildschirms (PNG, 1280×800), je mit Namen, Token, Schriftrollen (Lizenz je Schrift
belegt), Abstandsskala, Signaturelement; dazu ASCII-Wireframes der sieben Bildschirme
(Einrichtung, Buch und Kapitel, Fortschritt, Triage-Liste, Triage-Eintrag, Blockende,
Abschluss) und je Bildschirm die Liste „verifiziert heißt" (die Recherche warnt: ohne
sie meldet ein Agent auch bei kaputter Seite Erfolg). Nach der Wahl: technik.md §14 (die
Richtung samt Begründung und den beiden verworfenen), `gui/qml/Theme.qml` (Token als
QML-Singleton, **einzige** Quelle für Farben, Schriften, Abstände), Kurzblock in CLAUDE.md
(höchstens acht Zeilen: Richtung, Token-Datei, „keine Hex-Farbe außerhalb `Theme.qml`",
Schriftverbot für Systemschriften, Screenshot-Regel). **Prüfung.** Jeder Mockup lädt ohne
QML-Warnung; kein Layoutüberlauf und keine Textkürzung im Objektbaum; Kontrast ≥ 4,5:1
**im gerenderten PNG an jeder Textstelle** (unter 24 px; ab 24 px beziehungsweise ab
18,66 px halbfett gilt 3,0:1 nach WCAG 2.1). **nach** AP 1.

> **Berichtigt am 17.09.2026.** Die Prüfzeile lautete bis hierher: „Die drei Mockups
> laden ohne QML-Warnung; Kontrast Text/Grund je Token-Paar ≥ 4,5:1, **aus den Token
> gerechnet**." Beide Hälften sind widerlegt, und zwar an diesem Arbeitspaket
> selbst: Die Tokenrechnung meldete „0 Paare unter 4,5:1", während im Bild sieben
> Textstellen darunter lagen, die schlechteste bei 2,41:1 — `opacity`-Faktoren und
> getönte Füllungen kommen in keiner Tokenrechnung vor. Und „0 QML-Warnungen" fängt
> keinen Layoutüberlauf: Qt meldet dabei nichts, während der Belegsatz aus dem Fenster
> läuft. Begründung und Zahlen: technik.md §14, „Gemessen wird im Bild, nicht aus den
> Token".

> **Erledigt am 17.09.2026** (Wahl Dominiks: „Lesetisch"). Abweichungen von der
> Vorgabe oben, begründet in technik.md §14, E11: **zwei** Richtungen statt dreier (die
> erste wurde verworfen, die zweite entstand aus deren Kritik) und **vier** gebaute
> Bildschirme statt eines. Gelandet ist es in `gui/qml/Theme.qml` (Token), `gui/fonts/`
> samt `NOTICE` Abschnitt 5 (Schriften), technik.md §14, E11 (Begründung und
> Messwerte), konzept.md, „Die sieben Bildschirme der Oberfläche" (Wireframes und
> „verifiziert heißt"-Listen), CLAUDE.md, „Gestaltung" (Kurzblock),
> `tools/design_mockup/` (lauffähiger Mockup samt beiden Durchsichten) und
> `tests/test_design_tokens.py` (der Grep-Test aus AP 15, vorgezogen).

#### AP 15 — Gerüst der Oberfläche · M · `gui/` (neu), `tools/gui_screenshot.py` (neu), `tests/test_gui_*.py`

**Ziel.** `python -m gui`: `QGuiApplication`, `QQuickStyle` auf `Basic` **vor** dem
Laden, mitgebrachte Schriften über `QFontDatabase`, `QQmlApplicationEngine` mit
`Theme.qml` als Singleton, `Main.qml` mit Fenster und Bildschirmstapel; QML-Warnungen
gehen nach `stderr` und lassen im Test den Lauf scheitern (eine falsche Bindung ist sonst
der stille Fehlschlag aus Regel 13 — nichts erscheint, nichts meldet). `gui/workers.py`:
`run_in_worker(fn, *, on_done, on_error)` als `QObject` mit Signalen, Ausnahmen des Fadens
erreichen `on_error` **immer** (Regel 13). `tools/gui_screenshot.py <screen> <png>` rendert
einen Bildschirm mit Vorführdaten bei 1280×800 und bei der Mindestgröße (900×600 als
Vorgabe) über `QQuickWindow.grabWindow()`. **Form (fest)** wie genannt; Aufteilung unter
`gui/` bestimmt der Bauende, mit je einem Modul-Docstring nach dokumentation.md §3.
**Prüfung.** Regel 9 wird hier zum ersten Mal **prüfbar**: Ein Arbeiter, der 0,5 s schläft,
lässt einen 50-ms-Timer der Ereignisschleife weiterlaufen (Verfälschung: `fn` im
Hauptfaden → Timer feuert nicht → rot); eine Ausnahme im Arbeiter kommt bei `on_error` an
(Verfälschung: `except: pass` → rot). Der Grep-Test — keine Hex-Farbe und keine
Schriftfamilie außerhalb `Theme.qml` — steht seit AP 14 als `tests/test_design_tokens.py`
und ist hier nicht noch einmal zu bauen, sondern nur dann anzupassen, wenn `gui/qml/`
neue QML-Dateien bekommt. **nach** AP 14.

> **Ergänzt am 17.09.2026 zur Prüfschleife.** `tools/gui_screenshot.py` rendert nicht
> nur: Es zählt QML-Warnungen, prüft den Objektbaum auf Layoutüberlauf und gekürzten
> Text und misst den Kontrast **im PNG an jeder Textstelle** — vier Schritte, nicht
> einer. Die ersten drei fangen je einen Fehlschlag, den die anderen nicht sehen
> (technik.md §14, „Gemessen wird im Bild, nicht aus den Token"). Vorbild und
> Vorlage sind `shot.py`, `layout_check.py` und `contrast_check.py` in
> `tools/design_mockup/`; sie bleiben dort, bis `gui_screenshot.py` ihre Arbeit tut.

#### AP 16a — Einstellungen und Wörterbuch · M · `gui/`, `libreverbum/dictionary.py`, Tests

**Ziel.** Datenverzeichnis sichtbar (technik.md §9, erste Zeile jedes Laufs); fehlt
`config.toml`: Dialog für `model.url` und `model.name`, schreibt die Datei nach E10; fehlt
das Wörterbuch: Hinweis mit `dictionary.SOURCE_NOTICE` und Größe, Bezug im Arbeiter mit
Fortschritt — dafür bekommt `dictionary.fetch_dictionary` einen `on_progress(done_bytes,
total_bytes)`-Rückruf (Vorgabe `None`, unverändertes Verhalten), und `ensure_index` läuft
ebenfalls im Arbeiter (32 bis 44 s ohne Index, technik.md §3). Fehlschläge erscheinen im
Dialog, nie nur auf `stderr`. **Form (fest)** für `fetch_dictionary`; Dialoge bestimmt der
Bauende nach den Wireframes. **Prüfung.** Ansichtsmodell ohne QML: jeder Zweig (Datei
fehlt / da / Bezug abgelehnt / Bezug scheitert) mit Attrappe; Verfälschung: Fehlschlag des
Bezugs verschluckt → rot. Screenshots beider Dialoge im Bericht. **nach** AP 15, AP 3.

#### AP 16b — Profil anlegen und Niveau · M · `gui/`, Tests

**Ziel.** Fehlt das Profil: Bestätigung mit Pfad (`cli.main._confirm_new_profile` als
Vorbild), Niveauwahl A1 bis C1 oder „keine Angabe" mit der Zahl vorbelegter Grundformen je
Stufe (`pipeline.PRESET_WORD_COUNT`), Vorbelegung im Arbeiter mit Fortschritt, Hinweis
„einmalig, nicht zurücknehmbar" (technik.md §11). **Prüfung.** wie AP 16a; gegen
`tools/en-de.sqlite3`: B1 bucht dieselbe Ereigniszahl wie die Kommandozeile (Zahl aus
`tests/test_cli_main.py` übernehmen und **belegen**, nicht abschreiben). **nach** AP 16a.

#### AP 17 — Buch und Kapitel · M · `gui/`, `app/texts.py` (neu), Tests

**Ziel.** Datei öffnen (nativer Dialog, nur `.epub`), Struktur im Arbeiter lesen,
Kapitelliste mit Titel, Einrückung nach Ebene und Wortzahl (`pipeline.list_chapters`, AP 4;
bis dahin `epub.count_chapter_words`), übersprungene Kapitel gedimmt mit Grund und nicht
wählbar, Hinweis bei fehlender Navigation; „Kapitel vorbereiten" lädt spaCy und ruft
`run_chapter` im Arbeiter, die vier Etappen (`ChapterStage`) werden als Text mit Zähler
gezeigt. Die Zuordnung Etappe → deutscher Satz wandert aus `cli/main.py` nach `app/texts.py`
(zweiter Anwendungsfall). **Prüfung.** Ansichtsmodell: Wahl eines übersprungenen Kapitels
wird abgelehnt; Fortschritt kommt in Etappenreihenfolge an; Fehlschlag in `run_chapter`
landet im Dialog. Screenshots mit `tools/sherlock.epub` (14 Kapitel, eines übersprungen).
**nach** AP 16b; weich nach AP 4.

#### AP 18a — Triage-Ansichtsmodell und geteilte Buchung · L · `gui/triage_view_model.py`, `app/triage.py` (neu), `cli/interaction.py`, Tests

**Ziel.** Die Buchungslogik einer Entscheidung (Ereignis mit Herkunft und Zeitstempel,
Karten-GUID, Sammelaktion über `triage.bulk_mark`) verlässt `cli.interaction._record` und
`_bulk_phase` nach `app/triage.py`; die Kommandozeile ruft sie von dort. Darauf ein
`QObject`-Zustandsautomat ohne QML: Zustände `BLOCK_LIST` (Sammelaktion), `ENTRY`,
`BLOCK_END` (Bilanz, Fortsetzungsfrage), `FINISHED`, `FAILED`; Eingänge `bulk_known_up_to`,
`decide(action)`, `continue_(yes)`, `quit`; Eigenschaften mit `notify`-Signalen (fehlt
`notify`, bleibt die Anzeige still stehen — Regel 13). Eine `TriageResolution` je Block
kommt von außen (AP 18c liefert das Vorladen). **Form (fest)** für `app/triage.py`
(Signaturen der beiden Funktionen bestimmt der Bauende, sie ersetzen die beiden privaten
Stellen in `cli/interaction.py` eins zu eins); Ansichtsmodell bestimmt der Bauende.
**Prüfung.** Jeder Übergang mit Attrappen-`TriageResolution`; die CLI-Tests bleiben grün
(die Buchung ist dieselbe); Verfälschung: `Origin.BULK_MARK` durch `TRIAGE` ersetzt → rot
in beiden Oberflächen. **nach** AP 17.

#### AP 18b — Triage-Bildschirm · L · `gui/qml/`, Tests, Screenshots

**Ziel.** Nach den Wireframes aus AP 14: die nummerierte Blockliste mit „bis hier kenne ich
alles" (Klick auf die Zeile, Tastatur), danach der Einzeleintrag — Kopfzeile Wortform und
Übersetzung, Nebendaten gedimmt, Belegsatz mit hervorgehobener Wortform, Marke „neue
Bedeutung eines bekannten Wortes", Zähler in der Trennlinie (technik.md §13 bleibt der
inhaltliche Maßstab) —, Tasten K/L/S/Q **und** Schaltflächen, Blockbilanz, Fortsetzungsfrage,
Übergänge zwischen Einträgen. **Prüfung.** „verifiziert heißt"-Liste aus AP 14 je
Bildschirm gegen Screenshots bei beiden Größen; Tastendruck K erreicht das Ansichtsmodell
(QML-Test über `QSignalSpy`); kein Fließtext abgeschnitten bei einem 400-Zeichen-Belegsatz
(Screenshot). **nach** AP 18a.

#### AP 18c — Vorladen und Fehlerweg · M · `app/prefetch.py` (neu), `cli/main.py`, `cli/interaction.py`, `gui/`, Tests

**Ziel.** `cli.main._resolve_silently` und `cli.interaction._BlockPrefetch` werden
`app/prefetch.py` (zweiter Anwendungsfall) mit den vier Festlegungen aus technik.md §12:
eigene Profilverbindung im Faden, Fehlschlag erscheint bei der Fortsetzungsfrage, keine
Ausgabe, Abbestellung über `on_progress`. Die Oberfläche startet das Vorladen beim Anzeigen
eines Blocks und bestellt es bei Q/„nein" ab. Fehlschlag mitten im Lauf: Dialog mit
Meldung und Angebot des Teilexports (technik.md §12, „Entschieden 15.09.2026"). **Form
(fest).** `app.prefetch.BlockPrefetch` mit `start`, `cancel`, `is_done`, `join` — die
heutige Schnittstelle. **Prüfung.** Der Test aus `tests/test_cli_main.py`
(`test_prefetch_resolves_the_background_block_with_a_connection_of_its_own`) zieht mit
um; in der Oberfläche: Fehlschlag im Vorladen → `FAILED` mit Meldung, nie ein leerer
Block (Verfälschung: Ausnahme im Faden verschluckt → rot). **nach** AP 18b.

#### AP 19 — Export und Abschluss · M · `gui/`, Tests

**Ziel.** Kartenrichtung wählbar (je Export, konzept.md §6), Zielordner (nativer Dialog,
Vorgabe wie Kommandozeile), Export über `app.export` und `pipeline.export_cards`
(Dateinamen `_2`/`_3` unverändert), Abschluss mit Pfaden, „Ordner öffnen"
(`QDesktopServices`), Bilanz und der Abdeckungszeile aus AP 6 („Mit diesen N Wörtern
verstehst du X % von Kapitel K", beide Werte). „Keine Karte" → Hinweis, kein Export.
**Prüfung.** Nach dem Export steht je Karte eine `card`-Zeile (Regel 6, über die geteilte
Verkettung); zweiter Export legt `_2` an. Screenshot. **nach** AP 18c; weich nach AP 6.

#### AP 24 (erster Lauf) — Gestaltungsdurchsicht · M · **Opus**

Siehe unten; läuft nach AP 19, bevor die Zusatzansichten entstehen.

#### AP 20 — Ganzes Buch in der Oberfläche · M · `gui/`, Tests

**Ziel.** Nach E6 (a): Mehrfachauswahl oder Bereich in der Kapitelliste, Kapitel
nacheinander mit je eigener Triage und eigenem Export, Zwischenstand („Kapitel 3 von 7"),
Abschluss über alle. **Prüfung.** Ansichtsmodell mit zwei Attrappenkapiteln: Buchungen des
ersten wirken im zweiten (Abnahmekriterium 2). **nach** AP 19, AP 4.

#### AP 21 — Schwierigkeitscheck-Ansicht · M · `gui/`, `app/` (Schwellen), Tests

**Ziel.** Vom Startbildschirm ohne Kapitelwahl erreichbar („Buch prüfen"): Fortschritt,
dann je Kapitel ein Balken (unbekannte je 1.000) und die Buchzeile mit Einordnung nach E12.
**Prüfung.** Schwellenworte aus einer Tabelle in `app/`, mit Test je Grenze. Screenshot mit
`tools/dorian_gray.epub`. **nach** AP 20, AP 7.

#### AP 22 — Druckvarianten und Figuren & Orte · M · `gui/`, Tests

**Ziel.** Im Exportschritt wählbar: Kapitelliste, Lesezeichen, je als HTML oder PDF
(AP 9, AP 10), Anhang „Figuren & Orte" (AP 8) — und dieselbe Liste als Ansicht im
Programm. **Prüfung.** Jede Kombination erzeugt die erwarteten Dateien; PDF nur, wenn
`app.pdf` verfügbar, sonst Hinweis statt stillem Weglassen. **nach** AP 21, AP 8 bis 10.

#### AP 23a/b/c — Sicherung, Anki-Import, Einstufungstest in der Oberfläche · je S–M · `gui/`, Tests

**Ziel.** Menü „Profil sichern …" / „Profil ausleiten …" (AP 13); Dialog „Anki-Deck
importieren" mit Feldwahl und Ergebnis samt `unmatched` (AP 11); Einstufungstest als
Alternative zur Niveaufrage beim Anlegen des Profils, rund 30 Fragen, Ergebnis N mit
Bestätigung (AP 12). **Prüfung.** je Dialog jeder Zweig mit Attrappe; `unmatched`
sichtbar (Verfälschung: leer angezeigt → rot). **nach** AP 22 und dem jeweiligen Kern-AP.

#### AP 24 — Gestaltungsdurchsicht · M · **Opus**, zweimal (nach AP 19, nach AP 23)

**Ziel.** Screenshots aller Bildschirme bei beiden Größen gegen Token, Wireframes und die
„verifiziert heißt"-Listen; die Kritikfragen der Recherche („remove one accessory",
Typografiehierarchie, ein orchestrierter Übergang statt verstreuter Effekte);
Tastaturfokus sichtbar, Kontrast je Token-Paar, Mindestgröße ohne Abschneiden. Ergebnis
sind Befunde nach dokumentation.md §10, Nachbesserung als eigenes AP.

### Block D — Tor der Phase 2 · S–M · Dokumente, `git`

**Ziel.** README „Stand"; konzept.md, „Phasenplan": Phase 2 abgenommen mit Datum;
technik.md: erledigte offene Punkte gestrichen (Übersichtstabelle und Abschnitte), neue
aus den Berichten eingetragen; `beobachtungen/` eingefaltet und geleert;
`recherche_hochwertige_UIs_mit_Claude.md` gelöscht (E14: „Entschieden 16.09.2026", was
daraus dauerhaft gilt, steht bereits in technik.md §14 und Abschnitt 7 dieses Plans);
dieses Dokument gelöscht — vorher je `grep -rn bauplan-phase2` und
`grep -rn recherche_hochwertige_UIs_mit_Claude` und je Treffer entscheiden
(dokumentation.md §7, „Vor dem Löschen einer Datei"); `phase-2` per Fast-Forward nach
`main`, Zweigregel in CLAUDE.md zurückgenommen. **nach** allem.

---

## 5. Reihenfolge und Parallelität

```
Fundament   AP 0 → AP 0b → AP 1 → AP 2 → AP 3
                                            │
            ┌───────────────────────────────┴───────────────────────────────┐
Spur B      AP 4 → AP 6 → AP 7 → AP 8 → AP 9 → AP 10 → AP 11 → AP 12       AP 13 (frei)
(Kern)             AP 5 (nach 4, unabhängig vom Rest der Spur)
            │
Spur C      AP 14 → 15 → 16a → 16b → 17 → 18a → 18b → 18c → 19 → 24 → 20 → 21 → 22 → 23a-c → 24
(GUI)                                           ▲          ▲     ▲     ▲      ▲
                                        weich: AP 4    AP 6  AP 7  AP 8-10  AP 11-13
            └───────────────────────────────┬───────────────────────────────┘
Tor         Block D
```

**Was nebeneinander laufen darf.** Spur B und Spur C berühren disjunkte Dateien —
`libreverbum/`, `cli/`, `tools/` gegen `gui/` — mit drei Ausnahmen, die deshalb in Spur C
liegen und dort die Reihenfolge bestimmen: AP 16a (`dictionary.py`), AP 17 (`app/texts.py`
aus `cli/main.py`), AP 18a/18c (`cli/interaction.py`, `cli/main.py`, `app/`). Während
diese drei laufen, ruht Spur B an `cli/` — AP 5 also nicht zeitgleich mit AP 17/18.
**Innerhalb** einer Spur ist die Reihenfolge fest, weil aufeinanderfolgende AP dieselben
Dateien anfassen (`pipeline.py`, `printout.py`, `gui/`).

**Was das Abo hergibt.** Höchstens zwei Agenten, davon höchstens ein Opus. Der stete Zustand
ist deshalb: **ein Sonnet baut (Spur B oder C), ein Opus sieht das zuletzt gebaute AP der
anderen Spur durch.** Zwei Sonnets zugleich nur dort, wo beide Spuren gerade an
disjunkten Dateien sind und keine Durchsicht wartet. Ein Opus-AP (14, 24) belegt den
Opus-Platz allein.

**Weiche Abhängigkeiten** (Pfeile im Bild): Die GUI-AP laufen auch ohne das Kern-AP, zeigen
dann nur die Zeile noch nicht (AP 19 ohne AP 6) oder greifen auf den Vorläufer zurück
(AP 17 ohne AP 4). Spur B soll deshalb **vorlaufen**; sie ist kürzer.

**Abbildung auf den `Workflow`-Mechanismus.** Ein Workflow-Lauf je Runde von vier bis fünf
AP (je AP drei Agenten: Bau, Durchsicht, Nachbesserung — die Größenvorgabe liegt bei
fünfzehn), `meta.phases` = Bau / Durchsicht / Nachbesserung, `pipeline()` mit
Nebenläufigkeit **1** je Modell. Zwischen zwei Runden legt die Hauptsitzung die
Beobachtungen ab, committet nichts selbst und gibt die nächste Runde frei. Der Start eines
Workflows ist eine ausdrückliche Entscheidung von Dominik, kein Automatismus.

---

## 6. Auftragsvorlage

Jeder Auftrag an einen Bauagenten enthält, in dieser Reihenfolge:

1. **Kaltstart.** „Lies CLAUDE.md vollständig, dann die dort genannten Stellen in
   konzept.md, technik.md, dokumentation.md, die dieses AP berührt. Arbeite auf dem Zweig
   `phase-2`. Es läuft ein zweiter Bearbeiter — fremde Änderungen in `git status` sind kein
   Fehler und werden nicht angefasst."
2. **Das AP** aus Abschnitt 4 wörtlich, samt Form der Schnittstellen. Was aus einem
   Bericht übernommen ist, trägt „Vermutung, Quelle: …" (dokumentation.md §9, „Der Auftrag
   trennt Belegtes von Vermutetem").
3. **Umgebung.** `.venv/` aktivieren, `PYTHONPATH=.` für `tools/`, `PYTHONUTF8=1`, Dateien
   nur mit `encoding="utf-8"`, Tests der Oberfläche mit `QT_QPA_PLATFORM=offscreen`. Nicht
   `uv sync`, nicht `uv run`.
4. **Prüfung.** Die vier Torbefehle, `pytest` **ungefiltert in eine Datei** mit Zeitlimit
   ≥ 600 s; die Testzahl und die Übersprungenen gehören in den Bericht. Für jeden neuen
   Test die Verfälschungsprobe (dokumentation.md §5): welcher Test bei welcher Verfälschung
   rot war — Rücknahme durch gezielten Edit oder Scratchpad-Kopie, **nie** `git checkout`.
   Bei einem GUI-AP: Screenshots beider Größen im Scratchpad, Pfade im Bericht, geprüft
   gegen die „verifiziert heißt"-Liste des Bildschirms.
5. **Commit.** Nur die eigenen Dateien namentlich, `git status --short` davor und danach,
   deutsche Nachricht, Betreff sagt *was*; kein Push; Halbfertiges wird gemeldet, nicht
   verbucht.
6. **Bericht.** Was gebaut wurde, die Torergebnisse mit Zahlen, der rote Lauf, offene
   Punkte für technik.md, und wörtlich:

   > ## Beobachtungen zum Ablauf
   > Was hat dich aufgehalten, in die Irre geführt oder zu einer Entscheidung gezwungen, die
   > eigentlich woanders hingehört? Je Punkt eine Zeile, dazu: was es dich gekostet hat, und
   > ob dabei ein falsches Ergebnis hätte durchgehen können. Sonst „nichts".

Der Auftrag an den Durchsehenden nennt statt 2 den Commit, die Wegwerfkopie
(`git archive`, `tools/en-de.sqlite3` und `tools/*.epub` dazu), die Gegenprobe „genau zwei
Übersprungene", Zwischenergebnisse nach jedem Prüfpunkt in eine Datei, und dass die
Kommandozeile beziehungsweise `tools/gui_screenshot.py` wirklich bedient wird
(dokumentation.md §10).

---

## 7. Was aus der Recherche übernommen wird — und was nicht

Quelle: `recherche_hochwertige_UIs_mit_Claude.md` (15.09.2026), geschrieben für
Web-Frontends. Übernommen wird, was technikneutral ist; die Zuordnung zu Qt ist eine
Vermutung dieses Plans und wird in AP 14/15 am Bestand geprüft.

| Empfehlung der Recherche | Hier | Wo |
|---|---|---|
| Auf **eine** Ästhetik festlegen statt „modern"; Token-System (4–6 Farben, 2 Schriftrollen, Abstände, Signaturelement) | übernommen | E11, AP 14, `Theme.qml`, technik.md §14 |
| Keine Standardschriften (Inter, Roboto, Systemschrift) | übernommen — mitgebrachte OFL-Schriften, Lizenz je Schrift belegt | AP 14, `NOTICE` |
| Kompakter Design-Block in CLAUDE.md, unter 200 Zeilen bleiben | übernommen als Kurzblock; CLAUDE.md ist bereits länger, der Block bleibt deshalb bei acht Zeilen und **verweist** | AP 14 |
| Screenshot-Verifikationsschleife: Route öffnen, zwei Größen, Konsole prüfen, gegen Akzeptanzkriterien | übernommen: `tools/gui_screenshot.py`, 1280×800 und Mindestgröße, QML-Warnungen als Fehler, „verifiziert heißt"-Listen | AP 15, jeder GUI-Auftrag |
| Writer/Reviewer mit frischem Kontext | ist Hausordnung (dokumentation.md §10) | — |
| Zwei-Pass mit Selbstkritik („remove one accessory") | übernommen als AP 24 | AP 24 |
| Plan Mode vor Code, stärkeres Modell plant | dieses Dokument; Opus für AP 14/24 | — |
| frontend-design-Skill installieren | **nicht** übernommen: Prozessteil steht oben, Stack-Teil (React/Tailwind) passt nicht; ein Skill im Projekt widerspräche der Dokumentrolle aus CLAUDE.md | — |
| Chrome-DevTools-/Playwright-MCP, shadcn-MCP, Storybook, Figma, 21st, Lighthouse/axe | **nicht** übernommen (Web-Werkzeuge); Kontrast wird aus den Token gerechnet | — |
| Web-Stack React + Tailwind + shadcn | **nicht** übernommen, siehe E1 | — |

---

## 8. Fallen beim Bau der Qt-Oberfläche

Vermutungen aus Erfahrung mit PySide6, **am Bestand zu prüfen**, bevor sie als Regel
gelten; wer eine widerlegt, schreibt das in den Bericht:

- Genau **eine** `QGuiApplication` je Prozess — im Test ein Fixture mit Sitzungsreichweite,
  nie eine je Test.
- Die `QQmlApplicationEngine` und ihre Wurzelobjekte müssen referenziert bleiben, sonst
  räumt Python sie weg und das Fenster verschwindet still.
- `QQuickStyle.setStyle(...)` **vor** dem ersten Laden; danach wirkt es nicht mehr.
- Eigenschaften eines `QObject` für QML brauchen `Property(..., notify=signal)`; ohne
  `notify` bleibt die Anzeige beim alten Wert stehen — der stille Fehlschlag, gegen den
  AP 15 die Warnungen zu Fehlern macht.
- Aus einem Arbeiterfaden nie ein `QObject` des Hauptfadens anfassen; nur Signale senden
  (Qt stellt sie in die Ereignisschleife). `sqlite3`-Verbindungen bleiben im Faden, der sie
  öffnet (technik.md §12, Festlegung 1).
- `grabWindow()` liefert erst nach dem ersten Rendern etwas; im Offscreen-Betrieb vorher
  Ereignisse verarbeiten und auf das Fenster warten (`QTest.qWaitForWindowExposed`).
- Mitgebrachte Schriften über `QFontDatabase.addApplicationFont` **vor** dem Laden von
  QML; der Rückgabewert −1 ist ein Fehlschlag und wird gemeldet (Regel 13).
- Unter Windows die Pfade an QML als `QUrl.fromLocalFile`, nie als Zeichenkette mit
  Backslashes.

---

## 9. Abnahmekriterien Phase 2 (Vorschlag)

Die Phase ist abgenommen, wenn an echten, DRM-freien EPUBs gelingt:

1. **Ein Kapitel in der Oberfläche** von „Buch öffnen" bis zum geschriebenen Deck und zur
   Druckseite, ohne Konsole; Anki importiert das Deck fehlerfrei; das Profil hat die
   Karten (Regel 6). Währenddessen bleibt die Oberfläche bedienbar — der Timer-Test aus
   AP 15 ist der prüfbare Teil von Regel 9, der Augenschein der andere
2. **Drei Kapitel nacheinander**; das dritte zeigt spürbar weniger Einträge als es allein
   gezeigt hätte, weil das Profil zwischen den Kapiteln greift (Zahlen im Bericht)
3. **Abdeckung** wird angezeigt und stimmt an einem Kapitel mit einer Handrechnung nach E5
   überein
4. **Schwierigkeitscheck** ordnet zwei Bücher in der Reihenfolge, die das eigene Lesen
   bestätigt; die Zahl je 1.000 Wortformen steht mit Rezept in technik.md
5. **PDF** entsteht ohne Handgriff und hat dieselbe Blattzahl wie der Browserdruck derselben
   Datei
6. **Lesezeichen** gedruckt, geschnitten, ins Buch gelegt — lesbar
7. **Anki-Import** eines fremden Decks bucht die gefundenen Wörter, nennt die nicht
   gefundenen, und der nächste Kapitellauf zeigt sie nicht mehr
8. **Einstufungstest** liefert ein N, die Vorbelegung damit ist im Profil belegt, und das N
   steht dem Selbstniveau gegenüber im Bericht
9. **Gestaltung**: AP 24 ohne Befund `schwer`; keine Hex-Farbe außerhalb `Theme.qml`
   (Test); keine Systemschrift; Kontrast je Token-Paar ≥ 4,5:1 (Test)
10. Das Tor aus CLAUDE.md ist grün, `pytest` nennt die Testzahl und genau zwei
    Übersprungene, und die Kommandozeile der Phase 1 läuft unverändert durch
    (Abnahmekriterien 1 bis 6 der Phase 1 an `tools/sherlock.epub`)
