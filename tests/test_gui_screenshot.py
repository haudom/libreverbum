"""Prüft `tools/gui_screenshot.py` gegen den Bestand: Läuft als eigener Prozess (Aufruf wie
im Modulkopf beschrieben), damit jeder Testfall eine eigene `QGuiApplication` bekommt
(bauplan-phase2.md, Abschnitt 8: „Genau eine `QGuiApplication` je Prozess").

Eine Durchsicht (Commit `d993e3e`) hat die erste Fassung dieses Werkzeugs in sieben von
rund zwanzig Angriffen „Ergebnis: OK" melden lassen, obwohl die Seite kaputt war — die
Befunde B1–B4 und B6 unten sind je ein Fall aus dieser Tabelle, als eigener Test
festgehalten, damit keiner von ihnen je wieder unbemerkt zurückkommt. Die
Angriffsvorlagen liegen unter `tests/qml_fixtures/` (nicht unter `gui/qml/`, das nicht mit
absichtlich blassen Testfarben verschmutzt werden soll — `tests/test_design_tokens.py`
klammert das Verzeichnis deshalb aus, siehe dort).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "gui_screenshot.py"
FONTS = REPO_ROOT / "gui" / "fonts"
FIXTURES = REPO_ROOT / "tests" / "qml_fixtures"

pytestmark = pytest.mark.needs_gui


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        cwd=REPO_ROOT,
    )


def _run_fixture(screen: str, tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    png = tmp_path / f"{screen}.png"
    return _run(
        screen,
        str(png),
        "--offscreen",
        "--qml-dir",
        str(FIXTURES),
        "--font-dir",
        str(FONTS),
        "--size",
        "900x600",
        *extra,
    )


def test_gui_screenshot_renders_the_placeholder_screen_without_findings(tmp_path: Path) -> None:
    """Gegen den echten Bestand (`gui/qml/Placeholder.qml`, über `Main.qml` mit Fenster
    und Loader eingebettet — Befund B6, Durchsicht d993e3e: die erste Fassung rendere
    `<screen>.qml` einzeln, ohne je `Main.qml` zu laden): 0 Warnungen, kein Layoutbefund,
    jede Textstelle über ihrer Kontrastschwelle."""
    png = tmp_path / "placeholder.png"
    result = _run("Placeholder", str(png), "--offscreen")

    assert result.returncode == 0, result.stdout + result.stderr
    assert png.is_file()
    assert "0 Warnungen" in result.stdout
    assert "0 Befunde" in result.stdout
    assert "Textstellen gemessen" in result.stdout
    assert "Ergebnis: OK" in result.stdout


def test_gui_screenshot_reports_a_blank_screen_instead_of_passing_silently(tmp_path: Path) -> None:
    """Untergrenze (Befund B4): Ein Bildschirm, der nichts zeichnet, gilt selbst als
    Fehlschlag — nicht als „0 Warnungen, 0 Befunde".

    Verfälschung: die Prüfung auf ein einfarbiges Bild aus `render()` entfernen (Vorbild
    `tools/design_mockup/shot.py`) → dieser Test wird rot, weil `returncode` dann 0 statt
    2 ist und die Meldung „einfarbig" fehlt."""
    qml_dir = tmp_path / "qml"
    qml_dir.mkdir()
    (qml_dir / "Blank.qml").write_text(
        "import QtQuick\nItem {\n    width: 10\n    height: 10\n}\n", encoding="utf-8"
    )
    png = tmp_path / "blank.png"

    result = _run(
        "Blank", str(png), "--offscreen", "--qml-dir", str(qml_dir), "--font-dir", str(FONTS)
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "einfarbig" in (result.stdout + result.stderr)
    assert not png.is_file(), "ein einfarbiges Bild hätte nicht geschrieben werden dürfen"


def test_gui_screenshot_fails_on_a_qml_binding_warning(tmp_path: Path) -> None:
    """Eine falsche Bindung erzeugt eine QML-Warnung, und die zählt als Fehlschlag
    (Regel 13) — nicht nur als Rauschen in der Ausgabe.

    Verfälschung: `qInstallMessageHandler`/`engine.warnings` in `render()` nicht mehr
    auswerten → `returncode` bliebe 0 trotz der `ReferenceError` unten."""
    qml_dir = tmp_path / "qml"
    qml_dir.mkdir()
    (qml_dir / "Broken.qml").write_text(
        "import QtQuick\n"
        "Rectangle {\n"
        "    width: 400\n"
        "    height: 300\n"
        '    color: "white"\n'
        "    Text {\n"
        '        text: "kaputt"\n'
        "        color: nichtVorhanden\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    png = tmp_path / "broken.png"

    result = _run(
        "Broken", str(png), "--offscreen", "--qml-dir", str(qml_dir), "--font-dir", str(FONTS)
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "ReferenceError" in (result.stdout + result.stderr)


def test_gui_screenshot_flags_low_contrast_text(tmp_path: Path) -> None:
    """Befund B3 (Durchsicht d993e3e), Grundfall: ein Text mit Kontrast deutlich unter der
    Schwelle wird gemeldet (`tests/qml_fixtures/Pale.qml`).

    Verfälschung: in `check_contrast` `grenze = 0.0` statt `3.0`/`4.5` setzen → jeder
    Kontrast besteht, `returncode` bliebe 0 und „Blasser Text" käme nicht als Fehlschlag
    vor."""
    result = _run_fixture("Pale", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Blasser Text" in result.stdout


def test_gui_screenshot_flags_layout_overflow(tmp_path: Path) -> None:
    """Grundfall Überlauf (`tests/qml_fixtures/Overflow.qml`): ein Text, breiter als sein
    unmittelbares Elternelement.

    Verfälschung: die Überlaufprüfung in `check_layout` (`if worst > tolerated: ...`)
    entfernen → `returncode` bliebe 0, „ÜBERLAUF" käme nicht vor."""
    result = _run_fixture("Overflow", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "ÜBERLAUF" in result.stdout


def test_gui_screenshot_flags_truncated_text(tmp_path: Path) -> None:
    """Grundfall Kürzung (`tests/qml_fixtures/Elide.qml`): ein zu schmaler Text mit
    `elide: Text.ElideRight`.

    Verfälschung: `if child.property("truncated") and ...` in `check_layout` entfernen →
    `returncode` bliebe 0, „GEKÜRZT" käme nicht vor."""
    result = _run_fixture("Elide", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "GEKÜRZT" in result.stdout


def test_gui_screenshot_measures_label_required_delegate_and_custom_component(
    tmp_path: Path,
) -> None:
    """Befund B1 (Durchsicht d993e3e): `className() == "QQuickText"` (der alte Vergleich)
    übersah ein `Label` (erbt von `Text`, aber `className()` heißt `"QQuickLabel"`), einen
    Repeater-Delegaten mit `required property` (eigener QML-Untertyp) und eine eigene
    Komponente mit Text-Wurzel — keiner der drei hätte einen blassen Text gemeldet
    (`tests/qml_fixtures/TextKinds.qml`, drei Textstellen, alle blass).

    Verfälschung: `_text_kind` auf `item.metaObject().className() == "QQuickText"` (den
    alten wörtlichen Vergleich) zurücksetzen → `returncode` würde 0, keine der drei
    Textstellen (`Label-Text`, `Eigene Komponente`, `required-Delegat`) käme in der
    Ausgabe vor."""
    result = _run_fixture("TextKinds", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Label-Text" in result.stdout
    assert "Eigene Komponente" in result.stdout
    assert "required-Delegat" in result.stdout


def test_gui_screenshot_measures_text_field_content(tmp_path: Path) -> None:
    """Befund B1, vierter Fall: ein `TextField` — weder `className() == "QQuickText"`
    noch `inherits("QQuickText")` trifft zu, `TextInput` ist ein eigener Klassenzweig
    (`tests/qml_fixtures/TextFieldScreen.qml`, blasser Eingabetext).

    Verfälschung: den `input`-Zweig aus `_text_kind` entfernen (nur noch
    `inherits("QQuickText")`) → `returncode` würde 0, „Blasser Eingabetext" käme in der
    Ausgabe nicht vor."""
    result = _run_fixture("TextFieldScreen", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Blasser Eingabetext" in result.stdout


def test_gui_screenshot_reports_text_hidden_under_a_zero_sized_holder(tmp_path: Path) -> None:
    """Befund B2 (Durchsicht d993e3e): Ein 0×0-Halter ließ den alten Code den ganzen
    Teilbaum überspringen (`continue`, noch vor dem rekursiven Abstieg) — ein Text weit
    außerhalb des Fensters darunter wurde nie besucht (`tests/qml_fixtures/
    ZeroSizeHolder.qml`).

    Verfälschung: den alten `continue` bei `child.width() == 0 and child.height() == 0`
    in `check_layout` wiederherstellen → `returncode` würde 0 statt 1, „AUSSERHALB DES
    SICHTBAREN BEREICHS" käme nicht vor — der Teilbaum unter `holder` würde gar nicht erst
    besucht."""
    result = _run_fixture("ZeroSizeHolder", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "AUSSERHALB DES SICHTBAREN BEREICHS" in result.stdout


def test_gui_screenshot_measures_the_true_contrast_despite_a_line_crossing_the_box(
    tmp_path: Path,
) -> None:
    """Nachprüfung d00e7c9, Befunde F1–F3: ein dunkler Balken im selben Textkasten wie ein
    blasser Text (`tests/qml_fixtures/Underline.qml`, der Balken nach dem Text deklariert,
    liegt beim Zeichnen also über ihm). Der alte Weg (Commit `d00e7c9`) meldete das bloße
    Überschneiden bereits als eigenen Befund „GEMISCHTER KASTENINHALT" — an jedem der
    sechzehn bekannt guten Mockup-Bilder, weil dort ein Fokusring, eine `MouseArea` oder
    ein weggerollter, per `clip` unsichtbarer Nachbar jeden Kasten berühren kann, ohne ihn
    zu betreffen (Befund F1). Das Differenzbild (`check_contrast`) kennt diesen Begriff
    nicht mehr: Es greift das Fenster einmal mit und einmal ohne die Textstelle selbst und
    misst nur noch, was sich dabei tatsächlich ändert.

    Verfälschung: `item.setOpacity(0.0)` durch `pass` ersetzen (die Textstelle bleibt
    sichtbar, „mit" und „ohne" wären identisch) → `aenderungen` bliebe für jede Textstelle
    leer, „UNSICHTBAR" käme für **jede** Textstelle im Bild, nicht nur für „Blasser Text
    mit Linie" — die Zusicherung unten wird rot, weil der falsche Kontrastwert (rund
    1,2:1) dann gar nicht mehr vorkäme."""
    result = _run_fixture("Underline", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "GEMISCHTER KASTENINHALT" not in result.stdout
    assert re.search(r"!\s+1\.\d\d:1.*'Blasser Text mit Linie'", result.stdout), (
        f"der Kontrastwert der Textstelle selbst muss unter der Schwelle liegen: {result.stdout}"
    )


def test_gui_screenshot_flags_text_wider_than_its_own_box(tmp_path: Path) -> None:
    """Befund F4 (Nachprüfung d00e7c9): `check_layout` maß bisher nur die Höhe
    (`implicitHeight` gegen `height`), nie die Breite. Ein Text mit fester, zu schmaler
    Breite, ohne `elide` und ohne Umbruch, überschreibt seinen Nachbarn unbemerkt
    (`tests/qml_fixtures/WidthOverflow.qml`, wie `NxOwnBox` in der Nachprüfung).

    Verfälschung: die `TEXT ZU BREIT`-Prüfung (Vergleich `contentWidth - child.width()`)
    aus `check_layout` entfernen → `returncode` würde 0, „TEXT ZU BREIT" käme nicht vor."""
    result = _run_fixture("WidthOverflow", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "TEXT ZU BREIT" in result.stdout


def test_gui_screenshot_names_a_mismatched_text_property_and_exempts_a_mirrored_one(
    tmp_path: Path,
) -> None:
    """Befund F5 (Nachprüfung d00e7c9): „ÜBERSEHENE TEXTEIGENSCHAFT" war bisher ein
    einziger Vergleich zweier Zahlen über den ganzen Baum — er schlug bei **jeder**
    Komponente mit eigener `property string text` an, ohne sie zu nennen, MessageBox im
    Mockup und jeden Controls-`Button` eingeschlossen, obwohl deren `text` nur den eines
    eigenen `Text`-Nachfahren spiegelt (`tests/qml_fixtures/MirroredText.qml`: eine
    Komponente spiegelt ihren Wert richtig, eine zweite zeigt einen anderen Text als ihr
    Nachfahre).

    Verfälschung: die Ausnahmeprüfung (`ausgenommen = any(...)`) aus `check_layout`
    entfernen, sodass jeder Kandidat unbedingt gemeldet wird → `gespiegelt` käme
    fälschlich als zweiter Befund vor, nicht nur `auseinandergelaufen` — die Zusicherung
    unten (genau **ein** Fundstellen-Name) wird rot."""
    result = _run_fixture("MirroredText", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "auseinandergelaufen" in result.stdout
    assert "ÜBERSEHENE TEXTEIGENSCHAFT" in result.stdout
    ueberzaehlige = result.stdout.count("ÜBERSEHENE TEXTEIGENSCHAFT")
    assert ueberzaehlige == 1, f"nur `auseinandergelaufen` darf gemeldet werden: {result.stdout}"
    assert "gespiegelt" not in result.stdout.split("ÜBERSEHENE TEXTEIGENSCHAFT")[1]


def test_gui_screenshot_distinguishes_occluded_from_invisible_text(tmp_path: Path) -> None:
    """Befund F3-Vorschlag (Nachprüfung d00e7c9): Ändert sich beim Ausblenden einer
    Textstelle nichts, ist sie entweder deckungsgleich mit ihrem Grund (UNSICHTBAR,
    `tests/qml_fixtures/InvisibleAndEmpty.qml`, „farbgleich") oder von einem anderen,
    später gezeichneten Element vollständig verdeckt (ÜBERDECKT,
    `tests/qml_fixtures/Occluded.qml`, „verdeckt") — unterschieden über `_find_occluder`.

    Verfälschung: in `check_contrast` `verdecker = _find_occluder(...)` durch
    `verdecker = None` ersetzen → `Occluded` meldete „UNSICHTBAR" statt „ÜBERDECKT", die
    zweite Zusicherung unten wird rot."""
    unsichtbar = _run_fixture("InvisibleAndEmpty", tmp_path)
    assert unsichtbar.returncode == 1, unsichtbar.stdout + unsichtbar.stderr
    assert "! UNSICHTBAR: 'Verschwindet im Grund'" in unsichtbar.stdout
    assert "ÜBERDECKT" not in unsichtbar.stdout

    ueberdeckt = _run_fixture("Occluded", tmp_path)
    assert ueberdeckt.returncode == 1, ueberdeckt.stdout + ueberdeckt.stderr
    assert "ÜBERDECKT" in ueberdeckt.stdout
    assert "'Wichtiger Hinweis, verdeckt'" in ueberdeckt.stdout


def test_gui_screenshot_skips_empty_text_without_flagging_it(tmp_path: Path) -> None:
    """Befund F6 (Nachprüfung d00e7c9): Ein leerer Text hat nichts zu messen — er wird
    übersprungen, nicht als „UNSICHTBAR" gemeldet und nicht mitgezählt
    (`tests/qml_fixtures/InvisibleAndEmpty.qml`, „leer").

    Verfälschung: die Bedingung `if text.strip():` in `check_contrast` entfernen (jede,
    auch die leere Textstelle wird angehängt) → „leer" käme mit einer eigenen Zeile vor
    (leerer String in Anführungszeichen), die Zusicherung unten wird rot."""
    result = _run_fixture("InvisibleAndEmpty", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr  # wegen "farbgleich"
    assert "''" not in result.stdout
    assert "2 Textstellen gemessen" in result.stdout


def test_gui_screenshot_does_not_flag_a_font_generic_alias_as_unloaded(tmp_path: Path) -> None:
    """Befund F8 (Nachprüfung d00e7c9): RichText mit `<font face="Inter">`, aber ohne
    eigenes `font.family` — die Item-eigene Angabe bleibt der QML-Vorgabewert ("Sans
    Serif", ein generischer Alias, keine echte Familie). Der alte Vergleich
    (`font.family()` gegen `QFontInfo(font).family()`) meldete dafür „SCHRIFT NICHT
    GELADEN", obwohl die Textstelle tatsächlich ordentlich rendert
    (`tests/qml_fixtures/FontEdgeCases.qml`, „richtext").

    Verfälschung: die Ausnahme `if erwartet.strip().lower() not in _GENERISCHE_FAMILIEN:`
    durch eine bedingungslose Prüfung ersetzen → „SCHRIFT NICHT GELADEN" käme für
    „richtext" vor, die Zusicherung unten wird rot."""
    result = _run_fixture("FontEdgeCases", tmp_path)

    assert "SCHRIFT NICHT GELADEN" not in result.stdout, result.stdout


def test_gui_screenshot_resolves_point_size_fonts_to_a_real_pixel_size(tmp_path: Path) -> None:
    """Befund F11 (Nachprüfung d00e7c9): `font.pixelSize()` liefert -1, wenn die Schrift
    über `pointSize` statt `pixelSize` gesetzt wurde (Qt kennt nur eine der beiden Angaben
    je Font) — die WCAG-Schwelle fiele dann auf 4,5 statt der korrekten 3,0 für großen Text
    (`tests/qml_fixtures/FontEdgeCases.qml`, „punktgroesse", 30 pt).

    Verfälschung: `QFontInfo(font).pixelSize()` durch `font.pixelSize()` ersetzen →
    „-1px" käme in der Ausgabe vor, die Zusicherung unten wird rot."""
    result = _run_fixture("FontEdgeCases", tmp_path)

    assert "-1px" not in result.stdout, result.stdout
    assert re.search(r"Soll 3\.0 \d\dpx.*'Grosse Schrift in Punkt'", result.stdout), result.stdout


def test_gui_screenshot_catches_console_warn_on_the_direct_qml_dir_path(tmp_path: Path) -> None:
    """Befund F7 (Nachprüfung d00e7c9): Der Direktpfad (`--qml-dir` außerhalb von
    `gui/qml/`, für Angriffsvorlagen) hatte vor der Nachbesserung keinen eigenen
    `qInstallMessageHandler` — `console.warn` und Qt-eigene Meldungen liefen unbemerkt
    durch, „Ergebnis: OK" trotz kaputter Seite (`tests/qml_fixtures/ConsoleWarn.qml`).

    Verfälschung: den Aufruf `install_message_handler(warnings)` in `_load_direct`
    entfernen → `returncode` bliebe 0, „F7-Testwarnung" käme nicht in der Ausgabe vor."""
    result = _run_fixture("ConsoleWarn", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "F7-Testwarnung" in result.stdout + result.stderr


def test_gui_screenshot_reports_a_window_below_main_qml_minimum_size(tmp_path: Path) -> None:
    """Befund F12 (Nachprüfung d00e7c9): Unter `--offscreen` klemmt Qt eine angeforderte
    Größe nicht von selbst auf `Main.qml`s `minimumWidth`/`minimumHeight` — 700×400 hätte
    klaglos ohne jeden Hinweis gerendert, obwohl `Main.qml` 900×600 verlangt.

    Verfälschung: den Vergleich `window.width() < min_w or window.height() < min_h` in
    `render()` entfernen → die Meldung „unter Main.qml-Mindestgröße" käme nicht vor,
    `returncode` bliebe 0."""
    png = tmp_path / "placeholder.png"
    result = _run("Placeholder", str(png), "--offscreen", "--size", "700x400")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "unter Main.qml-Mindestgröße" in result.stdout + result.stderr


def test_gui_screenshot_does_not_bypass_main_qml_via_a_relative_qml_dir(tmp_path: Path) -> None:
    """Befund F12, zweiter Fall: `--qml-dir gui/qml` (relativ statt der absoluten Vorgabe)
    wich bisher, ohne jede Meldung, auf den Direktpfad aus — derselbe Bildschirm, aber
    ohne `Main.qml`, ohne Fenster, ohne Mindestgröße.

    Verfälschung: `_is_main_qml_path` von `qml_dir.resolve() == GUI_QML.resolve()` auf
    `qml_dir == GUI_QML` zurücksetzen → dieser Aufruf liefe über den Direktpfad, „›
    screenStack" (der Loader aus `Main.qml`) käme in keiner Fundmeldung vor, und die
    Zusicherung unten (Mindestgrößen-Meldung bei zu kleiner Anforderung) wird rot."""
    png = tmp_path / "placeholder.png"
    result = _run(
        "Placeholder", str(png), "--offscreen", "--qml-dir", "gui/qml", "--size", "700x400"
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "unter Main.qml-Mindestgröße" in result.stdout + result.stderr


def test_gui_screenshot_finds_no_finding_on_a_real_mockup_screen(tmp_path: Path) -> None:
    """Abnahmekriterium der Nachprüfung d00e7c9: Der bekannt gute Bestand ist grün — nicht
    nur der Platzhalter, sondern auch die vier fertig gestalteten Mockup-Bildschirme aus
    `tools/design_mockup/qml/`. Diese Gegenprobe rendert `Triage` (den Datenfall `lang`,
    rund 117 Textstellen, darunter eine am unteren Rand angeschnittene Listenzeile) und
    verlangt „Ergebnis: OK" — die Kehrseite der Angriffstests oben: Ein Werkzeug, das nur
    noch rot melden kann, wäre so nutzlos wie eines, das nur noch grün meldet.

    Verfälschung: die Zusicherung `ganz = (sichtbar.width() >= ... and ...)` in
    `check_contrast` durch `ganz = True` ersetzen (jeder, auch ein nur angeschnittener
    Kasten, gilt als ganz sichtbar) → die angeschnittene letzte Listenzeile bekäme einen
    Fehlalarm „ÜBERDECKT"/„UNSICHTBAR", die Zusicherung unten wird rot."""
    png = tmp_path / "triage.png"
    result = _run(
        "Triage",
        str(png),
        "--offscreen",
        "--qml-dir",
        str(REPO_ROOT / "tools" / "design_mockup" / "qml"),
        "--fall",
        "lang",
        "--size",
        "1280x800",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ergebnis: OK" in result.stdout


def test_gui_screenshot_fails_when_the_font_directory_is_empty(tmp_path: Path) -> None:
    """Befund B4 (Durchsicht d993e3e): Ein leeres Schriftverzeichnis lief bisher klaglos
    durch — die Ladeschleife fand keine `*.ttf`-Datei und meldete das nicht, die Seite
    zeigte Ersatzkästchen statt der eigentlichen Schrift, und das Werkzeug meldete „OK".

    Verfälschung: die Prüfung `if not families: ...` in `_load_direct` entfernen →
    `returncode` würde 0 statt 2, „Keine Schrift" käme nicht in der Ausgabe vor."""
    empty_fonts = tmp_path / "leer"
    empty_fonts.mkdir()
    png = tmp_path / "pale.png"

    result = _run(
        "Pale",
        str(png),
        "--offscreen",
        "--qml-dir",
        str(FIXTURES),
        "--font-dir",
        str(empty_fonts),
        "--size",
        "900x600",
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Keine Schrift" in (result.stdout + result.stderr)
    assert not png.is_file()


def test_gui_screenshot_fails_when_a_theme_font_family_is_missing(tmp_path: Path) -> None:
    """Befund B4, zweiter Fall — gilt für den echten Bildschirm (`--qml-dir gui/qml`, über
    `gui.app.load_fonts`): Ein Schriftverzeichnis, das eine Datei enthält, aber nicht
    **beide** von `Theme.qml` genannten Familien (`fonts.book` = Literata, `fonts.ui` =
    Inter) mitbringt, lief bisher ebenso klaglos durch. Kopiert wird absichtlich nur die
    echte `Inter`-Datei — die Familie kommt aus dem inneren Namensfeld der Schriftdatei,
    nicht aus dem Dateinamen, ein umbenannter Dateiname allein würde die Zusicherung also
    nicht auslösen.

    Verfälschung: die Prüfung `if fehlend: raise RuntimeError(...)` in
    `gui.app.load_fonts` entfernen → `returncode` würde 0 statt 2, „Theme.fonts nennt"
    käme nicht in der Ausgabe vor."""
    inter_font = next(FONTS.glob("Inter*.ttf"))
    ohne_literata = tmp_path / "ohne-literata"
    ohne_literata.mkdir()
    (ohne_literata / inter_font.name).write_bytes(inter_font.read_bytes())
    png = tmp_path / "placeholder.png"

    result = _run("Placeholder", str(png), "--offscreen", "--font-dir", str(ohne_literata))

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Theme.fonts nennt" in (result.stdout + result.stderr)
    assert not png.is_file()


def test_gui_screenshot_measures_the_true_contrast_of_a_filled_control_background(
    tmp_path: Path,
) -> None:
    """Befund N1 (Nachprüfung 00ce53b): Ein `TextField` mit eigener Fläche
    (`tests/qml_fixtures/FieldBackground.qml`, Feldfläche `#ffffff`, Seite `#e3dfd6` —
    absichtlich verschieden). `item.setOpacity(0)` blendete beim Ausblenden die eigene
    Feldfläche mit aus — das „ohne"-Bild zeigte dadurch die Seite statt der echten
    Feldfläche, und die Messung träfe Schrift gegen den falschen Grund.

    Verfälschung: in `check_contrast` das Ausblenden per `color` wieder durch
    `item.setOpacity(0.0)` ersetzen → der gemeldete Grund wäre `#e3dfd6` (die Seite)
    statt `#ffffff` (die echte Feldfläche); die zweite Zusicherung unten wird rot."""
    result = _run_fixture("FieldBackground", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Eingabe hell auf hell" in result.stdout
    assert "auf #ffffff 'Eingabe hell auf hell'" in result.stdout, result.stdout


def test_gui_screenshot_does_not_flag_a_well_contrasted_filled_field(tmp_path: Path) -> None:
    """Gegenprobe zu N1 (Nachprüfung 00ce53b): Dieselbe Bauform — ein Eingabefeld mit
    eigener, von der Seite verschiedener Fläche — aber mit gut lesbarer Schrift
    (`tests/qml_fixtures/FieldBackgroundGood.qml`). Ein falsch-rot messendes Werkzeug
    (Feldfläche beim Ausblenden mit entfernt) meldete hier einen Kontrastfehler gegen die
    Seitenfarbe, obwohl die Schrift auf ihrer eigenen Fläche einwandfrei ist — die Falle,
    die `tests/qml_fixtures/TextFieldScreen.qml` vor dieser Nachbesserung verdeckte, weil
    Feldfläche und Seite dort zufällig gleich gefärbt waren (`beobachtungen/
    2026-09-23-ap15-nachpruefung-runde2.md`).

    Verfälschung: dieselbe wie oben (`setOpacity(0)` statt `color`) → der Grund stünde
    als `#e3dfd6` (die Seite) in der Ausgabe statt `#fdfcfa` (die echte Feldfläche) — die
    zweite Zusicherung unten wird rot, auch wenn der Kontrast zufällig gegen beide Gründe
    reicht und `returncode` allein die Verfälschung nicht zeigt."""
    result = _run_fixture("FieldBackgroundGood", tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ergebnis: OK" in result.stdout
    assert "auf #fdfcfa 'Gut lesbare Eingabe'" in result.stdout, result.stdout


def test_gui_screenshot_flags_the_worst_color_span_in_rich_text(tmp_path: Path) -> None:
    """Befund N2 (Nachprüfung 00ce53b): RichText mit zwei Farbspannen in einer Textstelle
    (`tests/qml_fixtures/ColorSpan.qml`) — ein langer, gut lesbarer Teil und eine kurze,
    blasse Randbemerkung („Warnung"). Die Randbemerkung liefert für sich genommen weit
    weniger geänderte Pixel als der lange Teil; gemessen werden muss trotzdem sie, nicht
    der bessere Teil derselben Textstelle.

    Verfälschung: in `check_contrast` `nennenswert` durch `[max(klumpen, key=len)]`
    ersetzen (immer nur der größte Klumpen zählt) → der lange, gut lesbare Teil würde
    gewählt, „Warnung" käme nicht als eigener, blasser Fund vor, `returncode` bliebe 0."""
    result = _run_fixture("ColorSpan", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "#cfcabf" in result.stdout, result.stdout


def test_gui_screenshot_flags_a_partial_occlusion(tmp_path: Path) -> None:
    """Befund N3 (Nachprüfung 00ce53b): Ein Rechteck mit höherem `z` deckt die rechte
    Hälfte eines Satzes ab (`tests/qml_fixtures/Overlap.qml`) — die linke Hälfte zeigt
    weiterhin normal Tinte. „Irgendeine Änderung beim Ausblenden" allein sagt nichts über
    den fehlenden Teil des Satzes; erst `_covering_elements` erkennt die Überdeckung.

    Verfälschung: den Aufruf von `_covering_elements` für eine Textstelle mit eigener
    Tinte (der zweite, nach `TEILWEISE VERDECKT` benannte Aufruf in `check_contrast`)
    entfernen → „TEILWEISE VERDECKT" käme nicht vor, `returncode` bliebe an dieser Stelle
    unbeeinflusst von der Verdeckung."""
    result = _run_fixture("Overlap", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "TEILWEISE VERDECKT von deckel" in result.stdout


def test_gui_screenshot_does_not_flag_a_highlight_behind_text(tmp_path: Path) -> None:
    """Gegenprobe zu N3 (Nachprüfung 00ce53b): Ein Rechteck überschneidet den Textkasten
    geometrisch genauso wie ein Deckel, liegt aber mit niedrigerem `z` **hinter** dem Text
    (`tests/qml_fixtures/HighlightBehindText.qml`, wie die laufende Zeile einer Liste,
    `Theme.qml`-Token `marked`) — eine reine Baumreihenfolge ohne `z` hätte das fälschlich
    als Verdeckung gemeldet (Befund F1/F2 der Nachprüfung von `d00e7c9`, an allen 16
    Mockup-Bildern).

    Verfälschung: `_painted_after` in `_covering_elements` durch `True` ersetzen (jedes
    spätere Element gilt als obenauf, `z` wird ignoriert) → „TEILWEISE VERDECKT" oder
    „ÜBERDECKT" käme fälschlich vor, `returncode` würde 1 statt 0."""
    result = _run_fixture("HighlightBehindText", tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ergebnis: OK" in result.stdout


def test_gui_screenshot_flags_an_unbreakable_word_under_word_wrap(tmp_path: Path) -> None:
    """Befund N4 (Nachprüfung 00ce53b): Ein unteilbares, zusammengesetztes Wort mit
    `wrapMode: Text.WordWrap` in einem schmalen Kasten (`tests/qml_fixtures/
    WrapOverflow.qml`) — Qt bricht bei `WordWrap` nur an Wortgrenzen, ein einzelnes zu
    breites Wort läuft deshalb unverändert über den Kasten hinaus. Deutsche Komposita in
    schmalen Spalten sind hier der Normalfall, nicht der Ausnahmefall.

    Verfälschung: die Bedingung in `check_layout` von
    `wrap_mode not in (_TEXT_WRAP_ANYWHERE, _TEXT_WRAP)` zurück auf
    `wrap_mode == _TEXT_NO_WRAP` setzen → „TEXT ZU BREIT" käme nicht vor, `returncode`
    wäre nicht mehr an dieser Stelle 1."""
    result = _run_fixture("WrapOverflow", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "TEXT ZU BREIT" in result.stdout


def test_gui_screenshot_flags_opacity_on_an_ancestor_of_text(tmp_path: Path) -> None:
    """Befund N7 (Nachprüfung 00ce53b): `opacity` sitzt auf einem Vorfahren der
    Textstelle, nicht auf ihr selbst (`tests/qml_fixtures/AncestorOpacity.qml`) — die
    Hausregel „opacity nie auf Text" (CLAUDE.md, Gestaltung) galt bisher nur für die
    eigene Opacity der Textstelle.

    Verfälschung: in `check_contrast` die Suche über `_ancestors(child)` entfernen und
    nur noch `child.opacity()` prüfen → „Vorfahr" käme in keiner Zeile vor, `returncode`
    bliebe an dieser Stelle unbeeinflusst von der gedämpften Textstelle."""
    result = _run_fixture("AncestorOpacity", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "opacity 0.80, Vorfahr" in result.stdout
