# CLAUDE.md

Arbeitsanweisung für Claude Code in diesem Repository.

## Was das Projekt ist

LibreVerbum bereitet den Wortschatz eines Buchkapitels **vor dem Lesen** auf: EPUB
einlesen → Kapitel wählen → Wortschatz extrahieren → Bedeutungen beschaffen (Wörterbuch +
LLM) → gegen das Nutzerprofil filtern → Triage durch den Nutzer → Export nach Anki und
Druck. Einzelheiten in [konzept.md](konzept.md).

**Stand:** steht nicht hier, sondern in `git log` und in den drei Dokumenten unten. Eine
Momentaufnahme in Prosa veraltet mit jeder Teilaufgabe, und diese Datei liest jeder
Bearbeiter zuerst — sie darf ihn nicht in die Irre führen.

## Die Dokumente und ihre Zuständigkeit

| Datei | beantwortet |
|---|---|
| [konzept.md](konzept.md) | **Was** gebaut wird und warum — Kernablauf, Phasenplan, Abnahmekriterien |
| [technik.md](technik.md) | **Womit** — Sprache, Wörterbuchquelle, Modell, Datenablage, samt Messwerten |
| [dokumentation.md](dokumentation.md) | **Wie** geschrieben und dokumentiert wird — Sprachregel, Begriffe, Docstrings, Regel-Kommentare |

> Die Dokumente beantworten **warum**. Der Code beantwortet **was und wie**.
> Wo der Code das Warum braucht, **verweist** er darauf — er schreibt es nicht ab.

Daneben steht [README.md](README.md) — kein viertes Dokument, sondern das Schaufenster: Sie
richtet sich an Fremde auf GitHub, erklärt Zweck, Einrichtung und Bedienung und verweist für
jedes Warum nach innen. Sie begründet nichts selbst. **Ihr Abschnitt „Stand" ist die einzige
Momentaufnahme im Bestand** und deshalb an den Toren einer Phase nachzuziehen — überall sonst
gilt weiter, dass der Stand in `git log` und im Phasenplan steht.

Das gilt auch für diese Datei: Sie navigiert, sie dupliziert keine Begründungen.
Verweisform ist `technik.md §3, „Datenfalle"` — Nummer und Überschrift, nie eine
Zeilennummer.

Dazu, nur für die Dauer der laufenden Phase, das Arbeitsdokument
[bauplan-phase2.md](bauplan-phase2.md): Es zerlegt Phase 2 in Arbeitspakete (Herkunftsangabe
im Quelltext: `bauplan-phase2.md AP 7`) und fällt am Tor der Phase 2 weg — wie `bauplan.md`
am Tor der Phase 1 (Blockquote unten). Was daraus dauerhaft gilt, wandert vorher in die drei
Dokumente oben.

> **`bauplan.md T13` im Quelltext ist eine Herkunftsangabe, kein Verweis.** Der Bauplan
> hat die Phase 1 in die Teilaufgaben T1 bis T18 geschnitten und ist mit deren Abnahme am
> 26.08.2026 weggefallen; was daraus dauerhaft gilt, steht in den drei Dokumenten oben.
> Die Marken bleiben stehen, weil sie sagen, aus welchem Schritt eine Stelle stammt —
> nachzulesen mit `git show 84c8895:bauplan.md` (der letzte Stand der Datei).

## Harte Regeln

**Sprachregel** (dokumentation.md §1) — die am leichtesten verletzte Regel, weil das
Projekt deutsch ist:

> Was der Übersetzer liest, ist englisch. Was ein Mensch in Sätzen liest, ist deutsch.

- **Englisch:** Bezeichner, Dateinamen, Tabellen- und Spaltennamen
- **Deutsch:** Docstrings, Kommentare, Commit-Nachrichten, Oberflächentexte,
  Fehlermeldungen, Protokollausgaben
- **Nie übersetzt:** Namen aus Fremdquellen (`token.lemma_`, `token.pos_`, WikDicts
  `sense`, `score`, `lexentry`, `written_rep`). Eigene Momentaufnahmen davon tragen das
  Präfix `wikdict_`
- Neue Begriffe kommen in die Tabelle in dokumentation.md §2, **bevor** der erste
  Bezeichner damit entsteht. Dort nachsehen, statt einen zweiten Namen für dasselbe Ding
  zu erfinden

**Die fünfzehn Regeln aus dokumentation.md §4** sind vor jeder Codeänderung dort
nachzulesen; im Code werden sie als `# REGEL (quelle, „stichwort"): …` markiert, damit
`grep -rn REGEL .` sie auflistet. **Die Marke bleibt dafür reserviert** — ein Befund aus
einer Durchsicht trägt `# (Befund 4, Review Runde 1): …`. Beim Bauen am ehesten relevant:

- Reihenfolge **Wortart → Grundform → Nachschlagen** ist zwingend (technik.md, „Warum
  die Reihenfolge zwingend ist"). Der `saw`-Fall scheitert sonst *leise*
- Das Modell **wählt aus einer Liste**, es erzeugt nie frei. Kandidaten ohne
  Wörterbucheintrag werden `uncertain` markiert
- Zeilen ohne `sense`-Text **nicht** wegfiltern (36 % der Zeilen, systematisch die
  Hauptbedeutungen)
- Bei jedem Modellaufruf `reasoning_effort: "none"`
- NLP- und Modellaufrufe nie im Oberflächen-Thread
- **Kein `except`, das den Fehler nur protokolliert und weiterläuft.** Ein Fehlschlag wird
  im Ergebnis sichtbar — Abbruch mit Meldung oder markierter Eintrag (`uncertain`)
- **Gebaut wird, was die aktuelle Phase verlangt.** Kein Konfigurationsschalter ohne
  zweiten Anwendungsfall, keine Abstraktion über einer einzigen Umsetzung, kein
  Zwischenspeicher ohne gemessenen Anlass. Das begrenzt **Verhalten**, nicht Struktur:
  Datenstrukturen entstehen vollständig, weil ein nachgereichtes Teilstück Migration heißt

**Wo eine Regel prüfbar ist, ist sie zu prüfen** (dokumentation.md §5). Testnamen
englisch, Docstring im Wortlaut des Abnahmekriteriums oder der Regel. Dazu zwei Regeln
darüber, *woran* geprüft wird:

- Was über den **Inhalt einer Fremdquelle** behauptet wird, wird zusätzlich gegen das echte
  Gegenüber geprüft — `needs_dictionary` für `tools/en-de.sqlite3`, die echten `tools/*.epub`.
  Beim Modellserver stattdessen die **Attrappe abgleichen**, nicht die Trefferquote messen
- Ein neuer Test gilt erst als Test, wenn er **einmal gegen eine absichtlich falsche
  Umsetzung rot** war. Welcher Test bei welcher Verfälschung fiel, gehört in den Bericht

**Dateien immer mit `encoding="utf-8"` öffnen.** Unter Windows zerstört die
Systemkodierung sonst still typografische Zeichen im Buchtext.

## Architektur (technik.md §1, §7 und §14)

- **Python als einzige Sprache**, Oberfläche Qt Quick über PySide6
- Der **Kern** — EPUB-Einlesen, Wortschatzextraktion, Profil, Übersetzung, Export — ist
  ein eigenständiges Python-Paket **ohne jeden Bezug zur Oberfläche**. Die Oberfläche
  ruft ihn nur auf. Diese Regel hält den späteren Hybrid, die Testbarkeit und den
  Kommandozeilenzugang offen
- **Modulkarte und Importregel:** zehn Module entlang der sechs Schritte des Kernablaufs.
  Jeder Schritt importiert nur `entities`, verkettet wird allein in `pipeline`. Die Karte
  sagt, wo etwas hingehört — Module entstehen, wenn sie gebraucht werden, nicht vorab
- **Drei Pakete neben dem Kern:** `cli/` (Kommandozeile, Phase 1, seit Phase 2
  eingefroren mit den Ausnahmen `--chapters` und `--assess`), `gui/` (Qt-Oberfläche,
  Phase 2) und `app/` (Anwendungsschicht — Datenverzeichnis, `config.toml`,
  Modellauflösung, Exportnamen, Triage-Buchung, Vorladen; ohne Qt, ohne Konsole).
  **Importrichtung:** `app/` importiert den Kern, wird von `cli/` und `gui/` importiert,
  vom Kern nie; `cli/` und `gui/` importieren sich nicht gegenseitig.
  `tests/test_architecture.py` prüft seit AP 1, dass der Kern keines der drei Pakete
  importiert (`FORBIDDEN_IN_CORE`, vormals `GUI_PACKAGES` — umbenannt in der Durchsicht von
  907ab02, Befund 5, weil `app/` selbst keine Oberfläche ist), und dass `app/` seinerseits
  weder `cli` noch `gui` noch eine Oberflächenbibliothek importiert — bis `app/` mit AP 3
  entsteht, überspringt sich dieser zweite Teil sichtbar mit Begründung statt
  stillschweigend nichts zu prüfen. Die Ausnahme `app/pdf.py` aus E7 (b) ist dabei noch
  nicht eingebaut, weil E7 noch nicht entschieden ist (Regel 14). Begründung: technik.md §14
- **Lizenz jeder neuen Bibliothek vor der Aufnahme prüfen** (Regel 15, starkes Copyleft)

## Prüfen vor „fertig" (technik.md §6)

Python 3.12, Abhängigkeiten in `pyproject.toml`, Sperrdatei `uv.lock`. Diese vier
Befehle laufen bei aktiver `.venv/`, **bevor** eine Änderung als fertig gilt — alle vier
müssen durchgehen:

```
ruff format .      # formatiert
ruff check .       # prüft Regeln
mypy               # prüft Typen (nur libreverbum/ und tests/)
pytest             # führt Tests aus
```

> **Nicht `uv sync` und nicht `uv run`.** Beide bringen die Umgebung auf den Stand von
> `pyproject.toml` und entfernen dabei `en_core_web_sm`, das `nlp_check.py` für den
> Vergleich aus technik.md §5 braucht. Neue Pakete mit `pip` in die bestehende `.venv/`,
> danach `uv lock`. Begründung: technik.md §6, „Falle: `uv sync` beschneidet die
> Messumgebung".

> **`pytest` läuft rund 145 s** — über dem 120-Sekunden-Zeitlimit mancher Werkzeuge, die
> Befehle ausführen, und zwei Läufe sind deshalb schon unbeabsichtigt in den Hintergrund
> gefallen. Der Lauf gehört deshalb in eine Datei, **ungefiltert** — nie durch `| tail`
> oder ähnliches gefiltert, das hat schon eine **leere** Ergebnisdatei bei gemeldetem
> „exit code 0" erzeugt, ohne ablesbare Testzahl —, mit großzügigem Zeitlimit oder im
> Hintergrund. Die Testzahl gehört zum Ergebnis: „exit 0" ohne Zählwerk sieht aus wie ein
> grünes Tor, sagt aber nicht, ob 559 Tests liefen oder 30.

Zwei Prüfregeln sind abgeschaltet, weil sie gegen die Sprachregel arbeiten (`RUF001`–`003`
melden Gedankenstrich und typografische Anführungszeichen). Wer sie wieder anschaltet,
liest erst technik.md §6, „Zwei Prüfregeln arbeiten gegen die Hausordnung".

**Ergänzung für die Oberfläche (seit Phase 2, technik.md §14, ab AP 1).** Tests, die
`PySide6` brauchen, sollen die Marke `needs_gui` tragen und mit
`QT_QPA_PLATFORM=offscreen` laufen (`conftest.py` soll das setzen, eine
`QGuiApplication` je Testlauf) — heute, vor AP 1, kennt `conftest.py` weder die Marke
noch die Umgebungsvariable. Das Tor allein wird bei einem GUI-AP nicht reichen: Dazu
kommt die Screenshot-Prüfschleife — `tools/gui_screenshot.py <screen> <png>` soll bei
1280×800 und bei der Mindestgröße rendern, QML-Warnungen sollen als Fehlschlag gelten,
geprüft werden soll gegen eine vorab notierte „verifiziert heißt"-Liste des Bildschirms;
das Skript entsteht erst in AP 15. Ohne sie meldet ein Agent auch bei kaputter Seite
Erfolg.

**Nach den vier Befehlen folgt die Durchsicht.** Sie ist kein fünfter Befehl, sondern die
Antwort auf eine andere Frage: Das Tor prüft **Form** — ob das Gebaute das Richtige tut,
prüft es nicht. Die Durchsicht sucht den **stillen Fehlschlag** — das leere, unmarkierte
oder unbemerkt falsche Ergebnis bei vier grünen Befehlen — und **macht nicht derselbe
Bearbeiter**, der gebaut hat. Ihr Ergebnis sind Befunde mit Ort, Wirkung und Schwere
(`schwer`/`mittel`/`leicht`); `schwer` und `mittel` werden nachgebessert. Ausführlich:
dokumentation.md §10, „Die Durchsicht".

**Das Tor ist auf den Bauenden geschrieben.** Wer *prüft*, während ein zweiter Bearbeiter im
Arbeitsbaum steht, nimmt stattdessen `ruff format --check .` und lässt `pytest` nur auf den
betroffenen Dateien laufen: `ruff format .` formatiert fremde Arbeit mit, und ein
vollständiger Lauf zeigt Rot, das dem anderen gehört — „grün" ist bei zwei Bearbeitern nur
je Datei eine Aussage. Den vollständigen Lauf macht die verkettende Stelle zwischen den
Runden.

**Die Durchsicht prüft gar nicht im Arbeitsbaum**, sondern gegen `git archive <commit>` in
einem Wegwerfordner — `tools/en-de.sqlite3` und `tools/*.epub` gehören mit hinein. Die
Gegenprobe: Die Schlusszeile von `pytest` muss **zwei** Übersprungene nennen, wenn PySide6
installiert ist — `needs_model` und `needs_wordfreq` —, und **drei**, wenn nicht: `needs_gui`
kommt dann als dritte Marke dazu. Meldet der Lauf stattdessen rund fünfunddreißig, ist die
Kopie missraten; meldet er einen weniger als hier genannt, steht `LIBREVERBUM_MODEL_URL`
oder `LIBREVERBUM_WORDFREQ_PYTHON` noch in der Umgebung (falscher Alarm, kein falsches
Grün). Begründung: dokumentation.md §10, „Woran sie prüft: gegen den Commit, nicht gegen den
Arbeitsbaum". (Zwischen AP 1 und AP 3 zählte ein dritter, von PySide6 unabhängiger
Übersprungener dazu, solange das Paket `app/` noch nicht existierte — seit AP 3 (`421cb95`)
ist `app/` angelegt, und dieser Skip ist weg.)

## Daten

| Datei | Inhalt |
|---|---|
| `en-de.sqlite3` | WikDict EN→DE, ~20 MB, wird **heruntergeladen**, nicht mitgeliefert, nicht versioniert |
| `profil.sqlite3` | Nutzerprofil — der langfristige Wert des Programms, gehört nie ins Repository |

Beide **niemals in derselben Datei**, und **keine Fremdschlüssel ins Wörterbuch** —
WikDict-Werte nur als Momentaufnahme (`wikdict_*`). Begründung: technik.md §4.
`PRAGMA user_version` ab der ersten Fassung, seit dem 31.08.2026 auf **2**. Tabellen heißen
im Schema `book`, `chapter`, `lemma`, `sense`, `occurrence`, `event`, `card`, `learner` —
acht seit Fassung 2 (technik.md §4, „Fassung 2").

Zur Laufzeit liegen beide samt `config.toml` in `data/` neben dem Projekt, solange
LibreVerbum aus dem Quellbaum läuft (seit 27.08.2026, vorher im Nutzerverzeichnis).
**Der Kern bekommt jeden Pfad als Argument** und kennt keine Vorgabe — die setzt der
Aufrufer. Begründung: technik.md §9.

Keine Nutzerdatei, sondern ein **Programmbestandteil** im Paket ist dagegen
`libreverbum/wordfreq_en_5000.txt`, die eingefrorene Grundwortschatzliste für die
Vorbelegung des Profils. Sie steht als einzige Datei unter CC BY-SA 4.0 statt unter der
MIT-Lizenz daneben — das Repositorium ist gemischt lizenziert. Begründung: technik.md §11.

## `tools/` — die Messskripte

Reproduzieren die Messungen, auf die sich technik.md stützt. Die Wörterbuchdatei
erwarten sie neben sich in `tools/`.

```
python tools/coverage_check.py --fetch-dictionary     # Wörterbuch herunterladen
python tools/coverage_check.py buch.txt               # Abdeckung des Wörterbuchs
python tools/sense_check.py                           # Bedeutungsauswahl durch das Modell
python tools/mwe_check.py buch.txt                    # Mehrwortausdrücke
python tools/ambiguity_check.py buch.txt              # mehrdeutige Grundformen je Kapitel
python tools/bundle_check.py buch.txt                 # Bündelgrößen gegen Einzelanfragen
python tools/nlp_check.py buch.txt                    # spaCy gegen Stanza
python tools/epub_check.py buch.epub                  # EPUB-Struktur und Fließtext
python tools/epub_check.py --summary *.epub           # eine Zeile je Buch
python tools/print_fit_check.py                       # Blattkapazität, echt gedruckt
python tools/build_wordfreq_preset.py …               # erzeugt statt zu messen (s. u.)
```

Alle bis auf fünf kommen mit der Standardbibliothek aus, brauchen also keine
Projektumgebung. **`nlp_check.py` verlangt spaCy oder Stanza samt Modellen**: Ein Vergleich
der beiden lässt sich nur an den echten Modellen führen, nicht nachbilden; das Skript nennt
die Installationsbefehle in seinem Kopf. **`ambiguity_check.py` und `bundle_check.py`
verlangen spaCy und den Kern selbst** (`libreverbum.extraction`, `libreverbum.dictionary`):
Gemessen wird, was der Kern tatsächlich liefert, nicht eine nachgebaute Näherung. Die
übrigen beiden — `print_fit_check.py` und `build_wordfreq_preset.py` — stehen unten.

**`build_wordfreq_preset.py` misst nicht, es erzeugt** — als einziges Skript hier: Es
schreibt `libreverbum/wordfreq_en_5000.txt`, einen ausgelieferten Programmbestandteil
(technik.md §9, „Die Regel gilt für Nutzerdaten, nicht für Programmbestandteile"). Dafür
läuft es zweistufig in **zwei** Umgebungen — `export-forms` braucht `wordfreq`, das bewusst
nie in `.venv/` landet, `build` braucht spaCy mit `en_core_web_md`, das nur dort liegt.
Einzelheiten im Kopf des Skripts.

**Wer ein Skript aufruft, das den Kern importiert, braucht `PYTHONPATH=.`** — das Paket
`libreverbum` ist in `.venv/` nicht installiert, und ohne die Zuweisung bricht
`ambiguity_check.py` mit `ModuleNotFoundError` ab. Dasselbe gilt für `bundle_check.py`
(eigener Modulkopf: „den Kern `libreverbum` selbst (`extraction`, `dictionary`)") und für
`print_fit_check.py` (`libreverbum.printout`, `libreverbum.entities`) — Letzteres druckt
die echte Druckseite des Kerns statt eine nachgebaute (technik.md §8c, „Offene Punkte"),
und braucht daneben einen echten, lokal gefundenen Browser (Edge oder Chrome, headless) für
den Ausdruck zu PDF. Aufzurufen also aus dem Wurzelverzeichnis des Repositoriums.

`sense_check.py` sucht einen lokalen Modellserver auf den üblichen Adressen ab
(llama-server, LM Studio, Ollama, …) oder nimmt `--url` — **ohne** `/v1`, das hängen die
Skripte selbst an; in `config.toml` steht dieselbe Adresse dagegen **mit** `/v1`
(technik.md §9, „Zwei Fallen beim Eintragen von Hand"). `mwe_check.py` verlangt `--url`.
Testtexte (`*.txt`) und `*.sqlite3` sind bewusst nicht versioniert.

## Aktueller Stand

Er steht in drei Quellen, die sich selbst nachführen — nicht hier:

- **Was fertig ist:** `git log --oneline`. Jede Teilaufgabe ist ein Commit, der das Tor
  oben bestanden hat
- **Was als Nächstes gebaut wird:** [konzept.md](konzept.md), „Phasenplan" — welche Phase
  an der Reihe ist und was zu ihr gehört. **Vor der ersten Zeile Anwendungscode** dazu die
  offenen Punkte: konzept.md, „Bewusst offen" für die inhaltlichen, technik.md, „Offene
  Punkte im Überblick" für die technischen — die Tabelle am Kopf von
  [technik.md](technik.md) verweist auf die einzelnen „Offene Punkte"-Abschnitte, ersetzt
  aber deren Lektüre für den Kaltstart. Was dort steht, wird erst entschieden, dann gebaut.
  Innerhalb der laufenden Phase zerlegt [bauplan-phase2.md](bauplan-phase2.md) das in
  Arbeitspakete — Vorlage, kein Ersatz für den Phasenplan; fällt am Tor der Phase 2 weg
- **Was gerade jemand anderes bearbeitet:** `git status`. Es laufen regelmäßig zwei
  Bearbeiter gleichzeitig — fremde Änderungen im Arbeitsbaum sind kein Fehler und werden
  weder repariert noch mitcommittet

**Zwei Bearbeiter gleichzeitig lohnen sich nur bei disjunkten Dateien.** Zweimal starben
beide gleichzeitig an Sitzungslimits und ließen verschränkte Halbarbeit in derselben Datei
zurück; einmal kostete eine falsche Verortung des anderen eine Stunde (dokumentation.md §9,
„Der Auftrag trennt Belegtes von Vermutetem"). Ab dem Punkt, an dem zwei Teilaufgaben
dieselben Dateien berühren, lief es einspurig glatter.

Die technischen Entscheidungen stehen sämtlich in technik.md — auch die zuletzt gefallenen
E8b (Anki-Erzeugung, §8b) und E8c (Druckausgabe, §8c).

Nicht im Repository, aber zur Arbeit vorhanden: die Umgebung `.venv/` (spaCy mit
`en_core_web_md` und `en_core_web_sm` — Wiederherstellung nach einem Rechnerwechsel:
`.venv/Scripts/python -m spacy download en_core_web_sm` entsprechend `en_core_web_md`;
beide liegen bereits in `.venv/`, hier nur dokumentiert, nicht auszuführen. Ein grünes
`pytest` ist kein Nachweis einer vollständigen Arbeitsumgebung — kein Prüfbefehl merkt ein
fehlendes `en_core_web_sm`, das bewusst nicht in `pyproject.toml` steht, technik.md §6,
„Falle: `uv sync` beschneidet die Messumgebung"), das Wörterbuch `tools/en-de.sqlite3`, die
Testtexte `tools/*.txt` und die EPUBs `tools/*.epub`, darunter `tools/dune.epub`
(Calibre-Konvertat mit `_split_NNN`-Dokumenten, technik.md §8, „Ein Kapitel ist nicht ein
Dokument"). Tests,
die davon abhängen, tragen `needs_dictionary`, `needs_model`, `needs_epub`,
`needs_calibre_split_epub` oder `needs_wordfreq` und werden ohne sie übersprungen.

## Arbeitsweise

- **Erst das Was, dann getrennt das Wie.** Inhaltliche und technische Entscheidungen
  werden nacheinander besprochen. Nicht ungefragt mit Code beginnen — offene Punkte
  stehen in den Dokumenten unter „Offene Punkte" und werden erst entschieden, dann
  gebaut
- **Fertig heißt committet.** Was abgeschlossen ist **und das Tor aus „Prüfen vor
  »fertig«" besteht**, wird committet — ohne Rückfrage; diese Regel ist die Erlaubnis.
  „Läuft" ist dabei kein Eindruck, sondern sind die vier grünen Befehle
  - **Die vier Befehle erlauben den Commit, sie schließen die Teilaufgabe nicht ab.** Das
    tut erst die Durchsicht (dokumentation.md §10, „Die Durchsicht"); ihre Befunde der
    Stufen `schwer` und `mittel` werden nachgebessert und ergeben nach derselben Regel
    ihren eigenen Commit
  - **Ein Commit je abgeschlossener Sache**, nicht je Sitzung. Liegen zwei Anliegen im
    Arbeitsbaum, werden es zwei Commits
  - **Seit Phase 2 (E2, technik.md §14) auf dem Zweig `phase-2`**, alle Commits der
    Phase dorthin, weiterhin **ohne zu pushen**. Veröffentlichen bleibt eine eigene
    Entscheidung. `main` bleibt bis zum Tor der Phase 2 der abgenommene Stand der
    Phase 1 und wird dort per Fast-Forward nachgezogen. Diese Zeile fällt am Tor der
    Phase 2 zurück auf „auf `main`"
  - **Nur die eigenen Dateien werden gestagt** — `git add` mit den Dateien namentlich, nie
    `git add -A` und nie `git commit -a`; `git status --short` vor und nach dem Commit.
    Es laufen regelmäßig zwei Bearbeiter gleichzeitig (siehe „Aktueller Stand" oben), und
    zweimal lagen deren fremde, unversionierte Änderungen im Arbeitsbaum. Mit `git add -A`
    wäre die fremde, halbfertige Arbeit mitgewandert — an einer der beiden Stellen war eine
    zugehörige Testdatei zu dem Zeitpunkt noch nicht angepasst, der Commit also rot gewesen
  - Nachricht deutsch (dokumentation.md §1). Der Betreff sagt, *was* sich ändert; das
    dauerhafte *warum* gehört in die Dokumente, nicht in die Nachricht
  - **Halbfertiges wird nicht committet**, um einen Stand zu haben. Läuft es nicht, ist
    das zu melden und nicht zu verbuchen
- **Jeder Auftrag endet mit „Beobachtungen zum Ablauf"** (dokumentation.md §9), jeder
  Bericht beantwortet ihn. Das ist der einzige Rückweg für das, was einen Bearbeiter
  aufgehalten hat; eingefaltet wird an den Toren einer Phase, nicht nebenbei
  - **Wer den Bericht entgegennimmt, legt dessen Beobachtungen sofort unter
    `beobachtungen/` ab** — eine Datei je Bericht, bevor irgendetwas anderes geschieht.
    Wer es aufschiebt, hat sie nur im Sitzungsprotokoll, und das liegt außerhalb des
    Repositoriums. In Phase 1 tat `nacharbeit.md` dieselbe Arbeit — bei T18 aufgelöst und
    gelöscht, nachzulesen mit `git show abe42cf^:nacharbeit.md`. Form, Inhalt und was
    **nicht** hineingehört: dokumentation.md §9, „Wo die Beobachtungen liegen"
  - Das Verzeichnis ist zwischen zwei Toren gefüllt und danach leer. **Ist es beim
    Kaltstart nicht leer, steht ein Einfalten aus** — das ist seine zweite Aufgabe
- **Korrigieren: Nachtrag oder überschreiben** (dokumentation.md §7). Eine widerlegte,
  aber plausible Annahme bekommt einen datierten Nachtrag — der Musterfall stand bis zum
  Einfalten der Phase-1-Nachträge in konzept.md §5, wo die Wendungsmessung eine
  Konzeptaussage gekippt hat (`git show b663678:konzept.md`). Ersetzte Festlegungen werden
  dagegen überschrieben; die Historie hat Git. In beiden Fällen gilt: **der gültige
  Stand steht oben**, nie die überholte Fassung zuerst
- **Keine erzeugte Schnittstellenreferenz, keine Änderungshistorie in Dateiköpfen**
  (dafür ist Git da), keine Kommentare, die die Zeile darunter nacherzählen
- Datumsangaben im Format `TT.MM.JJJJ`
