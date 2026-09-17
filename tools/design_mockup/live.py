"""Zeigt einen Entwurfsbildschirm in einem echten Fenster — mit laufenden Animationen.

Ein Standbild sagt nicht, ob sich eine Bewegung gut anfühlt. Dieses Skript ist deshalb die
zweite Hälfte der Schleife: `shot.py` friert ein, `live.py` lässt laufen. Beim Roboter ist
das keine Formalie — die drei Bewegungen (Umsehen 8 s, Atmen 3,4 s, Blinzeln 5,2 s) sind
gerade deshalb so gewählt, dass sie sich **nicht** zu einem Takt zusammenfinden, und das
sieht man nur bewegt.

Im Fenster: Leertaste wechselt den Bildschirm, Esc schließt. Hell/dunkel wird beim Start
gewählt (`--dark`) — eine Kontexteigenschaft lässt sich aus QML nicht umsetzen, eine Taste
dafür hätte still nichts getan.

Aufruf:  python live.py [Progress|Triage|Setup|Chapters] [--dark] [--fall NAME]
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Die Schriften liegen beim Bestand, nicht beim Mockup: Gerendert wird mit denselben
# Dateien, die die Oberfläche später über `QFontDatabase` lädt — wie beim Theme
# (technik.md §14, „Der Mockup rendert gegen den Bestand").
FONTS = HERE.parent.parent / "gui" / "fonts"
SCREENS = ["Progress", "Triage", "Setup", "Chapters"]

SHELL = """
import QtQuick

Item {{
    id: shell
    width: 1280; height: 800
    focus: true

    property int index: {index}

    readonly property string screenName: {screens}[index]

    Loader {{
        id: loader
        anchors.fill: parent
        source: "qml/" + shell.screenName + ".qml"
    }}

    Keys.onPressed: function (event) {{
        if (event.key === Qt.Key_Escape) {{
            Qt.quit()
        }} else if (event.key === Qt.Key_Space) {{
            shell.index = (shell.index + 1) % {count}
        }}
        event.accepted = true
    }}
}}
"""


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase, QGuiApplication
    from PySide6.QtQuick import QQuickView

    argumente = [a for a in sys.argv[1:] if not a.startswith("--")]
    dark = "--dark" in sys.argv
    fall = ""
    if "--fall" in sys.argv:
        fall = sys.argv[sys.argv.index("--fall") + 1]
        argumente = [a for a in argumente if a != fall]
    name = argumente[0] if argumente else "Progress"
    if name not in SCREENS:
        print(f"Unbekannter Bildschirm {name!r}; bekannt: {', '.join(SCREENS)}")
        return 2

    def on_message(msg_type: QtMsgType, context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            print("QML-Warnung:", message, file=sys.stderr)

    qInstallMessageHandler(on_message)
    app = QGuiApplication(sys.argv[:1])

    for font in sorted(FONTS.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(font)) < 0:
            # Regel 13: -1 ist ein Fehlschlag, keine stille Ersatzschrift.
            print(f"Schrift nicht geladen: {font}", file=sys.stderr)
            return 2

    shell_path = HERE / "_live_shell.qml"
    shell_path.write_text(
        SHELL.format(
            index=SCREENS.index(name), screens=str(SCREENS).replace("'", '"'), count=len(SCREENS)
        ),
        encoding="utf-8",
    )

    view = QQuickView()
    view.rootContext().setContextProperty("appDark", dark)
    view.rootContext().setContextProperty("appCase", fall)
    view.rootContext().setContextProperty("appAnimate", True)
    view.engine().addImportPath(str(HERE / "qml"))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1280, 800)
    view.setTitle("LibreVerbum — Entwurf „Lesetisch“ (Leertaste = Bildschirm, Esc = schließen)")
    view.setSource(QUrl.fromLocalFile(str(shell_path)))
    if view.status() != QQuickView.Status.Ready:
        print("QML nicht geladen:", view.errors(), file=sys.stderr)
        return 2
    view.show()
    if "--selbsttest" in sys.argv:
        # Für den Lauf ohne Mensch davor: zeigt, dass das Fenster aufgeht und die
        # Animationen anlaufen, und schließt wieder.
        from PySide6.QtCore import QTimer

        QTimer.singleShot(2500, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
