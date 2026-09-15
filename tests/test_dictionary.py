"""Prüft `libreverbum/dictionary.py` — bauplan.md T5, Auswahlliste je Grundform und
Wortart, bauplan.md T6, Erstbezug der Wörterbuchdatei, und bauplan.md T7, Abgleich der
Mehrwortausdruck-Kandidaten aus T4."""

from __future__ import annotations

import http.server
import sqlite3
import stat
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import pytest

from libreverbum import dictionary
from libreverbum.entities import Lemma, Sense


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


def test_missing_dictionary_file_is_a_visible_failure_for_candidate_lists(tmp_path: Path) -> None:
    """Befund 4 (Review T15), Regel 13 (dokumentation.md §4): `candidate_lists` bricht wie
    `candidates` sichtbar ab, wenn die Wörterbuchdatei fehlt — nicht erst am ersten Lemma
    der Liste."""
    missing = tmp_path / "en-de.sqlite3"

    with pytest.raises(FileNotFoundError):
        dictionary.candidate_lists(missing, [Lemma(text="watch", pos="NOUN")])


def test_candidate_lists_matches_candidates_for_each_lemma_with_its_own_part_of_speech(
    mini_dictionary_db: Path,
) -> None:
    """Befund 4 (Review T15): `candidate_lists` teilt eine Verbindung über mehrere Lemmas
    hinweg (gemessen: 1,43 s gegen 0,20 s bei 1.465 Vorkommen, Bericht T15) — dabei behält
    **jedes** Lemma seine eigene Wortart. `saw` als Verb und als Substantiv bei gleichem
    `written_rep` prüft das in einem Zug: Eine Umsetzung, die die Wortart nur einmal für
    die ganze Liste bestimmte (etwa aus dem ersten Lemma), lieferte für „saw" (Verb) die
    Substantiv-Bedeutungen oder umgekehrt, statt für jedes Lemma dasselbe Ergebnis wie der
    einzelne Aufruf von `candidates`."""
    lemmas = [
        Lemma(text="watch", pos="NOUN"),
        Lemma(text="saw", pos="VERB"),
        Lemma(text="saw", pos="NOUN"),
    ]

    result = dictionary.candidate_lists(mini_dictionary_db, lemmas)

    assert len(result) == 3
    for lemma, expected in zip(lemmas, result, strict=True):
        assert expected == dictionary.candidates(mini_dictionary_db, lemma)
    assert [s.wikdict_trans_list for s in result[0]] == ["Uhr | Armbanduhr", "Wache"]
    assert [s.wikdict_trans_list for s in result[1]] == ["sägen"]
    assert [s.wikdict_trans_list for s in result[2]] == ["Säge", "Sprichwort | Spruch"]


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


# ------------------------------------------------- Mehrwortausdrücke (bauplan.md T7)


def _own_dictionary(path: Path, rows: list[tuple[object, ...]]) -> None:
    """Baut eine eigene, kleine Wörterbuchdatei für einen einzelnen Test auf (wie bei
    `test_candidates_are_sorted_by_score_descending`) — für Fälle, die `mini_dictionary_db`
    nicht abdeckt und die die gemeinsame, von einem zweiten Bearbeiter nicht angefasste
    Vorrichtung deshalb nicht bekommen soll."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE translation("
        "lexentry, sense_num, sense, written_rep TEXT, trans_list, score, is_good, importance"
        ")"
    )
    con.executemany("INSERT INTO translation VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.commit()
    con.close()


def test_missing_dictionary_file_is_a_visible_failure_for_contiguous_candidates(
    tmp_path: Path,
) -> None:
    """Regel 13 (dokumentation.md §4): eine fehlende Wörterbuchdatei ergibt bei
    `contiguous_candidates` denselben sichtbaren Fehlschlag wie bei `candidates` — kein
    leerer Kandidat, sondern ein vollständig fehlendes Wörterbuch."""
    missing = tmp_path / "en-de.sqlite3"

    with pytest.raises(FileNotFoundError):
        dictionary.contiguous_candidates(missing, [Lemma(text="give up", pos="")])


def test_missing_dictionary_file_is_a_visible_failure_for_particle_verb_candidates(
    tmp_path: Path,
) -> None:
    """Regel 13 (dokumentation.md §4): derselbe sichtbare Fehlschlag bei
    `particle_verb_candidates`."""
    missing = tmp_path / "en-de.sqlite3"

    with pytest.raises(FileNotFoundError):
        dictionary.particle_verb_candidates(missing, [Lemma(text="give up", pos="VERB")])


def test_contiguous_candidates_drop_entries_without_a_dictionary_match(
    mini_dictionary_db: Path,
) -> None:
    """Befund 1 (Review T7): Ein Kandidat aus `extraction.extract_contiguous_candidates`
    ohne bestandenen Filter — kein Eintrag, score unter der Schwelle, oder `Proper_noun` —
    wird verworfen, nicht markiert; die n-Gramm-Hypothese verschwindet einfach, wie es der
    Filter aus technik.md, „Messung: Mehrwortausdrücke" verlangt. `south america`
    kleingeschrieben (Befund 2, so wie T4 die Grundform wirklich liefert) prüft dabei die
    case-insensitive Suche und den `Proper_noun`-Filter in einem Zug: Nur wer die
    großgeschriebene Zeile überhaupt findet, kann sie auch als `Proper_noun` ausschließen.
    Eine einzige Liste für vier Kandidaten prüft außerdem, dass die Rückgabe in der
    Reihenfolge der Eingabe steht (Befund 5, Review T7)."""
    lemmas = [
        Lemma(text="give up", pos="VERB"),
        Lemma(text="completely unknown phrase", pos=""),
        Lemma(text="of the", pos=""),
        Lemma(text="south america", pos=""),
    ]

    result = dictionary.contiguous_candidates(mini_dictionary_db, lemmas)

    assert len(result) == 4
    assert {sense.wikdict_trans_list for sense in result[0]} == {
        "aufgeben | kapitulieren",
        "aufgeben | ergeben",
    }
    assert result[1] == []
    assert result[2] == []
    assert result[3] == []


def test_particle_verb_candidates_mark_entries_without_a_dictionary_match_as_uncertain(
    mini_dictionary_db: Path,
) -> None:
    """Befund 1 (Review T7): Ein Kandidat aus `extraction.extract_particle_verb_candidates`
    ohne bestandenen Filter wird als `uncertain` markiert (Regel 10, Regel 11), nicht
    verworfen — anders als bei `contiguous_candidates`, geprüft an derselben Liste mit
    denselben drei Gründen, an einem Kandidaten zu scheitern (kein Eintrag, score unter der
    Schwelle, `Proper_noun`), plus derselben Reihenfolgeprüfung (Befund 5, Review T7)."""
    lemmas = [
        Lemma(text="give up", pos="VERB"),
        Lemma(text="completely unknown phrase", pos=""),
        Lemma(text="of the", pos=""),
        Lemma(text="south america", pos=""),
    ]

    result = dictionary.particle_verb_candidates(mini_dictionary_db, lemmas)

    assert len(result) == 4
    assert len(result[0]) == 2
    assert all(sense.uncertain is False for sense in result[0])
    for lemma, matches in zip(lemmas[1:], result[1:], strict=True):
        assert len(matches) == 1
        assert matches[0].uncertain is True
        assert matches[0].lemma == lemma
        assert matches[0].wikdict_sense is None
        assert matches[0].wikdict_trans_list is None


def test_contiguous_candidates_are_sorted_by_score_descending(tmp_path: Path) -> None:
    """bauplan.md T7, wie bei T5 (test_candidates_are_sorted_by_score_descending): die
    Auswahlliste steht nach score absteigend. Eigens aufgebaute Vorrichtung mit einer
    Einfügereihenfolge, die genau umgekehrt zu score ist, damit der Test ohne
    `ORDER BY score DESC` tatsächlich fehlschlägt."""
    path = tmp_path / "en-de.sqlite3"
    _own_dictionary(
        path,
        [
            ("eng/phrase__Verb__1", None, "lowest", "some phrase", "niedrig", 51.0, 1, 1.0),
            ("eng/phrase__Verb__1", None, "highest", "some phrase", "hoch", 99.0, 1, 1.0),
            ("eng/phrase__Verb__1", None, "middle", "some phrase", "mittel", 75.0, 1, 1.0),
        ],
    )

    result = dictionary.contiguous_candidates(path, [Lemma(text="some phrase", pos="VERB")])

    assert [s.wikdict_sense for s in result[0]] == ["highest", "middle", "lowest"]


def test_lowercase_candidate_matches_capitalised_dictionary_entry_regardless_of_case(
    tmp_path: Path,
) -> None:
    """Befund 2 (Review T7): T4 liefert jede Grundform kleingeschrieben
    (`extraction.py`, `token.lemma_.lower()`), WikDicts `written_rep` ist schreibungsecht
    (`New York`, nicht `new york`) — ohne case-insensitiven Vergleich fände `new york` die
    Zeile nie. Eigene Vorrichtung, weil `mini_dictionary_db` keine großgeschriebene
    Mehrwortzeile ohne `Proper_noun` enthält, an der sich das prüfen ließe."""
    path = tmp_path / "en-de.sqlite3"
    _own_dictionary(
        path,
        [
            (
                "eng/New_York__Noun__1",
                None,
                "city in the United States",
                "New York",
                "New York",
                163.6,
                1,
                1.0,
            )
        ],
    )

    result = dictionary.particle_verb_candidates(path, [Lemma(text="new york", pos="")])

    assert len(result[0]) == 1
    assert result[0][0].uncertain is False
    assert result[0][0].wikdict_trans_list == "New York"


def test_rule_1_row_without_sense_text_is_not_filtered_for_multiword_candidates(
    tmp_path: Path,
) -> None:
    """Regel 1 (dokumentation.md §4), Befund 4 (Review T7): `put up with` steht in
    `tools/en-de.sqlite3` ohne `sense`-Text (score 101,7) — die Abfrage aus T7 darf solche
    Zeilen nicht wegfiltern, genau wie `candidates` aus T5. Eigene Vorrichtung, wie vom
    Review vorgeschlagen, weil `mini_dictionary_db` keine mehrwortige Zeile ohne
    `sense`-Text enthält und von einem zweiten Bearbeiter nicht angefasst wird."""
    path = tmp_path / "en-de.sqlite3"
    _own_dictionary(
        path,
        [
            (
                "eng/put_up_with__Verb__1",
                None,
                None,
                "put up with",
                "ertragen | aushalten | akzeptieren",
                101.7,
                1,
                1.0,
            )
        ],
    )

    result = dictionary.contiguous_candidates(path, [Lemma(text="put up with", pos="VERB")])

    assert len(result[0]) == 1
    assert result[0][0].wikdict_sense is None
    assert result[0][0].wikdict_trans_list == "ertragen | aushalten | akzeptieren"


def test_uncertain_placeholder_has_a_different_label_than_a_real_rule_1_row() -> None:
    """Befund 3 (Review T7): Der Platzhalter für einen Mehrwortausdruck-Kandidaten ohne
    Wörterbucheintrag (`uncertain=True`, kein `wikdict_sense`) darf nicht dieselbe
    Beschriftung tragen wie eine echte Regel-1-Zeile ohne `sense`-Text — sonst sähe ein
    leeres Übersetzungsfeld in der Auswahlliste (T11) wie eine belegte Hauptbedeutung aus."""
    real_rule_1_row = Sense(
        lemma=Lemma(text="watch", pos="NOUN"), wikdict_trans_list="Uhr | Armbanduhr"
    )
    uncertain_placeholder = Sense(lemma=Lemma(text="unknown phrase", pos=""), uncertain=True)

    assert dictionary.label(real_rule_1_row) == dictionary.NO_SENSE_LABEL
    assert dictionary.label(uncertain_placeholder) == dictionary.UNCERTAIN_LABEL
    assert dictionary.label(real_rule_1_row) != dictionary.label(uncertain_placeholder)


@pytest.mark.needs_dictionary
def test_give_up_passes_the_filter_against_real_dictionary(real_dictionary_path: Path) -> None:
    """technik.md, „Messung: Mehrwortausdrücke": `give up` liegt in `tools/en-de.sqlite3`
    bei score 120,0 und besteht den Filter — dieselbe Behauptung wie an der Vorrichtung,
    zusätzlich gegen die echte Datei geprüft (dokumentation.md §5, „Woran geprüft wird")."""
    result = dictionary.particle_verb_candidates(
        real_dictionary_path, [Lemma(text="give up", pos="VERB")]
    )

    assert len(result[0]) > 1
    assert all(sense.uncertain is False for sense in result[0])


@pytest.mark.needs_dictionary
def test_take_up_is_marked_uncertain_against_real_dictionary(real_dictionary_path: Path) -> None:
    """technik.md §3, „Grenze: rund ein Fünftel der Phrasal Verbs steht getrennt": `take
    up` steht zwar in `tools/en-de.sqlite3`, aber keine seiner Zeilen erreicht score 50 —
    der Filter markiert den Kandidaten trotzdem als unsicher, statt ihn stillschweigend mit
    einer der niedrig bewerteten Zeilen zu übersetzen."""
    result = dictionary.particle_verb_candidates(
        real_dictionary_path, [Lemma(text="take up", pos="VERB")]
    )

    assert len(result[0]) == 1
    assert result[0][0].uncertain is True


@pytest.mark.needs_dictionary
def test_indian_summer_lowercase_matches_capitalised_entry_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Befund 2 (Review T7): `indian summer` kleingeschrieben — so, wie T4 die Grundform
    wirklich liefert (`token.lemma_.lower()`) — findet in `tools/en-de.sqlite3` die
    großgeschriebene Zeile `Indian summer` (`Noun`, score 112,1) und wird nicht `uncertain`.
    Vor der Behebung liefert die binäre Abfrage keinen Treffer."""
    result = dictionary.particle_verb_candidates(
        real_dictionary_path, [Lemma(text="indian summer", pos="")]
    )

    assert len(result[0]) >= 1
    assert all(sense.uncertain is False for sense in result[0])


@pytest.mark.needs_dictionary
def test_great_britain_lowercase_is_marked_uncertain_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Befund 2 (Review T7): `great britain` kleingeschrieben findet in
    `tools/en-de.sqlite3` trotz case-insensitiver Suche keine Lernvokabel — die Zeile
    `Great Britain` (score 210,0) ist `Proper_noun` und bleibt deshalb `uncertain`, wie
    schon vor der Behebung, aber jetzt, weil der Filter greift, nicht weil die Suche die
    Zeile verfehlt."""
    result = dictionary.particle_verb_candidates(
        real_dictionary_path, [Lemma(text="great britain", pos="")]
    )

    assert len(result[0]) == 1
    assert result[0][0].uncertain is True


@pytest.mark.needs_dictionary
def test_put_up_with_row_without_sense_text_is_not_filtered_against_real_dictionary(
    real_dictionary_path: Path,
) -> None:
    """Regel 1 (dokumentation.md §4), Befund 4 (Review T7): `put up with` hat in
    `tools/en-de.sqlite3` genau eine Zeile ohne `sense`-Text (score 101,7) — dieselbe
    Behauptung wie an der eigenen Vorrichtung
    (test_rule_1_row_without_sense_text_is_not_filtered_for_multiword_candidates),
    zusätzlich gegen die echte Datei geprüft. Entsteht laut `extraction.py` als eigener
    3-Gramm-Kandidat, deshalb hier über `contiguous_candidates`."""
    result = dictionary.contiguous_candidates(
        real_dictionary_path, [Lemma(text="put up with", pos="VERB")]
    )

    assert len(result[0]) == 1
    assert result[0][0].wikdict_sense is None
    assert result[0][0].wikdict_trans_list
    assert result[0][0].uncertain is False


# ---------------------------------------------------- Erstbezug (bauplan.md T6) — Attrappe

# Örtliche Attrappe des HTTP-Bezugs statt eines echten Zugriffs auf download.wikdict.com
# (dokumentation.md §5, „Woran geprüft wird: die Vorrichtung zeigt Laufen, die
# Fremdquelle Stimmen"). `behavior` schaltet zwischen den Fällen um, die fetch_dictionary
# unterscheiden muss (Regel 13): "ok" liefert den Inhalt von mini_dictionary_db
# vollständig, "http_error" antwortet mit Status 500, "no_length" antwortet ohne
# Content-Length-Kopfzeile, "truncated" bricht die Verbindung nach der Hälfte der Bytes
# ab, ohne die angekündigte Content-Length einzuhalten — der abgebrochene Bezug aus dem
# Auftrag.


@dataclass
class _FetchServerDouble:
    url: str
    body: bytes
    behavior: Literal["ok", "http_error", "truncated", "no_length"] = "ok"
    request_count: int = 0


class _FetchHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass  # Testlauf soll nicht auf stderr protokollieren

    def do_GET(self) -> None:
        server = cast("_FetchHTTPServer", self.server)
        double = server.double
        double.request_count += 1
        if double.behavior == "http_error":
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = double.body
        if double.behavior == "truncated":
            # REGEL (dokumentation.md §4 Regel 13): Content-Length verspricht die volle
            # Länge, aber nur die halbe Länge wird tatsächlich geschickt, dann bricht die
            # Verbindung ab — der abgebrochene Bezug, den fetch_dictionary erkennen muss.
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body[: len(body) // 2])
            self.close_connection = True
            return
        if double.behavior == "no_length":
            # Befund 1 (Review T6): keine Content-Length-Kopfzeile — die Vollständigkeit
            # ist dann gar nicht erst prüfbar, unabhängig davon, wie viele Bytes ankommen.
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _FetchHTTPServer(http.server.ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[_FetchHandler],
        double: _FetchServerDouble,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.double = double


@pytest.fixture
def fetch_server(mini_dictionary_db: Path) -> Iterator[_FetchServerDouble]:
    """Attrappe für den Download-Bezug — läuft ohne Netz, liefert standardmäßig den Inhalt
    von `mini_dictionary_db` als Dateibytes (bauplan.md T6)."""
    double = _FetchServerDouble(url="", body=mini_dictionary_db.read_bytes())
    server = _FetchHTTPServer(("127.0.0.1", 0), _FetchHandler, double)
    double.url = f"http://127.0.0.1:{server.server_port}/en-de.sqlite3"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield double
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _realistic_row_count_floor_disabled_for_the_mini_dictionary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`mini_dictionary_db` hat absichtlich nur eine Handvoll Zeilen (bauplan.md T2). Die
    Plausibilitätsgrenze aus `_validate_schema` bezieht sich auf die echte Zeilenzahl von
    WikDict (technik.md §3, 157.801 Zeilen; technik.md §2, „Keine Prüfsumme, weil WikDict
    keine veröffentlicht") und würde sie sonst in jedem Erstbezug-Test hier als
    abgebrochen werten. Wer die Grenze selbst
    prüfen will, hebt sie in seinem eigenen Test wieder an."""
    monkeypatch.setattr(dictionary, "_MIN_TRANSLATION_ROWS", 1)


def test_fetch_dictionary_downloads_verifies_and_indexes_a_missing_file(
    tmp_path: Path, fetch_server: _FetchServerDouble
) -> None:
    """bauplan.md T6: Fehlt die Datei, wird sie von der angegebenen Adresse bezogen, geprüft
    (Vollständigkeit, Schema, Zeilenzahl) und danach indiziert (technik.md §3, „Der Engpass
    ist das Nachschlagen, nicht das Modell")."""
    # REGEL (dokumentation.md §5, „ein Test gilt erst als Test…"): eigener Unterordner statt
    # tmp_path direkt — fetch_server hängt an mini_dictionary_db, die selbst schon
    # tmp_path/"en-de.sqlite3" anlegt. Ohne den Unterordner läge die Zieldatei zufällig
    # schon am Ort, den fetch_dictionary erst erzeugen soll, und path.is_file() wäre stets
    # wahr — der Download-Zweig würde nie geprüft, ohne dass ein Test das bemerkte.
    target = tmp_path / "fetched" / "en-de.sqlite3"

    dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert target.is_file()
    assert fetch_server.request_count == 1
    con = sqlite3.connect(target)
    try:
        indexes = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
    finally:
        con.close()
    assert dictionary.INDEX_NAME in indexes
    assert dictionary.INDEX_NAME_NOCASE in indexes
    # keine Nebendatei bleibt liegen, die den Erstbezug ein zweites Mal auslöste
    assert not target.with_name(target.name + ".part").exists()


def test_download_failure_is_a_visible_failure_and_leaves_no_file(
    tmp_path: Path, fetch_server: _FetchServerDouble
) -> None:
    """Regel 13: Ein abgebrochener Bezug (HTTP-Fehlschlag) bricht mit einer deutschen
    Meldung ab und lässt weder die Zieldatei noch eine Nebendatei zurück — kein leeres
    Ergebnis, das wie ein erfolgreicher, aber leerer Bezug aussähe."""
    target = tmp_path / "fetched" / "en-de.sqlite3"
    fetch_server.behavior = "http_error"

    with pytest.raises(ValueError, match="fehlgeschlagen"):
        dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()


def test_truncated_download_is_a_visible_failure_and_leaves_no_file(
    tmp_path: Path, fetch_server: _FetchServerDouble
) -> None:
    """Regel 13, „Die Falle: es scheitert nicht laut, sondern leise": Ein Bezug, der mitten
    im Übertragen abbricht, liefert weniger Bytes als per Content-Length angekündigt — ohne
    eigene Prüfung sähe das wie eine kleinere, aber gültige Datei aus. fetch_dictionary
    muss das erkennen und darf weder die Ziel- noch eine Nebendatei zurücklassen."""
    target = tmp_path / "fetched" / "en-de.sqlite3"
    fetch_server.behavior = "truncated"

    with pytest.raises(ValueError, match="abgebrochen"):
        dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()


def test_download_without_content_length_is_a_visible_failure(
    tmp_path: Path, fetch_server: _FetchServerDouble
) -> None:
    """Befund 1 (Review T6): Ohne Content-Length-Kopfzeile ist die Vollständigkeit des
    Downloads gar nicht erst prüfbar (Transfer-Encoding: chunked, ein Zwischenspeicher
    ohne Kopfzeile, …) — das gilt als sichtbarer Fehlschlag (Regel 13), nicht als
    stillschweigend akzeptierter, mittendrin abgebrochener Bezug."""
    target = tmp_path / "fetched" / "en-de.sqlite3"
    fetch_server.behavior = "no_length"

    with pytest.raises(ValueError, match="Content-Length"):
        dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()


def test_implausibly_small_translation_table_is_a_visible_failure(
    tmp_path: Path, fetch_server: _FetchServerDouble, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 1 (Review T6): `PRAGMA table_info` liest nur das Schema (Seite 1) — eine
    schemarichtige, aber (nahezu) leere Tabelle bestünde die Schemaprüfung trotzdem. Die
    Zeilenzahl-Untergrenze aus `_validate_schema` fängt das unabhängig von der
    Content-Length-Prüfung ab (technik.md §2, „Keine Prüfsumme, weil WikDict keine
    veröffentlicht")."""
    monkeypatch.setattr(dictionary, "_MIN_TRANSLATION_ROWS", 1_000_000)
    target = tmp_path / "fetched" / "en-de.sqlite3"

    with pytest.raises(ValueError, match="Zeilen"):
        dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()


def test_index_failure_during_download_leaves_no_file_at_the_final_path(
    tmp_path: Path, fetch_server: _FetchServerDouble, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 2 (Review T6): `ensure_index` läuft vor dem Umbenennen der Nebendatei —
    schlägt er fehl, bleibt weder an `path` noch als Nebendatei etwas liegen. Liefe er erst
    danach, stünde eine unindizierte Datei bereits an `path`, und `path.is_file()`
    verhinderte beim nächsten Versuch jeden erneuten Download (technik.md §3, „Der Engpass
    ist das Nachschlagen, nicht das Modell")."""
    target = tmp_path / "fetched" / "en-de.sqlite3"

    def _boom(path: Path) -> None:
        raise sqlite3.DatabaseError("Testfehler: Index kann nicht angelegt werden")

    monkeypatch.setattr(dictionary, "ensure_index", _boom)

    with pytest.raises(sqlite3.DatabaseError):
        dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()


def test_existing_file_is_not_downloaded_again(
    tmp_path: Path, fetch_server: _FetchServerDouble, mini_dictionary_db: Path
) -> None:
    """Auftrag T6, Tests: eine vorhandene Datei — heruntergeladen oder von Hand hinterlegt
    (technik.md §2, „Warum nicht mitgeliefert") — wird nicht neu geladen. Die Attrappe zählt
    ihre Anfragen; bleibt sie bei 0, wurde die Adresse gar nicht erst kontaktiert."""
    target = tmp_path / "fetched" / "en-de.sqlite3"
    target.parent.mkdir()
    target.write_bytes(mini_dictionary_db.read_bytes())

    dictionary.fetch_dictionary(target, url=fetch_server.url)

    assert fetch_server.request_count == 0


def test_existing_file_gets_indexed_even_though_it_is_not_downloaded(
    tmp_path: Path, fetch_server: _FetchServerDouble, mini_dictionary_db: Path
) -> None:
    """bauplan.md T6: Auch eine von Hand hinterlegte Datei bringt den Index nicht mit
    (technik.md §3, „Der Engpass ist das Nachschlagen, nicht das Modell") —
    fetch_dictionary muss ihn trotzdem anlegen, obwohl die Datei nicht neu geladen wird."""
    target = tmp_path / "fetched" / "en-de.sqlite3"
    target.parent.mkdir()
    target.write_bytes(mini_dictionary_db.read_bytes())

    dictionary.fetch_dictionary(target, url=fetch_server.url)

    con = sqlite3.connect(target)
    try:
        indexes = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
    finally:
        con.close()
    assert dictionary.INDEX_NAME in indexes
    assert dictionary.INDEX_NAME_NOCASE in indexes


def test_file_without_expected_table_is_a_visible_failure(tmp_path: Path) -> None:
    """Auftrag T6, Regel 13: Eine vorhandene Datei ohne die erwartete Tabelle `translation`
    bricht sichtbar ab, statt unbemerkt als gültiges Wörterbuch zu gelten — etwa eine
    versehentlich verwechselte SQLite-Datei."""
    target = tmp_path / "en-de.sqlite3"
    con = sqlite3.connect(target)
    con.execute("CREATE TABLE other(id INTEGER)")
    con.commit()
    con.close()

    # Befund 5 (Review T6): unerreichbare Adresse statt DICTIONARY_URL — bestünde der
    # is_file()-Zweig oben nicht mehr, zöge der Testlauf sonst die echten 20 MB von
    # download.wikdict.com, statt am Netzverbot zu scheitern.
    with pytest.raises(ValueError, match="translation"):
        dictionary.fetch_dictionary(target, url="http://127.0.0.1:9/nicht-erreichbar")


def test_ensure_index_does_not_create_a_file_for_a_missing_path(tmp_path: Path) -> None:
    """Befund 3 (Review T6): `ensure_index` prüft `path.is_file()` zuerst, statt über
    `sqlite3.connect` stillschweigend eine leere Datenbankdatei anzulegen, wenn `path`
    nicht existiert."""
    missing = tmp_path / "en-de.sqlite3"

    with pytest.raises(ValueError, match="nicht lesbar"):
        dictionary.ensure_index(missing)

    assert not missing.exists()


def test_ensure_index_fails_visibly_and_in_german_on_a_read_only_file(
    mini_dictionary_db: Path,
) -> None:
    """Befund 3 (Review T6): Eine schreibgeschützt hinterlegte Wörterbuchdatei (technik.md
    §2, „von Hand hinterlegte Datenbankdatei") bricht mit einer deutschen Meldung ab, statt
    `sqlite3`s englische Fremdmeldung „attempt to write a readonly database" unverändert
    durchzureichen (dokumentation.md §1, Sprachregel)."""
    mini_dictionary_db.chmod(stat.S_IREAD)
    try:
        with pytest.raises(ValueError, match="schreibgeschützt"):
            dictionary.ensure_index(mini_dictionary_db)
    finally:
        mini_dictionary_db.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_index_is_created_and_not_created_twice(mini_dictionary_db: Path) -> None:
    """Auftrag T6, Tests: Beide Indizes (Befund 2, Review T7: zweiter Index für den
    case-insensitiven Vergleich) entstehen und werden nicht doppelt angelegt — ein
    zweiter Aufruf auf derselben Datei bleibt folgenlos statt mit „index already exists"
    abzubrechen."""
    dictionary.ensure_index(mini_dictionary_db)
    dictionary.ensure_index(mini_dictionary_db)

    con = sqlite3.connect(mini_dictionary_db)
    try:
        counts = {
            name: con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
            ).fetchone()[0]
            for name in (dictionary.INDEX_NAME, dictionary.INDEX_NAME_NOCASE)
        }
    finally:
        con.close()
    assert counts == {dictionary.INDEX_NAME: 1, dictionary.INDEX_NAME_NOCASE: 1}


def test_index_is_created_on_a_file_that_already_carries_the_old_single_index(
    mini_dictionary_db: Path,
) -> None:
    """Befund 2 (Review T7): `ensure_index` bleibt idempotent, auch wenn die Datei bereits
    den alten, einzelnen Index aus einem früheren Aufruf trägt — der zweite Index entsteht
    dann zusätzlich, nicht anstelle des ersten."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        con.execute(f"CREATE INDEX {dictionary.INDEX_NAME} ON translation(written_rep)")
        con.commit()
    finally:
        con.close()

    dictionary.ensure_index(mini_dictionary_db)

    con = sqlite3.connect(mini_dictionary_db)
    try:
        indexes = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }
    finally:
        con.close()
    assert indexes == {dictionary.INDEX_NAME, dictionary.INDEX_NAME_NOCASE}


def test_index_turns_full_scan_into_indexed_search(mini_dictionary_db: Path) -> None:
    """technik.md §3, „Der Engpass ist das Nachschlagen, nicht das Modell": Ohne Index
    scannt die Abfrage aus `dictionary.candidates` die volle Tabelle; mit Index sucht sie
    gezielt."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        plan_before = con.execute(
            "EXPLAIN QUERY PLAN SELECT lexentry FROM translation WHERE written_rep = ?", ("watch",)
        ).fetchall()
    finally:
        con.close()
    assert any("SCAN" in str(row) for row in plan_before)

    dictionary.ensure_index(mini_dictionary_db)

    con = sqlite3.connect(mini_dictionary_db)
    try:
        plan_after = con.execute(
            "EXPLAIN QUERY PLAN SELECT lexentry FROM translation WHERE written_rep = ?", ("watch",)
        ).fetchall()
    finally:
        con.close()
    assert any("USING INDEX " + dictionary.INDEX_NAME in str(row) for row in plan_after)


def test_nocase_index_turns_full_scan_into_indexed_search_for_multiword_candidates(
    mini_dictionary_db: Path,
) -> None:
    """Befund 2 (Review T7): Die case-insensitive Abfrage aus `_lookup_matches` (T7)
    braucht einen eigenen Index — der binäre `INDEX_NAME` passt nicht zu `COLLATE NOCASE`
    und ließe die Abfrage sonst auf den vollen Scan zurückfallen (technik.md §3, „Der
    Engpass ist das Nachschlagen, nicht das Modell": 32–44 s statt 1,1 s je Kapitel)."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        plan_before = con.execute(
            "EXPLAIN QUERY PLAN SELECT lexentry FROM translation "
            "WHERE written_rep = ? COLLATE NOCASE",
            ("give up",),
        ).fetchall()
    finally:
        con.close()
    assert any("SCAN" in str(row) for row in plan_before)

    dictionary.ensure_index(mini_dictionary_db)

    con = sqlite3.connect(mini_dictionary_db)
    try:
        plan_after = con.execute(
            "EXPLAIN QUERY PLAN SELECT lexentry FROM translation "
            "WHERE written_rep = ? COLLATE NOCASE",
            ("give up",),
        ).fetchall()
    finally:
        con.close()
    assert any("USING INDEX " + dictionary.INDEX_NAME_NOCASE in str(row) for row in plan_after)


def test_source_notice_names_the_dictionary_source_and_its_licence() -> None:
    """Auftrag T6: Hinweis auf Herkunft und Lizenz, den der Aufrufer beim ersten Bezug
    anzeigen kann (technik.md §2, „Warum nicht mitgeliefert")."""
    assert "WikDict" in dictionary.SOURCE_NOTICE
    assert "Creative Commons" in dictionary.SOURCE_NOTICE
    assert dictionary.DICTIONARY_URL in dictionary.SOURCE_NOTICE


@pytest.mark.needs_dictionary
def test_real_dictionary_has_no_index_on_written_rep(real_dictionary_path: Path) -> None:
    """technik.md §3, „Der Engpass ist das Nachschlagen, nicht das Modell": Die bezogene
    Datei bringt keinen Index mit — geprüft an der echten Datei, nicht behauptet
    (dokumentation.md §5, „Woran geprüft wird")."""
    con = sqlite3.connect(real_dictionary_path)
    try:
        indexes = [
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        ]
    finally:
        con.close()
    # Befund 6 (Review T6), erweitert um den zweiten Index aus Befund 2 (Review T7): nur
    # „kein fremder Index" prüfen. INDEX_NAME und INDEX_NAME_NOCASE stammen aus diesem
    # Projekt (ensure_index, bauplan.md T6) — läuft fetch_dictionary einmal auf der echten
    # Datei, tragen sie sie danach dauerhaft, ohne dass das ein Widerspruch zur Aussage
    # oben wäre. `assert indexes == []` schiede dann unwiderruflich fehl, wiederherstellbar
    # nur durch erneutes Herunterladen der 20 MB.
    assert set(indexes) <= {dictionary.INDEX_NAME, dictionary.INDEX_NAME_NOCASE}


# ------------------------------------- pos_variants/pos_variant_lists (Bauschritt 3/5 der
# ------------------------------------- Vorbelegung, 31.08.2026)


def test_pos_variants_word_class_comes_from_the_dictionary_not_a_fixed_value(
    mini_dictionary_db: Path,
) -> None:
    """Bauschritt 3/5 der Vorbelegung, Auftragstext: „Eine feste Wortart zu schreiben wäre
    der stille Fehlschlag" — die Wortart eines (Grundform, Wortart)-Paars kommt aus dem
    Fund, nicht aus einer Annahme. `bank` trägt im Mini-Wörterbuch nur Substantiv-Einträge,
    `draw` sowohl Verb- als auch Substantiv-Einträge; eine feste Wortart, gleich welche,
    verfehlte mindestens eines der beiden Wörter."""
    bank_variants = dictionary.pos_variants(mini_dictionary_db, "bank")
    draw_variants = dictionary.pos_variants(mini_dictionary_db, "draw")

    assert {lemma.pos for lemma, _ in bank_variants} == {"NOUN"}
    assert {lemma.pos for lemma, _ in draw_variants} == {"VERB", "NOUN"}


def test_pos_variants_groups_all_senses_of_one_wordclass_into_one_pair(
    mini_dictionary_db: Path,
) -> None:
    """`bank` trägt zwei Substantiv-Bedeutungen (Geldinstitut, Flussufer) — beide gehören
    zu **einem** (Grundform, Wortart)-Paar, nicht zu zweien."""
    variants = dictionary.pos_variants(mini_dictionary_db, "bank")

    assert len(variants) == 1
    lemma, senses = variants[0]
    assert lemma == Lemma(text="bank", pos="NOUN")
    assert {sense.wikdict_trans_list for sense in senses} == {"Bank", "Ufer"}


def test_pos_variants_is_empty_for_a_lemma_without_a_dictionary_entry(
    mini_dictionary_db: Path,
) -> None:
    """Eine Grundform ohne Wörterbucheintrag liefert eine leere Liste, kein
    `uncertain`-Ergebnis: `pos_variants` ist ein reiner Nachschlagevorgang, kein
    Kandidat aus einem Kapiteldurchlauf."""
    assert dictionary.pos_variants(mini_dictionary_db, "flumplewort") == []


def test_pos_variant_lists_matches_individual_pos_variants_calls(mini_dictionary_db: Path) -> None:
    """`pos_variant_lists` über eine geteilte Verbindung liefert dieselben Paare wie
    einzelne `pos_variants`-Aufrufe, in derselben Reihenfolge wie die Eingabe."""
    texts = ["bank", "draw", "flumplewort"]

    batched = dictionary.pos_variant_lists(mini_dictionary_db, texts)

    assert batched == [dictionary.pos_variants(mini_dictionary_db, text) for text in texts]
