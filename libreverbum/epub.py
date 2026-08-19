"""EPUB — Struktur und Fließtext: Metadaten, Lesereihenfolge, Kapitelliste, Kapiteltext
(bauplan.md T12, T12b).

Aufgabe
-------
Schritt 1 des Kernablaufs (konzept.md, „1. Buch einlesen"): `container.xml` → OPF →
Metadaten, `spine`, Navigation (technik.md §8, T12) liefern die Kapitelliste, mit der der
Nutzer ein Kapitel auswählt (konzept.md, „Der Kernablauf"). `read_chapter` (T12b) liest
danach den Fließtext genau dieses einen Kapitels mit `html.parser`, von Vorspann und
Impressum ausgesteuert, und meldet die drei Ablehnfälle (kein ZIP-Archiv, Bildband ohne
Text, verschlüsselt) statt leer zurückzugeben.

Voraussetzungen
---------------
Erwartet eine lesbare EPUB-Datei. Kein Kopierschutz wird umgangen (konzept.md, Schritt
1). `read_structure` öffnet die Datei ungeprüft — ob sie überhaupt ein ZIP-Archiv,
verschlüsselt oder ohne Text ist, prüft erst `read_chapter` beim Lesen des gewählten
Kapitels (Regel 13); die Kapitelliste allein muss dafür nicht reichen.

Liefert
-------
`read_structure` liefert Titel und Autor sowie die Kapitelliste nach eindeutigen Zielen
aus der Navigation (`nav.xhtml` oder `toc.ncx`) — mehrere Navigationseinträge auf
dasselbe Dokument zählen als ein Kapitel (technik.md §8, „Sherlock-Fall 18→14"). Fehlt
die Navigation oder liefert sie keinen Eintrag, gilt jedes Dokument der `spine` als
eigenes Kapitel, zusammen mit `notice` als sichtbarem Hinweis, dass die Grenzen nicht aus
dem Buch stammen — ein Feld im Ergebnis, kein Protokolleintrag, den ein Aufrufer
übersehen könnte. `ChapterReference.number` zählt dabei stets in der Reihenfolge der
`spine`, auch wenn die Beschriftung aus der Navigation stammt (`entities.Chapter`,
Docstring zu `number`) — die Navigation legt nur Beschriftung und eindeutige Ziele fest,
nicht die Zählrichtung. `ChapterReference.document` trägt das Inhaltsdokument im Archiv.

`read_chapter` liefert dazu `entities.Chapter` mit dem Fließtext genau dieses Dokuments:
Skripte, Stilangaben und Kopfzeilen bleiben draußen, Blockelemente behalten ihre
Absatzgrenze — `extraction` (T3) braucht sie für Belegsätze (tools/epub_check.py,
`TextCollector`, dieselbe Auswahl an Tags). Vorspann und Impressum werden ausgesteuert,
soweit Project-Gutenberg-Dateien sie zwischen den Textmarken „*** START OF THE PROJECT
GUTENBERG …" und „*** END OF THE PROJECT GUTENBERG …" kapseln — denselben Marken, mit
denen `tools/coverage_check.py` den Lizenz-Vorspann der Textfassungen abschneidet. Ein
`epub:type`, das die Norm dafür vorsähe, kommt in der Praxis nicht vor (technik.md §8,
„Neuer Befund: epub:type gibt es in der Praxis nicht"); außerhalb von Project Gutenberg
bleibt die Trennung deshalb unversucht und der Text unverändert — eine allgemeine
Schwelle ist durch keine Messung belegt (Regel 14).
"""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ElementTree
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

from libreverbum.entities import Book, Chapter

_CONTAINER_PATH = "META-INF/container.xml"
_ENCRYPTION_PATH = "META-INF/encryption.xml"

_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "enc": "http://www.w3.org/2001/04/xmlenc#",
}

_EPUB_TYPE_ATTRIBUTE = "{http://www.idpf.org/2007/ops}type"

_UNKNOWN_AUTHOR = "unbekannt"

# Text des Hinweises aus technik.md §8, „Regel: Kapitel kommen aus der Navigation …
# Fehlt sie, gilt jedes Dokument der Lesereihenfolge als ein Kapitel — zusammen mit einem
# sichtbaren Hinweis, dass die Grenzen nicht aus dem Buch stammen." Öffentliche Konstante,
# damit ein Aufrufer (und ein Test) exakt darauf prüfen kann, statt eine eigene Kopie des
# Wortlauts zu pflegen.
NAVIGATION_MISSING_NOTICE = (
    "Diese Datei nennt keine Kapitelstruktur (weder nav.xhtml noch toc.ncx). Jedes "
    "Dokument der Lesereihenfolge gilt deshalb als eigenes Kapitel — die Grenzen stammen "
    "nicht aus dem Buch."
)


@dataclass(frozen=True)
class ChapterReference:
    """Ein Eintrag der Kapitelliste vor dem Einlesen des Fließtexts (bauplan.md T12):
    Titel und das Inhaltsdokument im Archiv, auf das er zeigt. `number` zählt ab 1 in der
    Reihenfolge der `spine`, wie `entities.Chapter.number` es später fortführt.
    `entities.Chapter` entsteht daraus erst, wenn der Fließtext dieses einen Dokuments
    gelesen ist (T12b) — das Auswählen eines Kapitels soll nicht das ganze Buch parsen."""

    number: int
    title: str
    document: str


@dataclass(frozen=True)
class BookStructure:
    """Ergebnis von `read_structure` (bauplan.md T12): Metadaten und Kapitelliste, dazu
    `notice`, gesetzt, wenn die Datei keine Navigation nennt (technik.md §8) — ein
    Ergebnisbestandteil, kein Protokolleintrag, damit der Aufrufer ihn nicht übersehen
    kann."""

    book: Book
    chapters: list[ChapterReference]
    notice: str | None


class _Package(NamedTuple):
    """Aus der OPF-Package-Datei gelesen: Metadaten, `spine` und die Verweise auf beide
    Navigationsformen. Rein intern — `read_structure` formt daraus `BookStructure`."""

    title: str
    author: str
    spine_documents: list[str]
    nav_href: str | None
    ncx_href: str | None


def _find_opf(archive: zipfile.ZipFile, path: Path) -> str:
    """Pfad der Package-Datei aus `container.xml` — der von der Norm vorgeschriebene
    Einstieg."""
    try:
        raw = archive.read(_CONTAINER_PATH)
    except KeyError as error:
        raise ValueError(
            f"{path}: {_CONTAINER_PATH} fehlt — keine gültige EPUB-Struktur."
        ) from error
    root = ElementTree.fromstring(raw)
    rootfile = root.find("container:rootfiles/container:rootfile", _NS)
    full_path = rootfile.get("full-path") if rootfile is not None else None
    if not full_path:
        raise ValueError(f"{path}: {_CONTAINER_PATH} nennt keine Package-Datei.")
    # (Befund 8, Review Runde 1): archive.read(full_path) würfe sonst einen englischen
    # KeyError, obwohl der Docstring von read_structure für diesen Fall ausdrücklich eine
    # deutsche Meldung verspricht (Regel 13, dokumentation.md §1).
    if full_path not in archive.namelist():
        raise ValueError(
            f"{path}: {full_path} — die in {_CONTAINER_PATH} genannte Package-Datei "
            "fehlt im Archiv."
        )
    return full_path


def _text_of(root: ElementTree.Element, tag: str) -> str | None:
    """Getrimmter Text des ersten **nichtleeren** Metadaten-Elements mit diesem Tag,
    `None`, wenn keins einen Text trägt.

    Manche Konvertate stellen ein leeres Element voran und führen den eigentlichen Wert
    erst im zweiten (etwa ein leeres `dc:title` vor dem echten Buchtitel). `root.find`
    läse nur das erste und meldete die Datei fälschlich als titellos. Mehrere `dc:creator`
    mit eigenem Text werden dagegen **nicht** zusammengeführt — `entities.Book.author` ist
    ein einzelnes Feld, und ein zweites `dc:creator` bleibt deshalb ungenutzt (Regel 14)."""
    for found in root.findall(f"opf:metadata/{tag}", _NS):
        if found.text and found.text.strip():
            return found.text.strip()
    return None


def _read_package(archive: zipfile.ZipFile, opf_path: str, path: Path) -> _Package:
    """Metadaten, Lesereihenfolge (`spine`) und die Verweise auf beide Navigationsformen
    aus der Package-Datei.

    Bricht sichtbar ab (Regel 13), wenn die Datei keinen Titel oder keine `spine` nennt —
    beides macht die Datei für den Kernablauf unbrauchbar, kein Fall für ein leeres
    Ergebnis.
    """
    root = ElementTree.fromstring(archive.read(opf_path))
    base = posixpath.dirname(opf_path)

    manifest: dict[str, dict[str, str]] = {}
    for item in root.findall("opf:manifest/opf:item", _NS):
        item_id = item.get("id")
        href = item.get("href")
        if not item_id or not href:
            continue
        # (Befund 1, Review Runde 1): href ist laut Norm eine IRI und darf prozentkodiert
        # sein (chapter%201.xhtml); unquote erst nach dem Fragment-Split anwenden würde
        # hier nichts ändern, weil manifest-hrefs keins tragen — trotzdem vor dem Vergleich
        # gegen archive.namelist() dekodieren, sonst verschwindet das Kapitel still.
        manifest[item_id] = {
            "href": posixpath.normpath(posixpath.join(base, unquote(href))),
            "properties": item.get("properties") or "",
        }

    spine_documents = [
        manifest[ref]["href"]
        for element in root.findall("opf:spine/opf:itemref", _NS)
        if (ref := element.get("idref")) and ref in manifest
    ]
    if not spine_documents:
        raise ValueError(f"{path}: {opf_path} nennt keine Lesereihenfolge (spine).")

    nav_href = next(
        (item["href"] for item in manifest.values() if "nav" in item["properties"].split()), None
    )
    spine_element = root.find("opf:spine", _NS)
    toc_id = spine_element.get("toc") if spine_element is not None else None
    ncx_href = manifest[toc_id]["href"] if toc_id and toc_id in manifest else None

    title = _text_of(root, "dc:title")
    if title is None:
        raise ValueError(f"{path}: {opf_path} nennt keinen Titel (dc:title).")

    return _Package(
        title=title,
        author=_text_of(root, "dc:creator") or _UNKNOWN_AUTHOR,
        spine_documents=spine_documents,
        nav_href=nav_href,
        ncx_href=ncx_href,
    )


def _read_nav(archive: zipfile.ZipFile, href: str) -> list[tuple[str, str]]:
    """Rohe Kapitelliste aus dem EPUB-3-Navigationsdokument (`nav` mit
    `epub:type="toc"`) — Beschriftung und Ziel je Eintrag, Anker (`#…`) abgeschnitten.
    Kann Wiederholungen enthalten (technik.md §8, Sherlock-Fall); die Zusammenführung auf
    eindeutige Ziele übernimmt `_deduplicate_by_target`."""
    root = ElementTree.fromstring(archive.read(href))
    base = posixpath.dirname(href)
    entries: list[tuple[str, str]] = []
    for nav in root.iter(f"{{{_NS['xhtml']}}}nav"):
        # (Befund 3, Review Runde 1): epub:type ist eine leerzeichengetrennte Liste, nicht
        # ein einzelner Wert — "toc bodymatter" trägt ebenso ein Inhaltsverzeichnis. Zwei
        # Zeilen weiter oben (properties) wird deshalb schon mit .split() verglichen.
        if "toc" not in (nav.get(_EPUB_TYPE_ATTRIBUTE) or "").split():
            continue
        for anchor in nav.iter(f"{{{_NS['xhtml']}}}a"):
            # (Befund 1, Review Runde 1): erst das Fragment abschneiden, dann dekodieren —
            # sonst findet der Vergleich gegen archive.namelist() das Dokument nicht.
            target = unquote((anchor.get("href") or "").split("#", 1)[0])
            label = " ".join("".join(anchor.itertext()).split())
            if label and target:
                entries.append((label, posixpath.normpath(posixpath.join(base, target))))
        break
    return entries


def _read_ncx(archive: zipfile.ZipFile, href: str) -> list[tuple[str, str]]:
    """Rohe Kapitelliste aus der EPUB-2-Datei `toc.ncx` — derselbe Aufbau wie `_read_nav`,
    für den Mehrheitsfall aus technik.md §8 (zehn von zwölf gemessenen Dateien EPUB 2.0)."""
    root = ElementTree.fromstring(archive.read(href))
    base = posixpath.dirname(href)
    entries: list[tuple[str, str]] = []
    for point in root.iter(f"{{{_NS['ncx']}}}navPoint"):
        label_element = point.find("ncx:navLabel/ncx:text", _NS)
        content = point.find("ncx:content", _NS)
        if label_element is None or content is None:
            continue
        label = " ".join((label_element.text or "").split())
        # (Befund 1, Review Runde 1): siehe _read_nav — erst das Fragment abschneiden,
        # dann dekodieren.
        target = unquote((content.get("src") or "").split("#", 1)[0])
        if label and target:
            entries.append((label, posixpath.normpath(posixpath.join(base, target))))
    return entries


def _deduplicate_by_target(entries: list[tuple[str, str]]) -> dict[str, str]:
    """Beschriftung des ersten Navigationseintrags je eindeutigem Ziel (technik.md §8,
    „Sherlock-Fall 18→14"): Unterpunkte wie „I./II./III." einer Erzählung und der Eintrag
    „Contents" zeigen auf dasselbe Dokument wie ein anderer Eintrag und dürfen die
    Kapitelliste nicht aufblähen. Bei mehreren Einträgen auf dasselbe Ziel gewinnt der
    erste in der Reihenfolge der Navigation."""
    labels: dict[str, str] = {}
    for label, target in entries:
        labels.setdefault(target, label)
    return labels


def _resolve_chapters(
    archive: zipfile.ZipFile, names: set[str], package: _Package, path: Path
) -> tuple[list[ChapterReference], str | None]:
    """Kapitelliste aus der Navigation, sonst der Rückfall auf die `spine` (technik.md
    §8). Bricht sichtbar ab (Regel 13), bleibt am Ende keine einzige Kapitelreferenz übrig
    — statt eines leeren Ergebnisses, das wie ein leeres Buch aussähe."""
    entries: list[tuple[str, str]] = []
    if package.nav_href and package.nav_href in names:
        entries = _read_nav(archive, package.nav_href)
    # (Befund 4, Review Runde 1): EPUB-3-Vorrang bleibt erhalten — die toc.ncx wird nur
    # versucht, wenn die nav.xhtml fehlt oder keinen verwertbaren Eintrag liefert (leer
    # oder epub:type ohne "toc"), nicht als gleichwertige Alternative.
    if not entries and package.ncx_href and package.ncx_href in names:
        entries = _read_ncx(archive, package.ncx_href)

    labels = _deduplicate_by_target(entries)
    # `number` zählt in der Reihenfolge der spine, nicht der Navigation
    # (entities.Chapter, Docstring zu `number`) — die Navigation legt nur
    # Beschriftung und eindeutige Ziele fest, nicht die Zählrichtung.
    ordered_targets = [
        document for document in package.spine_documents if document in labels and document in names
    ]

    # (Befund 2, Review Runde 1): Die Weiche hängt am Ergebnis der Auflösung, nicht an der
    # rohen Einträgeliste. Nennt die Navigation nur Ziele, die sich nicht auflösen lassen
    # (Prozentkodierung, Ziele außerhalb der spine, fehlende Dokumente), ist das materiell
    # eine fehlende Navigation und muss in den spine-Rückfall samt Hinweis laufen, nicht in
    # den ValueError am Ende dieser Funktion.
    if ordered_targets:
        chapters = [
            ChapterReference(number=number, title=labels[document], document=document)
            for number, document in enumerate(ordered_targets, start=1)
        ]
        notice = None
    else:
        documents = [document for document in package.spine_documents if document in names]
        chapters = [
            ChapterReference(number=number, title=f"Kapitel {number}", document=document)
            for number, document in enumerate(documents, start=1)
        ]
        notice = NAVIGATION_MISSING_NOTICE

    # REGEL (dokumentation.md §4 Regel 13): kein leeres Ergebnis, das wie ein Buch ohne
    # jedes Kapitel aussähe — weder Navigation noch spine haben ein lesbares Dokument
    # geliefert.
    if not chapters:
        raise ValueError(
            f"{path}: keine Kapitel gefunden — weder aus der Navigation noch aus der spine."
        )
    return chapters, notice


def read_structure(path: Path) -> BookStructure:
    """Liest Metadaten, `spine` und Navigation eines EPUB (bauplan.md T12).

    Bricht mit einer deutschen Meldung ab (Regel 13), wenn `path` fehlt oder die Struktur
    unvollständig ist (kein `container.xml`, keine Package-Datei, keine `spine`, kein
    Titel, keine Kapitel) — statt eines leeren oder nur teilweise gefüllten Ergebnisses.
    Ob die Datei überhaupt ein ZIP-Archiv, verschlüsselt oder ohne Text ist, bleibt Sache
    von T12b (bauplan.md); hier wird nur die Struktur gelesen.
    """
    if not path.is_file():
        raise FileNotFoundError(f"EPUB nicht lesbar: {path}")

    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        package = _read_package(archive, _find_opf(archive, path), path)
        chapters, notice = _resolve_chapters(archive, names, package, path)

    return BookStructure(
        book=Book(title=package.title, author=package.author), chapters=chapters, notice=notice
    )


# ------------------------------------------------------------------- Fließtext (bauplan.md T12b)

# Inhalt dieser Elemente ist kein Fließtext (tools/epub_check.py, TextCollector).
_SKIPPED_TAGS = frozenset({"script", "style", "head", "title"})

# Elemente, nach denen ein Zeilenumbruch steht — sonst klebt „…Ende.Anfang…" zusammen und
# extraction (T3) kann keine Absatzgrenze mehr für den Belegsatz ziehen (tools/epub_check.py).
_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "tr",
        "blockquote",
        "section",
        "aside",
        "figcaption",
    }
)

# Buchstaben statt [A-Za-z], sonst zerfallen Ligaturen (tools/epub_check.py, WORD) — hier
# nur benutzt, um „kein einziges Wort" (Bildband ohne Text) von echtem Fließtext zu
# unterscheiden, nicht zum Zählen.
_WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")

# Project-Gutenberg-Textmarken, dieselben wie in tools/coverage_check.py (GUTENBERG_START,
# GUTENBERG_END) — dort schneiden sie den Lizenz-Vorspann der .txt-Fassungen ab, hier den
# der EPUB-Fassungen. Kein zweites Verfahren, nur dieselben Marken auf einer anderen Quelle.
_GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
_GUTENBERG_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)


class _FlowingTextParser(HTMLParser):
    """Sammelt den Fließtext eines Inhaltsdokuments (tools/epub_check.py, `TextCollector`):
    `_SKIPPED_TAGS` liefern keinen Text, `_BLOCK_TAGS` erzwingen einen Zeilenumbruch."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skipped_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skipped_depth += 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS and self._skipped_depth:
            self._skipped_depth -= 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipped_depth:
            self._parts.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\n{2,}", "\n", "".join(self._parts)).strip()


def _extract_flowing_text(source: str) -> str:
    """Fließtext eines Inhaltsdokuments mit `html.parser` (E8a, technik.md §8)."""
    parser = _FlowingTextParser()
    parser.feed(source)
    return parser.text


def _remove_boilerplate(text: str) -> str:
    """Vorspann und Impressum aussteuern (bauplan.md T12b) — siehe Moduldocstring,
    Abschnitt „Liefert": Text vor der Start- und nach der Endmarke fällt weg. Trägt eine
    Datei keine der beiden Marken, bleibt der Text unverändert."""
    if start_match := _GUTENBERG_START.search(text):
        text = text[start_match.end() :]
    if end_match := _GUTENBERG_END.search(text):
        text = text[: end_match.start()]
    return text.strip()


def _encrypts_document(archive: zipfile.ZipFile, names: set[str], document: str) -> bool:
    """Prüft `META-INF/encryption.xml` gegen `document`, statt allein ihre Anwesenheit zu
    werten (Befund 6, Review Runde 2): Die Datei kennzeichnet laut OCF-Norm auch bloße
    Schriftverschleierung (`Algorithm=".../2008/embedding"`), die Calibre, InDesign und
    Sigil routinemäßig erzeugen — ein DRM-freies EPUB würde sonst fälschlich abgelehnt.
    Verschlüsselt ist der Text erst, wenn eine `CipherReference` ausgerechnet auf das
    gelesene Kapiteldokument zeigt."""
    if _ENCRYPTION_PATH not in names:
        return False
    root = ElementTree.fromstring(archive.read(_ENCRYPTION_PATH))
    return any(
        unquote(reference.get("URI") or "") == document
        for reference in root.iter(f"{{{_NS['enc']}}}CipherReference")
    )


def _encrypted_error(path: Path) -> ValueError:
    """Meldung für beide Erscheinungsformen des dritten Ablehnfalls (Befund 6 und 7,
    Review Runde 2): `encryption.xml` nennt das Kapiteldokument, oder der ZIP-Eintrag
    selbst ist mit einem Passwort geschützt."""
    return ValueError(
        f"{path}: verschlüsselt ({_ENCRYPTION_PATH}) — Kopierschutz wird nicht umgangen."
    )


def read_chapter(path: Path, book: Book, chapter: ChapterReference) -> Chapter:
    """Liest den Fließtext eines einzelnen Kapitels (bauplan.md T12b).

    Bricht mit einer deutschen Meldung ab (Regel 13) statt eines leeren oder beschädigten
    Ergebnisses: wenn `path` fehlt, die Datei kein gültiges ZIP-Archiv ist, das
    Kapiteldokument im Archiv fehlt oder nicht UTF-8 kodiert ist, `META-INF/encryption.xml`
    ausgerechnet dieses Dokument als verschlüsselt nennt oder der ZIP-Eintrag selbst
    passwortgeschützt ist (Kopierschutz wird nicht umgangen, konzept.md Schritt 1), das
    Kapitel überhaupt keinen Fließtext enthält — das Kennzeichen eines Bildbands ohne Text
    (technik.md §8) — oder nach dem Aussteuern von Vorspann und Impressum keiner mehr übrig
    bleibt, weil das Dokument nur aus Lizenztext bestand.
    """
    # (Befund 12, Review Runde 2): dieselben zwei Zeilen wie in read_structure — sonst
    # entkäme hier der englische FileNotFoundError der Standardbibliothek.
    if not path.is_file():
        raise FileNotFoundError(f"EPUB nicht lesbar: {path}")

    # (Befund 11, Review Runde 2): nur das Öffnen des Archivs steht im try — sonst meldete
    # eine kaputte CRC-Summe beim späteren archive.read() fälschlich „kein ZIP-Archiv".
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as error:
        raise ValueError(f"{path}: keine gültige EPUB-Datei (kein ZIP-Archiv).") from error

    with archive:
        names = set(archive.namelist())
        if _encrypts_document(archive, names, chapter.document):
            raise _encrypted_error(path)
        # (Befund 7, Review Runde 2): sonst entkäme hier ein englischer KeyError, wenn das
        # Kapiteldokument im Archiv fehlt.
        if chapter.document not in names:
            raise ValueError(
                f"{path}: {chapter.document} — das Dokument des Kapitels "
                f"„{chapter.title}“ fehlt im Archiv."
            )
        try:
            raw = archive.read(chapter.document)
        except RuntimeError as error:
            # (Befund 7, Review Runde 2): der dritte Ablehnfall in anderer Gestalt — ein
            # passwortgeschützter ZIP-Eintrag ohne META-INF/encryption.xml.
            raise _encrypted_error(path) from error

    # (Befund 8, Review Runde 2): kein errors="replace" — sonst landete U+FFFD still im
    # Wortschatz statt eines sichtbaren Fehlschlags.
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"{path}: {chapter.document} ist nicht UTF-8 kodiert — der Text wäre still beschädigt."
        ) from error

    raw_text = _extract_flowing_text(source)
    if not _WORD.search(raw_text):
        raise ValueError(
            f"{path}: Kapitel „{chapter.title}“ enthält keinen Fließtext — vermutlich ein "
            "Bildband ohne Text."
        )

    # (Befund 1, Review Runde 2): Aussteuern kann auch das ganze Kapitel verschlingen — ein
    # reines Lizenzdokument darf danach nicht als leerer Fließtext durchgehen (Regel 13).
    text = _remove_boilerplate(raw_text)
    if not _WORD.search(text):
        raise ValueError(
            f"{path}: Kapitel „{chapter.title}“ besteht nur aus Vorspann bzw. Impressum — "
            "nach dem Aussteuern bleibt kein Fließtext übrig."
        )

    return Chapter(book=book, number=chapter.number, title=chapter.title, text=text)
