"""Prüft `cli/interaction.py` — die Triage über die Tastatur (bauplan.md T16).

Baut die Testvorrichtung direkt aus `entities`/`pipeline.VocabularyEntry`, ohne EPUB oder
spaCy: Geprüft werden die Entscheidungen, die die Triage trifft, nicht die
Bildschirmausgabe (dokumentation.md §5). Der volle Weg durch `pipeline.run_chapter` bis
zum Export ist `tests/test_cli_main.py` vorbehalten.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cli import interaction
from libreverbum import pipeline, printout, profile
from libreverbum.entities import Book, CardDirection, Lemma, Occurrence, Sense

if TYPE_CHECKING:
    from conftest import ModelServerDouble

_BOOK = Book(title="Testbuch", author="Autorin")


def _occurrence(word: str, pos: str, frequency: int) -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text=word, pos=pos),
        word_form=word,
        example_sentence=f"An example sentence with {word} in it.",
        frequency=frequency,
        proper_noun_frequency=0,
    )


def _sense(word: str, pos: str, translation: str) -> Sense:
    return Sense(
        lemma=Lemma(text=word, pos=pos),
        wikdict_sense="a meaning",
        wikdict_trans_list=translation,
        wikdict_lexentry=f"eng/{word}__{pos.title()}__1",
    )


def _entries(count: int) -> list[pipeline.VocabularyEntry]:
    """`count` Einzelwort-Einträge, `word0` am häufigsten, `word{count-1}` am seltensten
    — je einer eindeutigen Bedeutung, damit `_representative_sense` keine Wahl hat."""
    result = []
    for index in range(count):
        occurrence = _occurrence(f"word{index}", "NOUN", frequency=count - index)
        sense = _sense(f"word{index}", "NOUN", f"Übersetzung{index}")
        result.append(
            pipeline.VocabularyEntry(occurrence=occurrence, candidates=[sense], status={})
        )
    return result


@pytest.fixture
def profile_con(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    interaction.ensure_chapter_row(con, _BOOK, 1, "Testkapitel")
    try:
        yield con
    finally:
        con.close()


def _events(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """`(lemma, knowledge_state, origin)` je Ereignis — für Zusicherungen, die nicht an
    `sense_id`-Zahlen hängen sollen."""
    rows = con.execute(
        "SELECT l.text, e.knowledge_state, e.origin FROM event e "
        "JOIN sense s ON s.id = e.sense_id JOIN lemma l ON l.id = s.lemma_id"
    ).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def _no_op_write(_: str) -> None:
    return None


def _never_needed() -> str:
    raise AssertionError("Modellserver wurde angefragt, obwohl kein Wort gelernt wurde.")


def test_bulk_action_marks_all_more_frequent_words(profile_con: sqlite3.Connection) -> None:
    """konzept.md §4, „Sammelaktion »ab hier kenne ich alles« — markiert alle
    häufigeren Wörter auf einen Schlag" (bauplan.md T10, hier über die Tastatur
    bedient): Position 3 markiert die drei häufigsten Wörter als bekannt, der Rest wird
    einzeln gefragt."""
    entries = _entries(5)
    answers = iter(["3", "s", "s"])  # Sammelaktion bis 3, dann zwei individuelle "skip"

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=entries,
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert cards == []
    events = _events(profile_con)
    bulk_marked = {lemma for lemma, state, origin in events if origin == "bulk_mark"}
    assert bulk_marked == {"word0", "word1", "word2"}
    assert all(state == "known" for _, state, origin in events if origin == "bulk_mark")
    skipped = {lemma for lemma, state, origin in events if origin == "triage"}
    assert skipped == {"word3", "word4"}
    assert all(state == "deferred" for _, state, origin in events if origin == "triage")


def test_bulk_action_does_not_mark_a_word_behind_the_selected_position(
    profile_con: sqlite3.Connection,
) -> None:
    """`triage.bulk_mark`, Regel: „Ein gleich häufiges Wort hinter selected bucht der
    Klick nicht mit" — hier mit zwei gleich häufigen Wörtern, damit ein Off-by-one bei
    der Positionsauflösung sichtbar würde."""
    tied = [
        pipeline.VocabularyEntry(
            occurrence=_occurrence("tied_a", "NOUN", frequency=1),
            candidates=[_sense("tied_a", "NOUN", "A")],
            status={},
        ),
        pipeline.VocabularyEntry(
            occurrence=_occurrence("tied_b", "NOUN", frequency=1),
            candidates=[_sense("tied_b", "NOUN", "B")],
            status={},
        ),
    ]
    answers = iter(["1", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=tied,
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    events = _events(profile_con)
    bulk_marked = {lemma for lemma, _, origin in events if origin == "bulk_mark"}
    assert bulk_marked == {"tied_a"}


def test_word_limit_defers_the_rest_without_recording_an_event(
    profile_con: sqlite3.Connection,
) -> None:
    """konzept.md §4, „Obergrenze pro Kapitel — der Rest wird zurückgestellt": Wörter
    jenseits von `limit` werden weder angezeigt noch im Profil vermerkt."""
    entries = _entries(5)
    answers = iter(["", "s", "s", "s"])  # keine Sammelaktion, drei individuelle "skip"

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=entries,
        limit=3,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    events = _events(profile_con)
    assert {lemma for lemma, _, _ in events} == {"word0", "word1", "word2"}


def test_learning_a_word_calls_the_model_and_creates_a_card(
    profile_con: sqlite3.Connection, model_server_double: ModelServerDouble
) -> None:
    """„will ich lernen" ruft `translation.choose_sense` auf (Abnahmekriterium 3) und
    erzeugt eine `Card` mit der vom Modell gewählten, aufgelösten Übersetzung."""
    entries = _entries(1)
    model_server_double.choice = 1
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=entries,
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=lambda: model_server_double.model_name,
        model_url=model_server_double.url,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert len(cards) == 1
    assert cards[0].occurrence.lemma.text == "word0"
    assert cards[0].sense.translation == "Übersetzung0"
    events = _events(profile_con)
    assert events == [("word0", "learning", "triage")]


def test_expressions_reach_the_triage_and_the_resulting_card(
    profile_con: sqlite3.Connection, model_server_double: ModelServerDouble
) -> None:
    """Abnahmekriterium 3 in klein (bauplan.md T16, „Wendungen erscheinen in der Triage
    und landen im Export"): Eine Wendung aus `pipeline.ChapterVocabulary.expressions`
    läuft durch dieselbe Triage wie ein Einzelwort und erzeugt bei „will ich lernen"
    ebenso eine Karte."""
    expression_occurrence = Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text="give up", pos="VERB"),
        word_form="gave up",
        example_sentence="In the end she gave up the chase.",
        frequency=1,
        proper_noun_frequency=0,
    )
    expression_sense = Sense(
        lemma=Lemma(text="give up", pos="VERB"),
        wikdict_sense="admit defeat",
        wikdict_trans_list="aufgeben",
        wikdict_lexentry="eng/give_up__Verb__1",
    )
    expressions = [
        pipeline.VocabularyEntry(
            occurrence=expression_occurrence, candidates=[expression_sense], status={}
        )
    ]
    model_server_double.choice = 1
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=expressions,
        limit=interaction.EXPRESSION_LIMIT,
        label="Wendungen",
        card_direction=CardDirection.EN_DE,
        get_model_name=lambda: model_server_double.model_name,
        model_url=model_server_double.url,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert len(cards) == 1
    assert cards[0].occurrence.word_form == "gave up"
    assert cards[0].sense.translation == "aufgeben"


def test_word_limit_plus_expression_limit_fits_the_printout() -> None:
    """Abnahmekriterium 5 in klein: Die Summe aus beiden Deckeln — der Wortobergrenze
    und dem daraus abgeleiteten Wendungsdeckel — übersteigt `printout.MAX_ENTRIES`
    nicht, selbst wenn jedes durchgelassene Wort und jede durchgelassene Wendung gelernt
    würde."""
    assert interaction.WORD_LIMIT + interaction.EXPRESSION_LIMIT == printout.MAX_ENTRIES


def test_acceptance_6_known_words_are_not_asked_again(profile_con: sqlite3.Connection) -> None:
    """Abnahmekriterium 6 (konzept.md, „Abnahmekriterien"): „Beim zweiten Durchlauf
    desselben Kapitels werden die als *bekannt* markierten Wörter **nicht erneut**
    abgefragt — das Profil greift." Geprüft direkt an `run_triage_pass` mit
    `entry.status`, wie `pipeline.run_chapter` es aus `profile.
    compare_chapter_vocabulary` liefert (Befund schwer 1, Durchsicht T16)."""
    known_sense = _sense("known_word", "NOUN", "Bekannt")
    known_entry = pipeline.VocabularyEntry(
        occurrence=_occurrence("known_word", "NOUN", frequency=5),
        candidates=[known_sense],
        status={known_sense: profile.VocabularyStatus.KNOWN},
    )
    new_entry = _entries(1)[0]  # word0, ohne Profileintrag
    written: list[str] = []
    answers = iter(["", "s"])  # keine Sammelaktion, dann "skip" für word0

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[known_entry, new_entry],
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert not any(line.startswith("known_word (") for line in written)
    events = _events(profile_con)
    assert {lemma for lemma, _, _ in events} == {"word0"}
    assert any("bereits bekannt" in line for line in written)


def test_a_candidate_with_one_known_and_one_new_sense_is_not_skipped(
    profile_con: sqlite3.Connection,
) -> None:
    """Ein Eintrag mit **gemischtem** Kenntnisstand — eine Bedeutung bekannt, eine noch
    nicht — bleibt in der Triage: Nur ein Eintrag, dessen *sämtliche* Kandidaten bekannt
    sind, gilt als bekannt (Befund schwer 1, Durchsicht T16, `_is_known`). Ohne dieses
    Wort wäre die neue Bedeutung eines mehrdeutigen Worts nie abgefragt worden."""
    known_sense = _sense("bank", "NOUN", "Geldinstitut")
    new_sense = _sense("bank", "NOUN", "Flussufer")
    entry = pipeline.VocabularyEntry(
        occurrence=_occurrence("bank", "NOUN", frequency=2),
        candidates=[known_sense, new_sense],
        status={
            known_sense: profile.VocabularyStatus.KNOWN,
            new_sense: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
        },
    )
    written: list[str] = []
    answers = iter(["", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[entry],
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert any(line.startswith("bank (") for line in written)


def test_new_meaning_of_a_known_word_is_marked_in_the_display(
    profile_con: sqlite3.Connection,
) -> None:
    """konzept.md §5, „Mehrdeutigkeit": Der zweite Eintrag einer mehrdeutigen Grundform
    wird in der Triage als „neue Bedeutung eines bekannten Wortes" gekennzeichnet, damit
    der Nutzer versteht, warum ein scheinbar bekanntes Wort erneut auftaucht (Befund
    mittel 6, Durchsicht T16)."""
    known_sense = _sense("bank", "NOUN", "Geldinstitut")
    new_sense = _sense("bank", "NOUN", "Flussufer")
    entry = pipeline.VocabularyEntry(
        occurrence=_occurrence("bank", "NOUN", frequency=2),
        candidates=[known_sense, new_sense],
        status={
            known_sense: profile.VocabularyStatus.KNOWN,
            new_sense: profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD,
        },
    )
    written: list[str] = []
    answers = iter(["", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[entry],
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    marked = [line for line in written if "neue Bedeutung eines bekannten Wortes" in line]
    assert len(marked) == 1
    assert "Flussufer" in marked[0]
    assert not any("Geldinstitut" in line and "neue Bedeutung" in line for line in written)


def test_a_candidate_without_a_dictionary_entry_becomes_uncertain_when_learned(
    profile_con: sqlite3.Connection,
) -> None:
    """Regel 11 (dokumentation.md §4): Ein Wort ohne Wörterbucheintrag wird nicht dem
    Modell vorgelegt, sondern unmittelbar `uncertain` (dieselbe Regel wie
    `translation.choose_sense` bei leerer Auswahlliste — hier ohne Modellaufruf
    geprüft, `get_model_name` darf nie aufgerufen werden)."""
    entries = [
        pipeline.VocabularyEntry(
            occurrence=_occurrence("obscure", "NOUN", frequency=1), candidates=[], status={}
        )
    ]
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=entries,
        limit=10,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        get_model_name=_never_needed,
        model_url="http://unerreichbar.invalid",
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert len(cards) == 1
    assert cards[0].sense.uncertain is True
    assert cards[0].sense.translation is None
