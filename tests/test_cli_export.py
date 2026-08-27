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


def _occurrence(chapter_number: int = 1, word_form: str = "watch") -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=chapter_number,
        lemma=Lemma(text="watch", pos="NOUN"),
        word_form=word_form,
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


def test_a_second_run_over_the_same_chapter_writes_next_to_the_first(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """Ein zweiter Lauf über dasselbe Kapitel überschreibt die Dateien des ersten nicht,
    sondern legt sich mit `_2` daneben (`cli/export.py`, `export_paths`).

    Der Verlust wäre still: `profile.record_card` hat die Karten des ersten Laufs längst
    gebucht, sie kommen kein zweites Mal — wer das erste `.apkg` noch nicht importiert
    hatte, hätte sie mit der überschriebenen Datei verloren."""
    output_dir = tmp_path / "export"
    erster = export.write_exports(
        profile_con,
        output_dir,
        [_card_for(_occurrence())],
        book_title=_BOOK.title,
        chapter_number=1,
    )
    erster_inhalt = erster.printout_path.read_bytes()

    zweiter = export.write_exports(
        profile_con,
        output_dir,
        [_card_for(_occurrence(word_form="watched"))],
        book_title=_BOOK.title,
        chapter_number=1,
    )

    assert zweiter.anki_path != erster.anki_path
    assert zweiter.printout_path != erster.printout_path
    assert erster.printout_path.read_bytes() == erster_inhalt
    assert zweiter.printout_path.name.endswith("_2.html")
    assert zweiter.anki_path.name.endswith("_2.apkg")


def test_both_export_files_of_one_run_carry_the_same_number(tmp_path: Path) -> None:
    """Deck und Druckseite eines Laufs gehören zusammen: Liegt nur eine der beiden
    Dateien schon da, rückt **das Paar** weiter, nicht nur die belegte Hälfte."""
    output_dir = tmp_path / "export"
    output_dir.mkdir()
    (output_dir / "Testbuch_kapitel1.html").write_text("alte Druckseite", encoding="utf-8")

    paths = export.export_paths(output_dir, "Testbuch", 1)

    assert paths.anki_path.name == "Testbuch_kapitel1_2.apkg"
    assert paths.printout_path.name == "Testbuch_kapitel1_2.html"


def test_export_paths_keeps_counting_past_an_occupied_second_pair(tmp_path: Path) -> None:
    """Der dritte Lauf über dasselbe Kapitel landet auf `_3` — die Suche zählt weiter,
    statt beim zweiten Namen stehenzubleiben."""
    output_dir = tmp_path / "export"
    output_dir.mkdir()
    for name in ("Testbuch_kapitel1.apkg", "Testbuch_kapitel1_2.apkg"):
        (output_dir / name).write_bytes(b"")

    paths = export.export_paths(output_dir, "Testbuch", 1)

    assert paths.anki_path.name == "Testbuch_kapitel1_3.apkg"
    assert paths.printout_path.name == "Testbuch_kapitel1_3.html"


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
