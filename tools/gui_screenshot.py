"""Screenshot-Prüfschleife der Oberfläche — der Nachfolger von `tools/design_mockup/`
(bauplan-phase2.md AP 15, Nachtrag 17.09.2026).

Hintergrund
-----------
„0 QML-Warnungen" beweist nichts, und aus den Token gerechneter Kontrast liefert falsches
Grün — beides an der Gestaltungsrichtung „Lesetisch" selbst nachgemessen. Die eine gültige
Fassung der Begründung steht in technik.md §14, „Gemessen wird im Bild, nicht aus den
Token"; hier wird sie nicht nacherzählt. Vorbild und Vorlage sind `tools/design_mockup/
shot.py`, `layout_check.py` und `contrast_check.py` — sie bleiben dort, bis dieses Skript
ihre Arbeit vollständig übernommen hat.

Verfahren
---------
Vier Schritte gegen **eine** Rendering, nicht drei getrennte Prozesse wie im Vorbild:

1. **rendern** — Schriften laden, `<screen>.qml` aus `gui/qml/` laden, zeigen, warten,
   `QQuickWindow.grabWindow()`, als PNG schreiben.
2. **Warnungen zählen** — über `QQmlEngine.warnings` **und** `qInstallMessageHandler`
   (Durchsicht 907ab02, Befund 1: Ersteres sieht nur, was die QML-Maschine selbst als
   `QQmlError` einstuft; `console.warn` und Qt-eigene Meldungen laufen nur über den
   Meldungs-Handler).
3. **Layout prüfen** — der Objektbaum auf Überlauf, tatsächliches Abschneiden und
   gekürzten Text, wie `layout_check.py`.
4. **Kontrast messen** — im gerenderten Bild an jeder sichtbaren Textstelle, wie
   `contrast_check.py`.

Jeder der letzten drei Schritte meldet zusätzlich, wenn er **nichts** angesehen hat (Befund
B4, Durchsicht `b2d5cab`): ein einfarbiges Bild, kein `Text` im Objektbaum, keine gemessene
Textstelle gelten als eigener Fehlschlag, nicht als sauberes Ergebnis.

Aufruf
------
    python tools/gui_screenshot.py <screen> <png> [--size 1280x800] [--dark]
        [--offscreen] [--fall NAME] [--font-dir DIR] [--wait MS]

`<screen>` ist der Dateiname ohne Endung unter `gui/qml/` — für AP 15 also `Placeholder`.
`--dark` setzt `Theme.dark` über die Kontexteigenschaft `appDark`, wie im Vorbild. Ohne
`--offscreen` braucht der Lauf ein echtes Fenstersystem; mit `--offscreen` fällt Qt Quick
auf den Software-Renderer zurück (dieselbe Einschränkung wie im Vorbild — `MultiEffect`
fiele dort still aus, dieser Bildschirm nutzt es heute nicht).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtQuick import QQuickItem, QQuickView

REPO = Path(__file__).resolve().parent.parent
GUI_QML = REPO / "gui" / "qml"
FONTS = REPO / "gui" / "fonts"

# Text, der gekürzt werden darf, weil er ein Name und keine Aussage ist (wie
# tools/design_mockup/layout_check.py, ELIDE_ERLAUBT). Heute leer: Kein Delegat dieses
# Bestands kürzt Text — Platz für die künftigen Bildschirme ab AP 16a.
ELIDE_ERLAUBT: set[str] = set()

# Textstellen ohne Aussagekraft für die Kontrastmessung (wie contrast_check.py,
# AUSNAHMEN). Bleibt leer, solange keine dazukommt — eine Ausnahmeliste, die wächst, ist
# eine Ausrede.
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


def resolve_screen(name: str, qml_dir: Path = GUI_QML) -> Path:
    """`<qml_dir>/<name>.qml` — die einzige Stelle, an der ein Bildschirmname zu einer
    Datei wird, damit sie sich nicht in `Main.qml` und hier auseinander entwickeln können.

    `qml_dir` ist für `tests/test_gui_screenshot.py` da: Die Verfälschungsproben brauchen
    einen absichtlich leeren beziehungsweise falsch gebundenen Bildschirm, ohne `gui/qml/`
    dafür zu verschmutzen — Vorgabe bleibt der echte Bestand."""
    path = qml_dir / f"{name}.qml"
    if not path.is_file():
        raise SystemExit(f"Unbekannter Bildschirm: {path} nicht gefunden")
    return path


def render(
    qml_path: Path,
    *,
    width: int,
    height: int,
    dark: bool,
    fall: str,
    offscreen: bool,
    font_dir: Path,
    wait_ms: int,
) -> tuple[int, list[str], QQuickView | None, object]:
    """Schritt 1 und 2: laden, zeigen, Bild greifen, jede QML-/Qt-Warnung als Fehlschlag.

    Liefert `(code, warnings, view, image)`; `view` bleibt `None` bei einem Fehlschlag vor
    dem Laden. `code` ist 0 bei Erfolg, 2 bei einem Fehlschlag, der nichts zum Prüfen
    übrig lässt (kein Bild, falsches Format, einfarbig — Untergrenze aus Befund B4)."""
    if offscreen:
        import os

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        # Ohne diese Zeile kennt der Offscreen-Treiber unter Windows keine einzige
        # Schriftfamilie (am Bestand gemessen, siehe gui/app.py, Modulkopf „Regeln").
        os.environ["QT_QPA_FONTDIR"] = str(font_dir)

    from PySide6.QtCore import QtMsgType, QUrl, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase, QGuiApplication, QImage
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest

    messages: list[str] = []

    def on_message(msg_type: QtMsgType, context: object, message: str) -> None:
        del context
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            messages.append(message)

    qInstallMessageHandler(on_message)

    # Referenz halten (Abschnitt 8 des Bauplans): Ohne sie räumt Python die Anwendung weg,
    # solange das Fenster noch lebt.
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    del app

    for font_path in sorted(font_dir.glob("*.ttf")):
        handle = QFontDatabase.addApplicationFont(str(font_path))
        if handle < 0:
            print(f"Schrift nicht geladen: {font_path}", file=sys.stderr)
            return 2, messages, None, None

    view = QQuickView()
    view.engine().rootContext().setContextProperty("appDark", dark)
    view.engine().rootContext().setContextProperty("appCase", fall)
    view.engine().rootContext().setContextProperty("appAnimate", False)
    view.engine().addImportPath(str(qml_path.parent))
    view.engine().warnings.connect(lambda errors: messages.extend(str(e) for e in errors))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(width, height)
    view.setSource(QUrl.fromLocalFile(str(qml_path)))
    if view.status() != QQuickView.Status.Ready:
        print(f"QML nicht geladen: {view.errors()}", file=sys.stderr)
        return 2, messages, None, None

    view.show()
    if not QTest.qWaitForWindowExposed(view, 5000):
        print("Fenster wurde nicht sichtbar", file=sys.stderr)
        return 2, messages, view, None
    QTest.qWait(wait_ms)
    image = view.grabWindow()
    if image.isNull() or image.width() != width:
        print(f"grabWindow() lieferte {image.width()}x{image.height()}", file=sys.stderr)
        return 2, messages, view, None

    # Untergrenze (Befund B4, Durchsicht b2d5cab): Ein Bildschirm, der gar nichts
    # zeichnet, bestände sonst jede Prüfung unten mit „0 Warnungen, 0 Befunde".
    flach = image.convertToFormat(QImage.Format.Format_RGB32)
    roh = bytes(flach.constBits())
    if not roh or roh == roh[:4] * (len(roh) // 4):
        print("Bild ist einfarbig — es wurde nichts gezeichnet", file=sys.stderr)
        return 2, messages, view, image

    return 0, messages, view, image


def check_layout(root: QQuickItem) -> tuple[int, list[str], int]:
    """Schritt 3: Überlauf, tatsächliches Abschneiden und gekürzter Text im Objektbaum —
    wie `tools/design_mockup/layout_check.py`. Liefert `(code, befunde, angesehene_texte)`;
    `code` ist 2, wenn kein einziger `Text` angesehen wurde (Untergrenze, Befund B4)."""
    findings: list[str] = []
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

            # Der Inhalt einer ListView/Flickable ragt naturgemäß aus ihr heraus — das ist
            # der Bildlauf selbst, kein Befund (wie im Vorbild).
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

    walk(root, describe(root))

    if not texte:
        return 2, findings, texte
    return (1 if findings else 0), findings, texte


def check_contrast(root: QQuickItem, image: object) -> tuple[int, list[str], int]:
    """Schritt 4: Kontrast im gerenderten Bild an jeder sichtbaren Textstelle — wie
    `tools/design_mockup/contrast_check.py`. Liefert `(code, zeilen, gemessene_texte)`;
    `code` ist 2, wenn keine einzige Textstelle gemessen wurde (Untergrenze, Befund B4)."""
    from PySide6.QtCore import QPointF, QRectF

    texte: list[tuple[object, float, float, float, float, bool]] = []
    verblasst: list[str] = []

    def walk(item: QQuickItem, clip: QRectF) -> None:
        for child in item.childItems():
            if not child.isVisible():
                continue
            oben_links = child.mapToScene(QPointF(0, 0))
            rechteck = QRectF(oben_links.x(), oben_links.y(), child.width(), child.height())
            sichtbar = rechteck.intersected(clip)
            innen = clip.intersected(rechteck) if child.clip() else clip

            if (
                child.metaObject().className() == "QQuickText"
                and child.width() > 0
                and child.objectName() not in AUSNAHMEN
                and sichtbar.width() >= 2
                and sichtbar.height() >= 2
            ):
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
                    (child, sichtbar.x(), sichtbar.y(), sichtbar.width(), sichtbar.height(), ganz)
                )
            walk(child, innen)

    walk(root, QRectF(0, 0, root.width(), root.height()))

    zeilen: list[str] = []
    schlechtester: tuple[float, str] | None = None
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
        text = str(item.property("text") or "")[:46].replace("\n", " ")
        if anteil > 0.985:
            if ganz:
                zeilen.append(f"! UNSICHTBAR: {text!r}")
            continue
        grund_lum = relative_luminance(hintergrund)
        vordergrund = max(pixel, key=lambda p: abs(relative_luminance(p) - grund_lum))
        verhaeltnis = contrast(vordergrund, hintergrund)
        groesse = item.property("font").pixelSize()
        fett = item.property("font").weight() >= 600
        grenze = 3.0 if (groesse >= 24 or (groesse >= 19 and fett)) else 4.5
        marke = "!" if verhaeltnis < grenze else " "
        zeilen.append(
            f"{marke} {verhaeltnis:5.2f}:1 Soll {grenze} {groesse:.0f}px "
            f"#{vordergrund[0]:02x}{vordergrund[1]:02x}{vordergrund[2]:02x} auf "
            f"#{hintergrund[0]:02x}{hintergrund[1]:02x}{hintergrund[2]:02x} {text!r}"
        )
        if verhaeltnis < grenze and (schlechtester is None or verhaeltnis < schlechtester[0]):
            schlechtester = (verhaeltnis, text)

    for eintrag in verblasst:
        zeilen.append(f"! `opacity` auf Text: {eintrag}")

    if not texte:
        return 2, zeilen, 0
    befunde = sum(1 for z in zeilen if z.startswith("!"))
    return (1 if befunde else 0), zeilen, len(texte)


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche Ausgabe
    # auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("screen")
    parser.add_argument("png")
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--fall", default="")
    parser.add_argument("--offscreen", action="store_true")
    parser.add_argument("--font-dir", default=str(FONTS))
    parser.add_argument("--qml-dir", default=str(GUI_QML))
    parser.add_argument("--wait", type=int, default=250)
    args = parser.parse_args()

    qml_path = resolve_screen(args.screen, Path(args.qml_dir))
    width, height = (int(part) for part in args.size.split("x"))

    code_render, warnings, view, image = render(
        qml_path,
        width=width,
        height=height,
        dark=args.dark,
        fall=args.fall,
        offscreen=args.offscreen,
        font_dir=Path(args.font_dir),
        wait_ms=args.wait,
    )

    label = f"{args.screen} {args.size} {'dunkel' if args.dark else 'hell'}"
    if args.fall:
        label += f" [{args.fall}]"

    if code_render:
        print(f"{label}: Schritt 1/2 (rendern) fehlgeschlagen", file=sys.stderr)
        for message in warnings:
            print("  " + message, file=sys.stderr)
        return code_render

    out = Path(args.png)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(out), "PNG"):
        print(f"PNG nicht geschrieben: {out}", file=sys.stderr)
        return 2

    root = view.rootObject()
    code_layout, layout_findings, texte_layout = check_layout(root)
    code_contrast, contrast_lines, texte_contrast = check_contrast(root, image)

    print(f"{label}  →  {out}")
    print(f"  1/2 rendern+Warnungen: {len(warnings)} Warnungen")
    for message in warnings:
        print("      " + message)
    print(f"  3   Layout: {texte_layout} Textstellen angesehen, {len(layout_findings)} Befunde")
    for finding in layout_findings:
        print("      " + finding)
    print(f"  4   Kontrast: {texte_contrast} Textstellen gemessen")
    for line in contrast_lines:
        print("      " + line)

    view.hide()
    del view

    code = max(code_render, 1 if warnings else 0, code_layout, code_contrast)
    print(f"  Ergebnis: {'OK' if code == 0 else 'FEHL' if code == 1 else 'NICHTS GEPRÜFT'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
