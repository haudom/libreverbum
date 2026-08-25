"""Prüft `cli/interaction.py` — die Triage über die Tastatur (bauplan.md T16).

Baut die Testvorrichtung direkt aus `entities`/`pipeline.ResolvedEntry`, ohne EPUB oder
spaCy: Geprüft werden die Entscheidungen, die die Triage trifft, nicht die
Bildschirmausgabe (dokumentation.md §5). Seit der zweiten T16-Durchsicht (Befund schwer 1)
liegen Profilabgleich, Häufigkeitssortierung, Bedeutungsauflösung durch das Modell und
Wortobergrenze in `pipeline.resolve_triage_entries`, nicht mehr hier — geprüft in
`tests/test_pipeline.py`. Diese Datei baut deshalb `pipeline.TriageResolution` direkt statt
über einen echten `resolve_triage_entries`-Aufruf, ohne Modellserver. Der volle Weg durch
`pipeline.run_chapter` bis zum Export ist `tests/test_cli_main.py` vorbehalten.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from cli import interaction
from libreverbum import pipeline, printout, profile
from libreverbum.entities import Book, CardDirection, Lemma, Occurrence, Sense
from libreverbum.profile import VocabularyStatus

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


def _resolved_sense(word: str, pos: str, translation: str) -> Sense:
    """Eine bereits aufgelöste Bedeutung, wie `translation.choose_sense` sie liefert —
    `translation` und `wikdict_trans_list` tragen denselben Text (`translation.py`,
    „Liefert")."""
    return Sense(
        lemma=Lemma(text=word, pos=pos),
        translation=translation,
        wikdict_sense="a meaning",
        wikdict_trans_list=translation,
        wikdict_lexentry=f"eng/{word}__{pos.title()}__1",
    )


def _resolved_entry(
    word: str,
    pos: str,
    frequency: int,
    translation: str,
    *,
    status: VocabularyStatus = VocabularyStatus.UNKNOWN,
) -> pipeline.ResolvedEntry:
    return pipeline.ResolvedEntry(
        occurrence=_occurrence(word, pos, frequency),
        sense=_resolved_sense(word, pos, translation),
        status=status,
    )


def _entries(count: int) -> list[pipeline.ResolvedEntry]:
    """`count` bereits aufgelöste Einzelwort-Einträge, `word0` am häufigsten,
    `word{count-1}` am seltensten — wie `pipeline.resolve_triage_entries` sie liefert."""
    return [
        _resolved_entry(f"word{index}", "NOUN", count - index, f"Übersetzung{index}")
        for index in range(count)
    ]


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


def test_bulk_action_marks_all_more_frequent_words(profile_con: sqlite3.Connection) -> None:
    """konzept.md §4, „Sammelaktion »ab hier kenne ich alles« — markiert alle
    häufigeren Wörter auf einen Schlag" (bauplan.md T10, hier über die Tastatur
    bedient): Position 3 markiert die drei häufigsten Wörter als bekannt, der Rest wird
    einzeln gefragt."""
    resolution = pipeline.TriageResolution(
        entries=_entries(5), known=0, resolved_known=0, skipped=0, deferred=0
    )
    answers = iter(["3", "s", "s"])  # Sammelaktion bis 3, dann zwei individuelle "skip"

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
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
    tied = [_resolved_entry("tied_a", "NOUN", 1, "A"), _resolved_entry("tied_b", "NOUN", 1, "B")]
    resolution = pipeline.TriageResolution(
        entries=tied, known=0, resolved_known=0, skipped=0, deferred=0
    )
    answers = iter(["1", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    events = _events(profile_con)
    bulk_marked = {lemma for lemma, _, origin in events if origin == "bulk_mark"}
    assert bulk_marked == {"tied_a"}


def test_learning_a_word_creates_a_card_with_the_already_resolved_sense(
    profile_con: sqlite3.Connection,
) -> None:
    """„will ich lernen" erzeugt eine `Card` mit der Bedeutung, die
    `pipeline.resolve_triage_entries` bereits aufgelöst hat (Befund schwer 1, zweite
    T16-Durchsicht) — kein weiterer Modellaufruf an dieser Stelle, `entry.sense` wird
    unverändert übernommen."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=0, resolved_known=0, skipped=0, deferred=0
    )
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert len(cards) == 1
    assert cards[0].occurrence.lemma.text == "word0"
    assert cards[0].sense.translation == "Übersetzung0"
    events = _events(profile_con)
    assert events == [("word0", "learning", "triage")]


def test_expressions_reach_the_triage_and_the_resulting_card(
    profile_con: sqlite3.Connection,
) -> None:
    """Abnahmekriterium 3 in klein (bauplan.md T16, „Wendungen erscheinen in der Triage
    und landen im Export"): Eine Wendung läuft durch dieselbe Triage wie ein Einzelwort
    und erzeugt bei „will ich lernen" ebenso eine Karte."""
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
        translation="aufgeben",
        wikdict_sense="admit defeat",
        wikdict_trans_list="aufgeben",
        wikdict_lexentry="eng/give_up__Verb__1",
    )
    resolution = pipeline.TriageResolution(
        entries=[
            pipeline.ResolvedEntry(
                occurrence=expression_occurrence,
                sense=expression_sense,
                status=VocabularyStatus.UNKNOWN,
            )
        ],
        known=0,
        resolved_known=0,
        skipped=0,
        deferred=0,
    )
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wendungen",
        card_direction=CardDirection.EN_DE,
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


def test_run_triage_pass_reports_entries_the_pipeline_already_filtered_as_known(
    profile_con: sqlite3.Connection,
) -> None:
    """Abnahmekriterium 6 (konzept.md, „Abnahmekriterien"): „Beim zweiten Durchlauf
    desselben Kapitels werden die als *bekannt* markierten Wörter **nicht erneut**
    abgefragt — das Profil greift." Der Vorfilter selbst liegt seit der zweiten
    T16-Durchsicht (Befund schwer 1) in `pipeline.resolve_triage_entries`
    (`tests/test_pipeline.py`) — hier wird nur geprüft, dass `run_triage_pass` die Zahl
    aus `resolution.known` meldet und ausschließlich zeigt, was tatsächlich in
    `resolution.entries` steht."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=1, resolved_known=0, skipped=0, deferred=0
    )
    written: list[str] = []
    answers = iter(["", "s"])  # keine Sammelaktion, dann "skip" für word0

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert not any(line.startswith("known_word (") for line in written)
    events = _events(profile_con)
    assert {lemma for lemma, _, _ in events} == {"word0"}
    assert any("bereits bekannt" in line for line in written)


def test_run_triage_pass_combines_both_ways_of_being_already_known_in_one_message(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund mittel, Durchsicht 46ef37b: Die Meldung „bereits bekannt" muss auch die
    Einträge zählen, die `pipeline.resolve_triage_entries` erst **nach** dem Auflösen als
    `KNOWN` verworfen hat (`resolution.resolved_known`) — nicht nur die des kostenlosen
    Vorfilters (`resolution.known`). Im Auftragsbeispiel fehlten so 21 von 25 Wörtern in
    der gemeldeten Zahl (4 statt 25)."""
    resolution = pipeline.TriageResolution(
        entries=[], known=4, resolved_known=21, skipped=0, deferred=0
    )
    written: list[str] = []

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: (_ for _ in ()).throw(AssertionError("keine Frage erwartet")),
        write_line=written.append,
    )

    matching = [line for line in written if "bereits bekannt" in line]
    assert len(matching) == 1
    assert "25 Wörter" in matching[0]


def test_run_triage_pass_reports_entries_skipped_for_no_matching_sense(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund schwer 1, Durchsicht 46ef37b: Ein Eintrag, den `resolve_triage_entries`
    übersprungen hat, weil das Modell trotz echter Wörterbuchkandidaten „keine passt"
    wählte (`resolution.skipped`), wird gezählt gemeldet — Regel 13, keine stille
    Störungsmeldung."""
    resolution = pipeline.TriageResolution(
        entries=[], known=0, resolved_known=0, skipped=2, deferred=0
    )
    written: list[str] = []

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: (_ for _ in ()).throw(AssertionError("keine Frage erwartet")),
        write_line=written.append,
    )

    matching = [line for line in written if "übersprungen" in line]
    assert len(matching) == 1
    assert "2 Wörter" in matching[0]


def test_new_meaning_of_a_known_word_is_marked_in_the_display(
    profile_con: sqlite3.Connection,
) -> None:
    """konzept.md §5, „Mehrdeutigkeit": Ein Eintrag mit `VocabularyStatus.
    NEW_MEANING_OF_KNOWN_WORD` wird in der Triage als „neue Bedeutung eines bekannten
    Wortes" gekennzeichnet, damit der Nutzer versteht, warum ein scheinbar bekanntes Wort
    erneut auftaucht."""
    entry = _resolved_entry(
        "bank", "NOUN", 2, "Ufer", status=VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD
    )
    resolution = pipeline.TriageResolution(
        entries=[entry], known=0, resolved_known=0, skipped=0, deferred=0
    )
    written: list[str] = []
    answers = iter(["", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    marked = [line for line in written if "neue Bedeutung eines bekannten Wortes" in line]
    assert len(marked) == 1
    assert "Ufer" in marked[0]


def test_a_word_without_a_dictionary_entry_keeps_its_uncertain_marker_when_learned(
    profile_con: sqlite3.Connection,
) -> None:
    """Regel 11 (dokumentation.md §4): Ein Wort ohne Wörterbucheintrag trägt weiterhin
    `uncertain=True`, wenn es gelernt wird — dieselbe Markierung, mit der `pipeline.
    resolve_triage_entries` es geliefert hat, ohne dass hier ein zweiter Modellaufruf
    nötig wäre (der erste unterblieb bereits dort, siehe `tests/test_pipeline.py`)."""
    placeholder = Sense(lemma=Lemma(text="obscure", pos="NOUN"), uncertain=True)
    entry = pipeline.ResolvedEntry(
        occurrence=_occurrence("obscure", "NOUN", 1),
        sense=placeholder,
        status=VocabularyStatus.UNKNOWN,
    )
    resolution = pipeline.TriageResolution(
        entries=[entry], known=0, resolved_known=0, skipped=0, deferred=0
    )
    answers = iter(["", "l"])

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert len(cards) == 1
    assert cards[0].sense.uncertain is True
    assert cards[0].sense.translation is None
