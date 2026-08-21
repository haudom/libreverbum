"""Prüft `cli/export.py` — Export nach Anki und Druckseite (bauplan.md T16).

`test_export_writes_the_decks_guid_into_the_profile` ist die Nachbesserung zum Befund
mittel aus der T16-Durchsicht: Regel 6 (dokumentation.md §4, „Anki-GUID beim Export in
card mitschreiben") verlangt, dass nach dem Export dieselbe GUID sowohl im Anki-Deck als
auch in `card` steht — geprüft, indem die erzeugte `.apkg`-Datei wieder aufgemacht wird
(dieselbe Bauart wie `tests/test_anki.py`, `_open_collection`/`_notes`), statt genankis
Rückgabewerte gegen sich selbst zu halten.
"""

from __future__ import annotations

import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

from cli import export
from libreverbum import anki, profile
from libreverbum.entities import Book, Card, CardDirection, Lemma, Occurrence, Sense

_BOOK = Book(title="Testbuch", author="Autorin")


def _occurrence(chapter_number: int = 1) -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=chapter_number,
        lemma=Lemma(text="watch", pos="NOUN"),
        word_form="watch",
        example_sentence="He checked his watch before leaving.",
        frequency=2,
        proper_noun_frequency=0,
    )


def _card_for(occurrence: Occurrence) -> Card:
    sense = Sense(
        lemma=occurrence.lemma,
        translation="Uhr",
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    direction = CardDirection.EN_DE
    guid = anki.new_card_guid(occurrence, sense, direction)
    return Card(sense=sense, occurrence=occurrence, card_direction=direction, guid=guid)


def _apkg_note_guids(path: Path) -> list[str]:
    """Liest die Notiz-GUIDs direkt aus der erzeugten `.apkg`-Datei — dieselbe Bauart wie
    `tests/test_anki.py`, `_open_collection`/`_notes`: die Datei wird als ZIP wieder
    aufgemacht, nicht genankis Rückgabewert gegen sich selbst gehalten."""
    with zipfile.ZipFile(path) as archive:
        collection_bytes = archive.read("collection.anki2")
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as handle:
        handle.write(collection_bytes)
        collection_path = Path(handle.name)
    con = sqlite3.connect(collection_path)
    try:
        rows = con.execute("SELECT guid FROM notes ORDER BY id").fetchall()
    finally:
        con.close()
        collection_path.unlink()
    return [row[0] for row in rows]


@pytest.fixture
def profile_con(tmp_path: Path) -> sqlite3.Connection:
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    con.execute(
        "INSERT INTO chapter (book_id, number, title) VALUES (?, ?, ?)", (book_id, 1, "Testkapitel")
    )
    con.commit()
    return con


def test_export_writes_the_decks_guid_into_the_profile(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """Regel 6: Nach `write_exports` steht zu jeder Karte eine Zeile in `card`, und ihre
    GUID stimmt mit der im erzeugten Anki-Deck überein (Befund mittel, Durchsicht T16:
    bislang landete `card.guid` nirgends im Profil — `grep -rn "INSERT INTO card"` war
    über den ganzen Bestand leer)."""
    card = _card_for(_occurrence())

    paths = export.write_exports(
        profile_con, tmp_path / "export", [card], book_title=_BOOK.title, chapter_number=1
    )

    deck_guids = _apkg_note_guids(paths.anki_path)
    assert deck_guids == [card.guid]

    profile_guids = [
        row[0] for row in profile_con.execute("SELECT guid FROM card ORDER BY id").fetchall()
    ]
    assert profile_guids == deck_guids


def test_a_second_export_of_the_same_meaning_does_not_duplicate_the_card_row(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """Der Nutzen von Regel 6 ist erst eingelöst, wenn ein zweiter Export derselben
    Bedeutung sich darauf stützen kann: Zwei Aufrufe von `write_exports` mit derselben
    Karte (dieselbe GUID) hinterlassen nur eine `card`-Zeile im Profil."""
    card = _card_for(_occurrence())

    export.write_exports(
        profile_con, tmp_path / "erster", [card], book_title=_BOOK.title, chapter_number=1
    )
    export.write_exports(
        profile_con, tmp_path / "zweiter", [card], book_title=_BOOK.title, chapter_number=1
    )

    assert profile_con.execute("SELECT count(*) FROM card").fetchone()[0] == 1
