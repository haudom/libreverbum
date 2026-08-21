"""Prüft `libreverbum/printout.py` — bauplan.md T14, Kapitelliste als Druckseite,
zweispaltig, auf ein Blatt (Abnahmekriterium 5)."""

from __future__ import annotations

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
    """Sammelt Body-Text, Style-Inhalt und die Zahl der Listeneinträge — dasselbe
    Werkzeug wie `epub._FlowingTextParser` (dokumentation.md §5, „für die Struktur genügt
    html.parser"), hier auf die erzeugte Druckseite angewendet."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._body_parts: list[str] = []
        self._style_parts: list[str] = []
        self._in_style = False
        self.list_item_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "style":
            self._in_style = True
        elif tag == "li":
            self.list_item_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_parts.append(data)
        else:
            self._body_parts.append(data)

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


def test_book_and_chapter_appear_as_heading(tmp_path: Path) -> None:
    """Abnahmekriterium 5 und bauplan.md T14: Buch und Kapitel stehen als Überschrift auf
    der Druckseite."""
    path = tmp_path / "kapitelliste.html"

    printout.write_printout(path, [_entry("beehive", "Bienenstock", chapter_number=7)])

    parser = _parse(path)
    assert _BOOK.title in parser.body_text
    assert "7" in parser.body_text


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


def test_capacity_limit_raises_instead_of_silently_truncating(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): Mehr Einträge, als `printout.MAX_ENTRIES`
    vorsieht, sind ein sichtbarer Fehlschlag — kein stillschweigend gekürztes Blatt,
    keine zweite Seite ohne Ansage."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry(f"wort{n}", f"übersetzung{n}") for n in range(printout.MAX_ENTRIES + 1)]

    with pytest.raises(ValueError):
        printout.write_printout(path, entries)

    assert not path.exists()


def test_capacity_limit_accepts_exactly_the_maximum(tmp_path: Path) -> None:
    """Gegenprobe zur vorigen Prüfung: Genau `MAX_ENTRIES` Wörter sind kein Fehlschlag."""
    path = tmp_path / "kapitelliste.html"
    entries = [_entry(f"wort{n}", f"übersetzung{n}") for n in range(printout.MAX_ENTRIES)]

    printout.write_printout(path, entries)

    assert path.exists()


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
