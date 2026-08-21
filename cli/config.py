"""Datenverzeichnis und `config.toml` (technik.md §9).

Aufgabe
-------
Bestimmt das plattformübliche Nutzerverzeichnis und liest darin `config.toml` mit
`tomllib`. Fehlt die Datei, wird sie einmalig aus einer Vorlage angelegt — geschrieben
wird sie sonst nie (technik.md §9: „Geschrieben wird die Datei nicht: Fehlt sie, legt der
Aufrufer sie einmalig aus einer Vorlage an und ändert sie danach der Nutzer von Hand").
Dieses Modul bestimmt und legt an; der Kern (`libreverbum.*`) bekommt von hier aus nur
fertige Pfade und eine fertige Modellserver-Adresse (technik.md §9, „Der Kern kennt keine
Vorgabe") — keine dieser beiden Vorgaben entsteht im Kern selbst.

Voraussetzungen
---------------
Keine. Importiert nichts aus `libreverbum` — reine Pfad- und Dateiverwaltung.

Liefert
-------
`default_data_dir` das plattformübliche Verzeichnis (Windows:
`%LOCALAPPDATA%\\LibreVerbum`, sonst `$XDG_DATA_HOME/libreverbum` beziehungsweise
`~/.local/share/libreverbum`). `load_config` liefert `Config` samt einem zweiten
Rückgabewert, der genau dann `True` ist, wenn `config.toml` bei diesem Aufruf gerade erst
aus der Vorlage entstanden ist — der Aufrufer meldet das (bauplan.md T16) und bricht den
Lauf ab, statt mit den unveränderten Vorgabewerten (insbesondere `model.url`) einfach
weiterzumachen.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# REGEL (technik.md §9, „Einstellungen: config.toml"): dieselben vier Schlüssel, dieselben
# Vorgaben wie in der dortigen Tabelle. Kein fünfter Schlüssel ohne zweiten Anwendungsfall
# (dokumentation.md §4 Regel 14) — Kartenrichtung und Wortobergrenze bleiben Aufrufargumente
# beziehungsweise feste Zahlen, siehe cli/interaction.py und cli/main.py.
_TEMPLATE = """\
# LibreVerbum — Einstellungen (technik.md §9)
#
# Automatisch angelegt beim ersten Start. Von Hand anzupassen, bevor der nächste Lauf
# beginnt — insbesondere model.url, falls der Modellserver nicht auf localhost läuft (im
# Heimnetz laufende Server sind der Regelfall, nicht die Ausnahme). Es gibt keine
# Autosuche: Eine falsch geratene Adresse nähme im Zweifel stillschweigend einen anderen
# Server (Regel 13).

[model]
url = "http://localhost:11434/v1"
# Leer lassen, um das erste vom Server genannte Modell zu verwenden.
name = ""

[paths]
# Leer lassen, um die Dateien im selben Verzeichnis wie diese Einstellungen abzulegen.
dictionary = ""
profile = ""
"""

_CONFIG_FILE_NAME = "config.toml"


@dataclass(frozen=True)
class Config:
    """Fertig aufgelöste Einstellungen — genau das, was der Kern als Argument bekommt
    (technik.md §9, „Der Kern kennt keine Vorgabe")."""

    model_url: str
    model_name: str
    dictionary_path: Path
    profile_path: Path


def default_data_dir() -> Path:
    """Plattformübliches Nutzerverzeichnis (technik.md §9, „Wohin die Dateien gehören").

    Bricht sichtbar ab (dokumentation.md §4 Regel 13), wenn unter Windows `LOCALAPPDATA`
    fehlt — eine gewöhnliche Windows-Umgebung setzt diese Variable immer; ihr Fehlen ist
    ein Anzeichen für eine kaputte Umgebung, kein Fall für eine geratene Ersatzangabe.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise ValueError(
                "Umgebungsvariable LOCALAPPDATA ist nicht gesetzt — das plattformübliche "
                "Nutzerverzeichnis lässt sich nicht bestimmen."
            )
        return Path(base) / "LibreVerbum"

    xdg = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base_dir / "libreverbum"


def _write_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE, encoding="utf-8")


def load_config(data_dir: Path) -> tuple[Config, bool]:
    """Liest `config.toml` aus `data_dir`, legt sie beim ersten Aufruf aus der Vorlage an.

    Der zweite Rückgabewert ist `True`, wenn die Datei bei diesem Aufruf gerade erst
    entstanden ist — dann trägt sie noch die unveränderten Vorgabewerte, und der
    Aufrufer (`cli.main`) meldet das, statt mit einer vermutlich falschen
    Modellserver-Adresse weiterzulaufen (technik.md §9, „Warum eine Datei und nicht bloß
    ein Aufrufargument").

    `paths.dictionary` und `paths.profile` bleiben leer in der Vorlage; leer bedeutet
    „im Datenverzeichnis" (technik.md §9, Tabelle „Einstellungen: config.toml").
    """
    config_path = data_dir / _CONFIG_FILE_NAME
    just_created = not config_path.is_file()
    if just_created:
        _write_template(config_path)

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    model = raw.get("model", {})
    paths = raw.get("paths", {})

    model_url = str(model.get("url") or "http://localhost:11434/v1")
    model_name = str(model.get("name") or "")

    dictionary_raw = str(paths.get("dictionary") or "")
    profile_raw = str(paths.get("profile") or "")
    dictionary_path = Path(dictionary_raw) if dictionary_raw else data_dir / "en-de.sqlite3"
    profile_path = Path(profile_raw) if profile_raw else data_dir / "profil.sqlite3"

    config = Config(
        model_url=model_url,
        model_name=model_name,
        dictionary_path=dictionary_path,
        profile_path=profile_path,
    )
    return config, just_created
