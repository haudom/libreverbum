"""Prüft `libreverbum/extraction.py` (bauplan.md T3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from libreverbum.entities import Book, Chapter, Occurrence
from libreverbum.extraction import extract_vocabulary, load_nlp

if TYPE_CHECKING:
    from spacy.language import Language


@pytest.fixture(scope="module")
def nlp() -> Language:
    """Lädt das spaCy-Modell einmal für alle Tests dieser Datei — das Laden kostet rund
    eine Sekunde (technik.md §5) und soll nicht je Test anfallen."""
    return load_nlp()


@pytest.fixture(scope="module")
def nlp_without_lemmatizer() -> Language:
    """spaCy-Pipeline ohne Lemmatisierer — Testvorrichtung für Regel 2 und Regel 13
    (Befund 2, Review Runde 1): Eine kaputte Pipeline darf nicht still zu
    Oberflächenformen als Grundform führen."""
    import spacy

    return spacy.load("en_core_web_md", exclude=["lemmatizer"])


def make_chapter(text: str, *, number: int = 1) -> Chapter:
    book = Book(title="Testbuch", author="Test Autorin")
    return Chapter(book=book, number=number, title="Testkapitel", text=text)


def find(occurrences: list[Occurrence], lemma_text: str, pos: str | None = None) -> Occurrence:
    """Sucht ein `Occurrence` nach Grundform, optional nach Wortart."""
    matches = [
        o for o in occurrences if o.lemma.text == lemma_text and (pos is None or o.lemma.pos == pos)
    ]
    assert len(matches) == 1, (
        f"{lemma_text!r} (pos={pos}) genau einmal erwartet, {len(matches)}-mal gefunden"
    )
    return matches[0]


def has_lemma(occurrences: list[Occurrence], lemma_text: str) -> bool:
    return any(o.lemma.text == lemma_text for o in occurrences)


def has_word_form(occurrences: list[Occurrence], word_form: str) -> bool:
    return any(o.word_form == word_form for o in occurrences)


# --------------------------------------------------------------------------- Regel 2


def test_rule_2_saw_as_verb_becomes_the_lemma_see_not_the_tool(nlp: Language) -> None:
    """Regel 2 (dokumentation.md §4): `He saw her yesterday.` ergibt die Grundform
    *see*, nicht *saw* — Lemmatisierung vor dem Nachschlagen (technik.md, „Warum die
    Reihenfolge zwingend ist")."""
    chapter = make_chapter("He saw her yesterday.")
    occurrences = extract_vocabulary(chapter, nlp)

    see = find(occurrences, "see", "VERB")
    assert see.frequency == 1
    assert see.word_form == "saw"
    assert not has_lemma(occurrences, "saw")


def test_rule_2_saw_as_noun_stays_the_tool(nlp: Language) -> None:
    """Gegenprobe zu Regel 2: Als Werkzeug bleibt `saw` bei der Grundform *saw*, weil
    die Wortart hier NOUN und nicht VERB ist — die Wortart entscheidet, nicht die
    Wortform allein."""
    chapter = make_chapter("He cut the plank in half with a rusty saw.")
    occurrences = extract_vocabulary(chapter, nlp)

    saw = find(occurrences, "saw", "NOUN")
    assert saw.frequency == 1
    assert not has_lemma(occurrences, "see")


def test_broken_pipeline_without_lemmatizer_aborts_instead_of_silently_using_surface_forms(
    nlp_without_lemmatizer: Language,
) -> None:
    """Regel 2 und Regel 13 (dokumentation.md §4, Befund 2 Review Runde 1): Fehlt der
    Lemmatisierer, bricht die Extraktion sichtbar ab, statt `saw` still als eigene
    Grundform durchzureichen — der saw-Fall darf nicht leise scheitern."""
    chapter = make_chapter("He saw her yesterday.")

    with pytest.raises(ValueError):
        extract_vocabulary(chapter, nlp_without_lemmatizer)


# -------------------------------------------------------------------------- Regel 12


def test_rule_12_red_stays_a_learning_word_despite_appearing_in_a_proper_name(
    nlp: Language,
) -> None:
    """Regel 12: Der Eigennamenfilter wirkt auf das Vorkommen, nie auf die Grundform —
    `red` bleibt Lernvokabel, obwohl es auch in einem Namen steht (dokumentation.md §5)."""
    chapter = make_chapter(
        "Mr. Red walked down the street with his dog. She painted the old fence a bright red."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    red = find(occurrences, "red")
    assert red.frequency == 2
    assert red.proper_noun_frequency == 1
    assert red.proper_noun_frequency < red.frequency, "red müsste als Lernvokabel gelten"


def test_rule_12_a_name_that_never_occurs_as_an_ordinary_word_is_not_extracted(
    nlp: Language,
) -> None:
    """Regel 12 / Abnahmekriterium 2: Ein Wort, das ausschließlich als Eigenname
    vorkommt, wird gar nicht erst als Grundform geliefert — keine Figurennamen als
    Lernvokabeln."""
    chapter = make_chapter("Sherlock arrived at noon.")
    occurrences = extract_vocabulary(chapter, nlp)

    # (Befund 4, Review Runde 1): Grundformen werden kleingeschrieben (Regel 12), eine
    # großgeschriebene Grundform ist unerreichbar — das prüft stattdessen word_form, das
    # die ursprüngliche Schreibung behält.
    assert not has_lemma(occurrences, "sherlock")
    assert not has_word_form(occurrences, "Sherlock")


# ------------------------------------------------------------- Inhaltswortfilter


def test_auxiliary_modal_and_gerund_forms_are_not_extracted(nlp: Language) -> None:
    """technik.md §5, offener Punkt: `could` und `having` (als Hilfsverb) werden vor
    dem Nachschlagen ausgesteuert, statt als Wörterbuchlücke zu erscheinen — beide sind
    Funktionswörter, die nie Lernvokabeln werden."""
    chapter = make_chapter(
        "He could not believe his eyes. Having finished the letter, she sealed the envelope."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    assert not has_lemma(occurrences, "could")
    assert not has_lemma(occurrences, "having")
    # Der Hauptsatz bleibt regulär vorhanden — nur die Hilfsverbform ist ausgesteuert.
    assert has_lemma(occurrences, "believe")
    assert has_lemma(occurrences, "finish")


def test_having_as_a_main_verb_is_still_extracted(nlp: Language) -> None:
    """Gegenprobe: `having` in Hauptverbstellung („having a hard time") trägt bei
    spaCy die Wortart VERB statt AUX und bleibt deshalb erhalten — der Filter trifft
    die Wortart, nicht die Wortform."""
    chapter = make_chapter("She has been having a hard time lately.")
    occurrences = extract_vocabulary(chapter, nlp)

    have = find(occurrences, "have", "VERB")
    assert have.word_form == "having"


def test_only_content_words_are_extracted_function_words_are_filtered_out(nlp: Language) -> None:
    """Nur Inhaltswörter kommen in die Wortliste (Review Runde 2, erlaubte statt
    Sperrliste): Artikel, Pronomen, Präpositionen und Hilfsverben fehlen, obwohl sie im
    Satz stehen — die Inhaltswörter desselben Satzes stehen dagegen alle drin. Ein Test,
    der nur die Abwesenheit prüfte, wäre auch bei einer leeren Liste grün."""
    chapter = make_chapter("The dog was quickly chased by his loyal friend.")
    occurrences = extract_vocabulary(chapter, nlp)

    assert not has_lemma(occurrences, "the")
    assert not has_lemma(occurrences, "be")
    assert not has_lemma(occurrences, "by")
    assert not has_lemma(occurrences, "his")

    assert has_lemma(occurrences, "dog")
    assert has_lemma(occurrences, "quickly")
    assert has_lemma(occurrences, "chase")
    assert has_lemma(occurrences, "loyal")
    assert has_lemma(occurrences, "friend")


# ---------------------------------------------------- Wortartauflösung und Belegsatz


def test_pos_resolution_more_frequent_pos_wins(nlp: Language) -> None:
    """Moduldocstring, Abschnitt „Regeln": Mischt eine Grundform mehrere Wortarten
    unter ihren nicht-eigennamigen Vorkommen, gewinnt die häufigere — `watch` tritt
    zweimal als NOUN und nur einmal als VERB auf."""
    chapter = make_chapter(
        "She bought a new watch. He wore his watch every day. They needed to watch the news."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "NOUN")
    assert watch.word_form == "watch"
    assert watch.example_sentence == "She bought a new watch."


def test_pos_resolution_tie_is_broken_by_first_seen_pos(nlp: Language) -> None:
    """Moduldocstring, Abschnitt „Regeln", Gleichstand: je ein VERB- und ein
    NOUN-Vorkommen von `watch` — die zuerst gesehene Wortart gewinnt, hier VERB."""
    chapter = make_chapter("They wanted to watch the game. He checked his watch.")
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "VERB")
    assert watch.word_form == "watch"
    assert watch.example_sentence == "They wanted to watch the game."


def test_representative_word_form_and_sentence_match_the_chosen_pos(nlp: Language) -> None:
    """Befund 1 (Review Runde 1): Belegsatz und Wortform gehören zur gewählten
    Wortart — bei `watch` gewinnt VERB (zwei von drei Vorkommen), Wortform und
    Belegsatz stammen deshalb vom ersten VERB-Vorkommen, nicht vom ersten Vorkommen
    überhaupt."""
    chapter = make_chapter(
        "He checked his watch. Then he watched the door. Later he watched the clock."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "VERB")
    assert watch.word_form == "watched"
    assert watch.example_sentence == "Then he watched the door."


# ---------------------------------------------------------- Häufigkeit und Belegsatz


def test_inflected_forms_are_merged_into_one_entry_with_combined_frequency(nlp: Language) -> None:
    """Abnahmekriterium 2: Beugungsformen sind in der Wortliste zusammengefasst —
    `running`, `runs` und `ran` ergeben eine Grundform *run* mit Häufigkeit 3."""
    chapter = make_chapter(
        "She was running late. He runs every morning. They ran together yesterday."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    run = find(occurrences, "run", "VERB")
    assert run.frequency == 3
    assert run.word_form == "running"
    assert run.example_sentence == "She was running late."


def test_frequency_and_example_sentence_are_scoped_to_the_given_chapter(nlp: Language) -> None:
    """Häufigkeit und Belegsatz gehören zum übergebenen Kapitel — `book` und
    `chapter_number` auf dem `Occurrence` stammen aus dem `Chapter`-Argument."""
    chapter = make_chapter("The dog barked twice. The dog ran across the street.", number=3)
    occurrences = extract_vocabulary(chapter, nlp)

    dog = find(occurrences, "dog", "NOUN")
    assert dog.frequency == 2
    assert dog.book == chapter.book
    assert dog.chapter_number == 3
    assert dog.example_sentence == "The dog barked twice."


# ------------------------------------------------------------------- Abnahmekriterium 2


def test_acceptance_2_inflections_merged_and_no_proper_names_as_learning_words(
    nlp: Language,
) -> None:
    """Abnahmekriterium 2: Für ein mittleres Kapitel entsteht eine Wortliste, in der
    Beugungsformen zusammengefasst sind und keine Figurennamen als Lernvokabeln
    auftauchen."""
    chapter = make_chapter(
        "Sherlock walked through London. "
        "He was walking for an hour before he finally stopped walking."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    walk = find(occurrences, "walk", "VERB")
    assert walk.frequency == 3

    # (Befund 4, Review Runde 1): siehe Begründung bei Regel 12 oben.
    assert not has_lemma(occurrences, "sherlock")
    assert not has_lemma(occurrences, "london")
    assert not has_word_form(occurrences, "Sherlock")
    assert not has_word_form(occurrences, "London")
