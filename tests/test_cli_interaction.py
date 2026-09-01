"""Prüft `cli/interaction.py` — die Triage über die Tastatur (bauplan.md T16).

Baut die Testvorrichtung direkt aus `entities`/`pipeline.ResolvedEntry`, ohne EPUB oder
spaCy: Geprüft werden die Entscheidungen, die die Triage trifft, nicht die
Bildschirmausgabe (dokumentation.md §5). Seit der zweiten T16-Durchsicht (Befund schwer 1)
liegen Profilabgleich, Häufigkeitssortierung, Bedeutungsauflösung durch das Modell und
Blockgröße in `pipeline.resolve_triage_entries`, nicht mehr hier — geprüft in
`tests/test_pipeline.py`. Diese Datei baut deshalb `pipeline.TriageResolution` direkt statt
über einen echten `resolve_triage_entries`-Aufruf, ohne Modellserver. Der volle Weg durch
`pipeline.run_chapter` bis zum Export ist `tests/test_cli_main.py` vorbehalten. Die
Blockschleife selbst (`run_triage_blocks`) hat ihre eigenen Tests weiter unten.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import pytest

from cli import interaction
from libreverbum import pipeline, profile
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


def _vocabulary_entry(word: str) -> pipeline.VocabularyEntry:
    """Ein unaufgelöster Eingabeeintrag für `run_triage_blocks` — als `resolution.remaining`
    weitergereicht wird eine `list[VocabularyEntry]`, nicht die bereits aufgelösten
    `ResolvedEntry` aus `_entries`. Kandidaten und Kenntnisstand bleiben leer, weil
    `resolve_block` in diesen Tests ohnehin nur gescriptet antwortet, statt sie
    auszuwerten."""
    return pipeline.VocabularyEntry(
        occurrence=_occurrence(word, "NOUN", 1), candidates=[], status={}
    )


def _scripted_resolver(
    responses: list[pipeline.TriageResolution],
) -> tuple[
    Callable[[Sequence[pipeline.VocabularyEntry]], pipeline.TriageResolution],
    list[list[pipeline.VocabularyEntry]],
]:
    """Ein `resolve_block`-Rückruf, der `responses` der Reihe nach ausliefert und jeden
    Aufruf (die tatsächlich übergebene Eingabe) in der zweiten Rückgabe protokolliert —
    so lässt sich prüfen, ob `run_triage_blocks` beim Folgeblock wirklich
    `resolution.remaining` weiterreicht statt der ursprünglichen `entries`."""
    calls: list[list[pipeline.VocabularyEntry]] = []
    responses_iter = iter(responses)

    def _resolve(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        calls.append(list(block))
        return next(responses_iter)

    return _resolve, calls


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
        entries=_entries(5), known=0, resolved_known=0, skipped=0, remaining=[]
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
    ).cards

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
        entries=tied, known=0, resolved_known=0, skipped=0, remaining=[]
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
        entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
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
    ).cards

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
        remaining=[],
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
    ).cards

    assert len(cards) == 1
    assert cards[0].occurrence.word_form == "gave up"
    assert cards[0].sense.translation == "aufgeben"


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
        entries=_entries(1), known=1, resolved_known=0, skipped=0, remaining=[]
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
        entries=[], known=4, resolved_known=21, skipped=0, remaining=[]
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
        entries=[], known=0, resolved_known=0, skipped=2, remaining=[]
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
        entries=[entry], known=0, resolved_known=0, skipped=0, remaining=[]
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
        entries=[entry], known=0, resolved_known=0, skipped=0, remaining=[]
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
    ).cards

    assert len(cards) == 1
    assert cards[0].sense.uncertain is True
    assert cards[0].sense.translation is None


def test_learning_a_word_without_a_dictionary_entry_is_refused_for_de_en(
    profile_con: sqlite3.Connection,
) -> None:
    """In Kartenrichtung `DE_EN` wird „lernen" auf einem Wort ohne Wörterbucheintrag nicht
    angenommen, sondern erneut gefragt (`interaction._card_is_possible`) — die Vorderseite
    trüge dort keine deutsche Bedeutung (`anki._DE_EN_MODEL`).

    Regel 13: Die Entscheidung wird nicht stillschweigend zu „skip" umgedeutet, und der
    Abbruch fällt nicht erst am Ende des Durchlaufs im Export an, wo er Deck und Druckseite
    samt aller übrigen Karten kostete (gemeldet am 01.09.2026). Dass die dritte Antwort
    verbraucht wird, ist der eigentliche Beleg: Wäre „l" angenommen worden, bliebe sie
    ungelesen und es gäbe eine Karte."""
    placeholder = Sense(lemma=Lemma(text="obscure", pos="NOUN"), uncertain=True)
    entry = pipeline.ResolvedEntry(
        occurrence=_occurrence("obscure", "NOUN", 1),
        sense=placeholder,
        status=VocabularyStatus.UNKNOWN,
    )
    resolution = pipeline.TriageResolution(
        entries=[entry], known=0, resolved_known=0, skipped=0, remaining=[]
    )
    answers = iter(["", "l", "s"])
    lines: list[str] = []

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.DE_EN,
        read_line=lambda _prompt: next(answers),
        write_line=lines.append,
    ).cards

    assert cards == []
    assert _events(profile_con) == [("obscure", "deferred", "triage")]
    assert any("de_en" in line for line in lines)


def test_learning_a_word_whose_form_has_no_boundary_in_the_sentence_is_refused_for_cloze(
    profile_con: sqlite3.Connection,
) -> None:
    """Derselbe Schutz für die zweite Unmöglichkeit (Befund mittel, Durchsicht 35736a9):
    Steht die Wortform an keiner Wortgrenze des Belegsatzes (`heart` in `heart-broken`),
    ist daraus kein Lückentext zu bilden — `anki.export_deck` bräche ab, und weil es der
    erste der beiden Exporte ist, kostete das Deck, Druckseite und alle übrigen Karten.

    Der Fall ist nicht selten: 2.170 von 103.897 Wortvorkommen der Kapitel 1 bis 12 von
    `tools/dorian_gray.epub` (2,1 %). Vor dieser Nachbesserung fing die Triage allein den
    `de_en`-Fall ab und ließ diesen laufen."""
    occurrence = Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text="heart", pos="NOUN"),
        word_form="heart",
        example_sentence="I can't tell you how heart-broken I am about the whole thing.",
        frequency=1,
        proper_noun_frequency=0,
    )
    entry = pipeline.ResolvedEntry(
        occurrence=occurrence,
        sense=_resolved_sense("heart", "NOUN", "Herz"),
        status=VocabularyStatus.UNKNOWN,
    )
    resolution = pipeline.TriageResolution(
        entries=[entry], known=0, resolved_known=0, skipped=0, remaining=[]
    )
    answers = iter(["", "l", "s"])
    lines: list[str] = []

    cards = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.CLOZE,
        read_line=lambda _prompt: next(answers),
        write_line=lines.append,
    ).cards

    assert cards == []
    assert _events(profile_con) == [("heart", "deferred", "triage")]
    assert any("Lückentext" in line for line in lines)


def test_run_triage_blocks_asks_continue_and_hands_the_remainder_to_the_next_block(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, „Blockweise Triage mit Vorladen — entschieden": Nach einem
    vollständig durchgeklickten Block mit vorhandenem Rest wird die Fortsetzungsfrage
    gestellt; „j" führt zu einem zweiten `resolve_block`-Aufruf mit genau
    `resolution.remaining` als Eingabe — nicht mit der ursprünglichen `entries`-Liste.

    Verfälschungsprobe: Reicht `run_triage_blocks` beim Folgeblock `entries` statt
    `resolution.remaining` weiter (`current` nie auf `resolution.remaining` gesetzt), sieht
    der zweite `resolve_block`-Aufruf dieselbe Liste wie der erste — der Vergleich
    `calls[1] == leftover` schlägt fehl. Test war damit rot, bevor `current =
    resolution.remaining` stand."""
    initial_entries = [_vocabulary_entry("a"), _vocabulary_entry("b")]
    leftover = [_vocabulary_entry("leftover")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            ),
            pipeline.TriageResolution(
                entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
            ),
        ]
    )
    answers = iter(["", "s", "j"])  # keine Sammelaktion, "skip" für word0, "j" fortsetzen

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=initial_entries,
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert cards == []
    assert len(calls) == 2
    assert calls[0] == initial_entries
    assert calls[1] == leftover


def test_run_triage_blocks_reports_the_exact_count_of_unchecked_entries_on_no(
    profile_con: sqlite3.Connection,
) -> None:
    """„nein" beendet die Blockschleife und meldet die **Zahl** der ungeprüften Einträge —
    nicht nur, dass irgendetwas gemeldet wird.

    Verfälschungsprobe: Wird die Fortsetzungsfrage ignoriert und immer fortgesetzt (die
    Rückgabe von `_ask_continue` nicht ausgewertet), ruft die Schleife `resolve_block` ein
    zweites Mal auf, statt zu enden — `len(calls) == 1` schlägt fehl. Test war damit rot,
    bevor `if not _ask_continue(...): return cards` stand."""
    leftover = [_vocabulary_entry("x"), _vocabulary_entry("y"), _vocabulary_entry("z")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            )
        ]
    )
    answers = iter(["", "s", "n"])
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert len(calls) == 1
    matching = [line for line in written if "noch nicht geprüft" in line]
    assert len(matching) == 1
    assert "3 Wörter" in matching[0]


def test_run_triage_blocks_treats_enter_as_no_at_the_continuation_question(
    profile_con: sqlite3.Connection,
) -> None:
    """Enter beendet die Blockschleife ebenso wie „nein" — Aufhören ist die sichere
    Vorgabe (dieselbe Handhabung wie bei der Sammelaktion, Enter = keine).

    Verfälschungsprobe: Vertauscht `_ask_continue` die Vorgabe (Enter würde als „ja"
    gelten), verlangt die Schleife einen zweiten `resolve_block`-Aufruf — `next(answers)`
    lieft dafür ins Leere, `StopIteration` bricht den Test ab, statt ihn regulär enden zu
    lassen. Test war damit rot, bevor `answer in ("", "n", "nein")` stand."""
    leftover = [_vocabulary_entry("x")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            )
        ]
    )
    answers = iter(["", "s", ""])  # dritte Antwort: Enter auf die Fortsetzungsfrage
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert len(calls) == 1
    assert any("1 Wörter" in line and "noch nicht geprüft" in line for line in written)


def test_run_triage_blocks_asks_the_continuation_question_again_on_invalid_input(
    profile_con: sqlite3.Connection,
) -> None:
    """Regel 13 (dokumentation.md §4): Eine unbekannte Eingabe bei der Fortsetzungsfrage
    verwirft keine Entscheidung stillschweigend als „nein", sondern führt zu einer
    erneuten Frage — dieselbe Handhabung wie `_ask_action`.

    Verfälschungsprobe: Deutet `_ask_continue` eine unbekannte Eingabe stillschweigend als
    „nein" statt erneut zu fragen, bleibt es beim einen `resolve_block`-Aufruf — `len(calls)
    == 2` schlägt fehl. Test war damit rot, bevor die Schleife bei unbekannter Eingabe
    erneut fragte, statt `False` zurückzugeben."""
    leftover = [_vocabulary_entry("x")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            ),
            pipeline.TriageResolution(
                entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
            ),
        ]
    )
    # "x" ist keine gültige Antwort auf die Fortsetzungsfrage, "j" die zweite Antwort danach.
    answers = iter(["", "s", "x", "j"])
    written: list[str] = []

    interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(calls) == 2
    assert calls[1] == leftover
    assert any("Ungültige Eingabe" in line for line in written)


def test_run_triage_blocks_does_not_ask_to_continue_after_q(
    profile_con: sqlite3.Connection,
) -> None:
    """Abnahmekriterium 7: `q` in der Einzelabfrage beendet die Blockschleife **ohne**
    Fortsetzungsfrage — der Nutzer hat den Abbruch bereits erklärt.

    Verfälschungsprobe: Fragt `run_triage_blocks` nach einem Abbruch trotzdem weiter
    (fehlende `if triage_pass.aborted`-Prüfung), verlangt sie eine vierte Antwort, die die
    Antwortliste nicht hergibt — `next(answers)` wirft `StopIteration`. Test war damit rot,
    bevor die Prüfung auf `aborted` vor der Fortsetzungsfrage stand. Der `resolve_block`-
    Rückruf selbst darf dabei kein zweites Mal aufgerufen werden."""
    leftover = [_vocabulary_entry("x")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(2), known=0, resolved_known=0, skipped=0, remaining=leftover
            )
        ]
    )
    answers = iter(["", "q"])  # keine Sammelaktion, dann sofortiger Abbruch bei word0
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a"), _vocabulary_entry("b")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert len(calls) == 1
    assert any("1 Wörter" in line and "noch nicht geprüft" in line for line in written)


def test_run_triage_blocks_does_not_ask_to_continue_when_nothing_remains(
    profile_con: sqlite3.Connection,
) -> None:
    """Ist `resolution.remaining` schon nach dem ersten Block leer, wird gar nicht erst
    gefragt — es gibt nichts, womit fortgesetzt werden könnte.

    Verfälschungsprobe: Fehlt die Prüfung auf ein leeres `current` vor der
    Fortsetzungsfrage, verlangt die Schleife eine dritte Antwort, die die Liste nicht
    hergibt — `next(answers)` wirft `StopIteration`. Test war damit rot, bevor `if not
    current: ... return cards` vor der Fortsetzungsfrage stand."""
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
            )
        ]
    )
    answers = iter(["", "s"])  # keine dritte Antwort — eine Fortsetzungsfrage wäre ein Fehler
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert len(calls) == 1
    assert any("durchgesehen" in line for line in written)


def test_run_triage_blocks_collects_cards_from_every_block_into_one_list(
    profile_con: sqlite3.Connection,
) -> None:
    """Karten aus mehreren Blöcken kommen vollständig und in einer Liste zurück — nicht
    nur die des letzten Blocks.

    Verfälschungsprobe: Überschreibt `run_triage_blocks` die gesammelten Karten bei jedem
    Block statt sie anzuhängen (`cards = triage_pass.cards` statt `cards.extend(...)`),
    fehlt die Karte des ersten Blocks im Ergebnis — `len(cards) == 2` schlägt fehl (nur 1).
    Test war damit rot, bevor `cards.extend(triage_pass.cards)` stand."""
    leftover = [_vocabulary_entry("b")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            ),
            pipeline.TriageResolution(
                entries=[_resolved_entry("second", "NOUN", 1, "Zweitens")],
                known=0,
                resolved_known=0,
                skipped=0,
                remaining=[],
            ),
        ]
    )
    answers = iter(["", "l", "j", "", "l"])
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(calls) == 2
    assert len(cards) == 2
    assert {card.occurrence.lemma.text for card in cards} == {"word0", "second"}


def test_run_triage_blocks_names_the_block_number_from_the_second_block_on(
    profile_con: sqlite3.Connection,
) -> None:
    """„Ab dem zweiten Block nennt die Kopfzeile der Liste die Blocknummer" (Auftragstext):
    Der erste Block zeigt die Kopfzeile unverändert, ab dem zweiten trägt sie die
    Blocknummer — sonst verliert ein Nutzer nach der dritten Fortsetzung die Orientierung.

    Verfälschungsprobe: Reicht `run_triage_pass` `block_number` nicht an `_bulk_phase`
    weiter (fester Wert 1), fehlt „Block 2" in der zweiten Kopfzeile — der zweite
    `any(...)`-Ausdruck schlägt fehl. Test war damit rot, bevor `block_number=block_number`
    beim `_bulk_phase`-Aufruf stand."""
    leftover = [_vocabulary_entry("b")]
    resolve_block, calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
            ),
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
            ),
        ]
    )
    answers = iter(["", "s", "j", "", "s"])
    written: list[str] = []

    interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_block=resolve_block,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(calls) == 2
    headings = [line for line in written if line.startswith("-- Wörter")]
    assert headings == ["-- Wörter: 1 --", "-- Wörter (Block 2): 1 --"]
