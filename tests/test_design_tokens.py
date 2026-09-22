"""Prüft die Zusicherung aus technik.md §14: `gui/qml/Theme.qml` ist die **einzige** Quelle
für Farbe und Schrift.

Ein reiner Textlauf über alle QML-Dateien — kein PySide6, keine Marke `needs_gui`: Die
Regel gilt auch dort, wo Qt nicht installiert ist, und ein übersprungener Test hätte hier
denselben Wert wie keiner.

Vorgezogen aus bauplan-phase2.md AP 15 („Neuer Grep-Test: keine Hex-Farbe und kein
`font.family` außerhalb `Theme.qml`"): Mit AP 14 stehen bereits zwanzig QML-Dateien im
Bestand, und ohne diese Prüfung könnte die Regel vier Arbeitspakete lang still brechen.

**Wie die Vorgabe zu lesen ist.** Wörtlich genommen verböte sie jedes `font.family`
außerhalb der Token-Datei — dann stünde keine Schrift mehr an einem Text. Gemeint ist der
**Wert**: Eine Schriftfamilie wird nie benannt, sie wird aus `Theme.fonts` genommen.
Dasselbe für Farbe: kein Hexwert, kein Farbname, keine im Bauteil erzeugte Tönung.

**Woran sich die Muster messen lassen müssen.** Ein Test über Textmuster prüft nicht die
Regel, sondern eine Schreibweise. QML kennt für dieselbe Aussage mehrere, und vier davon
kamen bis zur Nachbesserung von AP 14 ungesehen durch (Befund B2, Durchsicht b2d5cab):
einfache Anführungszeichen (`'white'`), der bedingte Ausdruck (`color: b ? "white" :
Theme.ink` — im Bestand zehnmal vorhanden), der Funktionsaufruf (`Qt.color("white")`) und
die gruppierte Eigenschaft (`font { family: "Arial" }`). Wer die Muster ändert, zählt
deshalb zuerst die Schreibweisen der Sprache auf und verfälscht gegen jede einzeln.

**Was `transparent` hier soll.** Es ist keine Farbe der Richtung, sondern die Abwesenheit
einer Fläche, und es gibt dafür bewusst kein Token. Es steht deshalb als **geschlossene**
Ausnahme in `ALLOWED_COLOR_WORDS` — unter anderem an zwei bedingten Ausdrücken
(`ActionButton.qml`, `MessageBox.qml`), die der Test erst seit dieser Fassung überhaupt
sieht.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "gui" / "qml" / "Theme.qml"

# Hexfarbe im QML-Sinn: #RGB, #RGBA, #RRGGBB, #AARRGGBB. Die Anführungszeichen stehen
# hier absichtlich nicht im Muster: `'#fff'` ist derselbe Verstoß wie `"#fff"`.
HEX_COLOR = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")

# Eine Schriftfamilie darf nur aus den Token kommen. Gesucht wird `family:` selbst, nicht
# `font.family:` — QML kennt für dieselbe Eigenschaft zwei Schreibweisen, die gepunktete
# und die **gruppierte** (`font { family: …; pixelSize: … }`). Das Muster auf die
# gepunktete zu beschränken, hieße: Wer die Gruppe schreibt, schreibt am Test vorbei
# (Befund B2, Durchsicht b2d5cab).
FONT_FAMILY = re.compile(r"\bfamily\s*:\s*(.+)")
FONT_FROM_THEME = re.compile(r"^Theme\.fonts\.\w+\s*$")

# Eine im Bauteil **erzeugte** Farbe. Theme.qml begründet, warum selbst der Roboter seine
# beiden Flächen als Token bekommt: „eine Zeichnung, die sich ihre Töne selbst mischt, ist
# genau die Ausnahme, die diese Zeile verhindern soll." `Qt.color` mischt zwar nichts,
# erzeugt die Farbe aber ebenso im Bauteil — aus einem Namen, den niemand sucht.
COLOR_FUNCTION = re.compile(r"\bQt\.(?:color|rgba|hsla|hsva|lighter|darker|tint)\s*\(")

# Die **Wertseite** einer Farbeigenschaft, vom Doppelpunkt bis zum Zeilenende. Geprüft wird
# der ganze Ausdruck, nicht nur eine unmittelbar folgende Zeichenkette: `color: bedingung ?
# "white" : Theme.ink` ist reguläres QML, im Bestand zehnmal vorhanden und ging am alten
# Muster vorbei (Befund B2).
COLOR_PROPERTY = re.compile(r"\b(?:property\s+color\s+\w+|\w*[Cc]olor)\s*:\s*(.+)")

# Eine Zeichenkette in beiden QML-Schreibweisen. Einfache Anführungszeichen sind dieselbe
# Sprache und waren am alten Muster unsichtbar (Befund B2).
STRING_LITERAL = re.compile(r"\"([^\"]*)\"|'([^']*)'")

# Eine Zeichenkette, die an einem Vergleich steht, ist ein **Zustandsname** und keine
# Farbe: `tone === "warn" ? Theme.warn : Theme.inkSoft` (MessageBox.qml) nennt keine Farbe,
# obwohl der Ausdruck an einer Farbeigenschaft hängt. Beide Stellungen kommen vor.
COMPARED_STRING = re.compile(r"[=!]=+\s*(\"[^\"]*\"|'[^']*')|(\"[^\"]*\"|'[^']*')\s*[=!]=+")

# Geschlossene Ausnahmeliste. „transparent" ist keine Farbe der Richtung, sondern die
# Abwesenheit einer Fläche — es gibt dafür bewusst kein Token, und die Liste bleibt
# geschlossen: Eine Ausnahmeliste, die wächst, ist eine Ausrede.
ALLOWED_COLOR_WORDS = frozenset({"transparent"})


def colour_words(value: str) -> list[str]:
    """Die Farbnamen in der Wertseite einer Farbeigenschaft, beide Anführungszeichenarten.

    Zeichenketten an einem Vergleichsoperator fallen vorher weg — sie stehen in der
    **Bedingung** eines bedingten Ausdrucks und benennen keine Farbe."""
    ohne_bedingung = COMPARED_STRING.sub(" ", value)
    return [
        doppelt if doppelt else einfach
        for doppelt, einfach in STRING_LITERAL.findall(ohne_bedingung)
    ]


def qml_without_comments(path: Path) -> list[tuple[int, str]]:
    """Die Zeilen einer QML-Datei ohne `//`- und `/* */`-Kommentare, mit Zeilennummer.

    Geprüft wird der Code, nicht die Prosa: Ein Kommentar, der eine alte Farbe im Wortlaut
    nennt (`war #0B0E12`), dokumentiert eine Entscheidung und setzt keine."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    lines = []
    for number, line in enumerate(text.split("\n"), start=1):
        lines.append((number, re.sub(r"//.*$", "", line)))
    return lines


def test_no_colour_outside_the_theme_file() -> None:
    """technik.md §14: keine Hex-Farbe außerhalb `Theme.qml` — und keine im Bauteil
    gemischte Tönung, kein Farbname."""
    files = sorted(p for p in REPO.rglob("*.qml") if p != THEME and ".venv" not in p.parts)
    assert files, "Keine QML-Datei außerhalb von Theme.qml gefunden — dieser Test prüfte nichts."
    assert THEME.is_file(), f"{THEME} fehlt — die Quelle, gegen die hier geprüft wird."

    seen = 0
    offenders: list[str] = []
    for path in files:
        where = path.relative_to(REPO).as_posix()
        for number, line in qml_without_comments(path):
            for found in HEX_COLOR.findall(line):
                offenders.append(f"{where}:{number}: Hexfarbe {found}")
            if COLOR_FUNCTION.search(line):
                offenders.append(f"{where}:{number}: Farbe im Bauteil erzeugt: {line.strip()}")
            match = COLOR_PROPERTY.search(line)
            if not match:
                continue
            seen += 1
            for found in colour_words(match.group(1)):
                if found not in ALLOWED_COLOR_WORDS:
                    offenders.append(f"{where}:{number}: Farbname {found!r}")
    assert not offenders, "Farbe außerhalb von gui/qml/Theme.qml: " + "; ".join(offenders)
    assert seen, "Keine einzige Farbeigenschaft gefunden — dieser Test prüfte nichts."


def test_no_font_family_outside_the_theme_file() -> None:
    """technik.md §14: kein `font.family` außerhalb `Theme.qml` — gemeint ist der Wert.
    Eine Schriftfamilie wird nie benannt, sie kommt aus `Theme.fonts`."""
    files = sorted(p for p in REPO.rglob("*.qml") if p != THEME and ".venv" not in p.parts)
    assert files, "Keine QML-Datei außerhalb von Theme.qml gefunden — dieser Test prüfte nichts."

    seen = 0
    offenders: list[str] = []
    for path in files:
        where = path.relative_to(REPO).as_posix()
        for number, line in qml_without_comments(path):
            match = FONT_FAMILY.search(line)
            if not match:
                continue
            seen += 1
            # In der gruppierten Schreibweise steht hinter dem Wert noch der Rest der
            # Gruppe (`family: Theme.fonts.ui; pixelSize: 14 }`).
            value = match.group(1).split(";")[0].strip().rstrip("}").strip()
            if not FONT_FROM_THEME.match(value):
                offenders.append(f"{where}:{number}: font.family: {value}")
    assert not offenders, "Schriftfamilie nicht aus Theme.fonts: " + "; ".join(offenders)
    assert seen, "Kein einziges `font.family` gefunden — dieser Test prüfte nichts."
