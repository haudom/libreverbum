"""Greift Einzelbilder aus der **laufenden** Animation und legt sie nebeneinander.

`shot.py` friert die Animation ein (`appAnimate: false`), damit zwei Läufe dasselbe Bild
ergeben. Genau deshalb sagt es nichts darüber, ob eine Bewegung sich gut anfühlt — und die
Roboterdrehung aus Runde 1 ist nicht am Standbild gescheitert, sondern an der dritten
Minute (B18). `live.py` zeigt die Bewegung einem Menschen; dieses Skript macht sie
**nachprüfbar**: Es lässt laufen, greift in festen Abständen zu und legt die Bilder in
einen Streifen. Am Streifen ist abzulesen, ob die Bewegung durchgehend ein Gesicht zeigt,
wo sie hält und ob sich die Phasen wiederholen.

Aufruf:  python motion_strip.py <qml> <png> [--bilder 8] [--abstand 900] [--dark]
         [--ausschnitt x,y,b,h]
"""

from __future__ import annotations

import argparse
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
    parser.add_argument("--bilder", type=int, default=8)
    parser.add_argument(
        "--abstand", type=int, default=900, help="Millisekunden zwischen den Bildern"
    )
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--fall", default="anfang")
    parser.add_argument("--ausschnitt", default="", help="x,y,b,h — sonst das ganze Fenster")
    parser.add_argument("--font-dir", default=str(FONTS))
    args = parser.parse_args()

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase, QGuiApplication, QImage, QPainter
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest

    width, height = (int(part) for part in args.size.split("x"))
    # Die Anwendung muss am Leben bleiben, solange das Fenster steht — ohne eine
    # Referenz sammelt Python sie ein, und Qt stürzt ab. Der Unterstrich sagt, dass
    # sie nur deshalb hier steht.
    _app = QGuiApplication(sys.argv[:1])
    for font in sorted(Path(args.font_dir).glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(font)) < 0:
            print(f"Schrift nicht geladen: {font}", file=sys.stderr)
            return 2

    view = QQuickView()
    view.engine().rootContext().setContextProperty("appDark", args.dark)
    view.engine().rootContext().setContextProperty("appCase", args.fall)
    # Der ganze Zweck dieses Skripts: die Animationen laufen.
    view.engine().rootContext().setContextProperty("appAnimate", True)
    view.engine().addImportPath(str(Path(args.qml).resolve().parent))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(width, height)
    view.setSource(QUrl.fromLocalFile(str(Path(args.qml).resolve())))
    if view.status() != QQuickView.Status.Ready:
        print("QML nicht geladen:", view.errors(), file=sys.stderr)
        return 2
    view.show()
    QTest.qWaitForWindowExposed(view, 5000)
    QTest.qWait(200)

    bilder = []
    for _ in range(args.bilder):
        QTest.qWait(args.abstand)
        bild = view.grabWindow()
        if args.ausschnitt:
            x, y, b, h = (int(t) for t in args.ausschnitt.split(","))
            bild = bild.copy(x, y, b, h)
        bilder.append(bild)

    einzel_b, einzel_h = bilder[0].width(), bilder[0].height()
    streifen = QImage(einzel_b * len(bilder), einzel_h, QImage.Format.Format_RGB32)
    maler = QPainter(streifen)
    for index, bild in enumerate(bilder):
        maler.drawImage(index * einzel_b, 0, bild)
    maler.end()

    ziel = Path(args.png)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if not streifen.save(str(ziel), "PNG"):
        print(f"PNG nicht geschrieben: {ziel}", file=sys.stderr)
        return 2
    gesamt = args.bilder * args.abstand / 1000
    print(
        f"{ziel}  {len(bilder)} Bilder im Abstand {args.abstand} ms "
        f"({gesamt:.1f} s), je {einzel_b}×{einzel_h}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
