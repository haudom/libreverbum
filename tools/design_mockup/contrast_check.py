"""Misst den Kontrast **im gerenderten Bild** an jeder echten Textstelle.

Warum nicht aus den Token gerechnet wird: `kontrast.py` aus Runde 1 hat die Tokenwerte
übereinandergelegt und „0 Paare unter 4,5:1" gemeldet, während im Bild 2,41:1 stand — es
kannte die `opacity:`-Faktoren, die getönten Füllungen und den Glanzstreifen nicht
(review_round1.md B3). Ein Prüfwerkzeug, das falsches Grün liefert, ist schlimmer als
keines.

Deshalb hier der umgekehrte Weg, und zwar ohne Handarbeit: Der Bildschirm wird geladen,
gerendert, und dann wird **der Objektbaum nach jedem sichtbaren `Text` abgesucht**. Für
jeden wird sein Rechteck in Bildkoordinaten umgerechnet und darin gemessen:

* **Hintergrund** = die häufigste Farbe des Rechtecks (Text bedeckt nie die Mehrheit),
* **Vordergrund** = der extremste Pixel in der Gegenrichtung, also der Kern eines Glyphen.
  Die Kantenpixel der Glättung liegen dazwischen und sind nicht die Farbe, die WCAG meint.

Der Unterschied zu einer Liste von Hand abgelesener Rechtecke: Ein Text, den jemand
vergisst einzutragen, wird hier trotzdem gemessen. Vergessen ist der Normalfall.

Schwelle: 4,5:1. Ein Text ab 24 px (oder ab 18,66 px halbfett) darf nach WCAG 2.1 auf
3,0:1 — das wird ausgewiesen, aber nicht als Freibrief verrechnet: gemeldet wird beides.

Aufruf:  python contrast_check.py <qml> [--size 1280x800] [--dark] [--fall NAME] [--alle]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Die Schriften liegen beim Bestand, nicht beim Mockup: Gerendert wird mit denselben
# Dateien, die die Oberfläche später über `QFontDatabase` lädt — wie beim Theme
# (technik.md §14, „Der Mockup rendert gegen den Bestand").
FONTS = HERE.parent.parent / "gui" / "fonts"

# Stellen, an denen kein Text steht, den ein Mensch liest: die Tastenkappe des Roboters
# gibt es nicht, wohl aber Zeichnungen, die als `Text` gebaut sein könnten. Bleibt leer,
# solange keine dazukommt — eine Ausnahmeliste, die wächst, ist eine Ausrede.
AUSNAHMEN: set[str] = set()


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


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
    parser.add_argument(
        "--alle", action="store_true", help="jede Messung ausgeben, nicht nur Befunde"
    )
    parser.add_argument("--font-dir", default=str(FONTS))
    args = parser.parse_args()

    from PySide6.QtCore import QPointF, QRectF, QUrl
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
    image = view.grabWindow()

    # (Textelement, sichtbares Rechteck in Bildkoordinaten)
    texte: list[tuple[object, float, float, float, float]] = []
    verblasst: list[str] = []
    verdeckt = 0

    def walk(item: QQuickItem, clip: QRectF) -> None:
        nonlocal verdeckt
        for child in item.childItems():
            if not child.isVisible():
                continue
            oben_links = child.mapToScene(QPointF(0, 0))
            rechteck = QRectF(oben_links.x(), oben_links.y(), child.width(), child.height())
            # Ein Element, das in einer rollenden Liste gerade aus dem Ausschnitt gerollt
            # ist, ist `visible` — aber im Bild steht dort nichts. Ohne diese Rechnung
            # misst das Werkzeug dort Grund gegen Grund, meldet 1,00:1 und behauptet einen
            # Befund, den es nicht gibt. Der Ausschnitt wird deshalb mitgeführt: Jede
            # Fläche mit `clip` verkleinert ihn.
            sichtbar = rechteck.intersected(clip)
            innen = clip.intersected(rechteck) if child.clip() else clip

            # NICHT `type(child).__name__`: PySide reicht die Kinder als `QQuickItem`
            # heraus und stuft sie nicht auf die konkrete C++-Klasse herunter. Der Name
            # traf deshalb **nie** zu — das Werkzeug meldete „0 Textstellen, 0 unter der
            # Schwelle", und der Lauf sah grün aus. Das ist derselbe Fehlschlag wie B3,
            # nur eine Runde später und im eigenen Prüfwerkzeug. Der Metaobjektname
            # stammt aus der C++-Seite und stimmt.
            if child.metaObject().className() == "QQuickText" and child.width() > 0:
                if sichtbar.width() < 2 or sichtbar.height() < 2:
                    verdeckt += 1
                else:
                    # `opacity` auf Text ist in dieser Richtung verboten: Genau daran ist
                    # Runde 1 gescheitert (B3). Das Messen im Bild deckte es zwar auch
                    # auf, aber erst als Kontrastzahl — hier wird die Ursache benannt.
                    if child.opacity() < 0.999:
                        verblasst.append(
                            f"{str(child.property('text') or '')[:40]!r} "
                            f"(opacity {child.opacity():.2f})"
                        )
                    ganz = (
                        sichtbar.width() >= rechteck.width() - 0.5
                        and sichtbar.height() >= rechteck.height() - 0.5
                    )
                    texte.append(
                        (
                            child,
                            sichtbar.x(),
                            sichtbar.y(),
                            sichtbar.width(),
                            sichtbar.height(),
                            ganz,
                        )
                    )
            walk(child, innen)

    wurzel = view.rootObject()
    walk(wurzel, QRectF(0, 0, wurzel.width(), wurzel.height()))

    zeilen = []
    angeschnitten = 0
    schlechtester = None
    for item, x, y, w, h, ganz in texte:
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(image.width(), int(x + w)), min(image.height(), int(y + h))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        pixel = []
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                c = image.pixelColor(xx, yy)
                pixel.append((c.red(), c.green(), c.blue()))
        if not pixel:
            continue
        haeufig = Counter(pixel)
        hintergrund = haeufig.most_common(1)[0][0]
        anteil = haeufig.most_common(1)[0][1] / len(pixel)
        if anteil > 0.985:
            # Im sichtbaren Teil steht kein Glyph. Bei einer **angeschnittenen** Zeile am
            # Rand einer rollenden Liste ist das der Normalfall — dort ragt nur der
            # Leerraum über dem Text herein. Steht das Element dagegen **vollständig** im
            # Ausschnitt und enthält trotzdem nur eine Farbe, ist es unsichtbar: Das ist
            # ein Befund und keine Randerscheinung.
            if ganz:
                zeilen.append(
                    (
                        1.0,
                        4.5,
                        item.property("font").pixelSize(),
                        "UNSICHTBAR: " + str(item.property("text") or "")[:34],
                        hintergrund,
                        hintergrund,
                        False,
                    )
                )
            else:
                angeschnitten += 1
            continue
        # Kein klarer Grund im Rechteck (etwa ein Text, der über einer Kante sitzt).
        # Das ist selbst ein Befund und wird als solcher ausgewiesen.
        grund_unklar = anteil < 0.30
        # Der Vordergrund ist der Pixel, der sich am **weitesten** vom Grund entfernt —
        # in welche Richtung, entscheidet das Bild und nicht das Thema. „Dunkles Thema
        # heißt helle Schrift" war die Annahme davor, und sie fällt genau dort um, wo sie
        # zählt: Auf der gefüllten Schaltfläche steht dunkle Schrift auf hellem Orange,
        # mitten im dunklen Thema. Gemessen wurden dann Füllung gegen Füllung, 1,00:1,
        # ein Befund, den es nicht gibt — ein Prüfwerkzeug, das falsches **Rot** liefert.
        grund_lum = relative_luminance(hintergrund)
        vordergrund = max(pixel, key=lambda p: abs(relative_luminance(p) - grund_lum))
        verhaeltnis = contrast(vordergrund, hintergrund)
        groesse = item.property("font").pixelSize()
        fett = item.property("font").weight() >= 600
        grenze = 3.0 if (groesse >= 24 or (groesse >= 19 and fett)) else 4.5
        text = str(item.property("text") or "")[:46].replace("\n", " ")
        zeilen.append((verhaeltnis, grenze, groesse, text, vordergrund, hintergrund, grund_unklar))
        if schlechtester is None or verhaeltnis < schlechtester[0]:
            schlechtester = (verhaeltnis, text, groesse, vordergrund, hintergrund)

    zeilen.sort(key=lambda z: z[0])
    befunde = [z for z in zeilen if z[0] < z[1]]

    kopf = (
        f"{Path(args.qml).stem} {args.size} {'dunkel' if args.dark else 'hell'}"
        f"{' [' + args.fall + ']' if args.fall else ''}"
    )
    print(
        f"{kopf}: {len(zeilen)} Textstellen gemessen, {len(befunde)} unter der Schwelle"
        f"{f', {verdeckt} ausserhalb des Ausschnitts' if verdeckt else ''}"
        f"{f', {angeschnitten} angeschnitten' if angeschnitten else ''}"
    )
    for verhaeltnis, grenze, groesse, text, fg, bg, unklar in zeilen if args.alle else befunde:
        marke = "!" if verhaeltnis < grenze else " "
        note = "  (Grund uneindeutig)" if unklar else ""
        print(
            f" {marke} {verhaeltnis:5.2f}:1  Soll {grenze}  {groesse:2d}px  "
            f"#{fg[0]:02x}{fg[1]:02x}{fg[2]:02x} auf #{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}  "
            f"{text!r}{note}"
        )
    for eintrag in verblasst:
        print(f" ! `opacity` auf Text — in dieser Richtung verboten (B3): {eintrag}")
    if schlechtester:
        print(
            f"   schlechtestes Paar: {schlechtester[0]:.2f}:1  {schlechtester[2]}px  "
            f"{schlechtester[1]!r}"
        )
    return 1 if (befunde or verblasst) else 0


if __name__ == "__main__":
    raise SystemExit(main())
