#!/usr/bin/env python3
"""EPUB-Test: Trägt die Standardbibliothek Schritt 1 des Kernablaufs?

Hintergrund
-----------
Die Wahl des EPUB-Lesers (siehe ../technik.md, Abschnitt 8) ist zuerst eine Lizenzfrage:
Die verbreitete Bibliothek EbookLib steht unter AGPL-3.0 und schiede damit nach Regel 15
aus. Die Gegenfrage lautet, ob es sie überhaupt braucht — ein EPUB ist ein ZIP-Archiv mit
XML darin, und beides kennt die Standardbibliothek.

Dieses Skript beantwortet sie an echten Dateien statt aus der Papierlage. Gemessen wird,
woran der Standardbibliotheks-Weg scheitern könnte:

1. **Struktur** — Titel, Autor, Lesereihenfolge und Kapitelliste. Abnahmekriterium 1
   verlangt, dass die Kapitelliste mit dem tatsächlichen Inhaltsverzeichnis übereinstimmt
2. **XML-Härte** — ob sich die Inhaltsdokumente mit ``xml.etree`` lesen lassen. Sie sind
   laut Norm wohlgeformtes XHTML, benutzen aber gern HTML-Entitäten wie ``&nbsp;``, die in
   XML nicht erklärt sind. Genau hier bricht der naive Weg
3. **Fließtext** — was ``html.parser`` an Wörtern herausholt, je Dokument
4. **Auszeichnung** — ob ``epub:type`` Vorspann, Inhaltsverzeichnis, Impressum und
   Fußnoten benennt. Ist das der Fall, ist die Trennung aus konzept.md, Schritt 1, eine
   Strukturfrage und keine Heuristik

Verfahren und seine Grenzen
---------------------------
Nur Standardbibliothek, damit das Skript ohne Projektumgebung läuft — wie die übrigen
Werkzeuge hier. Es liest **nur**: keine Datei wird verändert, kein Kopierschutz umgangen.
Verschlüsselte Dateien (``META-INF/encryption.xml``) werden gemeldet und übersprungen.

Die Wortzahl ist eine Rohzählung ohne Lemmatisierung; sie dient dem Vergleich der
Dokumente untereinander, nicht der Abdeckungsmessung. Dafür ist ``coverage_check.py`` da.

Aufruf
------
    python tools/epub_check.py buch.epub [weiteres.epub ...]
    python tools/epub_check.py --chapters buch.epub    # nur die Kapitelliste
"""

from __future__ import annotations

import argparse
import collections
import posixpath
import re
import sys
import xml.etree.ElementTree as ElementTree
import zipfile
from html.parser import HTMLParser

CONTAINER = "META-INF/container.xml"
ENCRYPTION = "META-INF/encryption.xml"

NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

EPUB_TYPE = "{http://www.idpf.org/2007/ops}type"

# Siehe coverage_check.py: Buchstaben statt [A-Za-z], sonst zerfallen Ligaturen.
WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")

# Inhalt dieser Elemente ist kein Fließtext.
SKIPPED_TAGS = {"script", "style", "head", "title"}

# Der Rückfall, wenn die Navigation keine Kapitel hergibt (technik.md §8).
HEADING_TAGS = {"h1", "h2", "h3"}

# Elemente, nach denen ein Zeilenumbruch steht — sonst klebt „…Ende.Anfang…" zusammen.
BLOCK_TAGS = {
    "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "tr", "blockquote", "section", "aside", "figcaption",
}  # fmt: skip


class TextCollector(HTMLParser):
    """Sammelt Fließtext und die ``epub:type``-Auszeichnungen eines Inhaltsdokuments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.types: collections.Counter[str] = collections.Counter()
        self.headings: list[str] = []
        self.depth_skipped = 0
        self.in_heading = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self.depth_skipped += 1
        if tag in HEADING_TAGS:
            self.in_heading = tag
            self.headings.append("")
        for name, value in attrs:
            # html.parser löst keine Namensräume auf; das Attribut heißt hier wörtlich
            # „epub:type". Das schlichte `type` wäre der MIME-Typ und gehört nicht dazu.
            if name == "epub:type" and value:
                self.types.update(f"{tag}:{part}" for part in value.split())
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS and self.depth_skipped:
            self.depth_skipped -= 1
        if tag == self.in_heading:
            self.in_heading = ""
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.depth_skipped:
            return
        self.parts.append(data)
        if self.in_heading and self.headings:
            self.headings[-1] += data

    @property
    def text(self) -> str:
        return re.sub(r"\n{2,}", "\n", "".join(self.parts)).strip()


def german(number: int) -> str:
    """Tausendertrennung mit Punkt. Muss auf die Zahl beschränkt bleiben — ein
    ``replace`` über die ganze Zeile macht aus jedem Komma im Buchtext einen Punkt."""
    return f"{number:,}".replace(",", ".")


def find_opf(archive: zipfile.ZipFile) -> str:
    """Pfad der Package-Datei — der Einstieg, den die Norm vorschreibt."""
    root = ElementTree.fromstring(archive.read(CONTAINER))
    rootfile = root.find("container:rootfiles/container:rootfile", NS)
    if rootfile is None or not rootfile.get("full-path"):
        raise ValueError(f"{CONTAINER} nennt keine Package-Datei")
    return rootfile.get("full-path", "")


def read_package(archive: zipfile.ZipFile, opf: str) -> dict:
    """Metadaten, Manifest und Lesereihenfolge (spine) aus der Package-Datei."""
    root = ElementTree.fromstring(archive.read(opf))
    base = posixpath.dirname(opf)

    manifest = {}
    for item in root.findall("opf:manifest/opf:item", NS):
        item_id = item.get("id") or ""
        manifest[item_id] = {
            "href": posixpath.normpath(posixpath.join(base, item.get("href") or "")),
            "media_type": item.get("media-type") or "",
            "properties": (item.get("properties") or "").split(),
        }

    spine = [
        manifest[ref]["href"]
        for item in root.findall("opf:spine/opf:itemref", NS)
        if (ref := item.get("idref") or "") in manifest
    ]

    nav = next((i["href"] for i in manifest.values() if "nav" in i["properties"]), None)
    spine_element = root.find("opf:spine", NS)
    toc_id = spine_element.get("toc") if spine_element is not None else None
    ncx = manifest[toc_id]["href"] if toc_id and toc_id in manifest else None

    def text_of(tag: str) -> str:
        found = root.find(f"opf:metadata/{tag}", NS)
        return (found.text or "").strip() if found is not None and found.text else "—"

    return {
        "version": root.get("version") or "?",
        "title": text_of("dc:title"),
        "creator": text_of("dc:creator"),
        "manifest": manifest,
        "spine": spine,
        "nav": nav,
        "ncx": ncx,
    }


def read_nav(archive: zipfile.ZipFile, href: str) -> list[tuple[str, str]]:
    """Kapitelliste aus dem EPUB-3-Navigationsdokument (nav mit epub:type=toc)."""
    root = ElementTree.fromstring(archive.read(href))
    base = posixpath.dirname(href)
    for nav in root.iter(f"{{{NS['xhtml']}}}nav"):
        if nav.get(EPUB_TYPE) != "toc":
            continue
        entries = []
        for anchor in nav.iter(f"{{{NS['xhtml']}}}a"):
            target = (anchor.get("href") or "").split("#")[0]
            label = " ".join("".join(anchor.itertext()).split())
            if label:
                entries.append((label, posixpath.normpath(posixpath.join(base, target))))
        return entries
    return []


def read_ncx(archive: zipfile.ZipFile, href: str) -> list[tuple[str, str]]:
    """Kapitelliste aus der EPUB-2-Datei toc.ncx."""
    root = ElementTree.fromstring(archive.read(href))
    base = posixpath.dirname(href)
    entries = []
    for point in root.iter(f"{{{NS['ncx']}}}navPoint"):
        label = point.find("ncx:navLabel/ncx:text", NS)
        content = point.find("ncx:content", NS)
        if label is not None and content is not None:
            target = (content.get("src") or "").split("#")[0]
            entries.append(
                (
                    " ".join((label.text or "").split()),
                    posixpath.normpath(posixpath.join(base, target)),
                )
            )
    return entries


def measure(path: str) -> dict:
    """Alles, was eine Datei über sich verrät — Struktur, XML-Härte, Fließtext."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if ENCRYPTION in names:
            # konzept.md, Schritt 1: Nur DRM-freie Dateien. Kopierschutz wird nicht umgangen.
            return {"encrypted": True}

        package = read_package(archive, find_opf(archive))
        if package["nav"] and package["nav"] in names:
            chapters, source = read_nav(archive, package["nav"]), "nav.xhtml (EPUB 3)"
        elif package["ncx"] and package["ncx"] in names:
            chapters, source = read_ncx(archive, package["ncx"]), "toc.ncx (EPUB 2)"
        else:
            chapters, source = [], "keine Navigation"

        documents = [h for h in package["spine"] if h in names]
        failures, types, per_document, headings = [], collections.Counter(), [], []
        for href in documents:
            raw = archive.read(href)
            try:
                ElementTree.fromstring(raw)
            except ElementTree.ParseError as error:
                failures.append((posixpath.basename(href), str(error)))

            collector = TextCollector()
            collector.feed(raw.decode("utf-8", errors="replace"))
            types.update(collector.types)
            found = [" ".join(h.split()) for h in collector.headings if h.strip()]
            headings.extend(found)
            per_document.append(
                (posixpath.basename(href), len(WORD.findall(collector.text)), collector.text, found)
            )

        return {
            "encrypted": False,
            "package": package,
            "chapters": chapters,
            "source": source,
            # Abnahmekriterium 1 hängt an dieser Zahl: Unterpunkte eines Kapitels zeigen auf
            # dieselbe Datei und dürfen die Kapitelliste nicht aufblähen.
            "distinct": len({target for _, target in chapters}),
            "documents": documents,
            "failures": failures,
            "types": types,
            "headings": headings,
            "per_document": per_document,
            "words": sum(count for _, count, _, _ in per_document),
        }


def report(result: dict, only_chapters: bool) -> None:
    package = result["package"]
    print(f"  EPUB {package['version']} · {package['title']} · {package['creator']}")
    print(
        f"  Navigation: {result['source']} — {len(result['chapters'])} Einträge, "
        f"{result['distinct']} eindeutige Ziele"
    )
    for label, target in result["chapters"]:
        print(f"      {label[:70]:<70} {posixpath.basename(target)}")
    if only_chapters:
        return

    documents, failures = result["documents"], result["failures"]
    print(f"  Lesereihenfolge: {len(documents)} Dokumente")
    print(f"  XML-Prüfung (xml.etree): {len(documents) - len(failures)}/{len(documents)} gelesen")
    for name, message in failures[:5]:
        print(f"      gescheitert: {name} — {message}")

    print(f"  Fließtext (html.parser): {german(result['words'])} Wörter")
    marked = ", ".join(f"{key} {value}" for key, value in result["types"].most_common(12))
    print(f"  epub:type: {marked or 'keine Auszeichnung'}")
    print(f"  Überschriften h1–h3: {len(result['headings'])}")

    print("  Je Dokument:")
    for name, count, text, found in result["per_document"]:
        start = " ".join(text.split())[:52]
        print(f"      {name[:30]:<30} {german(count):>9} W  {len(found):>3} Ü  {start}")


def report_line(path: str, result: dict) -> None:
    """Eine Zeile je Buch — für den Blick über eine ganze Sammlung."""
    name = posixpath.basename(path.replace("\\", "/"))[:38]
    if result["encrypted"]:
        print(f"  {name:<38}  verschlüsselt, übersprungen")
        return
    documents, failures = result["documents"], result["failures"]
    print(
        f"  {name:<38}  EPUB {result['package']['version']:<4} "
        f"Navigation {result['distinct']:>3}  Dokumente {len(documents):>3}  "
        f"h1–h3 {len(result['headings']):>4}  XML {len(documents) - len(failures):>3}/"
        f"{len(documents):<3} {german(result['words']):>9} W"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", help="EPUB-Dateien")
    parser.add_argument(
        "--chapters", action="store_true", help="nur die Kapitelliste, kein Fließtext"
    )
    parser.add_argument(
        "--summary", action="store_true", help="eine Zeile je Buch, für ganze Sammlungen"
    )
    arguments = parser.parse_args()

    for path in arguments.files:
        if not arguments.summary:
            print(f"\n=== {posixpath.basename(path.replace(chr(92), '/'))} ===")
        try:
            result = measure(path)
            if arguments.summary:
                report_line(path, result)
            elif result["encrypted"]:
                print(f"  übersprungen: {ENCRYPTION} vorhanden — verschlüsselte Datei")
            else:
                report(result, arguments.chapters)
        except (zipfile.BadZipFile, ElementTree.ParseError, ValueError, KeyError, OSError) as error:
            # REGEL (dokumentation.md §4, Regel 13): kein except, das nur protokolliert
            # und weiterläuft. Hier ist die Meldung das Ergebnis — das Skript misst, wie
            # weit die Standardbibliothek trägt, und ein Fehlschlag ist ein Messwert.
            name = posixpath.basename(path.replace(chr(92), "/"))[:38]
            print(f"  {name if arguments.summary else ''}  FEHLGESCHLAGEN: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
