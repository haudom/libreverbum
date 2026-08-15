"""Prüft die Architekturregel aus technik.md §1: Der Kern kennt die Oberfläche nicht.

Fehlt das Kernpaket oder ist es leer, schlägt der Test fehl, statt stillschweigend zu
bestehen — sonst bewiese er ab dem Tag nichts mehr, an dem der Pfad nicht mehr stimmt.
"""

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "libreverbum"

# PySide6 ist die Oberflächenbibliothek des Projekts (technik.md §1). PyQt steht daneben,
# weil es dieselbe Schnittstelle bedient und beim Übernehmen fremder Beispiele hereingerät.
GUI_PACKAGES = frozenset({"PySide6", "PyQt5", "PyQt6"})


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
