"""Profil — der einzige Zugriff auf profil.sqlite3 (technik.md §7, Modulkarte).

Aufgabe
-------
Schritt 3 des Kernablaufs (konzept.md): das Schema anlegen und Kenntnis als Ereignisfolge
festhalten — pro Bedeutung, nicht pro Wort (technik.md §4, „Kernentscheidung: Kenntnis pro
Bedeutung, nicht pro Wort", bauplan.md T8) —, daraus den Kenntnisstand ableiten und den
Kapitelwortschatz dagegen abgleichen (bauplan.md T9). Dazu, für Schritt 6 (Export),
`record_card`: die Anki-GUID beim Export in `card` mitschreiben (Regel 6) — ohne dieses
Gegenstück weiß das Profil nach einem Export nicht, für welche Bedeutung schon eine Karte
besteht, und ein zweiter Lauf erzeugte in Anki stumm eine Doppelnotiz (Befund mittel,
Durchsicht T16).

Voraussetzungen
---------------
Erwartet einen Pfad zu einer eigenen Profildatei. Profil und Wörterbuch bleiben getrennte
Dateien (technik.md §4, „Getrennte Datei — nicht mit dem Wörterbuch mischen") — dieses
Modul kennt `en-de.sqlite3` an keiner Stelle und importiert nichts aus `dictionary`. Der
Kern kennt auch keine Vorgabe für den Pfad selbst; den setzt der Aufrufer (technik.md §9).

`compare_chapter_vocabulary` erwartet bereits aufgelöste Bedeutungen (`entities.Sense`
samt `wikdict_`-Feldern) und läuft deshalb erst, nachdem „Bedeutungen beschaffen" den
Kapitelwortschatz angereichert hat (konzept.md, Nachtrag 18.08.2026 beim Kernablauf) —
ein Abgleich auf Grundformebene könnte „neue Bedeutung eines bekannten Wortes" gar nicht
erkennen (technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort").

Liefert
-------
`open_profile` legt beim ersten Aufruf das vollständige Schema an und setzt `PRAGMA
user_version` (Regel 5). `ensure_book`, `ensure_lemma`, `ensure_sense` und
`ensure_occurrence` liefern die bestehende oder neu angelegte Zeile anhand ihrer
Identität. `record_event` hängt ein Ereignis an, ohne ein vorheriges zu ersetzen
(technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand") — bei
`Origin.PRESET` ohne Buch und Kapitel (`event.book`/`event.chapter_number` sind dann
`None`, Schemafassung 2, siehe unten). `events_for_sense` liest die volle Folge zu einer
Bedeutung zurück, mit `book=None` für jedes Vorbelegungs-Ereignis darin — nicht ohne
dieses Ereignis, das JOIN auf `book` verwirft keine Zeile (Regel 13).
`current_knowledge_state` ist die Sicht darauf: das jüngste Ereignis je Bedeutung, `None`
ohne jedes Ereignis. `compare_chapter_vocabulary` hält einen Kapitelwortschatz gegen diese
Sicht: je Bedeutung `VocabularyStatus.UNKNOWN`, `.KNOWN` oder `.NEW_MEANING_OF_KNOWN_WORD`
— Letzteres, wenn eine andere Bedeutung derselben Grundform bereits bekannt ist
(konzept.md §5, „Mehrdeutigkeit"). Ein reiner Lesezugriff: Bedeutungen ohne bisheriges
Ereignis werden dabei nicht angelegt. `record_card` schreibt Vorkommen und Karte einer
exportierten `Card` fest, mit derselben GUID, die im Anki-Deck steht (Regel 6) — über die
GUID idempotent: ein zweiter Export derselben Bedeutung legt keine zweite Zeile an.

`get_cefr_level`/`set_cefr_level` lesen und setzen das Sprachniveau des Lernenden
(`entities.CefrLevel`, `None` für „keine Angabe") — eine Angabe über das Profil selbst,
nicht über ein Buch oder Kapitel, in der eigenen Tabelle `profile` mit genau einer Zeile
(siehe `_SCHEMA` unten, Kommentar bei `CREATE TABLE profile`, für die Abgrenzung gegen
eine allgemeine Schlüssel-Wert-Tabelle).

`record_preset` (Bauschritt 3/5 der Vorbelegung, 31.08.2026) schreibt die Ereignisse einer
Vorbelegung **und** das gewählte Niveau in einer einzigen Transaktion — ganz oder gar
nicht: Gemessen an 18.644 Ereignissen kostet `record_event` in einer Schleife 441 s (jeder
Aufruf committet für sich), dasselbe Sammelschreiben in einer Transaktion 0,2 s. Dafür
teilen sich `ensure_book`, `ensure_lemma`, `ensure_sense` und `record_event` ihre Logik
seit diesem Bauschritt mit einem unbestätigten Kern (`_ensure_book`, `_ensure_lemma`,
`_ensure_sense`, `_record_event`), den `record_preset` ohne Zwischen-Commit wiederverwendet
— welche Bedeutungen eine Grundform bekommt, ist Sache des Aufrufers (`pipeline`, der
einzige Ort, der `dictionary` und `profile` zugleich kennen darf, technik.md §7); dieses
Modul kennt `en-de.sqlite3` weiterhin an keiner Stelle.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from libreverbum.entities import (
    Book,
    Card,
    CefrLevel,
    Event,
    KnowledgeState,
    Lemma,
    Occurrence,
    Origin,
    Sense,
)


class VocabularyStatus(StrEnum):
    """Ergebnis des Abgleichs einer Bedeutung aus dem Kapitelwortschatz gegen das Profil
    (bauplan.md T9). Kein Kenntnisstand im Sinn von `entities.KnowledgeState` — der gilt je
    Ereignis, dieser Wert ist das Ergebnis eines Vergleichs mit dem gesamten Profil.

    `NEW_MEANING_OF_KNOWN_WORD` ist der Grund für diese Kennzeichnung (konzept.md §5,
    „Mehrdeutigkeit"): Eine andere Bedeutung derselben Grundform ist bereits bekannt, diese
    hier noch nicht — ohne die Kennzeichnung würde der Nutzer „kenne ich" für eine
    Bedeutung drücken, die er noch nie gesehen hat (konzept.md, Nachtrag beim Kernablauf)."""

    UNKNOWN = "unknown"
    KNOWN = "known"
    NEW_MEANING_OF_KNOWN_WORD = "new_meaning_of_known_word"


# REGEL (dokumentation.md §4 Regel 5): PRAGMA user_version ab der ersten Fassung gesetzt,
# bei jeder Schemaänderung zu erhöhen. Ohne die Zahl ist eine spätere Migration Ratearbeit.
# Fassung 2 (Bauschritt 2/5 der Vorbelegung): event.book_id/chapter_number dürfen NULL
# sein, ein Index auf event(sense_id) kam hinzu, dazu die Tabelle `profile` für das
# Sprachniveau. Eine Profildatei der Fassung 1 wird deshalb nicht mehr geöffnet — siehe
# open_profile, „Eine ältere Fassung wird nicht stillschweigend weiterverwendet".
SCHEMA_VERSION = 2

# REGEL (dokumentation.md §4 Regel 4, technik.md §4 „Getrennte Datei — nicht mit dem
# Wörterbuch mischen"): Profil und Wörterbuch liegen in getrennten Dateien. Kein Bezeichner
# in diesem Modul nimmt einen Pfad zu en-de.sqlite3 entgegen; geprüft in
# tests/test_profile.py, indem eine Wörterbuch-Attrappe im selben Verzeichnis unberührt
# bleiben muss.
_SCHEMA = """
CREATE TABLE book(
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    UNIQUE (title, author)
);

CREATE TABLE chapter(
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES book(id),
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    UNIQUE (book_id, number)
);

CREATE TABLE lemma(
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    pos TEXT NOT NULL,
    UNIQUE (text, pos)
);

-- REGEL (technik.md §4, „Achtung, zwei Dinge namens sense"; entities.Sense-Docstring):
-- Eine Bedeutung wird über den vollen Zeileninhalt eindeutig, nicht über wikdict_lexentry
-- allein — sonst kollabieren watch als Uhr und watch als Wache auf dieselbe Zeile, dieselbe
-- Kollision (22,7 % der Zeilen mit lexentry), die die Identität in entities.Sense begründet.
CREATE TABLE sense(
    id INTEGER PRIMARY KEY,
    lemma_id INTEGER NOT NULL REFERENCES lemma(id),
    wikdict_lexentry TEXT,
    wikdict_sense TEXT,
    wikdict_trans_list TEXT
);

-- (Befund 1, Review T8): Ein UNIQUE-Constraint über Spalten, die NULL sein dürfen,
-- unterscheidet SQLite-intern jedes NULL von jedem anderen — er greift also nicht, wo
-- wikdict_sense fehlt (36 % der Zeilen, Regel 1) oder alle drei wikdict_-Felder fehlen
-- (Wendung ohne Wörterbucheintrag, Regel 10). ifnull(...,'') macht NULL zu einem
-- vergleichbaren Wert und damit die Identität aus dem Sense-Docstring real.
CREATE UNIQUE INDEX sense_identity ON sense (
    lemma_id,
    ifnull(wikdict_lexentry, ''),
    ifnull(wikdict_sense, ''),
    ifnull(wikdict_trans_list, '')
);

CREATE TABLE occurrence(
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES book(id),
    chapter_number INTEGER NOT NULL,
    lemma_id INTEGER NOT NULL REFERENCES lemma(id),
    word_form TEXT NOT NULL,
    example_sentence TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    proper_noun_frequency INTEGER NOT NULL,
    UNIQUE (book_id, chapter_number, lemma_id),
    FOREIGN KEY (book_id, chapter_number) REFERENCES chapter(book_id, number)
);

-- REGEL (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand"):
-- Zeilen werden angehängt, nie geändert — dieses Modul enthält kein UPDATE auf `event` und
-- kein UNIQUE über sense_id, das die Folge auf einen einzigen Stand zusammenzwänge.
--
-- Schemafassung 2: book_id/chapter_number dürfen NULL sein — eine Vorbelegung
-- (Origin.PRESET) gehört zu keinem Buch (technik.md §4, „Jetzt billig, später teuer" gilt
-- sinngemäß: derselbe Fall trifft auch den Anki-Rückkanal aus Phase 3). Der
-- zusammengesetzte Fremdschlüssel greift bei SQLite nicht, sobald eine seiner Spalten NULL
-- ist (SQLites einzige unterstützte MATCH-Art ist MATCH SIMPLE) — ein Vorbelegungs-Ereignis
-- braucht deshalb keine Kapitelzeile. Der CHECK verhindert den gemischten Fall (eine Spalte
-- gesetzt, die andere NULL), den weder Fremdschlüssel noch NOT NULL allein ausschließen.
CREATE TABLE event(
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES sense(id),
    knowledge_state TEXT NOT NULL,
    origin TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    book_id INTEGER REFERENCES book(id),
    chapter_number INTEGER,
    CHECK ((book_id IS NULL) = (chapter_number IS NULL)),
    FOREIGN KEY (book_id, chapter_number) REFERENCES chapter(book_id, number)
);

-- Schemafassung 2, gemessener Anlass (Auftrag Bauschritt 2/5): Bei rund 18.600 Ereignissen
-- kostet profile.compare_chapter_vocabulary je Kapitel 2,1 s statt 0,4 s ohne diesen Index
-- — und es wächst mit dem Profil unbemerkt weiter (Regel 14 verlangt genau diesen
-- gemessenen Anlass für einen Index, kein Zwischenspeicher auf Vorrat).
CREATE INDEX event_sense_id ON event(sense_id);

CREATE TABLE card(
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES sense(id),
    occurrence_id INTEGER NOT NULL REFERENCES occurrence(id),
    card_direction TEXT NOT NULL,
    guid TEXT NOT NULL UNIQUE
);

-- Schemafassung 2: Das Sprachniveau ist eine Angabe über den Lernenden, nicht über ein
-- Buch oder Kapitel — deshalb eine eigene Tabelle statt einer Spalte in `book` oder
-- `chapter`. Bewusst keine allgemeine Schlüssel-Wert-Tabelle (setting(key, value)), die
-- Regel 14 als Abstraktion über einer einzigen Umsetzung untersagt: `profile` trägt eine
-- konkrete, typisierte Spalte für genau einen Zweck. Genau eine Zeile (CHECK id = 1), von
-- open_profile beim Schemaaufbau angelegt, damit get_cefr_level/set_cefr_level nie
-- zwischen „keine Zeile" und „Niveau ist NULL" unterscheiden müssen — NULL heißt „keine
-- Angabe" (entities.CefrLevel wird beim Rücklesen daraus erzeugt, nie geraten).
CREATE TABLE profile(
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cefr_level TEXT
);
INSERT INTO profile (id, cefr_level) VALUES (1, NULL);
"""


# (Befund 2, Review T8): Die Tabellennamen des Schemas, um beim Öffnen zu prüfen, ob eine
# Datei mit passender Schemaversion auch wirklich dieses Schema trägt. Seit Fassung 2 acht
# Tabellen (`profile` kam hinzu).
_TABLE_NAMES = frozenset(
    {"book", "chapter", "lemma", "sense", "occurrence", "event", "card", "profile"}
)


def open_profile(path: Path) -> sqlite3.Connection:
    """Öffnet die Profildatei, legt beim ersten Aufruf das vollständige Schema an
    (technik.md §4, „Tabellen im Überblick") und setzt `PRAGMA user_version` (Regel 5).

    Eine bestehende Datei mit unpassender Schemaversion bricht sichtbar ab (Regel 13)
    statt sie unbemerkt weiterzuverwenden.

    **Eine ältere Fassung wird nicht stillschweigend weiterverwendet.** Für den Übergang
    von Fassung 1 auf 2 (Bauschritt 2/5 der Vorbelegung: `event.book_id`/`chapter_number`
    werden `NULL`-fähig, dazu die Tabelle `profile`) ist das ein lauter Abbruch, keine
    Wanderung: Im Bestand existiert noch kein Profil mit Wert (`data/` gibt es im
    Arbeitsbaum nicht), und eine Migration ohne echten Altbestand wäre Vorratsarbeit
    (Regel 14). Träfe künftig doch ein Profil der Fassung 1 mit Wert ein, ist das hier zu
    entscheiden — nicht durch stillschweigendes Weiterlaufen.

    `user_version = 0` heißt bei SQLite auch „irgendeine fremde Datei, die diese Zeile nie
    gesetzt hat" — etwa eine Kopie von en-de.sqlite3. Das Schema wird deshalb nur angelegt,
    wenn die Datei noch keine einzige Tabelle trägt; sonst Abbruch mit Meldung (Regel 13)
    statt eines vermischten Bestands (technik.md §4, „Getrennte Datei — nicht mit dem
    Wörterbuch mischen"). Bei passender Version wird ebenso geprüft, dass alle Tabellen
    tatsächlich vorhanden sind — sonst bricht erst die nächste Abfrage darauf mit einer
    nichtssagenden Meldung ab.

    Bricht sichtbar mit einer deutschen Meldung ab (Regel 13), wenn das Verzeichnis von
    `path` nicht existiert — statt `sqlite3`s englische Fremdmeldung „unable to open
    database file" unverändert durchzureichen (dasselbe Muster wie
    `dictionary.ensure_index` für die fehlende Wörterbuchdatei). Existiert das
    Verzeichnis, die Profildatei selbst aber noch nicht, legt der Aufruf weiterhin
    wortlos eine neue, leere Profildatei an — das ist gewolltes Verhalten. Ob ein
    noch nicht vorhandenes Profil bestätigt werden muss, entscheidet der Aufrufer
    (technik.md §9, der Kern kennt keine Vorgabe); offen ist die Frage weiterhin —
    konzept.md, „Bewusst offen", „Woher der Nutzer seinen Grundwortschatz bekommt".
    """
    if not path.parent.is_dir():
        raise ValueError(
            f"Profilverzeichnis {path.parent} existiert nicht — Verzeichnis anlegen, "
            "bevor die Profildatei geöffnet wird."
        )

    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    version = con.execute("PRAGMA user_version").fetchone()[0]
    existing_tables = {
        row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    # (Befund 2, Review T8): version == 0 wird bei SQLite nie geschrieben, sondern ist der
    # Ausgangswert jeder neuen Datei — eine fremde SQLite-Datei trägt ihn also ebenso wie
    # eine echte, leere Profildatei. Nur die Tabellenmenge unterscheidet beide Fälle.
    if version == 0:
        if existing_tables:
            con.close()
            raise ValueError(
                f"Profildatei {path} hat Schemaversion 0, enthält aber bereits die "
                f"Tabelle(n) {', '.join(sorted(existing_tables))} — vermutlich keine leere "
                "Profildatei, sondern eine fremde oder vorversionierte SQLite-Datei. "
                "Abbruch, statt sie zu überschreiben."
            )
        con.executescript(_SCHEMA)
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
    elif version == SCHEMA_VERSION:
        missing_tables = _TABLE_NAMES - existing_tables
        if missing_tables:
            con.close()
            raise ValueError(
                f"Profildatei {path} hat Schemaversion {version}, es fehlen aber die "
                f"Tabelle(n) {', '.join(sorted(missing_tables))} — vermutlich eine fremde "
                "Datei mit zufällig passender Versionsnummer."
            )
    elif version < SCHEMA_VERSION:
        con.close()
        raise ValueError(
            f"Profildatei {path} hat Schemaversion {version}, erwartet {SCHEMA_VERSION} — "
            "eine ältere Profilfassung wird nicht stillschweigend weiterverwendet. Dieses "
            "Modul schreibt keine Migration (Regel 14, kein Anlass ohne echten Altbestand); "
            "wer den Inhalt übernehmen will, liest ihn mit der alten Programmfassung aus."
        )
    else:
        con.close()
        raise ValueError(
            f"Profildatei {path} hat Schemaversion {version}, erwartet {SCHEMA_VERSION} — "
            "neuer als von dieser Programmfassung erwartet."
        )
    return con


def _ensure_book(con: sqlite3.Connection, book: Book) -> int:
    """Unbestätigter Kern von `ensure_book` (Bauschritt 3/5 der Vorbelegung, 31.08.2026):
    `record_preset` braucht dieselbe Logik ohne Zwischen-Commit, damit ihr Sammelschreiben
    in einer einzigen Transaktion bleibt — ganz oder gar nicht."""
    con.execute(
        "INSERT OR IGNORE INTO book (title, author) VALUES (?, ?)", (book.title, book.author)
    )
    row = con.execute(
        "SELECT id FROM book WHERE title = ? AND author = ?", (book.title, book.author)
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(title, author) garantieren die Zeile
    return int(row[0])


def ensure_book(con: sqlite3.Connection, book: Book) -> int:
    """Liefert die id des Buchs, legt die Zeile an, falls sie fehlt. Identität über
    `title` und `author` — dieselbe Bemessung wie `entities.Book`."""
    book_id = _ensure_book(con, book)
    con.commit()
    return book_id


def _ensure_lemma(con: sqlite3.Connection, lemma: Lemma) -> int:
    """Unbestätigter Kern von `ensure_lemma` — siehe `_ensure_book`."""
    con.execute("INSERT OR IGNORE INTO lemma (text, pos) VALUES (?, ?)", (lemma.text, lemma.pos))
    row = con.execute(
        "SELECT id FROM lemma WHERE text = ? AND pos = ?", (lemma.text, lemma.pos)
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(text, pos) garantieren die Zeile
    return int(row[0])


def ensure_lemma(con: sqlite3.Connection, lemma: Lemma) -> int:
    """Liefert die id der Grundform, legt die Zeile an, falls sie fehlt. Identität über
    `text` und `pos` — dieselbe Bemessung wie `entities.Lemma`."""
    lemma_id = _ensure_lemma(con, lemma)
    con.commit()
    return lemma_id


def _ensure_sense(con: sqlite3.Connection, sense: Sense) -> int:
    """Unbestätigter Kern von `ensure_sense` — siehe `_ensure_book`."""
    lemma_id = _ensure_lemma(con, sense.lemma)
    con.execute(
        "INSERT OR IGNORE INTO sense "
        "(lemma_id, wikdict_lexentry, wikdict_sense, wikdict_trans_list) VALUES (?, ?, ?, ?)",
        (lemma_id, sense.wikdict_lexentry, sense.wikdict_sense, sense.wikdict_trans_list),
    )
    row = con.execute(
        "SELECT id FROM sense WHERE lemma_id = ? AND wikdict_lexentry IS ? "
        "AND wikdict_sense IS ? AND wikdict_trans_list IS ?",
        (lemma_id, sense.wikdict_lexentry, sense.wikdict_sense, sense.wikdict_trans_list),
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + sense_identity garantieren die Zeile
    return int(row[0])


def ensure_sense(con: sqlite3.Connection, sense: Sense) -> int:
    """Liefert die id einer Bedeutung, legt die Zeile an, falls sie fehlt.

    Identität über `lemma`, `wikdict_lexentry`, `wikdict_sense` und `wikdict_trans_list`
    gemeinsam — dieselbe Bemessung wie `entities.Sense` (siehe dessen Docstring): Über
    `wikdict_lexentry` allein fielen 22,7 % der Zeilen mit `lexentry` zu einer Bedeutung
    zusammen. Die drei `wikdict_`-Felder sind Momentaufnahmen aus dem Wörterbuch, keine
    Fremdschlüssel dorthin (Regel 3) — dieses Modul öffnet `en-de.sqlite3` nie.
    """
    sense_id = _ensure_sense(con, sense)
    con.commit()
    return sense_id


def ensure_occurrence(con: sqlite3.Connection, occurrence: Occurrence) -> int:
    """Liefert die id eines Vorkommens, legt die Zeile an, falls sie fehlt. Identität
    über `book_id`, `chapter_number` und `lemma_id` — dieselbe Bemessung wie das
    UNIQUE-Constraint auf `occurrence` (technik.md §4, „Ein Eintrag je Kapitel und
    Grundform — dasselbe Wort hat in Kapitel 2 einen anderen Belegsatz als in Kapitel
    9").

    Setzt voraus, dass die Kapitelzeile bereits besteht (`chapter(book_id, number)`,
    Fremdschlüssel auf `occurrence`) — dieses Modul bietet dafür bewusst keine eigene
    Schreibfunktion (Regel 14, `cli.interaction.ensure_chapter_row` übernimmt das); ein
    Aufruf ohne bestehende Kapitelzeile bricht mit `sqlite3.IntegrityError` ab, dasselbe
    Verhalten wie `record_event`.
    """
    book_id = ensure_book(con, occurrence.book)
    lemma_id = ensure_lemma(con, occurrence.lemma)
    con.execute(
        "INSERT OR IGNORE INTO occurrence "
        "(book_id, chapter_number, lemma_id, word_form, example_sentence, frequency, "
        "proper_noun_frequency) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            book_id,
            occurrence.chapter_number,
            lemma_id,
            occurrence.word_form,
            occurrence.example_sentence,
            occurrence.frequency,
            occurrence.proper_noun_frequency,
        ),
    )
    con.commit()
    row = con.execute(
        "SELECT id FROM occurrence WHERE book_id = ? AND chapter_number = ? AND lemma_id = ?",
        (book_id, occurrence.chapter_number, lemma_id),
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(book_id, chapter_number, lemma_id)
    return int(row[0])


def _record_event(con: sqlite3.Connection, event: Event) -> int:
    """Unbestätigter Kern von `record_event` (Bauschritt 3/5 der Vorbelegung, 31.08.2026)
    — siehe `_ensure_book`: dieselben Prüfungen und dieselbe Schreiblogik, nur ohne
    Zwischen-Commit, damit `record_preset` viele Ereignisse in einer einzigen Transaktion
    schreiben kann."""
    # (Befund 5, Review T8): Ein naiver Zeitstempel landete unbemerkt als
    # „2026-08-18T00:00:00" neben zeitzonenbehafteten Werten wie „…+00:00" in derselben
    # Spalte. events_for_sense sortiert danach (Befund 3) und T9 vergleicht danach — ein
    # Mix aus beidem scheitert dort erst, still oder mit einem entfernten TypeError.
    # entities.Event verlangt „zeitzonenbehaftet (UTC)" ausdrücklich, hier wird es geprüft.
    if event.timestamp.tzinfo is None:
        raise ValueError(
            f"Ereignis-Zeitstempel {event.timestamp.isoformat()!r} hat keine Zeitzone — "
            "erwartet wird ein zeitzonenbehafteter Zeitstempel (UTC), siehe "
            'entities.Event, „timestamp ist zeitzonenbehaftet".'
        )
    # REGEL (technik.md §4, Schemafassung 2, „event.book_id und event.chapter_number auf
    # NULL öffnen"): Buch und Kapitelnummer sind gemeinsam gesetzt oder gemeinsam None —
    # der gemischte Fall wäre in der Datenbank durch den CHECK zwar ebenfalls
    # ausgeschlossen, bricht dort aber erst mit sqlite3.IntegrityError ab, ohne zu sagen,
    # welches der beiden Felder fehlt.
    if (event.book is None) != (event.chapter_number is None):
        raise ValueError(
            f"Ereignis für {event.sense.lemma.text!r} hat nur eines von book/chapter_number "
            f"gesetzt (book={event.book!r}, chapter_number={event.chapter_number!r}) — "
            "erwartet wird entweder beides oder, bei einer Vorbelegung (Origin.PRESET), "
            "keines von beiden."
        )
    # (Befund 1, Review T9): Unterschiedliche UTC-Versätze in derselben TEXT-Spalte sortieren
    # lexikografisch falsch — „…T10:30:00+02:00" (= 08:30 UTC) stünde nach „…T09:00:00+00:00"
    # (= 09:00 UTC), obwohl es das ältere Ereignis ist. Normalisieren statt nur prüfen, weil
    # das auch Altbestand mit unterschiedlichen Versätzen vereinheitlicht.
    timestamp = event.timestamp.astimezone(UTC)
    sense_id = _ensure_sense(con, event.sense)
    book_id = _ensure_book(con, event.book) if event.book is not None else None
    cursor = con.execute(
        "INSERT INTO event (sense_id, knowledge_state, origin, timestamp, book_id, chapter_number) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            sense_id,
            event.knowledge_state,
            event.origin,
            timestamp.isoformat(),
            book_id,
            event.chapter_number,
        ),
    )
    assert cursor.lastrowid is not None  # INSERT INTO auf einer rowid-Tabelle setzt sie stets
    return cursor.lastrowid


def record_event(con: sqlite3.Connection, event: Event) -> int:
    """Hängt ein Ereignis an — der Kenntnisstand wird nie überschrieben, nur ergänzt
    (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand").

    Legt Buch und Bedeutung (samt Grundform) an, falls sie noch fehlen, und liefert die id
    des neuen Ereignisses. Ein naiver (nicht zeitzonenbehafteter) Zeitstempel wird
    zurückgewiesen (Regel 13), bevor Buch oder Bedeutung überhaupt angelegt werden. Ein
    zeitzonenbehafteter Zeitstempel wird vor dem Speichern auf UTC normalisiert (Befund 1,
    Review T9) — ein Ereignis entsteht in der Ortszeit des Nutzers, und erst nach der
    Normalisierung ist die lexikografische Sortierung über die TEXT-Spalte in
    `events_for_sense` wieder mit der zeitlichen Reihenfolge deckungsgleich.

    `event.book` ist `None` bei einer Vorbelegung (`Origin.PRESET`, technik.md §4,
    Schemafassung 2) — dann bleiben `book_id`/`chapter_number` in der Zeile `NULL`, ohne
    dass eine Kapitelzeile bestehen muss. Ein Ereignis mit nur einem der beiden gesetzt
    (Buch ohne Kapitelnummer oder umgekehrt) wird zurückgewiesen (Regel 13) — das wäre
    weder ein reguläres Kapitel-Ereignis noch eine Vorbelegung, sondern ein Zustand, den
    `entities.Event` nicht vorsieht.
    """
    event_id = _record_event(con, event)
    con.commit()
    return event_id


def events_for_sense(con: sqlite3.Connection, sense_id: int) -> list[Event]:
    """Die volle Ereignisfolge zu einer Bedeutung, älteste zuerst — unverkürzt: Der aktuelle
    Kenntnisstand ist erst die Ableitung, die `current_knowledge_state` als Sicht darauf
    bildet.

    Ein Vorbelegungs-Ereignis (`Origin.PRESET`) hat kein Buch — deshalb ein `LEFT JOIN` auf
    `book`, nicht `JOIN`: Ein `JOIN` würde jede Zeile mit `book_id IS NULL` stillschweigend
    aus dem Ergebnis werfen (Regel 13) — das Ereignis wäre da, bliebe aber aus jeder Folge
    verschwunden, ohne dass etwas darauf hinwiese."""
    sense_row = con.execute(
        "SELECT l.text, l.pos, s.wikdict_lexentry, s.wikdict_sense, s.wikdict_trans_list "
        "FROM sense s JOIN lemma l ON l.id = s.lemma_id WHERE s.id = ?",
        (sense_id,),
    ).fetchone()
    if sense_row is None:
        raise ValueError(f"Keine Bedeutung mit id {sense_id} im Profil.")
    lemma_text, lemma_pos, wikdict_lexentry, wikdict_sense, wikdict_trans_list = sense_row
    sense = Sense(
        lemma=Lemma(text=lemma_text, pos=lemma_pos),
        wikdict_sense=wikdict_sense,
        wikdict_trans_list=wikdict_trans_list,
        wikdict_lexentry=wikdict_lexentry,
    )

    # (Befund 3, Review T8): ORDER BY e.id lieferte die Einfügereihenfolge, nicht die
    # zeitliche. Ein nachgetragenes Ereignis (rückwirkend am 10.08. erfasst, nachdem am
    # 17.08. schon eines eingetragen wurde) stünde dann an letzter Stelle, obwohl es das
    # ältere ist. T9 vergleicht nach dem jüngsten Ereignis (entities.Event-Docstring),
    # also muss `e.timestamp` das führende Sortierkriterium sein.
    rows = con.execute(
        "SELECT e.knowledge_state, e.origin, e.timestamp, b.title, b.author, e.chapter_number "
        "FROM event e LEFT JOIN book b ON b.id = e.book_id WHERE e.sense_id = ? "
        "ORDER BY e.timestamp, e.id",
        (sense_id,),
    ).fetchall()
    return [
        Event(
            sense=sense,
            knowledge_state=KnowledgeState(knowledge_state),
            origin=Origin(origin),
            timestamp=datetime.fromisoformat(timestamp),
            book=Book(title=title, author=author) if title is not None else None,
            chapter_number=chapter_number,
        )
        for knowledge_state, origin, timestamp, title, author, chapter_number in rows
    ]


def current_knowledge_state(con: sqlite3.Connection, sense_id: int) -> KnowledgeState | None:
    """Der Kenntnisstand als Sicht auf die Ereignisse (bauplan.md T9, technik.md §4 „Der
    aktuelle Kenntnisstand ist eine Sicht auf die Ereignistabelle"): das jüngste Ereignis zu
    dieser Bedeutung nach Zeitstempel. `None`, wenn noch kein Ereignis vorliegt — das ist
    nicht dasselbe wie `KnowledgeState.FORGOTTEN`, das selbst ein Ereignis ist (Phase 3,
    Anki-Rückkanal) und hier nichts vorwegnimmt."""
    events = events_for_sense(con, sense_id)
    if not events:
        return None
    return events[-1].knowledge_state


def _find_sense_id(con: sqlite3.Connection, sense: Sense) -> int | None:
    """Liefert die id einer Bedeutung, falls sie im Profil bereits vorkommt — anders als
    `ensure_sense` legt dieser Lesezugriff keine Zeile an. `compare_chapter_vocabulary`
    braucht das: Der Abgleich prüft den Kenntnisstand, er stellt ihn nicht her — eine
    Bedeutung, die im Profil noch nie ein Ereignis hatte, bekommt dadurch keine Zeile.

    Der Vergleich der drei `wikdict_`-Felder folgt denselben `ifnull(..., '')`-Ausdrücken
    wie der Index `sense_identity` (Befund 6, Review T9): Der Index behandelt `NULL` und
    `''` als dieselbe Bedeutung, ein `IS`-Vergleich würde beide dagegen trennen und eine
    vorhandene Zeile stillschweigend verfehlen.
    """
    row = con.execute(
        "SELECT s.id FROM sense s JOIN lemma l ON l.id = s.lemma_id "
        "WHERE l.text = ? AND l.pos = ? "
        "AND ifnull(s.wikdict_lexentry, '') = ifnull(?, '') "
        "AND ifnull(s.wikdict_sense, '') = ifnull(?, '') "
        "AND ifnull(s.wikdict_trans_list, '') = ifnull(?, '')",
        (
            sense.lemma.text,
            sense.lemma.pos,
            sense.wikdict_lexentry,
            sense.wikdict_sense,
            sense.wikdict_trans_list,
        ),
    ).fetchone()
    return int(row[0]) if row is not None else None


def _sense_ids_for_lemma(con: sqlite3.Connection, lemma: Lemma) -> list[int]:
    """Alle im Profil bereits vorkommenden Bedeutungs-ids einer Grundform — die Grundlage
    für die Kennzeichnung „neue Bedeutung eines bekannten Wortes" in
    `compare_chapter_vocabulary` (konzept.md §5, „Mehrdeutigkeit")."""
    rows = con.execute(
        "SELECT s.id FROM sense s JOIN lemma l ON l.id = s.lemma_id WHERE l.text = ? AND l.pos = ?",
        (lemma.text, lemma.pos),
    ).fetchall()
    return [int(row[0]) for row in rows]


def compare_chapter_vocabulary(
    con: sqlite3.Connection, senses: Iterable[Sense]
) -> dict[Sense, VocabularyStatus]:
    """Abgleich des Kapitelwortschatzes gegen das Profil (bauplan.md T9, Abnahmekriterium
    6): je Bedeutung `VocabularyStatus.KNOWN`, `.UNKNOWN` oder
    `.NEW_MEANING_OF_KNOWN_WORD`.

    „Kenne ich das Wort?" ist eine aus der Bedeutung abgeleitete Frage (technik.md §4,
    „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort") — deshalb prüft dieser
    Abgleich zuerst den Kenntnisstand der Bedeutung selbst und erst danach, ob eine andere
    Bedeutung derselben Grundform bereits bekannt ist. Ein reiner Lesezugriff: Bedeutungen
    ohne bisheriges Ereignis werden dabei nicht angelegt (`_find_sense_id`).

    Allein `KnowledgeState.KNOWN` gilt als bekannt (Befund 3, Review T9, Abnahmekriterium
    6: „bekannt" ist der abgeschlossene Zustand, nicht der begonnene) — `learning`,
    `deferred` und `forgotten` gelten als nicht bekannt und werden erneut abgefragt.
    Dasselbe gilt für die Geschwisterbedeutung: Nur ein `known` bei ihr löst
    `NEW_MEANING_OF_KNOWN_WORD` aus, ein begonnenes oder zurückgestelltes Lernen nicht.
    """
    result: dict[Sense, VocabularyStatus] = {}
    for sense in senses:
        sense_id = _find_sense_id(con, sense)
        if sense_id is not None and current_knowledge_state(con, sense_id) == KnowledgeState.KNOWN:
            result[sense] = VocabularyStatus.KNOWN
            continue
        has_known_sibling = any(
            current_knowledge_state(con, sibling_id) == KnowledgeState.KNOWN
            for sibling_id in _sense_ids_for_lemma(con, sense.lemma)
            if sibling_id != sense_id
        )
        result[sense] = (
            VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD
            if has_known_sibling
            else VocabularyStatus.UNKNOWN
        )
    return result


# REGEL (dokumentation.md §4 Regel 6, „Anki-GUID beim Export in card mitschreiben"):
# Ohne diese Funktion wusste das Profil nach einem Export nicht, für welche Bedeutung
# schon eine Karte besteht — ein zweiter Lauf erzeugte in Anki stumm eine Doppelnotiz,
# und `anki.new_card_guid`s ganze Begründung (`anki.py:58-97`) hätte kein Gegenstück in
# der Datenbank (Befund mittel, Durchsicht T16).
def record_card(con: sqlite3.Connection, card: Card) -> int:
    """Schreibt Vorkommen und Karte einer exportierten `Card` fest — aufgerufen **nach**
    einem erfolgreichen `anki.export_deck` (`cli.export.write_exports`), mit derselben
    `card.guid`, die im Anki-Deck steht.

    Legt Vorkommen und Bedeutung an, falls sie noch fehlen (`ensure_occurrence`,
    `ensure_sense`), und trägt darüber die Kartenzeile ein — über die GUID idempotent
    (`INSERT OR IGNORE`): `anki.new_card_guid` liefert für dasselbe Vorkommen, dieselbe
    Bedeutung und dieselbe Kartenrichtung stets dieselbe GUID, ein zweiter Export
    derselben Bedeutung legt also keine zweite Zeile an, sondern liefert die bestehende
    id zurück.
    """
    occurrence_id = ensure_occurrence(con, card.occurrence)
    sense_id = ensure_sense(con, card.sense)
    con.execute(
        "INSERT OR IGNORE INTO card (sense_id, occurrence_id, card_direction, guid) "
        "VALUES (?, ?, ?, ?)",
        (sense_id, occurrence_id, card.card_direction, card.guid),
    )
    con.commit()
    row = con.execute("SELECT id FROM card WHERE guid = ?", (card.guid,)).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(guid) garantieren die Zeile
    return int(row[0])


def get_cefr_level(con: sqlite3.Connection) -> CefrLevel | None:
    """Das Sprachniveau des Lernenden (`entities.CefrLevel`), `None` für „keine Angabe".

    Liest die einzige Zeile der Tabelle `profile` (Schemafassung 2) — `open_profile` legt
    sie beim Schemaaufbau mit `cefr_level = NULL` an, die Zeile fehlt also nie."""
    row = con.execute("SELECT cefr_level FROM profile WHERE id = 1").fetchone()
    assert row is not None  # open_profile legt die Zeile beim Schemaaufbau stets an
    level = row[0]
    return CefrLevel(level) if level is not None else None


def set_cefr_level(con: sqlite3.Connection, level: CefrLevel | None) -> None:
    """Setzt das Sprachniveau des Lernenden — `None` trägt „keine Angabe" ein, unter-
    scheidbar von jedem gesetzten Niveau (`get_cefr_level`).

    Ein `UPDATE` auf die einzige Zeile von `profile`, kein `INSERT`: Anders als bei einem
    `Event` gibt es hier nur den einen aktuellen Stand, kein Verlauf — das Niveau ist eine
    Momentaufnahme des Lernenden, nicht ein Ereignis mit Herkunft und Zeitpunkt
    (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand" gilt
    hier bewusst nicht: Ein adaptiver Test aus Phase 2 soll diesen einen Wert verfeinern,
    nicht eine zweite Herleitung neben der Ereignisfolge aufbauen)."""
    con.execute("UPDATE profile SET cefr_level = ? WHERE id = 1", (level,))
    con.commit()


def record_preset(con: sqlite3.Connection, events: Iterable[Event], cefr_level: CefrLevel) -> None:
    """Schreibt die Ereignisse einer Vorbelegung und das gewählte Sprachniveau in **einer**
    Transaktion (Bauschritt 3/5 der Vorbelegung, 31.08.2026, Auftragstext: „Die Vorbelegung
    muss es ganz oder gar nicht geben — ein halb geschriebenes Profil ist schlimmer als
    keins"): Bricht ein einzelnes Ereignis ab (naiver Zeitstempel, gemischtes
    `book`/`chapter_number`, Regel 13), steht im Profil **nichts** von diesem Aufruf — kein
    Teil der Ereignisse, nicht das Niveau.

    Gemessen an 18.644 Ereignissen (Auftragstext): `record_event` in einer Schleife 441 s
    — jeder Aufruf committet für sich —, dasselbe Sammelschreiben hier 0,2 s: Jedes
    Ereignis läuft über den unbestätigten Kern `_record_event` (dieselbe Prüfung und
    Schreiblogik wie `record_event`, nur ohne Zwischen-Commit), das Niveau über dieselbe
    rohe `UPDATE`-Anweisung wie `set_cefr_level`, beides im selben, noch offenen
    Transaktionsblock — erst danach **ein** `commit()`. Scheitert ein Schritt, holt
    `rollback()` alles seit dem letzten Commit zurück, bevor der Fehler weitergereicht wird
    (Regel 13: kein `except`, das nur protokolliert und weiterläuft, sondern eines, das den
    Halbschritt zurücknimmt und den Fehler sichtbar lässt).

    Wie die Ereignisse zustande kommen — welche Grundformen, welche Bedeutungen aus dem
    Wörterbuch —, ist nicht Sache dieser Funktion: Sie kennt `en-de.sqlite3` nicht (Regel
    4). Das erledigt `pipeline`, der einzige Ort, der `dictionary` und `profile` zugleich
    kennen darf (technik.md §7)."""
    try:
        for event in events:
            _record_event(con, event)
        con.execute("UPDATE profile SET cefr_level = ? WHERE id = 1", (cefr_level,))
    except Exception:
        con.rollback()
        raise
    con.commit()
