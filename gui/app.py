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
shot.py`: `QT_QPA_FONTDIR` zeigt in diesem Fall auf `gui/fonts/`. Das gilt nur fuer den
Offscreen-Treiber selbst (`QQuickWindow`, `platform theme`) — `QFontDatabase.addApplicationFont`
in `load_fonts` unten ist davon unabhaengig und laeuft in jedem Treiber gleich.

# (Befund B4, Durchsicht d993e3e): Ein leeres `gui/fonts/` lief bisher klaglos durch —
# die Schleife in `load_fonts` fand keine `*.ttf`-Datei und meldete das nicht, die
# Oberflaeche zeigte erst am ersten Text ein Ersatzkaestchen (Tofu) oder unter
# `QT_QPA_PLATFORM=offscreen` sogar gar nichts Auffaelliges. `load_fonts` bricht deshalb
# jetzt ab, wenn keine einzige Schriftfamilie geladen wurde oder eine der beiden von
# `Theme.qml` (`fonts.book`, `fonts.ui`) genannten Familien nicht darunter ist — Regel 13.

# (Befund F7/F9, Nachprüfung d00e7c9): `install_message_handler` unten ist die **eine**
# Stelle, die `qInstallMessageHandler` einrichtet — sowohl für `build_engine` hier als
# auch für den Direktpfad von `tools/gui_screenshot.py` (der bisher gar keinen Handler
# hatte und `console.warn` sowie Qt-eigene Meldungen unbemerkt durchließ, Befund F7).
# Dieselbe Stelle dedupliziert auch (Befund F9): `QQmlApplicationEngine.warnings` und der
# Meldungs-Handler berichten denselben QML-Bindungsfehler manchmal über **beide** Wege —
# am Bestand beobachtet an einer fehlenden Kontexteigenschaft, die als zwei Warnungen
# statt einer gezählt wurde.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

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
    bräche sonst erst beim ersten sichtbaren Textfeld auf, ohne erkennbare Ursache.

    # REGEL (Befund B4, Durchsicht d993e3e): Zwei weitere stille Fehlschläge derselben
    # Familie — ein leeres `font_dir` (keine `*.ttf`-Datei, also auch kein `handle < 0`,
    # die Schleife oben lief einfach klaglos durch) und eine Familie, die `Theme.qml`
    # nennt (`fonts.book`, `fonts.ui`), aber die keine der geladenen Dateien mitbringt —
    # beide brechen hier ab statt eine Ersatzschrift lautlos hinzunehmen."""
    from PySide6.QtGui import QFontDatabase

    families: list[str] = []
    for font_path in sorted(font_dir.glob("*.ttf")):
        handle = QFontDatabase.addApplicationFont(str(font_path))
        if handle < 0:
            raise RuntimeError(f"Schrift nicht geladen: {font_path}")
        families.extend(QFontDatabase.applicationFontFamilies(handle))

    if not families:
        raise RuntimeError(f"Keine Schrift aus {font_dir} geladen (Verzeichnis leer?)")

    fehlend = sorted(name for name in _expected_font_families() if name not in families)
    if fehlend:
        raise RuntimeError(
            f"Theme.fonts nennt {fehlend}, geladen sind nur {sorted(set(families))} aus {font_dir}"
        )
    return families


def _expected_font_families() -> list[str]:
    """`Theme.fonts.book` und `Theme.fonts.ui` (`gui/qml/Theme.qml`) — die einzigen zwei
    Familien, die eine Textstelle dieser Richtung je benennt (dokumentation.md §2,
    „Schriftrolle"). Gelesen wird aus einer eigenen, kurzlebigen `QQmlEngine`, nie aus der
    laufenden Singleton-Instanz: `load_fonts` läuft vor `engine.load(Main.qml)` (Regel
    dieses Moduls, siehe Kopf), zu dem Zeitpunkt existiert noch keine."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlProperty

    probe_engine = QQmlEngine()
    component = QQmlComponent(probe_engine, QUrl.fromLocalFile(str(QML_DIR / "Theme.qml")))
    theme = component.create()
    if theme is None:
        print(f"Theme.qml nicht lesbar: {component.errorString()}", file=sys.stderr)
        return []
    return [
        str(QQmlProperty(theme, "fonts.book").read()),
        str(QQmlProperty(theme, "fonts.ui").read()),
    ]


def install_message_handler(warnings: list[str]) -> Callable[[str], None]:
    """Installiert `qInstallMessageHandler` so, dass jede Qt-/QML-Warnung sofort nach
    stderr geschrieben und an `warnings` angehängt wird (Befund B5, Durchsicht d993e3e).
    Liefert `record(message)` zurück — dieselbe Aufzeichnung, mit der auch
    `QQmlApplicationEngine.warnings` seine Fehler einträgt (Befund F9, Nachprüfung
    d00e7c9): Beide Wege können denselben QML-Bindungsfehler melden; `record` verwirft
    einen Text, der in diesem Aufbau schon einmal vorkam, statt ihn doppelt zu zählen.

    Eine Stelle für beide Aufrufer (Befund F7): `build_engine` unten **und** der
    Direktpfad von `tools/gui_screenshot.py` (`--qml-dir` außerhalb von `gui/qml/`) rufen
    diese Funktion, statt je einen eigenen Handler zu schreiben."""
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    gesehen: set[str] = set()

    def record(message: str) -> None:
        if message in gesehen:
            return
        gesehen.add(message)
        warnings.append(message)
        # REGEL (Befund B5, Durchsicht d993e3e): main() liest `warnings` nur ein einziges
        # Mal, bevor `app.exec()` startet — jede Warnung, die erst während der
        # Ereignisschleife auftritt, verschwand bisher spurlos, auch von stderr. Die
        # Zusicherung „QML-Warnungen gehen nach stderr" gilt deshalb hier, sofort bei
        # jeder Meldung, nicht erst über die Liste weiter unten.
        print(message, file=sys.stderr)

    def on_qt_message(msg_type: QtMsgType, context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            record(message)

    qInstallMessageHandler(on_qt_message)
    return record


def build_engine(
    argv: list[str] | None = None,
    *,
    font_dir: Path = FONTS_DIR,
    context_properties: dict[str, object] | None = None,
) -> tuple[QGuiApplication, QQmlApplicationEngine, list[str]]:
    """Baut Anwendung, Schriften und Engine auf und lädt `Main.qml` — ohne `app.exec()`.

    Getrennt von `main()`, damit ein Test das Ergebnis (Warnungen, geladene Wurzelobjekte)
    prüfen kann, ohne eine echte Ereignisschleife laufen zu lassen. `context_properties`
    ist für `tools/gui_screenshot.py` da (bauplan-phase2.md, Befund B6, Durchsicht
    d993e3e): Das Werkzeug rendert seither über **diese** Aufbaufunktion statt über einen
    zweiten, eigenen Aufbau — Fenster, Loader und Mindestgröße aus `Main.qml` laufen damit
    tatsächlich durch die Prüfung. Die Kontexteigenschaften (`appDark`, `appCase`,
    `appAnimate`) müssen **vor** `engine.load` gesetzt sein, wie beim Mockup-Vorbild."""
    from typing import cast

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from gui.workers import wait_for_active_workers

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
    bestehende = cast("QGuiApplication | None", QGuiApplication.instance())
    app = bestehende or QGuiApplication(args)
    if bestehende is None:
        # (Befund F13, Nachprüfung d00e7c9): nur beim ersten Aufbau in diesem Prozess
        # verbinden — ein zweiter `build_engine`-Aufruf auf derselben `QGuiApplication`
        # (wie in mehreren Tests) hinge sonst denselben Rückruf mehrfach ein.
        app.aboutToQuit.connect(lambda: wait_for_active_workers())

    warnings: list[str] = []
    record = install_message_handler(warnings)

    load_fonts(font_dir)

    engine = QQmlApplicationEngine()

    def on_engine_warnings(errors: list[object]) -> None:
        for error in errors:
            record(str(error))

    engine.warnings.connect(on_engine_warnings)

    for name, value in (context_properties or {}).items():
        engine.rootContext().setContextProperty(name, value)

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
