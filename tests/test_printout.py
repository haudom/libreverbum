"""Prüft `libreverbum/printout.py` — bauplan.md T14, Kapitelliste als Druckseite,
zweispaltig, auf so viele Blätter umbrechend wie nötig (Abnahmekriterium 5, nachgezogen
01.09.2026)."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

from libreverbum import printout
from libreverbum.entities import Book, Lemma, Occurrence, Sense

_BOOK = Book(title="Das Zeichen der Vier", author="Arthur Conan Doyle")


def _entry(
    word: str,
    translation: str | None,
    *,
    pos: str = "NOUN",
    lemma_text: str | None = None,
    chapter_number: int = 3,
    book: Book = _BOOK,
    uncertain: bool = False,
) -> tuple[Occurrence, Sense]:
    lemma = Lemma(text=lemma_text or word.lower(), pos=pos)
    occurrence = Occurrence(
        book=book,
        chapter_number=chapter_number,
        lemma=lemma,
        word_form=word,
        example_sentence=f"A sentence with {word} in it.",
        frequency=1,
        proper_noun_frequency=0,
    )
    sense = Sense(lemma=lemma, translation=translation, uncertain=uncertain)
    return occurrence, sense


class _StructureParser(HTMLParser):
    """Sammelt Body-Text, Style-Inhalt, die Zahl der Listeneinträge und — je Eintrag — die
    tatsächlich ausgegebene Wortform (`span.wort`) — dasselbe Werkzeug wie
    `epub._FlowingTextParser` (dokumentation.md §5, „für die Struktur genügt
    html.parser"), hier auf die erzeugte Druckseite angewendet. `word_forms` liefert eine
    exakte Liste statt einer Teilstring-Prüfung auf `body_text` (Befund 4, Durchsicht
    4fa3c8e): `wort3` ist Teilstring von `wort30`…`wort36`, `body_text` allein kann eine
    Vereinigungsprüfung deshalb nicht tragen."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._body_parts: list[str] = []
        self._style_parts: list[str] = []
        self._in_style = False
        self._in_word_span = False
        self.list_item_count = 0
        self.word_forms: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "style":
            self._in_style = True
        elif tag == "li":
            self.list_item_count += 1
        elif tag == "span" and ("class", "wort") in attrs:
            self._in_word_span = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        elif tag == "span":
            self._in_word_span = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_parts.append(data)
        else:
            self._body_parts.append(data)
            if self._in_word_span:
                self.word_forms.append(data)

    @property
    def body_text(self) -> str:
        return "".join(self._body_parts)

    @property
    def style_text(self) -> str:
        return "".join(self._style_parts)


def _parse(path: Path) -> _StructureParser:
    parser = _StructureParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _parse_fragment(fragment: str) -> _StructureParser:
    """Wie `_parse`, aber auf einen Teilstring statt eine Datei angewendet — für die
    Prüfung je einzelnem Blatt (Befund 3, Durchsicht 4fa3c8e), etwa nach einem Schnitt an
    `<div class="blatt">`."""
    parser = _StructureParser()
    parser.feed(fragment)
    return parser


def test_all_words_and_translations_appear_on_the_page(tmp_path: Path) -> None:
    """konzept.md §6, „Druckausgabe": Alle übergebenen Wörter und Übersetzungen stehen
    auf der erzeugten Seite."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry("beehive", "Bienenstock"), _entry("elementary", "elementar")]

    printout.write_printout(path, entries)

    parser = _parse(path)
    assert "beehive" in parser.body_text
    assert "Bienenstock" in parser.body_text
    assert "elementary" in parser.body_text
    assert "elementar" in parser.body_text


def test_page_declares_two_columns_and_a_page_size(tmp_path: Path) -> None:
    """bauplan.md T14: zweispaltig über CSS (`columns`), Seitengröße über `@page`."""
    path = tmp_path / "kapitelliste.html"

    printout.write_printout(path, [_entry("beehive", "Bienenstock")])

    parser = _parse(path)
    assert "@page" in parser.style_text
    assert "columns" in parser.style_text


def test_sheet_container_forces_a_page_break_except_after_the_last_sheet(tmp_path: Path) -> None:
    """Befund 2, Durchsicht 4fa3c8e; technik.md §12, „Folge: die Druckseite bricht um,
    statt abzubrechen": Der Blatt-Container (`div.blatt`) erzwingt den Seitenumbruch
    selbst, statt ihn dem natürlichen Fließverhalten des Browsers zu überlassen — sonst
    fielen zwei Blätter im Ausdruck wieder auf ein Blatt zusammen. Das letzte Blatt ist
    davon ausgenommen (`:last-of-type`), sonst endete der Ausdruck auf einer leeren Seite.
    Verfälschungsprobe: den ganzen `div.blatt { … }`-Block aus `_CSS` entfernt ließ diese
    Prüfung fehlschlagen (kein `page-break-after`/`break-after` mehr im Style-Text), ebenso
    das alleinige Entfernen der `:last-of-type`-Ausnahme (keine Gegenregel mehr, die den
    Umbruch nach dem letzten Blatt wieder aufhebt)."""
    path = tmp_path / "kapitelliste.html"

    printout.write_printout(path, [_entry("beehive", "Bienenstock")])

    style = _parse(path).style_text
    assert "div.blatt {" in style
    assert "page-break-after: always;" in style
    assert "break-after: page;" in style
    assert "div.blatt:last-of-type {" in style
    assert "page-break-after: auto;" in style
    assert "break-after: auto;" in style


def test_book_and_chapter_appear_as_heading(tmp_path: Path) -> None:
    """Abnahmekriterium 5 und bauplan.md T14: Buch und Kapitel stehen als Überschrift auf
    der Druckseite."""
    path = tmp_path / "kapitelliste.html"

    printout.write_printout(path, [_entry("beehive", "Bienenstock", chapter_number=7)])

    parser = _parse(path)
    assert _BOOK.title in parser.body_text
    assert "7" in parser.body_text


def test_every_sheet_carries_the_chapter_heading(tmp_path: Path) -> None:
    """Vorgabe des Auftrags: „Jedes Blatt trägt die Kapitelüberschrift (sonst weiß der
    Leser beim zweiten Blatt nicht mehr, wozu es gehört)." Bei zwei Blättern steht Buch
    und Kapitel deshalb zweimal auf der Seite. Verfälschungsprobe: Überschrift nur einmal
    vor allen Blatt-Containern ausgegeben (wie zuvor bei einem einzigen Blatt) ließ diese
    Prüfung fehlschlagen, weil `<h1>` nur einmal statt zweimal vorkam."""
    path = tmp_path / "kapitelliste.html"
    entries = [
        _entry(f"wort{n}", f"übersetzung{n}", chapter_number=7)
        for n in range(printout.MAX_ENTRIES + 1)
    ]

    printout.write_printout(path, entries)

    document = path.read_text(encoding="utf-8")
    assert document.count("<h1>") == 2
    assert document.count(_BOOK.title) >= 2
    assert document.count("Kapitel 7") >= 2


def test_entries_are_sorted_alphabetically_by_word_form(tmp_path: Path) -> None:
    """Moduldocstring, „Warum alphabetisch": Die Wortliste steht alphabetisch nach
    `word_form`, unabhängig von der Übergabereihenfolge und von Groß-/Kleinschreibung
    (Befund 3, Review T14: ohne `casefold` in `_sort_key` käme „Mango, Zebra, apple,
    banana" heraus, weil Großbuchstaben vor Kleinbuchstaben sortieren)."""
    path = tmp_path / "kapitelliste.html"
    zebra = _entry("Zebra", "Zebra")
    apple = _entry("apple", "Apfel")
    mango = _entry("Mango", "Mango")
    banana = _entry("banana", "Banane")

    printout.write_printout(path, [zebra, apple, mango, banana])

    parser = _parse(path)
    positions = {
        word: parser.body_text.index(word) for word in ("apple", "banana", "Mango", "Zebra")
    }
    assert positions["apple"] < positions["banana"] < positions["Mango"] < positions["Zebra"]


def test_special_characters_are_escaped_and_do_not_tear_the_page_apart(tmp_path: Path) -> None:
    """CLAUDE.md, T14-Vorgabe: „<, >, & maskieren — ein Belegsatz darf die Seite nicht
    zerlegen." Ein eingebettetes HTML-Fragment schleust kein zusätzliches Listenelement
    ein, und der Text kommt unverfälscht wieder heraus — typografische Zeichen
    eingeschlossen."""
    path = tmp_path / "kapitelliste.html"
    injected = 'Gefahr</li><li class="eingeschleust">Eingeschleust & „Gauner" – Halunke\'s Werk'
    entries = [_entry("rogue", injected), _entry("beehive", "Bienenstock")]

    printout.write_printout(path, entries)

    parser = _parse(path)
    assert parser.list_item_count == len(entries)
    assert injected in parser.body_text


def test_more_than_the_capacity_wraps_onto_a_second_sheet(tmp_path: Path) -> None:
    """konzept.md, Abnahmekriterium 5 (nachgezogen 01.09.2026): „Die Druckseite bricht
    sauber auf so viele Blätter um, wie nötig" — mehr Einträge, als `MAX_ENTRIES` auf ein
    Blatt passen, sind kein Fehlschlag mehr, sondern ergeben ein zweites Blatt, das die
    restlichen Einträge trägt. Verfälschungsprobe: Mit der alten Gruppierung um eins
    verschoben (`range(0, len(ordered), MAX_ENTRIES + 1)`) fiel diese Prüfung, weil dann
    wieder nur ein `div.blatt` entstand."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry(f"wort{n}", f"übersetzung{n}") for n in range(printout.MAX_ENTRIES + 1)]

    printout.write_printout(path, entries)

    document = path.read_text(encoding="utf-8")
    assert document.count('<div class="blatt">') == 2
    parser = _parse(path)
    assert parser.list_item_count == len(entries)
    for occurrence, _ in entries:
        assert occurrence.word_form in parser.body_text


def test_exactly_max_entries_plus_one_yields_second_sheet_with_a_single_entry(
    tmp_path: Path,
) -> None:
    """`MAX_ENTRIES + 1` Einträge ergeben genau zwei Blätter, das zweite mit genau einem
    Eintrag — kein Eintrag geht verloren, keiner erscheint doppelt (Vereinigung geprüft,
    nicht nur die Anzahl). Verfälschungsprobe: Alle Einträge doch auf ein Blatt gepackt
    (Gruppierung übersprungen, `_group_entries` gibt `[ordered]` zurück) ließ diese
    Prüfung fehlschlagen, weil nur ein `div.blatt` statt zwei entstand. Zweite
    Verfälschungsprobe (Befund 4, Durchsicht 4fa3c8e): den ersten Eintrag jeder Gruppe in
    `_sheet_html` zusätzlich ein zweites Mal ausgegeben ließ die alte Teilstring-Prüfung
    (`word in parser.body_text`) unbemerkt grün, weil sie ein doppelt vorkommendes Wort
    nicht von einem einmal vorkommenden unterscheidet — die Zählung über
    `Counter(parser.word_forms)` fällt dabei rot."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry(f"wort{n}", f"übersetzung{n}") for n in range(printout.MAX_ENTRIES + 1)]
    expected_word_forms = Counter(occurrence.word_form for occurrence, _ in entries)

    printout.write_printout(path, entries)

    document = path.read_text(encoding="utf-8")
    sheets = document.split('<div class="blatt">')[1:]
    assert len(sheets) == 2
    assert sheets[0].count("<li>") == printout.MAX_ENTRIES
    assert sheets[1].count("<li>") == 1

    parser = _parse(path)
    assert parser.list_item_count == len(entries)
    # Zählung statt Teilstring-Prüfung (Befund 4, Durchsicht 4fa3c8e): `wort3 in
    # body_text` wäre auch bei `wort30`…`wort36` wahr — erst der Abgleich der
    # tatsächlich ausgegebenen Wortformen als Menge (mit Häufigkeit) hält die
    # Docstring-Zusage „keiner erscheint doppelt, Vereinigung geprüft".
    assert Counter(parser.word_forms) == expected_word_forms


def test_capacity_limit_accepts_exactly_the_maximum_on_a_single_sheet(tmp_path: Path) -> None:
    """Bei genau `MAX_ENTRIES` Einträgen bleibt es bei einem Blatt und ohne Blattzählung
    (Moduldocstring, „bei genau einem Blatt entfällt sie, »Blatt 1 von 1« wäre Lärm").
    Verfälschungsprobe: Die Blattzählung ohne die `sheet_count > 1`-Bedingung immer
    angehängt ließ diese Prüfung fehlschlagen, weil „Blatt 1 von 1" im Text auftauchte."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry(f"wort{n}", f"übersetzung{n}") for n in range(printout.MAX_ENTRIES)]

    printout.write_printout(path, entries)

    document = path.read_text(encoding="utf-8")
    assert document.count('<div class="blatt">') == 1
    parser = _parse(path)
    assert "Blatt" not in parser.body_text


def test_sorting_is_continuous_across_a_sheet_boundary(tmp_path: Path) -> None:
    """Befund 3, Durchsicht 4fa3c8e; `_group_entries`-Docstring: „Gruppen entstehen nur
    durch Schneiden, nicht durch Umsortieren" — die alphabetische Sortierung
    (Moduldocstring, „Warum alphabetisch") gilt durchgehend über die Blattgrenze hinweg,
    nicht nur innerhalb eines Blatts: Der letzte Eintrag von Blatt 1 steht vor dem ersten
    Eintrag von Blatt 2. Verfälschungsprobe: `_sheet_html` sortiert jede Gruppe zusätzlich
    rückwärts, bevor sie ausgegeben wird (`group = list(reversed(group))`), ließ diese
    Prüfung fehlschlagen — innerhalb jedes Blatts stand die Reihenfolge dann verkehrt, und
    der letzte Eintrag von Blatt 1 lag hinter dem ersten Eintrag von Blatt 2."""
    path = tmp_path / "kapitelliste.html"
    entries = [
        _entry(f"wort{n:03d}", f"übersetzung{n:03d}") for n in range(printout.MAX_ENTRIES + 1)
    ]
    # Absichtlich nicht bereits sortiert übergeben, damit die Prüfung `write_printout`s
    # eigene Sortierung testet, nicht die Übergabereihenfolge.
    printout.write_printout(path, list(reversed(entries)))

    document = path.read_text(encoding="utf-8")
    sheets = document.split('<div class="blatt">')[1:]
    assert len(sheets) == 2
    first_sheet_words = _parse_fragment(sheets[0]).word_forms
    second_sheet_words = _parse_fragment(sheets[1]).word_forms
    assert first_sheet_words == sorted(first_sheet_words)
    assert second_sheet_words == sorted(second_sheet_words)
    assert first_sheet_words[-1] < second_sheet_words[0]


def test_rejects_an_empty_word_list(tmp_path: Path) -> None:
    """Regel 13: Eine leere Wortliste ergibt keine sinnvolle Druckseite."""
    with pytest.raises(ValueError):
        printout.write_printout(tmp_path / "kapitelliste.html", [])


def test_rejects_entries_from_different_chapters(tmp_path: Path) -> None:
    """Regel 13: Die Druckseite ist eine Kapitelliste (bauplan.md T14) — Wörter aus
    mehreren Kapiteln sind ein sichtbarer Fehlschlag, keine stillschweigend
    zusammengelegte Liste."""
    path = tmp_path / "kapitelliste.html"
    chapter_three = _entry("beehive", "Bienenstock", chapter_number=3)
    chapter_five = _entry("elementary", "elementar", chapter_number=5)

    with pytest.raises(ValueError):
        printout.write_printout(path, [chapter_three, chapter_five])


def test_rejects_an_unresolved_translation_that_is_not_marked_uncertain(tmp_path: Path) -> None:
    """Befund 2, Review T14, Fall 2: Eine `Sense` mit `translation is None` und
    `uncertain=False` ist ein echter Fehlschlag der Vorstufe (Regel 13) — wie
    `anki._translation_text` gehört sie nicht auf eine gedruckte Seite."""
    path = tmp_path / "kapitelliste.html"
    unresolved = _entry("beehive", None, uncertain=False)

    with pytest.raises(ValueError):
        printout.write_printout(path, [unresolved])

    assert not path.exists()


def test_unresolved_translation_marked_uncertain_is_shown_not_rejected(tmp_path: Path) -> None:
    """Befund 2, Review T14, Fall 1: Eine `Sense` ohne Übersetzung, aber mit
    `uncertain=True`, ist kein Fehlschlag — der Nutzer hat den Eintrag (etwa eine Wendung
    ohne Wörterbucheintrag, `dictionary.particle_verb_candidates`) in der Triage bewusst
    gewählt. Er erscheint auf der Seite, mit einer deutschen Textmarke statt der
    fehlenden Übersetzung."""
    path = tmp_path / "kapitelliste.html"
    placeholder = _entry("give up", None, pos="VERB", uncertain=True)

    printout.write_printout(path, [placeholder])

    parser = _parse(path)
    assert "give up" in parser.body_text
    assert "unsicher" in parser.body_text


def test_resolved_translation_marked_uncertain_is_visibly_distinguished(tmp_path: Path) -> None:
    """Befund 2, Review T14, Fall 3: Eine `Sense` mit Übersetzung **und** `uncertain=True`
    (die Ausweichantwort des Modells, heute in Phase 1 nicht erreichbar) steht nicht
    ununterscheidbar wie eine gesicherte Bedeutung da, sondern trägt zusätzlich die
    Textmarke."""
    path = tmp_path / "kapitelliste.html"
    certain = _entry("beehive", "Bienenstock", uncertain=False)
    uncertain = _entry("elementary", "elementar", uncertain=True)

    printout.write_printout(path, [certain, uncertain])

    parser = _parse(path)
    assert "Bienenstock" in parser.body_text
    assert "elementar" in parser.body_text
    # Nur der unsichere Eintrag trägt die Marke `(unsicher)` — der gesicherte bleibt
    # unmarkiert, genau einmal, nicht bei beiden Einträgen.
    assert parser.body_text.count("(unsicher)") == 1


def test_homographs_are_distinguished_by_pos_abbreviation(tmp_path: Path) -> None:
    """Befund 4, Review T14: Zwei Vorkommen derselben Wortform, aber verschiedener
    Wortart (`saw` als NOUN und VERB), sind auf der Druckseite an einem Wortart-Kürzel
    unterscheidbar, nicht nur an der Übersetzung — zwei Drittel der Grundformen eines
    Kapitels sind mehrdeutig (technik.md §3, Nachtrag 18.08.2026)."""
    path = tmp_path / "kapitelliste.html"
    saw_noun = _entry("saw", "Säge", pos="NOUN", lemma_text="saw")
    saw_verb = _entry("saw", "sah", pos="VERB", lemma_text="saw")

    printout.write_printout(path, [saw_noun, saw_verb])

    parser = _parse(path)
    assert "Subst." in parser.body_text
    assert "Verb" in parser.body_text


def test_multiword_expression_entries_have_no_pos_abbreviation(tmp_path: Path) -> None:
    """Befund 4, Review T14: Wendungen aus T4/T7 tragen keine Einzelwortart
    (`extraction._NO_SINGLE_POS`, leerer String) — die Druckseite zeigt für sie kein
    Wortart-Kürzel, statt an einer unbekannten Wortart zu scheitern."""
    path = tmp_path / "kapitelliste.html"
    expression = _entry("give up", "aufgeben", pos="", lemma_text="give up")

    printout.write_printout(path, [expression])

    parser = _parse(path)
    assert "give up" in parser.body_text
    assert "aufgeben" in parser.body_text
