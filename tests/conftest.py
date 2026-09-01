"""Testvorrichtungen für Phase 1 (bauplan.md, T2).

Die Kernmodule (`dictionary`, `epub`, `translation`, …) gibt es noch nicht — trotzdem
sollen Tests gegen ein Wörterbuch, ein EPUB und einen Modellserver laufen können, ohne
eine echte, unversionierte Datei zu brauchen oder einen laufenden Server vorauszusetzen.
Dieses Modul legt dafür drei Vorrichtungen an, alle auf `tmp_path`:

- ein Mini-Wörterbuch im echten WikDict-Schema (Tabelle `translation` aus
  `tools/en-de.sqlite3`), mit `watch`, `draw`, `saw`, `bank`, `give up`, `red`, `street`
  und je einem Eintrag, den der T7-Filter entfernen muss (score < 50, Proper_noun)
- ein Mini-EPUB als ZIP, mit EPUB-3-Navigation (`nav.xhtml`), mit EPUB-2-Navigation
  (`toc.ncx`) und ganz ohne Navigation (technik.md §8). Beide Navigationsformen nennen
  weniger eindeutige Ziele als Einträge und lassen ein spine-Dokument aus — der
  Sherlock-Fall 18→14, an dem sich T12 messen muss
- eine Attrappe für den lokalen Modellserver, die nur die OpenAI-kompatible Teilmenge
  nachbildet, die `tools/sense_check.py` anspricht — mit einstellbarem HTTP-Fehlschlag,
  unbrauchbarer Antwort, dem gemessenen leisen Fehlschlag `finish_reason: "length"`
  (technik.md §3, „Zwingende Einstellung: Denkschritt abschalten") und der Ausweichantwort
  „keine passt" als regulärem Listeneintrag, nicht als Sonderwert (technik.md §3)

Dazu die Marken `needs_dictionary` und `needs_model`: Tests, die das echte Wörterbuch
beziehungsweise einen echten Modellserver brauchen, werden ohne die Voraussetzung
übersprungen statt zu scheitern.

Die Marke `needs_epub` (bauplan.md T12) folgt demselben Muster für die beiden
Gutenberg-EPUBs `tools/sherlock.epub` und `tools/dorian_gray.epub`, an denen technik.md
§8 die Navigationsauswertung gemessen hat.

Die Marke `needs_calibre_split_epub` (technik.md §8, Nachtrag 28.08.2026) steht für sich:
`tools/dune.epub` ist eine Verlagsdatei, kein Gutenberg-Text, den sich jeder beschaffen
kann, und deckt einen anderen Fall ab — Calibre zerlegt große Inhaltsdokumente in
`…_split_000`, `…_split_001`, `…`, wovon die Navigation nur auf das jeweils erste Stück
zeigt. Eine eigene Marke, damit ihr Fehlen nicht die vierzehn Sherlock-/Dorian-Gray-Tests
mit übersprungen lässt, die `needs_epub` tragen.

Die Marke `needs_wordfreq` prüft weder Datei noch Paket, sondern eine **zweite Umgebung**:
`wordfreq` ist bewusst keine Abhängigkeit des Projekts (technik.md §11) und liegt deshalb
nie in `.venv/`, während spaCy und `en_core_web_md` nur dort liegen. Der Reproduktionstest
zu `tools/build_wordfreq_preset.py` braucht beides und läuft deshalb zweistufig — Stufe 1
mit dem Interpreter aus `LIBREVERBUM_WORDFREQ_PYTHON`, Stufe 2 mit `sys.executable`. Fehlt
die Variable, wird übersprungen.
"""

from __future__ import annotations

import http.server
import json
import os
import sqlite3
import threading
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

import pytest

# --------------------------------------------------------------------- Mini-Wörterbuch

# REGEL (dokumentation.md §4, Regel 1): `watch` und `draw` behalten ihre Zeilen ohne
# sense-Text — genau die Hauptbedeutungen mit der höchsten Bewertung (technik.md §3,
# „Datenfalle: Einträge ohne Bedeutungstext"). Ein Test, der sie beim Aufbau der
# Vorrichtung wegließe, könnte eine Verletzung von Regel 1 nie bemerken.
#
# Schema und Werte sind aus der echten WikDict-Datenbank abgelesen (tools/en-de.sqlite3,
# Tabelle `translation`), nicht erfunden.
_DICTIONARY_ROWS: list[tuple[Any, ...]] = [
    # (lexentry, sense_num, sense, written_rep, trans_list, score, is_good, importance)
    ("eng/watch__Noun__1", None, None, "watch", "Uhr | Armbanduhr", 136.7, 1, 3.52),
    (
        "eng/watch__Verb__1",
        None,
        None,
        "watch",
        "beobachten | überwachen | ansehen",
        124.7,
        1,
        2.74,
    ),
    (
        "eng/watch__Noun__1",
        None,
        "person or group of people who guard",
        "watch",
        "Wache",
        106.1,
        1,
        1.83,
    ),
    ("eng/draw__Verb__1", None, None, "draw", "zeichnen | malen | skizzieren", 172.9, 1, 5.49),
    (
        "eng/draw__Noun__1",
        None,
        "tie as a result of a game",
        "draw",
        "Remis | Unentschieden",
        124.2,
        1,
        1.29,
    ),
    (
        "eng/draw__Verb__1",
        None,
        "to pull out, unsheath",
        "draw",
        "ziehen | herausziehen",
        122.5,
        1,
        6.15,
    ),
    ("eng/saw__Noun__1", None, "tool", "saw", "Säge", 240.0, 1, 1.26),
    ("eng/saw__Verb__1", None, "cut with a saw", "saw", "sägen", 172.5, 1, 1.04),
    ("eng/saw__Noun__2", None, "saying or proverb", "saw", "Sprichwort | Spruch", 101.1, 1, 1.22),
    ("eng/bank__Noun__1", None, "institution", "bank", "Bank", 250.0, 1, 3.46),
    ("eng/bank__Noun__2", None, "edge of river or lake", "bank", "Ufer", 129.5, 1, 1.97),
    (
        "eng/give_up__Verb__1",
        None,
        "admit defeat",
        "give up",
        "aufgeben | kapitulieren",
        120.0,
        1,
        1.73,
    ),
    ("eng/give_up__Verb__1", None, "surrender", "give up", "aufgeben | ergeben", 120.0, 1, 1.73),
    ("eng/red__Adjective__1", None, "having red as its colour", "red", "rot | Rot", 223.5, 1, 3.36),
    ("eng/red__Noun__1", None, "colour", "red", "Rot | rot", 133.1, 1, 1.88),
    (
        "eng/street__Noun__1",
        None,
        "paved part of road in a village or a town",
        "street",
        "Straße",
        210.8,
        1,
        2.20,
    ),
    # REGEL (bauplan.md, T7): Filter score ≥ 50 und Wortart nicht Proper_noun. Ohne einen
    # Eintrag, der jeweils genau daran hängt, fiele ein fehlender Filter an dieser
    # Vorrichtung nicht auf. Beide Zeilen aus tools/en-de.sqlite3 abgelesen, nicht erfunden.
    (None, None, None, "of the", "vom", 4.0, 0, 0.0004),  # score < 50 — muss raus
    (
        "eng/South_America__Proper_noun__1",
        None,
        "continent that is the southern part of the Americas",
        "South America",
        "Südamerika",
        220.0,
        1,
        0.75,
    ),  # Proper_noun trotz hohem score — muss raus
]


def _build_mini_dictionary(path: Path) -> None:
    """Legt die Wörterbuchdatei an — Tabellenname und Spalten wie in `tools/en-de.sqlite3`."""
    con = sqlite3.connect(path)
    try:
        # Spaltentypen gegen PRAGMA table_info(translation) der echten Datenbank geprüft
        # (Befund 7, Review Runde 1): Dort trägt ebenfalls nur written_rep den Typ TEXT,
        # der Rest bleibt ungetypt. Das ist der reale Bestand, keine Lücke hier.
        con.execute(
            "CREATE TABLE translation("
            "lexentry, sense_num, sense, written_rep TEXT, trans_list, score, is_good, importance"
            ")"
        )
        con.executemany("INSERT INTO translation VALUES (?, ?, ?, ?, ?, ?, ?, ?)", _DICTIONARY_ROWS)
        con.commit()
    finally:
        con.close()


@pytest.fixture
def mini_dictionary_db(tmp_path: Path) -> Path:
    """Mini-Wörterbuch im WikDict-Schema mit den sieben Stichwörtern aus bauplan.md T2,
    dazu zwei Einträgen, die der T7-Filter entfernen muss (score < 50, Proper_noun)."""
    path = tmp_path / "en-de.sqlite3"
    _build_mini_dictionary(path)
    return path


# --------------------------------------------------------------------------- Mini-EPUB

_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _chapter_xhtml(title: str, paragraph: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
  <h1>{title}</h1>
  <p>{paragraph}</p>
</body>
</html>
"""


_CHAPTER_1 = _chapter_xhtml(
    "Chapter One", "This is the first chapter of the mini book used for testing."
)
_CHAPTER_2 = _chapter_xhtml(
    "Chapter Two", "This is the second chapter, shorter than the first one."
)
_CHAPTER_3 = _chapter_xhtml(
    "Chapter Three", "This is the third chapter, which the navigation never names."
)

# REGEL (technik.md §8, „manchen Dateien fehlen die Kapitelgrenzen ganz"): vier Einträge
# auf zwei eindeutige Ziele — je zwei #anker in dieselbe Datei, wie bei Sherlocks
# Unterpunkten I./II./III., die die rohe Liste von 18 auf 14 eindeutige Ziele senken.
# Das dritte Kapitel steht in der spine, aber in keiner der beiden Navigationsformen.
# Sonst bestünde eine T12-Umsetzung, die die spine als Kapitelliste übernimmt, diese
# Vorrichtung ebenso wie die richtige (Befund 2, Review Runde 1).
_NAV_ENTRIES = [
    ("Chapter One, Beginning", "chapter1.xhtml#anfang"),
    ("Chapter One, Middle", "chapter1.xhtml#mitte"),
    ("Chapter Two, Beginning", "chapter2.xhtml#anfang"),
    ("Chapter Two, End", "chapter2.xhtml#ende"),
]


def _nav_xhtml() -> str:
    """EPUB-3-Navigationsdokument (nav.xhtml) mit den vier Einträgen aus `_NAV_ENTRIES`."""
    items = "\n".join(
        f'      <li><a href="{href}">{label}</a></li>' for label, href in _NAV_ENTRIES
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol>
{items}
    </ol>
  </nav>
</body>
</html>
"""


def _toc_ncx() -> str:
    """EPUB-2-Navigation (toc.ncx) mit denselben vier Einträgen wie `_nav_xhtml` — der
    Mehrheitsfall aus technik.md §8: zehn von zwölf gemessenen Dateien sind EPUB 2.0."""
    points = "\n".join(
        f"""    <navPoint id="np{n}">
      <navLabel><text>{label}</text></navLabel>
      <content src="{href}"/>
    </navPoint>"""
        for n, (label, href) in enumerate(_NAV_ENTRIES, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head></head>
  <docTitle><text>Mini-Buch</text></docTitle>
  <navMap>
{points}
  </navMap>
</ncx>
"""


def _package_opf(*, navigation: str) -> str:
    """OPF-Package-Datei. `navigation` ist ``"none"``, ``"nav"`` (EPUB-3-`nav.xhtml`) oder
    ``"ncx"`` (EPUB-2-`toc.ncx`, technik.md §8) — steuert Manifest-Eintrag, das
    `spine`-Attribut `toc` und die Versionsangabe."""
    nav_item = (
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml"'
        ' properties="nav"/>\n    '
        if navigation == "nav"
        else ""
    )
    ncx_item = (
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n    '
        if navigation == "ncx"
        else ""
    )
    spine_toc = ' toc="ncx"' if navigation == "ncx" else ""
    version = "2.0" if navigation == "ncx" else "3.0"
    chapter_items = "\n    ".join(
        f'<item id="chap{n}" href="chapter{n}.xhtml" media-type="application/xhtml+xml"/>'
        for n in (1, 2, 3)
    )
    spine_refs = "\n    ".join(f'<itemref idref="chap{n}"/>' for n in (1, 2, 3))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="{version}" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:mini-epub-test</dc:identifier>
    <dc:title>Mini-Buch</dc:title>
    <dc:creator>Test Autorin</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    {nav_item}{ncx_item}{chapter_items}
  </manifest>
  <spine{spine_toc}>
    {spine_refs}
  </spine>
</package>
"""


def _build_mini_epub(path: Path, *, navigation: str) -> None:
    """Baut ein minimales EPUB als ZIP zusammen (technik.md §8): `mimetype` unkomprimiert
    und als erster Eintrag, `META-INF/container.xml`, ein OPF mit Metadaten und `spine`
    aus drei Dokumenten.

    `navigation` wählt zwischen keiner Navigation (``"none"`` — der Fall, für den T12
    einen sichtbaren Hinweis liefern muss), EPUB-3-`nav.xhtml` (``"nav"``) und
    EPUB-2-`toc.ncx` (``"ncx"``). technik.md §8 nennt beide Formen; zehn der zwölf
    gemessenen Dateien sind EPUB 2.0."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _package_opf(navigation=navigation))
        archive.writestr("OEBPS/chapter1.xhtml", _CHAPTER_1)
        archive.writestr("OEBPS/chapter2.xhtml", _CHAPTER_2)
        archive.writestr("OEBPS/chapter3.xhtml", _CHAPTER_3)
        if navigation == "nav":
            archive.writestr("OEBPS/nav.xhtml", _nav_xhtml())
        elif navigation == "ncx":
            archive.writestr("OEBPS/toc.ncx", _toc_ncx())


@pytest.fixture
def mini_epub_with_navigation(tmp_path: Path) -> Path:
    """Mini-EPUB mit EPUB-3-Navigation (`nav.xhtml`, bauplan.md T2). Muss herauskommen:
    3 Dokumente in der spine, 2 eindeutige Ziele in der Navigation (technik.md §8,
    Sherlock-Fall 18→14) — siehe Kommentar bei `_NAV_ENTRIES`."""
    path = tmp_path / "with_navigation.epub"
    _build_mini_epub(path, navigation="nav")
    return path


@pytest.fixture
def mini_epub_with_ncx_navigation(tmp_path: Path) -> Path:
    """Mini-EPUB mit EPUB-2-Navigation (`toc.ncx`, bauplan.md T2) — derselbe Aufbau wie
    `mini_epub_with_navigation`, für den Mehrheitsfall aus technik.md §8 (zehn von zwölf
    gemessenen Dateien sind EPUB 2.0). Muss herauskommen: 3 Dokumente in der spine,
    2 eindeutige Ziele in der Navigation."""
    path = tmp_path / "with_ncx_navigation.epub"
    _build_mini_epub(path, navigation="ncx")
    return path


@pytest.fixture
def mini_epub_without_navigation(tmp_path: Path) -> Path:
    """Mini-EPUB ohne Navigation — der Rückfallfall aus technik.md §8, für den T12 einen
    sichtbaren Hinweis liefern muss (bauplan.md, T2)."""
    path = tmp_path / "without_navigation.epub"
    _build_mini_epub(path, navigation="none")
    return path


# --------------------------------------------------------- Attrappe für den Modellserver


@dataclass
class ModelServerDouble:
    """Adresse, Antwortverhalten und aufgezeichnete Anfragen der Modellserver-Attrappe.

    Bildet nur die OpenAI-kompatible Teilmenge nach, die `tools/sense_check.py` anspricht:
    `/v1/models` und `/v1/chat/completions`. `choice` legt fest, welche Nummer die Attrappe
    im Gutfall (``"ok"``) und in der Ausweichantwort (``"no_match"``) als `choice`
    zurückgibt; Tests setzen sie vor der Anfrage. `behavior` schaltet zwischen den Fällen
    um, die T11 unterscheiden muss (Regel 13, „Die Falle: es scheitert nicht laut, sondern
    leise"):

    - ``"ok"`` — wohlgeformte Antwort mit einer echten Bedeutungsnummer
    - ``"no_match"`` — **kein Fehlschlag**, sondern der Gutfall der Ausweichantwort „keine
      passt" (technik.md §3, offener Punkt): ein **regulärer Eintrag** der Auswahlliste,
      die Nummer des zuletzt „keine passt" beschrifteten Eintrags (N+1 bei N echten
      Bedeutungen) — bewusst **kein Sonderwert außerhalb von 1..N+1**. Ein Sonderwert wie
      `0` läge zugleich auf dem üblichen ersten Listenindex, und eine T11-Umsetzung läse
      „keine passt" damit still als „erste Bedeutung" — genau der stille Fehlschlag, den
      der `saw`-Fall beschreibt
    - ``"http_error"`` — HTTP 500
    - ``"malformed"`` — Antwortkörper, der nicht dem erwarteten JSON-Schema entspricht
    - ``"truncated"`` — HTTP 200 mit `finish_reason: "length"` und leerem Inhalt: der
      gemessene Fehlschlag aus technik.md §3, „Zwingende Einstellung: Denkschritt
      abschalten" — sieht wie ein Erfolg aus (Status 200, wohlgeformte `choices`), ist
      aber keiner

    `requests` hält jede empfangene Anfrage fest, damit ein Test etwa `reasoning_effort`
    prüfen kann (Regel 7)."""

    url: str
    model_name: str
    choice: int = 1
    behavior: Literal["ok", "no_match", "http_error", "malformed", "truncated"] = "ok"
    requests: list[dict[str, Any]] = field(default_factory=list)


class _ModelServerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass  # Testlauf soll nicht auf stderr protokollieren

    def do_GET(self) -> None:
        server = cast("_ModelServerHTTPServer", self.server)
        if self.path == "/v1/models":
            self._reply(200, {"data": [{"id": server.double.model_name}]})
        else:
            self._reply(404, {"error": "unbekannter Pfad"})

    def do_POST(self) -> None:
        server = cast("_ModelServerHTTPServer", self.server)
        if self.path != "/v1/chat/completions":
            self._reply(404, {"error": "unbekannter Pfad"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        server.double.requests.append(body)
        behavior = server.double.behavior
        if behavior == "http_error":
            self._reply(500, {"error": "interner Serverfehler"})
            return
        if behavior == "malformed":
            content, finish_reason = "Diese Antwort folgt keinem JSON-Schema.", "stop"
        elif behavior == "truncated":
            # REGEL (technik.md §3, „Zwingende Einstellung: Denkschritt abschalten"): Ohne
            # reasoning_effort: none verbraucht das Modell sein Budget beim Nachdenken und
            # liefert HTTP 200 mit finish_reason: length und leerem Inhalt — sieht wie ein
            # Erfolg aus, ist aber keiner.
            content, finish_reason = "", "length"
        else:
            # "ok" und "no_match" unterscheiden sich nur in der Nummer, die choice trägt —
            # die Ausweichantwort ist ein regulärer Listeneintrag, kein Sonderwert.
            content, finish_reason = json.dumps({"choice": server.double.choice}), "stop"
        self._reply(
            200,
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": finish_reason,
                    }
                ]
            },
        )

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class _ModelServerHTTPServer(http.server.ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[_ModelServerHandler],
        double: ModelServerDouble,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.double = double


@pytest.fixture
def model_server_double() -> Iterator[ModelServerDouble]:
    """Attrappe für den lokalen Modellserver — läuft ohne Netz und ohne echten Server
    (bauplan.md, T2). Das Gegenstück, gegen das T11 geprüft wird.

    `url` trägt `/v1` (Befund schwer 2, Durchsicht T16): technik.md §9 dokumentiert
    `model.url` als `http://localhost:11434/v1`, die `base_url`-Form OpenAI-kompatibler
    Server — vorher lieferte diese Attrappe ein blankes `http://127.0.0.1:{port}` ohne
    `/v1`, und `cli/model.py` sowie `libreverbum/translation.py` hängten selbst noch
    einmal `/v1` an. Beide Fehler hoben sich in den Tests auf (`…/v1/models` traf zufällig
    genau den Pfad, den `_ModelServerHandler.do_GET` erwartet), und das doppelte `/v1`
    gegen einen echten Server (HTTP 404) fiel deshalb nie auf (dokumentation.md §5,
    „Woran geprüft wird: die Vorrichtung zeigt Laufen, die Fremdquelle Stimmen")."""
    double = ModelServerDouble(url="", model_name="mini-model")
    server = _ModelServerHTTPServer(("127.0.0.1", 0), _ModelServerHandler, double)
    double.url = f"http://127.0.0.1:{server.server_port}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield double
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# --------------------------------------------------- Marken needs_dictionary, needs_model


def _real_dictionary_path() -> Path:
    return Path(__file__).resolve().parent.parent / "tools" / "en-de.sqlite3"


@pytest.fixture
def real_dictionary_path() -> Path:
    """Pfad zur echten WikDict-Datenbank (`tools/en-de.sqlite3`) — dieselbe Stelle, gegen
    die auch `pytest_collection_modifyitems` die Marke `needs_dictionary` prüft. Einzige
    Stelle im Baum, damit ein driftender zweiter Pfad nicht still am Test vorbeiläuft."""
    return _real_dictionary_path()


def _real_model_url() -> str | None:
    # Bewusst keine Autosuche wie in tools/sense_check.py: Die dort gefundene Adresse
    # wäre im Zweifel der falsche Server (technik.md §9, „Die Autosuche aus tools/ ist
    # ausdrücklich nicht das Vorbild"). Wer needs_model-Tests ausführen will, setzt die
    # Umgebungsvariable — sonst wird übersprungen, nicht geraten.
    return os.environ.get("LIBREVERBUM_MODEL_URL")


def _real_epub_paths() -> dict[str, Path]:
    tools_dir = Path(__file__).resolve().parent.parent / "tools"
    return {"sherlock": tools_dir / "sherlock.epub", "dorian_gray": tools_dir / "dorian_gray.epub"}


@pytest.fixture
def real_epub_paths() -> dict[str, Path]:
    """Pfade zu `tools/sherlock.epub` und `tools/dorian_gray.epub` — den beiden Dateien,
    an denen technik.md §8 die Navigationsauswertung gemessen hat (bauplan.md T12).
    Dieselbe Stelle, gegen die auch `pytest_collection_modifyitems` die Marke
    `needs_epub` prüft."""
    return _real_epub_paths()


def _real_dune_epub_path() -> Path:
    return Path(__file__).resolve().parent.parent / "tools" / "dune.epub"


@pytest.fixture
def real_dune_epub_path() -> Path:
    """Pfad zu `tools/dune.epub` (technik.md §8, Nachtrag 28.08.2026) — dem
    Calibre-Konvertat, an dem der Mehrdokument-Fall gemessen wurde: Die Navigation zeigt
    nur auf das jeweils erste Stück eines in `…_split_NNN` zerlegten Inhaltsdokuments.
    Dieselbe Stelle, gegen die auch `pytest_collection_modifyitems` die Marke
    `needs_calibre_split_epub` prüft."""
    return _real_dune_epub_path()


def _wordfreq_python() -> str | None:
    # REGEL (dokumentation.md §4, Regel 15, „die Rohquelle entscheidet"): Der Test zu
    # tools/build_wordfreq_preset.py prüft die eingefrorene Datei gegen die echte
    # wordfreq-Bibliothek, nicht gegen eine erinnerte Zahl. wordfreq ist bewusst keine
    # Abhängigkeit des Projekts (technik.md §2, „Häufigkeitsdaten — unkritisch") und
    # liegt deshalb nie in .venv/ — die Marke zeigt daher auf einen *zweiten*
    # Interpreter: Stufe 1 des Bauskripts läuft dort, Stufe 2 braucht spaCy und
    # en_core_web_md und läuft mit sys.executable in .venv/. Vorbild ist _real_model_url()
    # oben: keine Autosuche, sondern eine Umgebungsvariable — sonst wird übersprungen,
    # nicht geraten (Befund 1, Review Bauschritt 1: die frühere Paketprüfung konnte in
    # keiner der beiden Umgebungen zutreffen und übersprang deshalb immer).
    return os.environ.get("LIBREVERBUM_WORDFREQ_PYTHON")


@pytest.fixture
def wordfreq_python() -> str:
    """Interpreter einer Wegwerfumgebung mit `wordfreq` (`LIBREVERBUM_WORDFREQ_PYTHON`) —
    dieselbe Stelle, gegen die auch `pytest_collection_modifyitems` die Marke
    `needs_wordfreq` prüft."""
    path = _wordfreq_python()
    assert path is not None, "needs_wordfreq hätte übersprungen haben müssen"
    return path


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Überspringt `needs_dictionary`-, `needs_model`-, `needs_epub`-,
    `needs_calibre_split_epub`- und `needs_wordfreq`-Tests ohne ihre Voraussetzung, statt
    sie scheitern zu lassen (bauplan.md, T2 und T12; technik.md §8, Nachtrag 28.08.2026)."""
    if not _real_dictionary_path().exists():
        skip_dictionary = pytest.mark.skip(reason="echtes Wörterbuch tools/en-de.sqlite3 fehlt")
        for item in items:
            if item.get_closest_marker("needs_dictionary") is not None:
                item.add_marker(skip_dictionary)
    if not _real_model_url():
        skip_model = pytest.mark.skip(
            reason="kein Modellserver konfiguriert (LIBREVERBUM_MODEL_URL setzen)"
        )
        for item in items:
            if item.get_closest_marker("needs_model") is not None:
                item.add_marker(skip_model)
    if not all(path.is_file() for path in _real_epub_paths().values()):
        skip_epub = pytest.mark.skip(
            reason="echte EPUB-Dateien tools/sherlock.epub, tools/dorian_gray.epub fehlen"
        )
        for item in items:
            if item.get_closest_marker("needs_epub") is not None:
                item.add_marker(skip_epub)
    if not _real_dune_epub_path().is_file():
        skip_dune = pytest.mark.skip(reason="echte EPUB-Datei tools/dune.epub fehlt")
        for item in items:
            if item.get_closest_marker("needs_calibre_split_epub") is not None:
                item.add_marker(skip_dune)
    if not _wordfreq_python():
        skip_wordfreq = pytest.mark.skip(
            reason="kein Interpreter mit wordfreq konfiguriert "
            "(LIBREVERBUM_WORDFREQ_PYTHON setzen; wordfreq liegt bewusst nicht in .venv/, "
            "siehe tools/build_wordfreq_preset.py)"
        )
        for item in items:
            if item.get_closest_marker("needs_wordfreq") is not None:
                item.add_marker(skip_wordfreq)
