"""Prüft `libreverbum/dictionary.py` — bauplan.md T5, Auswahlliste je Grundform und
Wortart."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from libreverbum import dictionary
from libreverbum.entities import Lemma


def test_rule_1_watch_keeps_its_headline_meaning_without_sense_text(
    mini_dictionary_db: Path,
) -> None:
    """Regel 1 (dokumentation.md §4): Zeilen ohne sense-Text gehören immer in die
    Auswahlliste — watch liefert seine Hauptbedeutung „Uhr" trotz fehlendem sense-Text,
    beschriftet als „Hauptbedeutung, ohne nähere Angabe" (technik.md §3, „Datenfalle")."""
    result = dictionary.candidates(mini_dictionary_db, Lemma(text="watch", pos="NOUN"))

    assert len(result) == 2
    headline = result[0]
    assert headline.wikdict_sense is None
    assert dictionary.label(headline) == "Hauptbedeutung, ohne nähere Angabe"
    assert headline.wikdict_trans_list == "Uhr | Armbanduhr"


def test_rule_1_draw_keeps_its_headline_meaning_without_sense_text(
    mini_dictionary_db: Path,
) -> None:
    """Regel 1 (dokumentation.md §4): dieselbe Prüfung für draw, den zweiten Beleg aus
    technik.md §3, „Datenfalle: Einträge ohne Bedeutungstext"."""
    result = dictionary.candidates(mini_dictionary_db, Lemma(text="draw", pos="VERB"))

    assert len(result) == 2
    headline = result[0]
    assert headline.wikdict_sense is None
    assert dictionary.label(headline) == "Hauptbedeutung, ohne nähere Angabe"
    assert headline.wikdict_trans_list == "zeichnen | malen | skizzieren"


def test_candidates_are_sorted_by_score_descending(tmp_path: Path) -> None:
    """bauplan.md T5: die Auswahlliste steht nach score absteigend.

    Befund 2 (Review Runde 1): In `mini_dictionary_db` steht die Einfügereihenfolge für
    watch und draw zufällig schon score-absteigend — dieser Test bestünde also auch ohne
    `ORDER BY score DESC` in der Abfrage. Eigens aufgebaute Vorrichtung mit einer
    Einfügereihenfolge, die genau umgekehrt zu score ist, damit der Test ohne die Sortierung
    in `dictionary.candidates` tatsächlich fehlschlägt."""
    path = tmp_path / "en-de.sqlite3"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE translation("
        "lexentry, sense_num, sense, written_rep TEXT, trans_list, score, is_good, importance"
        ")"
    )
    con.executemany(
        "INSERT INTO translation VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("eng/probe__Noun__1", None, "lowest score", "probe", "niedrig", 10.0, 1, 1.0),
            ("eng/probe__Noun__1", None, "highest score", "probe", "hoch", 90.0, 1, 1.0),
            ("eng/probe__Noun__1", None, "middle score", "probe", "mittel", 50.0, 1, 1.0),
        ],
    )
    con.commit()
    con.close()

    result = dictionary.candidates(path, Lemma(text="probe", pos="NOUN"))

    assert [s.wikdict_sense for s in result] == ["highest score", "middle score", "lowest score"]


def test_same_lemma_with_different_pos_yields_different_lists(mini_dictionary_db: Path) -> None:
    """Fortsetzung der zwingenden Reihenfolge Wortart → Grundform → Nachschlagen
    (technik.md, „Warum die Reihenfolge zwingend ist"): saw als Verb liefert nur „sägen",
    nie die Säge — der saw-Fall aus technik.md §3."""
    as_verb = dictionary.candidates(mini_dictionary_db, Lemma(text="saw", pos="VERB"))
    as_noun = dictionary.candidates(mini_dictionary_db, Lemma(text="saw", pos="NOUN"))

    assert [s.wikdict_trans_list for s in as_verb] == ["sägen"]
    assert [s.wikdict_trans_list for s in as_noun] == ["Säge", "Sprichwort | Spruch"]
    assert {s.wikdict_lexentry for s in as_verb}.isdisjoint({s.wikdict_lexentry for s in as_noun})


def test_missing_dictionary_file_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): eine fehlende Wörterbuchdatei ergibt einen sichtbaren
    Fehlschlag, keine leere Liste, die wie „kein Eintrag gefunden" aussähe."""
    missing = tmp_path / "en-de.sqlite3"

    with pytest.raises(FileNotFoundError):
        dictionary.candidates(missing, Lemma(text="watch", pos="NOUN"))


def test_unmapped_part_of_speech_is_a_visible_failure(mini_dictionary_db: Path) -> None:
    """Kein leiser Fehlschlag (Regel 13): Eine Wortart ohne WikDict-Entsprechung bricht
    sichtbar ab, statt eine leere Auswahlliste vorzutäuschen."""
    with pytest.raises(ValueError):
        dictionary.candidates(mini_dictionary_db, Lemma(text="watch", pos="AUX"))


def test_propn_is_no_longer_a_mapped_part_of_speech(mini_dictionary_db: Path) -> None:
    """Befund 3 (Review Runde 1): `PROPN → Proper_noun` ist entfernt — T3 setzt `chosen_pos`
    nie auf `PROPN`, T7 filtert `Proper_noun` ohnehin weg. Ein Aufruf mit `pos="PROPN"`
    bricht jetzt sichtbar ab wie jede andere nicht abgebildete Wortart (Regel 13), obwohl
    die Vorrichtung mit „South America" eine echte Proper_noun-Zeile enthält."""
    with pytest.raises(ValueError):
        dictionary.candidates(mini_dictionary_db, Lemma(text="South America", pos="PROPN"))


def test_rows_without_lexentry_are_deliberately_excluded(mini_dictionary_db: Path) -> None:
    """Befund 4 (Review Runde 1): Zeilen ohne `lexentry` (score < 50 in der Vorrichtung,
    „of the" → „vom") tragen keine Wortart und kommen bewusst nicht in die Auswahlliste —
    keine Nebenwirkung von `_wikdict_pos`, sondern `lexentry IS NOT NULL` in der Abfrage."""
    result = dictionary.candidates(mini_dictionary_db, Lemma(text="of the", pos="NOUN"))

    assert result == []


@pytest.mark.needs_dictionary
def test_rows_without_lexentry_are_excluded_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Befund 4 (Review Runde 1), gegen die echte Datei: `colour` hat in `tools/en-de.sqlite3`
    nur eine Zeile ohne `lexentry` und liefert darum eine leere, keine fehlende, Liste."""
    result = dictionary.candidates(real_dictionary_path, Lemma(text="colour", pos="NOUN"))

    assert result == []


@pytest.mark.needs_dictionary
def test_watch_noun_candidates_have_distinct_identity_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Befund 1 (Review Runde 1), schwerster Befund: `watch` als Substantiv liefert gegen die
    echte WikDict-Datenbank mehrere Zeilen mit demselben `lexentry` (u. a. dreimal „Wache" mit
    verschiedenem `wikdict_sense`) — jede muss ein eigenes Objekt in der Auswahlliste bleiben,
    statt über den geteilten `lexentry` im `set` zu kollabieren."""
    result = dictionary.candidates(real_dictionary_path, Lemma(text="watch", pos="NOUN"))

    assert len(result) > 1
    assert len(set(result)) == len(result)


@pytest.mark.needs_dictionary
def test_break_verb_candidates_have_distinct_identity_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Befund 1 (Review Runde 1): `break` als Verb kollabiert mit einer Identität allein aus
    `wikdict_lexentry` von 31 Bedeutungen auf 1 (Review-Messung) — mit dem vollen Zeileninhalt
    in der Identität bleiben alle Bedeutungen als eigene Objekte erhalten."""
    result = dictionary.candidates(real_dictionary_path, Lemma(text="break", pos="VERB"))

    assert len(result) > 1
    assert len(set(result)) == len(result)


def test_two_rows_with_same_lexentry_but_different_meaning_stay_distinct(
    mini_dictionary_db: Path,
) -> None:
    """Befund 1 (Review Runde 1), Nachweis an der Vorrichtung: `watch` als Substantiv enthält
    zwei Zeilen mit gleichem `lexentry` (`eng/watch__Noun__1`), aber verschiedener Bedeutung
    („Uhr" ohne sense-Text, „Wache" mit sense-Text „person or group of people who guard") —
    beide müssen als eigene Objekte im `set` überleben."""
    result = dictionary.candidates(mini_dictionary_db, Lemma(text="watch", pos="NOUN"))

    assert len({s.wikdict_lexentry for s in result}) == 1
    assert len(set(result)) == len(result) == 2
