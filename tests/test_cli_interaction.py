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

import re
import sqlite3
import threading
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import pytest

from cli import display, interaction
from libreverbum import dictionary, pipeline, profile
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


def test_non_numeric_bulk_answer_asks_again_instead_of_skipping(
    profile_con: sqlite3.Connection,
) -> None:
    """Offener Punkt aus technik.md §9, „Offene Punkte" (behoben durch Nutzerentscheidung
    vom 14.09.2026): Eine vertippte Antwort auf die Sammelaktionsfrage („1O" statt „10")
    überspringt die Sammelaktion nicht mehr, sondern führt zu einer erneuten Frage — die
    danach gegebene gültige Zahl bucht den Ausschnitt vollständig.

    Verfälschungsprobe: Vor dieser Behebung lieferte `_bulk_phase` bei einer nicht-zahligen
    Antwort sofort `set()` zurück, die Meldung „Sammelaktion übersprungen." stand fest, und
    die zweite Antwort „3" wäre als erste Antwort der anschließenden Einzelabfrage
    verbraucht worden — die Zusicherung über `bulk_marked` unten (drei Wörter statt einer
    leeren Menge) wäre damit falsch gewesen. Test war damit rot, bevor `_bulk_phase` bei
    einer ungültigen Antwort erneut fragte."""
    resolution = pipeline.TriageResolution(
        entries=_entries(5), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    # Sammelaktion: "1O" (Vertipper, muss erneut fragen), dann "3". Einzelabfrage: 2x "s".
    answers = iter(["1O", "3", "s", "s"])

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

    bulk_marked = {lemma for lemma, _, origin in _events(profile_con) if origin == "bulk_mark"}
    assert bulk_marked == {"word0", "word1", "word2"}
    hint = next(line for line in written if "1O" in line)
    assert "ist keine Zahl" in hint
    assert "übersprungen" not in hint


def test_out_of_range_bulk_answer_asks_again_instead_of_skipping(
    profile_con: sqlite3.Connection,
) -> None:
    """Wie beim vertippten Fall: Eine Zahl außerhalb der Liste (hier `0` und `6` bei fünf
    Einträgen) überspringt die Sammelaktion nicht, sondern führt zu einer erneuten Frage.
    Beide Ränder werden geprüft, weil ein Off-by-one nur an einem davon sichtbar würde.

    Verfälschungsprobe: Vor der Behebung lieferte `_bulk_phase` bei `not 1 <= position <=
    len(ordered)` sofort `set()` — die zweite und dritte Antwort ("6", "3") wären in der
    anschließenden Einzelabfrage verbraucht worden statt in der Sammelaktion, und die
    Zusicherung unten wäre falsch gewesen. Test war damit rot, bevor `_bulk_phase` erneut
    fragte."""
    resolution = pipeline.TriageResolution(
        entries=_entries(5), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    # Sammelaktion: "0" und "6" (beide außerhalb von 1..5), dann "3". Einzelabfrage: 2x "s".
    answers = iter(["0", "6", "3", "s", "s"])

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

    bulk_marked = {lemma for lemma, _, origin in _events(profile_con) if origin == "bulk_mark"}
    assert bulk_marked == {"word0", "word1", "word2"}
    hint_zero = next(line for line in written if '"0"' in line)
    hint_six = next(line for line in written if '"6"' in line)
    assert "liegt außerhalb der Liste" in hint_zero
    assert "liegt außerhalb der Liste" in hint_six
    assert "übersprungen" not in hint_zero
    assert "übersprungen" not in hint_six


def test_non_numeric_and_out_of_range_bulk_hints_are_worded_differently(
    profile_con: sqlite3.Connection,
) -> None:
    """Die beiden Fälle bleiben unterschieden (Auftragstext): eine nicht-zahlige und eine
    außerhalb der Liste liegende Antwort sagen verschiedene Dinge, auch wenn nur noch der
    Nachsatz „Sammelaktion übersprungen" wegfällt."""
    resolution = pipeline.TriageResolution(
        entries=_entries(3), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["1O", "9", "", "s", "s", "s"])

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

    non_numeric_hint = next(line for line in written if "1O" in line)
    out_of_range_hint = next(line for line in written if '"9"' in line)
    assert non_numeric_hint != out_of_range_hint
    assert "ist keine Zahl" in non_numeric_hint
    assert "liegt außerhalb der Liste" in out_of_range_hint


def test_empty_bulk_answer_still_skips_immediately_without_booking_anything(
    profile_con: sqlite3.Connection,
) -> None:
    """Enter bleibt unverändert „keine Sammelaktion" (Auftragstext, Punkt 1): eine leere
    Antwort liefert sofort `set()`, ohne Rückfrage und ohne ein Ereignis im Profil.

    Verfälschungsprobe: Fragte `_bulk_phase` auch bei einer Leereingabe erneut nach (statt
    sofort zurückzukehren), verbrauchte die Sammelaktion die erste individuelle Antwort
    "s" als weitere Sammelaktionsantwort — der Einzelabfrage fehlte danach eine Antwort
    und `next(answers)` würfe `StopIteration`. Test war damit rot, bevor die Leereingabe
    ohne erneute Frage sofort überspringt."""
    resolution = pipeline.TriageResolution(
        entries=_entries(5), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    answers = iter(["", "s", "s", "s", "s", "s"])

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

    bulk_marked = {lemma for lemma, _, origin in _events(profile_con) if origin == "bulk_mark"}
    assert bulk_marked == set()


def test_numbered_bulk_list_is_printed_exactly_once_despite_repeated_invalid_answers(
    profile_con: sqlite3.Connection,
) -> None:
    """Auftragstext, Punkt 3: Die nummerierte Liste wird bei einer erneuten Frage NICHT
    noch einmal gedruckt — wiederholt wird allein die Frage, auch nach mehreren
    Fehleingaben hintereinander."""
    resolution = pipeline.TriageResolution(
        entries=_entries(5), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["x", "0", "99", "abc", "3", "s", "s"])

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

    list_lines = [line for line in written if re.match(r"^\s*\d+\.\s+NOUN", line)]
    assert len(list_lines) == len(_entries(5))


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


def test_empty_answer_to_the_triage_prompt_is_not_booked_and_asks_again(
    profile_con: sqlite3.Connection,
) -> None:
    """Offener Punkt aus technik.md §9, „Offene Punkte" (behoben durch Nutzerentscheidung
    vom 14.09.2026): Eine Leereingabe auf den Triage-Prompt `[k]enne ich  [l]ernen  [s]kip
    [q]uit >` bucht nichts als „skip", sondern führt zu einer erneuten Frage.

    Verfälschungsprobe: Bildete `_ACTIONS` weiterhin eine Leereingabe auf „skip" ab (der
    Stand vor dieser Behebung), bekäme `word0` sofort und stillschweigend
    `KnowledgeState.DEFERRED`, die zweite Antwort „l" bliebe unverwendet liegen, und die
    Zusicherungen unten (eine Karte, ein `learning`-Ereignis) wären rot. Test war damit rot,
    bevor die Leereingabe aus `_ACTIONS` entfernt wurde."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    # Sammelaktion: keine (Enter). Triage: erst leer (ungültig, muss erneut fragen), dann "l".
    answers = iter(["", "", "l"])

    triage_pass = interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(triage_pass.cards) == 1
    assert _events(profile_con) == [("word0", "learning", "triage")]
    assert any("Keine Eingabe" in line for line in written)


def test_invalid_nonempty_answer_to_the_triage_prompt_names_what_was_typed(
    profile_con: sqlite3.Connection,
) -> None:
    """Der Hinweis auf eine ungültige, nicht-leere Antwort auf den Triage-Prompt nennt die
    tatsächlich eingegangene Zeichenfolge — auf `display.PLAIN_STYLE` (keine
    Unicode-Fähigkeit, die Vorgabe von `run_triage_pass`) in geraden ASCII-
    Anführungszeichen, keinen typografischen.

    Verfälschungsprobe: Stand statt dieser Meldung weiterhin die alte, generische
    „Ungültige Eingabe — k, l, s oder q erwartet." ohne die eingegebene Zeichenfolge, fand
    sich keine Zeile mit „ka" und „erwartet" zugleich, und der `next(...)`-Aufruf unten
    warf `StopIteration`. Test war damit rot, bevor der Hinweis die Eingabe nannte."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["", "ka", "s"])

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

    hint = next(line for line in written if "ka" in line and "erwartet" in line)
    assert '"ka"' in hint
    assert "„" not in hint
    assert "“" not in hint


def test_ask_action_hint_uses_typographic_quotes_on_a_unicode_capable_style() -> None:
    """Gegenprobe zum vorigen Test: Auf einem `Style` mit Unicode-Fähigkeit erscheinen die
    typografischen Anführungszeichen aus `display.quote`, nicht die ASCII-Form — der Hinweis
    hängt also tatsächlich am übergebenen `style`, nicht an einer fest verdrahteten Form."""
    unicode_style = display.Style(supports_color=False, supports_unicode=True, width=80)
    written: list[str] = []
    answers = iter(["ka", "s"])

    interaction._ask_action(lambda _prompt: next(answers), written.append, style=unicode_style)

    hint = next(line for line in written if "ka" in line)
    assert "„ka“" in hint


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("k", "known"),
        ("kenne", "known"),
        ("K", "known"),
        ("KENNE", "known"),
        ("l", "learn"),
        ("lernen", "learn"),
        ("L", "learn"),
        ("LERNEN", "learn"),
        ("s", "skip"),
        ("skip", "skip"),
        ("S", "skip"),
        ("SKIP", "skip"),
        ("q", "quit"),
        ("quit", "quit"),
        ("Q", "quit"),
        ("QUIT", "quit"),
    ],
)
def test_ask_action_accepts_all_valid_answers_case_insensitively(raw: str, expected: str) -> None:
    """Die gültigen Antworten (k, kenne, l, lernen, s, skip, q, quit, auch in
    Großschreibung) funktionieren nach der Behebung des offenen Punkts unverändert.

    Verfälschungsprobe: Ein `_ACTIONS.get(typed)` ohne das `.lower()` auf der Eingabe ließe
    jede Großschreibvariante (`K`, `KENNE`, …) als ungültig durchfallen; ohne eine zweite
    Antwort in `answers` würfe die Schleife dann `StopIteration` statt eines Ergebnisses —
    dieser Test war daran für jede Großschreibvariante rot."""
    answers = iter([raw])

    action = interaction._ask_action(
        lambda _prompt: next(answers), _no_op_write, style=display.PLAIN_STYLE
    )

    assert action == expected


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


def test_run_triage_pass_reports_the_already_known_count_in_the_singular_for_exactly_one_word(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund B (Durchsicht 5fda1b9): Bei genau einem laut Profil bereits bekannten
    Eintrag muss die Meldung „1 Wort … bereits bekannt" lauten, nicht „1 Wörter … bereits
    bekannt" — derselbe Fehler wie bei der Meldung „N noch nicht geprüft" aus
    `run_triage_blocks`, hier an der Meldung aus `run_triage_pass` geprüft.

    Verfälschungsprobe: Ohne `_count_label` (stattdessen `f"{...} {label} laut Profil …"`
    wie vor dieser Behebung) steht in `matching[0]` „1 Wörter", nicht „1 Wort" — dieser
    Test war daran rot, siehe Bericht."""
    resolution = pipeline.TriageResolution(
        entries=[], known=1, resolved_known=0, skipped=0, remaining=[]
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
    assert "1 Wort " in matching[0]
    assert "1 Wörter" not in matching[0]


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


def test_run_triage_pass_reports_the_skipped_count_in_the_singular_for_exactly_one_expression(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund B (Durchsicht 5fda1b9): Dieselbe Grammatikkorrektur wie bei der Meldung
    „bereits bekannt", hier für `resolution.skipped` und mit `label="Wendungen"` — die
    zweite der beiden Bezeichnungen, die `_count_label` heute kennt, damit der Singular
    nicht nur für „Wörter" geprüft ist.

    Verfälschungsprobe: Ohne `_count_label` steht in `matching[0]` „1 Wendungen", nicht
    „1 Wendung" — dieser Test war daran rot, siehe Bericht."""
    resolution = pipeline.TriageResolution(
        entries=[], known=0, resolved_known=0, skipped=1, remaining=[]
    )
    written: list[str] = []

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wendungen",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: (_ for _ in ()).throw(AssertionError("keine Frage erwartet")),
        write_line=written.append,
    )

    matching = [line for line in written if "übersprungen" in line]
    assert len(matching) == 1
    assert "1 Wendung " in matching[0]
    assert "1 Wendungen" not in matching[0]


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
    # Bauschritt 2/2 der Konsolenausgabe (02.09.2026): Die Markierung steht seither auf
    # einer eigenen Zeile statt an die Bedeutungszeile angehängt — "Ufer" steht deshalb
    # nicht mehr in derselben Zeile wie die Markierung, sondern in der Kopfzeile davor.
    heading = [line for line in written if "Ufer" in line]
    assert len(heading) == 1


def test_the_new_meaning_marker_appears_only_for_that_one_status(
    profile_con: sqlite3.Connection,
) -> None:
    """Gegenprobe zum vorigen Test: Ein Eintrag mit `VocabularyStatus.UNKNOWN` (der
    häufige Fall) trägt die Markierung „neue Bedeutung eines bekannten Wortes" **nicht** —
    sonst wäre die Kennzeichnung bedeutungslos.

    Verfälschungsprobe: Die `if entry.status is VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD`
    in `_entry_lines` durch eine Bedingung ersetzt, die immer wahr ist, ließ diesen Test
    rot werden — der vorige Test allein hätte das nicht bemerkt, weil er nie einen
    `UNKNOWN`-Eintrag prüft."""
    entry = _resolved_entry("word0", "NOUN", 1, "Wort", status=VocabularyStatus.UNKNOWN)
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

    assert not any("neue Bedeutung eines bekannten Wortes" in line for line in written)


def test_an_entry_shows_word_form_pos_frequency_sense_label_translation_and_example(
    profile_con: sqlite3.Connection,
) -> None:
    """Ein Eintrag zeigt weiterhin sämtliche Angaben — Wortform, Wortart, Häufigkeit,
    Bedeutungsangabe, Übersetzung, Belegsatz —, nur umgeordnet (Auftragstext vom
    02.09.2026, „Es geht kein Inhalt verloren"). Geprüft an einem Eintrag mit
    Platzhalter-Bedeutungsangabe (`dictionary.NO_SENSE_LABEL`, Regel 1: Zeilen ohne
    `sense`-Text werden **nicht** weggefiltert), damit auch der häufige Fall ohne
    `wikdict_sense`-Text gedeckt ist."""
    sense = Sense(
        lemma=Lemma(text="lurid", pos="ADJ"),
        translation="grell",
        wikdict_sense=None,
        wikdict_trans_list="grell",
        wikdict_lexentry="eng/lurid__Adjective__1",
    )
    occurrence = Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text="lurid", pos="ADJ"),
        word_form="lurid",
        example_sentence="The lurid light flickered on the wall.",
        frequency=3,
        proper_noun_frequency=0,
    )
    entry = pipeline.ResolvedEntry(
        occurrence=occurrence, sense=sense, status=VocabularyStatus.UNKNOWN
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

    joined = "\n".join(written)
    assert "lurid" in joined
    assert "grell" in joined
    assert "ADJ" in joined
    assert "3x im Kapitel" in joined
    assert dictionary.NO_SENSE_LABEL in joined
    assert "The lurid light flickered on the wall." in joined


def test_an_uncertain_entry_without_a_dictionary_match_still_shows_its_placeholder_label(
    profile_con: sqlite3.Connection,
) -> None:
    """Regel 1 (dokumentation.md §4) am zweiten Randfall: Ein `uncertain`-Eintrag (keine
    Wörterbuchzeile getroffen) zeigt weiterhin `dictionary.UNCERTAIN_LABEL` statt zu
    verschwinden — dieselbe Zusicherung wie beim vorigen Test, hier für den Platzhalter
    „unsicher" statt „keine Angabe"."""
    placeholder = Sense(lemma=Lemma(text="obscure", pos="ADJ"), uncertain=True)
    entry = pipeline.ResolvedEntry(
        occurrence=_occurrence("obscure", "ADJ", 1),
        sense=placeholder,
        status=VocabularyStatus.UNKNOWN,
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

    assert any(dictionary.UNCERTAIN_LABEL in line for line in written)


def test_two_consecutive_entries_are_separated_by_a_divider(
    profile_con: sqlite3.Connection,
) -> None:
    """Die ursprüngliche Beschwerde (Auftragstext vom 02.09.2026, Nutzermeldung): „Man
    sieht klar wo die vorherige Ausgabe aufhört, die nächste beginnt." Zwei
    aufeinanderfolgende Einträge tragen deshalb je eine eigene Trennlinie
    (`display.entry_rule`) — und dazwischen mindestens eine Leerzeile, der Trenner zur
    vorigen Eingabezeile.

    Verfälschungsprobe: `write_line("")` nach der Entscheidung eines Eintrags
    (`_individual_phase`) entfernt ließ die Leerzeilen-Zusicherung unten fehlschlagen,
    während die Trennlinien selbst (aus `_entry_lines`) unverändert blieben — dieser Test
    prüft deshalb **beides**, nicht nur die Trennlinien allein."""
    resolution = pipeline.TriageResolution(
        entries=_entries(2), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["", "s", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        style=display.PLAIN_STYLE,
    )

    rule_indices = [
        index
        for index, line in enumerate(written)
        if line.strip().startswith("-") and " von " in line
    ]
    assert len(rule_indices) == 2, "Erwartet: eine Trennlinie je Eintrag."
    # Zwischen den beiden Trennlinien stehen zwei Leerzeilen: die aus `_ask_action` vor
    # dem eigenen Prompt des ersten Eintrags **und** die trennende Leerzeile danach
    # (Auftragstext). Nur auf "mindestens eine" zu prüfen wäre zu schwach — diese eine
    # steht auch ohne den Trenner bereits da, weil jede Einzelfrage selbst mit einer
    # Leerzeile beginnt (dokumentation.md §5, „Bleibt der Test … grün, ist die
    # Zusicherung zu schwach").
    blanks_between = [
        index for index in range(rule_indices[0] + 1, rule_indices[1]) if written[index] == ""
    ]
    assert len(blanks_between) == 2, (
        "Zwischen den beiden Trennlinien fehlt die trennende Leerzeile nach der Entscheidung."
    )


def _rules(written: list[str]) -> list[str]:
    """Die Trennlinien aus `display.entry_rule` unter den geschriebenen Zeilen — sie tragen
    beide Zähler (`display.PLAIN_STYLE`, also `-` und `|`)."""
    return [line for line in written if line.strip().startswith("-") and " von " in line]


def test_the_learning_counter_grows_with_every_entry_chosen_for_learning(
    profile_con: sqlite3.Connection,
) -> None:
    """Zweite Nutzermeldung vom 02.09.2026: „Was mir irgendwie noch fehlt ist eine Anzeige,
    wie viele Vokabeln man bis jetzt zum Lernen ausgewählt hat." Die Zahl steht in der
    Trennlinie jedes Eintrags und ist der Stand **vor** der anstehenden Entscheidung: Der
    erste Eintrag zeigt 0, und nachdem er „lernen" bekommen hat, zeigt der zweite 1.

    Verfälschungsprobe: `chosen_before + len(cards)` in `_individual_phase` durch
    `chosen_before` ersetzt (der Zähler bleibt also stehen) — die zweite Zusicherung wurde
    rot, die erste blieb grün."""
    resolution = pipeline.TriageResolution(
        entries=_entries(2), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["", "l", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        style=display.PLAIN_STYLE,
    )

    rules = _rules(written)
    assert rules[0].endswith("1 von 2 | 0 zum Lernen")
    assert rules[1].endswith("2 von 2 | 1 zum Lernen")


def test_the_learning_counter_continues_where_the_previous_deck_stopped(
    profile_con: sqlite3.Connection,
) -> None:
    """Zweite Nutzermeldung vom 02.09.2026, Festlegung des Nutzers: Wörter und Wendungen
    zählen **fortlaufend**, nicht je Deckel neu — die Zahl in der Trennlinie ist damit das,
    was am Ende tatsächlich ins Anki-Deck geht. `chosen_before` trägt den Stand des vorigen
    Deckels (in `cli.main` `len(word_cards)`) herein, und die Kapitelbilanz am Blockende
    nennt die Summe.

    Verfälschungsprobe: `chosen_before` in `run_triage_pass` nicht an `_individual_phase`
    weitergereicht (fest 0) — beide Zusicherungen unten wurden rot."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["", "l"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wendungen",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        chosen_before=6,
        style=display.PLAIN_STYLE,
    )

    assert _rules(written)[0].endswith("1 von 1 | 6 zum Lernen")
    assert any("Insgesamt 7 Vokabeln zum Lernen" in line for line in written)


def test_every_block_ends_with_a_summary_of_its_decisions(profile_con: sqlite3.Connection) -> None:
    """Zweite Nutzermeldung vom 02.09.2026: Am Blockende steht, was der Block gebracht hat.
    Die als bekannt gebuchten zählen die Sammelaktion mit — für den Nutzer ist das eine
    Zahl, nicht zwei Wege dorthin (`Origin.BULK_MARK` und `Origin.TRIAGE` buchen beide
    `KnowledgeState.KNOWN`).

    Hier: vier Einträge, die Sammelaktion bucht die ersten zwei, danach je einmal „lernen"
    und „überspringen".

    Verfälschungsprobe: `len(bulk_marked)` in `_write_block_summary` weggelassen — die
    Bilanz meldete dann „0 als bekannt gebucht", die Zusicherung unten wurde rot."""
    resolution = pipeline.TriageResolution(
        entries=_entries(4), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["2", "l", "s"])

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        style=display.PLAIN_STYLE,
    )

    assert any(
        "Block beendet: 1 zum Lernen, 2 als bekannt gebucht, 1 übersprungen." in line
        for line in written
    ), written


def test_block_summary_after_an_abort_does_not_claim_the_block_was_finished(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund 5 (Durchsicht e537273): Nach `q` stand „Block beendet:" unmittelbar unter
    „Abgebrochen." — der Block wurde in diesem Fall gerade nicht beendet, sondern
    verlassen. Die Zahlen und ihre Reihenfolge bleiben unverändert, nur die Überschrift
    wechselt auf „Bis hierher:".

    Verfälschungsprobe: `heading` in `_write_block_summary` fest auf „Block beendet"
    belassen (der Stand vor dieser Behebung) lässt die zweite Zusicherung unten rot
    werden."""
    resolution = pipeline.TriageResolution(
        entries=_entries(2), known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["", "q"])  # keine Sammelaktion, sofortiger Abbruch bei word0

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        style=display.PLAIN_STYLE,
    )

    assert any(
        "Bis hierher: 0 zum Lernen, 0 als bekannt gebucht, 0 übersprungen." in line
        for line in written
    ), written
    assert not any("Block beendet" in line for line in written)


def test_entries_use_ascii_fallback_characters_without_unicode_support(
    profile_con: sqlite3.Connection,
) -> None:
    """`display.PLAIN_STYLE` (keine Sonderzeichenfähigkeit) — der Pfeil in der Kopfzeile
    steht als ASCII-Ersatz `->`, nicht als `→`, und kein `cli.interaction`-Baustein
    schreibt das Unicode-Zeichen von Hand hinein."""
    resolution = pipeline.TriageResolution(
        entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
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
        style=display.PLAIN_STYLE,
    )

    joined = "\n".join(written)
    assert "  ->  " in joined
    assert "→" not in joined


def test_no_written_line_contains_a_control_sequence_without_ansi_support(
    profile_con: sqlite3.Connection,
) -> None:
    """Die wichtigste Zusicherung überhaupt (Auftragstext vom 02.09.2026): Ohne
    ANSI-fähiges Ziel (`display.PLAIN_STYLE`) enthält **keine** ausgegebene Zeile eine
    Steuersequenz (`\\x1b`) — sie betrifft jede Umleitung in eine Datei. Geprüft über
    einen vollständigen Block mit Sammelaktion, einer neuen Bedeutung eines bekannten
    Wortes und einer regulären Einzelabfrage, damit kein Anzeigepfad ausgelassen wird.

    Verfälschungsprobe: `display._decorate` fest die ANSI-Codes anhängen lassen, ohne
    `style.supports_color` auszuwerten (dieselbe Verfälschung wie in
    `tests/test_cli_display.py`), ließ diesen Test rot werden."""
    entries = [
        _resolved_entry("word0", "NOUN", 3, "Erstens"),
        _resolved_entry(
            "bank", "NOUN", 2, "Ufer", status=VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD
        ),
    ]
    resolution = pipeline.TriageResolution(
        entries=entries, known=0, resolved_known=0, skipped=0, remaining=[]
    )
    written: list[str] = []
    answers = iter(["1", "s"])  # Sammelaktion markiert word0, dann "skip" für bank

    interaction.run_triage_pass(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        resolution=resolution,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
        style=display.PLAIN_STYLE,
    )

    assert not any("\x1b" in line for line in written)


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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
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

    Seit Bauschritt 3/4 (technik.md §12, „Vorladen …") stößt die Schleife den nächsten
    Block bereits an, sobald der aktuelle feststeht — auch dann, wenn „nein" ihn später
    verwirft; `len(calls)` ist deshalb kein stabiler Indikator mehr dafür, ob die Schleife
    korrekt beendet (der Vorladeblock läuft dazu in einem eigenen Faden, dessen genauer
    Abschlusszeitpunkt hier nicht geprüft wird — Wettlauf, dokumentation.md §5). Geprüft
    wird deshalb an der **Meldung**, nicht an der Aufrufzahl.

    Verfälschungsprobe: Wird die Fortsetzungsfrage ignoriert und immer fortgesetzt (die
    Rückgabe von `_ask_continue` nicht ausgewertet), fehlt die Meldung „... noch nicht
    geprüft" — `run_triage_pass` liefe stattdessen ein zweites Mal durch die Einzelabfrage
    und verlangte eine vierte Antwort, die `answers` nicht hergibt (`StopIteration`). Test
    war damit rot, bevor `if not _ask_continue(...): return cards` stand."""
    leftover = [_vocabulary_entry("x"), _vocabulary_entry("y"), _vocabulary_entry("z")]
    resolve_block, _calls = _scripted_resolver(
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    matching = [line for line in written if "noch nicht geprüft" in line]
    assert len(matching) == 1
    assert "3 Wörter" in matching[0]


def test_run_triage_blocks_treats_enter_as_no_at_the_continuation_question(
    profile_con: sqlite3.Connection,
) -> None:
    """Enter beendet die Blockschleife ebenso wie „nein" — Aufhören ist die sichere
    Vorgabe (dieselbe Handhabung wie bei der Sammelaktion, Enter = keine). Wie beim
    vorigen Test wird an der Meldung geprüft, nicht an der Aufrufzahl von `resolve_block`
    — seit dem Vorladen (Bauschritt 3/4) läuft ein zweiter Aufruf im Hintergrund an, egal
    wie die Fortsetzungsfrage endet (technik.md §12).

    Verfälschungsprobe: Vertauscht `_ask_continue` die Vorgabe (Enter würde als „ja"
    gelten), verlangt `run_triage_pass` eine vierte Antwort für einen zweiten
    Blockdurchlauf, die `answers` nicht hergibt — `next(answers)` wirft `StopIteration`.
    Test war damit rot, bevor `answer in ("", "n", "nein")` stand."""
    leftover = [_vocabulary_entry("x")]
    resolve_block, _calls = _scripted_resolver(
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    # (Befund B, Durchsicht 5fda1b9): Singular bei genau einem Eintrag — „1 Wort", nicht
    # „1 Wörter". Ein eigener, gezielter Singulartest steht unten
    # (`test_run_triage_blocks_reports_the_unchecked_count_in_the_singular_for_exactly_
    # one_entry`); dieser Test hier bleibt an derselben Meldung, nur mit der berichtigten
    # Grammatik.
    assert any("1 Wort" in line and "noch nicht geprüft" in line for line in written)


def test_run_triage_blocks_asks_the_continuation_question_again_on_invalid_input(
    profile_con: sqlite3.Connection,
) -> None:
    """Regel 13 (dokumentation.md §4): Eine unbekannte Eingabe bei der Fortsetzungsfrage
    verwirft keine Entscheidung stillschweigend als „nein", sondern führt zu einer
    erneuten Frage — dieselbe Handhabung wie `_ask_action`.

    Verfälschungsprobe: Deutet `_ask_continue` eine unbekannte Eingabe stillschweigend als
    „nein" statt erneut zu fragen, endet die Schleife dort mit „1 Wort noch nicht
    geprüft" statt mit dem zweiten, leeren Block bis „Alle Wörter … durchgesehen" —
    `resolve_block` wird seit dem Vorladen (Bauschritt 3/4) ohnehin schon für den
    zweiten Block angestoßen, sobald der erste feststeht, unabhängig vom Ausgang dieser
    Frage; `calls[1] == leftover` bleibt deshalb nur bei tatsächlichem Fortsetzen ein
    verlässlicher Beleg, nicht die reine Aufrufzahl. Test war damit rot, bevor die
    Schleife bei unbekannter Eingabe erneut fragte, statt `False` zurückzugeben."""
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(calls) == 2
    assert calls[1] == leftover
    assert any("Ungültige Eingabe" in line for line in written)
    assert any("durchgesehen" in line for line in written)
    assert not any("noch nicht geprüft" in line for line in written)


def test_run_triage_blocks_does_not_ask_to_continue_after_q(
    profile_con: sqlite3.Connection,
) -> None:
    """Abnahmekriterium 7: `q` in der Einzelabfrage beendet die Blockschleife **ohne**
    Fortsetzungsfrage — der Nutzer hat den Abbruch bereits erklärt. Seit dem Vorladen
    (Bauschritt 3/4, technik.md §12) hat die Schleife den nächsten Block zu diesem
    Zeitpunkt bereits im Hintergrund angestoßen (er entsteht, sobald der aktuelle Block
    feststeht, nicht erst nach einer bejahten Fortsetzungsfrage) — anders als vor jener
    Behebung darf `resolve_block` deshalb durchaus ein zweites Mal aufgerufen worden sein;
    was dieser Test prüft, ist einzig, dass darauf **nicht gewartet** wird.

    Die gemeldete Zahl zählt seit Befund 9 (Durchsicht 1cfb1e4) mehr als `len(current)`:
    `resolution.entries` hat zwei Einträge (word0, word1), die Sammelaktion markiert
    keinen, und `q` fällt sofort bei word0 — beide bleiben unentschieden
    (`triage_pass.unasked == 2`), dazu die eine Wendung aus `leftover`, macht 3.

    Verfälschungsprobe: Fragt `run_triage_blocks` nach einem Abbruch trotzdem weiter
    (fehlende `if triage_pass.aborted`-Prüfung), verlangt sie eine vierte Antwort, die die
    Antwortliste nicht hergibt — `next(answers)` wirft `StopIteration`. Test war damit rot,
    bevor die Prüfung auf `aborted` vor der Fortsetzungsfrage stand. Zählt die Meldung nur
    `len(current)` statt `len(current) + triage_pass.unasked` (der Stand vor Befund 9),
    steht dort „1 Wort" statt „3 Wörter" — dieselbe Verfälschung macht diesen Test
    ebenfalls rot."""
    leftover = [_vocabulary_entry("x")]
    resolve_block, _calls = _scripted_resolver(
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert any("3 Wörter" in line and "noch nicht geprüft" in line for line in written)


def test_run_triage_blocks_reports_unfinished_after_q_in_the_last_block(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund 1 (Durchsicht 1cfb1e4): `q` **im letzten Block** (kein Rest für einen
    weiteren Block) meldete vor dieser Behebung fälschlich „Alle Wörter für dieses
    Kapitel durchgesehen" — die Prüfung auf ein leeres `resolution.remaining` stand vor
    der auf `triage_pass.aborted`, und in diesem Fall sind beide leer/wahr zugleich.
    Reproduziert am echten Fall aus dem Auftragstext: Sherlock Kapitel 2, Block 17 von
    17, `q` beim ersten Eintrag — 10 der 11 Wendungen wurden nie gesehen, aber die
    Meldung sagte „durchgesehen".

    Verfälschungsprobe: Steht `if not current: ...` vor `if triage_pass.aborted: ...`
    (der Stand vor dieser Behebung), liefert dieser Test „Alle Wörter für dieses Kapitel
    durchgesehen." statt der Zusicherung unten — dieser Test war daran rot, siehe
    Bericht."""
    resolve_block, _calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(3), known=0, resolved_known=0, skipped=0, remaining=[]
            )
        ]
    )
    answers = iter(["", "q"])  # keine Sammelaktion, dann sofortiger Abbruch bei word0
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert not any("durchgesehen" in line for line in written)
    matching = [line for line in written if "noch nicht geprüft" in line]
    assert len(matching) == 1
    assert "3 Wörter" in matching[0]


def test_run_triage_blocks_reports_the_unasked_count_in_the_singular_for_exactly_one_entry(
    profile_con: sqlite3.Connection,
) -> None:
    """Befund B (Durchsicht 5fda1b9): dieselbe Grammatikkorrektur wie bei
    `test_run_triage_blocks_treats_enter_as_no_at_the_continuation_question`, hier für den
    Zweig nach `q` (`len(current) + triage_pass.unasked`) statt nach „nein"
    (`len(current)` allein) — beide Zweige rufen `_count_label` auf, aber an
    unterschiedlichen Stellen in `run_triage_blocks`, und nur ein Test je Stelle belegt,
    dass beide tatsächlich korrigiert sind. Ein Kapitel mit genau einem Worteintrag, `q`
    beim ersten und einzigen Eintrag, kein weiterer Block: `unasked == 1`, `current == []`.

    Verfälschungsprobe: Ohne `_count_label` an dieser Stelle steht in `matching[0]`
    „1 Wörter", nicht „1 Wort" — dieser Test war daran rot, siehe Bericht."""
    resolve_block, _calls = _scripted_resolver(
        [
            pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=[]
            )
        ]
    )
    answers = iter(["", "q"])  # keine Sammelaktion, dann sofortiger Abbruch bei word0
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    matching = [line for line in written if "noch nicht geprüft" in line]
    assert len(matching) == 1
    assert "1 Wort " in matching[0]
    assert "1 Wörter" not in matching[0]


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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
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
        resolve_visible_block=resolve_block,
        resolve_silent_block=lambda block, _cancelled: resolve_block(block),
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert len(calls) == 2
    # Bauschritt 2/2 der Konsolenausgabe (02.09.2026): Der Blockkopf trägt seither die
    # Einrückung und keine Bindestrich-Umrahmung mehr ("--...--") — geprüft wird deshalb
    # am Wortlaut, nicht an der alten Umrahmung.
    headings = [line.strip() for line in written if line.strip().startswith("Wörter")]
    assert headings == ["Wörter: 1", "Wörter (Block 2): 1"]


def test_run_triage_blocks_prefetches_the_next_block_before_the_continuation_question(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, „Vorladen: der nächste Block entsteht, während der Nutzer
    entscheidet": Der nächste Block wird angestoßen, sobald der aktuelle feststeht — nicht
    erst, nachdem die Fortsetzungsfrage mit „ja" beantwortet ist. Geprüft wird die
    **Reihenfolge** der Aufrufe, nicht nur, dass beide stattfinden: `read_line` wartet bei
    der Fortsetzungsfrage auf `prefetch_started` (mit großzügigem Sicherheitsabstand statt
    `sleep`, dokumentation.md §5) — unter der richtigen Umsetzung ist das Ereignis dort
    längst gesetzt, weil der Aufruf lange vor der Sammel- und Einzelabfrage steht.

    Verfälschungsprobe: Ruft `run_triage_blocks` `resolve_silent_block` erst nach einem
    bejahten `_ask_continue` auf (die triviale Umsetzung ohne echtes Vorladen), ist
    `prefetch_started` zum Zeitpunkt der Fortsetzungsfrage noch nicht gesetzt — der
    `wait(timeout=2)` läuft ins Leere, `assert` schlägt fehl. Test war damit rot, bevor der
    Vorladeaufruf vor `run_triage_pass` stand."""
    leftover = [_vocabulary_entry("x")]
    prefetch_started = threading.Event()

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        return pipeline.TriageResolution(
            entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], _cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        prefetch_started.set()
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    def read_line(prompt: str) -> str:
        if "weitermachen" in prompt:
            assert prefetch_started.wait(timeout=2), (
                "Vorladen wurde nicht vor der Fortsetzungsfrage angestoßen."
            )
            return "j"
        if "Sammelaktion" in prompt:
            return ""
        return "s"

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_visible_block=resolve_visible,
        resolve_silent_block=resolve_silent,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=read_line,
        write_line=_no_op_write,
    )

    assert cards == []


def test_run_triage_blocks_does_not_wait_for_a_still_running_prefetch_after_declining_to_continue(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, Festlegung 4: Ein noch laufender Vorladeblock darf das Ende nicht
    aufhalten — „nein" auf die Fortsetzungsfrage beendet die Blockschleife, ohne auf
    `resolve_silent_block` zu warten.

    Prüft seit Befund 4 (Durchsicht 1cfb1e4) zusätzlich, dass die Schleife den Block
    dabei tatsächlich **abbestellt**: Sie muss das `cancelled`-Ereignis setzen, das sie
    `resolve_silent` als zweites Argument übergeben hat — sonst liefe der Vorladeblock im
    Hintergrund einfach weiter und verbrauchte Modellaufrufe für ein verworfenes Ergebnis
    (gemessen: ein erster Wendungsblock brauchte dadurch 7,39 s statt 3,85 s). `stuck.
    wait(timeout=30)` statt eines unbegrenzten Warten (Befund 3, Durchsicht 1cfb1e4): Eine
    Verfälschung, die trotzdem wartet, soll rot werden, nicht hängen.

    Verfälschungsprobe: Ruft die Schleife nach „nein" trotzdem `prefetch.join()` auf
    (statt direkt zurückzukehren), hängt dieser Test 30 s lang, bis `stuck.wait` selbst
    aufgibt und `AssertionError("darf nicht erreicht werden")` wirft — er war damit rot
    (nicht hängend), bevor der Rückweg bei „nein" ohne diesen Aufruf auskam. Fehlt
    `prefetch.cancel()` in diesem Rückweg (der Stand vor Befund 4), bleibt `cancelled`
    ungesetzt — die Zusicherung am Ende schlägt fehl, ohne dass der Test dafür warten
    muss."""
    leftover = [_vocabulary_entry("x")]
    stuck = threading.Event()
    received_cancelled: list[threading.Event] = []

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        return pipeline.TriageResolution(
            entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        received_cancelled.append(cancelled)
        stuck.wait(timeout=30)  # kehrt in diesem Test absichtlich nie regulär zurück
        raise AssertionError("darf nicht erreicht werden")

    answers = iter(["", "s", "n"])

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_visible_block=resolve_visible,
        resolve_silent_block=resolve_silent,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert cards == []
    assert received_cancelled, "resolve_silent wurde nie mit einem Abbruchsignal aufgerufen."
    assert received_cancelled[0].is_set(), (
        "Befund 4 (Durchsicht 1cfb1e4): der Vorladeblock wurde nach der Ablehnung nicht abbestellt."
    )


def test_run_triage_blocks_does_not_wait_for_a_still_running_prefetch_after_q(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, Festlegung 4: derselbe Rückweg wie bei „nein", hier für den Abbruch
    mit `q` in der Einzelabfrage — auch er darf nicht auf einen noch laufenden
    Vorladeblock warten.

    Prüft seit Befund 4 (Durchsicht 1cfb1e4) zusätzlich, dass `q` den Block ebenso
    **abbestellt** wie „nein" (siehe die Schwesterprüfung oben). `wait(timeout=30)` statt
    eines unbegrenzten Warten (Befund 3, Durchsicht 1cfb1e4), damit eine Verfälschung rot
    wird statt zu hängen.

    Verfälschungsprobe: Wartet die Schleife nach `q` trotzdem auf den Vorladefaden, hängt
    dieser Test 30 s lang, bis das Warten selbst aufgibt und `AssertionError` wirft — er
    war damit rot (nicht hängend), bevor der Rückweg bei `q` ohne diesen Aufruf auskam.
    Fehlt `prefetch.cancel()` (der Stand vor Befund 4), bleibt `cancelled` ungesetzt — die
    Zusicherung am Ende schlägt sofort fehl."""
    leftover = [_vocabulary_entry("x")]
    received_cancelled: list[threading.Event] = []

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        return pipeline.TriageResolution(
            entries=_entries(2), known=0, resolved_known=0, skipped=0, remaining=leftover
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        received_cancelled.append(cancelled)
        cancelled.wait(timeout=30)  # kehrt in diesem Test absichtlich nie regulär zurück
        raise AssertionError("darf nicht erreicht werden")

    answers = iter(["", "q"])  # keine Sammelaktion, dann sofortiger Abbruch bei word0
    written: list[str] = []

    cards = interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a"), _vocabulary_entry("b")],
        resolve_visible_block=resolve_visible,
        resolve_silent_block=resolve_silent,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert cards == []
    assert not any("weitermachen" in line for line in written)
    assert received_cancelled, "resolve_silent wurde nie mit einem Abbruchsignal aufgerufen."
    assert received_cancelled[0].is_set(), (
        "Befund 4 (Durchsicht 1cfb1e4): der Vorladeblock wurde nach `q` nicht abbestellt."
    )


def test_run_triage_blocks_surfaces_a_prefetch_failure_when_the_block_is_awaited(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, Festlegung 2: Bricht der Vorlade-Rückruf ab (etwa weil der
    Modellserver wegbricht), erreicht der Fehler den Nutzer sichtbar, sobald auf den Block
    gewartet wird — nicht als leerer Block, der wie „Kapitel fertig" aussähe (Regel 13,
    dokumentation.md §4).

    Verfälschungsprobe: Fängt `_BlockPrefetch` den Fehler und liefert stattdessen eine
    leere `TriageResolution`, meldet `run_triage_blocks` fälschlich „durchgesehen" statt
    die Ausnahme durchzureichen — kein `pytest.raises` schlägt an, der Test war damit rot,
    bevor der Fehler im Hintergrundfaden festgehalten und bei `join` erneut geworfen
    wurde."""
    leftover = [_vocabulary_entry("x")]

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        return pipeline.TriageResolution(
            entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], _cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        raise ValueError("Modellserver antwortet nicht mehr.")

    answers = iter(["", "s", "j"])

    with pytest.raises(ValueError, match="Modellserver antwortet nicht mehr\\."):
        interaction.run_triage_blocks(
            con=profile_con,
            book=_BOOK,
            chapter_number=1,
            entries=[_vocabulary_entry("a")],
            resolve_visible_block=resolve_visible,
            resolve_silent_block=resolve_silent,
            label="Wörter",
            card_direction=CardDirection.EN_DE,
            read_line=lambda _prompt: next(answers),
            write_line=_no_op_write,
        )


def test_run_triage_blocks_uses_the_silent_resolver_only_for_blocks_after_the_first(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, Festlegung 3: Nur der allererste Block trägt die Fortschrittszeile
    (`resolve_visible_block`), jeder vorgeladene Folgeblock läuft still
    (`resolve_silent_block`) — unabhängig davon, wie viele Blöcke folgen. Prüft zugleich,
    dass jeder vorgeladene Block genau `resolution.remaining` des vorigen als Eingabe
    bekommt (technik.md §12).

    Verfälschungsprobe: Verwendet die Schleife für den zweiten oder dritten Block
    versehentlich wieder `resolve_visible_block` (etwa weil beide Rückrufe vertauscht
    wären), zählt `visible_calls` mehr als einmal, oder `silent_calls` weicht von
    `[leftover_1, leftover_2]` ab — der Test war damit rot, bevor `resolve_silent_block`
    für jeden Folgeblock stand."""
    leftover_1 = [_vocabulary_entry("x")]
    leftover_2 = [_vocabulary_entry("y")]
    visible_calls: list[list[pipeline.VocabularyEntry]] = []
    silent_calls: list[list[pipeline.VocabularyEntry]] = []

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        visible_calls.append(list(block))
        return pipeline.TriageResolution(
            entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover_1
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], _cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        silent_calls.append(list(block))
        if list(block) == leftover_1:
            return pipeline.TriageResolution(
                entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover_2
            )
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    answers = iter(["", "s", "j", "", "s", "j"])
    entries = [_vocabulary_entry("a")]

    interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=entries,
        resolve_visible_block=resolve_visible,
        resolve_silent_block=resolve_silent,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=_no_op_write,
    )

    assert visible_calls == [entries]
    assert silent_calls == [leftover_1, leftover_2]


def test_run_triage_blocks_announces_when_the_prefetched_block_is_not_ready_yet(
    profile_con: sqlite3.Connection,
) -> None:
    """technik.md §12, Festlegung 3: Ist der vorgeladene Block bei der Fortsetzungsfrage
    noch nicht fertig, sagt eine Zeile das, bevor auf ihn gewartet wird — sonst säße der
    Nutzer vor einer stummen Eingabeaufforderung.

    `resolve_silent` bleibt blockiert, bis genau diese Zeile geschrieben wird
    (`release.set()` in `write_line`) — `is_done()` kann zu diesem Zeitpunkt deshalb nicht
    wahr sein, ohne dass sich der Test auf einen Wettlauf um Zeit verlässt.

    Verfälschungsprobe: Wartet die Schleife stattdessen sofort auf `prefetch.join()`, ohne
    vorher zu prüfen und zu melden, wartet dieser Test die vollen 30 s von
    `release.wait(timeout=30)` ab und wird dann rot, statt zu hängen (Befund 3, Durchsicht
    1cfb1e4) — er war daran rot, bevor die Meldung vor dem Warten stand."""
    leftover = [_vocabulary_entry("x")]
    release = threading.Event()

    def resolve_visible(block: Sequence[pipeline.VocabularyEntry]) -> pipeline.TriageResolution:
        return pipeline.TriageResolution(
            entries=_entries(1), known=0, resolved_known=0, skipped=0, remaining=leftover
        )

    def resolve_silent(
        block: Sequence[pipeline.VocabularyEntry], _cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        release.wait(timeout=30)
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    written: list[str] = []

    def write_line(text: str) -> None:
        written.append(text)
        if "wird noch aufgelöst" in text:
            release.set()

    answers = iter(["", "s", "j"])

    interaction.run_triage_blocks(
        con=profile_con,
        book=_BOOK,
        chapter_number=1,
        entries=[_vocabulary_entry("a")],
        resolve_visible_block=resolve_visible,
        resolve_silent_block=resolve_silent,
        label="Wörter",
        card_direction=CardDirection.EN_DE,
        read_line=lambda _prompt: next(answers),
        write_line=write_line,
    )

    assert any("wird noch aufgelöst" in line for line in written)


def test_block_prefetch_join_lets_a_keyboard_interrupt_through_promptly() -> None:
    """Befund 5 (Durchsicht 1cfb1e4): `_BlockPrefetch.join` darf ein `KeyboardInterrupt`
    (Strg-C) nicht bis zum Ende des Hintergrundfadens verschlucken — ein einzelner
    `Thread.join()` ohne Frist tut genau das, weil CPython ein anstehendes Signal erst
    verarbeitet, wenn ein blockierender Aufruf zum Python-Bytecode zurückkehrt (gemessen:
    15,0 s statt 1,5 s bei einem Kontrolllauf mit `time.sleep(15)`).

    Simuliert mit `_thread.interrupt_main()` aus einem Kontrollfaden nach 0,3 s, während
    der Vorladeblock selbst 5 s „braucht" — `join()` muss binnen kurzer Zeit mit
    `KeyboardInterrupt` abbrechen, nicht erst nach den vollen 5 s.

    Verfälschungsprobe: Ersetzt man die Schleife durch ein einzelnes `self._thread.join()`
    ohne Frist (der Stand vor dieser Behebung), kommt `KeyboardInterrupt` erst nach den
    vollen 5 s an — `elapsed < 2.0` schlägt dann fehl, aber erst nach den 5 s: rot, nicht
    hängend, weil die Attrappe selbst befristet ist. Test war daran rot, siehe Bericht."""
    import _thread
    import time

    def _resolve(
        _block: Sequence[pipeline.VocabularyEntry], _cancelled: threading.Event
    ) -> pipeline.TriageResolution:
        time.sleep(5)
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    prefetch = interaction._BlockPrefetch(_resolve, [_vocabulary_entry("a")])
    prefetch.start()

    def _send_interrupt() -> None:
        time.sleep(0.3)
        _thread.interrupt_main()

    interrupter = threading.Thread(target=_send_interrupt, daemon=True)
    interrupter.start()

    started = time.monotonic()
    with pytest.raises(KeyboardInterrupt):
        prefetch.join()
    elapsed = time.monotonic() - started

    assert elapsed < 2.0, f"join() hat Strg-C erst nach {elapsed:.1f} s durchgelassen."
