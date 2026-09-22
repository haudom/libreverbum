"""Prüft `gui.app.build_engine`: `Main.qml` lädt ohne QML-Warnung (bauplan-phase2.md AP 15
— „eine falsche Bindung ist sonst der stille Fehlschlag aus Regel 13").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication

pytestmark = pytest.mark.needs_gui


def test_main_qml_loads_without_a_qml_warning(qt_gui_app: QGuiApplication) -> None:
    """`python -m gui` lädt `gui/qml/Main.qml` (mit dem eingebetteten Platzhalter-
    Bildschirm) ohne eine einzige QML-Warnung.

    Verfälschung: eine absichtlich falsche Bindung in `gui/qml/Placeholder.qml` (etwa
    `color: Theme.gibtEsNicht` statt `Theme.inkFaint`) — `build_engine` fängt sie über
    `QQmlApplicationEngine.warnings`, `warnings` wird nicht mehr leer, und die Zusicherung
    unten wird rot (am Bestand geprüft, Rücknahme über eine Scratchpad-Kopie, nie
    `git checkout`)."""
    del qt_gui_app  # sorgt nur dafür, dass genau eine QGuiApplication existiert
    from PySide6.QtCore import qInstallMessageHandler
    from PySide6.QtQuick import QQuickWindow

    from gui.app import build_engine

    _app, engine, warnings = build_engine([])
    try:
        assert engine.rootObjects(), "gui/qml/Main.qml wurde nicht geladen"
        assert not warnings, f"QML-Warnungen beim Laden von Main.qml: {warnings}"
    finally:
        for root in engine.rootObjects():
            if isinstance(root, QQuickWindow):
                root.setVisible(False)
        # REGEL (Durchsicht 907ab02, Befund 1, wie tests/test_environment.py): Ein
        # installierter Meldungs-Handler wirkt prozessweit und sonst in fremde Tests
        # hinein — ein liegengebliebener Handler wäre selbst der stille Fehlschlag, gegen
        # den dieser Test antritt.
        qInstallMessageHandler(None)
