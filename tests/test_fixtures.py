"""Selbsttests der Testvorrichtungen aus conftest.py (bauplan.md, T2).

Die Kernmodule, gegen die diese Vorrichtungen später eingesetzt werden, gibt es noch
nicht — deshalb belegt hier jeder Test unmittelbar, dass die erzeugte Vorrichtung
tatsächlich das ist, was sie behauptet.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Nur für die statische Typprüfung: Ein echter Import von conftest bricht unter
# --import-mode=importlib (kein Modul namens `conftest`) und ebenso, sobald es ein
# tests/__init__.py gibt. Dank `from __future__ import annotations` wertet Python
# Parameterannotationen zur Laufzeit nicht aus — die pytest-übliche Lösung, den Typ
# über die Fixture zu beziehen statt ihn zu importieren.
if TYPE_CHECKING:
    from conftest import ModelServerDouble

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
_XHTML_NS = {"xhtml": "http://www.w3.org/1999/xhtml"}
_NCX_NS = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}


# ------------------------------------------------------------------ Mini-Wörterbuch


def test_mini_dictionary_has_all_seven_required_headwords(mini_dictionary_db: Path) -> None:
    """Bauplan.md T2: das Mini-Wörterbuch enthält watch, draw, saw, bank, give up, red,
    street — die sieben in der Teilaufgabe geforderten Stichwörter. Daneben stehen
    ausdrücklich die beiden T7-Filterfälle `of the` und `South America` darin
    (bauplan.md T7) — die schließt dieser Test nicht aus, er verlangt sie nur nicht."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        headwords = {row[0] for row in con.execute("SELECT DISTINCT written_rep FROM translation")}
    finally:
        con.close()
    required = {"watch", "draw", "saw", "bank", "give up", "red", "street"}
    assert required <= headwords
    assert {"of the", "South America"} <= headwords


def test_mini_dictionary_filter_cases_violate_t7_criteria(mini_dictionary_db: Path) -> None:
    """Bauplan.md T7: der Filter verlangt `score >= 50` und Wortart ungleich Proper_noun.
    `of the` verletzt das erste Kriterium, `South America` das zweite — ohne diesen Beleg
    wäre nicht festgehalten, wozu die beiden Einträge in der Vorrichtung stehen."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        of_the_score = con.execute(
            "SELECT score FROM translation WHERE written_rep = ?", ("of the",)
        ).fetchone()
        south_america_lexentry = con.execute(
            "SELECT lexentry FROM translation WHERE written_rep = ?", ("South America",)
        ).fetchone()
    finally:
        con.close()
    assert of_the_score is not None
    assert of_the_score[0] < 50
    assert south_america_lexentry is not None
    assert "Proper_noun" in south_america_lexentry[0]


def test_mini_dictionary_answers_sense_check_query_with_multiple_rows(
    mini_dictionary_db: Path,
) -> None:
    """`watch` und `draw` liefern über die Abfrage aus tools/sense_check.py mehrere
    Zeilen, darunter je eine ohne sense-Text — Regel 1 (dokumentation.md §4)."""
    con = sqlite3.connect(mini_dictionary_db)
    try:
        for word in ("watch", "draw"):
            rows = con.execute(
                "SELECT lexentry, sense, trans_list FROM translation "
                "WHERE written_rep = ? ORDER BY score DESC",
                (word,),
            ).fetchall()
            assert len(rows) > 1, f"{word!r} liefert nur {len(rows)} Zeile(n)"
            assert any(sense is None for _, sense, _ in rows), (
                f"{word!r} hat keine Zeile ohne sense-Text — Regel 1 wäre ungeprüft"
            )
    finally:
        con.close()


# ------------------------------------------------------------------------- Mini-EPUB


def test_mini_epub_with_navigation_is_a_valid_zip_referencing_an_existing_opf(
    mini_epub_with_navigation: Path,
) -> None:
    """Bauplan.md T2: das Mini-EPUB lässt sich mit zipfile öffnen, und container.xml
    verweist auf ein tatsächlich vorhandenes OPF."""
    with zipfile.ZipFile(mini_epub_with_navigation) as archive:
        names = set(archive.namelist())
        assert "mimetype" in names
        container = ElementTree.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find("c:rootfiles/c:rootfile", _CONTAINER_NS)
        assert rootfile is not None
        assert rootfile.get("full-path") in names


def test_mini_epub_with_navigation_has_a_navigation_document(
    mini_epub_with_navigation: Path,
) -> None:
    """Die Variante mit Navigation zeichnet nach technik.md §8 ein EPUB-3-
    Navigationsdokument im Manifest aus und nennt darin mehrere Kapitelziele."""
    with zipfile.ZipFile(mini_epub_with_navigation) as archive:
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        nav_items = [
            item
            for item in opf.findall("opf:manifest/opf:item", _OPF_NS)
            if "nav" in (item.get("properties") or "").split()
        ]
        assert len(nav_items) == 1
        nav_href = nav_items[0].get("href")
        assert nav_href
        nav_doc = ElementTree.fromstring(archive.read(f"OEBPS/{nav_href}"))
        targets = {
            anchor.get("href")
            for nav in nav_doc.iter(f"{{{_XHTML_NS['xhtml']}}}nav")
            for anchor in nav.iter(f"{{{_XHTML_NS['xhtml']}}}a")
        }
        assert len(targets) >= 2


def test_mini_epub_with_navigation_unique_targets_differ_from_spine_document_count(
    mini_epub_with_navigation: Path,
) -> None:
    """Der wichtigste Beleg aus technik.md §8 (Sherlock-Fall 18→14): Die spine nennt drei
    Dokumente, die Navigation aber nur zwei eindeutige Ziele — je zwei #anker in
    chapter1.xhtml und chapter2.xhtml zählen als ein Ziel, chapter3.xhtml fehlt in der
    Navigation ganz. Eine T12-Umsetzung, die die spine als Kapitelliste übernimmt, muss
    daran scheitern (bauplan.md T12)."""
    with zipfile.ZipFile(mini_epub_with_navigation) as archive:
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        spine_document_count = len(opf.findall("opf:spine/opf:itemref", _OPF_NS))
        nav_doc = ElementTree.fromstring(archive.read("OEBPS/nav.xhtml"))
        hrefs = {
            anchor.get("href")
            for nav in nav_doc.iter(f"{{{_XHTML_NS['xhtml']}}}nav")
            for anchor in nav.iter(f"{{{_XHTML_NS['xhtml']}}}a")
        }
    unique_targets = {href.split("#", 1)[0] for href in hrefs if href}
    assert spine_document_count == 3
    assert len(hrefs) == 4
    assert len(unique_targets) == 2
    assert len(unique_targets) != spine_document_count


def test_mini_epub_with_ncx_navigation_has_toc_ncx_and_no_nav_xhtml(
    mini_epub_with_ncx_navigation: Path,
) -> None:
    """Bauplan.md T2 / technik.md §8 (Mehrheitsfall EPUB 2.0, zehn von zwölf gemessenen
    Dateien): die Variante hat wirklich EPUB-2-Navigation im ZIP und im Manifest
    ausgezeichnet, und kein nav.xhtml."""
    with zipfile.ZipFile(mini_epub_with_ncx_navigation) as archive:
        names = set(archive.namelist())
        assert "OEBPS/toc.ncx" in names
        assert "OEBPS/nav.xhtml" not in names
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        ncx_items = [
            item
            for item in opf.findall("opf:manifest/opf:item", _OPF_NS)
            if item.get("media-type") == "application/x-dtbncx+xml"
        ]
        assert len(ncx_items) == 1
        assert ncx_items[0].get("href") == "toc.ncx"
        nav_items = [
            item
            for item in opf.findall("opf:manifest/opf:item", _OPF_NS)
            if "nav" in (item.get("properties") or "").split()
        ]
        assert not nav_items


def test_mini_epub_with_ncx_navigation_unique_targets_differ_from_spine_document_count(
    mini_epub_with_ncx_navigation: Path,
) -> None:
    """Derselbe Beleg wie bei nav.xhtml, für die EPUB-2-Navigation (technik.md §8,
    Sherlock-Fall 18→14): drei Dokumente in der spine, zwei eindeutige Ziele in
    toc.ncx — T12 muss beide Navigationsformen daran gleichermaßen scheitern lassen."""
    with zipfile.ZipFile(mini_epub_with_ncx_navigation) as archive:
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        spine_document_count = len(opf.findall("opf:spine/opf:itemref", _OPF_NS))
        ncx_doc = ElementTree.fromstring(archive.read("OEBPS/toc.ncx"))
        srcs = {content.get("src") for content in ncx_doc.iter(f"{{{_NCX_NS['ncx']}}}content")}
    unique_targets = {src.split("#", 1)[0] for src in srcs if src}
    assert spine_document_count == 3
    assert len(srcs) == 4
    assert len(unique_targets) == 2
    assert len(unique_targets) != spine_document_count


def test_mini_epub_without_navigation_is_a_valid_zip_referencing_an_existing_opf(
    mini_epub_without_navigation: Path,
) -> None:
    """Dieselbe Grundstruktur wie mit Navigation — nur ohne deren Auszeichnung."""
    with zipfile.ZipFile(mini_epub_without_navigation) as archive:
        names = set(archive.namelist())
        container = ElementTree.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find("c:rootfiles/c:rootfile", _CONTAINER_NS)
        assert rootfile is not None
        assert rootfile.get("full-path") in names


def test_mini_epub_without_navigation_really_has_none(mini_epub_without_navigation: Path) -> None:
    """Bauplan.md T2 / technik.md §8: die Variante ohne Navigation hat wirklich keine —
    genau der Fall, für den T12 einen sichtbaren Hinweis liefern muss."""
    with zipfile.ZipFile(mini_epub_without_navigation) as archive:
        names = set(archive.namelist())
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        nav_items = [
            item
            for item in opf.findall("opf:manifest/opf:item", _OPF_NS)
            if "nav" in (item.get("properties") or "").split()
        ]
        assert not nav_items
        assert "OEBPS/nav.xhtml" not in names
        assert "OEBPS/toc.ncx" not in names


# ------------------------------------------------------------ Modellserver-Attrappe


def test_model_server_double_answers_models_endpoint(
    model_server_double: ModelServerDouble,
) -> None:
    """Bauplan.md T2: die Attrappe beantwortet /v1/models wie ein echter,
    OpenAI-kompatibler Server (vgl. tools/sense_check.py, `find_server`).

    `model_server_double.url` trägt `/v1` bereits selbst (Befund schwer 2, Durchsicht
    T16, technik.md §9) — hier wird deshalb nur noch `/models` angehängt."""
    with urllib.request.urlopen(f"{model_server_double.url}/models", timeout=5) as response:
        payload = json.load(response)
    assert payload["data"][0]["id"] == model_server_double.model_name


def test_model_server_double_answers_chat_completions_with_well_formed_json(
    model_server_double: ModelServerDouble,
) -> None:
    """Die Attrappe liefert eine wohlgeformte Antwort im Format, das tools/sense_check.py
    (`ask_model`) erwartet, und zeichnet die Anfrage auf — hier geprüft an
    `reasoning_effort` (Regel 7)."""
    model_server_double.choice = 2
    body = {
        "model": model_server_double.model_name,
        "messages": [{"role": "user", "content": "Welche Bedeutung passt?"}],
        "reasoning_effort": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "sense_choice", "schema": {"type": "object"}},
        },
    }
    request = urllib.request.Request(
        f"{model_server_double.url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.load(response)
    content = payload["choices"][0]["message"]["content"]
    assert json.loads(content) == {"choice": 2}
    assert model_server_double.requests[-1]["reasoning_effort"] == "none"


def _post_chat_completions(model_server_double: ModelServerDouble) -> urllib.request.Request:
    # model_server_double.url trägt /v1 bereits selbst (Befund schwer 2, Durchsicht T16).
    body = {"model": model_server_double.model_name, "messages": [{"role": "user", "content": "?"}]}
    return urllib.request.Request(
        f"{model_server_double.url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def test_model_server_double_http_error_is_a_visible_failure(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 13: ein HTTP-Fehlschlag (hier 500) muss beim Aufrufer als Fehler ankommen —
    T11 braucht genau diesen Fall, um den Abbruch statt eines stillen Lochs zu prüfen."""
    model_server_double.behavior = "http_error"
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(_post_chat_completions(model_server_double), timeout=5)
    assert excinfo.value.code == 500


def test_model_server_double_malformed_response_is_not_valid_json(
    model_server_double: ModelServerDouble,
) -> None:
    """Regel 13: eine unbrauchbare Antwort — ein Rumpf, der nicht dem erwarteten
    JSON-Schema entspricht — lässt sich nicht als Bedeutungsnummer auswerten und darf
    T11 deshalb nicht als stille Zahl durchrutschen."""
    model_server_double.behavior = "malformed"
    with urllib.request.urlopen(_post_chat_completions(model_server_double), timeout=5) as response:
        payload = json.load(response)
    content = payload["choices"][0]["message"]["content"]
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)


def test_model_server_double_truncated_response_looks_like_success_but_is_empty(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, „Zwingende Einstellung: Denkschritt abschalten": Ohne
    reasoning_effort: none verbraucht das Modell sein Budget beim Nachdenken und liefert
    HTTP 200 mit finish_reason: length und leerem Inhalt — der gemessene Fehlschlag, der
    T11 am ehesten hereinlegt, weil er wie ein Erfolg aussieht."""
    model_server_double.behavior = "truncated"
    with urllib.request.urlopen(_post_chat_completions(model_server_double), timeout=5) as response:
        assert response.status == 200
        payload = json.load(response)
    choice = payload["choices"][0]
    assert choice["finish_reason"] == "length"
    assert choice["message"]["content"] == ""


def test_model_server_double_no_match_answer_is_a_regular_list_entry(
    model_server_double: ModelServerDouble,
) -> None:
    """technik.md §3, offener Punkt „keine passt": Der `saw`-Fall zeigt, dass das Modell
    ohne diese Ausweichantwort keinen Fehler der Vorstufe melden kann. Die Attrappe liefert
    sie als wohlgeformtes JSON mit der Nummer des zuletzt „keine passt" beschrifteten
    Listeneintrags (N+1 bei N Bedeutungen) — kein Sonderwert außerhalb von 1..N+1. `0` läge
    zugleich auf dem üblichen ersten Listenindex und würde „keine passt" still als „erste
    Bedeutung" durchgehen lassen — dieselbe Falle wie im `saw`-Fall."""
    model_server_double.behavior = "no_match"
    model_server_double.choice = 3  # N=2 echte Bedeutungen, „keine passt" auf Platz N+1
    with urllib.request.urlopen(_post_chat_completions(model_server_double), timeout=5) as response:
        payload = json.load(response)
    content = payload["choices"][0]["message"]["content"]
    assert json.loads(content) == {"choice": 3}


def test_unreachable_model_server_is_a_visible_failure() -> None:
    """dokumentation.md §5, Regel 13: ein unerreichbarer Modellserver ergibt einen
    sichtbaren Fehlschlag, kein stilles Loch in der Wortliste — hier eine Adresse, an der
    kein Server lauscht (keine `model_server_double`-Attrappe gestartet)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]
    request = urllib.request.Request(
        f"http://127.0.0.1:{unused_port}/v1/chat/completions",
        data=json.dumps({"model": "mini-model", "messages": []}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(request, timeout=2)


# ----------------------------------------------------- Marken needs_dictionary, needs_model


@pytest.mark.needs_dictionary
def test_needs_dictionary_marker_reaches_the_real_wikdict_schema(
    real_dictionary_path: Path,
) -> None:
    """Bauplan.md T2: Mit tools/en-de.sqlite3 prüft dieser Test das echte WikDict-Schema
    gegen die Spalten der Mini-Vorrichtung; fehlt die Datei, wird er übersprungen statt
    zu scheitern."""
    con = sqlite3.connect(real_dictionary_path)
    try:
        columns = {row[1] for row in con.execute("PRAGMA table_info(translation)")}
    finally:
        con.close()
    assert {"lexentry", "sense", "written_rep", "trans_list", "score"} <= columns


@pytest.mark.needs_model
def test_needs_model_marker_reaches_a_configured_server() -> None:
    """Bauplan.md T2: Mit LIBREVERBUM_MODEL_URL erreicht dieser Test den echten
    Modellserver; ohne die Umgebungsvariable wird er übersprungen statt zu scheitern."""
    # (Befund mittel 2, Durchsicht T16): url trägt /v1 bereits selbst (technik.md §9,
    # cli/model.py) — ein zusätzliches /v1 hier ergab beim echten Server .../v1/v1/models
    # und HTTP 404 statt 200.
    url = os.environ["LIBREVERBUM_MODEL_URL"].rstrip("/")
    with urllib.request.urlopen(f"{url}/models", timeout=5) as response:
        assert response.status == 200
