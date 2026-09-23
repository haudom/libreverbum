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

Eine Durchsicht (Commit `d993e3e`) hat die erste Fassung dieses Skripts in sieben von rund
zwanzig Angriffen „Ergebnis: OK" melden lassen, obwohl die Seite kaputt war (Befunde B1–B4,
B6, B10, B11 — Einzelheiten je an der betroffenen Stelle unten). Diese Fassung behebt sie.

Verfahren
---------
Vier Schritte gegen **eine** Rendering, nicht drei getrennte Prozesse wie im Vorbild:

1. **rendern** — Schriften laden, den echten Bildschirm laden (über `gui.app.build_engine`
   — also über `Main.qml` mit Fenster, Loader und Mindestgröße, Befund B6 — solange kein
   `--qml-dir` einen anderen Ort nennt; ein abweichender `--qml-dir` lädt die einzelne
   Datei direkt, für Angriffsvorlagen unter `tests/qml_fixtures/`, die `gui/qml/` nicht
   verschmutzen sollen), zeigen, warten, `grabWindow()`, als PNG schreiben.
2. **Warnungen zählen** — über `QQmlEngine.warnings` **und** `qInstallMessageHandler`
   (Durchsicht 907ab02, Befund 1: Ersteres sieht nur, was die QML-Maschine selbst als
   `QQmlError` einstuft; `console.warn` und Qt-eigene Meldungen laufen nur über den
   Meldungs-Handler). Beide Wege schreiben seit Befund B5 zusätzlich sofort nach stderr.
3. **Layout prüfen** — der Objektbaum auf Überlauf, Lage außerhalb des sichtbaren
   Bereichs (Befund B2) und gekürzten Text.
4. **Kontrast messen** — im gerenderten Bild an jeder sichtbaren Textstelle; überschneidet
   ein fremdes Element denselben Kasten, wird es für einen zusätzlichen `grabWindow()`
   unsichtbar gemacht und die Messung läuft **isoliert** (Befund B3), dazu je Textstelle
   die tatsächlich geladene Schriftfamilie (Befund B4).

Jeder der letzten drei Schritte meldet zusätzlich, wenn er **nichts** angesehen hat (Befund
B4, Durchsicht `b2d5cab`): ein einfarbiges Bild, kein `Text` im Objektbaum, keine gemessene
Textstelle gelten als eigener Fehlschlag, nicht als sauberes Ergebnis.

Aufruf
------
    python tools/gui_screenshot.py <screen> <png> [--size 1280x800] [--dark]
        [--offscreen] [--fall NAME] [--font-dir DIR] [--qml-dir DIR] [--wait MS]

`<screen>` ist der Dateiname ohne Endung unter `gui/qml/` (Vorgabe für `--qml-dir`) — für
AP 15 also `Placeholder`. `--dark` setzt `Theme.dark` über die Kontexteigenschaft
`appDark`, wie im Vorbild. Ohne `--offscreen` braucht der Lauf ein echtes Fenstersystem;
mit `--offscreen` fällt Qt Quick auf den Software-Renderer zurück (dieselbe Einschränkung
wie im Vorbild — `MultiEffect` fiele dort still aus, dieser Bildschirm nutzt es heute
nicht).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtQuick import QQuickItem

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

# (Befund B1, Durchsicht d993e3e): Klassennamen, die eine Textstelle tragen kann, ohne
# "QQuickText" zu erben — Text-Eingabefelder sind eine eigene Klassenfamilie
# (QQuickTextInput/QQuickTextEdit), kein Untertyp von QQuickText.
_TEXT_INPUT_BASES = ("QQuickTextInput", "QQuickTextEdit")


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _text_kind(item: QQuickItem) -> str | None:
    """„text" für alles, was von `QQuickText` erbt — Label, ein `required property`-
    Delegat und eine eigene Komponente mit Text-Wurzel eingeschlossen, weil deren
    Metaobjektname zwar nicht wörtlich `"QQuickText"` heißt, ihre C++-Basisklasse aber
    dieselbe bleibt. „input" für `TextInput`/`TextEdit` (und damit auch `TextField`, deren
    Eingabeteil ein `TextInput` ist) — eine eigene Klassenfamilie, kein Untertyp von
    `QQuickText` (Befund B1, Durchsicht d993e3e; der alte Vergleich `className() ==
    "QQuickText"` übersah alle vier Fälle)."""
    if item.inherits("QQuickText"):
        return "text"
    if any(item.inherits(base) for base in _TEXT_INPUT_BASES):
        return "input"
    return None


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


def _load_via_main_qml(
    screen_name: str, *, dark: bool, fall: str, font_dir: Path
) -> tuple[int, object | None, list[str]]:
    """Lädt den echten Bildschirm über `gui.app.build_engine` — Fenster, Loader und
    Mindestgröße aus `Main.qml` eingeschlossen (Befund B6, Durchsicht d993e3e). Vorher
    rendere dieses Werkzeug `<screen>.qml` einzeln in einer eigenen `QQuickView`; ein
    Fenster, ein Loader und die Mindestgröße der echten Anwendung liefen damit nie durch
    die Prüfung, und ohne `QQuickStyle.setStyle("Basic")` erzeugte jeder Bildschirm mit
    `Button`/`TextField` fremde `OpenThemeData()`-Warnungen aus dem Windows-Stil.

    `warnings` ist dieselbe Liste, die `build_engine` intern führt — sie wächst weiter,
    solange der Meldungs-Handler installiert bleibt (auch während der spätere Wartezeit in
    `render()`), und jede neue Warnung ist zu diesem Zeitpunkt bereits nach stderr
    geschrieben (Befund B5).

    `window` trägt die `QQmlApplicationEngine` zusätzlich als eigenes Attribut: Ohne eine
    eigene Referenz räumt Python sie ein, sobald diese Funktion zurückkehrt — und
    `QQmlApplicationEngine` löscht beim eigenen Aufräumen jedes Objekt, das sie selbst
    geladen hat, das Fenster eingeschlossen (am Bestand geprüft: `window.resize(...)` im
    Aufrufer brach mit „Internal C++ object … already deleted" ab)."""
    from PySide6.QtQuick import QQuickWindow

    from gui.app import build_engine

    try:
        _app, engine, warnings = build_engine(
            [],
            font_dir=font_dir,
            context_properties={"appDark": dark, "appCase": fall, "appAnimate": False},
        )
    except RuntimeError as error:
        # gui.app.load_fonts bricht Regel 13 gemäß mit einer Ausnahme ab (Befund B4,
        # leeres Schriftverzeichnis oder eine Theme-Familie ohne geladene Datei) — hier in
        # eine reguläre Fehlschlagsmeldung dieses Werkzeugs übersetzt, statt den Aufrufer
        # mit einem rohen Stapelauszug zurückzulassen.
        print(str(error), file=sys.stderr)
        return 2, None, []
    windows = [root for root in engine.rootObjects() if isinstance(root, QQuickWindow)]
    if not windows:
        print(f"gui/qml/Main.qml lieferte kein Fenster: {engine.rootObjects()}", file=sys.stderr)
        return 2, None, warnings

    window = windows[0]
    window._gui_screenshot_engine = engine  # siehe Docstring oben
    if screen_name != window.property("screen"):
        from PySide6.QtTest import QTest

        window.setProperty("screen", screen_name)
        # Der Loader lädt den Wechsel asynchron; eine kurze Wartezeit reicht, weil es
        # sich um eine lokale Datei handelt (kein Netzwerk).
        QTest.qWait(50)
    return 0, window, warnings


def _load_direct(
    qml_path: Path, *, dark: bool, fall: str, font_dir: Path
) -> tuple[int, object | None, list[str]]:
    """Lädt `qml_path` einzeln in einer eigenen `QQuickView`, ohne `Main.qml` — für
    Angriffsvorlagen unter einem eigenen `--qml-dir` (`tests/qml_fixtures/`), die weder
    `gui/qml/` verschmutzen noch über den Bildschirmnamen von `Main.qml` erreichbar sein
    sollen. Lädt Schriften selbst, mit derselben Untergrenze wie `gui.app.load_fonts`
    (Befund B4): ein leeres `font_dir` bricht ab, statt klaglos ohne eine einzige
    Schriftfamilie weiterzumachen."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQuick import QQuickView

    families: list[str] = []
    for font_path in sorted(font_dir.glob("*.ttf")):
        handle = QFontDatabase.addApplicationFont(str(font_path))
        if handle < 0:
            print(f"Schrift nicht geladen: {font_path}", file=sys.stderr)
            return 2, None, []
        families.extend(QFontDatabase.applicationFontFamilies(handle))
    if not families:
        print(f"Keine Schrift aus {font_dir} geladen (Verzeichnis leer?)", file=sys.stderr)
        return 2, None, []

    warnings: list[str] = []
    view = QQuickView()
    view.engine().rootContext().setContextProperty("appDark", dark)
    view.engine().rootContext().setContextProperty("appCase", fall)
    view.engine().rootContext().setContextProperty("appAnimate", False)
    view.engine().addImportPath(str(qml_path.parent))
    view.engine().warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile(str(qml_path)))
    if view.status() != QQuickView.Status.Ready:
        print(f"QML nicht geladen: {view.errors()}", file=sys.stderr)
        return 2, None, warnings
    return 0, view, warnings


def render(
    qml_path: Path,
    qml_dir: Path,
    *,
    width: int,
    height: int,
    dark: bool,
    fall: str,
    offscreen: bool,
    font_dir: Path,
    wait_ms: int,
) -> tuple[int, list[str], object | None, object]:
    """Schritt 1 und 2: laden, zeigen, Bild greifen, jede QML-/Qt-Warnung als Fehlschlag.

    Liefert `(code, warnings, window, image)`; `window` bleibt `None` bei einem
    Fehlschlag vor dem Laden. `code` ist 0 bei Erfolg, 2 bei einem Fehlschlag, der nichts
    zum Prüfen übrig lässt (kein Bild, falsches Format, einfarbig — Untergrenze aus Befund
    B4). `window` trägt danach seine **tatsächliche** Größe (`window.width()`/`.height()`)
    — bei `--qml-dir gui/qml` (Vorgabe) über die echte Mindestgröße aus `Main.qml`
    geklemmt, wenn `--size` darunter liegt (Befund B6)."""
    if offscreen:
        import os

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        # Ohne diese Zeile kennt der Offscreen-Treiber unter Windows keine einzige
        # Schriftfamilie (am Bestand gemessen, siehe gui/app.py, Modulkopf „Regeln").
        os.environ["QT_QPA_FONTDIR"] = str(font_dir)

    from PySide6.QtGui import QGuiApplication, QImage
    from PySide6.QtTest import QTest

    # Referenz halten (Abschnitt 8 des Bauplans): Ohne sie räumt Python die Anwendung weg,
    # solange das Fenster noch lebt.
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    del app

    if qml_dir == GUI_QML:
        code, window, warnings = _load_via_main_qml(
            qml_path.stem, dark=dark, fall=fall, font_dir=font_dir
        )
    else:
        code, window, warnings = _load_direct(qml_path, dark=dark, fall=fall, font_dir=font_dir)
    if code:
        return code, warnings, None, None

    assert window is not None
    window.resize(width, height)
    window.show()
    if not QTest.qWaitForWindowExposed(window, 5000):
        print("Fenster wurde nicht sichtbar", file=sys.stderr)
        return 2, warnings, window, None
    QTest.qWait(wait_ms)
    image = window.grabWindow()
    actual_w, actual_h = window.width(), window.height()
    if image.isNull() or image.width() != actual_w or image.height() != actual_h:
        print(f"grabWindow() lieferte {image.width()}x{image.height()}", file=sys.stderr)
        return 2, warnings, window, None

    # Untergrenze (Befund B4, Durchsicht b2d5cab): Ein Bildschirm, der gar nichts
    # zeichnet, bestände sonst jede Prüfung unten mit „0 Warnungen, 0 Befunde".
    flach = image.convertToFormat(QImage.Format.Format_RGB32)
    roh = bytes(flach.constBits())
    if not roh or roh == roh[:4] * (len(roh) // 4):
        print("Bild ist einfarbig — es wurde nichts gezeichnet", file=sys.stderr)
        return 2, warnings, window, image

    return 0, warnings, window, image


def _content_root(window: object) -> QQuickItem:
    """Das Wurzelelement für den Objektbaumdurchlauf — bei `QQuickWindow`
    (`Main.qml`-Pfad) wie bei `QQuickView` (Direktpfad) über `contentItem()`, damit beide
    Render-Wege denselben Baumdurchlauf benutzen (Befund B6)."""
    item = window.contentItem()
    if item is None:
        raise RuntimeError("Fenster ohne contentItem() — nichts zu prüfen")
    return item


def check_layout(root: QQuickItem) -> tuple[int, list[str], int, int]:
    """Schritt 3: Überlauf, Lage außerhalb des sichtbaren Bereichs und gekürzter Text im
    Objektbaum. Liefert `(code, befunde, angesehene_texte, mit_text_eigenschaft)`; `code`
    ist 2, wenn kein einziger Text/TextInput angesehen wurde (Untergrenze, Befund B4).

    (Befund B2, Durchsicht d993e3e): Ein Kind mit 0×0 Ausdehnung wurde bisher komplett
    übersprungen — `continue`, noch vor dem rekursiven `walk()`-Aufruf —, sodass ein
    ganzer Teilbaum unter einem reinen Layout-Halter (0×0, ohne eigene Fläche) nie
    besucht wurde. Übersprungen wird jetzt nur noch der Elternvergleich, wenn das
    Elternelement selbst 0×0 ist (ein Vergleich dagegen wäre bedeutungslos); zusätzlich
    prüft eine zweite, unabhängige Kontrolle jede Textstelle gegen das Fenster und den
    nächsten abschneidenden Vorfahren (`clip: true`) in Szenenkoordinaten — das fängt
    genau den Fall, den ein reiner Elternvergleich nicht sieht: ein Text, dessen
    unmittelbarer Halter zufällig mitwächst, der aber selbst weit aus dem Fenster läuft."""
    from PySide6.QtCore import QPointF, QRectF

    findings: list[str] = []
    texte = 0
    mit_text_eigenschaft = 0
    fenster = QRectF(0, 0, root.width(), root.height())

    def describe(item: QQuickItem) -> str:
        name = item.objectName() or type(item).__name__
        return f"{name} ({item.width():.0f}×{item.height():.0f} bei {item.x():.0f},{item.y():.0f})"

    def scene_rect(item: QQuickItem) -> QRectF:
        oben_links = item.mapToScene(QPointF(0, 0))
        return QRectF(oben_links.x(), oben_links.y(), item.width(), item.height())

    def walk(item: QQuickItem, path: str, clip_rect: QRectF) -> None:
        nonlocal texte, mit_text_eigenschaft
        for child in item.childItems():
            if not child.isVisible():
                continue
            here = f"{path} › {describe(child)}"

            # Der Inhalt einer ListView/Flickable ragt naturgemäß aus ihr heraus — das ist
            # der Bildlauf selbst, kein Befund (wie im Vorbild).
            if item.metaObject().className() in (
                "QQuickListView",
                "QQuickFlickable",
            ) or child.objectName() in ("focusRing", "listContent"):
                walk(child, here, clip_rect)
                continue

            tolerated = 0.5

            if item.width() > 0 and item.height() > 0:
                over_right = child.x() + child.width() - item.width()
                over_bottom = child.y() + child.height() - item.height()
                over_left = -child.x()
                over_top = -child.y()
                worst = max(over_right, over_bottom, over_left, over_top)
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

            kind = _text_kind(child)

            # B2, zweite Kontrolle: unabhängig vom Elternvergleich oben — nötig genau
            # dort, wo der Elternvergleich oben ausgelassen wurde (Elternelement 0×0):
            # eine Textstelle unter einem reinen Layout-Halter kann trotzdem, ganz oder
            # teilweise, aus dem Fenster oder dem nächsten abschneidenden Vorfahren
            # laufen — hier gegen das Fenster **und** den laufenden Ausschnitt gemessen,
            # mit derselben Richtungsangabe wie beim gewöhnlichen Überlauf oben. Nur für
            # den 0×0-Fall: Hat das Elternelement selbst eine Ausdehnung, meldet der
            # Elternvergleich oben denselben Überlauf bereits — diese zweite Prüfung
            # würde ihn nur doppelt melden.
            if (
                kind is not None
                and child.width() > 0
                and child.height() > 0
                and (item.width() == 0 or item.height() == 0)
            ):
                szene = scene_rect(child)
                sichtbarer_bereich = clip_rect.intersected(fenster)
                over_right = (szene.x() + szene.width()) - (
                    sichtbarer_bereich.x() + sichtbarer_bereich.width()
                )
                over_bottom = (szene.y() + szene.height()) - (
                    sichtbarer_bereich.y() + sichtbarer_bereich.height()
                )
                over_left = sichtbarer_bereich.x() - szene.x()
                over_top = sichtbarer_bereich.y() - szene.y()
                worst_fenster = max(over_right, over_bottom, over_left, over_top)
                if worst_fenster > tolerated:
                    seiten = []
                    if over_right > tolerated:
                        seiten.append(f"rechts {over_right:.0f}")
                    if over_bottom > tolerated:
                        seiten.append(f"unten {over_bottom:.0f}")
                    if over_left > tolerated:
                        seiten.append(f"links {over_left:.0f}")
                    if over_top > tolerated:
                        seiten.append(f"oben {over_top:.0f}")
                    findings.append(
                        f"AUSSERHALB DES SICHTBAREN BEREICHS {' / '.join(seiten)} px: {here}"
                    )

            if child.property("text") is not None:
                mit_text_eigenschaft += 1

            if kind is not None:
                texte += 1
                if kind == "text":
                    name = child.objectName()
                    implicit = child.property("implicitHeight")
                    if implicit is not None and implicit - child.height() > 1:
                        findings.append(
                            f"TEXT ZU HOCH um {implicit - child.height():.0f} px "
                            f"(braucht {implicit:.0f}, hat {child.height():.0f}): {here}"
                        )
                    if child.property("truncated") and name not in ELIDE_ERLAUBT:
                        findings.append(f"TEXT GEKÜRZT (elide/truncated): {here}")

            naechster_clip = clip_rect.intersected(scene_rect(child)) if child.clip() else clip_rect
            walk(child, here, naechster_clip)

    walk(root, describe(root), fenster)

    # (Befund B1, zweite Hälfte, Durchsicht d993e3e): ein Sicherheitsnetz gegen jede
    # künftige Textklasse, die weder `_text_kind` noch die beiden Zweige darin trifft —
    # jedes Element mit einer `text`-Eigenschaft, das nicht mitgezählt wurde, wird
    # ausdrücklich gemeldet, statt lautlos durchzurutschen. Bewusst grob: Ein `Button`
    # trägt selbst eine `text`-Eigenschaft, die nur die seines internen Labels spiegelt
    # (das separat als eigene Textstelle gezählt wird) — käme ab AP 16a ein Bildschirm mit
    # `Button` dazu, wäre das ein erwarteter, kein echter Befund; bis dahin kommt kein
    # Bauteil dieser Art vor keinem `mit_text_eigenschaft`-Vergleich vor.
    if mit_text_eigenschaft > texte:
        findings.append(
            f"ÜBERSEHENE TEXTEIGENSCHAFT: {mit_text_eigenschaft} Elemente mit "
            f"text-Eigenschaft, aber nur {texte} als Text/TextInput erkannt"
        )

    if not texte:
        return 2, findings, texte, mit_text_eigenschaft
    return (1 if findings else 0), findings, texte, mit_text_eigenschaft


def _ancestors(item: QQuickItem) -> set[QQuickItem]:
    kette = set()
    eltern = item.parentItem()
    while eltern is not None:
        kette.add(eltern)
        eltern = eltern.parentItem()
    return kette


def check_contrast(
    root: QQuickItem, image: object, window: object
) -> tuple[int, list[str], int, int]:
    """Schritt 4: Kontrast im gerenderten Bild an jeder sichtbaren Textstelle, dazu je
    Textstelle die tatsächlich geladene Schriftfamilie. Liefert `(code, zeilen, gemessen,
    uebersprungen)`; `code` ist 2, wenn keine einzige Textstelle gemessen wurde
    (Untergrenze, Befund B4).

    (Befund B4, Durchsicht d993e3e): `QFontInfo(font).family() == font.family()` je
    Textstelle — eine nicht geladene Schrift bricht heute schon in `render()`/
    `gui.app.load_fonts` ab (leeres Verzeichnis, fehlende Theme-Familie), aber eine
    Familie, die zwar geladen wurde, an dieser einen Textstelle aber trotzdem nicht
    ankommt (etwa durch eine falsche Bindung), wäre sonst weiter unsichtbar.

    (Befund B11, Durchsicht d993e3e): „N Textstellen gemessen" zählte bisher auch
    Textstellen, die im zweiten Durchlauf wegen Rundung doch übersprungen wurden — `texte`
    aus dem ersten Durchlauf (Sichtbarkeitsfilter) und die tatsächlich gemessenen waren
    zwei verschiedene Zahlen, aber nur eine davon wurde ausgegeben. Gezählt wird jetzt nur
    noch, was tatsächlich eine Zeile ergeben hat; Übersprungenes wird gesondert gemeldet.

    (Befund B3, Durchsicht d993e3e): Liegt im selben Kasten ein zweiter Inhalt — eine
    dunkle Linie, ein Balken, ein eigenes Element —, verfälscht er die Messung:
    „häufigste/extremste Farbe im Kasten" trifft dann ihn, nicht den eigentlichen, oft
    absichtlich blassen Text. **Bekannte Lücke:** ein anders gefärbter RichText-Teil
    (`textFormat: Text.RichText`, zwei `<span style="color:…">` in derselben Textstelle)
    bleibt offen — es gibt kein zweites Element, das sich isolieren ließe, und ein
    erprobter Anteilsschwellwert war am Bestand nicht von gewöhnlichem Antialiasing zu
    unterscheiden (Einzelheiten unten, kurz vor der Messung). Zwei rein rechnerische
    Unterscheidungen für den allgemeinen Fall (Farben nach
    Abstand clustern; nach RGB-Kollinearität zur Grund-Tinte-Geraden trennen) sind an
    echten Textstellen aus `gui/qml/Placeholder.qml` gescheitert — Antialiasing streut zu
    unvorhersehbar, und zwei echte, aber ähnlich getönte Farben liegen im RGB-Raum
    manchmal zufällig nah an derselben Geraden. Gemessen wird deshalb **isoliert**: Vor
    dem Messen einer Textstelle werden alle anderen sichtbaren Elemente, die ihr Rechteck
    überschneiden, weder sie selbst noch einer ihrer Vorfahren sind und **nach** ihr
    gezeichnet werden, unsichtbar gemacht, das Fenster **neu gegriffen**, gemessen und die
    Sichtbarkeit danach wiederhergestellt — der Kasten enthält für die Messung dann nur
    noch seinen eigenen Grund und seine eigene Tinte, ganz ohne Heuristik. „Nach ihr
    gezeichnet" heißt: später im selben Durchlauf des Objektbaums besucht, derselbe
    Vorrang, den Qt Quick ohne eigene `z`-Eigenschaft selbst anwendet — ohne diese
    Einschränkung träfe es auch den Grund **hinter** jeder Textstelle (jede
    Hintergrundfläche überschneidet jeden Text, der vor ihr gezeichnet wird, aber
    verdeckt nichts) und meldete an jeder einzelnen Textstelle einen Befund, der keiner
    ist (am eingecheckten `gui/qml/Placeholder.qml` nachgemessen: alle elf Textstellen).
    Das kostet einen zusätzlichen `grabWindow()`-Aufruf je betroffener Textstelle, nicht
    je Textstelle insgesamt: Der Regelfall (kein zweiter Inhalt im selben Kasten) bleibt
    beim einen Bild aus `render()`."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QFontInfo

    texte: list[tuple[object, float, float, float, float, bool, int]] = []
    alle_elemente: list[tuple[QQuickItem, QRectF, int]] = []
    verblasst: list[str] = []
    naechster_index = 0

    def walk(item: QQuickItem, clip: QRectF) -> None:
        nonlocal naechster_index
        for child in item.childItems():
            if not child.isVisible():
                continue
            index = naechster_index
            naechster_index += 1
            oben_links = child.mapToScene(QPointF(0, 0))
            rechteck = QRectF(oben_links.x(), oben_links.y(), child.width(), child.height())
            sichtbar = rechteck.intersected(clip)
            innen = clip.intersected(rechteck) if child.clip() else clip

            if child.width() > 0 and child.height() > 0:
                alle_elemente.append((child, rechteck, index))

            if (
                _text_kind(child) is not None
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
                    (
                        child,
                        sichtbar.x(),
                        sichtbar.y(),
                        sichtbar.width(),
                        sichtbar.height(),
                        ganz,
                        index,
                    )
                )
            walk(child, innen)

    walk(root, QRectF(0, 0, root.width(), root.height()))

    zeilen: list[str] = []
    schlechtester: tuple[float, str] | None = None
    gemessen = 0
    uebersprungen = 0
    for item, x, y, w, h, ganz, eigener_index in texte:
        text = str(item.property("text") or "")[:46].replace("\n", " ")

        font = item.property("font")
        if font is not None:
            tatsaechlich = QFontInfo(font).family()
            erwartet = font.family()
            if tatsaechlich != erwartet:
                zeilen.append(
                    f"! SCHRIFT NICHT GELADEN: erwartet {erwartet!r}, geladen "
                    f"{tatsaechlich!r} ({text!r})"
                )

        eigenes_rechteck = QRectF(x, y, w, h)
        vorfahren = _ancestors(item)
        fremde = [
            (other, rect)
            for other, rect, index in alle_elemente
            if other is not item
            and other not in vorfahren
            and index > eigener_index
            and rect.intersects(eigenes_rechteck)
        ]

        aktives_bild = image
        if fremde:
            urspruenglich = [(other, other.isVisible()) for other, _ in fremde]
            for other, _ in urspruenglich:
                other.setVisible(False)
            aktives_bild = window.grabWindow()
            for other, war_sichtbar in urspruenglich:
                other.setVisible(war_sichtbar)
            zeilen.append(
                f"! GEMISCHTER KASTENINHALT ({len(fremde)} Elemente überschneiden den "
                f"Kasten, isoliert neu gemessen): {text!r}"
            )

        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(aktives_bild.width(), int(x + w)), min(aktives_bild.height(), int(y + h))
        if x1 - x0 < 2 or y1 - y0 < 2:
            uebersprungen += 1
            continue
        pixel = []
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                c = aktives_bild.pixelColor(xx, yy)
                pixel.append((c.red(), c.green(), c.blue()))
        if not pixel:
            uebersprungen += 1
            continue
        haeufig = Counter(pixel)
        hintergrund = haeufig.most_common(1)[0][0]
        anteil = haeufig.most_common(1)[0][1] / len(pixel)
        if anteil > 0.985:
            gemessen += 1
            if ganz:
                zeilen.append(f"! UNSICHTBAR: {text!r}")
            continue

        # Isoliert (oder ohnehin schon allein im Kasten): der extremste Pixel ist jetzt
        # zuverlässig die eigene Tinte, kein fremder Inhalt kann ihn mehr verdecken.
        #
        # Bekannte Lücke, bewusst nicht geschlossen (Aufwand/Nutzen, siehe Bericht der
        # Nachbesserung zu Befund B3): `textFormat: Text.RichText` mit zwei `<span
        # style="color:…">`-Farben in **derselben** Textstelle entzieht sich dem
        # Ausblenden oben — es gibt kein zweites Element, das isoliert werden könnte. Ein
        # zusätzlicher Anteilsschwellwert wurde erprobt und am Bestand wieder verworfen:
        # Ein kurzer, dunkler `<span>` in einem sonst langen, blassen Satz erreichte in
        # der Messung nur 1,3 % der Kastenfläche — nicht unterscheidbar von den 3,9–5,5 %,
        # die gewöhnliches Antialiasing an dispersen Kanten ohnehin erreicht (an
        # `gui/qml/Placeholder.qml` nachgemessen). Eine Schwelle, die das eine träfe,
        # träfe das andere mit.
        grund_lum = relative_luminance(hintergrund)
        vordergrund = max(pixel, key=lambda p: abs(relative_luminance(p) - grund_lum))
        verhaeltnis = contrast(vordergrund, hintergrund)
        gemessen += 1
        groesse = font.pixelSize()
        fett = font.weight() >= 600
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

    if not gemessen:
        return 2, zeilen, gemessen, uebersprungen
    befunde = sum(1 for z in zeilen if z.startswith("!"))
    return (1 if befunde else 0), zeilen, gemessen, uebersprungen


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

    # REGEL (bauplan-phase2.md, Abschnitt 8; Befund B6, Durchsicht d993e3e): muss vor jeder
    # QQuickWindow/Engine stehen, auf beiden Render-Wegen — ohne sie erzeugt jeder
    # Bildschirm mit Qt-Quick-Controls-Bedienelementen (Button, TextField) unter Windows
    # fremde `OpenThemeData()`-Warnungen aus dem systemeigenen Stil.
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")

    qml_dir = Path(args.qml_dir)
    qml_path = resolve_screen(args.screen, qml_dir)
    width, height = (int(part) for part in args.size.split("x"))

    code_render, warnings, window, image = render(
        qml_path,
        qml_dir,
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

    assert window is not None and image is not None
    if (window.width(), window.height()) != (width, height):
        label += f" (tatsächlich {window.width()}×{window.height()})"

    out = Path(args.png)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(out), "PNG"):
        print(f"PNG nicht geschrieben: {out}", file=sys.stderr)
        return 2

    root = _content_root(window)
    code_layout, layout_findings, texte_layout, mit_text_eigenschaft = check_layout(root)
    code_contrast, contrast_lines, gemessen, uebersprungen = check_contrast(root, image, window)

    print(f"{label}  →  {out}")
    print(f"  1/2 rendern+Warnungen: {len(warnings)} Warnungen")
    for message in warnings:
        print("      " + message)
    print(
        f"  3   Layout: {texte_layout} Textstellen angesehen "
        f"({mit_text_eigenschaft} mit text-Eigenschaft), {len(layout_findings)} Befunde"
    )
    for finding in layout_findings:
        print("      " + finding)
    print(f"  4   Kontrast: {gemessen} Textstellen gemessen, {uebersprungen} übersprungen")
    for line in contrast_lines:
        print("      " + line)

    window.hide()
    del window

    code = max(code_render, 1 if warnings else 0, code_layout, code_contrast)
    print(f"  Ergebnis: {'OK' if code == 0 else 'FEHL' if code == 1 else 'NICHTS GEPRÜFT'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
