"""Prüft `libreverbum/translation.py` — bauplan.md T11, Bedeutungsauswahl aus der
Auswahlliste des Wörterbuchs über die OpenAI-kompatible Schnittstelle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from libreverbum import translation
from libreverbum.entities import Book, Lemma, Occurrence, Sense

# Nur für die statische Typprüfung, siehe tests/test_fixtures.py für die Begründung.
if TYPE_CHECKING:
    from conftest import ModelServerDouble

_BOOK = Book(title="Testbuch", author="Autorin")
_BANK_LEMMA = Lemma(text="bank", pos="NOUN")

# Zwei Bedeutungen von bank, wie in tests/conftest.py, ModelServerDouble-Docstring und
# technik.md §2 vorgeführt — echte Wörterbuchzeilen, nicht erfunden.
_INSTITUTION = Sense(
    lemma=_BANK_LEMMA,
    wikdict_sense="institution",
    wikdict_trans_list="Bank",
    wikdict_lexentry="eng/bank__Noun__1",
)
_RIVERBANK = Sense(
    lemma=_BANK_LEMMA,
    wikdict_sense="edge of river or lake",
    wikdict_trans_list="Ufer",
    wikdict_lexentry="eng/bank__Noun__2",
)
_BANK_CANDIDATES = [_INSTITUTION, _RIVERBANK]


def _occurrence(
    *,
    word_form: str = "bank",
    example_sentence: str = "She deposited the cheque at the bank on Monday morning.",
    lemma: Lemma = _BANK_LEMMA,
) -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=lemma,
        word_form=word_form,
        example_sentence=example_sentence,
        frequency=1,
        proper_noun_frequency=0,
    )


def test_rule_7_reasoning_effort_none_is_sent_with_every_model_call(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 7 (dokumentation.md §4): Bei jedem Modellaufruf reasoning_effort: "none"."""
    model_server_double.choice = 1

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    assert model_server_double.requests[-1]["reasoning_effort"] == "none"


def test_rule_11_the_answer_is_always_an_entry_of_the_supplied_list(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 11 (dokumentation.md §4): Das Modell wählt aus der Liste, es erzeugt nie
    frei — das Ergebnis ist identisch mit dem gewählten übergebenen Kandidaten
    (`entities.Sense`: Identität über lemma, wikdict_lexentry, wikdict_sense,
    wikdict_trans_list)."""
    model_server_double.choice = 2  # zweiter Kandidat: die Uferbedeutung

    result = translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    assert result == _RIVERBANK
    assert result.translation == "Ufer"
    assert result.uncertain is False


def test_empty_candidate_list_becomes_uncertain_without_a_model_call(
    model_server_double: ModelServerDouble,
) -> None:
    """bauplan.md T11, Vorgabe zur Entscheidung „leere Auswahlliste": Eine leere
    Auswahlliste führt nicht zu einem Modellaufruf, sondern unmittelbar zu uncertain
    (Regel 11: „Kandidaten ohne Wörterbucheintrag werden uncertain markiert")."""
    result = translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=[],
    )

    assert result.uncertain is True
    assert result.translation is None
    assert model_server_double.requests == []


def test_no_match_answer_marks_uncertain_but_is_not_a_failure(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, offener Punkt „keine passt": Wählt das Modell die Ausweichantwort
    (den regulären Listeneintrag N+1), ist das kein Fehlschlag — Ergebnis: uncertain
    gesetzt, translation bleibt None (der `saw`-Fall meldet sich damit, statt still eine
    falsche Bedeutung zu wählen)."""
    model_server_double.behavior = "no_match"
    model_server_double.choice = 3  # N=2 echte Bedeutungen, „keine passt" auf Platz N+1

    result = translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    assert result.uncertain is True
    assert result.translation is None


def test_rule_13_http_error_is_a_visible_failure(model_server_double: ModelServerDouble) -> None:
    """Regel 13 (dokumentation.md §4): kein except, das nur protokolliert und
    weiterläuft — ein HTTP-Fehlschlag des Modellservers bricht sichtbar ab, statt als
    uncertain-Eintrag mit einer echten Modell-Unsicherheit zu verschmelzen."""
    model_server_double.behavior = "http_error"

    with pytest.raises(ValueError, match="Fehler 500"):
        translation.choose_sense(
            url=model_server_double.url,
            model_name=model_server_double.model_name,
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_malformed_response_is_a_visible_failure(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 13: eine Antwort, die nicht dem erwarteten JSON-Schema entspricht, bricht
    sichtbar ab, statt als stille Zahl durchzurutschen."""
    model_server_double.behavior = "malformed"

    with pytest.raises(ValueError, match="kein gültiges JSON"):
        translation.choose_sense(
            url=model_server_double.url,
            model_name=model_server_double.model_name,
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_truncated_response_is_a_visible_failure(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, „Zwingende Einstellung: Denkschritt abschalten": finish_reason
    "length" mit leerem Inhalt sieht wie ein Erfolg aus (Status 200, wohlgeformte
    choices), ist aber keiner und muss sichtbar abbrechen statt als uncertain-Eintrag
    durchzugehen."""
    model_server_double.behavior = "truncated"

    with pytest.raises(ValueError, match="Denkschritt"):
        translation.choose_sense(
            url=model_server_double.url,
            model_name=model_server_double.model_name,
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_number_outside_the_valid_range_is_a_visible_failure(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 13: Eine Zahl außerhalb von 1..N+1 verletzt das erzwungene JSON-Schema
    (minimum/maximum) und bricht sichtbar ab, statt stillschweigend als Listenindex
    verwendet zu werden."""
    model_server_double.choice = 99

    with pytest.raises(ValueError, match="gültig ist nur"):
        translation.choose_sense(
            url=model_server_double.url,
            model_name=model_server_double.model_name,
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_long_candidate_list_is_rejected_before_sending_to_avoid_silent_truncation(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, Nachtrag 19.08.2026, „Datenfalle: der Server kürzt zu lange
    Prompts still": Eine Auswahlliste, deren Prompt geschätzt über der sicheren Schwelle
    liegt (technik.md nennt `run` mit 48 Bedeutungen), wird nicht gesendet — der Server
    würde sie sonst ohne sichtbaren Hinweis kürzen und `usage.prompt_tokens` zeigte den
    gekürzten Wert als korrekt an."""
    long_candidates = [
        Sense(
            lemma=_BANK_LEMMA,
            wikdict_sense="x" * 300,
            wikdict_trans_list="Bank",
            wikdict_lexentry=f"eng/bank__Noun__{n}",
        )
        for n in range(1, 51)
    ]

    with pytest.raises(ValueError, match="zu lang"):
        translation.choose_sense(
            url=model_server_double.url,
            model_name=model_server_double.model_name,
            occurrence=_occurrence(),
            sense_candidates=long_candidates,
        )

    assert model_server_double.requests == []
