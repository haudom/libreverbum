# LibreVerbum

**Den Wortschatz eines Buchkapitels lernen, bevor man es liest — nicht währenddessen.**

[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](pyproject.toml)

LibreVerbum liest ein EPUB, nimmt sich ein Kapitel vor, findet darin die Wörter, die man
noch nicht kennt, beschafft ihre Bedeutung — und gibt sie als Anki-Deck und als Druckseite
aus. Danach lässt sich das Kapitel am Stück lesen: im Idealfall ohne Hilfsmittel, auf
Papier, offline.

## Wozu das gut ist

Wer ein englisches Buch im Original liest, ohne den Wortschatz dafür zu haben, wird ständig
aus dem Lesefluss gerissen: nachschlagen, Faden verlieren, weiterlesen, wieder nachschlagen.
Kindle-Wörterbuch und Übersetzer-Apps setzen alle **beim** Lesen an und verstärken damit
genau diese Unterbrechung.

LibreVerbum dreht die Reihenfolge um. Der zweite Kerngedanke ist ein **mitwachsendes
Nutzerprofil**: Das Programm merkt sich, welche Wörter man bereits kennt, und fragt sie nie
wieder ab. Über mehrere Bücher hinweg wird die Vorbereitung dadurch immer kürzer, obwohl die
Bücher schwerer werden dürfen.

## Der Ablauf

```
EPUB einlesen  →  Kapitel wählen  →  Wortschatz extrahieren
      →  gegen Profil filtern  →  Bedeutungen beschaffen (Wörterbuch + LLM)
      →  Triage durch den Nutzer  →  Export (Anki / Druck)
```

Das Eigentliche steckt im vorletzten Schritt. Ein Sprachmodell allein erfindet
Übersetzungen, die plausibel aussehen und falsch sind. Hier **erzeugt es nichts**: Ein
offline vorliegendes Wörterbuch liefert die Kandidatenliste zu genau diesem Wort, und das
Modell wählt daraus die Bedeutung aus, die zum Satz aus dem Buch passt. Findet das
Wörterbuch nichts, wird der Eintrag als `uncertain` markiert, statt geraten zu werden.

Ebenso zwingend ist die Reihenfolge **Wortart → Grundform → Nachschlagen**: `saw` ist als
Verb die Vergangenheit von *see* und als Substantiv die Säge. Wer zuerst nachschlägt,
bekommt kein Fehlersignal, sondern die falsche Bedeutung — lautlos.

## Stand

**Phase 1 ist abgenommen** (26.08.2026): ein vollständiger Durchlauf für ein Kapitel, von der
EPUB-Datei bis zum importierbaren Anki-Deck und zum geprüften Ausdruck, bedient über die
**Kommandozeile**. Die Qt-Oberfläche gehört zu Phase 2 und ist noch nicht gebaut — der Kern
ist bereits so geschnitten, dass sie ihn nur aufruft ([konzept.md](konzept.md), „Phasenplan").

Was fertig ist, steht in `git log`; was als Nächstes kommt, im Phasenplan.

## Voraussetzungen

| | |
|---|---|
| **Python 3.12** | Die Fassung ist eng gefasst, weil auf ihr die Messungen beruhen ([technik.md](technik.md) §6) |
| **Ein lokaler Modellserver** | Ollama, LM Studio, llama-server — alles mit OpenAI-kompatibler Schnittstelle. Empfehlung aus der Messung: `gemma4:e4b` bei `temperature: 0` ([technik.md](technik.md) §3) |
| **Das WikDict-Wörterbuch EN→DE** | rund 20 MB, wird bezogen und **nicht mitgeliefert** ([technik.md](technik.md) §2) |
| **Ein DRM-freies EPUB** | Project Gutenberg, DRM-freie Käufe. DRM wird nicht umgangen |
| optional | Anki für den Import, ein Browser zum Drucken der HTML-Seite |

Entwickelt und benutzt unter Windows 11. Linux ist Zielplattform ([technik.md](technik.md)
§1), und die Pfadbehandlung ist dafür gebaut — ein vollständiger Durchlauf dort ist bisher
nicht abgenommen.

## Einrichten

```bash
git clone https://github.com/haudom/libreverbum.git
cd libreverbum
uv sync
```

`uv sync` legt `.venv/` an und installiert alles aus `uv.lock` — samt spaCy-Modell
`en_core_web_md`, das nicht auf PyPI liegt und deshalb als Adresse mit Prüfsumme in
`pyproject.toml` steht. Ohne `uv` geht es auch von Hand: ein `venv` mit Python 3.12 und
darin `spacy>=3.8,<3.9`, `genanki>=0.13,<0.14` sowie das Modell-Wheel aus `pyproject.toml`.

Danach die Umgebung aktivieren — `.venv\Scripts\activate` unter Windows,
`source .venv/bin/activate` sonst. Alle folgenden Aufrufe laufen im Wurzelverzeichnis des
Repositoriums; das Paket ist bewusst nicht installiert, sondern wird von dort gefunden.

Das Wörterbuch besorgt das Programm selbst. Fehlt es beim Start, nennt LibreVerbum
Herkunft und Lizenz — WikDict EN→DE, aus Wiktionary über DBnary erzeugt, CC BY-SA — und
fragt einmalig nach; rund 20 MB. Wer die Datei schon hat, legt sie ins Datenverzeichnis
oder trägt sie unter `paths.dictionary` in `config.toml` ein: Die beiden Indizes, die sie
von Hand kopiert nicht mitbringt, legt der Start dann selbst an. **Sie sind der Unterschied
zwischen 1,1 s und 40 s pro Kapitel** ([technik.md](technik.md) §3, „Nachtrag
17.08.2026").

## Benutzen

```bash
python -m cli buch.epub
```

Beim **ersten Aufruf** entsteht `config.toml` im Datenverzeichnis `data/` neben dem
Projekt, und der Lauf endet sofort mit einem Hinweis. Das ist Absicht: In der Vorlage
steht `url = "http://localhost:11434/v1"`, und ein im Heimnetz laufender Modellserver ist
der Regelfall, nicht die Ausnahme. Also erst `model.url` und `model.name` eintragen, dann
denselben Befehl erneut. Beim **zweiten Aufruf** kommt die Frage nach dem Wörterbuch,
falls es noch fehlt, und danach die nach dem Profil, falls es noch keines gibt.

Wird ein Profil neu angelegt, folgt eine dritte Frage: das **Sprachniveau** (A1 bis C1 oder
ausdrücklich „keine Angabe"). Die häufigsten englischen Grundformen der gewählten Stufe
gelten dann als bekannt und tauchen in keiner Triage mehr auf — bei B1 sind das rund 1.700
Grundformen mit gut 8.000 Bedeutungen. Die Frage kommt einmalig, und die Vorbelegung lässt
sich nicht zurücknehmen ([technik.md](technik.md) §11).

Danach läuft der Durchgang:

1. **Kapitel wählen** — die Liste kommt aus dem Inhaltsverzeichnis der Datei. Fehlt es,
   tritt die Lesereihenfolge an seine Stelle, mit sichtbarem Hinweis
2. **Wortschatz** — Beugungsformen werden zusammengefasst, Eigennamen fliegen raus, bereits
   bekannte Wörter ebenso
3. **Bedeutungen** — Wörterbuch schlägt vor, Modell wählt aus, mit Fortschrittsanzeige
4. **Triage** — zuerst die vollständige, nach Häufigkeit sortierte Liste mit der Frage „bis
   zu welcher Nummer kennst du alles?"; ein Tastendruck erledigt damit den ganzen vorderen
   Teil. Erst für den Rest kommt die Einzelabfrage, je Wort mit Belegsatz aus dem Buch und
   Bedeutung: `[k]enne ich`, `[l]ernen`, `[s]kip`, `[q]uit`
5. **Export** — höchstens 25 Wörter und 11 Wendungen je Block; wer mehr will, geht nach
   der Fortsetzungsfrage in den nächsten Block ([technik.md](technik.md) §12)

Nützliche Argumente: `--chapter 3` überspringt die Auswahl, `--card-direction de_en`
dreht die Karten um (dann bleiben Wörter ohne Wörterbucheintrag außen vor — ihre
Vorderseite trüge keine deutsche Bedeutung), `--output-dir` und `--data-dir` verschieben
Ziel- und Datenverzeichnis. `python -m cli --help` zeigt alle.

Heraus kommen zwei Dateien je Lauf, `<Buchtitel>_kapitel<N>.apkg` und `.html`:

- das **Anki-Deck** mit Wort, Bedeutung, Belegsatz und Verschlagwortung nach Buch, Autor
  und Kapitel — direkt importierbar, ohne Bastelei mit CSV-Spalten
- die **Druckseite**, zweispaltig, aus dem Browser heraus zu drucken — auf so viele
  Blätter, wie nötig ([technik.md](technik.md) §12)

Ein zweiter Lauf über dasselbe Kapitel überschreibt nichts, sondern legt sich als
`…_2` daneben. In Anki landet er trotzdem im selben Deck: Deck-Kennung und Notiz-GUID
sind stabil, ein zweiter Import aktualisiert dieselben Notizen, statt Dubletten
anzulegen ([technik.md](technik.md) §8b).

### Wenn ein „Kapitel" ein Drittel des Buchs ist

Manche Dateien — vor allem Calibre-Konvertate — nennen im Inhaltsverzeichnis nur die
groben Teile eines Romans. Die Kapitelliste zeigt dann drei Einträge zu je 60.000 bis
80.000 Wörtern: Die Triage bleibt dank der blockweisen Portionierung benutzbar, die
Zusage, danach ein
Kapitel am Stück zu lesen, wird sie nicht ([technik.md](technik.md) §8, „Nachtrag
28.08.2026: ein Kapitel ist nicht ein Dokument").

Der saubere Weg führt über die Quelle: **calibre kann das Inhaltsverzeichnis neu erzeugen**,
wenn im Text eine wiederkehrende Marke steht, an der sich schneiden lässt. In einem
geprüften Konvertat war das die Zierleiste `= = = = = =` vor jedem Kapitel-Epigraph — 50
Stück, daraus 50 Kapitel mit im Mittel 3.500 Wörtern.

Original wegsichern (EPUB→EPUB überschreibt in calibre das vorhandene Format), dann
**Bücher konvertieren**, Ausgabeformat EPUB, und dort zwei Abschnitte:

| Abschnitt | Feld | Wert |
|---|---|---|
| Struktur-Erkennung | Kapitel erkennen bei (XPath-Ausdruck) | `//h:p[normalize-space(.)="= = = = = ="]` |
| Struktur-Erkennung | Kapitelmarkierung | Seitenumbruch |
| Inhaltsverzeichnis | Erzwinge Verwendung des automatisch erzeugten Inhaltsverzeichnisses | an |
| Inhaltsverzeichnis | Ebene-1-Inhaltsverzeichnis (XPath-Ausdruck) | `//h:p[preceding-sibling::h:p[1][normalize-space(.)="= = = = = ="]]` |

Die beiden Ausdrücke unterscheiden sich absichtlich: Der erste trifft die Marke selbst,
dort soll der **Schnitt** liegen; der zweite trifft den Absatz danach, von dem calibre den
**Namen** des Eintrags nimmt. Mit dem ersten für beides funktioniert es auch, dann heißen
nur alle Einträge gleich. `h:` ist calibres Präfix für den XHTML-Namensraum und muss mit.

Ob es geklappt hat, sagt das Messskript aus `tools/`:

```bash
python tools/epub_check.py neue.epub
```

Stimmen Navigationseinträge und Dokumente der Lesereihenfolge ungefähr überein und liegt
ihre Zahl bei der erwarteten Kapitelzahl, ist die Datei brauchbar. Hat der Text gar keine
wiederkehrende Marke — weder Überschriften noch Seitenumbrüche noch ein Ornament —, hilft
auch calibre nicht weiter.

## Wohin die Daten gehen

Nirgendwohin. Das Buch verlässt den Rechner nicht, der einzige Netzzugriff im Betrieb geht
an den Modellserver — und der läuft lokal oder im eigenen Netz. Das Wörterbuch wird einmal
heruntergeladen.

Zwei Dateien liegen im Datenverzeichnis, nie im Repository (`data/` steht in
`.gitignore`):

- `en-de.sqlite3` — das Wörterbuch, jederzeit neu beziehbar
- `profil.sqlite3` — das Nutzerprofil. Es ist der langfristige Wert des Programms: Was
  darin steht, ist mit jedem gelesenen Kapitel teurer nachzubauen. Sichern heißt vorerst
  schlicht: Datei kopieren, solange kein Lauf läuft — ein Menüpunkt für eine konsistente
  Kopie ist vorgesehen, aber noch nicht gebaut ([technik.md](technik.md) §4, „Sichern und
  Ausleiten")

## Lizenz und Herkunft

Der eigene Code steht unter der **MIT-Lizenz**, siehe [LICENSE](LICENSE). Was von außen
dazukommt:

| Bestandteil | Lizenz | mitgeliefert |
|---|---|---|
| WikDict EN→DE (aus Wiktionary über DBnary) | CC BY-SA | nein, wird bezogen |
| `wordfreq_en_5000.txt` (Grundwortschatz für die Vorbelegung, bearbeitet aus `wordfreq`) | CC BY-SA 4.0 | ja, im Repository |
| spaCy samt `en_core_web_md` | MIT | nein, über `uv sync` |
| genanki (Anki-Erzeugung) | MIT | nein, über `uv sync` |
| PySide6 (Oberfläche, Phase 2) | LGPL | nein, eigene Zusatzgruppe |

Die WikDict-Daten stehen unter CC BY-SA und werden deshalb **nicht** mit einer
GPL-lizenzierten Quelle verschmolzen — die beiden Lizenzen sind nicht verträglich, und
genau daran ist die naheliegende Alternative gescheitert ([technik.md](technik.md) §2,
„Lizenzfalle: nicht verschmelzen").

**Das Repositorium ist damit gemischt lizenziert:** Code MIT, `wordfreq_en_5000.txt`
CC BY-SA 4.0, weil sie bearbeitetes Material aus `wordfreq`s Häufigkeitsdaten ist.
Namensnennungen: siehe [NOTICE](NOTICE). Warum diese Quelle und was sie kostet, steht in
[technik.md](technik.md) §11.

## Dokumentation

Drei Dokumente, jedes mit einer eigenen Frage. Sie beantworten **warum**; der Code
beantwortet was und wie.

| Datei | beantwortet |
|---|---|
| [konzept.md](konzept.md) | **Was** gebaut wird und warum — Kernablauf, Phasenplan, Abnahmekriterien |
| [technik.md](technik.md) | **Womit** — Sprache, Wörterbuchquelle, Modell, Datenablage, samt Messwerten |
| [dokumentation.md](dokumentation.md) | **Wie** geschrieben und dokumentiert wird |

Dazu [CLAUDE.md](CLAUDE.md), die Arbeitsanweisung für jeden, der in diesem Repository
etwas ändert — sie navigiert zu den dreien und wiederholt deren Begründungen nicht.

Die technischen Entscheidungen sind einzeln begründet und mit Messwerten belegt, nicht
behauptet: Warum WikDict und nicht dict.cc, warum spaCy und nicht Stanza, warum je Wort
einzeln gefragt wird und nicht gebündelt, was der Wortartfilter kürzt und was er kostet.

## Entwicklung

In `tools/` liegen die Messskripte, die diese Zahlen nachrechnen — gegen ein anderes Buch,
einen neueren Datenstand oder ein anderes Modell:

```bash
python tools/coverage_check.py buch.txt      # Abdeckung des Wörterbuchs
python tools/ambiguity_check.py buch.txt     # mehrdeutige Grundformen je Kapitel
python tools/epub_check.py buch.epub         # EPUB-Struktur und Fließtext
python tools/nlp_check.py buch.txt           # spaCy gegen Stanza
```

Alle bis auf zwei kommen mit der Standardbibliothek aus und brauchen keine
Projektumgebung. `nlp_check.py` verlangt spaCy **und** Stanza samt Modellen,
`ambiguity_check.py` den Kern selbst und damit `PYTHONPATH=.` — ein Vergleich lässt sich
nur an den echten Werkzeugen führen, nicht an einer Nachbildung.

Vor jeder Änderung, die als fertig gelten soll, laufen diese vier Befehle durch:

```bash
ruff format .
ruff check .
mypy
pytest
```

Von den 431 Tests brauchen 34 das echte Wörterbuch, die echten EPUBs, einen Modellserver
oder einen zweiten Interpreter mit `wordfreq`; ohne sie werden sie übersprungen statt zu
scheitern — und jeder Lauf nennt am Ende, welche das waren.

Das Projekt ist zuerst ein Werkzeug für den eigenen Gebrauch. Fehlerberichte und Fragen sind
willkommen; wer Code beitragen will, liest vorher
[dokumentation.md](dokumentation.md) — Kommentare, Docstrings und Commit-Nachrichten sind
deutsch, Bezeichner englisch, und für beides gibt es Gründe.
