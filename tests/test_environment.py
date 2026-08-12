"""Prüft, dass die Umgebung der Festlegung aus Entscheidung 6 entspricht."""

import importlib.util
import sys


def test_decision_6_runtime_is_python_312() -> None:
    """Entscheidung 6: Gebaut wird auf Python 3.12 — der Fassung, auf der die Messungen
    zu Entscheidung 5 entstanden sind (technik.md §6)."""
    assert sys.version_info[:2] == (3, 12)


def test_decision_6_pinned_spacy_model_is_installed() -> None:
    """Entscheidung 6: `en_core_web_md` ist als Abhängigkeit festgeschrieben, nicht
    nebenher installiert — Entscheidung 5 gilt nur für dieses Modell (technik.md §6)."""
    assert importlib.util.find_spec("en_core_web_md") is not None
