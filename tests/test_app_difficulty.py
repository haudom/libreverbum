"""Prüft `app/difficulty.py` — die drei Schwellenworte des Schwierigkeitschecks
(bauplan-phase2.md AP 7, E12).

Seit der Nachbesserung der Durchsicht c6f3875 (Befund 2, Entscheidung Dominiks
23.09.2026) nimmt `classify_difficulty` eine Abdeckung (`coverage.share`, 0.0 bis 1.0,
höher heißt leichter), keine Dichte unbekannter Grundformen je 1.000 mehr — die Tests
unten sind entsprechend umgestellt, samt gespiegelter Grenzrichtung (`<=` wurde zu `>=`,
weil eine hohe Abdeckung jetzt „leicht" bedeutet)."""

from __future__ import annotations

from app import difficulty


def test_classify_difficulty_returns_easy_at_or_above_the_first_threshold() -> None:
    """E12: eine hohe Abdeckung gilt als `EASY`."""
    assert difficulty.classify_difficulty(1.0) is difficulty.DifficultyLevel.EASY
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_EASY_MIN_COVERAGE)
        is difficulty.DifficultyLevel.EASY
    )


def test_classify_difficulty_returns_moderate_between_the_two_thresholds() -> None:
    """E12: der mittlere Bereich, für den LibreVerbum in erster Linie gebaut ist — dort,
    wo die mit B1 vorbelegte Abdeckung der drei gemessenen Bücher tatsächlich liegt
    (84,1 bis 87,3 %, Bericht zu dieser Nachbesserung)."""
    midpoint = (
        difficulty._GUESSED_EASY_MIN_COVERAGE + difficulty._GUESSED_MODERATE_MIN_COVERAGE
    ) / 2
    assert difficulty.classify_difficulty(midpoint) is difficulty.DifficultyLevel.MODERATE
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_MODERATE_MIN_COVERAGE)
        is difficulty.DifficultyLevel.MODERATE
    )
    # Die drei real gemessenen B1-Werte (Rezept: app/difficulty.py, Kommentar bei den
    # beiden Schwellen) liegen alle in MODERATE — das ist der Zweck der Verschiebung
    # (Befund 2): Vorher (unknown_per_thousand) ordnete dieselbe Messung Dune als
    # „angemessen" trotz niedrigerer Abdeckung als Sherlock ein.
    for share in (0.8734, 0.8589, 0.8410):
        assert difficulty.classify_difficulty(share) is difficulty.DifficultyLevel.MODERATE


def test_classify_difficulty_returns_hard_below_the_second_threshold() -> None:
    """E12: „zu schwer für dich" im Wortlaut des Auftragstexts — unterhalb der zweiten
    Schwelle, etwa bei einem Kalibrierdurchlauf mit leerem Profil (Bericht zu dieser
    Nachbesserung: `tools/sherlock.epub` leer 58,36 % Abdeckung, weit darunter)."""
    below = difficulty._GUESSED_MODERATE_MIN_COVERAGE - 0.01
    assert difficulty.classify_difficulty(below) is difficulty.DifficultyLevel.HARD
    assert difficulty.classify_difficulty(0.5836) is difficulty.DifficultyLevel.HARD
    assert difficulty.classify_difficulty(0.0) is difficulty.DifficultyLevel.HARD


def test_classify_difficulty_is_monotonic_non_increasing() -> None:
    """Keine Regel behauptet das ausdrücklich, aber eine Einordnung, die bei sinkender
    Abdeckung in eine leichtere Stufe zurückfiele, wäre für eine Anzeige („zu schwer für
    dich") nicht vertretbar. Die Richtung ist gegenüber der früheren, je-1.000-basierten
    Fassung gespiegelt: Dort stieg der Rang mit dem Wert, hier fällt er.

    Verfälschungsprobe (Bericht): die beiden Rückgaben `MODERATE`/`HARD` in
    `classify_difficulty` vertauscht (mittlerer Bereich liefert `HARD`, unterster Bereich
    `MODERATE`) ließ diesen Test mit einer nicht absteigenden statt einer absteigenden
    Rangfolge rot werden. Eine erste, schwächere Verfälschung (zweite Bedingung auf die
    erste Schwelle statt die zweite umgestellt) blieb hier grün und riss stattdessen
    `test_classify_difficulty_returns_moderate_between_the_two_thresholds`: Ordnung
    (dieser Test) und Wert an der richtigen Schwelle (jener Test) sind zwei verschiedene
    Zusicherungen, keine schwache."""
    samples = [1.0, 0.95, 0.90, 0.899, 0.80, 0.75, 0.749, 0.50, 0.0]
    levels = [difficulty.classify_difficulty(value) for value in samples]
    order = {
        difficulty.DifficultyLevel.EASY: 0,
        difficulty.DifficultyLevel.MODERATE: 1,
        difficulty.DifficultyLevel.HARD: 2,
    }
    ranks = [order[level] for level in levels]
    assert ranks == sorted(ranks)
