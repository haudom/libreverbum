"""Sucht den stillen Layoutfehlschlag: Überlauf und abgeschnittenen Text.

Warum es dieses Skript gibt: „0 QML-Warnungen" beweist nichts. Qt meldet keinen
Layoutüberlauf — in Runde 1 lief der Belegsatz bei 900×600 unter die Tastenleiste und über
den Fensterrand hinaus, während `shot.py` null Warnungen meldete (review_round1.md B1/B2).
Genau dieser Fall wird hier gesucht, und zwar am geladenen Objektbaum, nicht am Bild:

1. **Überlauf** — ein Kindelement, dessen Rechteck aus dem Elternelement herausragt. Nur
   gemeldet, wo das Elternelement nicht `clip` setzt (dort ist Abschneiden gewollt) …
2. … dafür wird bei `clip`-Flächen **geprüft, ob tatsächlich etwas abgeschnitten wird** —
   das ist der gefährlichere Fall, weil das Bild dann ordentlich aussieht und trotzdem
   Text fehlt.
3. **Beschnittener Text** — ein `Text`, dessen `implicitHeight` größer ist als seine Höhe
   oder dessen `truncated` gesetzt ist (Kürzung durch `elide`). Regel 1: nichts fällt weg.
4. **Untergrenze** — wurde überhaupt ein `Text` angesehen? Ohne sie bestand ein Bildschirm
   ohne eine einzige Textstelle diese Prüfung (Befund B4, Durchsicht b2d5cab).

Aufruf:  python layout_check.py <qml> [--size 1280x800] [--dark] [--fall NAME]
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

# Text, der gekürzt werden **darf**: Buch- und Kapiteltitel in der Kopfzeile und die
# Wortform in einer Listenzeile sind Namen, keine Aussagen — sie stehen vollständig an
# ihrem eigentlichen Ort. Jede andere Kürzung ist ein Befund.
ELIDE_ERLAUBT = {"bookLine", "listTitle", "wordCell", "chapterCell", "stageLabel"}


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("qml")
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--fall", default="")
    parser.add_argument("--font-dir", default=str(FONTS))
    args = parser.parse_args()

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase, QGuiApplication
    from PySide6.QtQuick import QQuickItem, QQuickView
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
    view.engine().rootContext().setContextProperty("appAnimate", False)
    view.engine().addImportPath(str(Path(args.qml).resolve().parent))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(width, height)
    view.setSource(QUrl.fromLocalFile(str(Path(args.qml).resolve())))
    if view.status() != QQuickView.Status.Ready:
        print("QML nicht geladen:", view.errors(), file=sys.stderr)
        return 2
    view.show()
    QTest.qWaitForWindowExposed(view, 5000)
    QTest.qWait(300)

    findings: list[str] = []
    # Untergrenze (Befund B4, Durchsicht b2d5cab): Ein Bildschirm ohne eine einzige
    # Textstelle meldete hier „kein Überlauf, keine Kürzung" — die beiden Textprüfungen
    # unten liefen dann über nichts. Gezählt wird deshalb mit, wie viele `Text` überhaupt
    # angesehen wurden; null ist ein Fehlschlag und keine saubere Seite.
    texte = 0

    def describe(item: QQuickItem) -> str:
        name = item.objectName() or type(item).__name__
        return f"{name} ({item.width():.0f}×{item.height():.0f} bei {item.x():.0f},{item.y():.0f})"

    def walk(item: QQuickItem, path: str) -> None:
        nonlocal texte
        for child in item.childItems():
            if not child.isVisible() or (child.width() == 0 and child.height() == 0):
                continue
            here = f"{path} › {describe(child)}"

            # Der Inhalt einer ListView ragt naturgemäß aus ihr heraus — das ist der
            # Bildlauf selbst und kein Befund. Der Fokusring liegt absichtlich außen.
            if item.metaObject().className() in (
                "QQuickListView",
                "QQuickFlickable",
            ) or child.objectName() in ("focusRing", "listContent"):
                walk(child, here)
                continue

            over_right = child.x() + child.width() - item.width()
            over_bottom = child.y() + child.height() - item.height()
            over_left = -child.x()
            over_top = -child.y()
            worst = max(over_right, over_bottom, over_left, over_top)
            # Ein Fokusring liegt absichtlich außen; 4 px sind seine Einrückung.
            tolerated = 0.5
            if worst > tolerated:
                seiten = []
                if over_right > tolerated:
                    seiten.append(f"rechts {over_right:.0f}")
                if over_bottom > tolerated:
                    seiten.append(f"unten {over_bottom:.0f}")
                if over_left > tolerated:
                    seiten.append(f"links {over_left:.0f}")
                if over_top > tolerated:
                    seiten.append(f"oben {over_top:.0f}")
                art = "ABGESCHNITTEN" if item.clip() else "ÜBERLAUF"
                findings.append(f"{art} {' / '.join(seiten)} px: {here}")

            # Siehe contrast_check.py: `type(child).__name__` ist bei PySide immer
            # `QQuickItem`, der Metaobjektname ist die Wahrheit. Mit dem alten
            # Vergleich waren die beiden Textprüfungen unten tot.
            if child.metaObject().className() == "QQuickText":
                texte += 1
                name = child.objectName()
                implicit = child.property("implicitHeight")
                if implicit is not None and implicit - child.height() > 1:
                    findings.append(
                        f"TEXT ZU HOCH um {implicit - child.height():.0f} px "
                        f"(braucht {implicit:.0f}, hat {child.height():.0f}): {here}"
                    )
                if child.property("truncated") and name not in ELIDE_ERLAUBT:
                    findings.append(f"TEXT GEKÜRZT (elide/truncated): {here}")

            walk(child, here)

    root = view.rootObject()
    walk(root, describe(root))

    label = f"{Path(args.qml).stem} {args.size} {'dunkel' if args.dark else 'hell'}"
    if args.fall:
        label += f" [{args.fall}]"
    if findings:
        print(f"{label}: {len(findings)} Befunde")
        for finding in findings:
            print("  " + finding)
        return 1
    if not texte:
        print(f"{label}: kein einziger `Text` im Objektbaum — hier wurde nichts geprüft")
        return 2
    print(f"{label}: kein Überlauf, keine Kürzung ({texte} Textstellen angesehen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
