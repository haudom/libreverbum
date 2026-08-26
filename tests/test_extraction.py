"""Prüft `libreverbum/extraction.py` (bauplan.md T3, T4)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from libreverbum import epub
from libreverbum.entities import Book, Chapter, Occurrence
from libreverbum.extraction import (
    extract_contiguous_candidates,
    extract_particle_verb_candidates,
    extract_vocabulary,
    load_nlp,
)

if TYPE_CHECKING:
    from spacy.language import Language


@pytest.fixture(scope="module")
def nlp() -> Language:
    """Lädt das spaCy-Modell einmal für alle Tests dieser Datei — das Laden kostet rund
    eine Sekunde (technik.md §5) und soll nicht je Test anfallen."""
    return load_nlp()


@pytest.fixture(scope="module")
def nlp_without_lemmatizer() -> Language:
    """spaCy-Pipeline ohne Lemmatisierer — Testvorrichtung für Regel 2 und Regel 13
    (Befund 2, Review Runde 1; Befund 1, Review T4): Eine kaputte Pipeline darf nicht
    still zu Oberflächenformen als Grundform führen, in keiner der drei Funktionen
    dieses Moduls."""
    import spacy

    return spacy.load("en_core_web_md", exclude=["lemmatizer"])


def make_chapter(text: str, *, number: int = 1) -> Chapter:
    book = Book(title="Testbuch", author="Test Autorin")
    return Chapter(book=book, number=number, title="Testkapitel", text=text)


def find(occurrences: list[Occurrence], lemma_text: str, pos: str | None = None) -> Occurrence:
    """Sucht ein `Occurrence` nach Grundform, optional nach Wortart."""
    matches = [
        o for o in occurrences if o.lemma.text == lemma_text and (pos is None or o.lemma.pos == pos)
    ]
    assert len(matches) == 1, (
        f"{lemma_text!r} (pos={pos}) genau einmal erwartet, {len(matches)}-mal gefunden"
    )
    return matches[0]


def has_lemma(occurrences: list[Occurrence], lemma_text: str) -> bool:
    return any(o.lemma.text == lemma_text for o in occurrences)


def has_word_form(occurrences: list[Occurrence], word_form: str) -> bool:
    return any(o.word_form == word_form for o in occurrences)


# --------------------------------------------------------------------------- Regel 2


def test_rule_2_saw_as_verb_becomes_the_lemma_see_not_the_tool(nlp: Language) -> None:
    """Regel 2 (dokumentation.md §4): `He saw her yesterday.` ergibt die Grundform
    *see*, nicht *saw* — Lemmatisierung vor dem Nachschlagen (technik.md, „Warum die
    Reihenfolge zwingend ist")."""
    chapter = make_chapter("He saw her yesterday.")
    occurrences = extract_vocabulary(chapter, nlp)

    see = find(occurrences, "see", "VERB")
    assert see.frequency == 1
    assert see.word_form == "saw"
    assert not has_lemma(occurrences, "saw")


def test_rule_2_saw_as_noun_stays_the_tool(nlp: Language) -> None:
    """Gegenprobe zu Regel 2: Als Werkzeug bleibt `saw` bei der Grundform *saw*, weil
    die Wortart hier NOUN und nicht VERB ist — die Wortart entscheidet, nicht die
    Wortform allein."""
    chapter = make_chapter("He cut the plank in half with a rusty saw.")
    occurrences = extract_vocabulary(chapter, nlp)

    saw = find(occurrences, "saw", "NOUN")
    assert saw.frequency == 1
    assert not has_lemma(occurrences, "see")


def test_broken_pipeline_without_lemmatizer_aborts_instead_of_silently_using_surface_forms(
    nlp_without_lemmatizer: Language,
) -> None:
    """Regel 2 und Regel 13 (dokumentation.md §4, Befund 2 Review Runde 1): Fehlt der
    Lemmatisierer, bricht die Extraktion sichtbar ab, statt `saw` still als eigene
    Grundform durchzureichen — der saw-Fall darf nicht leise scheitern."""
    chapter = make_chapter("He saw her yesterday.")

    with pytest.raises(ValueError):
        extract_vocabulary(chapter, nlp_without_lemmatizer)


# -------------------------------------------------------------------------- Regel 12


def test_rule_12_red_stays_a_learning_word_despite_appearing_in_a_proper_name(
    nlp: Language,
) -> None:
    """Regel 12: Der Eigennamenfilter wirkt auf das Vorkommen, nie auf die Grundform —
    `red` bleibt Lernvokabel, obwohl es auch in einem Namen steht (dokumentation.md §5)."""
    chapter = make_chapter(
        "Mr. Red walked down the street with his dog. She painted the old fence a bright red."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    red = find(occurrences, "red")
    assert red.frequency == 2
    assert red.proper_noun_frequency == 1
    assert red.proper_noun_frequency < red.frequency, "red müsste als Lernvokabel gelten"


def test_rule_12_a_name_that_never_occurs_as_an_ordinary_word_is_not_extracted(
    nlp: Language,
) -> None:
    """Regel 12 / Abnahmekriterium 2: Ein Wort, das ausschließlich als Eigenname
    vorkommt, wird gar nicht erst als Grundform geliefert — keine Figurennamen als
    Lernvokabeln."""
    chapter = make_chapter("Sherlock arrived at noon.")
    occurrences = extract_vocabulary(chapter, nlp)

    # (Befund 4, Review Runde 1): Grundformen werden kleingeschrieben (Regel 12), eine
    # großgeschriebene Grundform ist unerreichbar — das prüft stattdessen word_form, das
    # die ursprüngliche Schreibung behält.
    assert not has_lemma(occurrences, "sherlock")
    assert not has_word_form(occurrences, "Sherlock")


@pytest.mark.needs_epub
def test_rule_12_proper_noun_ratio_excludes_the_title_character_but_keeps_an_address_noun(
    nlp: Language, real_epub_paths: dict[str, Path]
) -> None:
    """schwer 1 (Abnahme T17, 25.08.2026): Das vormalige strikte Kleiner-Zeichen
    (`proper_noun_frequency < frequency`, mindestens ein nicht-eigennamiges Vorkommen
    genügte) ließ die Titelfigur „Dorian" durch — 25 von 26 Vorkommen in
    `tools/dorian_gray.epub` Kapitel 16 sind PROPN (Anteil 0,96). Der Anteilsschwellwert
    (`extraction._PROPER_NOUN_RATIO_THRESHOLD`, 0,90) hält sie draußen, ohne ein echtes
    Anredesubstantiv mitzureißen — geprüft an echten Kapiteln aus
    `tools/dorian_gray.epub`, nicht an einer nachgebauten Vorrichtung (dokumentation.md
    §5, „Woran geprüft wird")."""
    path = real_epub_paths["dorian_gray"]
    structure = epub.read_structure(path)

    reference_16 = next(c for c in structure.chapters if c.number == 16)
    chapter_16 = epub.read_chapter(path, structure.book, reference_16)
    occurrences_16 = extract_vocabulary(chapter_16, nlp)
    assert not has_lemma(occurrences_16, "dorian")

    # Gegenprobe im selben Buch: „lady" in Kapitel 17 hat einen Anteil von 0,80 (24 von
    # 30 Vorkommen PROPN) — als Anredesubstantiv bleibt es trotz des Eigennamenanteils
    # Lernvokabel, weil 0,80 unter der Schwelle von 0,90 liegt.
    reference_17 = next(c for c in structure.chapters if c.number == 17)
    chapter_17 = epub.read_chapter(path, structure.book, reference_17)
    occurrences_17 = extract_vocabulary(chapter_17, nlp)
    lady = find(occurrences_17, "lady")
    assert lady.proper_noun_frequency > 0
    assert lady.proper_noun_frequency < lady.frequency


# ------------------------------------------------------------- Inhaltswortfilter


def test_auxiliary_modal_and_gerund_forms_are_not_extracted(nlp: Language) -> None:
    """technik.md §5, offener Punkt: `could` und `having` (als Hilfsverb) werden vor
    dem Nachschlagen ausgesteuert, statt als Wörterbuchlücke zu erscheinen — beide sind
    Funktionswörter, die nie Lernvokabeln werden."""
    chapter = make_chapter(
        "He could not believe his eyes. Having finished the letter, she sealed the envelope."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    assert not has_lemma(occurrences, "could")
    assert not has_lemma(occurrences, "having")
    # Der Hauptsatz bleibt regulär vorhanden — nur die Hilfsverbform ist ausgesteuert.
    assert has_lemma(occurrences, "believe")
    assert has_lemma(occurrences, "finish")


def test_having_as_a_main_verb_is_still_extracted(nlp: Language) -> None:
    """Gegenprobe: `having` in Hauptverbstellung („having a hard time") trägt bei
    spaCy die Wortart VERB statt AUX und bleibt deshalb erhalten — der Filter trifft
    die Wortart, nicht die Wortform."""
    chapter = make_chapter("She has been having a hard time lately.")
    occurrences = extract_vocabulary(chapter, nlp)

    have = find(occurrences, "have", "VERB")
    assert have.word_form == "having"


def test_only_content_words_are_extracted_function_words_are_filtered_out(nlp: Language) -> None:
    """Nur Inhaltswörter kommen in die Wortliste (Review Runde 2, erlaubte statt
    Sperrliste): Artikel, Pronomen, Präpositionen und Hilfsverben fehlen, obwohl sie im
    Satz stehen — die Inhaltswörter desselben Satzes stehen dagegen alle drin. Ein Test,
    der nur die Abwesenheit prüfte, wäre auch bei einer leeren Liste grün."""
    chapter = make_chapter("The dog was quickly chased by his loyal friend.")
    occurrences = extract_vocabulary(chapter, nlp)

    assert not has_lemma(occurrences, "the")
    assert not has_lemma(occurrences, "be")
    assert not has_lemma(occurrences, "by")
    assert not has_lemma(occurrences, "his")

    assert has_lemma(occurrences, "dog")
    assert has_lemma(occurrences, "quickly")
    assert has_lemma(occurrences, "chase")
    assert has_lemma(occurrences, "loyal")
    assert has_lemma(occurrences, "friend")


# ---------------------------------------------------- Wortartauflösung und Belegsatz


def test_pos_resolution_more_frequent_pos_wins(nlp: Language) -> None:
    """Moduldocstring, Abschnitt „Regeln": Mischt eine Grundform mehrere Wortarten
    unter ihren nicht-eigennamigen Vorkommen, gewinnt die häufigere — `watch` tritt
    zweimal als NOUN und nur einmal als VERB auf."""
    chapter = make_chapter(
        "She bought a new watch. He wore his watch every day. They needed to watch the news."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "NOUN")
    assert watch.word_form == "watch"
    assert watch.example_sentence == "She bought a new watch."


def test_pos_resolution_tie_is_broken_by_first_seen_pos(nlp: Language) -> None:
    """Moduldocstring, Abschnitt „Regeln", Gleichstand: je ein VERB- und ein
    NOUN-Vorkommen von `watch` — die zuerst gesehene Wortart gewinnt, hier VERB."""
    chapter = make_chapter("They wanted to watch the game. He checked his watch.")
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "VERB")
    assert watch.word_form == "watch"
    assert watch.example_sentence == "They wanted to watch the game."


def test_representative_word_form_and_sentence_match_the_chosen_pos(nlp: Language) -> None:
    """Befund 1 (Review Runde 1): Belegsatz und Wortform gehören zur gewählten
    Wortart — bei `watch` gewinnt VERB (zwei von drei Vorkommen), Wortform und
    Belegsatz stammen deshalb vom ersten VERB-Vorkommen, nicht vom ersten Vorkommen
    überhaupt."""
    chapter = make_chapter(
        "He checked his watch. Then he watched the door. Later he watched the clock."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    watch = find(occurrences, "watch", "VERB")
    assert watch.word_form == "watched"
    assert watch.example_sentence == "Then he watched the door."


# ---------------------------------------------------------- Häufigkeit und Belegsatz


def test_inflected_forms_are_merged_into_one_entry_with_combined_frequency(nlp: Language) -> None:
    """Abnahmekriterium 2: Beugungsformen sind in der Wortliste zusammengefasst —
    `running`, `runs` und `ran` ergeben eine Grundform *run* mit Häufigkeit 3."""
    chapter = make_chapter(
        "She was running late. He runs every morning. They ran together yesterday."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    run = find(occurrences, "run", "VERB")
    assert run.frequency == 3
    assert run.word_form == "running"
    assert run.example_sentence == "She was running late."


def test_frequency_and_example_sentence_are_scoped_to_the_given_chapter(nlp: Language) -> None:
    """Häufigkeit und Belegsatz gehören zum übergebenen Kapitel — `book` und
    `chapter_number` auf dem `Occurrence` stammen aus dem `Chapter`-Argument."""
    chapter = make_chapter("The dog barked twice. The dog ran across the street.", number=3)
    occurrences = extract_vocabulary(chapter, nlp)

    dog = find(occurrences, "dog", "NOUN")
    assert dog.frequency == 2
    assert dog.book == chapter.book
    assert dog.chapter_number == 3
    assert dog.example_sentence == "The dog barked twice."


# ------------------------------------------------------------------- Abnahmekriterium 2


def test_acceptance_2_inflections_merged_and_no_proper_names_as_learning_words(
    nlp: Language,
) -> None:
    """Abnahmekriterium 2: Für ein mittleres Kapitel entsteht eine Wortliste, in der
    Beugungsformen zusammengefasst sind und keine Figurennamen als Lernvokabeln
    auftauchen."""
    chapter = make_chapter(
        "Sherlock walked through London. "
        "He was walking for an hour before he finally stopped walking."
    )
    occurrences = extract_vocabulary(chapter, nlp)

    walk = find(occurrences, "walk", "VERB")
    assert walk.frequency == 3

    # (Befund 4, Review Runde 1): siehe Begründung bei Regel 12 oben.
    assert not has_lemma(occurrences, "sherlock")
    assert not has_lemma(occurrences, "london")
    assert not has_word_form(occurrences, "Sherlock")
    assert not has_word_form(occurrences, "London")


# ---------------------------------------------------------------------- bauplan.md T4


def find_mwe(occurrences: list[Occurrence], lemma_text: str) -> Occurrence:
    """Wie `find`, aber ohne Wortart — Mehrwortkandidaten tragen hier keine einzelne
    Wortart (particle-verb-Weg: immer VERB; n-Gramm-Weg: leer, siehe `_NO_SINGLE_POS`)."""
    matches = [o for o in occurrences if o.lemma.text == lemma_text]
    assert len(matches) == 1, f"{lemma_text!r} genau einmal erwartet, {len(matches)}-mal gefunden"
    return matches[0]


def has_mwe(occurrences: list[Occurrence], lemma_text: str) -> bool:
    return any(o.lemma.text == lemma_text for o in occurrences)


# ------------------------------------------------- extract_particle_verb_candidates


def test_acceptance_t4_separated_phrasal_verb_gave_the_idea_up_is_found(nlp: Language) -> None:
    """Prüfung aus bauplan.md T4: der getrennte Fall (`gave the idea up`) wird gefunden."""
    chapter = make_chapter("He gave the idea up.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    give_up = find_mwe(expressions, "give up")
    assert give_up.frequency == 1
    assert give_up.lemma.pos == "VERB"
    assert give_up.word_form == "gave the idea up"


def test_particle_verb_extraction_finds_the_separated_case_that_the_filtered_word_list_cannot(
    nlp: Language,
) -> None:
    """Die Falle aus dem Auftrag: `up` trägt die Wortart ADP und fällt darum durch den
    Inhaltswortfilter aus `extract_vocabulary` (`_CONTENT_POS`). Wer T4 auf dessen
    Ergebnis statt auf der Abhängigkeitsanalyse des geparsten Dokuments aufbaut, kann
    den getrennten Fall nie finden — die Partikel kommt in der gefilterten Liste gar
    nicht mehr vor. Ein Test, der nur die Wortliste läse, würde diese Umstellung nicht
    bemerken; deshalb prüft dieser Test beides gemeinsam."""
    chapter = make_chapter("He gave the idea up.")

    vocabulary = extract_vocabulary(chapter, nlp)
    assert not has_word_form(vocabulary, "up"), (
        "Testvoraussetzung verletzt: „up“ dürfte nicht in der gefilterten Wortliste stehen"
    )

    expressions = extract_particle_verb_candidates(chapter, nlp)
    assert find_mwe(expressions, "give up").word_form == "gave the idea up"


def test_contiguous_phrasal_verb_gave_up_the_idea_is_also_found(nlp: Language) -> None:
    """Gegenprobe zum getrennten Fall: Steht die Partikel unmittelbar hinter dem Verb,
    wird sie ebenfalls gefunden — beide Fälle kommen aus derselben Abhängigkeitsanalyse
    (bauplan.md T4, „zusammenhängende Kandidatenfolgen und getrennte
    Verb-Partikel-Paare")."""
    chapter = make_chapter("He gave up the idea.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    give_up = find_mwe(expressions, "give up")
    assert give_up.frequency == 1
    assert give_up.word_form == "gave up"


def test_contiguous_and_separated_occurrences_of_the_same_expression_are_merged(
    nlp: Language,
) -> None:
    """Wie bei Beugungsformen in `extract_vocabulary` (Abnahmekriterium 2) werden mehrere
    Vorkommen derselben Grundform zusammengefasst — hier eines zusammenhängend, eines
    getrennt, macht zusammen Häufigkeit 2."""
    chapter = make_chapter("He gave up the idea. Later she gave the plan up too.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    give_up = find_mwe(expressions, "give up")
    assert give_up.frequency == 2


def test_ordinary_preposition_after_a_verb_is_not_mistaken_for_a_particle(nlp: Language) -> None:
    """Gegenprobe: `to` in „walked to the store“ und `into` in „ran into a friend“ tragen
    bei spaCy die Abhängigkeit `prep`, nicht `prt` — echte Präpositionalobjekte sind
    keine Phrasal-Verb-Partikel und dürfen keinen Kandidaten erzeugen (siehe
    Begründung bei `_PARTICLE_DEP`)."""
    chapter = make_chapter("He walked to the store. They ran into an old friend.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    assert expressions == []


def test_multiword_expression_frequency_and_scope_match_the_given_chapter(nlp: Language) -> None:
    """Wie bei `extract_vocabulary`: `book` und `chapter_number` gehören zum übergebenen
    `Chapter`, und Wortform und Belegsatz stammen vom **ersten** Vorkommen (Befund 4,
    Review T4) — ein Kapitel mit zwei Sätzen, damit ein Test, der stattdessen das
    letzte Vorkommen nähme, tatsächlich fehlschlüge."""
    chapter = make_chapter(
        "They shut the business up before noon. Later she shut the shop up as well.", number=4
    )
    expressions = extract_particle_verb_candidates(chapter, nlp)

    shut_up = find_mwe(expressions, "shut up")
    assert shut_up.frequency == 2
    assert shut_up.book == chapter.book
    assert shut_up.chapter_number == 4
    assert shut_up.word_form == "shut the business up"
    assert shut_up.example_sentence == "They shut the business up before noon."


def test_broken_pipeline_without_lemmatizer_aborts_the_particle_verb_extraction(
    nlp_without_lemmatizer: Language,
) -> None:
    """Befund 1, Review T4: Wie `extract_vocabulary` bricht auch
    `extract_particle_verb_candidates` ohne Lemmatisierer sichtbar ab, statt eine
    Grundform aus lauter Leerzeichen zu erzeugen (nachgemessen mit
    `en_core_web_md, exclude=["lemmatizer"]` an „He gave the idea up.“, siehe Bericht)."""
    chapter = make_chapter("He gave the idea up.")

    with pytest.raises(ValueError):
        extract_particle_verb_candidates(chapter, nlp_without_lemmatizer)


def test_word_form_has_no_raw_newline_when_the_source_text_breaks_the_line(nlp: Language) -> None:
    """Befund 3, Review T4: `Span.text` gibt den Quelltext zwischen Verb und Partikel
    unverändert wieder — bei einem Zeilenumbruch im Buchtext stünde sonst ein rohes
    `\\n` in `word_form`, das laut `entities.Occurrence` „später auf der Karte steht“
    (T13)."""
    chapter = make_chapter("He threw himself\ndown on the bed.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    throw_down = find_mwe(expressions, "throw down")
    assert "\n" not in throw_down.word_form
    assert throw_down.word_form == "threw himself down"


def test_particle_dependent_on_a_non_verb_head_is_not_a_phrasal_verb_candidate(
    nlp: Language,
) -> None:
    """Befund 4, Review T4: spaCy zeichnet `prt` auch an substantivierten Fällen aus —
    „the washing up“ ist eine Nominalphrase, `washing` trägt hier NOUN, kein VERB. Ohne
    die Wortartprüfung am Kopf entstünde hier ein Scheinkandidat `washing up` (spaCy
    lemmatisiert das Gerundium als NOUN nicht auf `wash` zurück, nur als VERB)."""
    chapter = make_chapter("The washing up took forever after dinner.")
    expressions = extract_particle_verb_candidates(chapter, nlp)

    assert not has_mwe(expressions, "washing up")
    assert not has_mwe(expressions, "wash up")


# ------------------------------------------------------ extract_contiguous_candidates


def test_contiguous_candidates_finds_a_fixed_multiword_phrase(nlp: Language) -> None:
    """bauplan.md T4, n-Gramm-Weg: eine feste Wendung aus Funktionswörtern und einem
    Nomen (`out of the way`) wird als zusammenhängender Kandidat gefunden — genau die
    Wortarten, die `_CONTENT_POS` in `extract_vocabulary` ausschließt."""
    chapter = make_chapter("She quickly stepped out of the way of the carriage.")
    candidates = extract_contiguous_candidates(chapter, nlp)

    assert has_mwe(candidates, "out of the way")


def test_contiguous_candidates_normalize_to_the_lemma_not_the_surface_form(nlp: Language) -> None:
    """Befund 2, Review T4: Kandidaten werden auf die Grundform je Wort normalisiert
    (`token.lemma_.lower()`), weil WikDicts `written_rep` Wendungen selbst in der
    Grundform führt (`give up`, nicht `gave up`) — die Oberflächenform träfe nie."""
    chapter = make_chapter("He finally gave up his old plan.")
    candidates = extract_contiguous_candidates(chapter, nlp)

    give_up = find_mwe(candidates, "give up")
    assert give_up.word_form == "gave up"
    assert not has_mwe(candidates, "gave up")


def test_contiguous_candidates_do_not_cross_a_comma(nlp: Language) -> None:
    """Befund 2, Review T4: Kandidaten laufen nicht über Interpunktionsgrenzen — das
    Komma trennt „friend“ und „hoping“, ein Kandidat, der beide verbindet, darf nicht
    entstehen, während beide Seiten für sich weiter Kandidaten liefern."""
    chapter = make_chapter("He greeted his old friend, hoping for a quiet moment together.")
    candidates = extract_contiguous_candidates(chapter, nlp)

    assert not has_mwe(candidates, "friend hop")
    assert has_mwe(candidates, "old friend")
    assert has_mwe(candidates, "hop for")


def test_contiguous_candidates_do_not_cross_a_sentence_boundary(nlp: Language) -> None:
    """Befund 2, Review T4: Kandidaten laufen nicht über Satzgrenzen — der Punkt trennt
    „show“ vom folgenden Satz, ein Kandidat „show very“ darf nicht entstehen."""
    chapter = make_chapter("He saw the old show. Very quiet indeed today.")
    candidates = extract_contiguous_candidates(chapter, nlp)

    assert not has_mwe(candidates, "show very")
    assert has_mwe(candidates, "old show")
    assert has_mwe(candidates, "very quiet")


def test_contiguous_candidates_are_capped_at_the_measured_upper_bound(nlp: Language) -> None:
    """Befund 2, Review T4: Die Obergrenze ist gegen `tools/en-de.sqlite3` gemessen
    (99,12 % aller mehrwortigen `written_rep` mit `score ≥ 50` sind höchstens sechs
    Wörter lang, siehe `_MAX_EXPRESSION_LENGTH`) — ein zehn Wörter langer, durchgehend
    alphabetischer Lauf darf trotzdem keinen Kandidaten über sechs Wörtern erzeugen."""
    chapter = make_chapter("The old wooden ship sailed slowly across the calm harbor.")
    candidates = extract_contiguous_candidates(chapter, nlp)

    lengths = [len(c.lemma.text.split()) for c in candidates]
    assert lengths, "Testvoraussetzung verletzt: keine Kandidaten entstanden"
    assert max(lengths) == 6
    assert has_mwe(candidates, "the old wooden ship sail slowly")
    assert not has_mwe(candidates, "the old wooden ship sail slowly across")


def test_broken_pipeline_without_lemmatizer_aborts_the_contiguous_extraction(
    nlp_without_lemmatizer: Language,
) -> None:
    """Befund 1, Review T4: Wie die beiden anderen Funktionen dieses Moduls bricht auch
    `extract_contiguous_candidates` ohne Lemmatisierer sichtbar ab."""
    chapter = make_chapter("He finally gave up his old plan.")

    with pytest.raises(ValueError):
        extract_contiguous_candidates(chapter, nlp_without_lemmatizer)


def test_contiguous_candidates_scope_to_the_given_chapter(nlp: Language) -> None:
    """Wie bei den beiden anderen Extraktionsfunktionen: `book` und `chapter_number`
    gehören zum übergebenen `Chapter`, Häufigkeit zählt alle Vorkommen im Kapitel."""
    chapter = make_chapter("She stayed out of the way. He also stayed out of the way.", number=2)
    candidates = extract_contiguous_candidates(chapter, nlp)

    out_of_the_way = find_mwe(candidates, "out of the way")
    assert out_of_the_way.frequency == 2
    assert out_of_the_way.book == chapter.book
    assert out_of_the_way.chapter_number == 2


@pytest.mark.needs_dictionary
def test_contiguous_candidate_form_matches_written_rep_in_the_real_dictionary(
    nlp: Language, real_dictionary_path: Path
) -> None:
    """Hausordnungsregel (dokumentation.md §5, „Woran geprüft wird"): Die Behauptung,
    dass die lemmatisierte Kandidatenform auf WikDicts `written_rep` trifft, wird gegen
    die echte Datei geprüft, nicht nur gegen erfundene Beispiele im Docstring."""
    chapter = make_chapter("He decided to give up. She stayed out of the way after all, as a rule.")
    candidates = extract_contiguous_candidates(chapter, nlp)
    candidate_texts = {c.lemma.text for c in candidates}

    phrases = ("give up", "out of the way", "after all", "as a rule")
    con = sqlite3.connect(real_dictionary_path)
    try:
        written_reps = {
            phrase
            for phrase in phrases
            if con.execute(
                "SELECT 1 FROM translation WHERE lower(written_rep) = ? LIMIT 1", (phrase,)
            ).fetchone()
            is not None
        }
    finally:
        con.close()

    assert written_reps == set(phrases), (
        "Testvoraussetzung verletzt: nicht alle Vergleichsphrasen stehen in der echten Datei"
    )
    assert written_reps <= candidate_texts
