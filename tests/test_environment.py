"""Prüft, dass die Umgebung der Festlegung aus Entscheidung 6 entspricht."""

import importlib.util
import sys
from pathlib import Path

import pytest


def test_decision_6_runtime_is_python_312() -> None:
    """Entscheidung 6: Gebaut wird auf Python 3.12 — der Fassung, auf der die Messungen
    zu Entscheidung 5 entstanden sind (technik.md §6)."""
    assert sys.version_info[:2] == (3, 12)


def test_decision_6_pinned_spacy_model_is_installed() -> None:
    """Entscheidung 6: `en_core_web_md` ist als Abhängigkeit festgeschrieben, nicht
    nebenher installiert — Entscheidung 5 gilt nur für dieses Modell (technik.md §6)."""
    assert importlib.util.find_spec("en_core_web_md") is not None


@pytest.mark.needs_gui
def test_bauplan_phase2_ap1_empty_qml_loads_offscreen_without_warnings(
    tmp_path: Path, qt_gui_app: object
) -> None:
    """bauplan-phase2.md AP 1: Ein leeres QML lädt offscreen (`QT_QPA_PLATFORM=offscreen`)
    ohne QML-Warnung. Jede Warnung — auch ein Bindungsfehler — lässt den Test scheitern,
    statt sie zu verschlucken (Regel 13; Abschnitt 8 des Bauplans, „der stille
    Fehlschlag, gegen den AP 15 die Warnungen zu Fehlern macht")."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    del qt_gui_app  # sorgt nur dafür, dass genau eine QGuiApplication existiert

    qml_path = tmp_path / "Empty.qml"
    qml_path.write_text(
        "import QtQuick\nItem {\n    width: 1\n    height: 1\n}\n", encoding="utf-8"
    )

    warnings: list[str] = []
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: warnings.extend(str(error) for error in errors))
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    assert engine.rootObjects(), "leeres QML wurde nicht geladen"
    assert not warnings, f"QML-Warnungen beim Laden: {warnings}"
