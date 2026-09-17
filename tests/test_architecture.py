"""Prüft die Architekturregel aus technik.md §1: Der Kern kennt die Oberfläche nicht.

Fehlt das Kernpaket oder ist es leer, schlägt der Test fehl, statt stillschweigend zu
bestehen — sonst bewiese er ab dem Tag nichts mehr, an dem der Pfad nicht mehr stimmt.
"""

import ast
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parent.parent / "libreverbum"
APP = Path(__file__).resolve().parent.parent / "app"
CLI = Path(__file__).resolve().parent.parent / "cli"
GUI = Path(__file__).resolve().parent.parent / "gui"

# PySide6 ist die Oberflächenbibliothek des Projekts (technik.md §1). PyQt steht daneben,
# weil es dieselbe Schnittstelle bedient und beim Übernehmen fremder Beispiele hereingerät.
# "cli" (Befund mittel 5, Durchsicht T16): Mit bauplan.md T16 gibt es eine zweite
# Oberfläche neben der künftigen Qt-Oberfläche — ohne diesen Eintrag prüfte dieser Test
# nur PySide6/PyQt und ein `from cli import ...` im Kern bliebe grün.
# "gui" (bauplan-phase2.md AP 1): Mit technik.md §14, E4 gibt es eine dritte
# Oberflächenschicht — ein `from gui import ...` im Kern bliebe ohne diesen Eintrag grün.
# "app" (bauplan-phase2.md AP 1, technik.md §14, E4): app/ ist selbst keine Oberfläche —
# E4 definiert es ausdrücklich als „ohne Qt, ohne Konsole" —, gehört aber dennoch in diese
# Liste, weil der Kern auch app/ nie importieren darf. Der Konstantenname nennt deshalb den
# gemeinsamen Nenner „im Kern verboten", nicht „Oberfläche" (Durchsicht 907ab02, Befund 5):
# Ein Bearbeiter, der wegen dieser Konstante nach einem Qt-Import sucht, fände sonst einen
# app-Import und wäre in die Irre geführt.
FORBIDDEN_IN_CORE = frozenset({"PySide6", "PyQt5", "PyQt6", "cli", "gui", "app"})

# Was app/ selbst nicht importieren darf: keine der beiden Oberflächen, keine
# Oberflächenbibliothek (technik.md §14, E4 — „ein drittes Paket app/ … importiert den
# Kern, wird von beiden Oberflächen importiert, vom Kern nie"). Die Ausnahme app/pdf.py
# (E7 (b), AP 10) ist hier bewusst noch nicht eingebaut — E7 ist noch nicht entschieden,
# und Regel 14 verbietet einen Schalter ohne zweiten Anwendungsfall.
APP_FORBIDDEN_IMPORTS = frozenset({"PySide6", "PyQt5", "PyQt6", "cli", "gui"})

# CLAUDE.md, „Architektur": „cli/ und gui/ importieren sich nicht gegenseitig" — bisher eine
# Zusage ohne Test (Vorbefund V1, Durchsicht von 421cb95). Zwei getrennte Konstanten statt
# einer, weil die beiden Richtungen unterschiedlich geprüft werden: cli/ gibt es bereits,
# gui/ entsteht erst mit den kommenden Arbeitspaketen.
CLI_FORBIDDEN_IMPORTS = frozenset({"gui"})
GUI_FORBIDDEN_IMPORTS = frozenset({"cli"})


def imported_packages(source: str) -> set[str]:
    """Die obersten Paketnamen aller Importe, über den Syntaxbaum statt per Textsuche —
    eine Textsuche fände auch diese Zeile und den Docstring darunter."""
    packages: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            packages.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            packages.add(node.module.split(".")[0])
    return packages


def test_rule_9_core_does_not_import_the_user_interface() -> None:
    """Regel 9, strukturelle Hälfte: Der Kern wird ohne jeden Bezug zur Oberfläche gebaut,
    die Oberfläche ruft ihn nur auf (technik.md §1, „Architekturregel", und §7, „Die
    Importregel")."""
    modules = sorted(CORE.rglob("*.py"))
    assert modules, f"Kein Kernmodul unter {CORE} gefunden — dieser Test prüfte nichts."

    offenders = {
        module.relative_to(CORE.parent).as_posix(): sorted(found)
        for module in modules
        # utf-8-sig statt utf-8 (dokumentation.md §8): Python akzeptiert eine BOM in
        # Quelldateien, ast.parse nicht. Unter Windows erzeugt jedes `Out-File` eine —
        # sonst stürzt dieser Test an gültigem Code ab, statt ihn zu prüfen.
        if (found := imported_packages(module.read_text(encoding="utf-8-sig")) & FORBIDDEN_IN_CORE)
    }
    assert not offenders, f"Im Kern verbotener Import: {offenders}"


# Diese beiden Module verkettet die Importregel nicht: `__init__` trägt nur den
# Paket-Docstring, `pipeline` ist nach technik.md §7 der einzige Ort, der mehrere Schritte
# kennen darf. `entities` braucht die Ausnahme nicht: Es importiert nichts aus dem Kern.
STEP_MODULE_EXEMPTIONS = frozenset({"__init__.py", "pipeline.py"})


def core_siblings_imported(source: str) -> set[str]:
    """Die Namen der `libreverbum`-Geschwistermodule, die eine Datei importiert — absolut
    (`from libreverbum import entities`, `import libreverbum.entities`) wie relativ
    (`from . import entities`, `from .entities import Lemma`)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0:
                if node.module:
                    names.add(node.module.split(".")[0])
                else:
                    names.update(alias.name for alias in node.names)
            elif node.module == "libreverbum":
                names.update(alias.name for alias in node.names)
            elif node.module and node.module.startswith("libreverbum."):
                names.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "libreverbum" and len(parts) > 1:
                    names.add(parts[1])
    return names


def test_rule_9_step_modules_import_only_entities() -> None:
    """Regel 9, innere Hälfte: Innerhalb des Kerns importiert jeder Schritt nur `entities`.
    Wer mehrere Schritte kennt, ist `pipeline` — und sonst niemand (technik.md §7, „Die
    Importregel")."""
    modules = sorted(CORE.rglob("*.py"))
    assert modules, f"Kein Kernmodul unter {CORE} gefunden — dieser Test prüfte nichts."

    offenders = {
        module.relative_to(CORE.parent).as_posix(): sorted(found)
        for module in modules
        if module.name not in STEP_MODULE_EXEMPTIONS
        and (found := core_siblings_imported(module.read_text(encoding="utf-8-sig")) - {"entities"})
    }
    assert not offenders, f"Schrittmodul kennt mehr als entities: {offenders}"


def test_rule_9_app_package_does_not_import_the_interfaces() -> None:
    """technik.md §14, E4: `app/` importiert weder `cli` noch `gui` noch eine
    Oberflächenbibliothek — es liegt zwischen Kern und beiden Oberflächen, nicht über
    ihnen (bauplan-phase2.md AP 1).

    `app/` entsteht erst in AP 3. Bis dahin überspringt sich dieser Test **sichtbar** mit
    Begründung, statt stillschweigend nichts zu prüfen — sonst sähe eine Prüfung, die
    dauerhaft nichts prüft, wie eine grüne Prüfung aus (Klarstellung der Hauptsitzung zu
    AP 1). Sobald `app/` existiert, greift er wie `test_rule_9_core_does_not_import_the_
    user_interface` oben."""
    if not APP.is_dir():
        pytest.skip(
            "app/ existiert noch nicht (entsteht in AP 3, bauplan-phase2.md) — "
            "dieser Test greift, sobald das Paket da ist"
        )
    modules = sorted(APP.rglob("*.py"))
    assert modules, f"Kein Modul unter {APP} gefunden — dieser Test prüfte nichts."

    offenders = {
        module.relative_to(APP.parent).as_posix(): sorted(found)
        for module in modules
        if (
            found := imported_packages(module.read_text(encoding="utf-8-sig"))
            & APP_FORBIDDEN_IMPORTS
        )
    }
    assert not offenders, f"Oberflächen-Import in app/: {offenders}"


def test_cli_does_not_import_gui() -> None:
    """CLAUDE.md, „Architektur": „cli/ und gui/ importieren sich nicht gegenseitig" — hier
    die cli-Hälfte. cli/ gibt es bereits seit Phase 1, die Prüfung greift deshalb ab
    sofort, nicht erst, wenn gui/ entsteht."""
    modules = sorted(CLI.rglob("*.py"))
    assert modules, f"Kein Modul unter {CLI} gefunden — dieser Test prüfte nichts."

    offenders = {
        module.relative_to(CLI.parent).as_posix(): sorted(found)
        for module in modules
        if (
            found := imported_packages(module.read_text(encoding="utf-8-sig"))
            & CLI_FORBIDDEN_IMPORTS
        )
    }
    assert not offenders, f"gui-Import in cli/: {offenders}"


def test_gui_does_not_import_cli() -> None:
    """CLAUDE.md, „Architektur": „cli/ und gui/ importieren sich nicht gegenseitig" — hier
    die gui-Hälfte. Python bekommt `gui/` erst mit AP 15; bis dahin überspringt sich dieser
    Test **sichtbar** mit Begründung, genau wie zuvor
    `test_rule_9_app_package_does_not_import_the_interfaces` vor AP 3 oben.

    Seit AP 14 (`gui/qml/Theme.qml`, `gui/fonts/`) **gibt es das Verzeichnis**, aber kein
    Modul darin. `GUI.is_dir()` allein reicht deshalb nicht mehr als Bedingung: Der
    anschließende `assert modules` wäre rot geworden, obwohl nichts falsch ist — ein
    Fehlschlag, der auf das Anlegen eines Ordners zeigt statt auf einen verbotenen Import
    (dieselbe Verwechslung wie bei `app/` zwischen AP 1 und AP 3). Geprüft wird deshalb
    auf das erste Python-Modul, nicht auf das Verzeichnis."""
    modules = sorted(GUI.rglob("*.py"))
    if not modules:
        pytest.skip(
            "gui/ enthält noch kein Python-Modul (kommt mit AP 15, bauplan-phase2.md) — "
            "dieser Test greift, sobald das erste da ist"
        )

    offenders = {
        module.relative_to(GUI.parent).as_posix(): sorted(found)
        for module in modules
        if (
            found := imported_packages(module.read_text(encoding="utf-8-sig"))
            & GUI_FORBIDDEN_IMPORTS
        )
    }
    assert not offenders, f"cli-Import in gui/: {offenders}"
