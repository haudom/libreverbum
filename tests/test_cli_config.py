"""Prüft `cli/config.py` — Datenverzeichnis und `config.toml` (technik.md §9, bauplan.md T16)."""

from __future__ import annotations

from pathlib import Path

from cli import config


def test_load_config_creates_the_template_once_and_reports_it(tmp_path: Path) -> None:
    """bauplan.md T16: Fehlt `config.toml`, wird sie einmalig aus einer Vorlage angelegt
    (technik.md §9) — der zweite Rückgabewert meldet das dem Aufrufer."""
    config_path = tmp_path / "config.toml"
    assert not config_path.is_file()

    _, just_created = config.load_config(tmp_path)

    assert just_created is True
    assert config_path.is_file()


def test_load_config_does_not_report_creation_on_a_second_call(tmp_path: Path) -> None:
    """Ein zweiter Aufruf über dieselbe, jetzt vorhandene Datei liest sie nur noch —
    „geschrieben wird die Datei nicht" (technik.md §9)."""
    config.load_config(tmp_path)

    _, just_created = config.load_config(tmp_path)

    assert just_created is False


def test_template_defaults_match_technik_md_9(tmp_path: Path) -> None:
    """technik.md §9, Tabelle „Einstellungen: config.toml": `model.url` ist
    standardmäßig `http://localhost:11434/v1`, leere Pfade bedeuten „im
    Datenverzeichnis"."""
    cfg, _ = config.load_config(tmp_path)

    assert cfg.model_url == "http://localhost:11434/v1"
    assert cfg.model_name == ""
    assert cfg.dictionary_path == tmp_path / "en-de.sqlite3"
    assert cfg.profile_path == tmp_path / "profil.sqlite3"


def test_load_config_reads_values_written_by_hand(tmp_path: Path) -> None:
    """technik.md §9: „Geschrieben wird die Datei nicht … ändert sie danach der Nutzer
    von Hand" — geänderte Werte müssen beim nächsten Lesen ankommen."""
    (tmp_path / "config.toml").write_text(
        '[model]\nurl = "http://192.168.2.129:11434/v1"\nname = "granite4"\n\n'
        '[paths]\ndictionary = "D:/woerterbuch/en-de.sqlite3"\nprofile = ""\n',
        encoding="utf-8",
    )

    cfg, just_created = config.load_config(tmp_path)

    assert just_created is False
    assert cfg.model_url == "http://192.168.2.129:11434/v1"
    assert cfg.model_name == "granite4"
    assert cfg.dictionary_path == Path("D:/woerterbuch/en-de.sqlite3")
    assert cfg.profile_path == tmp_path / "profil.sqlite3"
