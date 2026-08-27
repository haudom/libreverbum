"""Datenverzeichnis und `config.toml` (technik.md §9).

Aufgabe
-------
Bestimmt das Datenverzeichnis und liest darin `config.toml` mit
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
`default_data_dir` das Verzeichnis `data/` neben dem Projekt — dieselbe Stelle auf
jeder Plattform, weil LibreVerbum aus dem Quellbaum läuft (technik.md §9).
`load_config` liefert `Config` samt einem zweiten
Rückgabewert, der genau dann `True` ist, wenn `config.toml` bei diesem Aufruf gerade erst
aus der Vorlage entstanden ist — der Aufrufer meldet das (bauplan.md T16) und bricht den
Lauf ab, statt mit den unveränderten Vorgabewerten (insbesondere `model.url`) einfach
weiterzumachen.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# REGEL (technik.md §9, „Einstellungen: config.toml"): dieselben fünf Schlüssel, dieselben
# Vorgaben wie in der dortigen Tabelle. Kein sechster Schlüssel ohne zweiten Anwendungsfall
# (dokumentation.md §4 Regel 14) — Kartenrichtung und Wortobergrenze bleiben Aufrufargumente
# beziehungsweise feste Zahlen, siehe cli/interaction.py und cli/main.py. `triage.order`
# ist am 25.08.2026 als fünfter Schlüssel dazugekommen: Regel 14 verlangt einen zweiten
# Anwendungsfall, und der liegt vor — der Nutzer will die teilweise bekannten Wörter
# wahlweise gleichberechtigt neben den neuen sehen, statt sie grundsätzlich zurückzustellen.
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
# Empfehlung aus der Messung (technik.md §3, Entscheidung 3): gemma4:e4b mit
# temperature: 0 — beste Trefferquote bei vertretbarer Zeit (0,48 s/Wort). Ein anderer
# Modellname ist möglich; leer lassen nimmt das erste vom Server genannte Modell.
name = "gemma4:e4b"

[paths]
# Leer lassen, um die Dateien im selben Verzeichnis wie diese Einstellungen abzulegen.
dictionary = ""
profile = ""

[triage]
# "new_words_first": zuerst Wörter, von denen noch keine Bedeutung bekannt ist — vier
#   Messläufe am echten Server (granite4.1:8b, sherlock.epub Kapitel 2, 25.08.2026)
#   ergaben 39 bis 44 Modellaufrufe je Kapitel, 44 bis 64 Sekunden. Dabei wird die
#   Gruppe der teilweise bekannten Wörter bei diesem Kapitel nie erreicht — „neue
#   Bedeutung eines bekannten Wortes" (konzept.md §5) taucht unter dieser Vorgabe also
#   praktisch nicht auf.
# "frequency": streng nach Häufigkeit, einschließlich der Wörter, von denen schon eine
#   andere Bedeutung bekannt ist. Dieselben vier Läufe ergaben 39 bis 112 Aufrufe (21
#   bis 37 Sekunden) und fand dabei auch neue Bedeutungen bekannter Wörter — anders als
#   "new_words_first" oben.
order = "new_words_first"
"""

_CONFIG_FILE_NAME = "config.toml"

# REGEL (dokumentation.md §4 Regel 13): Ein unbekannter Wert bricht sichtbar ab und nennt
# die zulässigen Werte — nicht stillschweigend auf die Vorgabe zurückfallen. Als Tupel und
# nicht als Aufzählung aus libreverbum: Dieses Modul importiert laut Moduldocstring nichts
# aus libreverbum („reine Pfad- und Dateiverwaltung"), `libreverbum.pipeline.
# resolve_triage_entries` validiert denselben Wert deshalb ein zweites Mal, unabhängig von
# dieser Stelle.
_VALID_TRIAGE_ORDERS = ("new_words_first", "frequency")


@dataclass(frozen=True)
class Config:
    """Fertig aufgelöste Einstellungen — genau das, was der Kern als Argument bekommt
    (technik.md §9, „Der Kern kennt keine Vorgabe")."""

    model_url: str
    model_name: str
    dictionary_path: Path
    profile_path: Path
    triage_order: str


# REGEL (technik.md §9, „Wohin die Dateien gehören"): Gemessen vom Ort dieser Datei aus
# (cli/config.py, eine Ebene unter der Wurzel), nicht vom Arbeitsverzeichnis. `Path.cwd()`
# träfe je nach Aufrufort ein anderes Profil, und ein Profil an unerwarteter Stelle sieht
# aus wie ein verlorenes — dieselbe Sorge, aus der `cli.main._confirm_new_profile` vor dem
# ersten Anlegen nachfragt.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def default_data_dir() -> Path:
    """`data/` neben dem Projekt (technik.md §9, „Wohin die Dateien gehören").

    LibreVerbum läuft aus dem Quellbaum; ein Installationspaket gibt es nicht und damit
    auch kein Verzeichnis unter `Program Files`, gegen das die frühere Vorgabe im
    Nutzerverzeichnis gebaut war. Ein sichtbarer Ordner neben dem Programm ist dagegen
    auffindbar, ohne im Explorer erst versteckte Verzeichnisse einzuschalten. Kommt später
    ein Installationspaket, dreht sich diese Entscheidung wieder um — technik.md §9 hält
    sie deshalb ausdrücklich als an den Quellbaumbetrieb gebunden fest.

    Wer sein Profil außerhalb des Projektordners will, trägt `paths.profile` in
    `config.toml` ein oder ruft mit `--data-dir` auf; beides gab es schon vorher.
    """
    return _PROJECT_ROOT / "data"


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

    Bricht sichtbar ab (dokumentation.md §4 Regel 13), wenn `triage.order` einen anderen
    Wert als `"new_words_first"` oder `"frequency"` trägt — ein Tippfehler in `config.toml`
    soll nicht stillschweigend auf die Vorgabe zurückfallen, sondern sofort auffallen,
    bevor der Lauf beginnt (nicht erst, wenn `pipeline.resolve_triage_entries` denselben
    Wert ein zweites Mal prüft)."""
    config_path = data_dir / _CONFIG_FILE_NAME
    just_created = not config_path.is_file()
    if just_created:
        _write_template(config_path)

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    model = raw.get("model", {})
    paths = raw.get("paths", {})
    triage = raw.get("triage", {})

    model_url = str(model.get("url") or "http://localhost:11434/v1")
    model_name = str(model.get("name") or "")

    dictionary_raw = str(paths.get("dictionary") or "")
    profile_raw = str(paths.get("profile") or "")
    dictionary_path = Path(dictionary_raw) if dictionary_raw else data_dir / "en-de.sqlite3"
    profile_path = Path(profile_raw) if profile_raw else data_dir / "profil.sqlite3"

    # (Befund leicht 3, Durchsicht T16/T17): `.get("order") or …` ließ jeden falschen,
    # aber leeren oder falschtypigen Wert (order = "", order = 0, order = false)
    # stillschweigend auf die Vorgabe zurückfallen, während jeder andere unzulässige Wert
    # abbrach — nur ein **fehlender** Schlüssel darf die Vorgabe nehmen (Regel 13).
    triage_order = str(triage.get("order", "new_words_first"))
    if triage_order not in _VALID_TRIAGE_ORDERS:
        erlaubt = " oder ".join(f'"{wert}"' for wert in _VALID_TRIAGE_ORDERS)
        raise ValueError(
            f'[triage] order = "{triage_order}" in {config_path} ist unzulässig — '
            f"erlaubt sind {erlaubt}."
        )

    config = Config(
        model_url=model_url,
        model_name=model_name,
        dictionary_path=dictionary_path,
        profile_path=profile_path,
        triage_order=triage_order,
    )
    return config, just_created
