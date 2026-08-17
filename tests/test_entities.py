"""Prüft die Identität von `Sense` aus `libreverbum/entities.py`."""

from dataclasses import replace

from libreverbum.entities import Lemma, Sense


def test_sense_identity_distinguishes_same_lexentry_with_different_sense_text() -> None:
    """Befund 1 (Review Runde 1, T5): `wikdict_lexentry` allein unterscheidet zwei Zeilen
    desselben Lemmas nicht — 22,7 % der Zeilen in `tools/en-de.sqlite3` teilen sich einen
    `lexentry` mit einer anderen Bedeutung. Zwei Bedeutungen mit gleichem `wikdict_lexentry`,
    aber verschiedenem `wikdict_sense`, sind darum ungleich und überleben gemeinsam in einem
    `set` — sonst kollabiert etwa `watch` als Substantiv von vier Zeilen auf eine."""
    lemma = Lemma(text="watch", pos="NOUN")
    a = Sense(lemma=lemma, wikdict_sense="particular time period", wikdict_lexentry="watch_1")
    b = Sense(
        lemma=lemma, wikdict_sense="group of sailors and officers", wikdict_lexentry="watch_1"
    )

    assert a != b
    assert len({a, b}) == 2


def test_rule_1_sense_identity_distinguishes_lexentry_without_sense_text() -> None:
    """Regel 1: Zeilen ohne `sense`-Text bleiben in der Triage — zwei Bedeutungen desselben
    Lemmas ohne Bedeutungstext, aber mit verschiedenem `wikdict_lexentry`, sind ungleich und
    überleben gemeinsam in einem `set`."""
    lemma = Lemma(text="bank", pos="NOUN")
    a = Sense(lemma=lemma, wikdict_sense=None, wikdict_lexentry="bank_1")
    b = Sense(lemma=lemma, wikdict_sense=None, wikdict_lexentry="bank_2")

    assert a != b
    assert len({a, b}) == 2


def test_sense_identity_survives_setting_translation() -> None:
    """Dieselbe Bedeutung bleibt vor und nach dem Setzen von `translation` gleich, weil
    Ergebnisfelder außerhalb von Gleichheit und Hash liegen."""
    lemma = Lemma(text="bank", pos="NOUN")
    before = Sense(lemma=lemma, wikdict_lexentry="bank_1")
    after = replace(before, translation="Ufer", uncertain=True)

    assert before == after
    assert hash(before) == hash(after)
