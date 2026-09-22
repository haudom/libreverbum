"""Rendert die ganze Matrix und prüft jedes Bild dreifach — der eine Befehl des Mockups.

    .venv/Scripts/python.exe tools/design_mockup/render_all.py

**Wozu dieses Verzeichnis da ist.** Es zeigt die Gestaltungsrichtung „Lesetisch" an vier
gebauten Bildschirmen (Einrichtung, Buch und Kapitel, Fortschritt, Triage-Eintrag) und
fünfzehn Bauteilen — nicht als Beschreibung, sondern lauffähig. Das Warum steht in
technik.md §14, E11; was auf welchem Bildschirm steht und
wann er als verifiziert gilt, in konzept.md, „Die sieben Bildschirme der Oberfläche".

**Gerendert wird gegen den Bestand, nicht gegen eine Kopie:** `qml/Mock/qmldir` zeigt auf
`gui/qml/Theme.qml`, die Schriften kommen aus `gui/fonts/`. Wer dort ein Token ändert,
bekommt hier beim nächsten Lauf ein anderes Bild und im Zweifel Rot — eine Kopie hätte
still danebengelegen (technik.md §14, „Der Mockup rendert gegen den Bestand").

**Lebensdauer.** Die Bauteile unter `qml/` sind die Saat für AP 15 bis AP 19 und ziehen
dort nach `gui/qml/` um; `Mock/Content.qml` (Vorführdaten) und die Prüfskripte bleiben
hier, bis `tools/gui_screenshot.py` aus AP 15 ihre Arbeit übernimmt. Das Verzeichnis ist
damit vorübergehend — `gui/qml/Theme.qml` ist es nicht.

Vier Bildschirme, je hell und dunkel, je 1280×800 und 900×600 — und jeder im
**ungünstigsten** Datenfall, nicht im schmeichelhaften (review_round1.md B24: „Ein Mockup,
das nur den günstigen Fall zeigt, prüft nichts"). Dazu die Nebenfälle, die je eine
Prüfzeile beantworten, die im Hauptfall nicht im Bild stehen kann.

Drei Prüfungen je Bild, weil keine davon die anderen ersetzt:

1. `shot.py` — rendert und zählt jede QML-Warnung als Fehlschlag.
2. `layout_check.py` — sucht Überlauf und gekürzten Text im Objektbaum. „0 Warnungen"
   beweist nichts: Qt meldet keinen Layoutüberlauf (B1/B2).
3. `contrast_check.py` — misst den Kontrast im PNG an jeder echten Textstelle. Aus den Token
   gerechnet käme falsches Grün heraus (B3).

Jedes der drei meldet außerdem, wenn es **nichts** angesehen hat: ein einfarbiges Bild,
kein `Text` im Objektbaum, keine gemessene Textstelle. Ohne diese Untergrenze bestand ein
Bildschirm, der gar nichts rendert, alle drei Prüfungen (Befund B4, Durchsicht b2d5cab).
Gezählt wird hier der **Rückgabewert** jedes der drei Läufe, nie eine erkannte Befundzeile
— siehe `melde` (Befund B1).

Aufruf:  python render_all.py [--nur triage]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PNG = HERE / "png"
PYTHON = sys.executable

# (Bildschirm, QML, Fall, Ordnername des Falls im Dateinamen, nur diese Größen)
HAUPT = [
    # Fortschritt: Anfangszustand — eine Etappe läuft, fünf sind offen. Genau der Fall,
    # der in Runde 1 nie gerendert wurde und mit 2,41:1 durchfiel.
    ("fortschritt", "Progress.qml", "anfang"),
    # Triage: der längste Belegsatz des Kapitels (473 Zeichen).
    ("triage", "Triage.qml", "lang"),
    # Einrichtung: der Fehlschlag steht im Wortlaut im Fenster.
    ("einrichtung", "Setup.qml", "fehler"),
    # Buch und Kapitel: 22 Kapitel, Bildlauf, Hinweis, nichts gewählt.
    ("kapitel", "Chapters.qml", "lang"),
]

NEBEN = [
    ("fortschritt", "Progress.qml", "lauf", ["1280x800"]),
    ("fortschritt", "Progress.qml", "fehler", ["1280x800"]),
    ("triage", "Triage.qml", "kette", ["1280x800", "900x600"]),
    ("einrichtung", "Setup.qml", "laeuft", ["1280x800"]),
    ("kapitel", "Chapters.qml", "kurz", ["1280x800", "900x600"]),
]

GROESSEN = ["1280x800", "900x600"]
THEMEN = [("hell", []), ("dunkel", ["--dark"])]


def lauf(skript: str, qml: Path, extra: list[str]) -> tuple[int, str]:
    ergebnis = subprocess.run(
        [PYTHON, str(HERE / skript), str(qml), *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return ergebnis.returncode, (ergebnis.stdout or "") + (ergebnis.stderr or "")


def melde(titel: str, code: int, ausgabe: str, zeilen: list[str]) -> int:
    """Zählt einen Fehlschlag und zeigt ihn; gibt 1 zurück, wenn `code` nicht 0 war.

    Gezählt wird der **Rückgabewert**, nie eine erkannte Befundzeile. Bis zur Nachbesserung
    von AP 14 las die Schleife den Rückgabewert von `contrast_check.py` nur für die Marke
    und zählte stattdessen dessen `!`-Zeilen: Ein Abbruch ohne solche Zeile — Absturz,
    fehlende Schrift, QML nicht geladen, falsches Argument — ergab sechsmal „FEHL" und
    trotzdem „0 Befunde" bei Exit 0 (Befund B1, Durchsicht b2d5cab). `zeilen` ist deshalb
    nur die schönere Auswahl; ist sie leer, steht die rohe Ausgabe da."""
    if not code:
        return 0
    print(f"     {titel}:")
    for zeile in (zeilen or ausgabe.splitlines())[:8]:
        print("       " + zeile.strip()[:160])
    return 1


def main() -> int:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--nur", default="")
    args = parser.parse_args()

    auftraege = []
    for name, datei, fall in HAUPT:
        for groesse in GROESSEN:
            for thema, flagge in THEMEN:
                auftraege.append((name, datei, fall, groesse, thema, flagge))
    for name, datei, fall, groessen in NEBEN:
        for groesse in groessen:
            for thema, flagge in THEMEN:
                auftraege.append((name, datei, fall, groesse, thema, flagge))
    if args.nur:
        auftraege = [a for a in auftraege if a[0] == args.nur]

    fehler = 0
    for name, datei, fall, groesse, thema, flagge in auftraege:
        qml = HERE / "qml" / datei
        breite = groesse.split("x")[0]
        ziel = PNG / f"{name}_{fall}_{breite}_{thema}.png"
        gemeinsam = ["--size", groesse, "--fall", fall, *flagge]

        code_s, aus_s = lauf("shot.py", qml, [str(ziel), *gemeinsam])
        code_l, aus_l = lauf("layout_check.py", qml, gemeinsam)
        code_m, aus_m = lauf("contrast_check.py", qml, gemeinsam)

        schlecht = [z for z in aus_m.splitlines() if z.startswith(" !")]
        kopf = aus_m.splitlines()[0] if aus_m else ""
        worst = next((z for z in aus_m.splitlines() if "schlechtestes Paar" in z), "")
        marke = "OK  " if (code_s == 0 and code_l == 0 and code_m == 0) else "FEHL"
        print(f"{marke} {ziel.name:38s} {worst.strip()}", flush=True)

        warnungen = [z for z in aus_s.splitlines() if "Warnung" in z or "QML" in z]
        fehler += melde("QML-Warnung", code_s, aus_s, warnungen)
        fehler += melde("Layout", code_l, aus_l, aus_l.splitlines())
        fehler += melde(f"Kontrast ({kopf})", code_m, aus_m, schlecht)

    print(f"\n{len(auftraege)} Bilder, {fehler} Befunde")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
