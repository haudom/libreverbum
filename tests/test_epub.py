"""Prüft `libreverbum/epub.py` — bauplan.md T12, Struktur eines EPUB: Metadaten, `spine`,
Navigation, Kapitelliste nach eindeutigen Zielen."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from libreverbum import epub

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
    """`ChapterReference.number` zählt ab 1 (`entities.Chapter`, Docstring zu `number`)."""
    result = epub.read_structure(mini_epub_with_navigation)

    assert [chapter.number for chapter in result.chapters] == [1, 2]
    assert [chapter.document for chapter in result.chapters] == [
        "OEBPS/chapter1.xhtml",
        "OEBPS/chapter2.xhtml",
    ]


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
    assert [chapter.document for chapter in result.chapters] == [
        "OEBPS/chapter1.xhtml",
        "OEBPS/chapter2.xhtml",
        "OEBPS/chapter3.xhtml",
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
    assert [chapter.document for chapter in result.chapters] == [
        "EPUB/text/chapter 1.xhtml",
        "EPUB/text/chapter2.xhtml",
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
    assert [chapter.document for chapter in result.chapters] == [
        "OEBPS/chapter1.xhtml",
        "OEBPS/chapter2.xhtml",
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
