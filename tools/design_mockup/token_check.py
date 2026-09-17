"""Vorprobe der Farbtoken — rechnet, was das gerenderte Bild später nachweisen muss.

Kein Ersatz für `contrast_check.py`: Gerechnet wird hier mit den reinen Tokenwerten,
gemessen wird dort im PNG an den echten Textstellen. Diese Datei dient nur dazu, eine
Farbe nicht erst nach dem Rendern zu verwerfen. Wer ihr allein glaubt, wiederholt
review_round1.md B3 — dort meldete ein rechnendes Werkzeug „0 Paare unter 4,5:1", während
im Bild 2,41:1 stand (technik.md §14, „Gemessen wird im Bild, nicht aus den Token").

**Die Werte stehen nicht hier, sie werden aus `gui/qml/Theme.qml` gelesen.** Die alte
Fassung trug eine Kopie der beiden Tabellen im Quelltext, und genau das ging schief: Als
vier dunkle Token ins Warme gezogen wurden (review_round3.md C5), blieb die Kopie stehen
und rechnete weiter mit `#0B0E12` statt `#0E0C08`. Ein zweites Verzeichnis derselben
Wahrheit widerspricht der Zusicherung, `Theme.qml` sei die **einzige** Quelle — und es
widerspricht ihr still.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME = HERE.parent.parent / "gui" / "qml" / "Theme.qml"

# Ein Farbtoken der Form:  readonly property color ground: dark ? "#0E0C08" : "#E3DFD6"
TOKEN = re.compile(
    r'readonly\s+property\s+color\s+(\w+)\s*:\s*dark\s*\?\s*"(#[0-9A-Fa-f]{6})"'
    r'\s*:\s*"(#[0-9A-Fa-f]{6})"'
)

# Was diese Probe braucht. Fehlt eines, bricht sie ab, statt eine Zeile wegzulassen
# (Regel 13): Eine Tabelle mit einer stillen Lücke sieht aus wie eine vollständige.
BENOETIGT = [
    "ground",
    "surface",
    "marked",
    "hairline",
    "ink",
    "inkSoft",
    "inkFaint",
    "accent",
    "accentFill",
    "inkOnAccent",
    "chosen",
    "warn",
    "warnFill",
]

TEXT_ROLES = ["ink", "inkSoft", "inkFaint", "accent", "chosen"]


def lum(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    parts = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(a: str, b: str) -> float:
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def read_themes(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Die beiden Farbtabellen aus `Theme.qml`, hell und dunkel."""
    text = path.read_text(encoding="utf-8")
    dunkel = {name: d for name, d, _ in TOKEN.findall(text)}
    hell = {name: h for name, _, h in TOKEN.findall(text)}
    fehlend = [name for name in BENOETIGT if name not in hell]
    if fehlend:
        raise SystemExit(
            f"In {path} nicht gefunden: {', '.join(fehlend)} — entweder ist ein Token "
            f"umbenannt worden oder seine Schreibweise passt nicht mehr zu diesem Muster. "
            f"Diese Probe rechnet dann nicht weniger, sie rechnet falsch."
        )
    return hell, dunkel


def report(name: str, t: dict[str, str]) -> int:
    print(f"\n=== {name} ===")
    befunde = 0
    flaeche = ratio(t["surface"], t["ground"])
    print(f"  Fläche L1 gegen L0   {flaeche:5.2f}:1   (Soll ≥ 1,25)")
    if flaeche < 1.25:
        befunde += 1
    print(f"  Markierte Zeile L2   {ratio(t['marked'], t['surface']):5.2f}:1   (gegen L1)")
    print(f"  Haarlinie auf L1     {ratio(t['hairline'], t['surface']):5.2f}:1")
    for role in TEXT_ROLES:
        on_surface = ratio(t[role], t["surface"])
        on_ground = ratio(t[role], t["ground"])
        on_marked = ratio(t[role], t["marked"])
        worst = min(on_surface, on_ground, on_marked)
        flag = "  <-- UNTER 4,5" if worst < 4.5 else ""
        if worst < 4.5:
            befunde += 1
        print(
            f"  {role:11} L1 {on_surface:5.2f}  L0 {on_ground:5.2f}  L2 {on_marked:5.2f}"
            f"   schlechtester {worst:5.2f}{flag}"
        )
    print(f"  warn auf warnFill    {ratio(t['warn'], t['warnFill']):5.2f}:1")
    print(f"  inkOnAccent auf Füll {ratio(t['inkOnAccent'], t['accentFill']):5.2f}:1")
    print(
        f"  accentFill auf L1    {ratio(t['accentFill'], t['surface']):5.2f}:1"
        f"   (Bedienelement ≥ 3)"
    )
    print(f"  accent auf L1        {ratio(t['accent'], t['surface']):5.2f}:1   (Fokusring ≥ 3)")
    return befunde


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    hell, dunkel = read_themes(THEME)
    print(f"Token aus {THEME}: {len(hell)} Farben je Thema")
    befunde = report("hell", hell) + report("dunkel", dunkel)
    print(
        f"\n{befunde} Befunde in der Rechnung — gemessen wird trotzdem im Bild (contrast_check.py)."
    )
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
