"""Profil — der einzige Zugriff auf profil.sqlite3 (technik.md §7, Modulkarte).

Aufgabe
-------
Schritt 3 des Kernablaufs (konzept.md), erste Hälfte (bauplan.md T8): das Schema anlegen
und Kenntnis als Ereignisfolge festhalten — pro Bedeutung, nicht pro Wort (technik.md §4,
„Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort"). Der daraus abgeleitete
Kenntnisstand und der Abgleich gegen den Kapitelwortschatz sind T9 und liegen bewusst noch
nicht hier (Regel 14).

Voraussetzungen
---------------
Erwartet einen Pfad zu einer eigenen Profildatei. Profil und Wörterbuch bleiben getrennte
Dateien (technik.md §4, „Getrennte Datei — nicht mit dem Wörterbuch mischen") — dieses
Modul kennt `en-de.sqlite3` an keiner Stelle und importiert nichts aus `dictionary`. Der
Kern kennt auch keine Vorgabe für den Pfad selbst; den setzt der Aufrufer (technik.md §9).

Liefert
-------
`open_profile` legt beim ersten Aufruf das vollständige Schema an und setzt `PRAGMA
user_version` (Regel 5). `ensure_book`, `ensure_lemma` und `ensure_sense` liefern die
bestehende oder neu angelegte Zeile anhand ihrer Identität. `record_event` hängt ein
Ereignis an, ohne ein vorheriges zu ersetzen (technik.md §4, „Kernentscheidung:
Ereignisfolge statt überschreibbarem Zustand"); `events_for_sense` liest die volle Folge zu
einer Bedeutung zurück. Der aktuelle Kenntnisstand selbst — jeweils das jüngste Ereignis —
ist **nicht** Teil dieses Moduls; das baut T9 als Sicht auf dieser Ereignisfolge.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from libreverbum.entities import Book, Event, KnowledgeState, Lemma, Origin, Sense

# REGEL (dokumentation.md §4 Regel 5): PRAGMA user_version ab der ersten Fassung gesetzt,
# bei jeder Schemaänderung zu erhöhen. Ohne die Zahl ist eine spätere Migration Ratearbeit.
SCHEMA_VERSION = 1

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
CREATE TABLE event(
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES sense(id),
    knowledge_state TEXT NOT NULL,
    origin TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    book_id INTEGER NOT NULL REFERENCES book(id),
    chapter_number INTEGER NOT NULL,
    FOREIGN KEY (book_id, chapter_number) REFERENCES chapter(book_id, number)
);

CREATE TABLE card(
    id INTEGER PRIMARY KEY,
    sense_id INTEGER NOT NULL REFERENCES sense(id),
    occurrence_id INTEGER NOT NULL REFERENCES occurrence(id),
    card_direction TEXT NOT NULL,
    guid TEXT NOT NULL UNIQUE
);
"""


# (Befund 2, Review T8): Die sieben Tabellennamen des Schemas, um beim Öffnen zu prüfen,
# ob eine Datei mit passender Schemaversion auch wirklich dieses Schema trägt.
_TABLE_NAMES = frozenset({"book", "chapter", "lemma", "sense", "occurrence", "event", "card"})


def open_profile(path: Path) -> sqlite3.Connection:
    """Öffnet die Profildatei, legt beim ersten Aufruf das vollständige Schema an
    (technik.md §4, „Tabellen im Überblick") und setzt `PRAGMA user_version` (Regel 5).

    Eine bestehende Datei mit unpassender Schemaversion bricht sichtbar ab (Regel 13)
    statt sie unbemerkt weiterzuverwenden. Eine Migration über diese Prüfung hinaus ist
    nicht Teil dieses Moduls (Regel 14) — es gibt bisher nur eine Fassung.

    `user_version = 0` heißt bei SQLite auch „irgendeine fremde Datei, die diese Zeile nie
    gesetzt hat" — etwa eine Kopie von en-de.sqlite3. Das Schema wird deshalb nur angelegt,
    wenn die Datei noch keine einzige Tabelle trägt; sonst Abbruch mit Meldung (Regel 13)
    statt eines vermischten Bestands (technik.md §4, „Getrennte Datei — nicht mit dem
    Wörterbuch mischen"). Bei passender Version wird ebenso geprüft, dass alle sieben
    Tabellen tatsächlich vorhanden sind — sonst bricht erst die nächste Abfrage darauf mit
    einer nichtssagenden Meldung ab.
    """
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
    else:
        con.close()
        raise ValueError(
            f"Profildatei {path} hat Schemaversion {version}, erwartet {SCHEMA_VERSION}."
        )
    return con


def ensure_book(con: sqlite3.Connection, book: Book) -> int:
    """Liefert die id des Buchs, legt die Zeile an, falls sie fehlt. Identität über
    `title` und `author` — dieselbe Bemessung wie `entities.Book`."""
    con.execute(
        "INSERT OR IGNORE INTO book (title, author) VALUES (?, ?)", (book.title, book.author)
    )
    con.commit()
    row = con.execute(
        "SELECT id FROM book WHERE title = ? AND author = ?", (book.title, book.author)
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(title, author) garantieren die Zeile
    return int(row[0])


def ensure_lemma(con: sqlite3.Connection, lemma: Lemma) -> int:
    """Liefert die id der Grundform, legt die Zeile an, falls sie fehlt. Identität über
    `text` und `pos` — dieselbe Bemessung wie `entities.Lemma`."""
    con.execute("INSERT OR IGNORE INTO lemma (text, pos) VALUES (?, ?)", (lemma.text, lemma.pos))
    con.commit()
    row = con.execute(
        "SELECT id FROM lemma WHERE text = ? AND pos = ?", (lemma.text, lemma.pos)
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + UNIQUE(text, pos) garantieren die Zeile
    return int(row[0])


def ensure_sense(con: sqlite3.Connection, sense: Sense) -> int:
    """Liefert die id einer Bedeutung, legt die Zeile an, falls sie fehlt.

    Identität über `lemma`, `wikdict_lexentry`, `wikdict_sense` und `wikdict_trans_list`
    gemeinsam — dieselbe Bemessung wie `entities.Sense` (siehe dessen Docstring): Über
    `wikdict_lexentry` allein fielen 22,7 % der Zeilen mit `lexentry` zu einer Bedeutung
    zusammen. Die drei `wikdict_`-Felder sind Momentaufnahmen aus dem Wörterbuch, keine
    Fremdschlüssel dorthin (Regel 3) — dieses Modul öffnet `en-de.sqlite3` nie.
    """
    lemma_id = ensure_lemma(con, sense.lemma)
    con.execute(
        "INSERT OR IGNORE INTO sense "
        "(lemma_id, wikdict_lexentry, wikdict_sense, wikdict_trans_list) VALUES (?, ?, ?, ?)",
        (lemma_id, sense.wikdict_lexentry, sense.wikdict_sense, sense.wikdict_trans_list),
    )
    con.commit()
    row = con.execute(
        "SELECT id FROM sense WHERE lemma_id = ? AND wikdict_lexentry IS ? "
        "AND wikdict_sense IS ? AND wikdict_trans_list IS ?",
        (lemma_id, sense.wikdict_lexentry, sense.wikdict_sense, sense.wikdict_trans_list),
    ).fetchone()
    assert row is not None  # INSERT OR IGNORE + sense_identity garantieren die Zeile
    return int(row[0])


def record_event(con: sqlite3.Connection, event: Event) -> int:
    """Hängt ein Ereignis an — der Kenntnisstand wird nie überschrieben, nur ergänzt
    (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand").

    Legt Buch und Bedeutung (samt Grundform) an, falls sie noch fehlen, und liefert die id
    des neuen Ereignisses. Ein naiver (nicht zeitzonenbehafteter) Zeitstempel wird
    zurückgewiesen (Regel 13), bevor Buch oder Bedeutung überhaupt angelegt werden.
    """
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
    sense_id = ensure_sense(con, event.sense)
    book_id = ensure_book(con, event.book)
    cursor = con.execute(
        "INSERT INTO event (sense_id, knowledge_state, origin, timestamp, book_id, chapter_number) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            sense_id,
            event.knowledge_state,
            event.origin,
            event.timestamp.isoformat(),
            book_id,
            event.chapter_number,
        ),
    )
    con.commit()
    assert cursor.lastrowid is not None  # INSERT INTO auf einer rowid-Tabelle setzt sie stets
    return cursor.lastrowid


def events_for_sense(con: sqlite3.Connection, sense_id: int) -> list[Event]:
    """Die volle Ereignisfolge zu einer Bedeutung, älteste zuerst — unverkürzt: Der aktuelle
    Kenntnisstand ist erst die Ableitung, die T9 als Sicht darauf baut (Regel 14)."""
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
        "FROM event e JOIN book b ON b.id = e.book_id WHERE e.sense_id = ? "
        "ORDER BY e.timestamp, e.id",
        (sense_id,),
    ).fetchall()
    return [
        Event(
            sense=sense,
            knowledge_state=KnowledgeState(knowledge_state),
            origin=Origin(origin),
            timestamp=datetime.fromisoformat(timestamp),
            book=Book(title=title, author=author),
            chapter_number=chapter_number,
        )
        for knowledge_state, origin, timestamp, title, author, chapter_number in rows
    ]
