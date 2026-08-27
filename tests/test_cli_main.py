"""Prüft `cli/main.py` — der vollständige Kapiteldurchlauf (bauplan.md T16).

`test_full_run_learns_a_word_and_an_expression_and_exports_them` ist Abnahmekriterium 3
"in klein": ein echter Durchlauf durch `pipeline.run_chapter`, die Tastatur-Triage und
den Export, an dessen Ende sowohl ein Einzelwort als auch eine Wendung auf der Druckseite
stehen. Die übrigen Tests prüfen die drei genannten Randfälle einzeln und ohne den vollen
Weg über spaCy, damit sie schnell bleiben.
"""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cli import export
from cli import main as cli_main
from cli.main import _build_parser, main
from libreverbum import dictionary

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from conftest import ModelServerDouble

    from libreverbum import pipeline

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


def _index_names(con: sqlite3.Connection) -> set[str]:
    """Die Namen der auf `translation` liegenden Indizes — ohne die von SQLite selbst
    angelegten (`sqlite_autoindex_…`)."""
    return {
        str(row[0])
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'translation'"
        )
        if not str(row[0]).startswith("sqlite_autoindex")
    }


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
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
) -> None:
    """Abnahmekriterium 6 (konzept.md, „Abnahmekriterien"): „Beim zweiten Durchlauf
    desselben Kapitels werden die als *bekannt* markierten Wörter **nicht erneut**
    abgefragt — das Profil greift." Hier über den vollen Einstiegspunkt `cli.main.main`,
    zweimal auf demselben Datenverzeichnis (Befund schwer 1, Durchsicht T16):
    `entry.status` aus `pipeline.run_chapter` wurde bis dahin von keinem `cli`-Modul
    gelesen, und der zweite Durchlauf fragte dieselben Wörter erneut ab.

    Ein erreichbarer Modellserver ist seit der zweiten T16-Durchsicht (Befund schwer 1)
    nötig, obwohl in diesem Test nie „will ich lernen" gewählt wird: Die Bedeutung wird
    seither vor **jeder** Triage-Entscheidung aufgelöst (`pipeline.resolve_triage_entries`,
    konzept.md Nachtrag 17.08.2026), auch für „kenne ich" und „überspringen" — andere
    Wörter im Kapitel (`bank`, `draw`, „give up") brauchen dafür ein Modell, selbst wenn
    dieser Test nur `watch` beobachtet.

    `watch` ist dabei **eindeutig** (ein einziger Kandidat in `mini_dictionary_db`) — der
    ursprüngliche Test bestand deshalb schon vor der Behebung, nur zufällig: Der alte
    Vorfilter verglich, ob *irgendeine* Bedeutung bekannt sei (`any(...)`), gegen
    `candidates[0]` auf der Schreibseite — bei genau einem Kandidaten sind beide
    dasselbe. Der eigentliche, vorher rote Fall steht in
    `test_acceptance_6_a_second_run_does_not_ask_about_an_ambiguous_word_marked_known`
    (`bank`, zwei Kandidaten)."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    model_server_double.choice = 1

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


def test_acceptance_6_a_second_run_does_not_ask_about_an_ambiguous_word_marked_known(
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
) -> None:
    """Dieselbe Zusicherung wie
    `test_acceptance_6_a_second_run_does_not_ask_about_words_marked_known`, aber an einem
    **mehrdeutigen** Wort: `bank` hat in `mini_dictionary_db` zwei Zeilen (Geldinstitut,
    Ufer, Auftragstext) und steht im Kapiteltext. Dieser Test war gegen den Stand vor der
    zweiten T16-Durchsicht (Befund schwer 1) rot: Der damalige Vorfilter verlangte, dass
    *irgendeine* Bedeutung von `bank` bekannt sei, während „kenne ich" stets nur
    `candidates[0]` bucht (bei `bank` die Geldinstitut-Bedeutung, höchster `score`) — der
    Vorfilter hätte `bank` beim zweiten Durchlauf also fälschlich erneut gezeigt, weil die
    zweite Bedeutung (Ufer) weiterhin als unbekannt galt."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    model_server_double.choice = 1  # erster Listenplatz nach score: Geldinstitut

    first_console = _MarkOneWordKnownConsole(known_word="bank")
    first_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=first_console.read,
        write_line=first_console.write,
    )
    assert first_exit == 0, "\n".join(first_console.log)
    assert any(line.startswith("bank (") for line in first_console.log), (
        "Testvoraussetzung verletzt: 'bank' wurde im ersten Durchlauf gar nicht gefragt."
    )

    second_console = _RejectWordConsole(forbidden_word="bank")
    second_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=second_console.read,
        write_line=second_console.write,
    )
    assert second_exit == 0, "\n".join(second_console.log)


def test_main_names_its_data_directory_on_every_run(tmp_path: Path) -> None:
    """Jeder Lauf nennt sein Datenverzeichnis (technik.md §9, „Wohin die Dateien
    gehören") — wo Profil, Wörterbuch und `config.toml` liegen, soll niemand suchen
    müssen. Geprüft am kürzesten Lauf, dem ersten mit frisch angelegter `config.toml`."""
    written: list[str] = []

    main(
        ["irrelevant.epub", "--data-dir", str(tmp_path)],
        read_line=_no_read,
        write_line=written.append,
    )

    assert any(str(tmp_path) in line and "Datenverzeichnis" in line for line in written), written


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


def test_main_offers_to_fetch_a_missing_dictionary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fehlt das Wörterbuch, wird es bezogen statt auf ein Messskript zu verweisen —
    nach einer Rückfrage, die Herkunft und Lizenz nennt (technik.md §2, „Warum nicht
    mitgeliefert").

    `dictionary.fetch_dictionary` selbst prüft `tests/test_dictionary.py` gegen einen
    örtlichen Server; hier wird nur die Verkettung geprüft (dokumentation.md §5, „Die
    Vorrichtung zeigt Laufen"), deshalb eine Attrappe statt eines 20-MB-Bezugs."""
    data_dir = tmp_path / "data"
    ziel = data_dir / "fehlt.sqlite3"
    _write_config(
        data_dir, model_url="http://localhost:11434/v1", model_name="", dictionary_path=ziel
    )
    bezogen: list[Path] = []

    def _attrappe(path: Path, *, url: str = "") -> None:
        bezogen.append(path)
        path.write_bytes(b"")

    monkeypatch.setattr("cli.main.dictionary.fetch_dictionary", _attrappe)
    written: list[str] = []
    gefragt: list[str] = []

    def _read(prompt: str) -> str:
        gefragt.append(prompt)
        return "j" if "beziehen" in prompt else "n"

    main(
        [str(tmp_path / "fehlt.epub"), "--data-dir", str(data_dir)],
        read_line=_read,
        write_line=written.append,
    )

    assert bezogen == [ziel]
    assert any("wikdict.com" in line for line in written), written
    assert any("BY-SA" in line for line in written), written


def test_main_aborts_when_the_dictionary_fetch_is_declined(tmp_path: Path) -> None:
    """dokumentation.md §4 Regel 13: Lehnt der Nutzer den Bezug ab, bricht der Lauf
    sichtbar ab — kein leerer oder scheinbar erfolgreicher Durchlauf."""
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
        read_line=lambda _prompt: "n",
        write_line=written.append,
    )

    assert exit_code == 1
    assert not (data_dir / "fehlt.sqlite3").exists()
    assert any("Wörterbuch nicht gefunden" in line for line in written)


def test_main_indexes_a_dictionary_that_was_placed_by_hand(
    tmp_path: Path, book_epub: Path, mini_dictionary_db: Path
) -> None:
    """Eine von Hand hinterlegte Wörterbuchdatei bringt die beiden Indizes nicht mit
    (technik.md §3, „Nachtrag 17.08.2026") — der Start legt sie an, sonst kostet jedes
    Kapitel 32 bis 44 s statt 1,1 s, und zwar lautlos.

    Geprüft am Lauf, der an der abgelehnten Profilfrage endet: Der Index muss vorher
    entstanden sein, nicht erst beim ersten Nachschlagen."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )
    with sqlite3.connect(mini_dictionary_db) as vorher:
        assert not _index_names(vorher), "Die Attrappe soll ohne Index in den Test gehen"

    main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=lambda _prompt: "n",
        write_line=lambda _text: None,
    )

    with sqlite3.connect(mini_dictionary_db) as nachher:
        assert _index_names(nachher) == {dictionary.INDEX_NAME, dictionary.INDEX_NAME_NOCASE}


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


def test_full_run_reports_progress_through_cli_display(
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auftragstext vom 25.08.2026, Abschnitt 3: `cli.main` bedient den Fortschritts-
    Rückruf aus `pipeline.resolve_triage_entries` über `cli.display.safe_print_progress`
    und schließt die Zeile mit `finish_progress_line` ab — hier über den vollen
    Einstiegspunkt geprüft, nicht nur isoliert an `cli.main._resolve_with_progress`.

    Verfälschungsprobe: Ruft `_resolve_with_progress` `on_progress` nicht an
    `pipeline.resolve_triage_entries` durch (etwa weil `on_progress=None` bliebe), bliebe
    `progress_calls` leer — dieser Test war daran rot."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    model_server_double.choice = 1
    console = _ScriptedConsole(learn_words={"watch", "gave up"})

    progress_calls: list[str] = []
    finish_calls: list[None] = []
    monkeypatch.setattr(
        "cli.main.safe_print_progress", lambda text, **_kwargs: progress_calls.append(text)
    )
    monkeypatch.setattr(
        "cli.main.finish_progress_line", lambda **_kwargs: finish_calls.append(None)
    )

    exit_code = main(
        [
            str(book_epub),
            "--chapter",
            "1",
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(tmp_path / "export"),
        ],
        read_line=console.read,
        write_line=console.write,
    )

    assert exit_code == 0, "\n".join(console.log)
    assert progress_calls, "Fortschritts-Rückruf wurde nie über cli.display bedient."
    assert all(text.startswith("Bedeutungen werden aufgelöst: ") for text in progress_calls)
    # Befund leicht 4 (Durchsicht T16/T17): der Nenner ist eine Obergrenze, nicht die Zahl
    # der tatsächlich zu prüfenden Einträge — "möglichen" macht das im Text sichtbar.
    assert all("möglichen geprüft" in text for text in progress_calls)
    assert finish_calls, "finish_progress_line wurde nie aufgerufen."


def test_resolve_with_progress_closes_the_line_even_when_the_model_server_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund leicht 1 (Durchsicht T16/46ef37b): Bricht `pipeline.resolve_triage_entries`
    mitten im Kapitel ab, muss `finish_progress_line` trotzdem laufen — sonst klebt die
    Fehlermeldung an der offenen Statuszeile (`…5 von 25 behalten.Fehler: …`).

    Verfälschungsprobe: `finish_progress_line()` hinter statt in `try/finally` aufgerufen
    (der Stand vor dieser Behebung) ließ diesen Test rot werden, weil `finish_calls` dann
    leer blieb — die Ausnahme verließ `_resolve_with_progress`, bevor die Zeile schloss."""
    finish_calls: list[None] = []
    monkeypatch.setattr(
        "cli.main.finish_progress_line", lambda **_kwargs: finish_calls.append(None)
    )
    monkeypatch.setattr("cli.main.safe_print_progress", lambda *_args, **_kwargs: None)

    def _raising_resolve_triage_entries(
        *,
        con: sqlite3.Connection,
        entries: Sequence[pipeline.VocabularyEntry],
        limit: int,
        url: str,
        get_model_name: Callable[[], str],
        order: str,
        on_progress: Callable[[int, int, int, int], None] | None = None,
    ) -> pipeline.TriageResolution:
        assert on_progress is not None
        on_progress(1, 5, 0, limit)
        raise RuntimeError("Modellserver antwortet nicht mehr.")

    monkeypatch.setattr("cli.main.pipeline.resolve_triage_entries", _raising_resolve_triage_entries)

    con = sqlite3.connect(":memory:")
    try:
        with pytest.raises(RuntimeError):
            cli_main._resolve_with_progress(
                con=con,
                entries=[],
                limit=5,
                url="http://127.0.0.1:0/v1",
                get_model_name=lambda: "mini-model",
                order="new_words_first",
            )
    finally:
        con.close()

    assert finish_calls, "finish_progress_line lief nicht, obwohl bereits berichtet wurde."


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
