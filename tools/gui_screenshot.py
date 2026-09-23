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
B6, B10, B11). Eine Nachbesserung (Commit `d00e7c9`) behob sie, meldete danach aber in
**beide** Richtungen falsch: Alle sechzehn Mockup-Bilder grundlos rot (Befunde F1–F3, F6),
sieben neue Angriffe falsch grün (Befunde F1, F2, F4, F7). Diese Fassung ersetzt den
Kontrastschritt durch ein Differenzbild (siehe `check_contrast`) und behebt die übrigen
Befunde F4–F13 der Nachprüfung von `d00e7c9` je an ihrer Stelle unten.

Verfahren
---------
Vier Schritte gegen **eine** Rendering, nicht drei getrennte Prozesse wie im Vorbild:

1. **rendern** — Schriften laden, den echten Bildschirm laden (über `gui.app.build_engine`
   — also über `Main.qml` mit Fenster, Loader und Mindestgröße, Befund B6 — solange kein
   `--qml-dir` einen anderen Ort nennt; ein abweichender `--qml-dir` lädt die einzelne
   Datei direkt, für Angriffsvorlagen unter `tests/qml_fixtures/`, die `gui/qml/` nicht
   verschmutzen sollen), zeigen, warten, `grabWindow()`, als PNG schreiben.
2. **Warnungen zählen** — über `QQmlEngine.warnings` **und** `qInstallMessageHandler`
   (Durchsicht 907ab02, Befund 1). Beide Wege laufen seit der Nachprüfung von `d00e7c9`
   (Befund F7) über `gui.app.install_message_handler` — **eine** Stelle für beide
   Render-Wege, dedupliziert (Befund F9), schreibt sofort nach stderr (Befund B5).
3. **Layout prüfen** — der Objektbaum auf Überlauf (Höhe **und** Breite, Befund F4), Lage
   außerhalb des sichtbaren Bereichs (Befund B2), gekürzten Text und eine übersehene
   `text`-Eigenschaft, benannt und mit Ausnahme für gespiegelten Text (Befund F5).
4. **Kontrast messen** — im gerenderten Bild an jeder sichtbaren Textstelle, per
   Differenzbild (siehe `check_contrast`, Befunde F1–F3, F6 der Nachprüfung von `d00e7c9`).

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
    from PySide6.QtCore import QRectF
    from PySide6.QtQuick import QQuickItem

REPO = Path(__file__).resolve().parent.parent
GUI_QML = REPO / "gui" / "qml"
FONTS = REPO / "gui" / "fonts"

# Text, der gekürzt werden darf, weil er ein Name und keine Aussage ist — übernommen aus
# der geprüften Vorlage `tools/design_mockup/layout_check.py`, ELIDE_ERLAUBT, damit dieses
# Werkzeug an denselben, bereits abgenommenen Mockup-Bildschirmen keine neuen, dort nie
# gemeldeten Kürzungsbefunde erzeugt.
ELIDE_ERLAUBT: set[str] = {"bookLine", "listTitle", "wordCell", "chapterCell", "stageLabel"}

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


# Qt::TextElideMode: ElideLeft=0, ElideRight=1, ElideMiddle=2, ElideNone=3 — Qt.ElideNone
# ist also **nicht** 0 (leicht zu verwechseln, am Bestand nachgeprüft: `elide` blieb ohne
# ausdrückliche Angabe auf 3 stehen). Text.NoWrap ist dagegen tatsächlich 0.
_TEXT_ELIDE_NONE = 3
_TEXT_NO_WRAP = 0


def _read_enum_property(item: QQuickItem, name: str) -> int | None:
    """Liest eine QML-Enum-Eigenschaft wie `elide`/`wrapMode` als Zahl.

    `item.property(name)` (und ebenso `QQmlProperty(item, name).read()`) scheitert dafür
    an PySide6 mit `RuntimeError: Can't find converter for 'QQuickText::TextElideMode'.`
    (am Bestand nachgeprüft, `gui/qml/Placeholder.qml`, „headline") — ein bekannter
    Konvertierungsfehler für als „uncreatable" registrierte QML-Enums, den auch
    `QQmlProperty` nicht umgeht. `QQmlExpression` wertet stattdessen `Number(<name>)` im
    Eigenschaftsbereich des Items selbst aus: QML wandelt den Enum-Wert dabei **selbst**
    in eine reine Zahl um, bevor der kaputte Cast überhaupt beteiligt wäre."""
    from PySide6.QtQml import QQmlEngine, QQmlExpression

    ctx = QQmlEngine.contextForObject(item)
    if ctx is None:
        return None
    ergebnis = QQmlExpression(ctx, item, f"Number({name})").evaluate()
    wert = ergebnis[0] if isinstance(ergebnis, tuple) else ergebnis
    if wert is None:
        return None
    return int(wert)


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


def _is_main_qml_path(qml_dir: Path) -> bool:
    """`qml_dir == GUI_QML`, aber gegen den aufgelösten Pfad statt gegen den wörtlichen
    (Befund F12, Nachprüfung d00e7c9): `--qml-dir gui/qml` (relativ statt der absoluten
    Vorgabe) wich bisher, ohne jede Meldung, auf den Direktpfad aus — derselbe Bildschirm,
    aber ohne `Main.qml`, ohne Fenster, ohne Mindestgröße, und der Direktpfad hatte vor
    Befund F7 nicht einmal einen Meldungs-Handler."""
    return qml_dir.resolve() == GUI_QML.resolve()


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
    Schriftfamilie weiterzumachen.

    (Befund F7, Nachprüfung d00e7c9): Der Meldungs-Handler kommt jetzt über
    `gui.app.install_message_handler` — dieselbe Stelle wie in `build_engine` — statt gar
    keinen zu installieren. Vorher sah dieser Pfad nur, was `QQmlEngine.warnings` als
    `QQmlError` einstufte; `console.warn` und Qt-eigene Meldungen (etwa von
    `QFontDatabase`) liefen unbemerkt durch, „Ergebnis: OK" trotz kaputter Seite."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQuick import QQuickView

    from gui.app import install_message_handler

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
    record = install_message_handler(warnings)

    view = QQuickView()
    view.engine().rootContext().setContextProperty("appDark", dark)
    view.engine().rootContext().setContextProperty("appCase", fall)
    view.engine().rootContext().setContextProperty("appAnimate", False)
    view.engine().addImportPath(str(qml_path.parent))
    view.engine().warnings.connect(lambda errors: [record(str(e)) for e in errors])
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
    geklemmt, wenn `--size` darunter liegt (Befund B6); unter `--offscreen` klemmt Qt das
    aber nicht von selbst (Befund F12, Nachprüfung d00e7c9) — das wird unten eigens
    geprüft und als Warnung gemeldet, statt eine zu kleine Fläche unbemerkt zu rendern."""
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

    ueber_main_qml = _is_main_qml_path(qml_dir)
    if ueber_main_qml:
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

    # (Befund F12, Nachprüfung d00e7c9): Unter einem echten Fenstersystem klemmt Qt eine
    # angeforderte Größe unter `minimumWidth`/`minimumHeight` selbst — deshalb der
    # Vergleich `window.width() != width` weiter unten in main(). Unter `--offscreen` tut
    # es das nicht: Eine Anforderung von 700×400 rendert dort klaglos 700×400, obwohl
    # `Main.qml` 900×600 verlangt. Das wird hier eigens erkannt und als Warnung gemeldet.
    if ueber_main_qml:
        min_w = window.property("minimumWidth")
        min_h = window.property("minimumHeight")
        passt_nicht = (
            isinstance(min_w, (int, float))
            and isinstance(min_h, (int, float))
            and (window.width() < min_w or window.height() < min_h)
        )
        if passt_nicht:
            meldung = (
                f"Fenstergröße {window.width()}×{window.height()} unter Main.qml-"
                f"Mindestgröße {min_w:.0f}×{min_h:.0f} (unter --offscreen nicht von "
                "selbst geklemmt)"
            )
            print(meldung, file=sys.stderr)
            warnings.append(meldung)

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


def _ancestors(item: QQuickItem) -> set[QQuickItem]:
    kette = set()
    eltern = item.parentItem()
    while eltern is not None:
        kette.add(eltern)
        eltern = eltern.parentItem()
    return kette


def check_layout(root: QQuickItem) -> tuple[int, list[str], int, int]:
    """Schritt 3: Überlauf (Höhe und Breite), Lage außerhalb des sichtbaren Bereichs,
    gekürzter Text und eine übersehene `text`-Eigenschaft im Objektbaum. Liefert `(code,
    befunde, angesehene_texte, mit_text_eigenschaft)`; `code` ist 2, wenn kein einziger
    Text/TextInput angesehen wurde (Untergrenze, Befund B4).

    (Befund B2, Durchsicht d993e3e): Ein Kind mit 0×0 Ausdehnung wurde bisher komplett
    übersprungen — `continue`, noch vor dem rekursiven `walk()`-Aufruf —, sodass ein
    ganzer Teilbaum unter einem reinen Layout-Halter (0×0, ohne eigene Fläche) nie
    besucht wurde. Übersprungen wird jetzt nur noch der Elternvergleich, wenn das
    Elternelement selbst 0×0 ist; zusätzlich prüft eine zweite, unabhängige Kontrolle jede
    Textstelle gegen das Fenster und den nächsten abschneidenden Vorfahren (`clip: true`)
    in Szenenkoordinaten.

    (Befund F4, Nachprüfung d00e7c9): Der Elternvergleich oben misst nur die **Höhe**
    (`implicitHeight` gegen `height`), nie die Breite — ein Text breiter als sein eigener
    Kasten, ohne `elide` und ohne Umbruch, überschrieb bisher unbemerkt seinen Nachbarn.
    `contentWidth` einer `Text`-Textstelle bindet sich bei fehlendem `elide`/`wrapMode` von
    selbst an `width`, sobald `width` nicht **explizit** gesetzt ist — der Vergleich unten
    schlägt deshalb nur an, wenn tatsächlich eine feste, zu schmale Breite vorgegeben ist.

    (Befund F5, Nachprüfung d00e7c9): „ÜBERSEHENE TEXTEIGENSCHAFT" war bisher ein einziger
    Vergleich zweier Zahlen über den ganzen Baum — er schlug bei **jeder** Komponente mit
    einer eigenen `property string text` an, ohne das Element zu nennen, MessageBox im
    Mockup und jeden Controls-`Button` eingeschlossen, obwohl deren `text` nur den eines
    eigenen `Text`/`Label`-Nachfahren spiegelt. Jetzt: je Fundstelle benannt (Pfad im
    Objektbaum), und ausgenommen, wenn irgendein Text/TextInput-Nachfahre genau denselben
    Wert zeigt."""
    from PySide6.QtCore import QPointF, QRectF

    findings: list[str] = []
    texte = 0
    mit_text_eigenschaft = 0
    fenster = QRectF(0, 0, root.width(), root.height())

    text_werte: list[tuple[QQuickItem, str]] = []
    text_prop_kandidaten: list[tuple[QQuickItem, str, str]] = []

    def describe(item: QQuickItem) -> str:
        # (Befund F5, Nachprüfung d00e7c9): `type(item).__name__` liefert für QML-eigene
        # Typen ohne eigene Python-Bindung nur den nächsten bekannten Basistyp (meist
        # "QQuickItem") — uninformativ in einer Fundmeldung. `metaObject().className()`
        # nennt stattdessen den tatsächlichen Qt-Metatyp (etwa "QQuickButton").
        name = item.objectName() or item.metaObject().className()
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
                if kind is None:
                    text_prop_kandidaten.append((child, here, str(child.property("text"))))

            if kind is not None:
                texte += 1
                text_werte.append((child, str(child.property("text") or "")))
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

                    content_width = child.property("contentWidth")
                    elide = _read_enum_property(child, "elide")
                    wrap_mode = _read_enum_property(child, "wrapMode")
                    if (
                        content_width is not None
                        and child.width() > 0
                        and elide == _TEXT_ELIDE_NONE
                        and wrap_mode == _TEXT_NO_WRAP
                        and content_width - child.width() > 1
                    ):
                        findings.append(
                            f"TEXT ZU BREIT um {content_width - child.width():.0f} px "
                            f"(braucht {content_width:.0f}, hat {child.width():.0f}): {here}"
                        )

            naechster_clip = clip_rect.intersected(scene_rect(child)) if child.clip() else clip_rect
            walk(child, here, naechster_clip)

    walk(root, describe(root), fenster)

    for kandidat, pfad, wert in text_prop_kandidaten:
        if not wert.strip():
            # Eine leere text-Eigenschaft versteckt nichts — nichts zu übersehen (wie die
            # leere Textstelle in check_contrast, Befund F6).
            continue
        ausgenommen = any(
            wert == anderer_wert and kandidat in _ancestors(anderes_item)
            for anderes_item, anderer_wert in text_werte
        )
        if not ausgenommen:
            findings.append(
                f"ÜBERSEHENE TEXTEIGENSCHAFT: {pfad} zeigt {wert[:40]!r}, aber kein "
                "Text/TextInput-Nachfahre zeigt denselben Text"
            )

    if not texte:
        return 2, findings, texte, mit_text_eigenschaft
    return (1 if findings else 0), findings, texte, mit_text_eigenschaft


def _find_occluder(
    root: QQuickItem, text_item: QQuickItem, eigenes_rechteck: QRectF, eigener_index: int
) -> str | None:
    """Nur zur Meldung, wenn sich beim Ausblenden einer Textstelle nichts geändert hat
    (siehe `check_contrast`): Sucht ein anderes sichtbares Element, dessen Rechteck den
    Textkasten überschneidet **und später im Baum besucht wird** als die Textstelle
    selbst — Letzteres bewusst nur als grobe Näherung an „danach gezeichnet", zur reinen
    Beschriftung des Befunds, nicht zu seiner Einstufung: Beides, ÜBERDECKT wie
    UNSICHTBAR, bleibt in jedem Fall ein Befund. Ohne die Reihenfolge fände die Suche an
    jeder Textstelle ihre eigene Hintergrundfläche (deklariert **vor** dem Text, also
    keine Verdeckung) und meldete „ÜBERDECKT" auch bei einer schlichten Farbgleichheit."""
    from PySide6.QtCore import QPointF, QRectF

    vorfahren = _ancestors(text_item)
    index = 0

    def suche(item: QQuickItem) -> str | None:
        nonlocal index
        for child in item.childItems():
            if not child.isVisible():
                continue
            mein_index = index
            index += 1
            if child is text_item or child in vorfahren:
                treffer = suche(child)
                if treffer:
                    return treffer
                continue
            if mein_index > eigener_index and child.width() > 0 and child.height() > 0:
                oben_links = child.mapToScene(QPointF(0, 0))
                rechteck = QRectF(oben_links.x(), oben_links.y(), child.width(), child.height())
                if rechteck.intersects(eigenes_rechteck):
                    return child.objectName() or child.metaObject().className()
            treffer = suche(child)
            if treffer:
                return treffer
        return None

    return suche(root)


_GENERISCHE_FAMILIEN = {"", "sans serif", "serif", "monospace", "cursive", "fantasy", "system"}


def check_contrast(
    root: QQuickItem, image: object, window: object
) -> tuple[int, list[str], int, int]:
    """Schritt 4: Kontrast per Differenzbild (Nachprüfung d00e7c9, Befunde F1–F3 und F6).

    Je Textstelle wird das Fenster einmal **mit** und einmal **ohne genau diese eine**
    Textstelle gegriffen (`opacity` nur auf ihr selbst, nicht auf Geschwistern — der Rest
    der Seite bleibt unangetastet, keine Umbrüche durch verschobene Nachbarn). Die Pixel
    im Textkasten, die sich dabei ändern, sind ihre Tinte; das Bild ohne Text liefert an
    genau denselben Pixeln den tatsächlichen Grund — Rahmen, Linie, Bild, eine per `z`
    verschobene Fläche, eine ListView-Markierung, was auch immer dort wirklich liegt,
    ganz ohne Annahme über Zeichenreihenfolge.

    Das ersetzt die alte Fassung, die jedes andere, später im Baum besuchte Element
    überschneidungsweise ausblendete: „später im Baum" ist nicht „oben gezeichnet"
    (Befund F2 — `z` blieb unbeachtet, eine ListView-Markierung wurde deshalb fälschlich
    verdeckt, ein `z: -1`-Grund fälschlich freigelegt) und der bloße Umstand, dass sich
    ein Kasten mit irgendetwas Späterem überschneidet, war selbst schon ein Befund
    (Befund F1 — an jedem der 16 bekannt guten Mockup-Bilder, weil ein Fokusring, eine
    `MouseArea` oder ein per `clip` unsichtbarer Nachbar jeden Kasten berühren kann, ohne
    ihn zu betreffen). Auch die Mehrheitsfarbe im ganzen Kasten als Unsichtbarkeits-
    kriterium entfällt (Befund F6 — eine schmale „7" in einer breiten Zelle wurde daran
    fälschlich erkannt, ein leerer Text sollte stattdessen übersprungen werden).

    Ändert sich beim Ausblenden nichts, ist die Textstelle entweder deckungsgleich mit
    ihrem Grund (UNSICHTBAR) oder von einem anderen, undurchsichtigen Element vollständig
    verdeckt (ÜBERDECKT, `_find_occluder`) — nur zur besseren Meldung unterschieden, beides
    ist ein Befund.

    Liefert `(code, zeilen, gemessen, uebersprungen)`; `code` ist 2, wenn keine einzige
    Textstelle gemessen wurde (Untergrenze, Befund B4). `gemessen` zählt nur, was
    tatsächlich eine Zeile ergeben hat — leerer Text wird übersprungen, ohne mitgezählt zu
    werden (Befund F10 der Nachprüfung entfällt damit von selbst: Jede besuchte Textstelle
    erzeugt entweder genau eine Zeile und einen Zähler, oder keins von beidem)."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QFontInfo

    texte: list[tuple[QQuickItem, str, float, float, float, float, bool, int]] = []
    verblasst: list[str] = []
    naechster_index = 0

    def walk(item: QQuickItem, clip: QRectF) -> None:
        nonlocal naechster_index
        for child in item.childItems():
            if not child.isVisible():
                continue
            eigener_index = naechster_index
            naechster_index += 1
            oben_links = child.mapToScene(QPointF(0, 0))
            rechteck = QRectF(oben_links.x(), oben_links.y(), child.width(), child.height())
            sichtbar = rechteck.intersected(clip)
            innen = clip.intersected(rechteck) if child.clip() else clip

            if (
                _text_kind(child) is not None
                and child.width() > 0
                and child.objectName() not in AUSNAHMEN
                and sichtbar.width() >= 2
                and sichtbar.height() >= 2
            ):
                text = str(child.property("text") or "")
                if text.strip():  # (Befund F6) leerer Text: nichts zu messen, kein Befund
                    if child.opacity() < 0.999:
                        verblasst.append(f"{text[:40]!r} (opacity {child.opacity():.2f})")
                    # Ganz sichtbar (Kasten nicht vom Rollbereich einer Liste angeschnitten)
                    # oder nur ein Rand-Rest — wie im Vorbild `contrast_check.py`: Ein
                    # Fehlschlag beim Ausblenden ("nichts geändert") ist an einem winzigen
                    # Rand-Rest zweideutig (die Zeile rollt gerade aus dem Fenster, ihr
                    # sichtbarer Streifen kann zufällig genau die Zwischenzeile treffen,
                    # ohne Tinte) — ein echter Befund UNSICHTBAR/ÜBERDECKT gilt deshalb nur
                    # für einen ganz sichtbaren Kasten.
                    ganz = (
                        sichtbar.width() >= rechteck.width() - 0.5
                        and sichtbar.height() >= rechteck.height() - 0.5
                    )
                    texte.append(
                        (
                            child,
                            text[:46].replace("\n", " "),
                            sichtbar.x(),
                            sichtbar.y(),
                            sichtbar.width(),
                            sichtbar.height(),
                            ganz,
                            eigener_index,
                        )
                    )
            walk(child, innen)

    walk(root, QRectF(0, 0, root.width(), root.height()))

    zeilen: list[str] = []
    gemessen = 0
    uebersprungen = 0
    # Summe |dR|+|dG|+|dB| — deutlich über dem, was gewöhnliches Antialiasing an
    # unbeteiligten Kanten (Rundung, Subpixel-Hinting) erzeugt, am eingecheckten
    # gui/qml/Placeholder.qml nachgemessen.
    schwelle = 24

    for item, text, x, y, w, h, ganz, eigener_index in texte:
        font = item.property("font")
        if font is not None:
            erwartet = font.family()
            # (Befund F8, Nachprüfung d00e7c9): Der alte Vergleich prüfte `font.family()`
            # (die Angabe **am Item**) gegen `QFontInfo(font).family()` (die tatsächliche
            # Auflösung **desselben** Items) für **jede** Textstelle — für RichText mit
            # `<font face="Inter">` oder für Controls ohne eigenes `font.family` bleibt die
            # Item-Angabe der QML-eigene Vorgabewert ("Sans Serif", ein generischer Alias,
            # keine echte Familie), unabhängig davon, was tatsächlich gezeichnet wird; der
            # Vergleich meldete dort einen Fehlschlag, wo keiner war. Geprüft wird deshalb
            # nur noch, wenn das Item **ausdrücklich** eine konkrete Familie nennt (nicht
            # einen der Qt-eigenen generischen Aliasnamen) — das trifft `Theme.fonts.*`
            # (`AtkBadFont`, echte, nicht geladene Familien) ebenso wie jede andere, direkt
            # angegebene Schriftfamilie.
            if erwartet.strip().lower() not in _GENERISCHE_FAMILIEN:
                tatsaechlich = QFontInfo(font).family()
                if tatsaechlich != erwartet:
                    zeilen.append(
                        f"! SCHRIFT NICHT GELADEN: erwartet {erwartet!r}, geladen "
                        f"{tatsaechlich!r} ({text!r})"
                    )

        x0, y0 = max(0, int(x)), max(0, int(y))
        x1 = min(image.width(), round(x + w))
        y1 = min(image.height(), round(y + h))
        if x1 - x0 < 2 or y1 - y0 < 2:
            uebersprungen += 1
            continue

        urspruengliche_opacity = item.opacity()
        item.setOpacity(0.0)
        ohne = window.grabWindow()
        item.setOpacity(urspruengliche_opacity)

        aenderungen: list[tuple[int, tuple[int, int, int], tuple[int, int, int]]] = []
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                mit_farbe = image.pixelColor(xx, yy)
                ohne_farbe = ohne.pixelColor(xx, yy)
                delta = (
                    abs(mit_farbe.red() - ohne_farbe.red())
                    + abs(mit_farbe.green() - ohne_farbe.green())
                    + abs(mit_farbe.blue() - ohne_farbe.blue())
                )
                if delta > schwelle:
                    aenderungen.append(
                        (
                            delta,
                            (mit_farbe.red(), mit_farbe.green(), mit_farbe.blue()),
                            (ohne_farbe.red(), ohne_farbe.green(), ohne_farbe.blue()),
                        )
                    )

        if not aenderungen:
            if not ganz:
                # Nur ein Rand-Rest, von einem Rollbereich angeschnitten (etwa die letzte,
                # halb aus dem Fenster gerollte Listenzeile) — zweideutig, siehe Docstring:
                # kein Befund, aber auch keine belastbare Messung.
                uebersprungen += 1
                continue
            gemessen += 1
            verdecker = _find_occluder(root, item, QRectF(x, y, w, h), eigener_index)
            if verdecker:
                zeilen.append(f"! ÜBERDECKT von {verdecker}: {text!r}")
            else:
                zeilen.append(f"! UNSICHTBAR: {text!r}")
            continue

        gemessen += 1

        # Die Tinte ist die häufigste "mit"-Farbe unter den geänderten Pixeln — nicht die
        # Pixel mit der größten Änderung: Kreuzt eine andersfarbige Linie oder ein Rahmen
        # nur einen schmalen Streifen des Kastens (`tests/qml_fixtures/Underline.qml`),
        # erzeugt genau dort der größte Farbsprung, ohne die Tinte des übrigen, deutlich
        # größeren Textanteils zu sein — „größte Änderung" hätte diesen Streifen fälschlich
        # als Tinte gewählt (an `NxUnderlineBefore` nachgemessen: 10,14:1 statt der
        # tatsächlichen rund 1,2:1).
        #
        # Bei einer kleinen oder nur mäßig kontrastreichen Textstelle ist die einzelne
        # häufigste Exaktfarbe dagegen kein verlässlicher Kern mehr: Ein Zeichensatz
        # rendert seinen soliden Kern so gut wie nie in **einer** exakten Farbe, sondern in
        # vielen, von Subpixel-Rundung minimal verschiedenen Tönen, während sich der
        # blasse Antialiasing-Rand auf wenige, dem Grund nahe Töne konzentriert — eine
        # einzelne Randfarbe kann dadurch häufiger sein als jede einzelne Kernfarbe, obwohl
        # der Kern in Summe weit mehr Pixel stellt (an der Beschriftung eines
        # `Button` nachgemessen: 47 Rand-Pixel in einer Farbe gegen über hundert
        # Kern-Pixel, verteilt auf gut ein Dutzend fast-schwarze Töne). Alle Farben **nahe
        # der Höchsthäufigkeit** (mindestens die Hälfte davon) treten deshalb gegeneinander
        # an; unter ihnen gewinnt die, die sich am weitesten vom Grund unterscheidet — der
        # echte Kern liegt immer weiter vom Grund entfernt als sein eigener, blasserer
        # Rand, und eine einzelne Rand-Exaktfarbe erreicht die Höchsthäufigkeit (oder
        # kommt ihr nahe) nur, wenn der Kern selbst auf noch mehr, noch seltenere
        # Exaktfarben verteilt ist.
        grund_schaetzung = Counter(eintrag[2] for eintrag in aenderungen).most_common(1)[0][0]
        grund_lum = relative_luminance(grund_schaetzung)
        mit_haeufigkeit = Counter(eintrag[1] for eintrag in aenderungen)
        max_haeufigkeit = mit_haeufigkeit.most_common(1)[0][1]
        kandidaten = [
            farbe for farbe, anzahl in mit_haeufigkeit.items() if anzahl >= max_haeufigkeit / 2
        ]
        vordergrund = max(kandidaten, key=lambda farbe: abs(relative_luminance(farbe) - grund_lum))
        ohne_bei_vordergrund = Counter(
            eintrag[2] for eintrag in aenderungen if eintrag[1] == vordergrund
        )
        hintergrund = ohne_bei_vordergrund.most_common(1)[0][0]

        verhaeltnis = contrast(vordergrund, hintergrund)
        # (Befund F11, Nachprüfung d00e7c9): `font.pixelSize()` liefert -1, wenn die
        # Schrift über `pointSize` statt `pixelSize` gesetzt wurde (Qt kennt nur eine der
        # beiden Angaben je Font, nie beide) — `QFontInfo(font).pixelSize()` liefert
        # stattdessen die tatsächlich aufgelöste Pixelgröße, unabhängig vom Weg der
        # Angabe. Die WCAG-Schwelle für „großer Text" ist wörtlich 18,66 px fett, nicht
        # der bisher gerundete Wert 19.
        groesse = QFontInfo(font).pixelSize() if font is not None else 0
        fett = font.weight() >= 600 if font is not None else False
        grenze = 3.0 if (groesse >= 24 or (groesse >= 18.66 and fett)) else 4.5
        marke = "!" if verhaeltnis < grenze else " "
        zeilen.append(
            f"{marke} {verhaeltnis:5.2f}:1 Soll {grenze} {groesse:.0f}px "
            f"#{vordergrund[0]:02x}{vordergrund[1]:02x}{vordergrund[2]:02x} auf "
            f"#{hintergrund[0]:02x}{hintergrund[1]:02x}{hintergrund[2]:02x} {text!r}"
        )

    for eintrag in verblasst:
        zeilen.append(f"! `opacity` auf Text: {eintrag}")

    if not gemessen:
        return 2, zeilen, gemessen, uebersprungen
    befunde = sum(1 for zeile in zeilen if zeile.startswith("!"))
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
