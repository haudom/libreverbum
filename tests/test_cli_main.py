"""Prüft `cli/main.py` — der vollständige Kapiteldurchlauf (bauplan.md T16).

`test_full_run_learns_a_word_and_an_expression_and_exports_them` ist Abnahmekriterium 3
"in klein": ein echter Durchlauf durch `pipeline.run_chapter`, die Tastatur-Triage und
den Export, an dessen Ende sowohl ein Einzelwort als auch eine Wendung auf der Druckseite
stehen. Die übrigen Tests prüfen die drei genannten Randfälle einzeln und ohne den vollen
Weg über spaCy, damit sie schnell bleiben.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cli import export
from cli.main import _build_parser, main

if TYPE_CHECKING:
    from conftest import ModelServerDouble

# ------------------------------------------------------------------------- Mini-EPUB
#
# Dieselbe Kapiteltextvorlage wie tests/test_pipeline.py (dort ausführlich begründet):
# abgestimmt auf mini_dictionary_db (tests/conftest.py) und enthält sowohl ein
# eindeutiges Einzelwort ("watch") als auch ein getrenntes Verb-Partikel-Paar ("gave
# up") für mini_dictionary_db's Stichwort "give up" — beide werden unten gelernt.

_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_CHAPTER_TEXT = (
    "He walked along a quiet street and saw the old bank stood beside the river, its "
    "walls painted red. She wanted to draw a picture and watch the sunset from there. "
    "In the end she gave up the chase."
)


def _chapter_xhtml(title: str, paragraph: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body><h1>{title}</h1><p>{paragraph}</p></body>
</html>
"""


_NAV_XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc">
    <ol><li><a href="chapter1.xhtml">Erstes Kapitel</a></li></ol>
  </nav>
</body>
</html>
"""

_PACKAGE_OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:cli-test</dc:identifier>
    <dc:title>CLI-Testbuch</dc:title>
    <dc:creator>Testautorin</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>
"""


@pytest.fixture
def book_epub(tmp_path: Path) -> Path:
    path = tmp_path / "book.epub"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", _CONTAINER_XML)
        archive.writestr("OEBPS/content.opf", _PACKAGE_OPF)
        archive.writestr("OEBPS/chapter1.xhtml", _chapter_xhtml("Erstes Kapitel", _CHAPTER_TEXT))
        archive.writestr("OEBPS/nav.xhtml", _NAV_XHTML)
    return path


def _no_read(prompt: str) -> str:
    raise AssertionError(f"Es wurde keine Eingabe erwartet, gefragt wurde: {prompt!r}")


def _write_config(
    data_dir: Path, *, model_url: str, model_name: str, dictionary_path: Path
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "config.toml").write_text(
        f'[model]\nurl = "{model_url}"\nname = "{model_name}"\n\n'
        f'[paths]\ndictionary = "{dictionary_path.as_posix()}"\nprofile = ""\n',
        encoding="utf-8",
    )


class _ScriptedConsole:
    """Testkonsole für einen vollständigen Lauf: beantwortet die Sammelaktions- und
    Profil-Bestätigungsfrage generisch und entscheidet bei jeder Einzelfrage anhand der
    zuletzt ausgegebenen Wortform, statt eine feste Anzahl Antworten vorzuhalten — eine
    Änderung an `extraction.py`, die die Wortliste um ein Wort verlängert oder verkürzt,
    soll diesen Test nicht allein deswegen zerbrechen (dokumentation.md §5, „Prüfe die
    Entscheidungen … nicht die Bildschirmausgabe Zeichen für Zeichen")."""

    def __init__(self, learn_words: set[str]) -> None:
        self._learn_words = learn_words
        self._pending: list[str] = []
        self.log: list[str] = []

    def write(self, text: str) -> None:
        self.log.append(text)
        self._pending.append(text)

    def read(self, prompt: str) -> str:
        if "Neu anlegen" in prompt:
            self._pending.clear()
            return "j"
        if "Sammelaktion" in prompt:
            self._pending.clear()
            return ""
        first_line = self._pending[0] if self._pending else ""
        self._pending.clear()
        word = first_line.split(" (", 1)[0]
        return "l" if word in self._learn_words else "s"


class _MarkOneWordKnownConsole:
    """Wie `_ScriptedConsole`, aber ohne Modellserver: markiert genau `known_word` als
    „kenne ich" ([k]) und alles andere als „skip" — für Abnahmekriterium 6, wo im ersten
    Durchlauf nichts gelernt werden muss, nur ein Wort als bekannt gebucht wird."""

    def __init__(self, known_word: str) -> None:
        self._known_word = known_word
        self._pending: list[str] = []
        self.log: list[str] = []

    def write(self, text: str) -> None:
        self.log.append(text)
        self._pending.append(text)

    def read(self, prompt: str) -> str:
        if "Neu anlegen" in prompt:
            self._pending.clear()
            return "j"
        if "Sammelaktion" in prompt:
            self._pending.clear()
            return ""
        first_line = self._pending[0] if self._pending else ""
        self._pending.clear()
        word = first_line.split(" (", 1)[0]
        return "k" if word == self._known_word else "s"


class _RejectWordConsole:
    """Bricht sofort ab, sobald `forbidden_word` in der Bildschirmausgabe auftaucht —
    Abnahmekriterium 6 verlangt, dass ein als bekannt gebuchtes Wort im zweiten
    Durchlauf weder in der Sammelaktionsliste noch in der Einzelabfrage erscheint."""

    def __init__(self, forbidden_word: str) -> None:
        self._forbidden_word = forbidden_word
        self._pending: list[str] = []
        self.log: list[str] = []

    def write(self, text: str) -> None:
        self.log.append(text)
        if f"{self._forbidden_word} (" in text:
            raise AssertionError(
                f"{self._forbidden_word!r} wurde im zweiten Durchlauf erneut angezeigt — "
                "das Profil greift nicht (Abnahmekriterium 6)."
            )
        self._pending.append(text)

    def read(self, prompt: str) -> str:
        if "Neu anlegen" in prompt:
            self._pending.clear()
            return "j"
        if "Sammelaktion" in prompt:
            self._pending.clear()
            return ""
        self._pending.clear()
        return "s"


def test_acceptance_6_a_second_run_does_not_ask_about_words_marked_known(
    tmp_path: Path, book_epub: Path, mini_dictionary_db: Path
) -> None:
    """Abnahmekriterium 6 (konzept.md, „Abnahmekriterien"): „Beim zweiten Durchlauf
    desselben Kapitels werden die als *bekannt* markierten Wörter **nicht erneut**
    abgefragt — das Profil greift." Hier über den vollen Einstiegspunkt `cli.main.main`,
    zweimal auf demselben Datenverzeichnis (Befund schwer 1, Durchsicht T16):
    `entry.status` aus `pipeline.run_chapter` wurde bis dahin von keinem `cli`-Modul
    gelesen, und der zweite Durchlauf fragte dieselben Wörter erneut ab."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://unerreichbar.invalid",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )

    first_console = _MarkOneWordKnownConsole(known_word="watch")
    first_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=first_console.read,
        write_line=first_console.write,
    )
    assert first_exit == 0, "\n".join(first_console.log)
    assert any(line.startswith("watch (") for line in first_console.log), (
        "Testvoraussetzung verletzt: 'watch' wurde im ersten Durchlauf gar nicht gefragt."
    )

    second_console = _RejectWordConsole(forbidden_word="watch")
    second_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=second_console.read,
        write_line=second_console.write,
    )
    assert second_exit == 0, "\n".join(second_console.log)


def test_main_creates_config_on_the_first_run_and_stops(tmp_path: Path) -> None:
    """bauplan.md T16: „fehlende config.toml wird einmalig angelegt und gemeldet" —
    hier über den vollen Einstiegspunkt, nicht nur über `cli.config.load_config`."""
    written: list[str] = []

    exit_code = main(
        ["irrelevant.epub", "--data-dir", str(tmp_path)],
        read_line=_no_read,
        write_line=written.append,
    )

    assert exit_code == 0
    assert (tmp_path / "config.toml").is_file()
    assert any("config.toml" in line for line in written)


def test_main_aborts_loudly_when_the_dictionary_is_missing(tmp_path: Path) -> None:
    """dokumentation.md §4 Regel 13: fehlendes Wörterbuch bricht laut ab — kein leerer
    oder scheinbar erfolgreicher Durchlauf, kein `except`, das nur protokolliert."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=data_dir / "fehlt.sqlite3",
    )
    written: list[str] = []

    exit_code = main(
        ["irrelevant.epub", "--data-dir", str(data_dir)],
        read_line=_no_read,
        write_line=written.append,
    )

    assert exit_code == 1
    assert any("Wörterbuch nicht gefunden" in line for line in written)


def test_main_declines_to_create_a_profile_without_confirmation(
    tmp_path: Path, book_epub: Path, mini_dictionary_db: Path
) -> None:
    """Entscheidung zu T16 (siehe Bericht): Ein noch nicht vorhandenes Profil wird nicht
    wortlos angelegt — lehnt der Nutzer ab, entsteht keine Profildatei.

    Mit einem echten, lesbaren EPUB und `--chapter`: Ohne beide bräche der Lauf schon
    vorher an einer fehlenden Datei ab, und die Zusicherung unten bestünde selbst dann,
    wenn die Bestätigungsfrage gar nicht mehr gestellt würde (die Verfälschungsprobe des
    Berichts zu T16 hat genau das an einer früheren Fassung dieses Tests gezeigt)."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )

    exit_code = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=lambda _prompt: "n",
        write_line=lambda _text: None,
    )

    assert exit_code == 1
    assert not (data_dir / "profil.sqlite3").is_file()


def test_full_run_learns_a_word_and_an_expression_and_exports_them(
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
) -> None:
    """Abnahmekriterium 3 „in klein" (bauplan.md T16, Prüfspalte): ein vollständiger
    Durchlauf über `cli.main.main`, an dessen Ende sowohl das gelernte Einzelwort
    "watch" als auch die gelernte Wendung "gave up" auf der Druckseite stehen — die
    Wendung reicht damit tatsächlich bis zum Export, nicht nur bis in die Triage-Liste.
    """
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    output_dir = tmp_path / "export"
    model_server_double.choice = 1
    console = _ScriptedConsole(learn_words={"watch", "gave up"})

    exit_code = main(
        [
            str(book_epub),
            "--chapter",
            "1",
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
        ],
        read_line=console.read,
        write_line=console.write,
    )

    assert exit_code == 0, "\n".join(console.log)
    paths = export.export_paths(output_dir, "CLI-Testbuch", 1)
    assert paths.anki_path.is_file()
    assert paths.printout_path.is_file()

    html = paths.printout_path.read_text(encoding="utf-8")
    assert "watch" in html
    assert "gave up" in html


def test_help_text_survives_a_restricted_console_codepage() -> None:
    """Mittel 3 (Durchsicht T16): `argparse.print_help()`/`format_help()` schreiben
    direkt auf `sys.stdout`, an `cli.display.safe_print` vorbei (dokumentation.md §4
    Regel 13) — `python -m cli --help` durfte deshalb nicht mit `UnicodeEncodeError`
    abbrechen, wenn die Konsole nur `cp850` beherrscht, die klassische
    DOS-/conhost-Codepage älterer Windows-Konsolen (`tests/test_cli_display.py` nennt
    sie als die gefährliche — cp1252 stellt Gedankenstrich und typografische
    Anführungszeichen bereits dar, cp850 nicht). Bauart wie
    `test_safe_print_does_not_crash_on_a_restricted_console_codepage`."""
    help_text = _build_parser().format_help()

    help_text.encode("cp850", errors="strict")
