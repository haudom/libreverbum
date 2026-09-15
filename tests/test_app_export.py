"""Prüft `app/export.py` — Export nach Anki und Druckseite (technik.md §14).

`test_export_writes_the_decks_guid_into_the_profile` ist die Nachbesserung zum Befund
mittel aus der T16-Durchsicht: Regel 6 (dokumentation.md §4, „Anki-GUID beim Export in
card mitschreiben") verlangt, dass nach dem Export dieselbe GUID sowohl im Anki-Deck als
auch in `card` steht — geprüft, indem die erzeugte `.apkg`-Datei wieder aufgemacht wird
(dieselbe Bauart wie `tests/test_anki.py`, `_open_collection`/`_notes`), statt genankis
Rückgabewerte gegen sich selbst zu halten.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

from app import export
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


def _deck_names(path: Path) -> set[str]:
    """Die Decknamen aus einer erzeugten `.apkg`-Datei — dieselbe Bauart wie
    `tests/test_anki.py`, `_col` (die Datei wird als ZIP wieder aufgemacht, `col.decks`
    ist ein JSON-Objekt je Deck-ID)."""
    with zipfile.ZipFile(path) as archive:
        collection_bytes = archive.read("collection.anki2")
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as handle:
        handle.write(collection_bytes)
        collection_path = Path(handle.name)
    con = sqlite3.connect(collection_path)
    try:
        (decks_json,) = con.execute("SELECT decks FROM col").fetchone()
    finally:
        con.close()
        collection_path.unlink()
    return {deck["name"] for deck in json.loads(decks_json).values()}


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
    sondern legt sich mit `_2` daneben (`app/export.py`, `export_paths`).

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
    Bedeutung sich darauf stützen kann: Zwei Aufrufe von `write_exports` mit zwei
    **getrennt erzeugten** `Card`-Objekten desselben Eintrags (zwei eigene `_card_for`-
    Aufrufe, nicht dasselbe Objekt zweimal übergeben) hinterlassen nur eine `card`-Zeile
    im Profil — `anki.new_card_guid` liefert für denselben Eintrag beide Male dieselbe
    GUID (technik.md §4, offener Punkt „Die beiden Idempotenz-Tests prüfen nicht, was ihr
    Docstring behauptet")."""
    erste_karte = _card_for(_occurrence())
    zweite_karte = _card_for(_occurrence())

    export.write_exports(
        profile_con, tmp_path / "erster", [erste_karte], book_title=_BOOK.title, chapter_number=1
    )
    export.write_exports(
        profile_con, tmp_path / "zweiter", [zweite_karte], book_title=_BOOK.title, chapter_number=1
    )

    assert profile_con.execute("SELECT count(*) FROM card").fetchone()[0] == 1


def test_a_word_without_a_dictionary_entry_does_not_cost_the_whole_export(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """Der am 01.09.2026 gemeldete Fehler, an der Stelle geprüft, an der er auftrat: Eine
    einzige Karte ohne Wörterbucheintrag (`uncertain=True`, `translation is None`) ließ
    `write_exports` in `anki.export_deck` abbrechen — und weil das der **erste** der beiden
    Exporte ist, blieben auch alle übrigen Karten und die Druckseite ungeschrieben.

    Geprüft wird deshalb der gemischte Fall, nicht die unsichere Karte allein: Beide
    Dateien entstehen, beide Karten stehen im Deck, und `profile.record_card` hat danach
    für beide eine Zeile geschrieben (Regel 6)."""
    sicher = _card_for(_occurrence())
    unsicheres_vorkommen = Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text="jabbar", pos="NOUN"),
        word_form="jabbar",
        example_sentence="A jabbar stood at the edge of the sietch.",
        frequency=1,
        proper_noun_frequency=0,
    )
    platzhalter = Sense(lemma=unsicheres_vorkommen.lemma, uncertain=True)
    unsicher = Card(
        sense=platzhalter,
        occurrence=unsicheres_vorkommen,
        card_direction=CardDirection.EN_DE,
        guid=anki.new_card_guid(unsicheres_vorkommen, platzhalter, CardDirection.EN_DE),
    )

    paths = export.write_exports(
        profile_con,
        tmp_path / "export",
        [sicher, unsicher],
        book_title=_BOOK.title,
        chapter_number=1,
    )

    assert paths.anki_path.is_file()
    assert paths.printout_path.is_file()
    assert sorted(_apkg_note_guids(paths.anki_path)) == sorted([sicher.guid, unsicher.guid])
    assert profile_con.execute("SELECT count(*) FROM card").fetchone()[0] == 2


def test_export_paths_marks_a_partial_export_in_the_filename(tmp_path: Path) -> None:
    """technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf exportiert, was er
    hat": Der Teilstand steht im Dateinamen, damit eine Teildatei nicht wie ein
    vollständiger Export aussieht (Regel 13, dokumentation.md §4)."""
    paths = export.export_paths(tmp_path / "export", "Testbuch", 1, partial=True)

    assert paths.anki_path.name == "Testbuch_kapitel1_teilexport.apkg"
    assert paths.printout_path.name == "Testbuch_kapitel1_teilexport.html"


def test_export_paths_still_searches_a_free_pair_for_a_partial_export(tmp_path: Path) -> None:
    """Die Suche aus `export_paths` nach dem freien Namenspaar gilt unverändert auch für
    einen Teilexport — ein zweiter abgebrochener Lauf über dasselbe Kapitel überschreibt
    den ersten Teilexport nicht, sondern rückt mit `_2` daneben."""
    output_dir = tmp_path / "export"
    output_dir.mkdir()
    (output_dir / "Testbuch_kapitel1_teilexport.html").write_text("alt", encoding="utf-8")

    paths = export.export_paths(output_dir, "Testbuch", 1, partial=True)

    assert paths.anki_path.name == "Testbuch_kapitel1_teilexport_2.apkg"
    assert paths.printout_path.name == "Testbuch_kapitel1_teilexport_2.html"


def test_write_exports_keeps_the_deck_name_unchanged_for_a_partial_export(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """technik.md §12, „Entschieden 15.09.2026 …": Der Teilexport landet im selben
    Anki-Deck, das ein späterer vollständiger Lauf über dasselbe Kapitel träfe — nur der
    Dateiname unterscheidet sich, nicht der Deckname. `anki.new_card_guid` liefert für
    dieselben Einträge dieselbe GUID unabhängig von `partial`; ein abweichender Deckname
    schöbe sie in ein zweites Deck.

    Verfälschungsprobe: Hängt `write_exports` den Teilstand versehentlich an den
    Deckname statt an den Dateinamen (etwa `deck_name=f"...{' (Teilexport)' if partial else
    ''}"`), liefert `_deck_names` `{"Testbuch - Kapitel 1 (Teilexport)"}` statt der
    unveränderten Zeichenkette — dieser Test war daran rot, bevor `deck_name` von `partial`
    unabhängig blieb."""
    card = _card_for(_occurrence())

    paths = export.write_exports(
        profile_con,
        tmp_path / "export",
        [card],
        book_title=_BOOK.title,
        chapter_number=1,
        partial=True,
    )

    assert "_teilexport" in paths.anki_path.name
    # "Default" ist genankis eigenes, immer mitgeschriebenes Deck (id 1) — geprüft wird
    # Mitgliedschaft, nicht Gleichheit der ganzen Menge (dieselbe Bauart wie
    # tests/test_anki.py, wo zwei Decklisten gegeneinander verglichen werden, nicht gegen
    # eine von Hand erwartete Menge).
    assert f"{_BOOK.title} - Kapitel 1" in _deck_names(paths.anki_path)


def test_a_partial_and_a_full_export_of_the_same_card_carry_the_same_guid(
    tmp_path: Path, profile_con: sqlite3.Connection
) -> None:
    """Die GUID einer Teilkarte ist dieselbe, die ein vollständiger Lauf für denselben
    Eintrag erzeugt (technik.md §8b) — `partial` beeinflusst nur den Dateinamen, nicht die
    Kennung, mit der ein späterer, vollständiger Lauf dieselbe Notiz wiederfindet."""
    card = _card_for(_occurrence())

    partial_paths = export.write_exports(
        profile_con,
        tmp_path / "teil",
        [card],
        book_title=_BOOK.title,
        chapter_number=1,
        partial=True,
    )
    full_paths = export.write_exports(
        profile_con, tmp_path / "voll", [card], book_title=_BOOK.title, chapter_number=1
    )

    assert _apkg_note_guids(partial_paths.anki_path) == [card.guid]
    assert _apkg_note_guids(full_paths.anki_path) == [card.guid]
