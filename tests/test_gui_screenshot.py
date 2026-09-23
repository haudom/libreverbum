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


def test_gui_screenshot_flags_mixed_box_content(tmp_path: Path) -> None:
    """Befund B3 (Durchsicht d993e3e), Kernfall: ein dunkler Balken im selben Textkasten
    wie ein blasser Text (`tests/qml_fixtures/Underline.qml`, der Balken nach dem Text
    deklariert, liegt beim Zeichnen also über ihm). Der alte Weg maß die häufigste oder
    extremste Farbe im **ganzen** Kasten als Vordergrund — der Balken hätte den blassen
    Text dabei überdeckt und einen guten Kontrast vorgetäuscht. Gemessen wird deshalb
    **isoliert**: Jedes andere sichtbare, überschneidende und nach dem Text gezeichnete
    Element wird vor der Messung ausgeblendet, das Fenster neu gegriffen.

    Verfälschung: in `check_contrast` die Zeile `aktives_bild = window.grabWindow()`
    entfernen (`aktives_bild` bliebe immer `image`, das ursprüngliche, unisolierte Bild)
    → der Kontrastwert für „Blasser Text mit Linie" träfe den Balken (rund 12,5:1, ohne
    „!") statt den blassen Text selbst (rund 1,2:1) — `returncode` bliebe zwar 1 (die
    „GEMISCHTER KASTENINHALT"-Zeile allein setzt das schon), aber ohne den zweiten
    Beleg unten wäre das falsche Grün an der eigentlichen Messung unentdeckt geblieben."""
    result = _run_fixture("Underline", tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "GEMISCHTER KASTENINHALT" in result.stdout
    assert re.search(r"!\s+1\.\d\d:1.*'Blasser Text mit Linie'", result.stdout), (
        "der Kontrastwert der Textstelle selbst muss unter der Schwelle liegen, nicht "
        f"nur die Zusatzmeldung: {result.stdout}"
    )


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
