"""Prüft die Architekturregel aus technik.md §1: Der Kern kennt die Oberfläche nicht.

Fehlt das Kernpaket oder ist es leer, schlägt der Test fehl, statt stillschweigend zu
bestehen — sonst bewiese er ab dem Tag nichts mehr, an dem der Pfad nicht mehr stimmt.
"""

import ast
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parent.parent / "libreverbum"
APP = Path(__file__).resolve().parent.parent / "app"

# PySide6 ist die Oberflächenbibliothek des Projekts (technik.md §1). PyQt steht daneben,
# weil es dieselbe Schnittstelle bedient und beim Übernehmen fremder Beispiele hereingerät.
# "cli" (Befund mittel 5, Durchsicht T16): Mit bauplan.md T16 gibt es eine zweite
# Oberfläche neben der künftigen Qt-Oberfläche — ohne diesen Eintrag prüfte dieser Test
# nur PySide6/PyQt und ein `from cli import ...` im Kern bliebe grün.
# "gui", "app" (bauplan-phase2.md AP 1): Mit technik.md §14, E4 gibt es eine dritte
# Oberflächenschicht — ein `from gui import ...` oder `from app import ...` im Kern bliebe
# ohne diese beiden Einträge grün.
GUI_PACKAGES = frozenset({"PySide6", "PyQt5", "PyQt6", "cli", "gui", "app"})

# Was app/ selbst nicht importieren darf: keine der beiden Oberflächen, keine
# Oberflächenbibliothek (technik.md §14, E4 — „ein drittes Paket app/ … importiert den
# Kern, wird von beiden Oberflächen importiert, vom Kern nie"). Die Ausnahme app/pdf.py
# (E7 (b), AP 10) ist hier bewusst noch nicht eingebaut — E7 ist noch nicht entschieden,
# und Regel 14 verbietet einen Schalter ohne zweiten Anwendungsfall.
APP_FORBIDDEN_IMPORTS = frozenset({"PySide6", "PyQt5", "PyQt6", "cli", "gui"})


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
        if (found := imported_packages(module.read_text(encoding="utf-8-sig")) & GUI_PACKAGES)
    }
    assert not offenders, f"Oberflächen-Import im Kern: {offenders}"


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
