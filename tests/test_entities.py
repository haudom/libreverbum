"""Prüft die Identität von `Sense` aus `libreverbum/entities.py`."""

from dataclasses import replace

from libreverbum.entities import Lemma, Sense


def test_rule_1_sense_identity_ignores_wikdict_sense_snapshot() -> None:
    """Regel 1: `wikdict_sense` ist eine Momentaufnahme und bildet nicht die Identität —
    zwei Bedeutungen, die sich nur darin unterscheiden, sind gleich und teilen den Hash."""
    lemma = Lemma(text="bank", pos="NOUN")
    a = Sense(lemma=lemma, wikdict_sense="ein Geldinstitut", wikdict_lexentry="bank_1")
    b = Sense(lemma=lemma, wikdict_sense=None, wikdict_lexentry="bank_1")

    assert a == b
    assert hash(a) == hash(b)


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
