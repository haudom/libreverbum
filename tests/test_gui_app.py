"""Prüft `gui.app.build_engine`: `Main.qml` lädt ohne QML-Warnung (bauplan-phase2.md AP 15
— „eine falsche Bindung ist sonst der stille Fehlschlag aus Regel 13"), und `gui.app.
load_fonts`: eine fehlende Schrift bricht ab statt eine Ersatzschrift lautlos hinzunehmen
(Befund B4, Durchsicht d993e3e).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication

pytestmark = pytest.mark.needs_gui

FONTS = Path(__file__).resolve().parent.parent / "gui" / "fonts"


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


def test_late_qml_warning_reaches_stderr(
    qt_gui_app: QGuiApplication, capsys: pytest.CaptureFixture[str]
) -> None:
    """Befund B5 (Durchsicht d993e3e): `main()` liest `warnings` bisher nur ein einziges
    Mal, bevor `app.exec()` startet — eine Warnung, die erst während der Ereignisschleife
    auftritt (etwa `console.warn` aus einem späten Rückruf, hier nachgebildet über einen
    verzögerten `qWarning()`-Aufruf), verschwand bisher spurlos, auch von stderr.

    Verfälschung: die Zeile `print(message, file=sys.stderr)` im Meldungs-Handler von
    `build_engine` entfernen → `capsys` läse hier nichts, die Zusicherung unten wird rot."""
    del qt_gui_app
    from PySide6.QtCore import QEventLoop, QTimer, qInstallMessageHandler, qWarning

    from gui.app import build_engine

    _app, engine, _warnings = build_engine([])
    try:
        capsys.readouterr()  # Warnungen aus dem Laden selbst nicht mitzählen

        loop = QEventLoop()
        QTimer.singleShot(50, lambda: qWarning("spaete Warnung nach dem Laden"))
        QTimer.singleShot(500, loop.quit)
        loop.exec()

        captured = capsys.readouterr()
        assert "spaete Warnung nach dem Laden" in captured.err
    finally:
        from PySide6.QtQuick import QQuickWindow

        for root in engine.rootObjects():
            if isinstance(root, QQuickWindow):
                root.setVisible(False)
        qInstallMessageHandler(None)


def test_install_message_handler_deduplicates_identical_messages(
    qt_gui_app: QGuiApplication,
) -> None:
    """Befund F9 (Nachprüfung d00e7c9): `QQmlApplicationEngine.warnings` und der
    Meldungs-Handler melden manchmal denselben QML-Bindungsfehler über **beide** Wege —
    am Bestand beobachtet an `tests/qml_fixtures/` mit einer fehlenden
    Kontexteigenschaft, dort als zwei Warnungen statt einer gezählt. `record` (aus
    `install_message_handler`) verwirft deshalb einen Text, der in diesem Aufbau schon
    einmal vorkam.

    Verfälschung: `if message in gesehen: return` in `install_message_handler` entfernen
    → `warnings` bekäme die gleiche Meldung zweimal, die Zusicherung unten wird rot."""
    del qt_gui_app
    from PySide6.QtCore import qInstallMessageHandler

    from gui.app import install_message_handler

    warnings: list[str] = []
    record = install_message_handler(warnings)
    try:
        record("gleiche Meldung")
        record("gleiche Meldung")
        record("andere Meldung")
        assert warnings == ["gleiche Meldung", "andere Meldung"]
    finally:
        # Wie test_main_qml_loads_without_a_qml_warning oben: ein installierter
        # Meldungs-Handler wirkt prozessweit, ein liegengebliebener wäre selbst der
        # stille Fehlschlag, gegen den dieser Test antritt.
        qInstallMessageHandler(None)


def test_load_fonts_fails_on_an_empty_font_directory(
    qt_gui_app: QGuiApplication, tmp_path: Path
) -> None:
    """Befund B4 (Durchsicht d993e3e): Ein leeres Schriftverzeichnis lief bisher klaglos
    durch — die Ladeschleife fand keine `*.ttf`-Datei, meldete das nicht, und die
    Oberfläche zeigte erst am ersten Text ein Ersatzkästchen.

    Verfälschung: `if not families: raise RuntimeError(...)` aus `gui.app.load_fonts`
    entfernen → dieser Test bekäme keine Ausnahme und würde rot."""
    del qt_gui_app  # QFontDatabase braucht eine bestehende QGuiApplication
    from gui.app import load_fonts

    leer = tmp_path / "leer"
    leer.mkdir()

    with pytest.raises(RuntimeError, match="Keine Schrift"):
        load_fonts(leer)


def test_load_fonts_fails_when_a_theme_font_family_is_missing(
    qt_gui_app: QGuiApplication, tmp_path: Path
) -> None:
    """Befund B4, zweiter Fall: Eine geladene Schriftdatei allein genügt nicht — fehlt eine
    der beiden von `Theme.qml` genannten Familien (`fonts.book` = Literata, `fonts.ui` =
    Inter), bricht `load_fonts` jetzt ab, statt mit einer Ersatzschrift lautlos
    weiterzumachen. Kopiert wird absichtlich nur die echte `Inter`-Datei — die Familie
    kommt aus dem inneren Namensfeld der Schriftdatei, nicht aus dem Dateinamen.

    Verfälschung: die Prüfung `if fehlend: raise RuntimeError(...)` entfernen → dieser
    Test bekäme keine Ausnahme und würde rot."""
    del qt_gui_app
    from gui.app import load_fonts

    inter_font = next(FONTS.glob("Inter*.ttf"))
    ohne_literata = tmp_path / "ohne-literata"
    ohne_literata.mkdir()
    (ohne_literata / inter_font.name).write_bytes(inter_font.read_bytes())

    with pytest.raises(RuntimeError, match=r"Theme\.fonts nennt"):
        load_fonts(ohne_literata)
