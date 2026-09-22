"""Rendert eine QML-Datei nach PNG und zaehlt jede Qt-/QML-Warnung als Fehlschlag.

Vorbild: der Renderer aus AP 14 Runde 1/2. Zwei Unterschiede, beide aus der Blur-Sonde
dieser Sitzung: Gerendert wird mit echtem Fenster, weil der Offscreen-Betrieb auf den
Software-Szenengraph faellt und `MultiEffect` dort **still** ausfaellt (weisses Bild,
keine Warnung); mit `--offscreen` laesst sich derselbe Aufruf zum Vergleich in genau
diesen Software-Modus zwingen.

Aufruf:  python shot.py <qml> <png> [--size 1280x800] [--offscreen] [--font-dir DIR]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Die Schriften liegen beim Bestand, nicht beim Mockup: Gerendert wird mit denselben
# Dateien, die die Oberfläche später über `QFontDatabase` lädt — wie beim Theme
# (technik.md §14, „Der Mockup rendert gegen den Bestand").
FONTS = HERE.parent.parent / "gui" / "fonts"


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("qml")
    parser.add_argument("png")
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--offscreen", action="store_true")
    parser.add_argument("--dark", action="store_true")
    # Welcher Datenfall gerendert wird (Content.variant). Ohne Angabe der erste.
    parser.add_argument("--fall", default="")
    parser.add_argument("--font-dir", default=str(FONTS))
    parser.add_argument("--fonts", nargs="*", default=None)
    parser.add_argument("--wait", type=int, default=250)
    args = parser.parse_args()

    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        # Runde 1 (AP 14): offscreen kennt unter Windows sonst keine einzige Schriftfamilie.
        os.environ["QT_QPA_FONTDIR"] = args.font_dir

    from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase, QGuiApplication, QImage
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest

    width, height = (int(part) for part in args.size.split("x"))
    messages: list[str] = []

    def on_message(msg_type: QtMsgType, context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            messages.append(message)

    qInstallMessageHandler(on_message)
    # Die Anwendung muss am Leben bleiben, solange das Fenster steht — ohne eine
    # Referenz sammelt Python sie ein, und Qt stürzt ab. Der Unterstrich sagt, dass
    # sie nur deshalb hier steht.
    _app = QGuiApplication(sys.argv[:1])

    font_dir = Path(args.font_dir)
    wanted = (
        args.fonts
        if args.fonts is not None
        else sorted(str(p.name) for p in font_dir.glob("*.ttf"))
    )
    loaded: list[str] = []
    for name in wanted:
        handle = QFontDatabase.addApplicationFont(str(font_dir / name))
        if handle < 0:
            # Regel 13: -1 ist ein Fehlschlag, keine stille Ersatzschrift.
            print(f"Schrift nicht geladen: {name}", file=sys.stderr)
            return 2
        loaded.extend(QFontDatabase.applicationFontFamilies(handle))

    view = QQuickView()
    view.engine().rootContext().setContextProperty("appDark", args.dark)
    view.engine().rootContext().setContextProperty("appCase", args.fall)
    # Standbilder ohne laufende Animation: sonst fällt der Roboter bei jedem
    # Lauf auf einen anderen Blickwinkel und zwei Bilder sind nicht vergleichbar.
    view.engine().rootContext().setContextProperty("appAnimate", False)
    view.engine().addImportPath(str(Path(args.qml).resolve().parent))
    view.engine().warnings.connect(lambda errors: messages.extend(str(e) for e in errors))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(width, height)
    view.setSource(QUrl.fromLocalFile(str(Path(args.qml).resolve())))
    if view.status() != QQuickView.Status.Ready:
        print("QML nicht geladen:", view.errors(), file=sys.stderr)
        return 2
    view.show()
    if not QTest.qWaitForWindowExposed(view, 5000):
        print("Fenster wurde nicht sichtbar", file=sys.stderr)
        return 2
    QTest.qWait(args.wait)
    image = view.grabWindow()
    if image.isNull() or image.width() != width:
        print(f"grabWindow() lieferte {image.width()}x{image.height()}", file=sys.stderr)
        return 2
    # Untergrenze (Befund B4, Durchsicht b2d5cab): Ein Bildschirm, der gar nichts zeichnet,
    # bestand bis hierher alle drei Prüfungen — „0 Warnungen", „kein Überlauf", „0
    # Textstellen gemessen". Ein einfarbiges Bild ist deshalb selbst ein Fehlschlag; es ist
    # zugleich genau die Form, in der `MultiEffect` im Software-Szenengraph still ausfällt
    # (siehe Modulkopf). Format_RGB32 hat bei jeder hier gerenderten Breite keine
    # Zeilenauffüllung, die Rohbytes sind also vergleichbar.
    flach = image.convertToFormat(QImage.Format.Format_RGB32)
    roh = bytes(flach.constBits())
    if not roh or roh == roh[:4] * (len(roh) // 4):
        print("Bild ist einfarbig — es wurde nichts gezeichnet", file=sys.stderr)
        return 2
    out = Path(args.png)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(out), "PNG"):
        print(f"PNG nicht geschrieben: {out}", file=sys.stderr)
        return 2
    view.hide()
    view.setSource(QUrl())
    del view

    backend = "software" if args.offscreen else "gpu"
    mode = "dunkel" if args.dark else "hell"
    case = args.fall or "-"
    print(
        f"{out}  [{backend}/{mode}/{case}]  {len(messages)} Warnungen  "
        f"Familien: {sorted(set(loaded))}"
    )
    if messages:
        print("Warnungen - Fehlschlag, kein Rauschen:", file=sys.stderr)
        for message in messages:
            print("  " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
