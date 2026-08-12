# CLAUDE.md

Arbeitsanweisung für Claude Code in diesem Repository.

## Was das Projekt ist

LibreVerbum bereitet den Wortschatz eines Buchkapitels **vor dem Lesen** auf: EPUB
einlesen → Kapitel wählen → Wortschatz extrahieren → gegen das Nutzerprofil filtern →
Triage durch den Nutzer → Hybrid-Übersetzung (Wörterbuch + LLM) → Export nach Anki und
Druck. Einzelheiten in [konzept.md](konzept.md).

**Stand:** Es gibt noch **keinen Anwendungscode**. Im Repository liegen drei
Entscheidungsdokumente und drei Messskripte unter `tools/`. Phase 1 (ein vollständiger
Durchlauf für ein Kapitel) ist noch nicht begonnen.

## Die drei Dokumente und ihre Zuständigkeit

| Datei | beantwortet |
|---|---|
| [konzept.md](konzept.md) | **Was** gebaut wird und warum — Kernablauf, Phasenplan, Abnahmekriterien |
| [technik.md](technik.md) | **Womit** — Sprache, Wörterbuchquelle, Modell, Datenablage, samt Messwerten |
| [dokumentation.md](dokumentation.md) | **Wie** geschrieben und dokumentiert wird — Sprachregel, Begriffe, Docstrings, Regel-Kommentare |

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

**Die elf Regeln aus dokumentation.md §4** sind vor jeder Codeänderung dort
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

**Wo eine Regel prüfbar ist, ist sie zu prüfen** (dokumentation.md §5). Testnamen
englisch, Docstring im Wortlaut des Abnahmekriteriums oder der Regel.

**Dateien immer mit `encoding="utf-8"` öffnen.** Unter Windows zerstört die
Systemkodierung sonst still typografische Zeichen im Buchtext.

## Architektur (technik.md §1)

- **Python als einzige Sprache**, Oberfläche Qt Quick über PySide6
- Der **Kern** — EPUB-Einlesen, Wortschatzextraktion, Profil, Übersetzung, Export — ist
  ein eigenständiges Python-Paket **ohne jeden Bezug zur Oberfläche**. Die Oberfläche
  ruft ihn nur auf. Diese Regel hält den späteren Hybrid, die Testbarkeit und den
  Kommandozeilenzugang offen
- **Lizenz jeder neuen Bibliothek vor der Aufnahme prüfen** (starkes Copyleft)

## Daten

| Datei | Inhalt |
|---|---|
| `en-de.sqlite3` | WikDict EN→DE, ~20 MB, wird **heruntergeladen**, nicht mitgeliefert, nicht versioniert |
| `profil.sqlite3` | Nutzerprofil — der langfristige Wert des Programms, gehört nie ins Repository |

Beide **niemals in derselben Datei**, und **keine Fremdschlüssel ins Wörterbuch** —
WikDict-Werte nur als Momentaufnahme (`wikdict_*`). Begründung: technik.md §4.
`PRAGMA user_version` ab der ersten Fassung. Tabellen heißen im Schema `book`,
`chapter`, `lemma`, `sense`, `occurrence`, `event`, `card`.

## `tools/` — die Messskripte

Reproduzieren die Messungen, auf die sich technik.md stützt. Nur Standardbibliothek,
keine Projektumgebung nötig. Die Wörterbuchdatei erwarten sie neben sich in `tools/`.

```
python tools/coverage_check.py --fetch-dictionary     # Wörterbuch herunterladen
python tools/coverage_check.py buch.txt               # Abdeckung des Wörterbuchs
python tools/sense_check.py                           # Bedeutungsauswahl durch das Modell
python tools/mwe_check.py buch.txt                    # Mehrwortausdrücke
```

`sense_check.py` und `mwe_check.py` suchen einen lokalen Modellserver auf den üblichen
Adressen ab (llama-server, LM Studio, Ollama, …) oder nehmen `--url`. Testtexte
(`*.txt`) und `*.sqlite3` sind bewusst nicht versioniert.

## Aktueller Stand

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
- **Widerspricht eine Messung einem Dokument: datierter Nachtrag**, die alte Aussage
  bleibt stehen. So wie der Nachtrag vom 11.08.2026 in konzept.md §5, den die
  Wendungsmessung erzwungen hat
- **Keine erzeugte Schnittstellenreferenz, keine Änderungshistorie in Dateiköpfen**
  (dafür ist Git da), keine Kommentare, die die Zeile darunter nacherzählen
- Datumsangaben im Format `TT.MM.JJJJ`
