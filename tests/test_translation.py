"""Prüft `libreverbum/translation.py` — bauplan.md T11, Bedeutungsauswahl aus der
Auswahlliste des Wörterbuchs über die OpenAI-kompatible Schnittstelle."""

from __future__ import annotations

import http.client
import json
import urllib.request
from collections.abc import Callable
from typing import TYPE_CHECKING, NoReturn

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

# (Befund 2, Review T11): der Verb-Partikel-Platzhalter aus T7 ohne jeden
# wikdict_-Wert — genau die Form, die `dictionary.particle_verb_candidates` für einen
# Mehrwortausdruck ohne Wörterbucheintrag liefert (`Sense(lemma=lemma, uncertain=True)`).
_UNCERTAIN_CANDIDATE = Sense(lemma=_BANK_LEMMA, uncertain=True)

# Eine echte Regel-1-Zeile (kein sense-Text, aber ein Wörterbucheintrag) zum Vergleich —
# wie tools/en-de.sqlite3s "watch" als Substantiv (tests/conftest.py, _DICTIONARY_ROWS).
_NO_SENSE_CANDIDATE = Sense(
    lemma=_BANK_LEMMA,
    wikdict_sense=None,
    wikdict_trans_list="Uhr",
    wikdict_lexentry="eng/watch__Noun__1",
)


def _urlopen_raising(exc: BaseException) -> Callable[..., NoReturn]:
    """Ersatz für `urllib.request.urlopen`, der beim Aufruf sofort `exc` wirft (Befund 3,
    Review T11) — die drei zusätzlichen Fehlschläge brauchen keine echte Gegenstelle,
    ein Ersatz für den Netzaufruf genügt und bleibt schnell."""

    def _fake(*args: object, **kwargs: object) -> NoReturn:
        raise exc

    return _fake


class _FakeHTTPResponse:
    """Minimale Gegenstelle für `json.load(response)`: nur `read()` und die
    Kontextmanager-Protokollmethoden, wie sie `urllib.request.urlopen` normalerweise
    liefert (Befund 3 und Befund 4, Review T11)."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


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


def test_temperature_zero_is_sent_with_every_model_call(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, „Zwingende Einstellung: Temperatur auf 0": Bei jedem Modellaufruf
    wird temperature: 0 gesetzt — ohne diese Festlegung liefert derselbe Prompt
    verschiedene Antworten, und jede Messung an diesem Prompt wird unbrauchbar."""
    model_server_double.choice = 1

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    assert model_server_double.requests[-1]["temperature"] == 0


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
    """technik.md §3, „Datenfalle: der Server kürzt zu lange Prompts still": Eine
    Auswahlliste, deren Prompt geschätzt über der sicheren Schwelle
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


# ------------------------------------------------------- Befund 1, Review T11: der Prompt


def test_prompt_contains_the_fallback_answer_as_entry_number_n_plus_1(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, offener Punkt „keine passt" (Befund 1, Review T11): Der
    tatsächlich gesendete Prompt enthält die Ausweichzeile als Eintrag N+1 (N=2 echte
    Bedeutungen) — ohne sie hat das Modell kein Mittel, den `saw`-Fall zu melden."""
    model_server_double.choice = 1

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    prompt = model_server_double.requests[-1]["messages"][0]["content"]
    assert "3. none of the listed meanings fits" in prompt


def test_prompt_numbers_correspond_to_the_supplied_candidate_order(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund 1 (Review T11): Nummer k im gesendeten Prompt bezeichnet denselben
    Kandidaten wie sense_candidates[k-1] — nicht nur irgendeine Nummerierung, sondern
    diese Zuordnung, geprüft an zwei Kandidaten mit unterscheidbaren Bedeutungstexten,
    damit eine vertauschte Reihenfolge auffiele."""
    model_server_double.choice = 1

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=_BANK_CANDIDATES,
    )

    prompt = model_server_double.requests[-1]["messages"][0]["content"]
    assert "1. (Noun) institution → Bank" in prompt
    assert "2. (Noun) edge of river or lake → Ufer" in prompt


def test_prompt_contains_the_example_sentence_and_the_word_form(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund 1 (Review T11): Ohne Belegsatz und Wortform im gesendeten Prompt wäre die
    Auswahl reine Ratesache — beide gehören zum Kontext, den das Modell für die Wahl
    braucht."""
    model_server_double.choice = 1
    occurrence = _occurrence()

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=occurrence,
        sense_candidates=_BANK_CANDIDATES,
    )

    prompt = model_server_double.requests[-1]["messages"][0]["content"]
    assert occurrence.example_sentence in prompt
    assert f'"{occurrence.word_form}"' in prompt


# ------------------------------------------------- Befund 2, Review T11: uncertain-Marke


def test_prompt_labels_an_uncertain_candidate_differently_from_the_no_sense_text(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund 2 (Review T11): Ein als uncertain hereingegebener Kandidat (der
    Verb-Partikel-Platzhalter aus T7, `dictionary.particle_verb_candidates`) wird im
    Prompt erkennbar anders beschriftet als eine echte Regel-1-Zeile ohne sense-Text —
    sonst wäre er von einer bestätigten Hauptbedeutung nicht zu unterscheiden."""
    model_server_double.choice = 1
    candidates = [_UNCERTAIN_CANDIDATE, _NO_SENSE_CANDIDATE]

    translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=candidates,
    )

    prompt = model_server_double.requests[-1]["messages"][0]["content"]
    assert "1. (?) kein Wörterbucheintrag — unsicher → ?" in prompt
    assert "2. (Noun) Hauptbedeutung, ohne nähere Angabe → Uhr" in prompt


def test_choosing_an_uncertain_candidate_keeps_the_uncertain_marker_on_the_result(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund 2 (Review T11), Regel 10: Wählt das Modell einen schon als uncertain
    hereingegebenen Kandidaten, trägt das Ergebnis uncertain=True statt beim Zusammenbau
    fest auf False gesetzt zu werden."""
    model_server_double.choice = 1  # wählt den uncertain-Platzhalter auf Position 1
    candidates = [_UNCERTAIN_CANDIDATE, _RIVERBANK]

    result = translation.choose_sense(
        url=model_server_double.url,
        model_name=model_server_double.model_name,
        occurrence=_occurrence(),
        sense_candidates=candidates,
    )

    assert result.uncertain is True
    assert result.translation is None


# ------------------------------------ Befund 3, Review T11: drei zusätzliche Fehlschläge


def test_rule_13_timeout_is_a_visible_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Befund 3 (Review T11), Regel 13: Eine Lesezeitüberschreitung nach dem
    Verbindungsaufbau kommt als rohes TimeoutError an (kein URLError) und muss ebenso
    sichtbar mit einer deutschen Meldung abbrechen wie die übrigen Fehlschläge."""
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_raising(TimeoutError("timed out")))

    with pytest.raises(ValueError, match="nicht innerhalb von"):
        translation.choose_sense(
            url="http://example.invalid",
            model_name="mini-model",
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_non_json_response_body_is_a_visible_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 3 (Review T11), Regel 13: HTTP 200 mit einem Körper, der kein JSON ist
    (etwa Ollamas Wurzelseite hinter einem falsch konfigurierten Proxy), muss sichtbar
    abbrechen statt mit einem rohen json.JSONDecodeError durchzugehen."""
    html_body = b"<html><body>Ollama is running</body></html>"
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *args, **kwargs: _FakeHTTPResponse(html_body)
    )

    with pytest.raises(ValueError, match="kein gültiges JSON"):
        translation.choose_sense(
            url="http://example.invalid",
            model_name="mini-model",
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_incomplete_read_is_a_visible_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Befund 3 (Review T11), Regel 13: Ein Abbruch mitten in der Antwort
    (http.client.IncompleteRead) muss sichtbar abbrechen statt als englische Ausnahme
    durchzugehen."""
    monkeypatch.setattr(
        urllib.request, "urlopen", _urlopen_raising(http.client.IncompleteRead(b""))
    )

    with pytest.raises(ValueError, match="brach mitten in der Antwort ab"):
        translation.choose_sense(
            url="http://example.invalid",
            model_name="mini-model",
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


def test_rule_13_remote_disconnected_is_a_visible_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Befund 3 (Review T11), Regel 13: Dieselbe Einordnung wie bei IncompleteRead — beide
    Ausnahmeklassen stehen im selben except-Block und müssen dort beide tatsächlich
    gefangen werden, nicht nur die zuerst genannte."""
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _urlopen_raising(
            http.client.RemoteDisconnected("Remote end closed connection without response")
        ),
    )

    with pytest.raises(ValueError, match="brach mitten in der Antwort ab"):
        translation.choose_sense(
            url="http://example.invalid",
            model_name="mini-model",
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )


# --------------------------------------------- Befund 4, Review T11: keine stille Rundung


def test_fractional_choice_is_a_visible_failure_instead_of_being_rounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 4 (Review T11): {"choice": 1.9} ist derselbe Vertragsbruch, den die
    Bereichsprüfung zwei Zeilen weiter unten laut behandelt — int() darf ihn nicht still
    auf 1 abrunden."""
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": json.dumps({"choice": 1.9})},
                    "finish_reason": "stop",
                }
            ]
        }
    ).encode("utf-8")
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *args, **kwargs: _FakeHTTPResponse(payload)
    )

    with pytest.raises(ValueError, match="keine ganze Zahl"):
        translation.choose_sense(
            url="http://example.invalid",
            model_name="mini-model",
            occurrence=_occurrence(),
            sense_candidates=_BANK_CANDIDATES,
        )
