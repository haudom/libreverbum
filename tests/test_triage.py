"""Prüft `libreverbum/triage.py` — bauplan.md T10, Häufigkeitssortierung, Wortobergrenze,
Sammelaktion."""

from __future__ import annotations

import pytest

from libreverbum import triage
from libreverbum.entities import Book, Lemma, Occurrence

_BOOK = Book(title="Testbuch", author="Autorin")


def _occurrence(text: str, pos: str, frequency: int, *, chapter_number: int = 1) -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=chapter_number,
        lemma=Lemma(text=text, pos=pos),
        word_form=text,
        example_sentence=f"A sentence with {text} in it.",
        frequency=frequency,
        proper_noun_frequency=0,
    )


def test_sort_by_frequency_orders_descending() -> None:
    """bauplan.md T10: Häufigkeitssortierung — häufigste zuerst (konzept.md §4, „nach
    Häufigkeit sortiert präsentiert, häufigste zuerst")."""
    rare = _occurrence("whale", "NOUN", 2)
    common = _occurrence("the", "DET", 50)
    middle = _occurrence("run", "VERB", 10)

    result = triage.sort_by_frequency([rare, common, middle])

    assert result == [common, middle, rare]


def test_sort_by_frequency_breaks_ties_deterministically_by_lemma() -> None:
    """Gleichstandsfall: Bei gleicher Häufigkeit entscheidet `(lemma.text, lemma.pos)` —
    das Ergebnis hängt nicht an der Eingabereihenfolge (dokumentation.md §5, „Ein Test gilt
    erst als Test, wenn er einmal rot war")."""
    b = _occurrence("bank", "NOUN", 5)
    a = _occurrence("apple", "NOUN", 5)
    c = _occurrence("cup", "NOUN", 5)

    forward = triage.sort_by_frequency([b, a, c])
    backward = triage.sort_by_frequency([c, a, b])

    assert forward == backward == [a, b, c]


def test_bulk_mark_marks_all_more_frequent_words_not_only_the_selected_one() -> None:
    """bauplan.md T10, Prüfung: Die Sammelaktion markiert alle häufigeren Wörter mit, nicht
    nur das eine, auf das der Nutzer geklickt hat."""
    most_frequent = _occurrence("the", "DET", 80)
    selected = _occurrence("run", "VERB", 20)
    less_frequent = _occurrence("whale", "NOUN", 2)

    marked = triage.bulk_mark([most_frequent, selected, less_frequent], selected)

    assert set(marked) == {most_frequent, selected}
    assert less_frequent not in marked


def test_bulk_mark_includes_a_tied_word_preceding_the_selected_one_in_the_display_order() -> None:
    """Gleichstandsfall: Ein Wort mit derselben Häufigkeit wie das gewählte, das in der
    Anzeige (`sort_by_frequency`) davorsteht, wird mitgebucht."""
    selected = _occurrence("cup", "NOUN", 5)
    tied_before = _occurrence("apple", "NOUN", 5)

    marked = triage.bulk_mark([selected, tied_before], selected)

    assert set(marked) == {selected, tied_before}


def test_bulk_mark_excludes_a_tied_word_following_the_selected_one_in_the_display_order() -> None:
    """Befund 1 (Review T10): Ein Wort mit derselben Häufigkeit wie das gewählte, das in der
    Anzeige (`sort_by_frequency`) dahinter steht, wird **nicht** mitgebucht — sonst bucht
    ein Klick in einem Gleichstandsblock mehr, als der Nutzer gesehen hat."""
    selected = _occurrence("apple", "NOUN", 5)
    tied_after = _occurrence("cup", "NOUN", 5)

    marked = triage.bulk_mark([selected, tied_after], selected)

    assert set(marked) == {selected}
    assert tied_after not in marked


def test_bulk_mark_stops_at_the_position_of_the_selected_word_within_a_tied_block() -> None:
    """Befund 1 (Review T10), das Beispiel aus dem Bericht: Ein Klick auf ein Wort mitten in
    einem Häufigkeit-1-Block bucht nur die Wörter bis zu dieser Position in der Anzeige, nicht
    den ganzen Gleichstandsblock."""
    the = _occurrence("the", "DET", 40)
    man = _occurrence("man", "NOUN", 12)
    agony = _occurrence("agony", "NOUN", 1)
    brooch = _occurrence("brooch", "NOUN", 1)
    cipher = _occurrence("cipher", "NOUN", 1)
    dowry = _occurrence("dowry", "NOUN", 1)
    ergot = _occurrence("ergot", "NOUN", 1)

    # absichtlich nicht in Häufigkeitsreihenfolge übergeben, siehe Befund 3
    marked = triage.bulk_mark([ergot, cipher, dowry, brooch, agony, man, the], brooch)

    assert set(marked) == {the, man, agony, brooch}
    assert cipher not in marked
    assert dowry not in marked
    assert ergot not in marked


def test_bulk_mark_rejects_a_word_outside_the_given_list() -> None:
    """Regel 13 (dokumentation.md §4): Ein `selected`, das nicht Teil der übergebenen
    Wortliste ist, ist ein sichtbarer Fehlschlag statt einer stillschweigenden Markierung."""
    known_word = _occurrence("run", "VERB", 20)
    foreign_word = _occurrence("whale", "NOUN", 2)

    with pytest.raises(ValueError):
        triage.bulk_mark([known_word], foreign_word)


def test_defer_beyond_word_limit_defers_the_rest() -> None:
    """bauplan.md T10, Prüfung: Die Wortobergrenze stellt den Rest zurück."""
    most_frequent = _occurrence("the", "DET", 80)
    middle = _occurrence("run", "VERB", 20)
    least_frequent = _occurrence("whale", "NOUN", 2)

    # (Befund 3, Review T10): absichtlich nicht in Häufigkeitsreihenfolge übergeben — sonst
    # bliebe eine Verfälschung, die die Sortierung in defer_beyond_word_limit aushängt,
    # unbemerkt grün.
    deferred = triage.defer_beyond_word_limit([middle, least_frequent, most_frequent], 2)

    assert deferred == [least_frequent]


def test_defer_beyond_word_limit_keeps_the_top_words_untouched() -> None:
    """Ergänzung zur vorigen Prüfung: Die `word_limit` häufigsten Wörter erscheinen in
    keinem zurückgestellten Ergebnis."""
    most_frequent = _occurrence("the", "DET", 80)
    middle = _occurrence("run", "VERB", 20)
    least_frequent = _occurrence("whale", "NOUN", 2)

    deferred = triage.defer_beyond_word_limit([least_frequent, most_frequent, middle], 2)

    assert most_frequent not in deferred
    assert middle not in deferred


def test_defer_beyond_word_limit_rejects_occurrences_from_different_chapters() -> None:
    """Befund 4 (Review T10): Die Obergrenze gilt „pro Kapitel" (konzept.md §4) — eine
    Liste mit Vorkommen aus mehreren Kapiteln ist ein sichtbarer Fehlschlag (Regel 13),
    keine kapitelübergreifende Obergrenze."""
    chapter_one = _occurrence("run", "VERB", 20, chapter_number=1)
    chapter_two = _occurrence("whale", "NOUN", 2, chapter_number=2)

    with pytest.raises(ValueError):
        triage.defer_beyond_word_limit([chapter_one, chapter_two], 1)


def test_negative_word_limit_is_a_visible_failure() -> None:
    """Regel 13 (dokumentation.md §4): Eine negative Wortobergrenze ist ein
    widersprüchliches Argument und damit ein sichtbarer Fehlschlag, keine leere Rückgabe."""
    with pytest.raises(ValueError):
        triage.defer_beyond_word_limit([_occurrence("run", "VERB", 5)], -1)
