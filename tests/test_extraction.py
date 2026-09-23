"""Prüft `libreverbum/extraction.py` (bauplan.md T3, T4)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from libreverbum import epub, triage
from libreverbum.entities import Book, Chapter, Occurrence, ProperNounEntry
from libreverbum.extraction import (
    book_proper_noun_ratios,
    extract_contiguous_candidates,
    extract_particle_verb_candidates,
    extract_proper_noun_list,
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


@pytest.fixture(scope="module")
def nlp_without_ner() -> Language:
    """spaCy-Pipeline ohne Entitätserkennung — Testvorrichtung für `_require_ner`
    (bauplan-phase2.md AP 8, Regel 13, analog `nlp_without_lemmatizer`): `doc.ents` wäre
    sonst stets leer, statt den falsch geladenen `nlp` zu melden."""
    import spacy

    return spacy.load("en_core_web_md", exclude=["ner"])


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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    see = find(occurrences, "see", "VERB")
    assert see.frequency == 1
    assert see.word_form == "saw"
    assert not has_lemma(occurrences, "saw")


def test_rule_2_saw_as_noun_stays_the_tool(nlp: Language) -> None:
    """Gegenprobe zu Regel 2: Als Werkzeug bleibt `saw` bei der Grundform *saw*, weil
    die Wortart hier NOUN und nicht VERB ist — die Wortart entscheidet, nicht die
    Wortform allein."""
    chapter = make_chapter("He cut the plank in half with a rusty saw.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    red = find(occurrences, "red")
    # (mittel 1, Abnahme T17, 26.08.2026): frequency zählt nur das eine nicht-eigennamige
    # Vorkommen („a bright red") — das eigennamige („Mr. Red") steht separat in
    # proper_noun_frequency und geht in frequency nicht mehr mit ein.
    assert red.frequency == 1
    assert red.proper_noun_frequency == 1


def test_rule_12_a_name_that_never_occurs_as_an_ordinary_word_is_not_extracted(
    nlp: Language,
) -> None:
    """Regel 12 / Abnahmekriterium 2: Ein Wort, das ausschließlich als Eigenname
    vorkommt, wird gar nicht erst als Grundform geliefert — keine Figurennamen als
    Lernvokabeln."""
    chapter = make_chapter("Sherlock arrived at noon.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences_16 = extract_vocabulary(chapter_16, nlp).occurrences
    assert not has_lemma(occurrences_16, "dorian")

    # Gegenprobe im selben Buch: „lady" in Kapitel 17 hat einen Anteil von 0,80 (24 von
    # 30 Vorkommen PROPN) — als Anredesubstantiv bleibt es trotz des Eigennamenanteils
    # Lernvokabel, weil 0,80 unter der Schwelle von 0,90 liegt.
    reference_17 = next(c for c in structure.chapters if c.number == 17)
    chapter_17 = epub.read_chapter(path, structure.book, reference_17)
    occurrences_17 = extract_vocabulary(chapter_17, nlp).occurrences
    lady = find(occurrences_17, "lady")
    # (mittel 1, Abnahme T17, 26.08.2026): frequency zählt nur die 6 nicht-eigennamigen
    # Vorkommen, proper_noun_frequency die 24 eigennamigen („Lady Narborough") — vor der
    # Behebung stand hier noch 30 (die Summe beider).
    assert lady.proper_noun_frequency == 24
    assert lady.frequency == 6


@pytest.mark.needs_epub
def test_rule_12_book_wide_ratio_excludes_sibyl_in_chapter_10_but_keeps_an_address_noun(
    nlp: Language, real_epub_paths: dict[str, Path]
) -> None:
    """schwer 1, zweiter Anlauf (Abnahme T17, 26.08.2026): In `tools/dorian_gray.epub`
    Kapitel 10 vertaggt spaCy drei elliptische Ausrufe („Sibyl dead!", „Did Sibyl—?",
    „Sibyl!") als NOUN statt PROPN — Tagger-Fehler in Ein-Wort-Ausrufen, kein
    Sprachbefund. Der Anteil **dieses** Kapitels sinkt dadurch auf 13/16 = 0,81, unter die
    Schwelle aus dem ersten Anlauf (25.08.2026) — „Sibyl" blieb dort trotzdem Lernvokabel,
    mit ausgerechnet einem der drei Fehltaggings als Belegsatz. Der **buchweite** Anteil
    (`book_proper_noun_ratios`, über alle Kapitel von `tools/dorian_gray.epub`) liegt bei
    80/85 = 0,94 und hält „Sibyl" jetzt auch in Kapitel 10 draußen, ohne ein echtes
    Anredesubstantiv mitzureißen — geprüft an der echten Datei, nicht an einer
    nachgebauten Vorrichtung (dokumentation.md §5, „Woran geprüft wird")."""
    path = real_epub_paths["dorian_gray"]
    structure = epub.read_structure(path)

    chapters = []
    for reference in structure.chapters:
        try:
            chapters.append(epub.read_chapter(path, structure.book, reference))
        except ValueError:
            continue
    ratios = book_proper_noun_ratios(chapters, nlp)

    chapter_10 = next(c for c in chapters if c.number == 10)
    occurrences_10 = extract_vocabulary(chapter_10, nlp, book_proper_noun_ratios=ratios).occurrences
    assert not has_lemma(occurrences_10, "sibyl")

    # Gegenprobe im selben Buch, mit denselben buchweiten Werten angewendet: „lady" in
    # Kapitel 17 bleibt Lernvokabel — ihr buchweiter Anteil (60/74 = 0,81) liegt wie ihr
    # Anteil je Kapitel unter der Schwelle von 0,90.
    chapter_17 = next(c for c in chapters if c.number == 17)
    occurrences_17 = extract_vocabulary(chapter_17, nlp, book_proper_noun_ratios=ratios).occurrences
    lady = find(occurrences_17, "lady")
    # Dieselben Kapitel-17-Zählungen wie im ersten Test oben — die buchweite statt der
    # kapitelweiten Ratio entscheidet nur über Aufnahme oder Ausschluss der Grundform,
    # nicht über frequency/proper_noun_frequency selbst.
    assert lady.proper_noun_frequency == 24
    assert lady.frequency == 6


def test_book_proper_noun_ratios_reports_progress_once_per_chapter_with_a_fixed_total(
    nlp: Language,
) -> None:
    """Auftragstext vom 02.09.2026, Bauschritt 1/2 der Konsolenausgabe: `on_progress` wird
    nach jedem verarbeiteten Kapitel genau einmal mit (fertig, gesamt) aufgerufen — `done`
    wächst dabei aufsteigend von 1 bis `total`, `total` bleibt über den ganzen Lauf fest bei
    der Kapitelzahl des Buchs.

    Verfälschungsprobe: `on_progress` in die Token-Schleife statt in die Kapitel-Schleife
    verlegt (also je Token statt je Kapitel aufgerufen) ließ `len(reports) ==
    len(chapters)` rot werden — `reports` hatte danach die Zahl der Token, nicht die der
    Kapitel (mehrere hundert statt drei)."""
    chapters = [
        make_chapter("A quiet street at dusk.", number=1),
        make_chapter("Another calm street nearby.", number=2),
        make_chapter("A third street scene unfolds.", number=3),
    ]
    reports: list[tuple[int, int]] = []

    book_proper_noun_ratios(
        chapters, nlp, on_progress=lambda done, total: reports.append((done, total))
    )

    assert len(reports) == len(chapters)
    assert [done for done, _ in reports] == list(range(1, len(chapters) + 1))
    assert all(total == len(chapters) for _, total in reports)


# ----------------------------------------------------------- token_count (bauplan-phase2.md AP 6)


def test_token_count_counts_every_alphabetic_token_not_just_the_extracted_occurrences(
    nlp: Language,
) -> None:
    """bauplan-phase2.md AP 6, E5 Festlegung 1: `token_count` zählt jedes alphabetische
    Token des Kapitels (`token.is_alpha`), auch Funktionswörter und ganz eigennamige
    Grundformen, die `occurrences` gar nicht führt.

    Von Hand nachgerechnet an „Sherlock arrived at noon.": vier alphabetische Token
    (Sherlock, arrived, at, noon — der Punkt zählt nicht, `token.is_alpha` ist dafür
    `False`), aber nur zwei Occurrence-Einträge: „Sherlock" ist ganz eigennamig und fällt
    nach Regel 12 komplett weg (siehe
    `test_rule_12_a_name_that_never_occurs_as_an_ordinary_word_is_not_extracted` oben),
    „at" ist ADP und damit kein Inhaltswort (`_CONTENT_POS`) — bleiben „arrive" (VERB) und
    „noon" (NOUN), je Häufigkeit 1."""
    chapter = make_chapter("Sherlock arrived at noon.")

    result = extract_vocabulary(chapter, nlp)

    assert result.token_count == 4
    assert len(result.occurrences) == 2
    assert sum(o.frequency for o in result.occurrences) == 2


# Ein von spaCy unabhängiger Maßstab für „was der Leser auf der Seite als Wort liest":
# Buchstabenfolgen, die auch ein Bindestrich oder ein Apostroph zusammenhalten darf
# (`bell-pull`, `o'clock`) — Befund 1, Durchsicht 3e71fb8.
_READER_WORD_PATTERN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")


@pytest.mark.needs_epub
def test_token_count_is_at_least_the_summed_frequency_of_a_real_chapter(
    nlp: Language, real_epub_paths: dict[str, Path]
) -> None:
    """bauplan-phase2.md AP 6, Prüfung gegen das echte Gegenüber: An `tools/sherlock.epub`
    Kapitel 2 gilt `sum(frequency) <= token_count` (E5 Festlegung 1) — der Nenner zählt
    jedes alphabetische Token, `frequency` je Grundform nur deren nicht-eigennamige
    Vorkommen. Funktionswörter, ganz eigennamige Grundformen und jedes eigennamige
    Vorkommen bleiben in der Summe der `frequency`-Werte unberücksichtigt, tragen aber zu
    `token_count` bei — die Ungleichung kann deshalb nie in die andere Richtung kippen.

    Selbst nachgemessen (16.09.2026, `extract_vocabulary(chapter, nlp)` ohne
    `book_proper_noun_ratios` — den Rückfallweg, den `run_chapter` nie nimmt, Befund 2
    Durchsicht 3e71fb8): `sum(frequency)` = 3497, `token_count` = 8579.

    Verfälschungsprobe (bauplan-phase2.md AP 6): Nenner und Zähler vertauscht — assert
    result.token_count <= total_frequency — wird an diesem echten Kapitel rot.

    Befund 1 (Durchsicht 3e71fb8, mittel): Diese Ungleichung allein sichert den Nenner
    nicht zu — `token_count` dürfte bis auf 41 % seines echten Werts schrumpfen (3497 /
    8579 = 0,41), ohne dass diese Zusicherung anschlägt. Die zweite, engere Zusicherung
    unten schließt die Lücke mit einem von `extract_vocabulary` unabhängigen Maßstab."""
    structure = epub.read_structure(real_epub_paths["sherlock"])
    reference = structure.chapters[1]  # Kapitel 2, "A Scandal in Bohemia"
    chapter = epub.read_chapter(real_epub_paths["sherlock"], structure.book, reference)

    result = extract_vocabulary(chapter, nlp)

    total_frequency = sum(occurrence.frequency for occurrence in result.occurrences)
    assert total_frequency <= result.token_count

    # Befund 1 (Durchsicht 3e71fb8, mittel): spaCy-unabhängiger Maßstab statt der zu
    # schwachen Ungleichung oben — selbst nachgemessen: reader_words = 8542, token_count =
    # 8579, Verhältnis 1,0043, deutlich innerhalb ±5 %.
    #
    # Verfälschungsprobe (i), Pflicht: token_count nur über die ersten 60 % der Sätze
    # gezählt ergibt an diesem Kapitel 5374 (5374 / 8542 = 0,63) — wird rot.
    # Verfälschungsprobe (ii), Pflicht: token_count erst nach dem Inhaltswortfilter
    # gezählt — der Nenner, den E5 Festlegung 1 ausdrücklich verwirft — ergibt an diesem
    # echten Kapitel 3829 (3829 / 8542 = 0,45) und wird ebenfalls rot. Die alte, zu
    # schwache Ungleichung oben bliebe dabei unbemerkt grün (3497 <= 3829) — genau die
    # Lücke, die diese zweite Zusicherung schließt.
    reader_words = len(_READER_WORD_PATTERN.findall(chapter.text))
    assert 0.95 * reader_words <= result.token_count <= 1.05 * reader_words


def test_mittel_1_frequency_excludes_proper_noun_occurrences_and_reorders_the_ranking(
    nlp: Language,
) -> None:
    """mittel 1 (Abnahme T17, 26.08.2026): `frequency` zählt nur die nicht-eigennamigen
    Vorkommen — „count" tritt fünfmal als Teil des Anredenamens „Count Olaf" auf (PROPN)
    und nur einmal als gewöhnliches Verb („count the money"); vor der Behebung ging die
    Grundform mit `frequency == 6` in die Wortobergrenze ein (`triage.sort_by_frequency`)
    und verdrängte dabei „shadow" (dreimal, kein Eigennamenanteil) von Platz 1 auf Platz
    2. Nach der Behebung steht „count" mit `frequency == 1` hinter „shadow" — dieselbe
    Grundform bleibt Lernvokabel (Eigennamenanteil 5/6 = 0,83 unter der Schwelle 0,90),
    aber ihre angezeigte und für die Rangfolge verwendete Häufigkeit stimmt jetzt."""
    chapter = make_chapter(
        "Count Olaf glared at the children. Count Olaf smiled coldly. "
        "Count Olaf turned away. Count Olaf laughed once more. Count Olaf left the room. "
        "She paused to count the money twice before she spoke. "
        "A long shadow fell across the garden. Another shadow moved past the window. "
        "The shadow vanished into the dusk."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    count = find(occurrences, "count", "VERB")
    assert count.frequency == 1
    assert count.proper_noun_frequency == 5

    shadow = find(occurrences, "shadow", "NOUN")
    assert shadow.frequency == 3
    assert shadow.proper_noun_frequency == 0

    ordered = triage.sort_by_frequency(occurrences)
    ranked_lemmas = [o.lemma.text for o in ordered]
    assert ranked_lemmas.index("shadow") < ranked_lemmas.index("count"), (
        "shadow (frequency 3) müsste count (frequency 1 nach der Behebung) vorausgehen"
    )


# ------------------------------------------------------------- Inhaltswortfilter


def test_auxiliary_modal_and_gerund_forms_are_not_extracted(nlp: Language) -> None:
    """technik.md §5, offener Punkt: `could` und `having` (als Hilfsverb) werden vor
    dem Nachschlagen ausgesteuert, statt als Wörterbuchlücke zu erscheinen — beide sind
    Funktionswörter, die nie Lernvokabeln werden."""
    chapter = make_chapter(
        "He could not believe his eyes. Having finished the letter, she sealed the envelope."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    have = find(occurrences, "have", "VERB")
    assert have.word_form == "having"


def test_only_content_words_are_extracted_function_words_are_filtered_out(nlp: Language) -> None:
    """Nur Inhaltswörter kommen in die Wortliste (Review Runde 2, erlaubte statt
    Sperrliste): Artikel, Pronomen, Präpositionen und Hilfsverben fehlen, obwohl sie im
    Satz stehen — die Inhaltswörter desselben Satzes stehen dagegen alle drin. Ein Test,
    der nur die Abwesenheit prüfte, wäre auch bei einer leeren Liste grün."""
    chapter = make_chapter("The dog was quickly chased by his loyal friend.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    watch = find(occurrences, "watch", "NOUN")
    assert watch.word_form == "watch"
    assert watch.example_sentence == "She bought a new watch."


def test_pos_resolution_tie_is_broken_by_first_seen_pos(nlp: Language) -> None:
    """Moduldocstring, Abschnitt „Regeln", Gleichstand: je ein VERB- und ein
    NOUN-Vorkommen von `watch` — die zuerst gesehene Wortart gewinnt, hier VERB."""
    chapter = make_chapter("They wanted to watch the game. He checked his watch.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    watch = find(occurrences, "watch", "VERB")
    assert watch.word_form == "watched"
    assert watch.example_sentence == "Then he watched the door."


# ------------------------------------------------------ Wendungsbeteiligung im Belegsatz


def test_expression_free_occurrence_is_preferred_for_the_example_sentence(nlp: Language) -> None:
    """T17-Nachbesserung (Ursache A, 26.08.2026): Von zwei Vorkommen derselben Grundform
    wird das wendungsfreie für Wortform und Belegsatz gewählt, auch wenn das
    wendungsbeteiligte zuerst im Kapitel steht — sonst zeigt der Belegsatz eine
    Redewendung („taken part"), während die Auswahlliste nur Bedeutungen des Einzelworts
    „take" enthält (dorian_gray.epub Kapitel 10, Auftragstext Ursache A)."""
    chapter = make_chapter(
        "She had taken part in the play. Yesterday she decided to take a long walk."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    take = find(occurrences, "take", "VERB")
    assert take.word_form == "take"
    assert take.example_sentence == "Yesterday she decided to take a long walk."


def test_falls_back_to_a_wendung_occurrence_when_none_is_free(nlp: Language) -> None:
    """Gegenprobe: Sind alle Vorkommen einer Grundform wendungsbeteiligt, weicht die Wahl
    auf das erste davon aus, statt eine Grundform ganz zu verlieren — „taken part" und
    „took heart" sind beides unbestimmte Akkusativobjekte ohne eigenes Kind-Token."""
    chapter = make_chapter(
        "She had taken part in the play. Then she quickly took heart and continued."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    take = find(occurrences, "take", "VERB")
    assert take.word_form == "taken"
    assert take.example_sentence == "She had taken part in the play."


def test_running_late_keeps_its_belegsatz(nlp: Language) -> None:
    """Gegenprobe zur Partikelliste (`_EXPRESSION_PARTICLE_WORDS`): „late" ist ein
    gewöhnliches Adverb, keine Phrasal-Verb-Partikel — ohne die geschlossene Liste träfe
    die advmod-Regel auch hier zu und risse den bislang richtigen Belegsatz aus
    `test_inflected_forms_are_merged_into_one_entry_with_combined_frequency` mit."""
    chapter = make_chapter("She was running late. He runs every morning.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    run = find(occurrences, "run", "VERB")
    assert run.word_form == "running"
    assert run.example_sentence == "She was running late."


def test_preposition_with_a_bare_pronoun_object_counts_as_an_expression(nlp: Language) -> None:
    """T17-Nachbesserung (mittel 3, zweiter Anlauf, 26.08.2026): „to" in „came to him" hat
    mit „him" ein eigenes Kind-Token und bestand die alte, pauschale Bareness-Prüfung
    deshalb nicht (`_is_bare`), obwohl ein bloßes Personalpronomen den idiomatischen
    Charakter der Wortfolge nicht ändert — „come to" (zu sich kommen) ist eine andere
    Bedeutung als das bloße Verb „come". Von zwei Vorkommen wird das wendungsfreie für den
    Belegsatz gewählt, obwohl das wendungsbeteiligte zuerst im Kapitel steht (wie bei
    `test_expression_free_occurrence_is_preferred_for_the_example_sentence`)."""
    chapter = make_chapter(
        "A dim sense of the danger came to him once or twice. "
        "Yesterday she decided to come early instead."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    come = find(occurrences, "come", "VERB")
    assert come.example_sentence == "Yesterday she decided to come early instead."


def test_preposition_with_a_real_noun_object_is_not_mistaken_for_an_expression(
    nlp: Language,
) -> None:
    """Gegenprobe: Ein echtes Objekt mit eigenem Inhalt ändert daran nichts — „into" in
    „went into the library" bleibt frei, weil „library" kein bloßes Personalpronomen ist
    (Kind „the" an „library"). Erste Vorkommen ist das wendungsbeteiligte („into it"),
    zweites das freie — die Wahl muss also tatsächlich unterscheiden, nicht einfach das
    erste Vorkommen nehmen."""
    chapter = make_chapter("He went into it. He also went into the library.")
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    go = find(occurrences, "go", "VERB")
    assert go.example_sentence == "He also went into the library."


def test_looked_at_him_is_an_expression_but_looked_at_the_painting_is_not(nlp: Language) -> None:
    """Zweites Beispiel aus dem Auftrag: „at" in „looked at him" — dieselbe
    Pronomen-Ausnahme wie bei „come to him" oben, an einer anderen Präposition und einem
    anderen Verb geprüft."""
    chapter = make_chapter(
        "Dorian looked at him for a moment. Later she looked at the old painting."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    look = find(occurrences, "look", "VERB")
    assert look.example_sentence == "Later she looked at the old painting."


# ---------------------------------------------------------- Häufigkeit und Belegsatz


def test_inflected_forms_are_merged_into_one_entry_with_combined_frequency(nlp: Language) -> None:
    """Abnahmekriterium 2: Beugungsformen sind in der Wortliste zusammengefasst —
    `running`, `runs` und `ran` ergeben eine Grundform *run* mit Häufigkeit 3."""
    chapter = make_chapter(
        "She was running late. He runs every morning. They ran together yesterday."
    )
    occurrences = extract_vocabulary(chapter, nlp).occurrences

    run = find(occurrences, "run", "VERB")
    assert run.frequency == 3
    assert run.word_form == "running"
    assert run.example_sentence == "She was running late."


def test_frequency_and_example_sentence_are_scoped_to_the_given_chapter(nlp: Language) -> None:
    """Häufigkeit und Belegsatz gehören zum übergebenen Kapitel — `book` und
    `chapter_number` auf dem `Occurrence` stammen aus dem `Chapter`-Argument."""
    chapter = make_chapter("The dog barked twice. The dog ran across the street.", number=3)
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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
    occurrences = extract_vocabulary(chapter, nlp).occurrences

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

    vocabulary = extract_vocabulary(chapter, nlp).occurrences
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


# -------------------------------------------------------- extract_proper_noun_list (AP 8)


def find_proper_noun(entries: list[ProperNounEntry], text: str) -> ProperNounEntry:
    matches = [entry for entry in entries if entry.text == text]
    assert len(matches) == 1, f"{text!r} genau einmal erwartet, {len(matches)}-mal gefunden"
    return matches[0]


def has_proper_noun_text(entries: list[ProperNounEntry], text: str) -> bool:
    return any(entry.text == text for entry in entries)


@pytest.mark.needs_epub
def test_acceptance_ap8_sherlock_chapter_2_lists_the_figures_and_places_but_not_the_title(
    nlp: Language, real_epub_paths: dict[str, Path]
) -> None:
    """bauplan-phase2.md AP 8, Prüfung: Gegen `tools/sherlock.epub` Kapitel 2 enthält die
    Liste „Sherlock Holmes"/„Holmes", „Irene Adler" und „Bohemia", aber nicht „Miss"
    (Regel 12, „miss" ist Lernvokabel).

    Verfälschungsprobe: Grundform statt Oberflächenform (`token.lemma_` je Token der
    Entitätsspanne statt `ent.text`) verwandelt „Holmes" in „holme" — spaCys
    Lemmatisierer behandelt die Endung „-es" wie bei einem regelmäßigen Plural
    („boxes" → „box"). Mit dieser Verfälschung schlägt `assert has_proper_noun_text(...,
    "Holmes")` fehl, weil die Liste nur noch „holme" enthält."""
    path = real_epub_paths["sherlock"]
    structure = epub.read_structure(path)
    reference = next(c for c in structure.chapters if c.number == 2)
    chapter = epub.read_chapter(path, structure.book, reference)

    entries = extract_proper_noun_list(chapter, nlp)
    texts = {entry.text for entry in entries}

    assert "Holmes" in texts
    assert "Sherlock Holmes" in texts
    assert "Irene Adler" in texts
    assert "Bohemia" in texts
    assert not any("Miss" in text for text in texts)


@pytest.mark.needs_epub
def test_acceptance_ap8_holmes_and_irene_adler_carry_their_surface_frequency(
    nlp: Language, real_epub_paths: dict[str, Path]
) -> None:
    """Ergänzung zur Abnahmeprüfung: `frequency` zählt die Vorkommen der jeweiligen
    Oberflächenform, nicht bloß eine feste Zahl (Rezept: gezählt gegen
    tools/sherlock.epub Kapitel 2, siehe Bericht zu diesem Arbeitspaket — „Holmes" 37,
    „Sherlock Holmes" 7, „Irene Adler" 11 Vorkommen)."""
    path = real_epub_paths["sherlock"]
    structure = epub.read_structure(path)
    reference = next(c for c in structure.chapters if c.number == 2)
    chapter = epub.read_chapter(path, structure.book, reference)

    entries = extract_proper_noun_list(chapter, nlp)

    assert find_proper_noun(entries, "Holmes").frequency == 37
    assert find_proper_noun(entries, "Sherlock Holmes").frequency == 7
    assert find_proper_noun(entries, "Irene Adler").frequency == 11


def test_proper_noun_occurrences_of_the_same_surface_form_are_merged_into_one_entry(
    nlp: Language,
) -> None:
    """Mehrere Vorkommen derselben Oberflächenform im Kapitel werden zu einem Eintrag
    zusammengezählt (Moduldocstring, „extract_proper_noun_list").

    Verfälschungsprobe: Zusammenführung entfernt (jedes `doc.ents`-Vorkommen wird ein
    eigener Eintrag) lässt `len(entries) == 1` rot werden — zwei Einträge mit
    `frequency == 1` statt einem mit `frequency == 2`."""
    chapter = make_chapter(
        "Sherlock Holmes walked to Baker Street. Sherlock Holmes then returned home."
    )
    entries = extract_proper_noun_list(chapter, nlp)

    matches = [entry for entry in entries if entry.text == "Sherlock Holmes"]
    assert len(matches) == 1
    assert matches[0].frequency == 2


def test_proper_noun_list_excludes_entity_types_outside_person_gpe_loc_fac(nlp: Language) -> None:
    """Nur die vier vermuteten Entitätstypen zählen (`extraction._PROPER_NOUN_ENTITY_TYPES`)
    — ein `DATE`-Vorkommen wie „Yesterday" erscheint nicht in der Liste, während „London"
    (GPE) und „Sherlock Holmes" (PERSON) im selben Satz erscheinen.

    Verfälschungsprobe: `_PROPER_NOUN_ENTITY_TYPES` um `DATE` erweitert lässt
    `not has_proper_noun_text(entries, "Yesterday")` rot werden."""
    chapter = make_chapter("Yesterday, Sherlock Holmes visited London.")
    entries = extract_proper_noun_list(chapter, nlp)

    assert not has_proper_noun_text(entries, "Yesterday")
    assert has_proper_noun_text(entries, "London")
    assert has_proper_noun_text(entries, "Sherlock Holmes")


def test_proper_noun_list_keeps_the_original_capitalization_not_a_lowercased_lemma(
    nlp: Language,
) -> None:
    """Die Liste trägt die Oberflächenform, keine kleingeschriebene Grundform — anders
    als `extract_vocabulary`s `Lemma.text` (Regel 12: Grundformen werden dort
    kleingeschrieben; hier ausdrücklich nicht, siehe Moduldocstring)."""
    chapter = make_chapter("Watson followed Holmes to Baker Street.")
    entries = extract_proper_noun_list(chapter, nlp)

    assert has_proper_noun_text(entries, "Holmes")
    assert not has_proper_noun_text(entries, "holmes")


def test_proper_noun_list_order_matches_first_occurrence_in_the_chapter(nlp: Language) -> None:
    """Reihenfolge wie bei `extract_vocabulary`s `occurrences`: erstes Auftreten im
    Kapitel, unsortiert (Moduldocstring)."""
    chapter = make_chapter("Watson met Holmes near Baker Street. Later, Holmes met Watson again.")
    entries = extract_proper_noun_list(chapter, nlp)
    texts = [entry.text for entry in entries]

    assert texts.index("Watson") < texts.index("Holmes") < texts.index("Baker Street")


def test_proper_noun_list_scopes_to_the_given_chapter(nlp: Language) -> None:
    """Wie bei den Wortlisten-Extraktionsfunktionen: `book` und `chapter_number` gehören
    zum übergebenen `Chapter` (Moduldocstring, „Ein Eintrag je Kapitel und
    Oberflächenform" — `entities.ProperNounEntry`)."""
    chapter = make_chapter("Holmes walked down Baker Street.", number=5)
    entries = extract_proper_noun_list(chapter, nlp)

    holmes = find_proper_noun(entries, "Holmes")
    assert holmes.book == chapter.book
    assert holmes.chapter_number == 5


def test_broken_pipeline_without_ner_aborts_the_proper_noun_extraction(
    nlp_without_ner: Language,
) -> None:
    """Regel 13 (bauplan-phase2.md AP 8, `_require_ner`): Fehlt die Entitätserkennung,
    bricht die Extraktion sichtbar ab, statt eine leere Liste als vollständiges Ergebnis
    auszugeben — analog `test_broken_pipeline_without_lemmatizer_aborts_instead_of_
    silently_using_surface_forms`."""
    chapter = make_chapter("Sherlock Holmes walked to Baker Street.")

    with pytest.raises(ValueError):
        extract_proper_noun_list(chapter, nlp_without_ner)
