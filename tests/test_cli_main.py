"""Prüft `cli/main.py` — der vollständige Kapiteldurchlauf (bauplan.md T16).

`test_full_run_learns_a_word_and_an_expression_and_exports_them` ist Abnahmekriterium 3
"in klein": ein echter Durchlauf durch `pipeline.run_chapter`, die Tastatur-Triage und
den Export, an dessen Ende sowohl ein Einzelwort als auch eine Wendung auf der Druckseite
stehen. Die übrigen Tests prüfen die drei genannten Randfälle einzeln und ohne den vollen
Weg über spaCy, damit sie schnell bleiben.
"""

from __future__ import annotations

import enum
import sqlite3
import threading
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cli import display
from cli import main as cli_main
from cli.main import _build_parser, main
from libreverbum import dictionary, epub, pipeline, profile
from libreverbum.entities import Book, CefrLevel

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

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


def _entry_word(pending: list[str]) -> str:
    """Extrahiert die Wortform aus der Kopfzeile eines Triage-Eintrags (Bauschritt 2/2 der
    Konsolenausgabe, 02.09.2026: `cli.interaction._entry_lines`, Format „kompakte
    Kopfzeile") — gesucht wird die Zeile mit dem ASCII-Pfeil, den `display.PLAIN_STYLE`
    liefert (die drei Testkonsolen unten geben diesen Stil über `main(..., style=…)`
    ausdrücklich vor, damit die Form plattformunabhängig feststeht statt vom tatsächlichen
    `sys.stdout` der Testumgebung abzuhängen)."""
    for line in pending:
        stripped = line.strip()
        if "  ->  " in stripped:
            return stripped.split("  ->  ", 1)[0]
    return ""


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


def _read_common_or_triage(
    prompt: str, pending: list[str], *, on_triage: Callable[[list[str]], str]
) -> str:
    """Gemeinsamer Kern der drei Testkonsolen unten (Befund mittel 2, Durchsicht
    ee34796): Erkennt die vier Fragen, die `cli/` heute je Konsole tatsächlich stellt, an
    ihrem Prompt-Wortlaut — die drei generischen (`Neu anlegen`, `Sprachniveau`,
    `Sammelaktion`) hier direkt, die Einzelabfrage der Triage (`[k]enne ich  [l]ernen
    [s]kip  [q]uit`, `cli/interaction.py`) über `on_triage`, dessen Antwort je Konsole
    verschieden ist.

    Vor dieser Behebung lieferte der Rückfallzweig jeder Konsole ungeprüft die
    Triage-Antwort — eine vergessene fünfte Frage (etwa `Kapitel wählen`) bekam damit
    stillschweigend `"l"`/`"k"`/`"s"` statt einer erkennbaren Antwort, und
    `_ask_cefr_level` fragte 200.000-mal erneut, bis ein Prüfer von Hand einen Zähler
    einbaute — ein Hänger, der nicht sagt, was fehlt. Eine unbekannte Frage wirft jetzt
    `AssertionError` mit ihrem eigenen Wortlaut: Ein vollständiger Testlauf wird dann rot
    statt endlos zu warten.

    Verfälschungsprobe: Fehlte der `raise` am Ende (Rückfall auf `on_triage` wie zuvor),
    hinge eine Konsole ohne `Sprachniveau`-Zweig wieder endlos an `_ask_cefr_level` —
    genau das hat der Test unten (`test_a_console_without_a_branch_…_raises_instead_of_
    hanging`) vor der Behebung nachgewiesen (200.000 Wiederholungen, dann Abbruch von
    Hand statt eines roten Tests)."""
    if "Neu anlegen" in prompt:
        pending.clear()
        return "j"
    if "Sprachniveau" in prompt:
        # Bauschritt 4/5 der Vorbelegung (31.08.2026): diese Konsolen prüfen die Triage,
        # nicht die Niveaufrage — „keine Angabe" hält das Profil leer, wie vor deren
        # Einführung, und lässt die übrige Prüfvorrichtung unverändert.
        pending.clear()
        return "keine angabe"
    if "Sammelaktion" in prompt:
        pending.clear()
        return ""
    if "[k]enne ich" in prompt:
        return on_triage(pending)
    raise AssertionError(f"unerwartete Frage: {prompt!r}")


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
        def _on_triage(pending: list[str]) -> str:
            word = _entry_word(pending)
            pending.clear()
            return "l" if word in self._learn_words else "s"

        return _read_common_or_triage(prompt, self._pending, on_triage=_on_triage)


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
        def _on_triage(pending: list[str]) -> str:
            word = _entry_word(pending)
            pending.clear()
            return "k" if word == self._known_word else "s"

        return _read_common_or_triage(prompt, self._pending, on_triage=_on_triage)


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
        if text.strip().startswith(f"{self._forbidden_word}  ->"):
            raise AssertionError(
                f"{self._forbidden_word!r} wurde im zweiten Durchlauf erneut angezeigt — "
                "das Profil greift nicht (Abnahmekriterium 6)."
            )
        self._pending.append(text)

    def read(self, prompt: str) -> str:
        def _on_triage(pending: list[str]) -> str:
            pending.clear()
            return "s"

        return _read_common_or_triage(prompt, self._pending, on_triage=_on_triage)


def test_a_console_without_a_branch_for_an_unknown_prompt_raises_instead_of_hanging() -> None:
    """Befund mittel 2 (Durchsicht ee34796): Eine Frage, die keine der drei Konsolen
    kennt, wirft `AssertionError` mit dem Wortlaut der Frage, statt eine geratene Antwort
    zu liefern. Vor dieser Behebung lieferte der Rückfallzweig ungeprüft die
    Triage-Antwort — eine vergessene fünfte Frage bekam damit still `"l"`/`"k"`/`"s"`
    statt einer erkennbaren Antwort; an `_ask_cefr_level` ohne den `Sprachniveau`-Zweig
    fragte das 200.000-mal erneut, bis ein Prüfer von Hand einen Zähler einbaute, statt
    dass ein Testlauf rot wurde.

    Verfälschungsprobe: Ersetzt man den `raise` am Ende von `_read_common_or_triage`
    durch `return on_triage(pending)` (der Stand vor dieser Behebung), liefert der Aufruf
    unten `"s"` statt einer Ausnahme — dieser Test war daran rot, siehe Bericht."""
    with pytest.raises(AssertionError, match="Kapitel wählen"):
        _read_common_or_triage("Kapitel wählen: ", [], on_triage=lambda _pending: "s")


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
        style=display.PLAIN_STYLE,
    )
    assert first_exit == 0, "\n".join(first_console.log)
    assert any(line.strip().startswith("watch  ->") for line in first_console.log), (
        "Testvoraussetzung verletzt: 'watch' wurde im ersten Durchlauf gar nicht gefragt."
    )

    second_console = _RejectWordConsole(forbidden_word="watch")
    second_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=second_console.read,
        write_line=second_console.write,
        style=display.PLAIN_STYLE,
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
        style=display.PLAIN_STYLE,
    )
    assert first_exit == 0, "\n".join(first_console.log)
    assert any(line.strip().startswith("bank  ->") for line in first_console.log), (
        "Testvoraussetzung verletzt: 'bank' wurde im ersten Durchlauf gar nicht gefragt."
    )

    second_console = _RejectWordConsole(forbidden_word="bank")
    second_exit = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=second_console.read,
        write_line=second_console.write,
        style=display.PLAIN_STYLE,
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


# ------------------------------- Niveaufrage bei der Vorbelegung (Bauschritt 4/5, 31.08.2026)
#
# `_ask_cefr_level` fragt beim Anlegen eines neuen Profils nach dem Sprachniveau für die
# einmalige Vorbelegung des Grundwortschatzes (konzept.md, „Bewusst offen", „Woher der
# Nutzer seinen Grundwortschatz bekommt"). Die ersten beiden Tests unten nageln die
# Hauptanforderung des Auftrags fest: Weder eine leere noch eine ungültige Eingabe wählt
# stillschweigend eine Stufe oder überspringt die Frage — genau das hat den Triage-Prompt
# schon zwei Abnahmeläufe gekostet (technik.md §9, „Offene Punkte"). `_confirm_new_profile`
# bekommt hier außerdem den eigenen Test, den es bislang nur beiläufig hatte.


def test_confirm_new_profile_returns_true_without_asking_for_an_existing_file(
    tmp_path: Path,
) -> None:
    """Bei einer vorhandenen Profildatei liefert `_confirm_new_profile` `True`, ohne
    `read_line` überhaupt aufzurufen — `_no_read` ließe den Test scheitern, würde doch
    gefragt."""
    profile_path = tmp_path / "profil.sqlite3"
    profile_path.write_bytes(b"")

    assert cli_main._confirm_new_profile(profile_path, _no_read, lambda _text: None) is True


def test_confirm_new_profile_declines_on_empty_or_other_input(tmp_path: Path) -> None:
    """Vorgabe bei bloßem Enter ist Ablehnung, nicht Zustimmung (Docstring von
    `_confirm_new_profile`) — hier direkt geprüft, nicht nur beiläufig über einen vollen
    Lauf wie in `test_main_declines_to_create_a_profile_without_confirmation`."""
    profile_path = tmp_path / "profil.sqlite3"

    assert (
        cli_main._confirm_new_profile(profile_path, lambda _prompt: "", lambda _text: None) is False
    )
    assert (
        cli_main._confirm_new_profile(profile_path, lambda _prompt: "nein", lambda _text: None)
        is False
    )


def test_confirm_new_profile_confirms_on_j_or_ja(tmp_path: Path) -> None:
    profile_path = tmp_path / "profil.sqlite3"

    assert (
        cli_main._confirm_new_profile(profile_path, lambda _prompt: "j", lambda _text: None) is True
    )
    assert (
        cli_main._confirm_new_profile(profile_path, lambda _prompt: "ja", lambda _text: None)
        is True
    )


def test_ask_cefr_level_asks_again_on_empty_input_instead_of_choosing_a_level() -> None:
    """Die Hauptanforderung des Auftrags: Eine Leereingabe wählt keine Stufe, sondern
    fragt erneut — genau die Falle, an der der Triage-Prompt (technik.md §9, „Offene
    Punkte") schon zwei Abnahmeläufe verloren hat, darf hier nicht entstehen.

    Verfälschungsprobe: Verhielte sich eine Leereingabe wie „keine Angabe" (`answer in
    ("", "keine angabe", "keine")` statt nur der beiden Wortformen), läse der zweite
    Eintrag des Antwortiterators nie — der Test bliebe grün, weil `next(answers)` gar
    nicht ein zweites Mal aufgerufen würde und `level` trotzdem `None` wäre. Erst die
    zusätzliche Zusicherung auf die Meldung „Ungültige Eingabe" macht die Probe scharf;
    ohne sie wäre der Test bei dieser Verfälschung fälschlich grün geblieben."""
    written: list[str] = []
    answers = iter(["", "keine angabe"])

    level = cli_main._ask_cefr_level(lambda _prompt: next(answers), written.append)

    assert level is None
    assert any("Ungültige Eingabe" in line for line in written)


def test_ask_cefr_level_asks_again_on_invalid_input_instead_of_skipping_the_question() -> None:
    """Eine vertippte Antwort (»B7«, »x«, »8L«) wählt weder eine Stufe noch überspringt
    sie die Frage — sie fragt erneut, wie `cli.interaction._ask_action` es bei der Triage
    vormacht. Drei Fehlversuche, dann eine gültige Stufe."""
    written: list[str] = []
    answers = iter(["B7", "x", "8L", "b1"])

    level = cli_main._ask_cefr_level(lambda _prompt: next(answers), written.append)

    assert level == CefrLevel.B1
    assert sum(1 for line in written if "Ungültige Eingabe" in line) == 3


def test_ask_cefr_level_explicit_no_answer_returns_none() -> None:
    """„Keine Angabe" muss ausdrücklich eingegeben werden — hier direkt geprüft, nicht
    nur über den vollen Lauf."""
    answers = iter(["keine Angabe"])

    level = cli_main._ask_cefr_level(lambda _prompt: next(answers), lambda _text: None)

    assert level is None


def _ask_cefr_level_with_single_answer(answer: str) -> CefrLevel | None:
    """Eigene Funktion statt eines Lambdas in der Schleife unten (Ruff B023): `answers`
    wäre sonst eine Schleifenvariable, die der Lambda-Ausdruck nicht bindet — hier ist
    sie in jedem Aufruf eine frische, lokale Variable."""
    answers = iter([answer])
    return cli_main._ask_cefr_level(lambda _prompt: next(answers), lambda _text: None)


def test_ask_cefr_level_accepts_each_level_case_insensitively() -> None:
    for expected in CefrLevel:
        assert _ask_cefr_level_with_single_answer(expected.value.upper()) == expected


def test_ask_cefr_level_prompt_and_error_message_are_built_from_cefr_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund leicht b (Durchsicht ee34796): Sowohl die Stufenliste im Prompt als auch in
    der Fehlermeldung bauen sich aus `CefrLevel` auf, statt von Hand gepflegt zu sein —
    käme `C2` hinzu oder fiele eine Stufe weg, zeigte eine von Hand geschriebene
    Aufzählung sonst still eine falsche Auswahl, und kein Test bemerkte es.

    Geprüft mit einer testweise verkürzten Aufzählung: Ein hartkodiertes
    „A1/A2/B1/B2/C1"/„A1, A2, B1, B2, C1" (die frühere Fassung, die zufällig mit der
    echten Aufzählung übereinstimmt und diesen Test sonst nicht von einer echten
    Ableitung unterscheiden könnte) bestünde diesen Test nicht — er war daran rot, siehe
    Bericht."""

    class _ShortLevel(enum.Enum):
        A1 = "a1"
        B1 = "b1"

    monkeypatch.setattr(cli_main, "CefrLevel", _ShortLevel)
    monkeypatch.setattr(pipeline, "PRESET_WORD_COUNT", {_ShortLevel.A1: 10, _ShortLevel.B1: 20})
    prompts: list[str] = []
    written: list[str] = []
    answers = iter(["falsch", "a1"])

    def _read(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    level = cli_main._ask_cefr_level(_read, written.append)

    # level ist zur Laufzeit ein _ShortLevel-Mitglied, statisch bleibt die Signatur bei
    # `CefrLevel | None` — über .value verglichen, damit mypy hier keinen unerreichbaren
    # Identitätsvergleich zwischen zwei unverwandten Aufzählungen meldet.
    assert level is not None
    assert level.value == "a1"
    assert prompts == ["Sprachniveau [A1/B1] oder 'keine Angabe': "] * 2
    assert any(
        line == "Ungültige Eingabe - A1, B1 oder 'keine Angabe' erwartet." for line in written
    )


def test_apply_vocabulary_preset_with_no_answer_writes_and_reports_nothing(
    tmp_path: Path, mini_dictionary_db: Path
) -> None:
    """„Keine Angabe" schreibt keine Ereignisse und setzt kein Niveau (Auftragstext) — mit
    dem echten `pipeline.write_vocabulary_preset` über `_apply_vocabulary_preset`, der
    Verkettung aus Frage und Schreiben. `write_vocabulary_preset` öffnet die Profildatei
    bei „keine Angabe" nicht einmal (`tests/test_pipeline.py`,
    `test_write_vocabulary_preset_with_no_answer_writes_nothing`) — dieselbe Zusicherung
    hier über den Aufruf aus `cli.main`."""
    profile_path = tmp_path / "profil.sqlite3"
    written: list[str] = []
    answers = iter(["keine angabe"])

    cli_main._apply_vocabulary_preset(
        dictionary_path=mini_dictionary_db,
        profile_path=profile_path,
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert not profile_path.exists()
    assert not any("gebucht" in line for line in written)


def test_apply_vocabulary_preset_calls_write_vocabulary_preset_with_the_chosen_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine gewählte Stufe ruft `pipeline.write_vocabulary_preset` mit genau dieser Stufe
    auf — eine Attrappe an Stelle des echten Nachschlagens hält den Test unabhängig vom
    Wörterbuchinhalt.

    (Befund mittel 4, Durchsicht ee34796): Die frühere Zusicherung
    (`any("3" in line and "4" in line for line in written)`) prüfte nur, dass irgendwo
    eine 3 und eine 4 auftauchen — vertauscht man `result.lemma_pos_pairs` und
    `result.senses` in der Meldung, bleibt sie unbemerkt grün. Geprüft wird deshalb der
    zusammenhängende Wortlaut mit Einheit, dazu die neuen Felder aus `PresetResult`
    (Befund leicht c) und der Hinweis auf die Einmaligkeit (Befund leicht d)."""
    calls: list[CefrLevel | None] = []

    def _stub(
        *,
        dictionary_path: Path,
        profile_path: Path,
        cefr_level: CefrLevel | None,
        timestamp: object,
    ) -> pipeline.PresetResult:
        calls.append(cefr_level)
        return pipeline.PresetResult(lemma_pos_pairs=3, senses=4, covered_lemmas=2, total_lemmas=5)

    monkeypatch.setattr("cli.main.pipeline.write_vocabulary_preset", _stub)
    written: list[str] = []
    answers = iter(["b2"])

    cli_main._apply_vocabulary_preset(
        dictionary_path=tmp_path / "en-de.sqlite3",
        profile_path=tmp_path / "profil.sqlite3",
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert calls == [CefrLevel.B2]
    assert any(
        "3 (Grundform, Wortart)-Paare" in line and "4 Bedeutungen" in line for line in written
    )
    assert any("2 von 5 Grundformen" in line for line in written)
    # (Befund leicht d, Durchsicht ee34796): Nicht nur auf „einmalig" prüfen — das Wort
    # steht schon in der Einleitung von `_ask_cefr_level` (Zeile „… einmalig
    # vorbelegen:"), eine schwächere Zusicherung wäre also selbst dann grün, wenn der
    # eigentliche Hinweis am Ende der Meldung fehlte.
    assert "Die Vorbelegung ist einmalig und lässt sich nicht zurücknehmen." in written


def test_apply_vocabulary_preset_removes_a_newly_created_profile_file_when_the_preset_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund mittel 1 (Durchsicht ee34796): `pipeline.write_vocabulary_preset` legt die
    Profildatei über `profile.open_profile` **vor** dem eigentlichen Schreiben an —
    `profile.record_preset` ist nur für die Ereignisse atomar, nicht für die Datei.
    Scheitert der Aufruf danach, blieb bislang eine leere, aber existierende Profildatei
    zurück, und `_run` fragt beim nächsten Lauf nicht mehr nach, weil es allein die
    Dateiexistenz prüft (`profile_is_new = not cfg.profile_path.is_file()`). Die Attrappe
    hier bildet genau dieses Verhalten nach: Sie legt die Datei an, bevor sie fehlschlägt.

    Verfälschungsprobe: Ohne die Bereinigung (kein `try`/`except` um den Aufruf in
    `_apply_vocabulary_preset`) bliebe die Attrappen-Datei nach dem Fehlschlag bestehen —
    dieser Test war daran rot, siehe Bericht."""
    profile_path = tmp_path / "profil.sqlite3"

    def _failing_but_creates_the_file(
        *, profile_path: Path, **_kwargs: object
    ) -> pipeline.PresetResult:
        profile_path.write_bytes(b"")
        raise ValueError("Profil ließ sich nicht schreiben (Attrappe für diesen Test).")

    monkeypatch.setattr("cli.main.pipeline.write_vocabulary_preset", _failing_but_creates_the_file)
    answers = iter(["a1"])

    with pytest.raises(ValueError, match="Profil ließ sich nicht schreiben"):
        cli_main._apply_vocabulary_preset(
            dictionary_path=tmp_path / "en-de.sqlite3",
            profile_path=profile_path,
            read_line=lambda _prompt: next(answers),
            write_line=lambda _text: None,
        )

    assert not profile_path.exists()


def test_apply_vocabulary_preset_keeps_a_pre_existing_profile_file_when_the_preset_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ergänzung zum vorigen Test: Existierte die Profildatei schon **vor** diesem
    Aufruf, räumt ein Fehlschlag sie nicht weg — gelöscht wird nur, was dieser Aufruf
    selbst angelegt hat (Befund mittel 1, Durchsicht ee34796, „Sei beim Löschen
    vorsichtig")."""
    profile_path = tmp_path / "profil.sqlite3"
    profile_path.write_bytes(b"vorhandener Inhalt")

    def _failing(**_kwargs: object) -> pipeline.PresetResult:
        raise ValueError("Profil ließ sich nicht schreiben (Attrappe für diesen Test).")

    monkeypatch.setattr("cli.main.pipeline.write_vocabulary_preset", _failing)
    answers = iter(["a1"])

    with pytest.raises(ValueError, match="Profil ließ sich nicht schreiben"):
        cli_main._apply_vocabulary_preset(
            dictionary_path=tmp_path / "en-de.sqlite3",
            profile_path=profile_path,
            read_line=lambda _prompt: next(answers),
            write_line=lambda _text: None,
        )

    assert profile_path.read_bytes() == b"vorhandener Inhalt"


def test_main_does_not_ask_for_a_cefr_level_when_the_profile_already_exists(
    tmp_path: Path, mini_dictionary_db: Path
) -> None:
    """Bei einem vorhandenen Profil wird die Niveaufrage nicht gestellt — anders als beim
    Anlegen. `_no_read` lässt den Lauf an der ersten Frage scheitern; da Wörterbuch und
    Profil schon bereitstehen, bricht der Lauf stattdessen erst an der (absichtlich
    ungültigen) EPUB-Datei ab, ohne dass `read_line` je aufgerufen wurde."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )
    profile.open_profile(data_dir / "profil.sqlite3").close()

    exit_code = main(
        [str(tmp_path / "fehlt.epub"), "--data-dir", str(data_dir)],
        read_line=_no_read,
        write_line=lambda _text: None,
    )

    assert exit_code == 1


def test_main_returns_a_nonzero_exit_code_when_the_preset_fails(
    tmp_path: Path, mini_dictionary_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regel 13: Scheitert die Vorbelegung, bricht der Lauf sichtbar ab, statt den Fehler
    nur zu protokollieren und weiterzulaufen — kein `except` in `_apply_vocabulary_preset`
    fängt ihn ab und schluckt ihn, er läuft bis zu `main`s eigenem Fang durch.

    (Befund mittel 3, Durchsicht ee34796): Die beiden früheren Zusicherungen
    (`exit_code != 0`, `"Fehler" in line`) waren erfüllt, gleichgültig ob die Vorbelegung
    überhaupt aufgerufen wurde oder ob ihr Fehlschlag stillschweigend geschluckt wurde —
    der Lauf endet ohnehin an der nicht existierenden EPUB-Datei
    (`tmp_path / "irrelevant.epub"`). Weder `if profile_is_new:` durch `if False:` ersetzt
    (Vorbelegung nie aufgerufen) noch `write_vocabulary_preset` in ein schluckendes
    `try/except Exception: pass` gehüllt hätte diesen Test damals rot werden lassen. Die
    Attrappe zählt ihre Aufrufe jetzt selbst mit, und geprüft wird ihr eigener Wortlaut,
    nicht nur das Wort „Fehler"."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )
    calls: list[CefrLevel | None] = []

    def _failing_preset(
        *, cefr_level: CefrLevel | None, **_kwargs: object
    ) -> pipeline.PresetResult:
        calls.append(cefr_level)
        raise ValueError("Profil ließ sich nicht schreiben (Attrappe für diesen Test).")

    monkeypatch.setattr("cli.main.pipeline.write_vocabulary_preset", _failing_preset)
    written: list[str] = []
    answers = iter(["j", "a1"])

    exit_code = main(
        [str(tmp_path / "irrelevant.epub"), "--data-dir", str(data_dir)],
        read_line=lambda _prompt: next(answers),
        write_line=written.append,
    )

    assert exit_code != 0
    assert calls == [CefrLevel.A1]
    assert any(
        "Profil ließ sich nicht schreiben (Attrappe für diesen Test)." in line for line in written
    )


def test_main_calls_write_vocabulary_preset_with_the_answered_level_on_a_new_profile(
    tmp_path: Path, mini_dictionary_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gegenstück zu `test_main_does_not_ask_for_a_cefr_level_when_the_profile_already_exists`,
    das bislang nur die Nein-Hälfte festnagelte (Befund mittel 3, Durchsicht ee34796,
    dritter Teil): Bei einem **neuen** Profil ruft `main` `pipeline.write_vocabulary_preset`
    tatsächlich mit der geantworteten Stufe auf.

    Verfälschungsprobe: Ersetzt man `if profile_is_new:` in `cli/main.py` durch
    `if False:`, bleibt `calls` leer — dieser Test war daran rot, siehe Bericht."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )
    calls: list[CefrLevel | None] = []

    def _stub(
        *,
        dictionary_path: Path,
        profile_path: Path,
        cefr_level: CefrLevel | None,
        timestamp: object,
    ) -> pipeline.PresetResult:
        calls.append(cefr_level)
        return pipeline.PresetResult(lemma_pos_pairs=0, senses=0, covered_lemmas=0, total_lemmas=0)

    monkeypatch.setattr("cli.main.pipeline.write_vocabulary_preset", _stub)
    answers = iter(["j", "c1"])

    exit_code = main(
        [str(tmp_path / "fehlt.epub"), "--data-dir", str(data_dir)],
        read_line=lambda _prompt: next(answers),
        write_line=lambda _text: None,
    )

    assert exit_code == 1
    assert calls == [CefrLevel.C1]


def test_main_reports_eof_in_german_instead_of_a_raw_traceback(
    tmp_path: Path, mini_dictionary_db: Path
) -> None:
    """Befund leicht a (Durchsicht ee34796): Eine abgeschnittene Eingabe (Pipe-Ende,
    umgeleitetes `/dev/null`) lässt `read_line` `EOFError` werfen — für jede der fünf
    Rückfragen aus `cli/`, hier an der ersten geprüft (`_confirm_new_profile`). Vor dieser
    Behebung lief das bis zu einem nackten, achtzeiligen englischen Traceback durch: Regel
    13 (sichtbarer Abbruch) war erfüllt, die Sprachregel (dokumentation.md §1) nicht."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="",
        dictionary_path=mini_dictionary_db,
    )
    written: list[str] = []

    def _eof(_prompt: str) -> str:
        raise EOFError

    exit_code = main(
        ["irrelevant.epub", "--data-dir", str(data_dir)], read_line=_eof, write_line=written.append
    )

    assert exit_code == 1
    assert written[-1] == "Abgebrochen — keine Eingabe mehr."


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
        style=display.PLAIN_STYLE,
    )

    assert exit_code == 0, "\n".join(console.log)
    # Die geschriebenen Dateien werden im Verzeichnis gesucht, nicht über einen zweiten
    # `export_paths`-Aufruf: Der liefert seit dem 27.08.2026 den nächsten **freien**
    # Namen und damit gerade nicht die eben geschriebenen Dateien (`cli/export.py`).
    decks = sorted(output_dir.glob("*.apkg"))
    printouts = sorted(output_dir.glob("*.html"))
    assert [pfad.name for pfad in decks] == ["CLI-Testbuch_kapitel1.apkg"]
    assert [pfad.name for pfad in printouts] == ["CLI-Testbuch_kapitel1.html"]

    html = printouts[0].read_text(encoding="utf-8")
    assert "watch" in html
    assert "gave up" in html


def test_full_run_uses_the_cover_banner_for_both_decks(
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
) -> None:
    """Bauschritt 2/2 der Konsolenausgabe (02.09.2026): `== Wörter ==`/`== Wendungen ==`
    sind durch das Deckel-Banner aus `cli.display.cover` ersetzt — geprüft am vollen
    Einstiegspunkt, für beide Decksel.

    Verfälschungsprobe: `display.cover(...)` durch die alte Zeile
    `write_line(f"== {label} ==")` ersetzt ließ diesen Test rot werden — die neue
    Bannerzeile fehlte, die alte Markerzeile stand wieder da."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    model_server_double.choice = 1
    console = _ScriptedConsole(learn_words=set())

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
        style=display.PLAIN_STYLE,
    )

    assert exit_code == 0, "\n".join(console.log)
    assert "  Wörter" in console.log
    assert "  Wendungen" in console.log
    assert not any(line == "== Wörter ==" for line in console.log)
    assert not any(line == "== Wendungen ==" for line in console.log)


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
        style=display.PLAIN_STYLE,
    )

    assert exit_code == 0, "\n".join(console.log)
    assert progress_calls, "Fortschritts-Rückruf wurde nie über cli.display bedient."
    # Seit Bauschritt 1/2 der Konsolenausgabe (02.09.2026) meldet auch
    # `_run_chapter_with_progress` über dieselbe Funktion — die beiden zählenden Phasen aus
    # `pipeline.run_chapter` stehen deshalb neben den resolve_triage_entries-Zeilen, statt
    # sie allein zu füllen.
    resolve_calls = [
        text for text in progress_calls if text.startswith("Bedeutungen werden aufgelöst: ")
    ]
    chapter_calls = [
        text
        for text in progress_calls
        if text.startswith(("Buch wird gelesen:", "Wortschatz des Buchs wird analysiert:"))
    ]
    assert resolve_calls, "Fortschritts-Rückruf aus resolve_triage_entries wurde nie bedient."
    assert chapter_calls, "Fortschritts-Rückruf aus run_chapter wurde nie bedient."
    assert len(resolve_calls) + len(chapter_calls) == len(progress_calls)
    # Befund leicht 4 (Durchsicht T16/T17): der Nenner ist eine Obergrenze, nicht die Zahl
    # der tatsächlich zu prüfenden Einträge — "möglichen" macht das im Text sichtbar.
    assert all("möglichen geprüft" in text for text in resolve_calls)
    assert finish_calls, "finish_progress_line wurde nie aufgerufen."


def test_full_run_prints_at_least_one_line_naming_the_running_analysis_before_triage(
    tmp_path: Path,
    book_epub: Path,
    mini_dictionary_db: Path,
    model_server_double: ModelServerDouble,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Die ursprüngliche Beschwerde (Auftragstext vom 02.09.2026): Auf dem Bildschirm stand
    „Lade Sprachmodell …", während `pipeline.run_chapter` tatsächlich 22 bis 29 s lang
    stumm das ganze Buch analysierte (`extraction.book_proper_noun_ratios`, technik.md
    §5/§13) — der stille Fehlschlag aus Regel 13. Hier über den vollen Einstiegspunkt
    geprüft: Zwischen der Zeile „Sprachmodell geladen." und dem Beginn der Wörter-Triage
    (dem Deckel-Banner aus `cli.display.cover`, seit Bauschritt 2/2 der Konsolenausgabe an
    die Stelle von „== Wörter ==" getreten) steht mindestens eine Zeile, die die laufende
    Analyse benennt.

    `safe_print_progress` wird — anders als in
    `test_full_run_reports_progress_through_cli_display` — auf dieselbe Konsole umgeleitet
    wie `write_line`, damit die sich fortschreibenden Phasenzeilen in der tatsächlichen
    Aufrufreihenfolge im Log erscheinen; `learn_words` bleibt leer, weil die
    Triage-Antworten hier nicht geprüft werden.

    Verfälschungsprobe: `on_progress=None` fest an den `pipeline.run_chapter`-Aufruf in
    `_run_chapter_with_progress` übergeben (statt `_on_progress`) ließ diesen Test zunächst
    nicht rot werden — die neue Abschlusszeile „Kapitel N: … Wörter, … Wendungen." steht
    ebenfalls zwischen den beiden geprüften Zeilen und füllte `between`. Erst die
    Stichwortprüfung unten, die gezielt nach einer Phasenzeile sucht, wurde bei derselben
    Verfälschung rot — `analysis_lines` blieb dann leer."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url=model_server_double.url,
        model_name=model_server_double.model_name,
        dictionary_path=mini_dictionary_db,
    )
    model_server_double.choice = 1
    console = _ScriptedConsole(learn_words=set())

    monkeypatch.setattr("cli.main.safe_print_progress", lambda text, **_kwargs: console.write(text))
    monkeypatch.setattr("cli.main.finish_progress_line", lambda **_kwargs: None)

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
        style=display.PLAIN_STYLE,
    )

    assert exit_code == 0, "\n".join(console.log)
    loaded_index = console.log.index("Sprachmodell geladen.")
    triage_index = console.log.index("  Wörter")  # Deckel-Banner, cli.display.cover
    between = console.log[loaded_index + 1 : triage_index]
    # Stichwörter der vier Phasen aus `_run_chapter_with_progress` — nicht bloß irgendeine
    # Zeile: Die Abschlusszeile „Kapitel N: … Wörter, … Wendungen." steht ebenfalls in
    # `between`, sagt aber nichts über die *laufende* Analyse (siehe Verfälschungsprobe).
    analysis_lines = [
        line
        for line in between
        if any(
            keyword in line
            for keyword in ("wird gelesen", "wird analysiert", "wird ermittelt", "nachgeschlagen")
        )
    ]
    assert analysis_lines, (
        "Zwischen Modell-Laden und Triage fehlt eine Zeile zur laufenden Analyse."
    )


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


def test_choose_chapter_shows_the_title_first_then_the_word_count_with_unknown_as_such(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 3b (Durchsicht 29715b2): technik.md §8, Nachtrag 28.08.2026, „Was die
    Kapitelliste zusätzlich zeigt" nennt die Zeile als „Book 1 DUNE — 78.800 Wörter" — der
    Titel steht vor der Zahl, nicht danach. Die Kapitelliste zeigt den Umfang je Kapitel
    mit deutschem Tausendertrennzeichen (`78.774`) und einen unbekannten Umfang sichtbar als
    solchen, nicht als Zahl (Regel 13)."""
    structure = epub.BookStructure(
        book=Book(title="Testbuch", author="Testautorin"),
        chapters=[
            epub.ChapterReference(number=1, title="Book 1 DUNE", documents=["a.xhtml"]),
            epub.ChapterReference(
                number=2, title="Kapitel ohne lesbares Dokument", documents=["b.xhtml"]
            ),
        ],
        notice=None,
    )
    monkeypatch.setattr(
        "cli.main.epub.count_chapter_words", lambda _path, _chapters: {1: 78774, 2: None}
    )
    written: list[str] = []

    cli_main._choose_chapter(Path("buch.epub"), structure, lambda _prompt: "1", written.append)

    listing = [line for line in written if "Book 1 DUNE" in line or "lesbares Dokument" in line]
    assert len(listing) == 2
    first_chapter_line, second_chapter_line = listing
    assert first_chapter_line.index("Book 1 DUNE") < first_chapter_line.index("78.774")
    assert "78774" not in first_chapter_line
    assert second_chapter_line.index("Kapitel ohne lesbares Dokument") < second_chapter_line.index(
        "unbekannt"
    )


def test_choose_chapter_aligns_the_word_count_column_from_chapter_ten_onward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Befund 3 (Durchsicht 29715b2): `chapter.number` wurde nicht aufgefüllt — ab Kapitel
    10 rutschte die ganze Wortspalte um ein Zeichen nach rechts, für jedes Buch mit zehn
    oder mehr Kapiteln (beide echten Bücher). Geprüft an zehn Kapiteln mit unterschiedlich
    langen Titeln und unterschiedlich vielen Ziffern im Umfang: Nummer-, Titel- und
    Zahlenspalte müssen für jede Zeile an derselben Stelle stehen."""
    titles = {
        1: "Kurz",
        9: "Ein deutlich längerer Kapiteltitel als die übrigen",
        10: "IX. THE ADVENTURE OF THE ENGINEER’S THUMB",
    }
    chapters = [
        epub.ChapterReference(
            number=number, title=titles.get(number, f"Kapitel {number}"), documents=["x.xhtml"]
        )
        for number in range(1, 11)
    ]
    structure = epub.BookStructure(
        book=Book(title="Testbuch", author="Testautorin"), chapters=chapters, notice=None
    )
    counts = {1: 97, 9: 9865, 10: 8327, **{number: number * 111 for number in range(2, 9)}}
    monkeypatch.setattr("cli.main.epub.count_chapter_words", lambda _path, _chapters: counts)
    written: list[str] = []

    cli_main._choose_chapter(Path("buch.epub"), structure, lambda _prompt: "1", written.append)

    table = written[1:]  # ohne die Buchzeile: Kopfzeile, dann zehn Kapitelzeilen
    assert len(table) == 11

    formatted = {number: cli_main._format_word_count(count) for number, count in counts.items()}
    number_width = max([len("Nr.")] + [len(f"{chapter.number}.") for chapter in chapters])
    title_width = max([len("Kapitel")] + [len(chapter.title) for chapter in chapters])
    count_width = max([len("Wörter")] + [len(value) for value in formatted.values()])
    assert {len(line) for line in table} == {2 + number_width + 2 + title_width + 2 + count_width}

    header = table[0]
    assert header[2 : 2 + number_width] == "Nr.".rjust(number_width)
    title_start = 2 + number_width + 2
    assert header[title_start : title_start + title_width] == "Kapitel".ljust(title_width)
    assert header[-count_width:] == "Wörter".rjust(count_width)

    for chapter, line in zip(chapters, table[1:], strict=True):
        assert line[2 : 2 + number_width] == f"{chapter.number}.".rjust(number_width)
        assert line[title_start : title_start + title_width] == chapter.title.ljust(title_width)
        assert line[-count_width:] == formatted[chapter.number].rjust(count_width)


def test_choose_chapter_indents_the_title_by_navigation_level_and_keeps_the_word_count_aligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auftrag Teilaufgabe 3, Punkt 6: Der Titel wird je Ebene eingerückt (zwei
    Leerzeichen, fest — Regel 14: kein Konfigurationsschalter) — die Einrückung zählt zur
    Breite der Titelspalte, damit die Spalte „Wörter" bei eingerückten Zeilen ausgerichtet
    bleibt (technik.md §8, Nachtrag 28.08.2026, „Was die Kapitelliste zusätzlich
    zeigt")."""
    chapters = [
        epub.ChapterReference(number=1, title="Teil I", documents=["a.xhtml"], level=0),
        epub.ChapterReference(
            number=2, title="Ein deutlich längeres Kapitel", documents=["b.xhtml"], level=1
        ),
        epub.ChapterReference(number=3, title="Kapitel 2", documents=["c.xhtml"], level=1),
        epub.ChapterReference(number=4, title="Teil II", documents=["d.xhtml"], level=0),
        epub.ChapterReference(number=5, title="Kapitel 3", documents=["e.xhtml"], level=1),
    ]
    structure = epub.BookStructure(
        book=Book(title="Testbuch", author="Testautorin"), chapters=chapters, notice=None
    )
    counts = {1: 500, 2: 1234, 3: 60, 4: 700, 5: 9}
    monkeypatch.setattr("cli.main.epub.count_chapter_words", lambda _path, _chapters: counts)
    written: list[str] = []

    cli_main._choose_chapter(Path("buch.epub"), structure, lambda _prompt: "1", written.append)

    table = written[1:]  # ohne die Buchzeile: Kopfzeile, dann fünf Kapitelzeilen
    assert len(table) == 6

    indented_titles = {
        chapter.number: f"{'  ' * chapter.level}{chapter.title}" for chapter in chapters
    }
    formatted = {number: cli_main._format_word_count(count) for number, count in counts.items()}
    number_width = max([len("Nr.")] + [len(f"{chapter.number}.") for chapter in chapters])
    title_width = max([len("Kapitel")] + [len(value) for value in indented_titles.values()])
    count_width = max([len("Wörter")] + [len(value) for value in formatted.values()])
    assert {len(line) for line in table} == {2 + number_width + 2 + title_width + 2 + count_width}

    title_start = 2 + number_width + 2
    for chapter, line in zip(chapters, table[1:], strict=True):
        assert line[title_start : title_start + title_width] == indented_titles[
            chapter.number
        ].ljust(title_width)
        assert line[-count_width:] == formatted[chapter.number].rjust(count_width)
        if chapter.level > 0:
            # Die Einrückung ist tatsächlich sichtbar — nicht nur rechnerisch Teil der
            # Spaltenbreite: Die ersten zwei Zeichen der Titelspalte sind Leerraum, und
            # der Titel selbst steht noch in der Zeile.
            assert line[title_start : title_start + 2] == "  "
            assert chapter.title in line


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


def test_prefetch_resolves_the_background_block_with_a_connection_of_its_own(
    tmp_path: Path, book_epub: Path, mini_dictionary_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund mittel 2 (Durchsicht 1cfb1e4, technik.md §12 Festlegung 1): Der stille
    Rückruf für den vorgeladenen Block (`cli.main._resolve_silently`) öffnet im
    Hintergrundfaden **seine eigene** Profilverbindung, statt die des Hauptfadens
    weiterzuverwenden. Eine geteilte Verbindung wäre im echten Betrieb kein
    Geschwindigkeitsproblem, sondern der in `sqlite3.ProgrammingError` sichtbare Fehler
    "SQLite objects created in a thread can only be used in that same thread" — der
    Hauptfaden schreibt zur selben Zeit über seine eigene Verbindung.

    `pipeline.resolve_triage_entries` wird hier durch eine Attrappe ersetzt, die für
    jeden Aufruf Faden- und Verbindungs-Identität aufzeichnet: Sie liefert beim ersten
    Aufruf (voller Wortschatz) genau **einen** Eintrag als `remaining`, beim zweiten
    (dieser eine Eintrag) eine leere `TriageResolution` — die Blockschleife entsteht damit
    unabhängig von `interaction.WORD_BLOCK_SIZE` zuverlässig zweimal: einmal im Hauptfaden
    (`resolve_visible_block`), einmal im Hintergrundfaden (`resolve_silent_block`).

    Verfälschungsprobe: Ersetzt man in `cli.main._run` beide `resolve_silent_block`-
    Argumente durch `_resolve_with_progress(con=con, ...)` (der naheliegende Fehlgriff,
    den Befund 2 der Durchsicht 1cfb1e4 beschreibt), bekommt die Attrappe im
    Hintergrundfaden dieselbe Verbindung wie der Hauptfaden — die Zusicherung auf
    `background_connections & main_thread_connections` schlägt dann an. Dieser Test war
    daran rot, siehe Bericht."""
    data_dir = tmp_path / "data"
    _write_config(
        data_dir,
        model_url="http://localhost:11434/v1",
        model_name="test-model",
        dictionary_path=mini_dictionary_db,
    )

    calls: list[tuple[int, int, int]] = []  # (thread_id, con_id, len(entries))

    def _fake_resolve_triage_entries(
        *,
        con: sqlite3.Connection,
        entries: Sequence[pipeline.VocabularyEntry],
        limit: int,
        url: str,
        get_model_name: Callable[[], str],
        order: str,
        on_progress: Callable[[int, int, int, int], None] | None = None,
    ) -> pipeline.TriageResolution:
        calls.append((threading.get_ident(), id(con), len(entries)))
        remaining = list(entries[:1]) if len(entries) > 1 else []
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=remaining
        )

    monkeypatch.setattr("cli.main.pipeline.resolve_triage_entries", _fake_resolve_triage_entries)

    def _read_line(prompt: str) -> str:
        if "Neu anlegen" in prompt:
            return "j"
        if "Sprachniveau" in prompt:
            return "keine angabe"
        if "weitermachen?" in prompt:
            return "j"
        raise AssertionError(f"unerwartete Frage im Prefetch-Test: {prompt!r}")

    written: list[str] = []

    exit_code = main(
        [str(book_epub), "--chapter", "1", "--data-dir", str(data_dir)],
        read_line=_read_line,
        write_line=written.append,
    )

    assert exit_code == 0, "\n".join(written)
    assert calls, "Testvoraussetzung verletzt: resolve_triage_entries wurde nie aufgerufen."
    first_entries_len = calls[0][2]
    assert first_entries_len > 1, (
        "Testvoraussetzung verletzt: das Testkapitel braucht mehr als einen Worteintrag, "
        f"damit überhaupt ein Vorladeblock entsteht (war {first_entries_len})."
    )

    main_thread_id = threading.get_ident()
    main_thread_connections = {
        con_id for thread_id, con_id, _ in calls if thread_id == main_thread_id
    }
    background_connections = {
        con_id for thread_id, con_id, _ in calls if thread_id != main_thread_id
    }
    assert background_connections, (
        "Testvoraussetzung verletzt: kein Vorladeblock lief im Hintergrundfaden."
    )
    assert not (background_connections & main_thread_connections), (
        "Der Hintergrundfaden hat dieselbe Profilverbindung wie der Hauptfaden benutzt "
        "(technik.md §12, Festlegung 1) - sqlite3-Objekte gehören dem Faden, der sie "
        "erzeugt hat, nicht der Datei."
    )


def test_resolve_silently_stops_within_one_more_progress_call_after_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Befund 4 (Durchsicht 1cfb1e4, technik.md §12 Festlegung 4): `_resolve_silently`
    bricht ab, sobald das übergebene `cancelled`-Ereignis gesetzt ist — spätestens nach
    einem weiteren, bereits laufenden Modellaufruf, nicht erst am Ende des ganzen Blocks.
    `pipeline.resolve_triage_entries` wird hier durch eine Attrappe ersetzt, die bei jedem
    simulierten Eintrag `on_progress` aufruft und mitzählt, wie oft das geschieht — das
    Ereignis wird nach dem ersten Aufruf gesetzt (simuliert: der Nutzer hat inzwischen mit
    `q` abgebrochen), ein zweiter Aufruf ist damit der letzte, den die Attrappe noch
    machen darf.

    Verfälschungsprobe: Übergibt `_resolve_silently` kein `on_progress` (der Stand vor
    dieser Behebung), prüft die Attrappe das Ereignis nie und läuft ungehindert bis zum
    Ende durch — `progress_calls` erreichte dann alle zehn simulierten Einträge statt nur
    zwei, und `pytest.raises(cli_main._PrefetchCancelled)` schlüge nie an. Dieser Test war
    daran rot, siehe Bericht."""
    cancelled = threading.Event()
    progress_calls: list[int] = []

    def _fake_resolve_triage_entries(
        *,
        con: sqlite3.Connection,
        entries: Sequence[pipeline.VocabularyEntry],
        limit: int,
        url: str,
        get_model_name: Callable[[], str],
        order: str,
        on_progress: Callable[[int, int, int, int], None] | None = None,
    ) -> pipeline.TriageResolution:
        assert on_progress is not None, "Befund 4 verlangt einen on_progress-Rückruf."
        for index in range(10):
            progress_calls.append(index + 1)
            on_progress(index + 1, 10, index + 1, limit)
            if index == 0:
                cancelled.set()  # simuliert: der Nutzer hat inzwischen abgebrochen
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    monkeypatch.setattr("cli.main.pipeline.resolve_triage_entries", _fake_resolve_triage_entries)
    monkeypatch.setattr("cli.main.profile.open_profile", lambda _path: sqlite3.connect(":memory:"))

    with pytest.raises(cli_main._PrefetchCancelled):
        cli_main._resolve_silently(
            profile_path=tmp_path / "profil.sqlite3",
            entries=[],
            limit=5,
            url="http://127.0.0.1:0/v1",
            get_model_name=lambda: "test-model",
            order="new_words_first",
            cancelled=cancelled,
        )

    assert progress_calls == [1, 2], (
        "Der Abbruch muss nach spätestens einem weiteren Fortschrittsaufruf greifen, "
        f"tatsächlich liefen {len(progress_calls)}."
    )


def test_resolve_silently_writes_nothing_to_the_screen_while_resolving_a_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(Befund A, Durchsicht 5fda1b9): technik.md §12, Festlegung 3 verlangt, dass ein
    vorgeladener Block **nichts** ausgibt — die sich fortschreibende Statuszeile
    (`cli.display.safe_print_progress`) schriebe aus dem Hintergrundfaden mitten in die
    Triage-Anzeige, über der der Nutzer gerade entscheidet. Bis zur Abbestellung (Befund
    4, Durchsicht 1cfb1e4) war das baulich erzwungen, weil `_resolve_silently` `on_progress`
    schlicht `None` ließ; seither hängt es allein am Rumpf von `_stop_if_cancelled`, das
    heute nur die Abbestellung prüft und sonst nichts tut — kein Test belegte das bisher.

    Verfälschungsprobe: Schreibt `_stop_if_cancelled` zusätzlich dieselbe
    Fortschrittszeile wie `_resolve_with_progress`s `_on_progress`
    (`safe_print_progress(f"Bedeutungen werden aufgelöst: {_examined} von {_total} …")`),
    bleiben alle anderen Tests aus `test_cli_main.py`, `test_cli_interaction.py` und
    `test_cli_display.py` grün (66 Tests, siehe Auftragstext) — nur dieser Test hier
    bemerkt es, weil er die Aufrufe von `safe_print_progress` tatsächlich mitzählt, statt
    nur die Kürze von `_stop_if_cancelled` beim Lesen zu unterstellen."""
    progress_calls: list[str] = []
    monkeypatch.setattr(
        "cli.main.safe_print_progress", lambda text, **_kwargs: progress_calls.append(text)
    )
    monkeypatch.setattr("cli.main.profile.open_profile", lambda _path: sqlite3.connect(":memory:"))

    def _fake_resolve_triage_entries(
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
        for index in range(5):
            on_progress(index + 1, 5, index + 1, limit)
        return pipeline.TriageResolution(
            entries=[], known=0, resolved_known=0, skipped=0, remaining=[]
        )

    monkeypatch.setattr("cli.main.pipeline.resolve_triage_entries", _fake_resolve_triage_entries)

    cli_main._resolve_silently(
        profile_path=tmp_path / "profil.sqlite3",
        entries=[],
        limit=5,
        url="http://127.0.0.1:0/v1",
        get_model_name=lambda: "test-model",
        order="new_words_first",
        cancelled=threading.Event(),
    )

    assert progress_calls == [], (
        "Der stille Vorladeblock hat auf dem Bildschirm geschrieben - Festlegung 3 aus "
        "technik.md §12 verlangt, dass er nichts ausgibt."
    )
