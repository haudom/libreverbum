"""Prüft `app/difficulty.py` — die drei Schwellenworte des Schwierigkeitschecks
(bauplan-phase2.md AP 7, E12)."""

from __future__ import annotations

from app import difficulty


def test_classify_difficulty_returns_easy_below_the_first_threshold() -> None:
    """E12: eine niedrige Dichte unbekannter Grundformen gilt als `EASY`."""
    assert difficulty.classify_difficulty(0.0) is difficulty.DifficultyLevel.EASY
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_EASY_MAX_UNKNOWN_PER_THOUSAND)
        is difficulty.DifficultyLevel.EASY
    )


def test_classify_difficulty_returns_moderate_between_the_two_thresholds() -> None:
    """E12: der mittlere Bereich, für den LibreVerbum in erster Linie gebaut ist."""
    midpoint = (
        difficulty._GUESSED_EASY_MAX_UNKNOWN_PER_THOUSAND
        + difficulty._GUESSED_MODERATE_MAX_UNKNOWN_PER_THOUSAND
    ) / 2
    assert difficulty.classify_difficulty(midpoint) is difficulty.DifficultyLevel.MODERATE
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_MODERATE_MAX_UNKNOWN_PER_THOUSAND)
        is difficulty.DifficultyLevel.MODERATE
    )


def test_classify_difficulty_returns_hard_above_the_second_threshold() -> None:
    """E12: „zu schwer für dich" im Wortlaut des Auftragstexts — oberhalb der zweiten
    Schwelle, etwa bei einem Kalibrierdurchlauf mit leerem Profil (Bericht zu diesem
    Auftragspaket: `tools/sherlock.epub` leer 156,9 je 1.000, weit oberhalb)."""
    above = difficulty._GUESSED_MODERATE_MAX_UNKNOWN_PER_THOUSAND + 0.1
    assert difficulty.classify_difficulty(above) is difficulty.DifficultyLevel.HARD
    assert difficulty.classify_difficulty(156.9) is difficulty.DifficultyLevel.HARD


def test_classify_difficulty_is_monotonic_non_decreasing() -> None:
    """Keine Regel behauptet das ausdrücklich, aber eine Einordnung, die bei steigender
    Dichte in eine leichtere Stufe zurückfiele, wäre für eine Anzeige („zu schwer für
    dich") nicht vertretbar.

    Verfälschungsprobe (Bericht): die beiden Rückgaben `MODERATE`/`HARD` in
    `classify_difficulty` vertauscht (mittlerer Bereich liefert `HARD`, oberster Bereich
    `MODERATE`) ließ diesen Test mit `[0, 0, 0, 2, 2, 2, …]` statt der sortierten Folge rot
    werden — Rang 2 vor Rang 1. Eine erste, schwächere Verfälschung (zweite Bedingung auf
    die erste Schwelle statt die zweite umgestellt) blieb hier grün und riss stattdessen
    `test_classify_difficulty_returns_moderate_between_the_two_thresholds`: Ordnung
    (dieser Test) und Wert an der richtigen Schwelle (jener Test) sind zwei verschiedene
    Zusicherungen, keine schwache."""
    samples = [0.0, 5.0, 40.0, 41.0, 70.0, 100.0, 100.1, 300.0]
    levels = [difficulty.classify_difficulty(value) for value in samples]
    order = {
        difficulty.DifficultyLevel.EASY: 0,
        difficulty.DifficultyLevel.MODERATE: 1,
        difficulty.DifficultyLevel.HARD: 2,
    }
    ranks = [order[level] for level in levels]
    assert ranks == sorted(ranks)
