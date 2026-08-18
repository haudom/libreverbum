# CLAUDE.md

Arbeitsanweisung für Claude Code in diesem Repository.

## Was das Projekt ist

LibreVerbum bereitet den Wortschatz eines Buchkapitels **vor dem Lesen** auf: EPUB
einlesen → Kapitel wählen → Wortschatz extrahieren → gegen das Nutzerprofil filtern →
Bedeutungen beschaffen (Wörterbuch + LLM) → Triage durch den Nutzer → Export nach Anki
und Druck. Einzelheiten in [konzept.md](konzept.md).

**Stand:** steht nicht hier, sondern in [bauplan.md](bauplan.md) und in `git log`. Eine
Momentaufnahme in Prosa veraltet mit jeder Teilaufgabe, und diese Datei liest jeder
Bearbeiter zuerst — sie darf ihn nicht in die Irre führen.

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
python tools/ambiguity_check.py buch.txt              # mehrdeutige Grundformen je Kapitel
python tools/nlp_check.py buch.txt                    # spaCy gegen Stanza
python tools/epub_check.py buch.epub                  # EPUB-Struktur und Fließtext
python tools/epub_check.py --summary *.epub           # eine Zeile je Buch
```

Alle bis auf zwei kommen mit der Standardbibliothek aus, brauchen also keine
Projektumgebung. **`nlp_check.py` verlangt spaCy oder Stanza samt Modellen**: Ein Vergleich
der beiden lässt sich nur an den echten Modellen führen, nicht nachbilden; das Skript nennt
die Installationsbefehle in seinem Kopf. **`ambiguity_check.py` verlangt spaCy und den Kern
selbst** (`libreverbum.extraction`, `libreverbum.dictionary`): Gemessen wird, was der Kern
tatsächlich liefert, nicht eine nachgebaute Näherung.

`sense_check.py` sucht einen lokalen Modellserver auf den üblichen Adressen ab
(llama-server, LM Studio, Ollama, …) oder nimmt `--url`; `mwe_check.py` verlangt `--url`.
Testtexte (`*.txt`) und `*.sqlite3` sind bewusst nicht versioniert.

## Aktueller Stand

Er steht in drei Quellen, die sich selbst nachführen — nicht hier:

- **Was als Nächstes gebaut wird:** [bauplan.md](bauplan.md). **Vor der ersten Zeile
  Anwendungscode dort nachsehen**, welche Teilaufgabe an der Reihe ist und welche
  Vorentscheidung sie blockiert
- **Was fertig ist:** `git log --oneline`. Jede Teilaufgabe ist ein Commit, der das Tor
  oben bestanden hat
- **Was gerade jemand anderes bearbeitet:** `git status`. Es laufen regelmäßig zwei
  Bearbeiter gleichzeitig — fremde Änderungen im Arbeitsbaum sind kein Fehler und werden
  weder repariert noch mitcommittet

Die technischen Entscheidungen 1 bis 9 sind gefallen und stehen in technik.md; offen sind
nur E8b (Anki-Bibliothek) und E8c (Druckausgabe), beide in bauplan.md unter Tor 0.

Nicht im Repository, aber zur Arbeit vorhanden: die Umgebung `.venv/` (spaCy mit
`en_core_web_md` und `en_core_web_sm`), das Wörterbuch `tools/en-de.sqlite3`, die
Testtexte `tools/*.txt` und die EPUBs `tools/*.epub`. Tests, die davon abhängen, tragen
`needs_dictionary`, `needs_model` oder `needs_epub` und werden ohne sie übersprungen.

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
- **Jeder Auftrag endet mit „Beobachtungen zum Ablauf"** (dokumentation.md §9), jeder
  Bericht beantwortet ihn. Das ist der einzige Rückweg für das, was einen Bearbeiter
  aufgehalten hat; eingefaltet wird an den Toren aus bauplan.md, nicht nebenbei
- **Korrigieren: Nachtrag oder überschreiben** (dokumentation.md §7). Eine widerlegte,
  aber plausible Annahme bekommt einen datierten Nachtrag — so wie in konzept.md §5,
  wo die Wendungsmessung eine Konzeptaussage gekippt hat. Ersetzte Festlegungen werden
  dagegen überschrieben; die Historie hat Git. In beiden Fällen gilt: **der gültige
  Stand steht oben**, nie die überholte Fassung zuerst
- **Keine erzeugte Schnittstellenreferenz, keine Änderungshistorie in Dateiköpfen**
  (dafür ist Git da), keine Kommentare, die die Zeile darunter nacherzählen
- Datumsangaben im Format `TT.MM.JJJJ`
