"""Baut die Anwendung auf: `QGuiApplication`, Schriften, `QQmlApplicationEngine`, `Main.qml`.

Voraussetzungen
----------------
Genau eine `QGuiApplication` je Prozess (bauplan-phase2.md, Abschnitt 8); in Tests
übernimmt das die sitzungsweite Vorrichtung `qt_gui_app` aus `tests/conftest.py`, hier
`build_engine` legt keine zweite an, wenn schon eine läuft.

Liefert
-------
`build_engine(argv=None)`: erzeugt Anwendung, lädt Schriften und `Main.qml`, liefert
`(app, engine, warnings)` — ohne die Ereignisschleife zu starten, damit ein Test das
Ergebnis prüfen kann, ohne ein Fenster laufen zu lassen. `main(argv=None)`: dasselbe, prüft
`warnings` und `engine.rootObjects()` und startet danach `app.exec()` — der eigentliche
Einstiegspunkt von `python -m gui`.

Regeln
------
`QQuickStyle.setStyle("Basic")` steht **vor** jedem `QQmlApplicationEngine.load` (Regel
gilt für die gesamte Prozesslaufzeit, nicht nur für dieses eine Laden) — danach wirkt der
Aufruf nicht mehr (bauplan-phase2.md, Abschnitt 8). Jede QML-Warnung gilt als Fehlschlag
(Regel 13): Ohne diese Zusicherung ist eine falsche Bindung der stille Fehlschlag, gegen
den AP 15 antritt — nichts erscheint, nichts meldet. Warnungen kommen über **zwei** Wege
herein, `QQmlApplicationEngine.warnings` und `qInstallMessageHandler` — Ersteres sieht nur,
was die QML-Maschine selbst als `QQmlError` einstuft, `console.warn` und Qt-eigene
Meldungen (etwa von `QFontDatabase`) laufen ausschließlich über den Meldungs-Handler
(Durchsicht 907ab02, Befund 1; `tests/test_environment.py`,
`test_bauplan_phase2_ap1_empty_qml_loads_offscreen_without_warnings`).

Unter `QT_QPA_PLATFORM=offscreen` kennt der Offscreen-Treiber unter Windows von sich aus
keine einzige Schriftfamilie und meldet das als eigene `QFontDatabase`-Warnung — unabhängig
davon, ob `load_fonts` erfolgreich war (am Bestand nachgemessen: ohne `QT_QPA_FONTDIR`
blieb die Warnung auch mit geladenen Schriften stehen). Vorbild `tools/design_mockup/
shot.py`: `QT_QPA_FONTDIR` zeigt in diesem Fall auf `gui/fonts/`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

GUI_DIR = Path(__file__).resolve().parent
QML_DIR = GUI_DIR / "qml"
FONTS_DIR = GUI_DIR / "fonts"
MAIN_QML = QML_DIR / "Main.qml"


def load_fonts(font_dir: Path = FONTS_DIR) -> list[str]:
    """Lädt jede `*.ttf` aus `font_dir` über `QFontDatabase.addApplicationFont`.

    Muss vor dem Laden von QML laufen (bauplan-phase2.md, Abschnitt 8). Der Rückgabewert
    `-1` ist ein Fehlschlag und wird nicht verschluckt (Regel 13): eine fehlende Schrift
    bräche sonst erst beim ersten sichtbaren Textfeld auf, ohne erkennbare Ursache."""
    from PySide6.QtGui import QFontDatabase

    families: list[str] = []
    for font_path in sorted(font_dir.glob("*.ttf")):
        handle = QFontDatabase.addApplicationFont(str(font_path))
        if handle < 0:
            raise RuntimeError(f"Schrift nicht geladen: {font_path}")
        families.extend(QFontDatabase.applicationFontFamilies(handle))
    return families


def build_engine(
    argv: list[str] | None = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, list[str]]:
    """Baut Anwendung, Schriften und Engine auf und lädt `Main.qml` — ohne `app.exec()`.

    Getrennt von `main()`, damit ein Test das Ergebnis (Warnungen, geladene Wurzelobjekte)
    prüfen kann, ohne eine echte Ereignisschleife laufen zu lassen."""
    from typing import cast

    from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    # Siehe Modulkopf, „Regeln", letzter Absatz — nur unter offscreen nötig.
    # setdefault, damit eine Vorgabe aus der aufrufenden Shell nicht überschrieben wird
    # (wie bei QT_QPA_PLATFORM in tests/conftest.py).
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        os.environ.setdefault("QT_QPA_FONTDIR", str(FONTS_DIR))

    # REGEL (bauplan-phase2.md, Abschnitt 8): Muss vor dem ersten Laden stehen.
    QQuickStyle.setStyle("Basic")

    args = list(argv) if argv is not None else sys.argv
    # instance() ist auf QCoreApplication typisiert (Basisklasse); in diesem Prozess ist
    # es entweder None oder genau die hier selbst erzeugte QGuiApplication (Abschnitt 8:
    # „Genau eine QGuiApplication je Prozess") — der cast trägt nur diese Zusicherung nach.
    app = cast("QGuiApplication", QGuiApplication.instance()) or QGuiApplication(args)

    warnings: list[str] = []

    def on_qt_message(msg_type: QtMsgType, context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            warnings.append(message)

    qInstallMessageHandler(on_qt_message)

    load_fonts()

    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: warnings.extend(str(error) for error in errors))
    engine.load(QUrl.fromLocalFile(str(MAIN_QML)))

    return app, engine, warnings


def main(argv: list[str] | None = None) -> int:
    """Einstiegspunkt von `python -m gui`. Bricht mit 1 ab, wenn `Main.qml` nicht lädt oder
    eine QML-Warnung auftrat (Regel 13) — sonst startet die Ereignisschleife."""
    app, engine, warnings = build_engine(argv)

    if not engine.rootObjects():
        print(f"{MAIN_QML} wurde nicht geladen.", file=sys.stderr)
        return 1
    if warnings:
        print("QML-Warnungen — Fehlschlag, kein Rauschen:", file=sys.stderr)
        for message in warnings:
            print("  " + message, file=sys.stderr)
        return 1

    return app.exec()
