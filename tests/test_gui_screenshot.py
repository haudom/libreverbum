"""Prüft `tools/gui_screenshot.py` gegen den Bestand: Läuft als eigener Prozess (Aufruf wie
im Modulkopf beschrieben), damit jeder Testfall eine eigene `QGuiApplication` bekommt
(bauplan-phase2.md, Abschnitt 8: „Genau eine `QGuiApplication` je Prozess").

Die Untergrenze aus Befund B4 (Durchsicht `b2d5cab`) ist hier die zweite Verfälschungsprobe
aus dem Auftrag: Ein Bildschirm, der nichts zeichnet, muss selbst als Fehlschlag gemeldet
werden, nicht als „0 Warnungen, 0 Befunde" durchgehen.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "gui_screenshot.py"
FONTS = REPO_ROOT / "gui" / "fonts"

pytestmark = pytest.mark.needs_gui


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def test_gui_screenshot_renders_the_placeholder_screen_without_findings(tmp_path: Path) -> None:
    """Gegen den echten Bestand (`gui/qml/Placeholder.qml`, über `Main.qml` eingebettet):
    0 Warnungen, kein Layoutbefund, jede Textstelle über ihrer Kontrastschwelle."""
    png = tmp_path / "placeholder.png"
    result = _run("Placeholder", str(png), "--offscreen")

    assert result.returncode == 0, result.stdout + result.stderr
    assert png.is_file()
    assert "0 Warnungen" in result.stdout
    assert "0 Befunde" in result.stdout
    assert "Textstellen gemessen" in result.stdout
    assert "Ergebnis: OK" in result.stdout


def test_gui_screenshot_reports_a_blank_screen_instead_of_passing_silently(tmp_path: Path) -> None:
    """Untergrenze (Befund B4): Ein Bildschirm, der nichts zeichnet, gilt selbst als
    Fehlschlag — nicht als „0 Warnungen, 0 Befunde".

    Verfälschung: die Prüfung auf ein einfarbiges Bild aus `render()` entfernen (Vorbild
    `tools/design_mockup/shot.py`) → dieser Test wird rot, weil `returncode` dann 0 statt
    2 ist und die Meldung „einfarbig" fehlt."""
    qml_dir = tmp_path / "qml"
    qml_dir.mkdir()
    (qml_dir / "Blank.qml").write_text(
        "import QtQuick\nItem {\n    width: 10\n    height: 10\n}\n", encoding="utf-8"
    )
    png = tmp_path / "blank.png"

    result = _run(
        "Blank", str(png), "--offscreen", "--qml-dir", str(qml_dir), "--font-dir", str(FONTS)
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "einfarbig" in (result.stdout + result.stderr)
    assert not png.is_file(), "ein einfarbiges Bild hätte nicht geschrieben werden dürfen"


def test_gui_screenshot_fails_on_a_qml_binding_warning(tmp_path: Path) -> None:
    """Eine falsche Bindung erzeugt eine QML-Warnung, und die zählt als Fehlschlag
    (Regel 13) — nicht nur als Rauschen in der Ausgabe.

    Verfälschung: `qInstallMessageHandler`/`engine.warnings` in `render()` nicht mehr
    auswerten → `returncode` bliebe 0 trotz der `ReferenceError` unten."""
    qml_dir = tmp_path / "qml"
    qml_dir.mkdir()
    (qml_dir / "Broken.qml").write_text(
        "import QtQuick\n"
        "Rectangle {\n"
        "    width: 400\n"
        "    height: 300\n"
        '    color: "white"\n'
        "    Text {\n"
        '        text: "kaputt"\n'
        "        color: nichtVorhanden\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    png = tmp_path / "broken.png"

    result = _run(
        "Broken", str(png), "--offscreen", "--qml-dir", str(qml_dir), "--font-dir", str(FONTS)
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "ReferenceError" in (result.stdout + result.stderr)
