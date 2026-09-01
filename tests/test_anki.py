"""Prüft `libreverbum/anki.py` — bauplan.md T13, Deck-Export samt stabiler GUID."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from libreverbum import anki, printout
from libreverbum.entities import Book, Card, CardDirection, Lemma, Occurrence, Sense


def _book(*, title: str = "Testbuch", author: str = "A. C. Doyle") -> Book:
    return Book(title=title, author=author)


def _occurrence(
    *,
    book: Book | None = None,
    chapter_number: int = 3,
    lemma_text: str = "watch",
    lemma_pos: str = "NOUN",
    word_form: str = "watch",
    example_sentence: str = "He checked his watch before leaving the house.",
    frequency: int = 4,
) -> Occurrence:
    return Occurrence(
        book=book or _book(),
        chapter_number=chapter_number,
        lemma=Lemma(text=lemma_text, pos=lemma_pos),
        word_form=word_form,
        example_sentence=example_sentence,
        frequency=frequency,
        proper_noun_frequency=0,
    )


def _sense(
    occurrence: Occurrence,
    *,
    translation: str | None = "Uhr | Armbanduhr",
    wikdict_sense: str | None = "a small timepiece",
    wikdict_lexentry: str | None = None,
    uncertain: bool = False,
) -> Sense:
    return Sense(
        lemma=occurrence.lemma,
        translation=translation,
        wikdict_sense=wikdict_sense,
        wikdict_trans_list=translation,
        wikdict_lexentry=wikdict_lexentry or f"eng/{occurrence.lemma.text}__Noun__1",
        uncertain=uncertain,
    )


def _card(
    occurrence: Occurrence,
    *,
    direction: CardDirection = CardDirection.EN_DE,
    translation: str | None = "Uhr | Armbanduhr",
    wikdict_sense: str | None = "a small timepiece",
    wikdict_lexentry: str | None = None,
    uncertain: bool = False,
    guid: str | None = None,
) -> Card:
    sense = _sense(
        occurrence,
        translation=translation,
        wikdict_sense=wikdict_sense,
        wikdict_lexentry=wikdict_lexentry,
        uncertain=uncertain,
    )
    return Card(
        sense=sense,
        occurrence=occurrence,
        card_direction=direction,
        guid=guid if guid is not None else anki.new_card_guid(occurrence, sense, direction),
    )


def _placeholder_card(
    occurrence: Occurrence, *, direction: CardDirection = CardDirection.EN_DE
) -> Card:
    """Eine Karte auf dem **echten** Platzhalter eines Wortes ohne Wörterbucheintrag
    (Befund leicht 5, Durchsicht 35736a9): `Sense(lemma=…, uncertain=True)` ohne jedes
    `wikdict_`-Feld, genau wie `pipeline.run_chapter` ihn für eine leere Auswahlliste und
    `dictionary.particle_verb_candidates` ihn für ein Phrasal Verb ohne Treffer einsetzt.

    `_card(translation=None, uncertain=True)` behielte `wikdict_sense` und
    `wikdict_lexentry` und wäre damit kein Wort ohne Wörterbucheintrag, sondern eines mit
    Eintrag und ohne Übersetzung — ein Fall, den es so nicht gibt. Dieselbe Form baut
    `tests/test_cli_export.py`."""
    sense = Sense(lemma=occurrence.lemma, uncertain=True)
    return Card(
        sense=sense,
        occurrence=occurrence,
        card_direction=direction,
        guid=anki.new_card_guid(occurrence, sense, direction),
    )


@contextmanager
def _open_collection(path: Path) -> Iterator[sqlite3.Connection]:
    """Öffnet `collection.anki2` aus einer erzeugten `.apkg`-Datei **erneut** — die vom
    Auftrag verlangte Prüfung „die Datei wieder aufmachen", nicht genankis Rückgabewerte
    gegen sich selbst halten."""
    with zipfile.ZipFile(path) as archive:
        collection_bytes = archive.read("collection.anki2")
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as handle:
        handle.write(collection_bytes)
        collection_path = Path(handle.name)
    con = sqlite3.connect(collection_path)
    try:
        yield con
    finally:
        con.close()
        collection_path.unlink()


def _notes(path: Path) -> list[dict[str, Any]]:
    with _open_collection(path) as con:
        rows = con.execute("SELECT guid, mid, tags, flds FROM notes ORDER BY id").fetchall()
    return [
        {"guid": guid, "mid": mid, "tags": tags.strip().split(), "fields": flds.split("\x1f")}
        for guid, mid, tags, flds in rows
    ]


def _col(path: Path) -> dict[str, Any]:
    with _open_collection(path) as con:
        models_json, decks_json = con.execute("SELECT models, decks FROM col").fetchone()
    return {"models": json.loads(models_json), "decks": json.loads(decks_json)}


def test_export_deck_writes_a_readable_apkg_with_the_given_fields_and_tags(tmp_path: Path) -> None:
    """Abnahmekriterium 4: Das erzeugte Deck importiert sich in Anki fehlerfrei, Felder
    und Verschlagwortung sitzen richtig — hier geprüft, indem die Datei als ZIP wieder
    aufgemacht wird, mit den Feldern aus konzept.md §6: Wort, Grundform, Übersetzung,
    Wortart, Belegsatz, Buch, Kapitel."""
    occurrence = _occurrence()
    card = _card(occurrence)
    path = tmp_path / "deck.apkg"

    anki.export_deck(path, [card], deck_name="Testbuch, Kapitel 3")

    notes = _notes(path)
    assert len(notes) == 1
    note = notes[0]
    assert note["guid"] == card.guid
    assert note["fields"] == [
        "watch",
        "Uhr | Armbanduhr",
        "watch",
        "NOUN",
        "He checked his watch before leaving the house.",
        "Testbuch",
        "3",
    ]
    assert set(note["tags"]) == {"buch::Testbuch", "autor::A._C._Doyle", "kapitel::3"}


def test_pos_display_shows_mwe_for_an_empty_word_class() -> None:
    """`anki.pos_display`: eine leere Wortart (Mehrwortausdruck ohne Einzelwortart,
    `extraction._NO_SINGLE_POS`) wird als „MWE" angezeigt, eine echte Wortart bleibt
    unverändert."""
    assert anki.pos_display("") == "MWE"
    assert anki.pos_display("VERB") == "VERB"


def test_export_deck_shows_mwe_instead_of_an_empty_word_class_field(tmp_path: Path) -> None:
    """mittel 4 (Abnahme T17, 25.08.2026): Eine Wendung aus
    `extraction.extract_contiguous_candidates` trägt keine Einzelwortart (leerer String)
    — das Kartenfeld „Wortart" zeigte dafür bisher ein leeres Feld, die Kartenrückseite
    („{{Grundform}} ({{Wortart}})") also „… ()". `_fields` verwendet jetzt dieselbe
    Anzeige wie `cli.interaction` auf dem Bildschirm (`anki.pos_display`, „MWE")."""
    occurrence = _occurrence(lemma_text="give up", lemma_pos="", word_form="gave up")
    card = _card(occurrence)
    path = tmp_path / "deck.apkg"

    anki.export_deck(path, [card], deck_name="Testbuch, Kapitel 3")

    note = _notes(path)[0]
    assert note["fields"][3] == "MWE"


def test_special_characters_in_the_example_sentence_are_html_escaped(tmp_path: Path) -> None:
    """Der Belegsatz kommt aus dem Buchtext (CLAUDE.md) und kann `&`, `<` oder `>`
    enthalten — unescaped bräche das die Feld-Darstellung in Anki."""
    occurrence = _occurrence(example_sentence="Smith & Sons watch <the> shop.")
    card = _card(occurrence)
    path = tmp_path / "deck.apkg"

    anki.export_deck(path, [card], deck_name="HTML-Test")

    fields = _notes(path)[0]["fields"]
    assert fields[4] == "Smith &amp; Sons watch &lt;the&gt; shop."


def test_cloze_card_wraps_the_word_form_as_a_cloze_deletion(tmp_path: Path) -> None:
    """konzept.md §6, „Export": Lückentext mit dem Originalsatz aus dem Buch — die
    Wortform wird im Belegsatz zur Cloze-Lücke `{{c1::…}}`."""
    occurrence = _occurrence(
        word_form="watch", example_sentence="He checked his watch before leaving."
    )
    card = _card(occurrence, direction=CardDirection.CLOZE)
    path = tmp_path / "cloze.apkg"

    anki.export_deck(path, [card], deck_name="Cloze-Test")

    fields = _notes(path)[0]["fields"]
    assert fields[0] == "He checked his {{c1::watch}} before leaving."


def test_cloze_does_not_take_a_partial_word_match(tmp_path: Path) -> None:
    """Befund 4, Review T13: `sentence.find` trifft die erste Zeichenkette, nicht das
    Wort — `watch` in „The watchman watched his watch." darf weder `watchman` noch
    `watched` treffen, nur das eigenständige `watch` am Satzende."""
    occurrence = _occurrence(word_form="watch", example_sentence="The watchman watched his watch.")
    card = _card(occurrence, direction=CardDirection.CLOZE)
    path = tmp_path / "cloze.apkg"

    anki.export_deck(path, [card], deck_name="Teilwort-Test")

    fields = _notes(path)[0]["fields"]
    assert fields[0] == "The watchman watched his {{c1::watch}}."


def test_cloze_matches_a_word_form_containing_an_apostrophe(tmp_path: Path) -> None:
    """Befund 4, Review T13: Die Wortform kann aus dem Buchtext einen Apostroph
    mitbringen (`don't`) — die Wortgrenzenprüfung darf sie deshalb nicht verwerfen."""
    occurrence = _occurrence(word_form="don't", example_sentence="I don't know what to say.")
    card = _card(occurrence, direction=CardDirection.CLOZE)
    path = tmp_path / "cloze.apkg"

    anki.export_deck(path, [card], deck_name="Apostroph-Test")

    fields = _notes(path)[0]["fields"]
    assert fields[0] == "I {{c1::don't}} know what to say."


def test_cloze_word_form_only_as_a_partial_match_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): Kommt die Wortform im Belegsatz nur als Teil
    eines anderen Wortes vor — nie an einer Wortgrenze —, bricht der Export sichtbar ab,
    statt den Teilworttreffer stillschweigend zu übernehmen (Befund 4, Review T13)."""
    occurrence = _occurrence(word_form="cat", example_sentence="The category is unclear.")
    card = _card(occurrence, direction=CardDirection.CLOZE)

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [card], deck_name="Fehlerfall")


def test_card_direction_selects_a_different_note_model(tmp_path: Path) -> None:
    """konzept.md §6, „Export": Kartenrichtung ist je Export wählbar — EN_DE fragt das
    Wort ab, DE_EN die Übersetzung, mit je eigener Kartenvorlage."""
    occurrence = _occurrence()
    en_de = _card(occurrence, direction=CardDirection.EN_DE)
    de_en = _card(occurrence, direction=CardDirection.DE_EN)
    path_en_de = tmp_path / "en_de.apkg"
    path_de_en = tmp_path / "de_en.apkg"

    anki.export_deck(path_en_de, [en_de], deck_name="EN-DE")
    anki.export_deck(path_de_en, [de_en], deck_name="DE-EN")

    qfmt_en_de = next(iter(_col(path_en_de)["models"].values()))["tmpls"][0]["qfmt"]
    qfmt_de_en = next(iter(_col(path_de_en)["models"].values()))["tmpls"][0]["qfmt"]

    assert qfmt_en_de == "{{Wort}}"
    assert qfmt_de_en == "{{Übersetzung}}"


def test_guid_stays_the_same_after_a_corrected_translation(tmp_path: Path) -> None:
    """Regel 6 (dokumentation.md §4): Anki-GUID beim Export in `card` mitschreiben — und
    sie muss über eine korrigierte Übersetzung hinweg **dieselbe** bleiben. Sonst legt
    Anki beim nächsten Import eine zweite Notiz an, und der Lernfortschritt der alten
    hängt an einer Karteileiche (T13-Auftrag, „Der Befund, der T13 formt")."""
    occurrence = _occurrence()
    direction = CardDirection.EN_DE
    guid = anki.new_card_guid(occurrence, _sense(occurrence), direction)

    original = _card(occurrence, direction=direction, translation="ziehen", guid=guid)
    corrected = _card(occurrence, direction=direction, translation="skizzieren", guid=guid)

    path_before = tmp_path / "vorher.apkg"
    path_after = tmp_path / "nachher.apkg"
    anki.export_deck(path_before, [original], deck_name="Stabilitätstest")
    anki.export_deck(path_after, [corrected], deck_name="Stabilitätstest")

    note_before = _notes(path_before)[0]
    note_after = _notes(path_after)[0]
    assert note_before["fields"][1] != note_after["fields"][1]  # Übersetzung hat sich geändert
    assert note_before["guid"] == note_after["guid"]


def test_new_card_guid_stays_the_same_when_word_form_sentence_or_frequency_change() -> None:
    """Regel 6: Die GUID hängt nicht an `word_form`, `example_sentence` oder `frequency`
    — nur an Buch, Kapitel, Grundform, Bedeutung und Kartenrichtung (Befund 6, Review
    T13). Ein Belegsatzwechsel oder eine neu gezählte Häufigkeit dürfen keine zweite
    Notiz erzeugen."""
    base = _occurrence()
    changed = _occurrence(
        word_form="watches",
        example_sentence="A completely different sentence about something else.",
        frequency=99,
    )
    sense = _sense(base)

    assert anki.new_card_guid(base, sense, CardDirection.EN_DE) == anki.new_card_guid(
        changed, sense, CardDirection.EN_DE
    )


def test_new_card_guid_differs_for_different_chapters_lemmas_and_directions() -> None:
    """Regel 6: Der Schlüssel unterscheidet, was verschiedene Karten sind — anders als
    `Sense` (T13-Auftrag, „Der Schlüssel darf nicht die Identität von Sense sein"), aber
    nicht so grob, dass unterschiedliche Karten dieselbe GUID trügen."""
    base = _occurrence()
    guid = anki.new_card_guid(base, _sense(base), CardDirection.EN_DE)

    other_chapter = _occurrence(chapter_number=4)
    other_lemma = _occurrence(lemma_text="draw", word_form="draw")

    assert anki.new_card_guid(other_chapter, _sense(other_chapter), CardDirection.EN_DE) != guid
    assert anki.new_card_guid(other_lemma, _sense(other_lemma), CardDirection.EN_DE) != guid
    assert anki.new_card_guid(base, _sense(base), CardDirection.DE_EN) != guid


def test_new_card_guid_differs_for_different_senses_of_the_same_occurrence() -> None:
    """Befund 1, Review T13: technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung,
    nicht pro Wort" — zwei Karten auf derselben `Occurrence` mit zwei verschiedenen
    `Sense` (etwa `watch` als „Uhr" und als „Wache") bekommen verschiedene GUIDs. Sonst
    überschriebe der Import der zweiten Bedeutung die Notiz der ersten, und
    `profile.compare_chapter_vocabulary`s `NEW_MEANING_OF_KNOWN_WORD` hätte keine eigene
    Karte."""
    occurrence = _occurrence()
    direction = CardDirection.EN_DE
    first_sense = _sense(
        occurrence, wikdict_sense="a small timepiece", wikdict_lexentry="eng/watch__Noun__1"
    )
    second_sense = _sense(
        occurrence, wikdict_sense="a period of guard duty", wikdict_lexentry="eng/watch__Noun__2"
    )

    assert anki.new_card_guid(occurrence, first_sense, direction) != anki.new_card_guid(
        occurrence, second_sense, direction
    )


def test_export_deck_rejects_duplicate_guids_within_one_export(tmp_path: Path) -> None:
    """Befund 2, Review T13: `genanki` prüft Doppel-GUIDs innerhalb eines Exports selbst
    nicht — `export_deck` bricht deshalb sichtbar ab (Regel 13), statt die zweite Notiz
    erst beim Import in Anki lautlos verschwinden zu lassen."""
    occurrence = _occurrence()
    guid = anki.new_card_guid(occurrence, _sense(occurrence), CardDirection.EN_DE)
    first = _card(occurrence, guid=guid)
    duplicate = _card(_occurrence(chapter_number=4), guid=guid)

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [first, duplicate], deck_name="Fehlerfall")


def test_a_card_with_an_uncertain_sense_gets_a_visible_tag(tmp_path: Path) -> None:
    """`dictionary.py` (Zeilen 93-103) verlangt, dass eine unbestätigte Bedeutung „vor
    der Anzeige (T11, T13)" sichtbar wird (Befund 3, Review T13) — hier als eigener Tag,
    kein stiller Durchgang trotz `sense.uncertain=True` und gesetzter Übersetzung."""
    occurrence = _occurrence()
    card = _card(occurrence, uncertain=True)
    path = tmp_path / "deck.apkg"

    anki.export_deck(path, [card], deck_name="Unsicher-Test")

    assert "unsicher" in _notes(path)[0]["tags"]


def test_repeated_export_with_the_same_deck_name_reuses_the_same_deck(tmp_path: Path) -> None:
    """Ein zweiter Export desselben Decknamens trifft in Anki denselben Stapel, nicht
    einen weiteren — dieselbe Überlegung wie bei der Karten-GUID (Regel 6), hier auf
    Deck-Ebene statt auf Kartenebene."""
    occurrence = _occurrence()
    card = _card(occurrence)
    path_first = tmp_path / "erster.apkg"
    path_second = tmp_path / "zweiter.apkg"

    anki.export_deck(path_first, [card], deck_name="Immer derselbe Stapel")
    anki.export_deck(path_second, [card], deck_name="Immer derselbe Stapel")

    assert set(_col(path_first)["decks"].keys()) == set(_col(path_second)["decks"].keys())


def test_missing_word_form_in_the_example_sentence_is_a_visible_failure_for_cloze(
    tmp_path: Path,
) -> None:
    """Regel 13 (dokumentation.md §4): Kein stiller Lückentext ohne Lücke — fehlt die
    Wortform wortwörtlich im Belegsatz, bricht der Export sichtbar ab."""
    occurrence = _occurrence(word_form="watch", example_sentence="Er sah auf die Uhr.")
    card = _card(occurrence, direction=CardDirection.CLOZE)

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [card], deck_name="Fehlerfall")


def test_unresolved_translation_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13: Eine Karte ohne aufgelöste Übersetzung (`sense.translation is None`) und
    **ohne** die Marke `uncertain` bricht den Export sichtbar ab statt eines leeren
    Feldes — der zweite der drei Fälle aus `anki._translation_text`: ein echter Fehlschlag
    der Vorstufe, nicht ein Wort ohne Wörterbucheintrag."""
    occurrence = _occurrence()
    card = _card(occurrence, translation=None)

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [card], deck_name="Fehlerfall")


@pytest.mark.parametrize("direction", [CardDirection.EN_DE, CardDirection.CLOZE])
def test_an_uncertain_card_without_translation_carries_a_german_mark_instead_of_failing(
    tmp_path: Path, direction: CardDirection
) -> None:
    """Ein Wort ohne Wörterbucheintrag (`uncertain=True`, `translation is None`) kommt ins
    Deck, mit einer deutschen Textmarke im Feld „Übersetzung" und dem Tag `unsicher` —
    kein Abbruch (konzept.md §5: „wird der Eintrag **markiert** statt still
    durchgereicht"; dieselbe Unterscheidung wie `printout.py`, „Wie mit uncertain
    verfahren wird"). Das Feld steht in beiden Kartenvorlagen an zweiter Stelle
    (`_SHARED_FIELDS`, `_CLOZE_FIELDS`).

    Gemeldet am 01.09.2026 aus einem Kapiteldurchlauf: Ein einziges „lernen" auf einem
    solchen Wort ließ den gesamten Export scheitern, Deck **und** Druckseite. Bis zu 9 von
    25 gezeigten Einträgen tragen nur diesen Platzhalter (technik.md §11, „Warum C2 nicht
    angeboten wird")."""
    card = _placeholder_card(_occurrence(), direction=direction)
    path = tmp_path / "deck.apkg"

    anki.export_deck(path, [card], deck_name="Unsicher")

    note = _notes(path)[0]
    assert note["fields"][1] == "unsicher – kein Wörterbucheintrag"
    assert "unsicher" in note["tags"]


def test_an_uncertain_card_without_translation_is_a_visible_failure_for_de_en(
    tmp_path: Path,
) -> None:
    """Regel 13: In Kartenrichtung `DE_EN` steht das Feld „Übersetzung" auf der
    **Vorderseite** (`anki._DE_EN_MODEL`, `qfmt`) — die Textmarke als Frage wäre keine
    Karte, sondern eine leere Abfrage, bei mehreren solchen Wörtern sogar mehrmals
    dieselbe. Was keine deutsche Seite hat, bricht deshalb sichtbar ab, statt still zu
    einer unlernbaren Karte zu werden. `cli.interaction` lässt eine solche Karte in dieser
    Richtung gar nicht erst entstehen; diese Prüfung ist der Rückhalt."""
    card = _placeholder_card(_occurrence(), direction=CardDirection.DE_EN)

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [card], deck_name="Fehlerfall")


def test_export_deck_rejects_an_empty_card_list(tmp_path: Path) -> None:
    """Regel 13: Ein Export ohne Karten ist ein sichtbarer Fehlschlag, keine leere,
    scheinbar gültige Datei."""
    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "deck.apkg", [], deck_name="Leerer Export")


def test_export_deck_rejects_a_missing_target_directory(tmp_path: Path) -> None:
    """Regel 13: Ein nicht existierendes Zielverzeichnis ist ein sichtbarer Fehlschlag,
    kein durchgereichter Fremdfehler aus `zipfile`."""
    card = _card(_occurrence())

    with pytest.raises(ValueError):
        anki.export_deck(tmp_path / "fehlt" / "deck.apkg", [card], deck_name="Fehlerfall")


def test_the_card_and_the_printout_call_a_missing_dictionary_entry_the_same(tmp_path: Path) -> None:
    """Der gleiche Wortlaut auf Karte und Papier ist Absicht (`anki._UNCERTAIN_TEXT`,
    Kommentar dort) — festgenagelt statt bloß behauptet (Befund leicht 6, Durchsicht
    35736a9).

    `anki` und `printout` dürfen einander nicht importieren (technik.md §7, „Die
    Importregel"), führen den Text deshalb je selbst. Ohne diese Prüfung könnte einer der
    beiden abwandern, ohne dass ein Test rot wird, und dasselbe Wort hieße auf dem Blatt
    anders als in Anki. Geprüft wird nicht Literal gegen Literal, sondern gegen das, was
    `printout` tatsächlich in die Seite schreibt."""
    occurrence = _occurrence()
    placeholder = Sense(lemma=occurrence.lemma, uncertain=True)
    path = tmp_path / "blatt.html"

    printout.write_printout(path, [(occurrence, placeholder)])

    assert anki._UNCERTAIN_TEXT in path.read_text(encoding="utf-8")


def test_card_obstacle_and_export_deck_agree(tmp_path: Path) -> None:
    """`card_obstacle` und `export_deck` müssen dieselbe Grenze ziehen (Befund mittel,
    Durchsicht 35736a9): Wo die Vorabfrage `None` liefert, muss der Export durchlaufen; wo
    sie einen Grund nennt, muss er abbrechen.

    Laufen die beiden auseinander, ist genau der Schaden zurück, gegen den die Vorabfrage
    gebaut ist — entweder bricht der Export trotz grüner Vorabfrage am Ende eines
    Durchlaufs ab (und kostet Deck, Druckseite und alle übrigen Karten), oder die Triage
    weist etwas zurück, das der Export klaglos genommen hätte."""
    ohne_wortgrenze = _occurrence(word_form="heart", example_sentence="I am heart-broken.")
    faelle = [
        _card(_occurrence()),
        _card(_occurrence(), direction=CardDirection.DE_EN),
        _card(_occurrence(), direction=CardDirection.CLOZE),
        _placeholder_card(_occurrence()),
        _placeholder_card(_occurrence(), direction=CardDirection.DE_EN),
        _placeholder_card(_occurrence(), direction=CardDirection.CLOZE),
        _card(ohne_wortgrenze, direction=CardDirection.CLOZE),
        _card(ohne_wortgrenze),
    ]

    for nummer, card in enumerate(faelle):
        obstacle = anki.card_obstacle(card.occurrence, card.sense, card.card_direction)
        path = tmp_path / f"deck{nummer}.apkg"
        if obstacle is None:
            anki.export_deck(path, [card], deck_name="Einigkeit")
            assert path.is_file()
        else:
            with pytest.raises(ValueError):
                anki.export_deck(path, [card], deck_name="Einigkeit")


def test_card_obstacle_names_the_two_cases_it_knows() -> None:
    """Die beiden Unmöglichkeiten, die `card_obstacle` vorab erkennt, und der Regelfall
    dazwischen — die Meldung nennt jeweils den Grund, nicht bloß ein „geht nicht"
    (dokumentation.md §1: Was ein Mensch in Sätzen liest, ist deutsch)."""
    ohne_uebersetzung = Sense(lemma=Lemma(text="jabbar", pos="NOUN"), uncertain=True)
    ohne_wortgrenze = _occurrence(word_form="heart", example_sentence="I am heart-broken.")

    assert anki.card_obstacle(_occurrence(), _sense(_occurrence()), CardDirection.DE_EN) is None
    assert anki.card_obstacle(_occurrence(), ohne_uebersetzung, CardDirection.EN_DE) is None

    de_en = anki.card_obstacle(_occurrence(), ohne_uebersetzung, CardDirection.DE_EN)
    cloze = anki.card_obstacle(ohne_wortgrenze, _sense(ohne_wortgrenze), CardDirection.CLOZE)
    assert de_en is not None and "de_en" in de_en
    assert cloze is not None and "Lückentext" in cloze
