"""Wörterbuch — Auswahlliste je Grundform und Wortart aus WikDict, samt Erstbezug.

Aufgabe
-------
Schritt 5 des Kernablaufs (konzept.md §5), erste Hälfte: der einzige Zugriff auf
`en-de.sqlite3` (technik.md §7, Modulkarte). `candidates` liefert die Kandidaten, aus
denen `translation` — Schritt 5, zweite Hälfte — die im Kontext passende Bedeutung wählt.
`fetch_dictionary` liefert dazu den Erstbezug der Datei selbst (bauplan.md T6):
Herunterladen, Prüfung, von Hand hinterlegte Datei, der Index auf
`translation(written_rep)`.

Voraussetzungen
---------------
`candidates` erwartet die Grundform bereits wortartbestimmt (`Lemma.pos`, spaCys
`token.pos_`): Die Reihenfolge Wortart → Grundform → Nachschlagen ist zwingend (technik.md,
„Warum die Reihenfolge zwingend ist"). `fetch_dictionary` erwartet nur den Zielpfad;
welches Verzeichnis das ist, entscheidet allein der Aufrufer (technik.md §9).

Liefert
-------
Je Grundform und Wortart eine nach `score` absteigend sortierte Liste von `Sense`
(bauplan.md T5). Zeilen ohne `sense`-Text bleiben darin (Regel 1); `label` liefert für sie
die vorgeschriebene Beschriftung. Wählt selbst keine Bedeutung aus und übersetzt nichts
frei — das bleibt `translation` vorbehalten.

`fetch_dictionary` lädt die Datei, falls sie fehlt, prüft Vollständigkeit und Schema und
legt den Index an — auch für eine bereits vorhandene, von Hand hinterlegte Datei, die den
Index ebenfalls nicht mitbringt. `SOURCE_NOTICE` ist der Text zu Herkunft und Lizenz, den
der Aufrufer beim ersten Bezug anzeigen kann (technik.md §2, „Warum nicht mitgeliefert").
"""

from __future__ import annotations

import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from libreverbum.entities import Lemma, Sense

# REGEL (dokumentation.md §4 Regel 1, technik.md §3 „Datenfalle: Einträge ohne
# Bedeutungstext"): Zeilen ohne sense-Text nicht wegfiltern. 36 % aller Zeilen, systematisch
# die Hauptbedeutungen (watch → „Uhr", draw → „zeichnen"). Wer sie entfernt, erzeugt
# scheinbare Wörterbuchlücken. `entities.Sense` hält `wikdict_sense` für diese Zeilen
# bewusst auf `None` — die Beschriftung unten ist reine Anzeige, kein gespeicherter Wert.
NO_SENSE_LABEL = "Hauptbedeutung, ohne nähere Angabe"

# REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): Wortart vor Grundform vor
# Nachschlagen — `saw` als Verb darf nicht die Säge liefern. WikDicts `lexentry` trägt die
# Wortart als eigenes Segment (`eng/<wort>__<Wortart>__<n>`) unter deren eigenem Namen.
# Nur die fünf Wortarten, die T3s Inhaltswortfilter dieser Phase überhaupt vorlegt (Regel 14,
# kein Vorrat auf Vorrat): Substantiv, Verb, Adjektiv, Adverb, Interjektion. `PROPN` fehlt
# bewusst — T3 setzt `chosen_pos` nie darauf, und T7 filtert `Proper_noun` ohnehin weg.
_WIKDICT_POS = {
    "NOUN": "Noun",
    "VERB": "Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "INTJ": "Interjection",
}


def label(sense: Sense) -> str:
    """Beschriftung für die Auswahlliste: `wikdict_sense`, oder — fehlt er — Regel 1s feste
    Beschriftung `NO_SENSE_LABEL`."""
    return sense.wikdict_sense or NO_SENSE_LABEL


def _wikdict_pos(lexentry: str | None) -> str | None:
    """Die Wortart aus WikDicts `lexentry`-Kennung (`eng/<wort>__<Wortart>__<n>`)."""
    if lexentry is None or "__" not in lexentry:
        return None
    return lexentry.split("__")[1]


def candidates(dictionary_path: Path, lemma: Lemma) -> list[Sense]:
    """Auswahlliste für eine Grundform und Wortart, nach `score` absteigend.

    Regel 1 (dokumentation.md §4): Zeilen ohne `sense`-Text bleiben in der Liste — sie sind
    systematisch die Hauptbedeutungen, keine Lücken. Die Wortart ist Teil der Abfrage: `saw`
    als Verb liefert nur „sägen", nie die Säge (technik.md, „Warum die Reihenfolge zwingend
    ist"). Eine fehlende oder unlesbare Wörterbuchdatei bricht sichtbar ab (Regel 13) statt
    eine leere Liste zurückzugeben, die wie „kein Eintrag gefunden" aussähe.
    """
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    try:
        wikdict_pos = _WIKDICT_POS[lemma.pos]
    except KeyError as error:
        raise ValueError(f"Keine WikDict-Wortart für {lemma.pos!r} hinterlegt.") from error

    con = sqlite3.connect(dictionary_path)
    try:
        # REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): lexentry IS NOT NULL ist
        # eine ausdrückliche Entscheidung, keine Nebenwirkung. 29,7 % der Zeilen in
        # tools/en-de.sqlite3 haben lexentry = NULL und tragen damit keine Wortart —
        # _wikdict_pos gäbe für sie still None zurück, das nie einer WikDict-Wortart gleicht,
        # und die Zeile verschwände unbemerkt aus jeder Auswahlliste. Vertretbar, weil alle
        # betroffenen Zeilen bei score <= 48 liegen, deutlich unter den Hauptbedeutungen —
        # aber das gehört sichtbar in die Abfrage, nicht als stiller Filterausfall.
        rows: list[tuple[str | None, str | None, str | None]] = con.execute(
            "SELECT lexentry, sense, trans_list FROM translation "
            "WHERE written_rep = ? AND lexentry IS NOT NULL ORDER BY score DESC",
            (lemma.text,),
        ).fetchall()
    finally:
        con.close()

    return [
        Sense(
            lemma=lemma,
            wikdict_sense=wikdict_sense,
            wikdict_trans_list=trans_list,
            wikdict_lexentry=lexentry,
        )
        for lexentry, wikdict_sense, trans_list in rows
        if _wikdict_pos(lexentry) == wikdict_pos
    ]


# --------------------------------------------------------------- Erstbezug (bauplan.md T6)

# REGEL (technik.md §2, „Warum nicht mitgeliefert"): Bezugsquelle laut Entscheidung 2,
# geprüft 11.08.2026. Ein Aufrufargument statt einer festen Verdrahtung, ausschließlich
# der Testbarkeit wegen (`fetch_dictionary` muss gegen eine örtliche Attrappe laufen können,
# dokumentation.md §5) — ein zweiter echter Anwendungsfall besteht nicht: `config.toml`
# (technik.md §9) sieht bewusst keinen eigenen Schlüssel für die Wörterbuchquelle vor, weil
# Entscheidung 2 sich auf genau eine Quelle festgelegt hat.
DICTIONARY_URL = "https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3"

# REGEL (technik.md §2, „Warum nicht mitgeliefert"): Hinweis auf Herkunft und Lizenz, den
# der Aufrufer beim ersten Bezug anzeigen kann. Die genaue CC-BY-SA-Version (3.0 oder 4.0)
# ist in technik.md §2 als offener Punkt vermerkt, nicht hier vorweggenommen.
SOURCE_NOTICE = (
    "Wörterbuch: WikDict, Sprachpaar Englisch-Deutsch, aus Wiktionary erzeugt über das "
    "DBnary-Projekt (https://wikdict.com). Lizenz: Creative Commons BY-SA. Bezug von "
    f"{DICTIONARY_URL}."
)

# Der Index aus technik.md §3, „Nachtrag 17.08.2026" — siehe ensure_index für die Messung.
INDEX_NAME = "idx_translation_written_rep"

_EXPECTED_TABLE = "translation"
_EXPECTED_COLUMNS = frozenset({"lexentry", "sense", "written_rep", "trans_list", "score"})

# REGEL (technik.md §2, Nachtrag 18.08.2026): Untergrenze für _validate_schema, deutlich
# unter den 157.801 Zeilen der echten Datei (technik.md §3), aber hoch genug, dass eine
# leere oder grob unvollständige, aber schemarichtige Tabelle nicht als gültig durchgeht.
_MIN_TRANSLATION_ROWS = 100_000


def ensure_index(path: Path) -> None:
    """Legt den Index auf `translation(written_rep)` an, falls er fehlt (bauplan.md T6).

    Ohne ihn scannt jede Abfrage aus `candidates` die volle Tabelle mit anschließender
    Sortierung im Speicher; Größenordnung und Wirkung des Index: technik.md §3, „Nachtrag
    17.08.2026". `CREATE INDEX IF NOT EXISTS` macht den Aufruf ungefährlich, wenn er ein
    zweites Mal auf derselben Datei läuft — etwa weil die Datei schon von Hand hinterlegt
    war.

    Bricht sichtbar mit einer deutschen Meldung ab (Regel 13), wenn `path` nicht existiert
    — statt über `sqlite3.connect` still eine leere Datenbankdatei anzulegen — oder wenn
    die Datei beziehungsweise ihr Verzeichnis nicht beschreibbar ist, etwa weil eine von
    Hand hinterlegte Kopie (technik.md §2, „Warum nicht mitgeliefert") das
    Schreibschutz-Attribut trägt. Ohne diese Prüfung reichte die Funktion `sqlite3`s
    englische Fremdmeldung `attempt to write a readonly database` unverändert durch,
    entgegen der Sprachregel.
    """
    if not path.is_file():
        raise ValueError(f"Wörterbuch nicht lesbar: {path}")

    con = sqlite3.connect(path)
    try:
        try:
            con.execute(
                f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {_EXPECTED_TABLE}(written_rep)"
            )
            con.commit()
        except sqlite3.DatabaseError as error:
            raise ValueError(
                f"Index auf {path} konnte nicht angelegt werden: {error}. Datei oder "
                "Verzeichnis schreibgeschützt — Schreibrecht geben oder eine beschreibbare "
                "Kopie hinterlegen."
            ) from error
    finally:
        con.close()


def _validate_schema(path: Path) -> None:
    """Bricht sichtbar ab (Regel 13), wenn `path` keine lesbare SQLite-Datenbank mit der
    Tabelle `translation`, deren für `candidates` nötigen Spalten und einer plausiblen
    Zeilenzahl ist — sonst bliebe eine abgebrochene, leere oder falsche Datei unbemerkt als
    gültiges Wörterbuch liegen. `PRAGMA table_info` allein liest nur das Schema (Seite 1);
    eine schemarichtige, aber leere oder stark gekürzte Tabelle bestünde ohne die
    Zeilenzahlprüfung trotzdem. Was diese Prüfung leistet und was nicht: technik.md §2,
    Nachtrag 18.08.2026."""
    try:
        con = sqlite3.connect(path)
        try:
            columns = {row[1] for row in con.execute(f"PRAGMA table_info({_EXPECTED_TABLE})")}
            row_count = (
                con.execute(f"SELECT COUNT(*) FROM {_EXPECTED_TABLE}").fetchone()[0]
                if columns
                else 0
            )
        finally:
            con.close()
    except sqlite3.DatabaseError as error:
        raise ValueError(f"{path} ist keine lesbare SQLite-Datenbank: {error}") from error

    if not columns:
        raise ValueError(
            f'{path} enthält keine Tabelle "{_EXPECTED_TABLE}" — kein WikDict-Wörterbuch '
            "im erwarteten Schema."
        )
    missing = _EXPECTED_COLUMNS - columns
    if missing:
        raise ValueError(
            f'{path}: Tabelle "{_EXPECTED_TABLE}" fehlen die Spalten '
            f"{', '.join(sorted(missing))} — kein WikDict-Wörterbuch im erwarteten Schema."
        )
    if row_count < _MIN_TRANSLATION_ROWS:
        raise ValueError(
            f'{path}: Tabelle "{_EXPECTED_TABLE}" enthält nur {row_count} Zeilen, erwartet '
            f"mindestens {_MIN_TRANSLATION_ROWS} — vermutlich ein abgebrochener oder "
            "beschädigter Bezug."
        )


def _download(url: str, target: Path) -> None:
    """Lädt `url` blockweise nach `target` und bricht sichtbar ab (Regel 13), wenn der
    Server keine `Content-Length` nennt oder weniger Bytes ankommen, als er angekündigt
    hat — ein abgebrochener Bezug bliebe sonst als kürzere, aber scheinbar vollständige
    Datei liegen. `response.read(n)` meldet ein solches vorzeitiges Verbindungsende bei
    blockweisem Lesen nicht selbst als Fehler, anders als bei `response.read()` ohne
    Grenze — die Prüfung unten ist deshalb notwendig, nicht nur zusätzliche Vorsicht.
    Fehlt `Content-Length` selbst (`Transfer-Encoding: chunked`, eine HTTP/1.0-Antwort mit
    Verbindungsende als Ende, ein Zwischenspeicher davor), ist die Vollständigkeit erst
    recht nicht prüfbar; das gilt hier ebenfalls als Fehlschlag, nicht als übersprungener
    Sonderfall."""
    try:
        with urllib.request.urlopen(url) as response:
            expected_length = response.headers.get("Content-Length")
            if expected_length is None:
                raise ValueError(
                    f"Bezug von {url}: Server nennt keine Content-Length, "
                    "Vollständigkeit nicht prüfbar."
                )
            expected = int(expected_length)
            written = 0
            with target.open("wb") as fh:
                while chunk := response.read(1024 * 1024):
                    fh.write(chunk)
                    written += len(chunk)
    except urllib.error.URLError as error:
        raise ValueError(f"Bezug von {url} fehlgeschlagen: {error}") from error

    if written != expected:
        raise ValueError(
            f"Bezug von {url} abgebrochen: erwartet {expected} Bytes, erhalten {written}."
        )


def fetch_dictionary(path: Path, *, url: str = DICTIONARY_URL) -> None:
    """Erstbezug der Wörterbuchdatei (bauplan.md T6).

    Existiert `path` bereits — heruntergeladen oder von Hand hinterlegt (technik.md §2,
    „Warum nicht mitgeliefert") —, wird nicht neu geladen, aber Schema und Index werden
    trotzdem geprüft beziehungsweise angelegt: Auch eine von Hand kopierte WikDict-Datei
    bringt den Index nicht mit (technik.md §3, „Nachtrag 17.08.2026"). Fehlt sie, wird sie
    von `url` bezogen und geprüft — vollständig (`Content-Length` in `_download`), im
    erwarteten Schema und mit plausibler Zeilenzahl (`_validate_schema`) — und erst danach
    indiziert und an `path` sichtbar. Bis dahin liegt sie unter einer Nebendatei (`path`
    mit Endung `.part`), damit eine unvollständige oder ungültige Datei in keinem
    Fehlerfall als gültiges Wörterbuch liegen bleibt (Regel 13): Ein Fehlschlag räumt die
    Nebendatei auf und bricht danach mit einer deutschen Meldung ab, statt ihn nur zu
    protokollieren. Ohne veröffentlichten Referenzwert prüft dieser Bezug keine
    Prüfsumme — Begründung und was die Prüfungen stattdessen leisten: technik.md §2,
    Nachtrag 18.08.2026.
    """
    if path.is_file():
        _validate_schema(path)
        ensure_index(path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".part")
    try:
        _download(url, tmp_path)
        _validate_schema(tmp_path)
        ensure_index(tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    tmp_path.replace(path)
