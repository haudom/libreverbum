"""Prüft `libreverbum/epub.py` — bauplan.md T12 (Struktur eines EPUB: Metadaten, `spine`,
Navigation, Kapitelliste nach eindeutigen Zielen) und T12b (Fließtext eines Kapitels,
Vorspann und Impressum aussteuern, die drei Ablehnfälle)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from libreverbum import epub
from libreverbum.entities import Book

# ------------------------------------------------- Lokale Vorrichtung: umsortierte Navigation

_REORDERED_NAV_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_REORDERED_NAV_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:reordered-nav-test</dc:identifier>
    <dc:title>Umsortiertes Buch</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapa" href="chaptera.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapb" href="chapterb.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapa"/>
    <itemref idref="chapb"/>
  </spine>
</package>
"""

# Nennt Kapitel B vor Kapitel A — umgekehrt zur spine-Reihenfolge oben.
_REORDERED_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chapterb.xhtml">Label B</a></li>
      <li><a href="chaptera.xhtml">Label A</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _reordered_nav_chapter_xhtml(title: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body><p>{title}</p></body>
</html>
"""


def _write_reordered_nav_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen Navigation die beiden Kapitel in umgekehrter
    spine-Reihenfolge nennt (B vor A) — Grundlage für die Prüfung, dass
    `ChapterReference.number` trotzdem in spine-Reihenfolge zählt (`entities.Chapter`,
    Docstring zu `number`). Die Vorrichtungen aus `tests/conftest.py` (T2) nennen
    Navigation und spine zufällig in derselben Reihenfolge und können diese Regel deshalb
    nicht prüfen."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _REORDERED_NAV_OPF)
        archive.writestr("OEBPS/nav.xhtml", _REORDERED_NAV_XHTML)
        archive.writestr("OEBPS/chaptera.xhtml", _reordered_nav_chapter_xhtml("Chapter A"))
        archive.writestr("OEBPS/chapterb.xhtml", _reordered_nav_chapter_xhtml("Chapter B"))


# --------------------------------------------------------------------- Mini-EPUB (T2)


def test_read_structure_reads_title_and_author_from_the_opf(
    mini_epub_with_navigation: Path,
) -> None:
    """bauplan.md T12: Metadaten kommen aus der OPF-Package-Datei."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert result.book.title == "Mini-Buch"
    assert result.book.author == "Test Autorin"


def test_acceptance_1_chapter_list_follows_unique_navigation_targets_not_spine_count(
    mini_epub_with_navigation: Path,
) -> None:
    """Abnahmekriterium 1: Die Kapitelliste stimmt mit dem Inhaltsverzeichnis der Datei
    überein. Die Navigation nennt vier Einträge auf zwei eindeutige Ziele, die spine aber
    drei Dokumente (technik.md §8, „Sherlock-Fall 18→14") — die Kapitelliste folgt der
    Navigation, nicht der Zahl der spine-Dokumente."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert len(result.chapters) == 2
    assert result.notice is None


def test_read_structure_uses_the_first_navigation_label_for_a_deduplicated_target(
    mini_epub_with_navigation: Path,
) -> None:
    """technik.md §8: Zeigen mehrere Navigationseinträge auf dasselbe Dokument (hier je
    zwei #anker je Kapitel), gewinnt die Beschriftung des ersten Eintrags."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert [chapter.title for chapter in result.chapters] == [
        "Chapter One, Beginning",
        "Chapter Two, Beginning",
    ]


def test_read_structure_numbers_chapters_from_one_in_document_order(
    mini_epub_with_navigation: Path,
) -> None:
    """`ChapterReference.number` zählt ab 1 (`entities.Chapter`, Docstring zu `number`).
    Kapitel 2 trägt zusätzlich `chapter3.xhtml`, das keinen eigenen Navigationseintrag hat
    (technik.md §8, „Ein Kapitel ist nicht ein Dokument")."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert [chapter.number for chapter in result.chapters] == [1, 2]


def test_a_chapter_spans_the_spine_up_to_but_excluding_the_next_navigation_target(
    mini_epub_with_navigation: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Ein Kapitel reicht von seinem
    Navigationsziel bis ausschließlich zum nächsten und umfasst alle Dokumente der
    Lesereihenfolge dazwischen — hier für die EPUB-3-Navigation (`nav.xhtml`)."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chapter1.xhtml"],
        ["OEBPS/chapter2.xhtml", "OEBPS/chapter3.xhtml"],
    ]


def test_a_chapter_spans_the_spine_up_to_the_next_navigation_target_with_ncx_navigation(
    mini_epub_with_ncx_navigation: Path,
) -> None:
    """Derselbe Beleg wie mit `nav.xhtml`, für die EPUB-2-Navigation `toc.ncx` (technik.md
    §8, Mehrheitsfall: zehn von zwölf gemessenen Dateien sind EPUB 2.0)."""
    result = epub.read_structure(mini_epub_with_ncx_navigation)

    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chapter1.xhtml"],
        ["OEBPS/chapter2.xhtml", "OEBPS/chapter3.xhtml"],
    ]


def test_spine_fallback_gives_each_document_its_own_single_element_chapter(
    mini_epub_without_navigation: Path,
) -> None:
    """technik.md §8: Fehlt die Navigation, gilt jedes Dokument der Lesereihenfolge als
    eigenes Kapitel — `documents` trägt dabei genau ein Element, kein Kapitel fasst mehrere
    Dokumente zusammen."""
    result = epub.read_structure(mini_epub_without_navigation)

    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chapter1.xhtml"],
        ["OEBPS/chapter2.xhtml"],
        ["OEBPS/chapter3.xhtml"],
    ]


def test_spine_fallback_chapters_have_level_zero(mini_epub_without_navigation: Path) -> None:
    """Ohne verwertbare Navigation hat jedes Kapitel die Ebene 0 — es gibt keine Hierarchie,
    wenn die Grenzen nicht aus dem Buch stammen (technik.md §8, „Ein Kapitel ist nicht ein
    Dokument")."""
    result = epub.read_structure(mini_epub_without_navigation)

    assert all(chapter.level == 0 for chapter in result.chapters)


def test_read_structure_with_ncx_navigation_follows_unique_navigation_targets_not_spine_count(
    mini_epub_with_ncx_navigation: Path,
) -> None:
    """Derselbe Beleg wie mit `nav.xhtml`, für die EPUB-2-Navigation `toc.ncx`
    (technik.md §8, Mehrheitsfall: zehn von zwölf gemessenen Dateien sind EPUB 2.0)."""
    result = epub.read_structure(mini_epub_with_ncx_navigation)

    assert len(result.chapters) == 2
    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == [
        "Chapter One, Beginning",
        "Chapter Two, Beginning",
    ]


def test_acceptance_1_missing_navigation_is_reported_and_every_spine_document_becomes_a_chapter(
    mini_epub_without_navigation: Path,
) -> None:
    """Abnahmekriterium 1: Enthält die Datei keine Kapitelstruktur, wird das gemeldet und
    die Lesereihenfolge tritt an ihre Stelle (technik.md §8) — alle drei spine-Dokumente
    werden zu Kapiteln, und `notice` trägt den Hinweis als Ergebnisbestandteil."""
    result = epub.read_structure(mini_epub_without_navigation)

    assert len(result.chapters) == 3
    assert result.notice == epub.NAVIGATION_MISSING_NOTICE
    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chapter1.xhtml"],
        ["OEBPS/chapter2.xhtml"],
        ["OEBPS/chapter3.xhtml"],
    ]


def test_read_structure_orders_chapters_by_spine_position_not_navigation_order(
    tmp_path: Path,
) -> None:
    """`entities.Chapter`, Docstring zu `number`: „number zählt ab 1 in der Reihenfolge
    des spine, auch wenn die Kapitelliste aus der Navigation stammt." Die Navigation
    dieser Vorrichtung nennt Kapitel B vor Kapitel A; die spine nennt A vor B."""
    path = tmp_path / "reordered_nav.epub"
    _write_reordered_nav_epub(path)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == ["Label A", "Label B"]
    assert [chapter.number for chapter in result.chapters] == [1, 2]


# --------------------------------------- Lokale Vorrichtung: verschachtelte Navigation

# Zwei Teile mit je eigener Titelseite, darunter je ein bis zwei Kapitel — die Bauform aus
# technik.md §8, „Unterkapitel gibt es": „Unterpunkte als eigene
# Dokumente unter einem Elternknoten (Teil I → Kapitel 1–5)". Die Vorrichtungen aus
# tests/conftest.py (T2) sind absichtlich flach und können diese Ebene nicht prüfen.
_NESTED_LEVEL_NAV_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:nested-level-nav-test</dc:identifier>
    <dc:title>Buch mit Teilen</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="part1" href="part1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="part2" href="part2.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap3" href="chapter3.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="part1"/>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
    <itemref idref="part2"/>
    <itemref idref="chap3"/>
  </spine>
</package>
"""

# Teil I und Teil II auf der obersten Ebene (0), ihre Kapitel je ein <ol> tiefer (1) —
# <a> und das verschachtelte <ol> sind beide direkte Kinder desselben <li>, wie es die
# EPUB-3-Norm für Navigationsdokumente vorsieht.
_NESTED_LEVEL_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="part1.xhtml">Teil I</a>
        <ol>
          <li><a href="chapter1.xhtml">Kapitel 1</a></li>
          <li><a href="chapter2.xhtml">Kapitel 2</a></li>
        </ol>
      </li>
      <li><a href="part2.xhtml">Teil II</a>
        <ol>
          <li><a href="chapter3.xhtml">Kapitel 3</a></li>
        </ol>
      </li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_nested_nav_xhtml_epub(path: Path) -> None:
    """Baut das Mini-EPUB mit der verschachtelten `nav.xhtml` oben zusammen."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _NESTED_LEVEL_NAV_OPF)
        archive.writestr("OEBPS/nav.xhtml", _NESTED_LEVEL_NAV_XHTML)
        archive.writestr("OEBPS/part1.xhtml", _reordered_nav_chapter_xhtml("Teil I"))
        archive.writestr("OEBPS/chapter1.xhtml", _reordered_nav_chapter_xhtml("Kapitel 1"))
        archive.writestr("OEBPS/chapter2.xhtml", _reordered_nav_chapter_xhtml("Kapitel 2"))
        archive.writestr("OEBPS/part2.xhtml", _reordered_nav_chapter_xhtml("Teil II"))
        archive.writestr("OEBPS/chapter3.xhtml", _reordered_nav_chapter_xhtml("Kapitel 3"))


# Dieselben fünf Dokumente und Beschriftungen wie oben, als EPUB-2-`toc.ncx` mit
# verschachtelten `navPoint` statt verschachtelter `<ol>` (technik.md §8, Mehrheitsfall:
# zehn von zwölf gemessenen Dateien sind EPUB 2.0).
_NESTED_LEVEL_NCX_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:nested-level-ncx-test</dc:identifier>
    <dc:title>Buch mit Teilen (ncx)</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="part1" href="part1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="part2" href="part2.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap3" href="chapter3.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="part1"/>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
    <itemref idref="part2"/>
    <itemref idref="chap3"/>
  </spine>
</package>
"""

_NESTED_LEVEL_TOC_NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head></head>
  <docTitle><text>Buch mit Teilen (ncx)</text></docTitle>
  <navMap>
    <navPoint id="np1">
      <navLabel><text>Teil I</text></navLabel>
      <content src="part1.xhtml"/>
      <navPoint id="np1-1">
        <navLabel><text>Kapitel 1</text></navLabel>
        <content src="chapter1.xhtml"/>
      </navPoint>
      <navPoint id="np1-2">
        <navLabel><text>Kapitel 2</text></navLabel>
        <content src="chapter2.xhtml"/>
      </navPoint>
    </navPoint>
    <navPoint id="np2">
      <navLabel><text>Teil II</text></navLabel>
      <content src="part2.xhtml"/>
      <navPoint id="np2-1">
        <navLabel><text>Kapitel 3</text></navLabel>
        <content src="chapter3.xhtml"/>
      </navPoint>
    </navPoint>
  </navMap>
</ncx>
"""


def _write_nested_toc_ncx_epub(path: Path) -> None:
    """Baut das Mini-EPUB mit der verschachtelten `toc.ncx` oben zusammen."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _NESTED_LEVEL_NCX_OPF)
        archive.writestr("OEBPS/toc.ncx", _NESTED_LEVEL_TOC_NCX)
        archive.writestr("OEBPS/part1.xhtml", _reordered_nav_chapter_xhtml("Teil I"))
        archive.writestr("OEBPS/chapter1.xhtml", _reordered_nav_chapter_xhtml("Kapitel 1"))
        archive.writestr("OEBPS/chapter2.xhtml", _reordered_nav_chapter_xhtml("Kapitel 2"))
        archive.writestr("OEBPS/part2.xhtml", _reordered_nav_chapter_xhtml("Teil II"))
        archive.writestr("OEBPS/chapter3.xhtml", _reordered_nav_chapter_xhtml("Kapitel 3"))


_NESTED_LEVEL_TITLES = ["Teil I", "Kapitel 1", "Kapitel 2", "Teil II", "Kapitel 3"]
_NESTED_LEVEL_LEVELS = [0, 1, 1, 0, 1]


def test_nested_nav_xhtml_reports_the_level_of_each_entry(tmp_path: Path) -> None:
    """technik.md §8, „Unterkapitel gibt es": Die Ebene ist die Zahl
    der umschließenden `<ol>` innerhalb des `nav` — Teil I und Teil II auf Ebene 0, ihre
    Kapitel je ein `<ol>` tiefer auf Ebene 1."""
    path = tmp_path / "nested_nav.epub"
    _write_nested_nav_xhtml_epub(path)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == _NESTED_LEVEL_TITLES
    assert [chapter.level for chapter in result.chapters] == _NESTED_LEVEL_LEVELS


def test_nested_nav_xhtml_numbers_run_through_across_levels_in_spine_order(tmp_path: Path) -> None:
    """Auftrag Teilaufgabe 3: Die Nummer zählt in der Reihenfolge der spine durch, ohne
    bei einer tieferen Ebene neu zu beginnen (keine Unternummerierung wie „3.1")."""
    path = tmp_path / "nested_nav_numbers.epub"
    _write_nested_nav_xhtml_epub(path)

    result = epub.read_structure(path)

    assert [chapter.number for chapter in result.chapters] == [1, 2, 3, 4, 5]


def test_nested_toc_ncx_reports_the_level_of_each_entry(tmp_path: Path) -> None:
    """Derselbe Beleg wie mit `nav.xhtml`, für die EPUB-2-Form `toc.ncx` — die Ebene ist
    hier die Verschachtelungstiefe des `navPoint`, nicht `dtb:depth` der Datei (technik.md
    §8, „Unterkapitel gibt es": bei Dune steht dort „2", obwohl die Navigation flach
    ist)."""
    path = tmp_path / "nested_ncx.epub"
    _write_nested_toc_ncx_epub(path)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == _NESTED_LEVEL_TITLES
    assert [chapter.level for chapter in result.chapters] == _NESTED_LEVEL_LEVELS
    assert [chapter.number for chapter in result.chapters] == [1, 2, 3, 4, 5]


def test_a_parent_chapter_stays_selectable_and_reads_its_own_document(tmp_path: Path) -> None:
    """Auftrag Teilaufgabe 3: „Elternzeilen bleiben wählbar, weil sie eigenen Text
    tragen" — `read_chapter` auf „Teil I" liefert dessen eigenes Vorspanndokument, nicht
    den Text seiner Kinder „Kapitel 1"/„Kapitel 2" (technik.md §8, „Was die Kapitelliste
    zusätzlich zeigt")."""
    path = tmp_path / "nested_nav_parent.epub"
    _write_nested_nav_xhtml_epub(path)
    structure = epub.read_structure(path)
    part_one = structure.chapters[0]
    assert part_one.title == "Teil I"
    assert part_one.documents == ["OEBPS/part1.xhtml"]

    chapter = epub.read_chapter(path, structure.book, part_one)

    assert chapter.text == "Teil I"


def test_deduplicate_by_target_keeps_the_first_entrys_level_too() -> None:
    """`_deduplicate_by_target`, technik.md §8, „Sherlock-Fall 18→14": Gewinnt bei mehreren
    Einträgen auf dasselbe Ziel der erste in der Reihenfolge der Navigation, gilt das auch
    für seine Ebene — ein tiefer eingerücktes Kind darf die Ebene des schon gesehenen
    Elternteils nicht überschreiben (dieselbe Lage wie die Kinder I./II./III. unter „I. A
    SCANDAL IN BOHEMIA" in `sherlock.epub`)."""
    entries = [("Teil I", "part1.xhtml", 0), ("I.", "part1.xhtml", 1), ("II.", "part1.xhtml", 1)]

    labels = epub._deduplicate_by_target(entries)

    assert labels["part1.xhtml"] == ("Teil I", 0)


# ------------- Lokale Vorrichtung: Bauformen, die die Tiefensuche aus 162e439 lautlos verlor

_LOST_ENTRIES_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:lost-entries-test</dc:identifier>
    <dc:title>Buch mit ungewoehnlicher Navigation</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="c1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="c2.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap3" href="c3.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
    <itemref idref="chap3"/>
  </spine>
</package>
"""


def _write_lost_entries_epub(path: Path, nav_xhtml: str) -> None:
    """Baut ein Mini-EPUB mit drei Kapiteln und der übergebenen Navigation — gemeinsame
    Grundlage für die Bauformen, die die Tiefensuche aus 162e439 lautlos verlor (Durchsicht
    162e439, Befund 1 und 2)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _LOST_ENTRIES_OPF)
        archive.writestr("OEBPS/nav.xhtml", nav_xhtml)
        archive.writestr("OEBPS/c1.xhtml", _reordered_nav_chapter_xhtml("Kapitel 1"))
        archive.writestr("OEBPS/c2.xhtml", _reordered_nav_chapter_xhtml("Kapitel 2"))
        archive.writestr("OEBPS/c3.xhtml", _reordered_nav_chapter_xhtml("Kapitel 3"))


# Kapitel 2 steht nicht als direktes Kind seines <li>, sondern in ein <p> verpackt — nach
# der Norm zulässig, weil epub:type="toc" keine Kindform des <a> vorschreibt.
_ANCHOR_WRAPPED_IN_PARAGRAPH_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="c1.xhtml">Kapitel 1</a></li>
      <li><p><a href="c2.xhtml">Kapitel 2</a></p></li>
      <li><a href="c3.xhtml">Kapitel 3</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def test_a_navigation_anchor_wrapped_in_a_paragraph_is_not_lost(tmp_path: Path) -> None:
    """Durchsicht 162e439, Befund 1: `<a>` als Kind eines `<p>` statt direktes Kind seines
    `<li>` ist EPUB-3-normkonform. Die Tiefensuche aus 162e439 fand mit `item.find(a)` nur
    direkte Kinder und verlor „Kapitel 2" lautlos — sein Dokument wanderte über
    `document_groups[-1].append(document)` ins vorige Kapitel."""
    path = tmp_path / "anchor_in_paragraph.epub"
    _write_lost_entries_epub(path, _ANCHOR_WRAPPED_IN_PARAGRAPH_NAV_XHTML)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]
    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/c1.xhtml"],
        ["OEBPS/c2.xhtml"],
        ["OEBPS/c3.xhtml"],
    ]


# Kapitel 2 steht in einem verschachtelten <ol>, das hinter einem umhüllenden <div> liegt —
# das <ol> ist damit kein direktes Kind mehr seines <li>.
_NESTED_OL_WRAPPED_IN_DIV_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="c1.xhtml">Kapitel 1</a>
        <div>
          <ol>
            <li><a href="c2.xhtml">Kapitel 2</a></li>
          </ol>
        </div>
      </li>
      <li><a href="c3.xhtml">Kapitel 3</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def test_a_nested_ol_wrapped_in_a_div_is_not_lost(tmp_path: Path) -> None:
    """Durchsicht 162e439, Befund 1: Ein verschachteltes `<ol>` hinter einem umhüllenden
    `<div>` ist kein direktes Kind mehr seines `<li>`. Die Tiefensuche aus 162e439 suchte
    mit `item.find(ol)` nur direkte Kinder und verlor den **ganzen Kindast** — hier
    „Kapitel 2"."""
    path = tmp_path / "nested_ol_in_div.epub"
    _write_lost_entries_epub(path, _NESTED_OL_WRAPPED_IN_DIV_NAV_XHTML)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]
    assert [chapter.level for chapter in result.chapters] == [0, 1, 0]


# Kapitel 2 und Kapitel 3 stehen in zwei Geschwister-<ol> im selben <li> — die Norm
# schränkt die Zahl verschachtelter <ol> je <li> nicht auf eines ein.
_TWO_SIBLING_OL_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="c1.xhtml">Kapitel 1</a>
        <ol>
          <li><a href="c2.xhtml">Kapitel 2</a></li>
        </ol>
        <ol>
          <li><a href="c3.xhtml">Kapitel 3</a></li>
        </ol>
      </li>
    </ol>
  </nav>
</body>
</html>
"""


def test_two_sibling_ol_elements_in_the_same_li_are_both_read(tmp_path: Path) -> None:
    """Durchsicht 162e439, Befund 1: Zwei Geschwister-`<ol>` im selben `<li>` sind erlaubt.
    `item.find(ol)` der Tiefensuche aus 162e439 liefert nur das erste Fundstück — das
    zweite verschwand vollständig, hier „Kapitel 3"."""
    path = tmp_path / "two_sibling_ol.epub"
    _write_lost_entries_epub(path, _TWO_SIBLING_OL_NAV_XHTML)

    result = epub.read_structure(path)

    assert [chapter.title for chapter in result.chapters] == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]
    assert [chapter.level for chapter in result.chapters] == [0, 1, 1]


# Die oberste Liste ist ein <ul> statt eines <ol> — beides sind laut EPUB-3-Norm zulässige
# Listenelemente für ein Navigationsdokument.
_TOP_LEVEL_UL_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ul>
      <li><a href="c1.xhtml">Kapitel 1</a></li>
      <li><a href="c2.xhtml">Kapitel 2</a></li>
      <li><a href="c3.xhtml">Kapitel 3</a></li>
    </ul>
  </nav>
</body>
</html>
"""


def test_a_top_level_ul_instead_of_ol_is_recognized(tmp_path: Path) -> None:
    """Befund 2, schließt sich mit Befund 1: `nav.find(...ol)` der Fassung aus 162e439 fand
    ein `<ul>` als oberste Liste nicht und lieferte eine leere Kapitelliste — die Datei
    fiel auf `toc.ncx` oder die spine samt Hinweis zurück, obwohl eine EPUB-3-Navigation
    vorhanden war."""
    path = tmp_path / "top_level_ul.epub"
    _write_lost_entries_epub(path, _TOP_LEVEL_UL_NAV_XHTML)

    result = epub.read_structure(path)

    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]
    assert [chapter.level for chapter in result.chapters] == [0, 0, 0]


# ------------------------ Lokale Vorrichtung: Dokument vor dem ersten Navigationsziel

_LEADING_DOCUMENT_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:leading-document-test</dc:identifier>
    <dc:title>Buch mit Umschlag vor dem ersten Kapitel</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapa" href="chaptera.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapb" href="chapterb.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="cover"/>
    <itemref idref="chapa"/>
    <itemref idref="chapb"/>
  </spine>
</package>
"""

# Nennt nur die beiden Kapitel, nicht den Umschlag davor in der spine.
_LEADING_DOCUMENT_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chaptera.xhtml">Chapter A</a></li>
      <li><a href="chapterb.xhtml">Chapter B</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_leading_document_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen spine mit einem Umschlagdokument beginnt, das keinen
    eigenen Navigationseintrag hat (technik.md §8, „Ein Kapitel ist nicht ein Dokument":
    Dokumente vor dem ersten Navigationsziel gehören zu keinem Kapitel)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _LEADING_DOCUMENT_OPF)
        archive.writestr("OEBPS/nav.xhtml", _LEADING_DOCUMENT_NAV_XHTML)
        archive.writestr("OEBPS/cover.xhtml", _reordered_nav_chapter_xhtml("Cover"))
        archive.writestr("OEBPS/chaptera.xhtml", _reordered_nav_chapter_xhtml("Chapter A"))
        archive.writestr("OEBPS/chapterb.xhtml", _reordered_nav_chapter_xhtml("Chapter B"))


def test_documents_before_the_first_navigation_target_belong_to_no_chapter(tmp_path: Path) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Ein Kapitel reicht von seinem
    Navigationsziel bis zum nächsten — ein spine-Dokument vor dem
    ersten Ziel (Umschlag, Titelei, Inhaltsverzeichnisseite) gehört deshalb zu keinem
    Kapitel und fällt weg."""
    path = tmp_path / "leading_document.epub"
    _write_leading_document_epub(path)

    result = epub.read_structure(path)

    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chaptera.xhtml"],
        ["OEBPS/chapterb.xhtml"],
    ]


# ------------- Lokale Vorrichtung: Navigationsziel fehlt im Archiv (Befund 1, Review Runde 2)

_MISSING_TARGET_DOCUMENT_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:missing-target-document-test</dc:identifier>
    <dc:title>Buch mit fehlendem Zieldokument</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapa" href="chaptera.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapa2" href="chaptera2.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapb" href="chapterb.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapb2" href="chapterb2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapa"/>
    <itemref idref="chapa2"/>
    <itemref idref="chapb"/>
    <itemref idref="chapb2"/>
  </spine>
</package>
"""

# Nennt beide Kapitel; chapterb.xhtml selbst fehlt gleich im Archiv (siehe
# _write_missing_target_document_epub) — das Navigationsziel des zweiten Kapitels ist damit
# unerreichbar, sein Folgedokument chapterb2.xhtml aber sehr wohl vorhanden.
_MISSING_TARGET_DOCUMENT_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chaptera.xhtml">Kapitel A</a></li>
      <li><a href="chapterb.xhtml">Kapitel B</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_missing_target_document_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen Navigation ein zweites Kapitel nennt, dessen eigenes
    Zieldokument (`chapterb.xhtml`) im Archiv fehlt, während sein Folgedokument
    (`chapterb2.xhtml`) da ist (Befund 1, Review Runde 2) — nachgestellt aus dem Beispiel
    des Befunds: spine `a, a2, b, b2`, Nav-Ziele `a` und `b`, `b.xhtml` fehlt im Archiv."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _MISSING_TARGET_DOCUMENT_OPF)
        archive.writestr("OEBPS/nav.xhtml", _MISSING_TARGET_DOCUMENT_NAV_XHTML)
        archive.writestr("OEBPS/chaptera.xhtml", _reordered_nav_chapter_xhtml("Chapter A"))
        archive.writestr("OEBPS/chaptera2.xhtml", _reordered_nav_chapter_xhtml("Chapter A, part 2"))
        # OEBPS/chapterb.xhtml wird absichtlich nicht geschrieben — das Zieldokument fehlt.
        archive.writestr("OEBPS/chapterb2.xhtml", _reordered_nav_chapter_xhtml("Chapter B, part 2"))


def test_a_chapter_with_a_missing_navigation_target_does_not_absorb_the_next_chapters_documents(
    tmp_path: Path,
) -> None:
    """Befund 1, Review Runde 2: Fehlt das Navigationsziel eines Kapitels im Archiv, während
    seine Folgedokumente da sind, darf das Kapitel nicht lautlos aus der Liste verschwinden
    und seine Dokumente sich nicht an das vorige Kapitel hängen. Kapitel B bleibt eine
    eigene Gruppe, obwohl `chapterb.xhtml` selbst fehlt."""
    path = tmp_path / "missing_target_document.epub"
    _write_missing_target_document_epub(path)

    result = epub.read_structure(path)

    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == ["Kapitel A", "Kapitel B"]
    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chaptera.xhtml", "OEBPS/chaptera2.xhtml"],
        ["OEBPS/chapterb.xhtml", "OEBPS/chapterb2.xhtml"],
    ]


def test_reading_a_chapter_whose_navigation_target_document_is_missing_reports_it(
    tmp_path: Path,
) -> None:
    """Befund 1, Review Runde 2: Der in `read_chapter` versprochene Zweig „ein Dokument des
    Kapitels … fehlt im Archiv" ist über `read_structure` erreichbar — vorher filterte
    `_resolve_chapters` das fehlende Zieldokument schon aus der Kapitelliste heraus, bevor
    `read_chapter` es je zu sehen bekam."""
    path = tmp_path / "missing_target_document.epub"
    _write_missing_target_document_epub(path)
    structure = epub.read_structure(path)

    with pytest.raises(ValueError, match=r"chapterb\.xhtml.*fehlt im Archiv"):
        epub.read_chapter(path, structure.book, structure.chapters[1])


_ALL_TARGETS_MISSING_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:all-targets-missing-test</dc:identifier>
    <dc:title>Buch mit sämtlich fehlenden Zieldokumenten</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapa" href="chaptera.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapb" href="chapterb.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapc" href="chapterc.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapa"/>
    <itemref idref="chapb"/>
    <itemref idref="chapc"/>
  </spine>
</package>
"""

# Nennt zwei Ziele, die beide im Archiv fehlen (siehe _write_all_targets_missing_epub);
# chapterc.xhtml steht in der spine, aber in keinem Navigationseintrag.
_ALL_TARGETS_MISSING_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chaptera.xhtml">Kapitel A</a></li>
      <li><a href="chapterb.xhtml">Kapitel B</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_all_targets_missing_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen beide Navigationsziele in der spine stehen, aber
    **keines** von ihnen im Archiv vorhanden ist — der „Achtung"-Fall aus Befund 1, Review
    Runde 2: die bestehende Zusicherung aus dem Kommentar „Befund 2, Review Runde 1" muss
    auch nach dessen Nachbesserung gelten. Nur `chapterc.xhtml`, das in keinem
    Navigationseintrag steht, ist tatsächlich im Archiv."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _ALL_TARGETS_MISSING_OPF)
        archive.writestr("OEBPS/nav.xhtml", _ALL_TARGETS_MISSING_NAV_XHTML)
        # OEBPS/chaptera.xhtml und OEBPS/chapterb.xhtml werden absichtlich nicht
        # geschrieben — beide Zieldokumente fehlen im Archiv.
        archive.writestr("OEBPS/chapterc.xhtml", _reordered_nav_chapter_xhtml("Chapter C"))


def test_falls_back_to_spine_when_every_navigation_target_document_is_missing_from_the_archive(
    tmp_path: Path,
) -> None:
    """Befund 1, Review Runde 2, „Achtung"-Fall: Stehen alle Navigationsziele zwar in der
    spine, fehlen aber sämtlich im Archiv, bleibt die Zusicherung aus dem Kommentar „Befund
    2, Review Runde 1" erhalten — das ist materiell eine fehlende Navigation und fällt auf
    die spine samt Hinweis zurück, statt eine Kapitelliste mit `notice=None` zu liefern,
    obwohl kein einziges ihrer Zieldokumente lesbar ist."""
    path = tmp_path / "all_targets_missing.epub"
    _write_all_targets_missing_epub(path)

    result = epub.read_structure(path)

    assert result.notice == epub.NAVIGATION_MISSING_NOTICE
    assert [chapter.documents for chapter in result.chapters] == [["OEBPS/chapterc.xhtml"]]


# ------------------------------------------- Lokale Vorrichtung: leeres erstes dc:title

_EMPTY_FIRST_METADATA_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

# Manche Konvertate stellen ein leeres dc:title voran und führen den echten Titel erst als
# zweites. Das erste dc:title trägt reinen
# Leerraum statt gar keines Textes: Nur so deckt der Test beide Hälften von `if
# found.text and found.text.strip():` ab, nicht nur die erste (found.text is None wäre
# von `if found.text:` allein schon abgefangen). dc:creator trägt zusätzlich zwei
# nichtleere Einträge, um zu belegen, dass sie nicht zusammengeführt werden.
_EMPTY_FIRST_METADATA_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:empty-first-metadata-test</dc:identifier>
    <dc:title>   </dc:title>
    <dc:title>Titel nach leerem Titel</dc:title>
    <dc:creator></dc:creator>
    <dc:creator>Erste Autorin</dc:creator>
    <dc:creator>Zweite Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>
"""

_EMPTY_FIRST_METADATA_CHAPTER_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter One</title></head>
<body><p>Chapter One</p></body>
</html>
"""


def _write_empty_first_metadata_epub(path: Path) -> None:
    """Baut ein Mini-EPUB ohne Navigation, dessen `dc:title` erst im zweiten, nichtleeren
    Element den echten Titel trägt."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _EMPTY_FIRST_METADATA_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _EMPTY_FIRST_METADATA_OPF)
        archive.writestr("OEBPS/chapter1.xhtml", _EMPTY_FIRST_METADATA_CHAPTER_XHTML)


def test_read_structure_uses_the_first_nonempty_title_when_an_earlier_one_is_empty(
    tmp_path: Path,
) -> None:
    """Ist das erste `dc:title` leer, wird das zweite, nichtleere
    Element gelesen, statt die Datei fälschlich als titellos abzulehnen. Mehrere
    `dc:creator` werden dabei nicht zusammengeführt — `book.author` bleibt der erste
    nichtleere Wert."""
    path = tmp_path / "empty_first_metadata.epub"
    _write_empty_first_metadata_epub(path)

    result = epub.read_structure(path)

    assert result.book.title == "Titel nach leerem Titel"
    assert result.book.author == "Erste Autorin"


# ------------------- Lokale Vorrichtung: verschachtelte Verzeichnisse, prozentkodiertes Ziel

_NESTED_NAV_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_NESTED_NAV_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:nested-nav-test</dc:identifier>
    <dc:title>Verschachteltes Buch</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav/toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="text/chapter%201.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="text/chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
"""

# Zwei Ziele mit "../" von EPUB/nav/ aus, eines davon prozentkodiert (Leerzeichen im
# tatsächlichen ZIP-Namen). Anders als in tests/conftest.py, wo OPF und Navigation flach
# im selben Verzeichnis liegen, ist die Navigations-Basis hier von der OPF-Basis nicht zu
# verwechseln (Befund 5, Review Runde 1).
_NESTED_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="../text/chapter%201.xhtml">Kapitel eins</a></li>
      <li><a href="../text/chapter2.xhtml">Kapitel zwei</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _nested_nav_chapter_xhtml(title: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body><p>{title}</p></body>
</html>
"""


def _write_nested_nav_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen OPF (`EPUB/package.opf`) und Navigation
    (`EPUB/nav/toc.xhtml`) in getrennten Verzeichnissen liegen, mit `../`-Zielen
    (Befund 5, Review Runde 1: In tests/conftest.py und beiden echten Dateien liegt alles
    flach in OEBPS/, wodurch die Navigations-Basis von der OPF-Basis nicht zu
    unterscheiden ist). Ein Kapitel trägt zusätzlich einen ZIP-Namen mit Leerzeichen
    (`text/chapter 1.xhtml`) und wird in OPF und Navigation prozentkodiert referenziert
    (`chapter%201.xhtml`, Befund 1 und 6, Review Runde 1)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _NESTED_NAV_CONTAINER_XML)
        archive.writestr("EPUB/package.opf", _NESTED_NAV_OPF)
        archive.writestr("EPUB/nav/toc.xhtml", _NESTED_NAV_XHTML)
        archive.writestr("EPUB/text/chapter 1.xhtml", _nested_nav_chapter_xhtml("Kapitel eins"))
        archive.writestr("EPUB/text/chapter2.xhtml", _nested_nav_chapter_xhtml("Kapitel zwei"))


# --------------------------- Lokale Vorrichtung: Navigation ohne auflösbares Ziel (Befund 2)

_UNRESOLVABLE_NAV_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_UNRESOLVABLE_NAV_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:unresolvable-nav-test</dc:identifier>
    <dc:title>Buch ohne auflösbare Navigation</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
"""

# Nennt ein Ziel, das weder in der spine noch überhaupt im Archiv vorkommt — die
# Navigation liefert damit einen Eintrag, aus dem sich kein einziges Kapitel ergibt.
_UNRESOLVABLE_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="does-not-exist.xhtml">Toter Verweis</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_unresolvable_nav_epub(path: Path) -> None:
    """Baut ein Mini-EPUB, dessen Navigation vorhanden ist, aber auf kein Dokument der
    spine zeigt — materiell eine fehlende Navigation (Befund 2, Review Runde 1)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _UNRESOLVABLE_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _UNRESOLVABLE_NAV_OPF)
        archive.writestr("OEBPS/nav.xhtml", _UNRESOLVABLE_NAV_XHTML)
        archive.writestr("OEBPS/chapter1.xhtml", _reordered_nav_chapter_xhtml("Chapter 1"))
        archive.writestr("OEBPS/chapter2.xhtml", _reordered_nav_chapter_xhtml("Chapter 2"))


# --------------------------- Lokale Vorrichtung: epub:type mit mehreren Begriffen (Befund 3)

_MULTI_TYPE_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc bodymatter">
    <ol>
      <li><a href="chaptera.xhtml">Label A</a></li>
      <li><a href="chapterb.xhtml">Label B</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _write_multi_type_nav_epub(path: Path) -> None:
    """Wie `_write_reordered_nav_epub`, aber `epub:type="toc bodymatter"` statt nur
    `"toc"` — epub:type ist eine leerzeichengetrennte Liste (Befund 3, Review Runde 1)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _REORDERED_NAV_OPF)
        archive.writestr("OEBPS/nav.xhtml", _MULTI_TYPE_NAV_XHTML)
        archive.writestr("OEBPS/chaptera.xhtml", _reordered_nav_chapter_xhtml("Chapter A"))
        archive.writestr("OEBPS/chapterb.xhtml", _reordered_nav_chapter_xhtml("Chapter B"))


# ------------------- Lokale Vorrichtung: nav.xhtml ohne Treffer, toc.ncx daneben (Befund 4)

_EMPTY_NAV_WITH_NCX_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:empty-nav-with-ncx-test</dc:identifier>
    <dc:title>Buch mit leerer Navigation und toc.ncx</dc:title>
    <dc:creator>Test Autorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="chap1" href="chaptera.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapterb.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
  </spine>
</package>
"""

# Kein <nav epub:type="toc">, nur "landmarks" — _read_nav liefert daraus keinen Eintrag.
_EMPTY_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="landmarks">
    <ol>
      <li><a href="chaptera.xhtml">Anfang</a></li>
    </ol>
  </nav>
</body>
</html>
"""

_EMPTY_NAV_WITH_NCX_NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head></head>
  <docTitle><text>Buch mit leerer Navigation und toc.ncx</text></docTitle>
  <navMap>
    <navPoint id="np1">
      <navLabel><text>Label A aus der ncx</text></navLabel>
      <content src="chaptera.xhtml"/>
    </navPoint>
    <navPoint id="np2">
      <navLabel><text>Label B aus der ncx</text></navLabel>
      <content src="chapterb.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""


def _write_empty_nav_with_ncx_epub(path: Path) -> None:
    """`nav.xhtml` ist vorhanden, nennt aber keine `<nav epub:type="toc">` — die daneben
    liegende `toc.ncx` muss trotzdem versucht werden, der EPUB-3-Vorrang bleibt dabei
    erhalten (Befund 4, Review Runde 1)."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _EMPTY_NAV_WITH_NCX_OPF)
        archive.writestr("OEBPS/nav.xhtml", _EMPTY_NAV_XHTML)
        archive.writestr("OEBPS/toc.ncx", _EMPTY_NAV_WITH_NCX_NCX)
        archive.writestr("OEBPS/chaptera.xhtml", _reordered_nav_chapter_xhtml("Chapter A"))
        archive.writestr("OEBPS/chapterb.xhtml", _reordered_nav_chapter_xhtml("Chapter B"))


def test_acceptance_1_resolves_percent_encoded_targets_across_nested_directories(
    tmp_path: Path,
) -> None:
    """Abnahmekriterium 1: Die Kapitelliste stimmt mit dem Inhaltsverzeichnis der Datei
    überein — auch wenn OPF und Navigation in getrennten Verzeichnissen mit `../`-Zielen
    liegen und ein Ziel prozentkodiert ist (`chapter%201.xhtml` für die Datei
    `chapter 1.xhtml`, Befund 1, 5 und 6, Review Runde 1)."""
    path = tmp_path / "nested_nav.epub"
    _write_nested_nav_epub(path)

    result = epub.read_structure(path)

    assert result.notice is None
    assert [chapter.documents for chapter in result.chapters] == [
        ["EPUB/text/chapter 1.xhtml"],
        ["EPUB/text/chapter2.xhtml"],
    ]
    assert [chapter.title for chapter in result.chapters] == ["Kapitel eins", "Kapitel zwei"]


def test_acceptance_1_falls_back_to_spine_with_notice_when_navigation_targets_do_not_resolve(
    tmp_path: Path,
) -> None:
    """Abnahmekriterium 1, technik.md §8: Nennt die Navigation nur Ziele, die sich nicht
    auflösen lassen, ist das materiell eine fehlende Navigation — die Datei fällt auf die
    spine zurück, samt Hinweis, statt mit einem Fehler abzubrechen (Befund 2, Review
    Runde 1)."""
    path = tmp_path / "unresolvable_nav.epub"
    _write_unresolvable_nav_epub(path)

    result = epub.read_structure(path)

    assert result.notice == epub.NAVIGATION_MISSING_NOTICE
    assert [chapter.documents for chapter in result.chapters] == [
        ["OEBPS/chapter1.xhtml"],
        ["OEBPS/chapter2.xhtml"],
    ]


def test_read_structure_recognizes_navigation_with_additional_epub_type_terms(
    tmp_path: Path,
) -> None:
    """`epub:type` ist eine leerzeichengetrennte Liste: `epub:type="toc bodymatter"` muss
    weiterhin als Inhaltsverzeichnis erkannt werden, wie es bei `properties="nav"` schon
    für mehrere Werte gilt (Befund 3, Review Runde 1)."""
    path = tmp_path / "multi_type_nav.epub"
    _write_multi_type_nav_epub(path)

    result = epub.read_structure(path)

    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == ["Label A", "Label B"]


def test_read_structure_falls_back_to_ncx_when_nav_is_present_but_yields_no_entry(
    tmp_path: Path,
) -> None:
    """Ist `nav.xhtml` vorhanden, nennt aber keine verwertbare `<nav epub:type="toc">`,
    wird die daneben liegende `toc.ncx` versucht, bevor auf die spine zurückgefallen wird
    — der EPUB-3-Vorrang bleibt dabei erhalten (Befund 4, Review Runde 1)."""
    path = tmp_path / "empty_nav_with_ncx.epub"
    _write_empty_nav_with_ncx_epub(path)

    result = epub.read_structure(path)

    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == [
        "Label A aus der ncx",
        "Label B aus der ncx",
    ]


def test_missing_package_file_referenced_in_container_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): Nennt `container.xml` eine Package-Datei, die im
    Archiv fehlt, ist das ein sichtbarer Fehlschlag mit deutscher Meldung (dokumentation.md
    §1) — kein englischer `KeyError` aus `zipfile` (Befund 8, Review Runde 1)."""
    path = tmp_path / "missing_opf.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _REORDERED_NAV_CONTAINER_XML)

    with pytest.raises(ValueError, match=r"OEBPS/content.opf.*fehlt im Archiv"):
        epub.read_structure(path)


def test_missing_file_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): Eine fehlende Datei ist ein sichtbarer Fehlschlag
    mit deutscher Meldung (dokumentation.md §1) — nicht nur ein beliebiger
    FileNotFoundError, den auch `zipfile.ZipFile` selbst ungeprüft geworfen hätte."""
    missing = tmp_path / "does_not_exist.epub"

    with pytest.raises(FileNotFoundError, match="EPUB nicht lesbar"):
        epub.read_structure(missing)


# ------------------------------------------------------- Echte Dateien (bauplan.md T12)


@pytest.mark.needs_epub
def test_acceptance_1_matches_the_measured_unique_chapter_count_for_real_books(
    real_epub_paths: dict[str, Path],
) -> None:
    """Abnahmekriterium 1 gegen die echten Dateien (dokumentation.md §5, „Was über den
    Inhalt einer Fremdquelle behauptet wird, wird zusätzlich gegen das echte Gegenüber
    geprüft"): technik.md §8 misst 14 eindeutige Navigationsziele für Sherlock Holmes und
    22 für Dorian Gray — dieselben Zahlen, gegen die `tools/epub_check.py` misst."""
    sherlock = epub.read_structure(real_epub_paths["sherlock"])
    dorian_gray = epub.read_structure(real_epub_paths["dorian_gray"])

    assert len(sherlock.chapters) == 14
    assert sherlock.notice is None
    assert len(dorian_gray.chapters) == 22
    assert dorian_gray.notice is None


@pytest.mark.needs_epub
def test_no_spine_document_from_the_first_navigation_target_onward_is_lost_or_duplicated(
    real_epub_paths: dict[str, Path],
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Jedes spine-Dokument ab dem
    ersten Navigationsziel gehört zu genau einem Kapitel — geprüft
    gegen die echte spine der Package-Datei (dokumentation.md §5, „Was über den Inhalt
    einer Fremdquelle behauptet wird, wird zusätzlich gegen das echte Gegenüber
    geprüft")."""
    for path in real_epub_paths.values():
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            package = epub._read_package(archive, epub._find_opf(archive, path), path)
        structure = epub.read_structure(path)

        assigned = [document for chapter in structure.chapters for document in chapter.documents]
        assert len(assigned) == len(set(assigned)), f"{path}: ein Dokument gehört zu zwei Kapiteln"

        first_target = structure.chapters[0].documents[0]
        first_target_index = package.spine_documents.index(first_target)
        expected = [
            document
            for document in package.spine_documents[first_target_index:]
            if document in names
        ]
        assert assigned == expected, f"{path}: Dokumente der spine sind verlorengegangen"


@pytest.mark.needs_epub
def test_read_structure_reads_metadata_and_first_chapter_title_for_a_real_book(
    real_epub_paths: dict[str, Path],
) -> None:
    """Gegenprobe gegen die echte Datei: Titel, Autor und die Beschriftung des ersten
    Kapitels aus der echten Navigation, nicht nur aus der Mini-Vorrichtung."""
    result = epub.read_structure(real_epub_paths["sherlock"])

    assert result.book.title == "The Adventures of Sherlock Holmes"
    assert result.book.author == "Arthur Conan Doyle"
    assert result.chapters[0].title == "The Adventures of Sherlock Holmes"
    assert result.chapters[1].title == "I. A SCANDAL IN BOHEMIA"


@pytest.mark.needs_epub
def test_read_structure_deduplicates_a_trailing_navigation_entry_in_a_real_book(
    real_epub_paths: dict[str, Path],
) -> None:
    """technik.md §8, Sherlock-Fall: „Contents" und die Unterpunkte I./II./III. einer
    Erzählung zeigen auf dasselbe Dokument wie ihr übergeordneter Eintrag. Am anderen Ende
    zeigt bei Dorian Gray die Gutenberg-Lizenz auf dasselbe Dokument wie „CHAPTER XX." —
    dessen frühere Beschriftung gewinnt, die Lizenz erzeugt kein eigenes Kapitel."""
    result = epub.read_structure(real_epub_paths["dorian_gray"])

    assert result.chapters[-1].title == "CHAPTER XX."


@pytest.mark.needs_epub
def test_sherlock_holmes_folds_entirely_to_level_zero_despite_nested_navpoints(
    real_epub_paths: dict[str, Path],
) -> None:
    """technik.md §8, „Unterkapitel gibt es": `sherlock.epub` verschachtelt die drei Kinder
    I./II./III. unter „I. A SCANDAL IN BOHEMIA", alle über `#anker` auf dasselbe Dokument
    wie der Elternteil. Nach dem Zusammenfalten (`_deduplicate_by_target`) liegt die ganze
    Kapitelliste auf Ebene 0 — keine einzige eingerückte Zeile, obwohl die Datei
    verschachtelt ist. (Die eigentliche Absicherung der Verschachtelungstiefe liefert
    `test_nested_toc_ncx_reports_the_level_of_each_entry` an einer Vorrichtung mit
    tatsächlichen Ebenen über 0 — gegen diese echte Datei allein wäre „liefert überall 0"
    kein Unterschied zu einer Umsetzung ohne jede Tiefenmessung, dokumentation.md §5)."""
    result = epub.read_structure(real_epub_paths["sherlock"])

    assert [chapter.level for chapter in result.chapters] == [0] * len(result.chapters)


@pytest.mark.needs_epub
def test_dorian_gray_has_no_nested_navigation_and_stays_at_level_zero(
    real_epub_paths: dict[str, Path],
) -> None:
    """Nachmessung (Auftrag Teilaufgabe 3): `dorian_gray.epub` führt anders als
    `sherlock.epub` überhaupt keine verschachtelten `navPoint` — nachgesehen im Archiv
    (`OEBPS/toc.ncx`, 28.08.2026: 24 `navPoint`, alle unmittelbar unter `navMap`). Die
    Kapitelliste liegt deshalb ebenfalls vollständig auf Ebene 0, aber weil die Datei
    flach ist, nicht weil etwas zusammengefaltet wurde."""
    result = epub.read_structure(real_epub_paths["dorian_gray"])

    assert [chapter.level for chapter in result.chapters] == [0] * len(result.chapters)


# ============================================================ bauplan.md T12b: Fließtext

_TEST_BOOK = Book(title="Testbuch", author="Test Autorin")


def _chapter_reference(document: str, title: str = "Kapitel 1") -> epub.ChapterReference:
    return epub.ChapterReference(number=1, title=title, documents=[document])


def _write_single_document_epub(path: Path, *, document: str, xhtml: str) -> None:
    """Baut ein EPUB, das nur aus dem einen zu lesenden Inhaltsdokument besteht.
    `read_chapter` (T12b) liest weder `container.xml` noch die Package-Datei — anders als
    `read_structure` (T12) braucht die Vorrichtung deshalb keine vollständige Struktur."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr(document, xhtml)


# ------------------------------------------------- Lokale Vorrichtung: Skripte und Absätze

_MARKUP_NOISE_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Kapitelkopf, kein Fließtext</title>
<style>body { color: red; }</style>
<script>var geheim = "sollte nie im Fließtext stehen";</script>
</head>
<body>
<script>document.write("auch das nicht");</script>
<p>Erster Absatz mit echtem Fließtext.</p><p>Zweiter Absatz, durch eine Absatzgrenze getrennt.</p>
</body>
</html>
"""


def test_read_chapter_excludes_script_and_style_content_from_the_flowing_text(
    tmp_path: Path,
) -> None:
    """Was am Ende in die Wortschatzextraktion geht: Skripte und Stilangaben dürfen nicht
    als Wörter durchschlagen (bauplan.md T12b)."""
    path = tmp_path / "markup_noise.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MARKUP_NOISE_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "sollte nie im Fließtext stehen" not in chapter.text
    assert "auch das nicht" not in chapter.text
    assert "Kapitelkopf, kein Fließtext" not in chapter.text


def test_read_chapter_keeps_a_paragraph_boundary_between_adjacent_paragraphs(
    tmp_path: Path,
) -> None:
    """Absatzgrenzen müssen erhalten bleiben, weil T3 Belegsätze daraus zieht (bauplan.md
    T12b) — zwei Absätze dürfen im Fließtext nicht zusammenkleben."""
    path = tmp_path / "markup_noise.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MARKUP_NOISE_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "Erster Absatz mit echtem Fließtext.\nZweiter Absatz" in chapter.text


def test_read_chapter_reads_the_text_of_every_document_in_a_multi_document_chapter(
    mini_epub_with_navigation: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": `read_chapter` liest alle Dokumente
    eines Kapitels und fügt ihren Fließtext mit einer Absatzgrenze zusammen wie zwischen zwei
    Blockelementen — chapter3.xhtml gehört zum zweiten Kapitel dieser Vorrichtung und muss im
    gelesenen Text enthalten sein."""
    structure = epub.read_structure(mini_epub_with_navigation)

    chapter = epub.read_chapter(mini_epub_with_navigation, structure.book, structure.chapters[1])

    assert "This is the second chapter, shorter than the first one." in chapter.text
    assert "This is the third chapter, which the navigation never names." in chapter.text
    # Absatzgrenze am Dokumentwechsel: ein einzelner Zeilenumbruch, kein Zusammenkleben.
    assert "This is the second chapter, shorter than the first one.\nChapter Three" in chapter.text


# --------------------------------------- Lokale Vorrichtung: Vorspann- und Impressum-Marken

_START_MARKER_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Vorspann</title></head>
<body>
<p>Vorspann-Absatz vor der Startmarke, der aussteuern muss.</p>
<p>*** START OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Erster echter Satz nach der Startmarke.</p>
</body>
</html>
"""

_END_MARKER_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Impressum</title></head>
<body>
<p>Letzter echter Satz vor der Endmarke.</p>
<p>*** END OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Lizenztext, der aussteuern muss.</p>
</body>
</html>
"""

# Wie bei Dorian Gray (technik.md §8): Ein Kapitel und die angehängte Lizenz teilen sich
# dasselbe Dokument — die Endmarke muss mitten im Dokument greifen, nicht nur am Rand.
_MIXED_MARKER_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Letztes Kapitel mit angehängter Lizenz</title></head>
<body>
<p>Echter letzter Satz des Kapitels.</p>
<p>*** END OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Lizenztext, der aussteuern muss.</p>
</body>
</html>
"""


def test_read_chapter_removes_the_front_matter_before_the_gutenberg_start_marker(
    tmp_path: Path,
) -> None:
    """Vorspann aussteuern (bauplan.md T12b): Text vor „*** START OF THE PROJECT
    GUTENBERG …" fällt weg — dieselbe Marke wie in tools/coverage_check.py
    (GUTENBERG_START)."""
    path = tmp_path / "start_marker.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_START_MARKER_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "Vorspann-Absatz" not in chapter.text
    assert chapter.text == "Erster echter Satz nach der Startmarke."


def test_read_chapter_removes_the_back_matter_after_the_gutenberg_end_marker(
    tmp_path: Path,
) -> None:
    """Impressum aussteuern (bauplan.md T12b): Text nach „*** END OF THE PROJECT
    GUTENBERG …" fällt weg — dieselbe Marke wie in tools/coverage_check.py
    (GUTENBERG_END)."""
    path = tmp_path / "end_marker.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_END_MARKER_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "Lizenztext" not in chapter.text
    assert chapter.text == "Letzter echter Satz vor der Endmarke."


def test_read_chapter_keeps_real_content_that_shares_a_document_with_the_license(
    tmp_path: Path,
) -> None:
    """technik.md §8, Dorian-Gray-Fall: Die Gutenberg-Lizenz kann demselben Dokument wie
    das letzte Kapitel angehängt sein — die Endmarke muss die Lizenz aussteuern, ohne den
    echten Kapiteltext davor zu verlieren."""
    path = tmp_path / "mixed_marker.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MIXED_MARKER_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert chapter.text == "Echter letzter Satz des Kapitels."


def _write_multi_document_epub(path: Path, documents: dict[str, str]) -> None:
    """Wie `_write_single_document_epub`, aber für mehrere Inhaltsdokumente eines Kapitels
    (technik.md §8, „Ein Kapitel ist nicht ein Dokument") — `read_chapter` braucht dafür
    weiterhin weder
    `container.xml` noch die Package-Datei."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        for document, xhtml in documents.items():
            archive.writestr(document, xhtml)


_MULTI_DOCUMENT_START_MARKER_FIRST_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Vorspann, erstes Dokument</title></head>
<body>
<p>Vorspann-Absatz im ersten Dokument, der vollständig aussteuern muss, weil die
Startmarke erst im zweiten Dokument steht.</p>
</body>
</html>
"""

_MULTI_DOCUMENT_START_MARKER_SECOND_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Vorspann, zweites Dokument</title></head>
<body>
<p>Vorspann-Absatz im zweiten Dokument vor der Marke, der ebenfalls aussteuern muss.</p>
<p>*** START OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Erster echter Satz nach der Startmarke.</p>
</body>
</html>
"""


def test_read_chapter_removes_the_entire_first_document_when_the_start_marker_is_in_the_second(
    tmp_path: Path,
) -> None:
    """Befund 2, Review Runde 2: `_remove_boilerplate` läuft auf dem bereits
    zusammengefügten Text des Kapitels, nicht je Dokument, weil der Vorspann über die
    Dokumentgrenze reichen kann. Steht die Startmarke erst im zweiten Dokument eines
    mehrteiligen Kapitels, fällt deshalb der vollständige Text des ersten Dokuments mit weg
    — nicht nur der Text vor der Marke im zweiten."""
    path = tmp_path / "multi_document_start_marker.epub"
    _write_multi_document_epub(
        path,
        {
            "OEBPS/front.xhtml": _MULTI_DOCUMENT_START_MARKER_FIRST_XHTML,
            "OEBPS/chapter.xhtml": _MULTI_DOCUMENT_START_MARKER_SECOND_XHTML,
        },
    )
    chapter = epub.ChapterReference(
        number=1, title="Kapitel 1", documents=["OEBPS/front.xhtml", "OEBPS/chapter.xhtml"]
    )

    result = epub.read_chapter(path, _TEST_BOOK, chapter)

    assert "Vorspann-Absatz" not in result.text
    assert result.text == "Erster echter Satz nach der Startmarke."


def test_read_chapter_leaves_text_unchanged_without_a_gutenberg_marker(tmp_path: Path) -> None:
    """technik.md §8, „epub:type gibt es in der Praxis nicht": Ohne Project-Gutenberg-Marke
    bleibt der Text unverändert — eine allgemeine Schwelle ist nicht gebaut (Regel 14)."""
    path = tmp_path / "markup_noise.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MARKUP_NOISE_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert chapter.text == (
        "Erster Absatz mit echtem Fließtext.\nZweiter Absatz, durch eine Absatzgrenze getrennt."
    )


# --------------------------------------------------- Die drei Ablehnfälle (bauplan.md T12b)


def test_read_chapter_reports_a_missing_file(tmp_path: Path) -> None:
    """Regel 13 (Befund 12, Review Runde 2): Eine fehlende Datei bekommt dieselbe deutsche
    Meldung wie `read_structure` — nicht den englischen `FileNotFoundError`, den
    `zipfile.ZipFile` selbst ungeprüft geworfen hätte."""
    missing = tmp_path / "does_not_exist.epub"

    with pytest.raises(FileNotFoundError, match="EPUB nicht lesbar"):
        epub.read_chapter(missing, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def test_read_chapter_reports_a_file_that_is_not_a_zip_archive(tmp_path: Path) -> None:
    """Regel 13: Kein `except`, das nur protokolliert und weiterläuft — eine Datei ohne
    ZIP-Archiv wird gemeldet statt leer zurückgegeben (bauplan.md T12b)."""
    path = tmp_path / "not_an_epub.epub"
    path.write_bytes(b"dies ist kein ZIP-Archiv")

    with pytest.raises(ValueError, match=r"keine gültige EPUB-Datei \(kein ZIP-Archiv\)"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def _corrupt_crc_of_zip_entry(path: Path, document: str) -> None:
    """Verfälscht die CRC-32-Prüfsumme eines Eintrags in dessen lokalem Header **und** im
    zentralen Verzeichnis, ohne die komprimierten Daten anzurühren — `zipfile` öffnet das
    Archiv trotzdem klaglos und erkennt den Schaden erst beim tatsächlichen Lesen des
    Eintrags (Befund 11, Review Runde 2)."""
    data = bytearray(path.read_bytes())
    target = document.encode("utf-8")

    offset = 0
    while (offset := data.find(b"PK\x03\x04", offset)) != -1:
        length = int.from_bytes(data[offset + 26 : offset + 28], "little")
        if bytes(data[offset + 30 : offset + 30 + length]) == target:
            crc = int.from_bytes(data[offset + 14 : offset + 18], "little")
            data[offset + 14 : offset + 18] = (crc ^ 0xFFFFFFFF).to_bytes(4, "little")
        offset += 4

    offset = 0
    while (offset := data.find(b"PK\x01\x02", offset)) != -1:
        length = int.from_bytes(data[offset + 28 : offset + 30], "little")
        if bytes(data[offset + 46 : offset + 46 + length]) == target:
            crc = int.from_bytes(data[offset + 16 : offset + 20], "little")
            data[offset + 16 : offset + 20] = (crc ^ 0xFFFFFFFF).to_bytes(4, "little")
        offset += 4

    path.write_bytes(bytes(data))


def test_read_chapter_does_not_call_a_corrupted_entry_a_missing_zip_archive(tmp_path: Path) -> None:
    """Befund 11, Review Runde 2, nachgebessert durch Befund 2 (Durchsicht 29715b2): Nur
    `zipfile.ZipFile(path)` steht in `_open_archive_for_chapter`s `try` — eine kaputte
    CRC-Summe beim Lesen des Kapiteldokuments wird deshalb nicht mehr als „kein
    ZIP-Archiv" gemeldet, obwohl sich das Archiv öffnen ließ. Sichtbar bleibt der
    Fehlschlag trotzdem, seit Befund 2 aber mit einer deutschen Meldung statt des
    englischen `zipfile.BadZipFile`, das `cli.main` sonst nicht abfängt (Regel 13)."""
    path = tmp_path / "corrupted_entry.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MARKUP_NOISE_XHTML)
    _corrupt_crc_of_zip_entry(path, "OEBPS/chapter.xhtml")

    with pytest.raises(ValueError, match=r"OEBPS/chapter\.xhtml ist beschädigt"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def test_count_chapter_words_reports_unknown_for_a_corrupted_document_but_counts_the_rest(
    tmp_path: Path,
) -> None:
    """Befund 2 (Durchsicht 29715b2): Eine kaputte CRC-Prüfsumme in einem Kapiteldokument
    macht bislang das ganze Buch unbenutzbar (`_choose_chapter` zählt vor der Auswahl) —
    die übrigen Kapitel müssen ihre Zahl trotzdem bekommen, das betroffene wird `None`,
    nicht `0` (Regel 13)."""
    path = tmp_path / "one_corrupted_document.epub"
    _write_multi_document_epub(
        path,
        {"OEBPS/chapter1.xhtml": _MARKUP_NOISE_XHTML, "OEBPS/chapter2.xhtml": _MARKUP_NOISE_XHTML},
    )
    _corrupt_crc_of_zip_entry(path, "OEBPS/chapter2.xhtml")
    chapters = [
        epub.ChapterReference(number=1, title="Erstes Kapitel", documents=["OEBPS/chapter1.xhtml"]),
        epub.ChapterReference(
            number=2, title="Zweites Kapitel", documents=["OEBPS/chapter2.xhtml"]
        ),
    ]

    counts = epub.count_chapter_words(path, chapters)

    assert counts[1] == 11
    assert counts[2] is None


def _encryption_xml_for(*documents: str) -> str:
    """`META-INF/encryption.xml` nach OCF-Norm, mit je einer `CipherReference` je
    übergebenem Dokument — dieselbe Form, die Calibre, InDesign und Sigil auch für bloße
    Schriftverschleierung erzeugen (Befund 6, Review Runde 2)."""
    references = "\n      ".join(f'<CipherReference URI="{document}"/>' for document in documents)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#">
    <EncryptionMethod Algorithm="http://www.idpf.org/2008/embedding"/>
    <CipherData>
      {references}
    </CipherData>
  </EncryptedData>
</encryption>
"""


def test_read_chapter_reports_an_encrypted_file(tmp_path: Path) -> None:
    """Regel 13: Ein verschlüsseltes EPUB wird gemeldet statt leer zurückgegeben (bauplan.md
    T12b) — Kopierschutz wird nicht umgangen (konzept.md, Schritt 1).
    `META-INF/encryption.xml` nennt das gelesene Kapiteldokument als `CipherReference`
    (Befund 6, Review Runde 2): bloße Anwesenheit der Datei genügt seither nicht mehr."""
    path = tmp_path / "encrypted.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/encryption.xml", _encryption_xml_for("OEBPS/chapter.xhtml"))
        archive.writestr("OEBPS/chapter.xhtml", _MARKUP_NOISE_XHTML)

    with pytest.raises(ValueError, match=r"verschlüsselt \(META-INF/encryption\.xml\)"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def test_read_chapter_ignores_encryption_xml_that_only_obfuscates_a_font(tmp_path: Path) -> None:
    """Befund 6, Review Runde 2: `META-INF/encryption.xml` kennzeichnet laut OCF-Norm auch
    bloße Schriftverschleierung (`Algorithm=".../2008/embedding"`) ohne jeden Kopierschutz
    auf dem Text — ein DRM-freies EPUB darf deshalb nicht allein wegen ihrer Anwesenheit
    abgelehnt werden, solange keine `CipherReference` auf das Kapiteldokument zeigt."""
    path = tmp_path / "font_obfuscation.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/encryption.xml", _encryption_xml_for("OEBPS/fonts/text.otf"))
        archive.writestr("OEBPS/chapter.xhtml", _MARKUP_NOISE_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "Erster Absatz mit echtem Fließtext." in chapter.text


# Absichtlich unvollständig — ein abgebrochenes Konvertat statt eines wohlgeformten
# Dokuments (Befund 2, Durchsicht 29715b2).
_MALFORMED_ENCRYPTION_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
    '  <EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#">\n'
    '    <EncryptionMethod Algorithm="http://www.idpf.org/2008/embedding"'
)


def test_read_chapter_reports_a_malformed_encryption_xml_in_german(tmp_path: Path) -> None:
    """Befund 2 (Durchsicht 29715b2): Eine unvollständige `META-INF/encryption.xml` wirft
    beim Parsen `xml.etree.ElementTree.ParseError`, einen englischen Fehler, den `cli.main`
    nicht abfängt (Regel 13) — die Meldung muss dieselbe deutsche Form wie die übrigen
    Ablehnfälle bekommen."""
    path = tmp_path / "malformed_encryption.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/encryption.xml", _MALFORMED_ENCRYPTION_XML)
        archive.writestr("OEBPS/chapter.xhtml", _MARKUP_NOISE_XHTML)

    with pytest.raises(
        ValueError, match=r"META-INF/encryption\.xml ist beschädigt \(kein wohlgeformtes XML\)"
    ):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def test_count_chapter_words_reports_unknown_for_every_chapter_behind_a_malformed_encryption_xml(
    tmp_path: Path,
) -> None:
    """Befund 2 (Durchsicht 29715b2): Dieselbe unvollständige `encryption.xml` darf die
    Zählung nicht ebenso englisch abbrechen lassen — jedes betroffene Kapitel wird `None`
    (Regel 13), nicht `0`. Anders als bei der kaputten CRC-Prüfsumme (siehe
    `test_count_chapter_words_reports_unknown_for_a_corrupted_document_but_counts_the_rest`)
    betrifft eine beschädigte `encryption.xml` beide Kapitel gleich: Sie wird für jedes
    Dokument neu geprüft, nicht nur für das eine, das sie beschädigt selbst nennen würde."""
    path = tmp_path / "malformed_encryption_multi.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/encryption.xml", _MALFORMED_ENCRYPTION_XML)
        archive.writestr("OEBPS/chapter1.xhtml", _MARKUP_NOISE_XHTML)
        archive.writestr("OEBPS/chapter2.xhtml", _MARKUP_NOISE_XHTML)
    chapters = [
        epub.ChapterReference(number=1, title="Erstes Kapitel", documents=["OEBPS/chapter1.xhtml"]),
        epub.ChapterReference(
            number=2, title="Zweites Kapitel", documents=["OEBPS/chapter2.xhtml"]
        ),
    ]

    counts = epub.count_chapter_words(path, chapters)

    assert counts[1] is None
    assert counts[2] is None


def test_read_chapter_reports_a_chapter_document_missing_from_the_archive(tmp_path: Path) -> None:
    """Regel 13 (Befund 7, Review Runde 2): Fehlt das Kapiteldokument im Archiv, ist das ein
    sichtbarer Fehlschlag mit deutscher Meldung — kein englischer `KeyError` aus `zipfile`,
    den `archive.read()` sonst ungeprüft geworfen hätte."""
    path = tmp_path / "missing_document.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)

    with pytest.raises(ValueError, match=r"OEBPS/chapter\.xhtml.*fehlt im Archiv"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def _mark_zip_entry_as_password_protected(path: Path, document: str) -> None:
    """Setzt das Verschlüsselungsbit (general purpose bit flag, Bit 0) im lokalen und im
    zentralen Header eines ZIP-Eintrags — `zipfile` kann keine echte Verschlüsselung
    schreiben, wirft beim Lesen aber denselben `RuntimeError` wie ein wirklich
    passwortgeschütztes Archiv, sobald dieses Bit gesetzt ist (Befund 7, Review Runde 2)."""
    data = bytearray(path.read_bytes())
    target = document.encode("utf-8")

    offset = 0
    while (offset := data.find(b"PK\x03\x04", offset)) != -1:
        length = int.from_bytes(data[offset + 26 : offset + 28], "little")
        if bytes(data[offset + 30 : offset + 30 + length]) == target:
            data[offset + 6] |= 0x01
        offset += 4

    offset = 0
    while (offset := data.find(b"PK\x01\x02", offset)) != -1:
        length = int.from_bytes(data[offset + 28 : offset + 30], "little")
        if bytes(data[offset + 46 : offset + 46 + length]) == target:
            data[offset + 8] |= 0x01
        offset += 4

    path.write_bytes(bytes(data))


def test_read_chapter_reports_a_password_protected_zip_entry_as_encrypted(tmp_path: Path) -> None:
    """Regel 13 (Befund 7, Review Runde 2): Ein ZIP-Eintrag kann auch ohne
    `META-INF/encryption.xml` passwortgeschützt sein — der dritte Ablehnfall in anderer
    Gestalt. `zipfile` wirft dafür beim Lesen einen englischen `RuntimeError`, der dieselbe
    deutsche Verschlüsselungsmeldung bekommen muss statt unverändert durchzureichen."""
    path = tmp_path / "password_protected.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_MARKUP_NOISE_XHTML)
    _mark_zip_entry_as_password_protected(path, "OEBPS/chapter.xhtml")

    with pytest.raises(ValueError, match=r"verschlüsselt \(META-INF/encryption\.xml\)"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


def test_read_chapter_reports_bytes_that_are_not_utf8(tmp_path: Path) -> None:
    """Regel 13 (Befund 8, Review Runde 2): Nicht-UTF-8-Bytes werden gemeldet statt mit
    `errors="replace"` still durch U+FFFD ersetzt — sonst landete das Ersatzzeichen im
    Wortschatz, in der Triage und auf der Anki-Karte."""
    path = tmp_path / "invalid_encoding.epub"
    invalid_bytes = b"<html><body><p>Ung\xffltiges UTF-8</p></body></html>"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("OEBPS/chapter.xhtml", invalid_bytes)

    with pytest.raises(ValueError, match=r"OEBPS/chapter\.xhtml ist nicht UTF-8 kodiert"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


_IMAGE_ONLY_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Bildseite</title></head>
<body><img src="page1.png" alt=""/></body>
</html>
"""


def test_read_chapter_reports_a_picture_book_without_text(tmp_path: Path) -> None:
    """Regel 13, technik.md §8 („Bildband ohne Text", 2 Manga mit 0 Wörtern gemessen): Ein
    Kapitel ohne Fließtext wird gemeldet statt leer zurückgegeben (bauplan.md T12b)."""
    path = tmp_path / "picture_book.epub"
    _write_single_document_epub(path, document="OEBPS/page1.xhtml", xhtml=_IMAGE_ONLY_XHTML)

    with pytest.raises(
        ValueError, match=r"Bildseite.*enthält keinen Fließtext.*Bildband ohne Text"
    ):
        epub.read_chapter(
            path, _TEST_BOOK, _chapter_reference("OEBPS/page1.xhtml", title="Bildseite")
        )


_LICENSE_ONLY_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Volle Lizenz</title></head>
<body>
<p>*** END OF THE PROJECT GUTENBERG EBOOK TESTBUCH ***</p>
<p>Lizenztext, der komplett aussteuern muss.</p>
</body>
</html>
"""


def test_read_chapter_reports_when_only_boilerplate_remains_after_removing_it(
    tmp_path: Path,
) -> None:
    """Regel 13 (Befund 1 und 2, Review Runde 2): Ein Dokument, das roh Wörter trägt und
    nach dem Aussteuern von Vorspann und Impressum keine mehr, wird gemeldet statt still als
    leerer Fließtext durchzugehen — nachgewiesen am letzten Sherlock-Kapitel, der vollen
    Gutenberg-Lizenz (siehe Test gegen die echte Datei weiter unten)."""
    path = tmp_path / "license_only.epub"
    _write_single_document_epub(path, document="OEBPS/license.xhtml", xhtml=_LICENSE_ONLY_XHTML)

    with pytest.raises(ValueError, match=r"besteht nur aus Vorspann bzw\. Impressum"):
        epub.read_chapter(
            path, _TEST_BOOK, _chapter_reference("OEBPS/license.xhtml", title="Lizenz")
        )


def test_read_chapter_raises_chapter_without_text_error_not_a_plain_value_error(
    tmp_path: Path,
) -> None:
    """Bauplan-phase2.md AP 4: Beide Kapitel-ohne-Fließtext-Fälle (Bildband, reiner
    Vorspann/Impressum) werfen `ChapterWithoutTextError` — einen `ValueError`-Untertyp mit
    eigenem `skip_reason` —, nicht einen gewöhnlichen `ValueError`. `run_chapter` und
    `pipeline.list_chapters` fangen seither genau diesen Typ statt den Meldungstext zu
    vergleichen; ein Test, der nur `pytest.raises(ValueError, match=...)` prüft (wie die
    beiden Tests oben), würde einen Rückbau auf `ValueError` nicht bemerken, weil ein
    `ChapterWithoutTextError` auch ein `ValueError` ist.

    `skip_reason` trägt seit Befund 2, Durchsicht f1177de, **nicht** mehr denselben Text wie
    `str(error)`: `str(error)` bleibt die volle Meldung mit Pfad und Kapiteltitel,
    `skip_reason` ist die knappe Fassung ohne beides — die Kapitelauswahl der Kommandozeile
    zeigt sie unter einem bereits mit Titel versehenen Kapitel, wo Pfad und Titel nur
    wiederholten, was in derselben Ausgabe schon steht.

    Verfälschungsprobe: `ChapterWithoutTextError`s beide Vorkommen in `epub.read_chapter`
    durch `ValueError` ersetzt (der Stand vor AP 4) ließ diesen Test rot werden, die beiden
    `match=`-Tests oben blieben dabei unverändert grün."""
    picture_book = tmp_path / "picture_book.epub"
    _write_single_document_epub(picture_book, document="OEBPS/page1.xhtml", xhtml=_IMAGE_ONLY_XHTML)
    license_only = tmp_path / "license_only.epub"
    _write_single_document_epub(
        license_only, document="OEBPS/license.xhtml", xhtml=_LICENSE_ONLY_XHTML
    )

    with pytest.raises(epub.ChapterWithoutTextError) as picture_book_error:
        epub.read_chapter(
            picture_book, _TEST_BOOK, _chapter_reference("OEBPS/page1.xhtml", title="Bildseite")
        )
    picture_book_reason = picture_book_error.value.skip_reason
    assert picture_book_reason
    assert str(picture_book) not in picture_book_reason
    assert "Bildseite" not in picture_book_reason
    assert str(picture_book) in str(picture_book_error.value)
    assert "Bildseite" in str(picture_book_error.value)

    with pytest.raises(epub.ChapterWithoutTextError) as license_error:
        epub.read_chapter(
            license_only, _TEST_BOOK, _chapter_reference("OEBPS/license.xhtml", title="Lizenz")
        )
    license_reason = license_error.value.skip_reason
    assert license_reason
    assert str(license_only) not in license_reason
    assert "Lizenz" not in license_reason
    assert str(license_only) in str(license_error.value)
    assert "Lizenz" in str(license_error.value)


def test_read_chapter_reports_an_encrypted_picture_book_as_encrypted_not_as_a_picture_book(
    tmp_path: Path,
) -> None:
    """Befund 9, Review Runde 2: Die Reihenfolge der drei Ablehnfälle ist geprüft, nicht nur
    behauptet — ein verschlüsseltes Kapitel ohne Fließtext muss „verschlüsselt" melden,
    nicht „Bildband ohne Text". Gegen eine absichtlich umgedrehte Reihenfolge einmal rot
    gelaufen (siehe Bericht)."""
    path = tmp_path / "encrypted_picture_book.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/encryption.xml", _encryption_xml_for("OEBPS/page1.xhtml"))
        archive.writestr("OEBPS/page1.xhtml", _IMAGE_ONLY_XHTML)

    with pytest.raises(ValueError, match=r"verschlüsselt \(META-INF/encryption\.xml\)"):
        epub.read_chapter(
            path, _TEST_BOOK, _chapter_reference("OEBPS/page1.xhtml", title="Bildseite")
        )


def test_read_chapter_reports_a_non_zip_file_before_inspecting_its_bytes_for_encryption(
    tmp_path: Path,
) -> None:
    """Befund 9, Review Runde 2: Eine Nicht-ZIP-Datei, deren Bytes zufällig
    `META-INF/encryption.xml` als Text enthalten, muss weiterhin „kein ZIP-Archiv" melden —
    die ZIP-Prüfung steht vor der Verschlüsselungsprüfung. Gegen eine absichtlich
    umgedrehte Reihenfolge einmal rot gelaufen (siehe Bericht)."""
    path = tmp_path / "not_a_zip_with_encryption_text.epub"
    path.write_bytes(b"kein ZIP-Archiv, nennt aber META-INF/encryption.xml im Klartext")

    with pytest.raises(ValueError, match=r"keine gültige EPUB-Datei \(kein ZIP-Archiv\)"):
        epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))


_ENTITIES_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Entitäten</title></head>
<body>
<p>Leerraum:&nbsp;Gedankenstrich&mdash;Anführung&#8217;Kaufmannsund&amp;Ende.</p>
</body>
</html>
"""


def test_read_chapter_resolves_html_entities(tmp_path: Path) -> None:
    """technik.md §8, „befürchtete Bruchstelle": HTML-Entitäten werden aufgelöst
    (`convert_charrefs=True`) statt als literale `&nbsp;` oder `&mdash;` in den Wortschatz
    zu gelangen (Befund 10, Review Runde 2)."""
    path = tmp_path / "entities.epub"
    _write_single_document_epub(path, document="OEBPS/chapter.xhtml", xhtml=_ENTITIES_XHTML)

    chapter = epub.read_chapter(path, _TEST_BOOK, _chapter_reference("OEBPS/chapter.xhtml"))

    assert "Leerraum: Gedankenstrich—Anführung’Kaufmannsund&Ende." in chapter.text
    assert "&nbsp;" not in chapter.text
    assert "&mdash;" not in chapter.text
    assert "&#8217;" not in chapter.text


# ------------------------------------------------------- Echte Dateien (bauplan.md T12b)


@pytest.mark.needs_epub
def test_read_chapter_removes_project_gutenberg_front_matter_from_a_real_book(
    real_epub_paths: dict[str, Path],
) -> None:
    """technik.md §8, Sherlock-Fall: Das erste Kapitel der echten Navigation ist der
    Titel-/Vorspanndokument (`chapters[0]`) — der Gutenberg-Vorspanntext darf danach nicht
    mehr im Fließtext stehen."""
    structure = epub.read_structure(real_epub_paths["sherlock"])

    chapter = epub.read_chapter(real_epub_paths["sherlock"], structure.book, structure.chapters[0])

    assert "This eBook is for the use of anyone" not in chapter.text
    assert "Release date" not in chapter.text


@pytest.mark.needs_epub
def test_read_chapter_reports_the_real_license_chapter_as_boilerplate_only(
    real_epub_paths: dict[str, Path],
) -> None:
    """Regel 13 (Befund 1 und 2, Review Runde 2): Das letzte Kapitel der echten Navigation
    ist die volle Gutenberg-Lizenz (`chapters[-1]`, 18.417 Zeichen vor dem Aussteuern) — die
    Endmarke steht dort an dessen Anfang, danach bleibt kein Fließtext mehr übrig. Statt
    still ein `Chapter` mit leerem Text zurückzugeben, meldet `read_chapter` das."""
    structure = epub.read_structure(real_epub_paths["sherlock"])

    with pytest.raises(ValueError, match=r"nach dem Aussteuern bleibt kein Fließtext übrig"):
        epub.read_chapter(real_epub_paths["sherlock"], structure.book, structure.chapters[-1])


@pytest.mark.needs_epub
def test_read_chapter_keeps_the_real_final_chapter_but_drops_the_appended_license(
    real_epub_paths: dict[str, Path],
) -> None:
    """technik.md §8, Dorian-Gray-Fall: Die Lizenz hängt am selben Dokument wie „CHAPTER
    XX." — der echte Kapiteltext bleibt bis „THE END" erhalten, die angehängte Lizenz
    nicht."""
    structure = epub.read_structure(real_epub_paths["dorian_gray"])

    chapter = epub.read_chapter(
        real_epub_paths["dorian_gray"], structure.book, structure.chapters[-1]
    )

    assert chapter.text.endswith("THE END")
    assert "PLEASE READ THIS BEFORE YOU DISTRIBUTE" not in chapter.text


@pytest.mark.needs_epub
def test_read_chapter_reads_a_real_story_chapter_unchanged(
    real_epub_paths: dict[str, Path],
) -> None:
    """Gegenprobe gegen die echte Datei: Ein gewöhnliches Erzählkapitel ohne
    Gutenberg-Marken bleibt inhaltlich unangetastet."""
    structure = epub.read_structure(real_epub_paths["sherlock"])

    chapter = epub.read_chapter(real_epub_paths["sherlock"], structure.book, structure.chapters[1])

    assert chapter.text.startswith("I.\nA SCANDAL IN BOHEMIA")
    assert "Sherlock Holmes" in chapter.text


# ================================== Wortumfang je Kapitel (technik.md §8, „Was die
# Kapitelliste zusätzlich zeigt")


def test_count_chapter_words_matches_what_read_chapter_actually_returns(
    mini_epub_with_navigation: Path,
) -> None:
    """technik.md §8, „Was die Kapitelliste zusätzlich zeigt": Für jedes Kapitel stimmt der
    gezählte Umfang mit der Zahl der Wörter überein, die
    `read_chapter` für dasselbe Kapitel tatsächlich liefert — die Zusicherung, die Anzeige
    und Wirklichkeit aneinanderbindet."""
    structure = epub.read_structure(mini_epub_with_navigation)

    counts = epub.count_chapter_words(mini_epub_with_navigation, structure.chapters)

    for chapter in structure.chapters:
        actual_text = epub.read_chapter(mini_epub_with_navigation, structure.book, chapter).text
        assert counts[chapter.number] == len(epub._WORD.findall(actual_text))


# Sherlocks 14. Kapitel — die volle Gutenberg-Lizenz, reiner Vorspann/Impressum
# (technik.md §8) — ist unter den echten Dateien das einzige, das `read_chapter` ablehnt
# (nachgeprüft: 13 von 14 Sherlock- und 22 von 22 Dorian-Gray-Kapiteln bestehen die strenge
# Gleichheitsprüfung unten). Der Ausnahmezweig ist deshalb auf genau dieses eine Kapitel
# beschränkt (Befund 1, Durchsicht 29715b2) statt über die ganze Schleife gelegt: Ein
# `except`, das jedes Kapitel abfängt, sichert nichts mehr zu, sobald jedes Kapitel
# unlesbar wird — 36-mal `None` liefe damit ebenso grün durch wie der echte Befund.
_LICENSE_ONLY_REAL_CHAPTER_TITLE = "THE FULL PROJECT GUTENBERG™ LICENSE"


@pytest.mark.needs_epub
def test_count_chapter_words_matches_read_chapter_for_real_books(
    real_epub_paths: dict[str, Path],
) -> None:
    """Dieselbe Zusicherung wie oben, gegen die echten Dateien geprüft (dokumentation.md
    §5, „Was über den Inhalt einer Fremdquelle behauptet wird, wird zusätzlich gegen das
    echte Gegenüber geprüft"), mit einer Untergrenze für die Zahl der tatsächlich streng
    verglichenen Kapitel (Befund 1, Durchsicht 29715b2): 13 von Sherlocks 14 und alle 22
    Dorian-Gray-Kapitel. Sherlocks „THE FULL PROJECT GUTENBERG™ LICENSE" (nur
    Vorspann/Impressum) lehnt `read_chapter` selbst ab (Regel 13) — sein Umfang ist dabei
    echt `0`, nicht unbekannt, denn `_read_chapter_documents` gelingt für dieses Kapitel;
    nur die zusätzliche Prüfung in `read_chapter` lehnt danach ab (derselbe Fall wie
    `test_count_chapter_words_reports_zero_not_unknown_for_a_picture_book_chapter`, hier an
    der Fremdquelle bestätigt)."""
    compared = 0
    for path in real_epub_paths.values():
        structure = epub.read_structure(path)

        counts = epub.count_chapter_words(path, structure.chapters)

        for chapter in structure.chapters:
            count = counts[chapter.number]
            if chapter.title == _LICENSE_ONLY_REAL_CHAPTER_TITLE:
                assert count == 0, (
                    f"{path}: Kapitel {chapter.number} „{chapter.title}“ ist reiner "
                    f"Vorspann/Impressum, sein Umfang ({count}) muss echt 0 sein, nicht "
                    "unbekannt."
                )
                with pytest.raises(ValueError, match=r"besteht nur aus Vorspann bzw\. Impressum"):
                    epub.read_chapter(path, structure.book, chapter)
                continue
            actual_text = epub.read_chapter(path, structure.book, chapter).text
            assert count == len(epub._WORD.findall(actual_text)), (
                f"{path}: Kapitel {chapter.number} „{chapter.title}“"
            )
            compared += 1

    assert compared == 13 + 22, (
        f"{compared} von 35 erwarteten streng verglichenen Kapiteln (13 Sherlock, 22 Dorian "
        "Gray) — die Untergrenze aus Befund 1 (Durchsicht 29715b2) ist verletzt."
    )


@pytest.mark.needs_calibre_split_epub
def test_count_chapter_words_matches_read_chapter_for_dune(real_dune_epub_path: Path) -> None:
    """Dieselbe Zusicherung wie
    `test_count_chapter_words_matches_read_chapter_for_real_books`, hier gegen
    `tools/dune.epub` statt gegen `real_epub_paths` (Vorbefund V-B, Durchsicht f1177de): Die
    beiden dortigen Bücher nehmen nie den Mehrdokument-Zweig aus technik.md §8, „Ein Kapitel
    ist nicht ein Dokument" — genau der Fall, in dem `count_chapter_words` und `read_chapter`
    am ehesten auseinanderfallen könnten, weil beide die zusammengefügte Dokumentliste des
    Kapitels unabhängig durchlaufen. Dune trägt kein Vorspann-/Impressum-Kapitel wie
    Sherlocks Gutenberg-Lizenz; alle vier Kapitel bestehen deshalb die strenge
    Gleichheitsprüfung ohne Ausnahmezweig.

    Verfälschungsprobe: `count_chapter_words` in `libreverbum/epub.py` auf das jeweils erste
    Dokument eines Kapitels beschränkt (`_read_chapter_documents(...)[:1]`, der stille
    Verlust aus technik.md §8, „Ohne die vollständige Dokumentliste wäre das ein stiller
    Verlust") ließ diesen Test rot werden — 20.803 statt 78.774 für Kapitel 2 —, während die
    Sherlock/Dorian-Gray-Fassung oben unverändert grün blieb, weil keines ihrer Kapitel mehr
    als ein Dokument umfasst."""
    structure = epub.read_structure(real_dune_epub_path)
    counts = epub.count_chapter_words(real_dune_epub_path, structure.chapters)

    assert len(structure.chapters) == 4
    for chapter in structure.chapters:
        actual_text = epub.read_chapter(real_dune_epub_path, structure.book, chapter).text
        assert counts[chapter.number] == len(epub._WORD.findall(actual_text)), (
            f"Kapitel {chapter.number} „{chapter.title}“"
        )


def test_count_chapter_words_reports_zero_for_a_chapter_that_is_pure_boilerplate(
    tmp_path: Path,
) -> None:
    """Befund 1, Zusatz (Durchsicht 29715b2): Dieselbe Zusicherung wie
    `test_count_chapter_words_matches_read_chapter_for_real_books` (Sherlocks 14. Kapitel,
    reiner Lizenztext), hier an einer eigenen Vorrichtung (`_LICENSE_ONLY_XHTML`, bereits
    genutzt in `test_read_chapter_reports_when_only_boilerplate_remains_after_removing_it`),
    damit sie nicht allein an einer Fremdquelle hängt: `read_chapter` lehnt das Kapitel ab
    (Regel 13), `count_chapter_words` zählt seinen echten Umfang `0`, nicht `None`."""
    path = tmp_path / "license_only_chapter.epub"
    _write_single_document_epub(path, document="OEBPS/license.xhtml", xhtml=_LICENSE_ONLY_XHTML)
    chapter = epub.ChapterReference(number=1, title="Lizenz", documents=["OEBPS/license.xhtml"])

    with pytest.raises(ValueError, match=r"besteht nur aus Vorspann bzw\. Impressum"):
        epub.read_chapter(path, _TEST_BOOK, chapter)
    counts = epub.count_chapter_words(path, [chapter])

    assert counts[1] == 0


def test_count_chapter_words_counts_every_document_of_a_multi_document_chapter(
    mini_epub_with_navigation: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": ein mehrdokumentiges Kapitel wird über
    alle seine Dokumente gezählt, nicht nur über sein Navigationsziel — chapter2.xhtml und
    chapter3.xhtml gehören beide zum zweiten Kapitel dieser Vorrichtung (Kommentar bei
    `_NAV_ENTRIES` in tests/conftest.py)."""
    structure = epub.read_structure(mini_epub_with_navigation)
    second_chapter = structure.chapters[1]
    assert second_chapter.documents == ["OEBPS/chapter2.xhtml", "OEBPS/chapter3.xhtml"]
    only_first_document = epub.ChapterReference(
        number=second_chapter.number,
        title=second_chapter.title,
        documents=second_chapter.documents[:1],
    )

    full_count = epub.count_chapter_words(mini_epub_with_navigation, [second_chapter])
    partial_count = epub.count_chapter_words(mini_epub_with_navigation, [only_first_document])

    full = full_count[second_chapter.number]
    partial = partial_count[second_chapter.number]
    assert full is not None
    assert partial is not None
    assert full > partial


def test_count_chapter_words_reports_unknown_not_zero_for_a_missing_document(
    tmp_path: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Ein Kapitel mit fehlendem Dokument im
    Archiv liefert unbekannt (`None`), nicht `0` — `0` sähe aus wie ein leeres Kapitel und wäre
    der stille Fehlschlag aus Regel 13. Die übrigen Kapitel bekommen trotzdem ihre Zahl."""
    path = tmp_path / "one_missing_document.epub"
    _write_single_document_epub(path, document="OEBPS/chapter1.xhtml", xhtml=_MARKUP_NOISE_XHTML)
    chapters = [
        epub.ChapterReference(number=1, title="Erstes Kapitel", documents=["OEBPS/chapter1.xhtml"]),
        epub.ChapterReference(
            number=2, title="Zweites Kapitel", documents=["OEBPS/chapter2.xhtml"]
        ),
    ]

    counts = epub.count_chapter_words(path, chapters)

    assert counts[1] == 11
    assert counts[2] is None


def test_count_chapter_words_reports_zero_not_unknown_for_a_picture_book_chapter(
    tmp_path: Path,
) -> None:
    """technik.md §8, „Was gemeldet und nicht verarbeitet wird": Ein Kapitel ohne
    Fließtext (Bildband) hat echt den Umfang `0` — das ist die Wahrheit, keine unbekannte
    Größe, obwohl `read_chapter` dasselbe Kapitel als Bildband ablehnt."""
    path = tmp_path / "picture_book.epub"
    _write_single_document_epub(path, document="OEBPS/page1.xhtml", xhtml=_IMAGE_ONLY_XHTML)
    chapters = [epub.ChapterReference(number=1, title="Bildseite", documents=["OEBPS/page1.xhtml"])]

    counts = epub.count_chapter_words(path, chapters)

    assert counts[1] == 0


def test_count_chapter_words_opens_the_archive_only_once(
    monkeypatch: pytest.MonkeyPatch, mini_epub_with_navigation: Path
) -> None:
    """technik.md §8, „Was die Kapitelliste zusätzlich zeigt": Das Archiv wird einmal
    geöffnet, nicht einmal je Kapitel — sonst kostete jedes zusätzliche
    Kapitel eine weitere Archivöffnung, obwohl genau das vermieden werden soll (Befund 4,
    Durchsicht 29715b2: die vorige Fassung dieser Zeile zitierte Fließtext statt der
    Überschrift, die Verweisform verlangt beides)."""
    structure = epub.read_structure(mini_epub_with_navigation)
    original_zip_file = zipfile.ZipFile
    opened: list[int] = []

    def _counting_zip_file(path: Path) -> zipfile.ZipFile:
        opened.append(1)
        return original_zip_file(path)

    monkeypatch.setattr(zipfile, "ZipFile", _counting_zip_file)

    epub.count_chapter_words(mini_epub_with_navigation, structure.chapters)

    assert len(opened) == 1


# ============ Echte Datei: Calibre-Konvertat mit _split_NNN-Dokumenten (technik.md §8,
# ============ „Ein Kapitel ist nicht ein Dokument")


@pytest.mark.needs_calibre_split_epub
def test_book_one_dune_spans_all_three_split_documents(real_dune_epub_path: Path) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Calibre zerlegt „Book 1 DUNE"
    in drei `…_split_NNN`-Dokumente, wovon die Navigation nur auf das
    erste zeigt — `documents` muss trotzdem alle drei tragen, nicht nur das Navigationsziel."""
    structure = epub.read_structure(real_dune_epub_path)

    book_one = next(chapter for chapter in structure.chapters if chapter.title == "Book 1 DUNE")

    assert book_one.documents == [
        "OEBPS/part2_split_000.xhtml",
        "OEBPS/part2_split_001.xhtml",
        "OEBPS/part2_split_002.xhtml",
    ]


@pytest.mark.needs_calibre_split_epub
def test_book_two_and_three_span_their_two_split_documents_each(real_dune_epub_path: Path) -> None:
    """Derselbe Beleg wie oben für die beiden übrigen Mehrdokument-Kapitel — beide mit zwei
    statt drei `…_split_NNN`-Dokumenten (technik.md §8, „Ein Kapitel ist nicht ein
    Dokument")."""
    structure = epub.read_structure(real_dune_epub_path)

    by_title = {chapter.title: chapter.documents for chapter in structure.chapters}

    assert by_title["Book Two MUAD’DIB"] == [
        "OEBPS/part3_split_000.xhtml",
        "OEBPS/part3_split_001.xhtml",
    ]
    assert by_title["Book Three THE PROPHET"] == [
        "OEBPS/part4_split_000.xhtml",
        "OEBPS/part4_split_001.xhtml",
    ]


@pytest.mark.needs_calibre_split_epub
def test_chapter_word_counts_match_the_measured_table_in_technik_md(
    real_dune_epub_path: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": Die gemessene Tabelle — 78.774 /
    63.513 / 64.637 Wörter für die drei Mehrdokument-Kapitel — ist die Gegenprobe, dass die
    Anzeige (`count_chapter_words`) und die Dokumentliste (`documents`) dasselbe Kapitel
    meinen."""
    structure = epub.read_structure(real_dune_epub_path)

    counts = epub.count_chapter_words(real_dune_epub_path, structure.chapters)
    by_title = {chapter.title: counts[chapter.number] for chapter in structure.chapters}

    assert by_title["Book 1 DUNE"] == 78774
    assert by_title["Book Two MUAD’DIB"] == 63513
    assert by_title["Book Three THE PROPHET"] == 64637


@pytest.mark.needs_calibre_split_epub
def test_read_chapter_includes_text_from_the_third_split_document_of_book_one(
    real_dune_epub_path: Path,
) -> None:
    """technik.md §8, „Ohne die vollständige Dokumentliste wäre das ein stiller Verlust": Ohne
    diese Regel läge rund 63 % des Buchs außerhalb jedes Kapitels — der Text des dritten Dokuments
    von „Book 1 DUNE" (`part2_split_002.xhtml`) muss jetzt über `read_chapter` erreichbar sein."""
    structure = epub.read_structure(real_dune_epub_path)
    book_one = next(chapter for chapter in structure.chapters if chapter.title == "Book 1 DUNE")

    chapter = epub.read_chapter(real_dune_epub_path, structure.book, book_one)

    assert "Paul swallowed in a dry throat." in chapter.text


@pytest.mark.needs_calibre_split_epub
def test_documents_before_the_first_navigation_target_belong_to_no_chapter_in_dune(
    real_dune_epub_path: Path,
) -> None:
    """technik.md §8, „Ein Kapitel ist nicht ein Dokument": `titlepage.xhtml` und
    `OEBPS/title.xhtml` stehen
    vor dem ersten Navigationsziel (`OEBPS/part1.xhtml`) und dürfen deshalb in keiner
    `documents`-Liste auftauchen."""
    structure = epub.read_structure(real_dune_epub_path)

    assigned = {document for chapter in structure.chapters for document in chapter.documents}

    assert "titlepage.xhtml" not in assigned
    assert "OEBPS/title.xhtml" not in assigned


@pytest.mark.needs_calibre_split_epub
def test_dune_navigation_is_used_without_falling_back_to_the_spine(
    real_dune_epub_path: Path,
) -> None:
    """technik.md §8: Dune trägt eine gültige `toc.ncx`-Navigation — `notice` bleibt
    `None`, es ist kein spine-Rückfall. Schreibt zusätzlich die vollständige Titelliste
    fest (Durchsicht 3997c8b, Befund 2): Ginge das erste Kapitel „Dune" (`OEBPS/part1.xhtml`,
    5 Wörter) verloren, blieben die übrigen fünf `needs_calibre_split_epub`-Tests grün,
    weil keiner von ihnen die Kapitelanzahl zusichert."""
    result = epub.read_structure(real_dune_epub_path)

    assert result.notice is None
    assert [chapter.title for chapter in result.chapters] == [
        "Dune",
        "Book 1 DUNE",
        "Book Two MUAD’DIB",
        "Book Three THE PROPHET",
    ]
