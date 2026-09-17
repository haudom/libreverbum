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
Dasselbe für Farbe: kein Hexwert, kein Farbname, keine im Bauteil gemischte Tönung.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "gui" / "qml" / "Theme.qml"

# Hexfarbe im QML-Sinn: #RGB, #RGBA, #RRGGBB, #AARRGGBB.
HEX_COLOR = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")

# Eine Schriftfamilie darf nur aus den Token kommen.
FONT_FAMILY = re.compile(r"font\.family\s*:\s*(.+)")
FONT_FROM_THEME = re.compile(r"^Theme\.fonts\.\w+\s*$")

# Farbmischung im Bauteil. Theme.qml begründet, warum selbst der Roboter seine beiden
# Flächen als Token bekommt: „eine Zeichnung, die sich ihre Töne selbst mischt, ist genau
# die Ausnahme, die diese Zeile verhindern soll."
COLOR_MIXING = re.compile(r"\bQt\.(?:rgba|hsla|hsva|lighter|darker|tint)\s*\(")

# Zeichenkette an einer Farbeigenschaft. „transparent" ist keine Farbe der Richtung,
# sondern die Abwesenheit einer Fläche, und bleibt deshalb erlaubt.
COLOR_LITERAL = re.compile(r"\b(?:property\s+color\s+\w+|\w*[Cc]olor)\s*:\s*\"([^\"]*)\"")
ALLOWED_COLOR_WORDS = frozenset({"transparent"})


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

    offenders: list[str] = []
    for path in files:
        where = path.relative_to(REPO).as_posix()
        for number, line in qml_without_comments(path):
            for found in HEX_COLOR.findall(line):
                offenders.append(f"{where}:{number}: Hexfarbe {found}")
            for found in COLOR_MIXING.findall(line):
                offenders.append(f"{where}:{number}: gemischte Farbe {found}")
            for found in COLOR_LITERAL.findall(line):
                if found not in ALLOWED_COLOR_WORDS:
                    offenders.append(f"{where}:{number}: Farbname {found!r}")
    assert not offenders, "Farbe außerhalb von gui/qml/Theme.qml: " + "; ".join(offenders)


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
            value = match.group(1).strip().rstrip(";").strip()
            if not FONT_FROM_THEME.match(value):
                offenders.append(f"{where}:{number}: font.family: {value}")
    assert not offenders, "Schriftfamilie nicht aus Theme.fonts: " + "; ".join(offenders)
    assert seen, "Kein einziges `font.family` gefunden — dieser Test prüfte nichts."
