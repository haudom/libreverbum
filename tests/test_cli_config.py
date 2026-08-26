"""Prüft `cli/config.py` — Datenverzeichnis und `config.toml` (technik.md §9, bauplan.md T16)."""

from __future__ import annotations

from pathlib import Path

import pytest

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
    standardmäßig `http://localhost:11434/v1`, `model.name` die Empfehlung aus §3,
    Entscheidung 3 (`gemma4:e4b`), leere Pfade bedeuten „im Datenverzeichnis",
    `triage.order` standardmäßig `"new_words_first"`."""
    cfg, _ = config.load_config(tmp_path)

    assert cfg.model_url == "http://localhost:11434/v1"
    assert cfg.model_name == "gemma4:e4b"
    assert cfg.dictionary_path == tmp_path / "en-de.sqlite3"
    assert cfg.profile_path == tmp_path / "profil.sqlite3"
    assert cfg.triage_order == "new_words_first"


def test_load_config_reads_values_written_by_hand(tmp_path: Path) -> None:
    """technik.md §9: „Geschrieben wird die Datei nicht … ändert sie danach der Nutzer
    von Hand" — geänderte Werte müssen beim nächsten Lesen ankommen."""
    (tmp_path / "config.toml").write_text(
        '[model]\nurl = "http://192.168.2.129:11434/v1"\nname = "granite4"\n\n'
        '[paths]\ndictionary = "D:/woerterbuch/en-de.sqlite3"\nprofile = ""\n\n'
        '[triage]\norder = "frequency"\n',
        encoding="utf-8",
    )

    cfg, just_created = config.load_config(tmp_path)

    assert just_created is False
    assert cfg.model_url == "http://192.168.2.129:11434/v1"
    assert cfg.model_name == "granite4"
    assert cfg.dictionary_path == Path("D:/woerterbuch/en-de.sqlite3")
    assert cfg.profile_path == tmp_path / "profil.sqlite3"
    assert cfg.triage_order == "frequency"


def test_load_config_defaults_triage_order_when_the_section_is_missing(tmp_path: Path) -> None:
    """Eine von Hand geschriebene `config.toml` ohne `[triage]`-Abschnitt (etwa aus einer
    Fassung vor dem 25.08.2026) darf nicht scheitern — leer bedeutet die Vorgabe
    `"new_words_first"`, genau wie bei den übrigen Schlüsseln."""
    (tmp_path / "config.toml").write_text(
        '[model]\nurl = "http://localhost:11434/v1"\nname = ""\n\n'
        '[paths]\ndictionary = ""\nprofile = ""\n',
        encoding="utf-8",
    )

    cfg, _ = config.load_config(tmp_path)

    assert cfg.triage_order == "new_words_first"


def test_load_config_rejects_an_unknown_triage_order_value(tmp_path: Path) -> None:
    """Auftragstext vom 25.08.2026, Abschnitt 2: Ein unbekannter Wert von `[triage]
    order` bricht sichtbar ab und nennt die zulässigen Werte (Regel 13, dokumentation.md
    §4) — nicht stillschweigend auf die Vorgabe `new_words_first` zurückfallen."""
    (tmp_path / "config.toml").write_text(
        '[model]\nurl = "http://localhost:11434/v1"\nname = ""\n\n'
        '[paths]\ndictionary = ""\nprofile = ""\n\n'
        '[triage]\norder = "alphabetisch"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="new_words_first"):
        config.load_config(tmp_path)


@pytest.mark.parametrize("order_literal", ['""', "0", "false"])
def test_load_config_rejects_an_empty_or_falsy_triage_order_value(
    tmp_path: Path, order_literal: str
) -> None:
    """Befund leicht 3 (Durchsicht T16/T17): `order = ""`, `order = 0` und `order = false`
    fielen vor dieser Behebung still auf die Vorgabe zurück (`.get("order") or …`), obwohl
    der Schlüssel **gesetzt** war — nur ein fehlender Schlüssel darf die Vorgabe nehmen
    (Regel 13, dokumentation.md §4). Anders als beim fehlenden `[triage]`-Abschnitt
    (`test_load_config_defaults_triage_order_when_the_section_is_missing` oben) bricht das
    hier sichtbar ab, genau wie bei einem unbekannten Wert.

    Verfälschungsprobe: `triage.get("order", "new_words_first")` durch
    `triage.get("order") or "new_words_first"` ersetzt (der Stand vor dieser Behebung)
    ließ diesen Test rot werden — `load_config` lieferte dann klaglos `cfg.triage_order ==
    "new_words_first"`, statt wie hier erwartet abzubrechen."""
    (tmp_path / "config.toml").write_text(
        '[model]\nurl = "http://localhost:11434/v1"\nname = ""\n\n'
        '[paths]\ndictionary = ""\nprofile = ""\n\n'
        f"[triage]\norder = {order_literal}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="new_words_first"):
        config.load_config(tmp_path)
