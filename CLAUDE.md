# CLAUDE.md

Arbeitsanweisung für Claude Code in diesem Repository.

## Was das Projekt ist

LibreVerbum bereitet den Wortschatz eines Buchkapitels **vor dem Lesen** auf: EPUB
einlesen → Kapitel wählen → Wortschatz extrahieren → gegen das Nutzerprofil filtern →
Triage durch den Nutzer → Hybrid-Übersetzung (Wörterbuch + LLM) → Export nach Anki und
Druck. Einzelheiten in [konzept.md](konzept.md).

**Stand:** Es gibt noch **keinen Anwendungscode**. Im Repository liegen drei
Entscheidungsdokumente, der Bauplan für Phase 1, fünf Messskripte unter `tools/` und seit
dem 12.08.2026 das Projektgerüst: `pyproject.toml`, das leere Kernpaket `libreverbum/`
und `tests/`. Phase 1 (ein vollständiger Durchlauf für ein Kapitel) ist noch nicht
begonnen.

## Die Dokumente und ihre Zuständigkeit

| Datei | beantwortet |
|---|---|
| [konzept.md](konzept.md) | **Was** gebaut wird und warum — Kernablauf, Phasenplan, Abnahmekriterien |
| [technik.md](technik.md) | **Womit** — Sprache, Wörterbuchquelle, Modell, Datenablage, samt Messwerten |
| [dokumentation.md](dokumentation.md) | **Wie** geschrieben und dokumentiert wird — Sprachregel, Begriffe, Docstrings, Regel-Kommentare |
| [bauplan.md](bauplan.md) | **In welcher Reihenfolge** — Teilaufgaben der Phase 1, was parallel geht. Auf Phase 1 begrenzt und fällt mit deren Abnahme weg |

> Die Dokumente beantworten **warum**. Der Code beantwortet **was und wie**.
> Wo der Code das Warum braucht, **verweist** er darauf — er schreibt es nicht ab.

Das gilt auch für diese Datei: Sie navigiert, sie dupliziert keine Begründungen.
Verweisform ist `technik.md §3, „Datenfalle"` — Nummer und Überschrift, nie eine
Zeilennummer.

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
`grep -rn REGEL .` sie auflistet. Beim Bauen am ehesten relevant:

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
  Zwischenspeicher ohne gemessenen Anlass

**Wo eine Regel prüfbar ist, ist sie zu prüfen** (dokumentation.md §5). Testnamen
englisch, Docstring im Wortlaut des Abnahmekriteriums oder der Regel.

**Dateien immer mit `encoding="utf-8"` öffnen.** Unter Windows zerstört die
Systemkodierung sonst still typografische Zeichen im Buchtext.

## Architektur (technik.md §1 und §7)

- **Python als einzige Sprache**, Oberfläche Qt Quick über PySide6
- Der **Kern** — EPUB-Einlesen, Wortschatzextraktion, Profil, Übersetzung, Export — ist
  ein eigenständiges Python-Paket **ohne jeden Bezug zur Oberfläche**. Die Oberfläche
  ruft ihn nur auf. Diese Regel hält den späteren Hybrid, die Testbarkeit und den
  Kommandozeilenzugang offen
- **Modulkarte und Importregel:** zehn Module entlang der sechs Schritte des Kernablaufs.
  Jeder Schritt importiert nur `entities`, verkettet wird allein in `pipeline`. Die Karte
  sagt, wo etwas hingehört — Module entstehen, wenn sie gebraucht werden, nicht vorab
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

Zwei Prüfregeln sind abgeschaltet, weil sie gegen die Sprachregel arbeiten (`RUF001`–`003`
melden Gedankenstrich und typografische Anführungszeichen). Wer sie wieder anschaltet,
liest erst technik.md §6, „Zwei Prüfregeln arbeiten gegen die Hausordnung".

## Daten

| Datei | Inhalt |
|---|---|
| `en-de.sqlite3` | WikDict EN→DE, ~20 MB, wird **heruntergeladen**, nicht mitgeliefert, nicht versioniert |
| `profil.sqlite3` | Nutzerprofil — der langfristige Wert des Programms, gehört nie ins Repository |

Beide **niemals in derselben Datei**, und **keine Fremdschlüssel ins Wörterbuch** —
WikDict-Werte nur als Momentaufnahme (`wikdict_*`). Begründung: technik.md §4.
`PRAGMA user_version` ab der ersten Fassung. Tabellen heißen im Schema `book`,
`chapter`, `lemma`, `sense`, `occurrence`, `event`, `card`.

Zur Laufzeit liegen beide samt `config.toml` im plattformüblichen Nutzerverzeichnis
(`%LOCALAPPDATA%\LibreVerbum\`, unter Linux `~/.local/share/libreverbum/`). **Der Kern
bekommt jeden Pfad als Argument** und kennt keine Vorgabe — die setzt der Aufrufer.
Begründung: technik.md §9.

## `tools/` — die Messskripte

Reproduzieren die Messungen, auf die sich technik.md stützt. Die Wörterbuchdatei
erwarten sie neben sich in `tools/`.

```
python tools/coverage_check.py --fetch-dictionary     # Wörterbuch herunterladen
python tools/coverage_check.py buch.txt               # Abdeckung des Wörterbuchs
python tools/sense_check.py                           # Bedeutungsauswahl durch das Modell
python tools/mwe_check.py buch.txt                    # Mehrwortausdrücke
python tools/nlp_check.py buch.txt                    # spaCy gegen Stanza
python tools/epub_check.py buch.epub                  # EPUB-Struktur und Fließtext
python tools/epub_check.py --summary *.epub           # eine Zeile je Buch
```

Alle bis auf eines kommen mit der Standardbibliothek aus, brauchen also keine
Projektumgebung. **`nlp_check.py` ist die Ausnahme** und verlangt spaCy oder Stanza samt
Modellen: Ein Vergleich der beiden lässt sich nur an den echten Modellen führen, nicht
nachbilden. Das Skript nennt die Installationsbefehle in seinem Kopf.

`sense_check.py` und `mwe_check.py` suchen einen lokalen Modellserver auf den üblichen
Adressen ab (llama-server, LM Studio, Ollama, …) oder nehmen `--url`. Testtexte
(`*.txt`) und `*.sqlite3` sind bewusst nicht versioniert.

## Aktueller Stand

**Entscheidungen 8 und 9 sind am 12.08.2026 gefallen** (technik.md §8 und §9):

- **EPUB ohne Bibliothek** — `zipfile`, `xml.etree`, `html.parser`. EbookLib steht unter
  AGPL-3.0 und scheidet nach Regel 15 aus; gemessen an zwölf Dateien liest die
  Standardbibliothek **570 von 570** Inhaltsdokumenten, und der gewonnene Wortschatz weicht
  um 0,08 % von der Textfassung ab, auf der die Entscheidungen 2 und 5 beruhen
- **Kapitel kommen aus der Navigation**, gezählt nach eindeutigen Zielen. Fehlt sie, gilt
  jedes Dokument der Lesereihenfolge als Kapitel — **mit sichtbarem Hinweis**. Ein Rückfall
  auf Überschriften wurde gemessen und verworfen: Jede Datei mit Überschriften hat auch ein
  Inhaltsverzeichnis. `epub:type` kommt in der Praxis nicht vor, die Trennung von Vorspann
  und Impressum bleibt Heuristik
- **Ablage und Konfiguration** stehen unter „Daten" oben

**Der Bauplan für Phase 1 steht seit dem 12.08.2026 in [bauplan.md](bauplan.md).** Er
teilt Phase 1 in achtzehn Teilaufgaben, hält fest, welche davon gleichzeitig gebaut werden
dürfen, und nennt die vier Vorentscheidungen, die noch Code blockieren — die drei
Bibliotheken aus technik.md §1 samt Lizenzprüfung und die Ablage zur Laufzeit. **Vor der
ersten Zeile Anwendungscode dort nachsehen**, welche Teilaufgabe an der Reihe ist. Die
Triage läuft in Phase 1 über die Kommandozeile; die Qt-Oberfläche kommt nach der Abnahme.

**Entscheidung 7 ist am 12.08.2026 gefallen: die Modulaufteilung des Kerns samt
Importregel** (technik.md §7), zusammen mit den Regeln 13 bis 15 in dokumentation.md §4.
Damit sind die Vorarbeiten abgeschlossen und **die nächste Aufgabe ist Phase 1 selbst** —
der erste Anwendungscode. Die Importregel ist keine Absichtserklärung mehr:
`tests/test_architecture.py` prüft sie.

**Entscheidung 6 ist am 12.08.2026 gefallen: Python 3.12 mit uv, ruff, pytest und mypy**
(technik.md §6). Das Gerüst steht, das Tor oben gilt ab sofort, und **das ganze
Repository besteht es** — `tools/` ist am selben Tag nachgezogen worden. Dass die
Messwerte davon unberührt sind, ist durch einen Vorher-Nachher-Lauf belegt, nicht
angenommen (technik.md §6, „Der Bestand ist nachgezogen"). Die verbliebenen offenen
Punkte stehen dort.

**Entscheidung 5 ist am 12.08.2026 gefallen: spaCy mit `en_core_web_md`** (technik.md
§5). Damit sind alle technischen Vorfragen beantwortet und **Phase 1 kann beginnen**.
Zwei Ergebnisse der Messung wirken sich unmittelbar aufs Bauen aus:

- Der **Eigennamenfilter wirkt auf das Vorkommen, nie auf die Grundform**. Sonst
  verschwinden `red`, `orange`, `street` ganz aus der Triage (technik.md §5)
- Die getrennten Phrasal Verbs sind **gelöst und betrafen 21 %, nicht ~51 %** — die alte
  Zahl steht mit Nachtrag in technik.md, „Messung: Mehrwortausdrücke"

Die Messumgebung liegt in `.venv/` (spaCy + `en_core_web_sm`/`md`), die Testtexte in
`tools/*.txt`. Beides ungetrackt.

Die Sprachregel aus dokumentation.md §1 ist am 12.08.2026 auf den Bestand angewandt
worden: `werkzeuge/` → `tools/`, die drei Skripte englisch benannt, Bezeichner und
Argumente übersetzt, Verweise in technik.md und `.gitignore` nachgezogen. Der Bestand
widerspricht der Regel damit nicht mehr — das war der Zweck, denn wer nach vorhandenem
Code arbeitet, folgt dem Bestand, nicht der Regel.

## Arbeitsweise

- **Erst das Was, dann getrennt das Wie.** Inhaltliche und technische Entscheidungen
  werden nacheinander besprochen. Nicht ungefragt mit Code beginnen — offene Punkte
  stehen in den Dokumenten unter „Offene Punkte" und werden erst entschieden, dann
  gebaut
- **Fertig heißt committet.** Was abgeschlossen ist **und das Tor aus „Prüfen vor
  »fertig«" besteht**, wird committet — ohne Rückfrage; diese Regel ist die Erlaubnis.
  „Läuft" ist dabei kein Eindruck, sondern sind die vier grünen Befehle
  - **Ein Commit je abgeschlossener Sache**, nicht je Sitzung. Liegen zwei Anliegen im
    Arbeitsbaum, werden es zwei Commits
  - Auf `main` und **ohne zu pushen**. Veröffentlichen bleibt eine eigene Entscheidung
  - Nachricht deutsch (dokumentation.md §1). Der Betreff sagt, *was* sich ändert; das
    dauerhafte *warum* gehört in die Dokumente, nicht in die Nachricht
  - **Halbfertiges wird nicht committet**, um einen Stand zu haben. Läuft es nicht, ist
    das zu melden und nicht zu verbuchen
- **Korrigieren: Nachtrag oder überschreiben** (dokumentation.md §7). Eine widerlegte,
  aber plausible Annahme bekommt einen datierten Nachtrag — so wie in konzept.md §5,
  wo die Wendungsmessung eine Konzeptaussage gekippt hat. Ersetzte Festlegungen werden
  dagegen überschrieben; die Historie hat Git. In beiden Fällen gilt: **der gültige
  Stand steht oben**, nie die überholte Fassung zuerst
- **Keine erzeugte Schnittstellenreferenz, keine Änderungshistorie in Dateiköpfen**
  (dafür ist Git da), keine Kommentare, die die Zeile darunter nacherzählen
- Datumsangaben im Format `TT.MM.JJJJ`
