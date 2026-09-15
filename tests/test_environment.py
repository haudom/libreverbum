"""Prüft, dass die Umgebung der Festlegung aus Entscheidung 6 entspricht."""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication


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
    tmp_path: Path, qt_gui_app: "QGuiApplication"
) -> None:
    """bauplan-phase2.md AP 1: Ein leeres QML lädt offscreen (`QT_QPA_PLATFORM=offscreen`)
    ohne QML-Warnung. Jede Warnung — auch ein Bindungsfehler — lässt den Test scheitern,
    statt sie zu verschlucken (Regel 13; Abschnitt 8 des Bauplans, „der stille
    Fehlschlag, gegen den AP 15 die Warnungen zu Fehlern macht").

    `QQmlEngine.warnings` allein sieht nicht jede Warnung (Durchsicht 907ab02, Befund 1):
    `console.warn`/`console.error` aus QML sowie eigene Qt-Meldungen (`qWarning`,
    `qCritical` — etwa `QFontDatabase`, das AP 15 mit mitgebrachten Schriften und Qt Quick
    Controls anspricht) laufen ausschließlich über `qInstallMessageHandler`, nie über
    `QQmlEngine.warnings`: Dort erzeugt nur, was die QML-Maschine selbst als `QQmlError`
    einstuft. Deshalb zusätzlich der Meldungs-Handler, mit derselben Zusicherung.

    Die `QFontDatabase`-Meldung selbst tritt bei diesem leeren QML nicht auf — nachgemessen
    (Durchsicht 907ab02): Erst ein echtes `Qt Quick Controls`-Element mit `Basic`-Stil und
    tatsächlichem Rendern löst sie aus, nicht schon der bloße `import`. Für dieses leere QML
    ist sie also nicht unvermeidbar und braucht deshalb keine Ausnahmeliste — AP 15 misst
    das für Controls neu, sobald es sie tatsächlich lädt."""
    from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtQml import QQmlApplicationEngine

    del qt_gui_app  # sorgt nur dafür, dass genau eine QGuiApplication existiert

    qml_path = tmp_path / "Empty.qml"
    qml_path.write_text(
        "import QtQuick\nItem {\n    width: 1\n    height: 1\n}\n", encoding="utf-8"
    )

    qt_messages: list[str] = []

    def _on_qt_message(msg_type: "QtMsgType", context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            qt_messages.append(message)

    qInstallMessageHandler(_on_qt_message)
    try:
        warnings: list[str] = []
        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda errors: warnings.extend(str(error) for error in errors))
        engine.load(QUrl.fromLocalFile(str(qml_path)))

        assert engine.rootObjects(), "leeres QML wurde nicht geladen"
        assert not warnings, f"QML-Warnungen (engine.warnings) beim Laden: {warnings}"
        assert not qt_messages, f"Qt-Meldungen (Meldungs-Handler) beim Laden: {qt_messages}"
    finally:
        # REGEL (Durchsicht 907ab02, Befund 1): Ein installierter Handler wirkt
        # prozessweit und sonst in fremde Tests hinein — ein liegengebliebener Handler wäre
        # selbst der stille Fehlschlag, den dieser Test verhindern soll.
        qInstallMessageHandler(None)
