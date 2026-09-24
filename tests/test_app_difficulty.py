"""Prüft `app/difficulty.py` — die drei Schwellenworte des Schwierigkeitschecks
(bauplan-phase2.md AP 7, E12) und die Umrechnung „unbekannte Wörter je Seite"
(Entscheidung B, E12).

Seit der Nachbesserung der Durchsicht c6f3875 (Befund 2, Entscheidung Dominiks
23.09.2026) nimmt `classify_difficulty` eine Abdeckung (`coverage.share`, 0.0 bis 1.0,
höher heißt leichter), keine Dichte unbekannter Grundformen je 1.000 mehr — die Tests
unten sind entsprechend umgestellt, samt gespiegelter Grenzrichtung (`<=` wurde zu `>=`,
weil eine hohe Abdeckung jetzt „leicht" bedeutet). Seit der Nachbesserung der Durchsicht
3b1e201 (Entscheidung A, 23.09.2026) liegen die beiden Schwellen bei 92 %/86 % statt
90 %/75 % — mit dieser Verschiebung unterscheidet die Einordnung erstmals zwischen den
drei gemessenen Büchern (Modulkommentar bei den beiden Schwellen, „Warum 90 %/75 % nicht
taugte")."""

from __future__ import annotations

import pytest

from app import difficulty


def test_classify_difficulty_returns_easy_at_or_above_the_first_threshold() -> None:
    """E12: eine hohe Abdeckung gilt als `EASY`."""
    assert difficulty.classify_difficulty(1.0) is difficulty.DifficultyLevel.EASY
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_EASY_MIN_COVERAGE)
        is difficulty.DifficultyLevel.EASY
    )


def test_classify_difficulty_returns_moderate_between_the_two_thresholds() -> None:
    """E12: der mittlere Bereich, für den LibreVerbum in erster Linie gebaut ist."""
    midpoint = (
        difficulty._GUESSED_EASY_MIN_COVERAGE + difficulty._GUESSED_MODERATE_MIN_COVERAGE
    ) / 2
    assert difficulty.classify_difficulty(midpoint) is difficulty.DifficultyLevel.MODERATE
    assert (
        difficulty.classify_difficulty(difficulty._GUESSED_MODERATE_MIN_COVERAGE)
        is difficulty.DifficultyLevel.MODERATE
    )


def test_classify_difficulty_distinguishes_the_three_measured_books_at_b1() -> None:
    """Entscheidung A, Nachbesserung der Durchsicht 3b1e201: Mit 90 %/75 % fielen alle
    drei mit B1 vorbelegten Bücher unter `MODERATE` — die Einordnung unterschied das
    Profil, nicht das Buch. Mit 92 %/86 % (Rezept: `app/difficulty.py`, Kommentar bei den
    beiden Schwellen; Bericht zu dieser Nachbesserung) bleibt nur Sherlock `MODERATE`,
    Dorian Gray und Dune fallen knapp darunter in `HARD`.

    Verfälschungsprobe (Bericht): die beiden Schwellen auf die alten Werte 0.90/0.75
    zurückgestellt ließ diesen Test rot werden — alle drei Werte lagen dann in
    `MODERATE`."""
    assert difficulty.classify_difficulty(0.8734) is difficulty.DifficultyLevel.MODERATE  # Sherlock
    assert difficulty.classify_difficulty(0.8589) is difficulty.DifficultyLevel.HARD  # Dorian Gray
    assert difficulty.classify_difficulty(0.8410) is difficulty.DifficultyLevel.HARD  # Dune


def test_classify_difficulty_returns_hard_below_the_second_threshold() -> None:
    """E12: „zu schwer für dich" im Wortlaut des Auftragstexts — unterhalb der zweiten
    Schwelle, etwa bei einem Kalibrierdurchlauf mit leerem Profil (Bericht zur
    Nachbesserung der Durchsicht c6f3875: `tools/sherlock.epub` leer 58,36 % Abdeckung,
    weit darunter)."""
    below = difficulty._GUESSED_MODERATE_MIN_COVERAGE - 0.01
    assert difficulty.classify_difficulty(below) is difficulty.DifficultyLevel.HARD
    assert difficulty.classify_difficulty(0.5836) is difficulty.DifficultyLevel.HARD
    assert difficulty.classify_difficulty(0.0) is difficulty.DifficultyLevel.HARD


def test_classify_difficulty_matches_the_rounded_percentage_shown_to_the_user() -> None:
    """Befund D5, Nachbesserung Durchsicht 79b4479, 24.09.2026: Anzeige und Einordnung
    dürfen sich an der Schwelle nicht widersprechen. `cli._format_decimal(share * 100,
    ndigits=1)` rundet auf ein Zehntelprozent — 0,85996 erscheint dort als „86,0 %".
    Ungerundet läge dieser Wert unter `_GUESSED_MODERATE_MIN_COVERAGE` (0,86) und ergäbe
    `HARD`: „86,0 % — zu schwer für dich" auf derselben Zeile. `classify_difficulty`
    rundet seit dieser Behebung selbst auf dieselbe Stelle, bevor es einordnet, und liefert
    hier `MODERATE`, passend zur angezeigten Zahl.

    Verfälschungsprobe (Bericht): Die Rundung in `classify_difficulty` entfernt (Vergleich
    wieder gegen den rohen `share`) ließ diesen Test rot werden — `classify_difficulty`
    lieferte dann `HARD` statt des erwarteten `MODERATE`."""
    share = 0.85996
    assert f"{share * 100:.1f}" == "86.0", (
        f"Testvoraussetzung verletzt: {share} rundet nicht auf 86,0 % — "
        "der Test prüft dann nicht den behaupteten Widerspruch."
    )
    assert difficulty.classify_difficulty(share) is difficulty.DifficultyLevel.MODERATE


def test_classify_difficulty_stays_hard_when_rounding_misses_the_threshold() -> None:
    """Gegenprobe zum Test oben: Ein Wert, der auch gerundet unter der Schwelle bleibt
    (85,9 % statt 86,0 %), bleibt `HARD` — die Rundung darf die Schwelle selbst nicht
    aufweichen, nur den Widerspruch zur angezeigten Stelle beseitigen."""
    share = 0.8589
    assert f"{share * 100:.1f}" == "85.9"
    assert difficulty.classify_difficulty(share) is difficulty.DifficultyLevel.HARD


def test_classify_difficulty_is_monotonic_non_increasing() -> None:
    """Keine Regel behauptet das ausdrücklich, aber eine Einordnung, die bei sinkender
    Abdeckung in eine leichtere Stufe zurückfiele, wäre für eine Anzeige („zu schwer für
    dich") nicht vertretbar. Die Richtung ist gegenüber der früheren, je-1.000-basierten
    Fassung gespiegelt: Dort stieg der Rang mit dem Wert, hier fällt er. Die Stichproben
    liegen um die aktuellen Schwellen (92 %/86 %, Entscheidung A), nicht mehr um die
    abgelösten 90 %/75 %.

    Verfälschungsprobe (Bericht): die beiden Rückgaben `MODERATE`/`HARD` in
    `classify_difficulty` vertauscht (mittlerer Bereich liefert `HARD`, unterster Bereich
    `MODERATE`) ließ diesen Test mit einer nicht absteigenden statt einer absteigenden
    Rangfolge rot werden. Eine erste, schwächere Verfälschung (zweite Bedingung auf die
    erste Schwelle statt die zweite umgestellt) blieb hier grün und riss stattdessen
    `test_classify_difficulty_returns_moderate_between_the_two_thresholds`: Ordnung
    (dieser Test) und Wert an der richtigen Schwelle (jener Test) sind zwei verschiedene
    Zusicherungen, keine schwache."""
    samples = [1.0, 0.95, 0.92, 0.919, 0.88, 0.86, 0.859, 0.50, 0.0]
    levels = [difficulty.classify_difficulty(value) for value in samples]
    order = {
        difficulty.DifficultyLevel.EASY: 0,
        difficulty.DifficultyLevel.MODERATE: 1,
        difficulty.DifficultyLevel.HARD: 2,
    }
    ranks = [order[level] for level in levels]
    assert ranks == sorted(ranks)


# ------------------------------------------------- unknown_words_per_page (Entscheidung B)


def test_unknown_words_per_page_derives_from_coverage_not_from_a_fixed_density() -> None:
    """Entscheidung B, E12: `(1 − share) × _GUESSED_PAGE_LENGTH_WORD_FORMS` — bei
    Sherlocks B1-Abdeckung (87,34 %, Bericht zu dieser Nachbesserung) ergibt das rund 38
    unbekannte Wörter je Seite, dieselbe Größenordnung wie die im Konzept genannten „ca.
    14 unbekannte Wörter pro Seite" (konzept.md, „Phase 2") auf einer geschätzten, nicht
    gemessenen Seitenlänge.

    Verfälschungsprobe (Bericht): die Umrechnung auf `unknown_lemma_count / token_count *
    300` (dieselbe Buchlängen-/Kapitelteilungsabhängigkeit wie das abgelöste
    `unknown_per_thousand`, nur mit anderem Faktor) umgestellt ließ diesen Test rot
    werden — er vergleicht nur gegen die Abdeckung, nicht gegen Wortzahlen."""
    assert difficulty.unknown_words_per_page(0.8734) == pytest.approx(37.98, abs=0.01)
    assert difficulty.unknown_words_per_page(1.0) == 0.0
    assert difficulty.unknown_words_per_page(0.0) == difficulty._GUESSED_PAGE_LENGTH_WORD_FORMS


def test_unknown_words_per_page_is_monotonically_decreasing_in_coverage() -> None:
    """Eine höhere Abdeckung darf nie mehr unbekannte Wörter je Seite ergeben — sonst
    widerspräche die Anzeige sich selbst (hohe Abdeckung, aber „mehr zu lernen").
    Auftragstext, Entscheidung B: dieselbe Funktion bedient Kapitel- **und** Buchzeile
    („einheitlich ist besser als zwei Maßzahlen nebeneinander"), deshalb genügt eine
    Zusicherung für beide — nur `Coverage.share` fließt ein, nichts, das zwischen Kapitel
    und Buch unterschiede.

    Verfälschungsprobe (Bericht): `1 - share` zu `share` verkehrt (also mehr Abdeckung
    ergäbe mehr unbekannte Wörter je Seite) ließ diesen Test rot werden."""
    values = [difficulty.unknown_words_per_page(share) for share in (0.5, 0.7, 0.87, 0.95, 1.0)]
    assert values == sorted(values, reverse=True)
