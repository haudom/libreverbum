#!/usr/bin/env python3
"""Blattfüllungstest: Wie viele Einträge passen bei welcher Übersetzungslänge tatsächlich
auf ein physisches Blatt?

Hintergrund
-----------
`printout.MAX_ENTRIES = 36` (../libreverbum/printout.py) stammt aus einer **Rechnung**:
Arial-Schriftmetrik, Zeilenhöhe, 36 × 13,3 mm = 478,8 mm von 491 mm nutzbarer
Spaltenhöhe — 97,5 % Füllung (../technik.md §8c, „Gemessene Ergebnisse: »passt auf ein
Blatt« ist gedeckt"). Gedruckt wurde dabei nie. Eine Durchsicht hat mit Edge headless
gedruckt und die Rechnung am eigenen Designpunkt widerlegt: 36 Einträge mit rund 75
Zeichen Übersetzungstext (dem p99-Wert, auf den §8c auslegt) ergaben **zwei** physische
Seiten. `../technik.md §8c`, „Offene Punkte" nennt genau dieses Werkzeug als fehlend.

Dieses Skript rechnet nicht, es druckt. Es erzeugt die Druckseite über den echten Kern
(`libreverbum.printout.write_printout`, nicht einen Nachbau — ../dokumentation.md §5:
„die Vorrichtung zeigt Laufen, die Fremdquelle Stimmen"), lässt sie von einem echten
Browser als PDF ausdrucken und zählt die tatsächlich entstandenen Seiten.

Verfahren
---------
1. Übersetzungstexte kommen aus `tools/en-de.sqlite3` (neben diesem Skript erwartet, wie
   bei den übrigen Werkzeugen hier): Zu einer Ziellänge wird je die reale `trans_list`
   ausgewählt, deren Länge ihr am nächsten liegt — keine erfundenen Füllzeichen. Wie
   `Sense.translation` tatsächlich gefüllt wird (die ganze `trans_list`-Zeile, nicht eine
   einzelne Bedeutung — `translation.choose_sense`, `translation=chosen.wikdict_trans_list`),
   bildet `_build_entries` unten nach
2. Je Kombination aus Eintragszahl und Ziellänge baut `_build_entries` eine Liste aus
   `(Occurrence, Sense)`, `write_printout` schreibt daraus die echte HTML-Druckseite
3. Ein gefundener Browser (Edge oder Chrome, siehe `BROWSER_CANDIDATES`) druckt sie
   headless zu PDF: `<browser> --headless --disable-gpu --print-to-pdf=<datei>
   --no-pdf-header-footer <html>`
4. Die PDF-Seiten werden **zweifach** gezählt, ohne einen PDF-Leser (der liegt nicht in
   `.venv/` und soll auch nicht hinzukommen): die einzelnen Seitenobjekte (`/Type
   /Page`) und, gegengeprüft, der `/Count` im Seitenbaum (`/Type /Pages`) — weichen beide
   voneinander ab, bricht das Skript ab statt eine falsche Zahl zu melden
   (../dokumentation.md §4, Regel 13)

Aufruf
------
    PYTHONPATH=. python tools/print_fit_check.py
    PYTHONPATH=. python tools/print_fit_check.py --entries 33 --entries 36 --length 65
    PYTHONPATH=. python tools/print_fit_check.py --p99-length 76
    PYTHONPATH=. python tools/print_fit_check.py --browser "C:\\Pfad\\zu\\msedge.exe"

Ohne `--entries`/`--length` läuft eine Voreinstellung, die die in ../technik.md §8c
gemessene Längenverteilung abdeckt (Median 12, p90 32, p95 45, p99 76) sowie die im
Auftrag genannte Schwelle (60 hält noch, um 65 kippt es). `--p99-length` wird immer
mitgetestet und trägt die Schlusszeile: die größte getestete Eintragszahl, die bei dieser
Länge noch sicher auf ein Blatt passt.

Verfahren und seine Grenzen
---------------------------
Dieses Skript importiert den Kern (`libreverbum.printout`, `libreverbum.entities`) und
braucht deshalb `PYTHONPATH=.`, aufgerufen aus dem Wurzelverzeichnis des Repositoriums —
wie `tools/ambiguity_check.py`. Es ändert `printout.MAX_ENTRIES` nicht und liest den Wert
nirgends: Gemessen wird die tatsächliche Blattkapazität, unabhängig davon, welche Zahl
`printout` heute dafür hält.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
# Der Kern ist nicht als Paket installiert (../technik.md §6) — deshalb das
# Repository-Wurzelverzeichnis von Hand auf den Suchpfad, vor den Kern-Importen.
sys.path.insert(0, os.path.dirname(HERE))

from libreverbum.entities import Book, Lemma, Occurrence, Sense  # noqa: E402
from libreverbum.printout import write_printout  # noqa: E402

DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

# Übliche Installationsorte, Edge zuerst — auf diesem Rechner vorhanden, Chrome nicht
# (Auftrag). Dasselbe Muster wie `sense_check.SERVER_CANDIDATES`: der Reihe nach
# abgesucht, der erste vorhandene Pfad gewinnt.
BROWSER_CANDIDATES = [
    (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "Edge"),
    (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "Edge"),
    (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "Chrome"),
    (r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "Chrome"),
]
if os.environ.get("LOCALAPPDATA"):
    # Chrome installiert sich ohne Admin-Rechte oft hierhin, nicht nach Program Files.
    BROWSER_CANDIDATES.append(
        (
            os.path.join(os.environ["LOCALAPPDATA"], r"Google\Chrome\Application\chrome.exe"),
            "Chrome (Benutzerinstallation)",
        )
    )
# Für einen Lauf außerhalb von Windows: übliche Programmnamen über PATH.
WHICH_CANDIDATES = [("msedge", "Edge"), ("google-chrome", "Chrome"), ("chromium", "Chromium")]

DEFAULT_ENTRY_COUNTS = [25, 30, 33, 35, 36, 37, 40]
# ../technik.md §8c: Median 12, p90 32, p95 45, p99 76 über alle 157.801 `trans_list`-
# Werte. 60 und 65 aus dem Auftrag: „bei 60 hält es noch", „die Schwelle liegt bei rund
# 65 Zeichen".
DEFAULT_LENGTHS = [12, 32, 45, 60, 65, 76]
DEFAULT_P99_LENGTH = 76
DEFAULT_TIMEOUT = 30.0


def find_browser(preset: str | None) -> tuple[str, str] | None:
    """Sucht Edge oder Chrome an den üblichen Orten, Edge zuerst; gibt (Pfad,
    Beschreibung) zurück oder `None`, wenn keiner gefunden wurde. `preset` (`--browser`)
    wird ungeprüft vorgezogen, wenn die Datei existiert."""
    if preset:
        return (preset, "vorgegeben") if os.path.isfile(preset) else None
    for path, name in BROWSER_CANDIDATES:
        if os.path.isfile(path):
            return path, name
    for command, name in WHICH_CANDIDATES:
        found = shutil.which(command)
        if found:
            return found, name
    return None


def load_translation_pairs(dictionary_path: str) -> list[tuple[str, str]]:
    """Liest alle (`written_rep`, `trans_list`)-Paare aus dem Wörterbuch — die Grundlage,
    aus der `_pick_translations` unten nach Länge auswählt. Echte Wörterbuchdaten, keine
    erfundenen Füllzeichen (Auftrag)."""
    con = sqlite3.connect(dictionary_path)
    try:
        rows = con.execute(
            "SELECT written_rep, trans_list FROM translation "
            "WHERE written_rep IS NOT NULL AND trans_list IS NOT NULL"
        ).fetchall()
    finally:
        con.close()
    return rows


def _pick_translations(
    pairs: list[tuple[str, str]], target_length: int, count: int
) -> list[tuple[str, str]]:
    """Wählt `count` Paare, deren `trans_list`-Länge `target_length` am nächsten liegt,
    je `written_rep` höchstens einmal (sonst erschiene dasselbe Stichwort mehrfach auf
    der Seite, ohne dass das etwas über die Blattkapazität aussagte). Bricht sichtbar ab,
    wenn das Wörterbuch nicht genug verschiedene Stichwörter dieser Länge trägt
    (../dokumentation.md §4, Regel 13) statt mit weniger als verlangt weiterzurechnen."""
    ordered = sorted(pairs, key=lambda pair: abs(len(pair[1]) - target_length))
    selected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for written_rep, trans_list in ordered:
        key = written_rep.casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append((written_rep, trans_list))
        if len(selected) == count:
            return selected
    raise ValueError(
        f"Nur {len(selected)} verschiedene Stichwörter im Wörterbuch, {count} für die "
        f"Ziellänge {target_length} verlangt."
    )


_MEASURE_BOOK = Book(title="Blattfüllungstest", author="tools/print_fit_check.py")


def _build_entries(pairs: list[tuple[str, str]]) -> list[tuple[Occurrence, Sense]]:
    """Baut aus (`written_rep`, `trans_list`)-Paaren dieselbe Eingabeform, die
    `write_printout` von einem echten Kapitel bekäme: je Paar ein `Occurrence` und ein
    `Sense` mit `translation` gleich der echten `trans_list` (`translation.choose_sense`
    setzt genau dieses Feld unverändert, siehe Modulkopf). `pos=""` wie bei Wendungen
    ohne Einzelwortart (`extraction._NO_SINGLE_POS`) — dieses Skript kennt die echte
    Wortart der Stichwörter nicht und würde mit einer geschätzten sonst ein falsches
    Wortart-Kürzel auf die Seite drucken."""
    entries = []
    for written_rep, trans_list in pairs:
        lemma = Lemma(text=written_rep.casefold(), pos="")
        occurrence = Occurrence(
            book=_MEASURE_BOOK,
            chapter_number=1,
            lemma=lemma,
            word_form=written_rep,
            example_sentence="",
            frequency=1,
            proper_noun_frequency=0,
        )
        sense = Sense(lemma=lemma, translation=trans_list)
        entries.append((occurrence, sense))
    return entries


def render_pdf(browser: str, html_path: Path, pdf_path: Path, timeout: float) -> None:
    """Druckt `html_path` headless zu `pdf_path` — genau die im Auftrag genannten Schalter.
    Ein eigenes `--user-data-dir` verhindert, dass ein zweiter, parallel offener Browser
    mit demselben Profil den headless-Aufruf blockiert; an den Druckschaltern ändert das
    nichts."""
    with tempfile.TemporaryDirectory(prefix="print_fit_check_profile_") as profile_dir:
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            f"--user-data-dir={profile_dir}",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            html_path.resolve().as_uri(),
        ]
        result = subprocess.run(command, capture_output=True, timeout=timeout)
    if result.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f"Browser-Aufruf zum Drucken ist gescheitert (Rückgabewert {result.returncode}): "
            f"{result.stderr.decode('utf-8', 'replace')[:500]}"
        )


# `/Type /Page` (Seitenobjekt), nicht `/Type /Pages` (Knoten im Seitenbaum) —
# das negative Lookahead grenzt beides voneinander ab.
_PAGE_OBJECT = re.compile(rb"/Type\s*/Page(?!s)\b")
_PAGES_NODE = re.compile(rb"/Type\s*/Pages\b")
_COUNT_FIELD = re.compile(rb"/Count\s+(\d+)")
# Suchfenster um einen /Pages-Fund, in dem /Count zum selben Objekt gehört — Chromiums
# PDF-Ausgabe schreibt beide Schlüssel im selben, kurzen Objektwörterbuch, Reihenfolge
# nicht garantiert.
_COUNT_WINDOW = 500


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """Zählt die Seiten eines PDF ohne PDF-Leser: die Seitenobjekte selbst, gegengeprüft
    gegen `/Count` im Seitenbaum. Weichen beide voneinander ab oder trägt das PDF gar
    keinen lesbaren `/Count` (etwa weil die Objekte in einem komprimierten Objektstrom
    stecken, `/Type /ObjStm` — Chromiums unkomprimierte Standardausgabe tut das nicht),
    bricht die Funktion ab statt eine falsche Zahl zu melden (Auftrag: „die
    Gegenprüfung gehört dazu, sonst misst eine falsche Zählweise unbemerkt falsch")."""
    object_count = len(_PAGE_OBJECT.findall(pdf_bytes))

    tree_counts: set[int] = set()
    for match in _PAGES_NODE.finditer(pdf_bytes):
        start = max(0, match.start() - _COUNT_WINDOW)
        end = match.end() + _COUNT_WINDOW
        found = _COUNT_FIELD.search(pdf_bytes[start:end])
        if found:
            tree_counts.add(int(found.group(1)))

    if not tree_counts:
        raise ValueError(
            "Kein /Count im Seitenbaum des PDF gefunden — die Gegenprüfung der "
            "Seitenzählung ist damit nicht möglich."
        )
    # Bei verschachtelten Seitenbaumknoten trägt die Wurzel die Gesamtzahl, ein
    # Zwischenknoten nur die eines Teilbaums — der größte gefundene Wert ist die
    # Gesamtzahl. Chromiums Ausgabe verschachtelt heute nicht; die Fallunterscheidung
    # schadet trotzdem nicht.
    tree_count = max(tree_counts)
    if tree_count != object_count:
        raise ValueError(
            f"Seitenzählung widersprüchlich: {object_count} Seitenobjekte (/Type /Page), "
            f"aber /Count nennt {tree_count} — eine der beiden Zählweisen ist hier falsch."
        )
    return object_count


def measure(
    entry_count: int,
    target_length: int,
    pairs: list[tuple[str, str]],
    browser: str,
    tmp_dir: Path,
    timeout: float,
) -> dict[str, float | int]:
    """Eine einzelne Messung: `entry_count` Einträge mit Übersetzungen nahe
    `target_length` Zeichen, echt gedruckt, echte Seitenzahl."""
    selected = _pick_translations(pairs, target_length, entry_count)
    html_path = tmp_dir / f"seite_{entry_count}_{target_length}.html"
    pdf_path = tmp_dir / f"seite_{entry_count}_{target_length}.pdf"
    write_printout(html_path, _build_entries(selected))
    render_pdf(browser, html_path, pdf_path, timeout)
    pages = count_pdf_pages(pdf_path.read_bytes())
    achieved_lengths = [len(trans_list) for _, trans_list in selected]
    return {
        "entries": entry_count,
        "ziel_laenge": target_length,
        "erreichte_laenge": round(statistics.median(achieved_lengths)),
        "seiten": pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Misst, wie viele Einträge bei welcher Übersetzungslänge tatsächlich auf ein "
            "physisches Blatt passen — gedruckt mit einem echten Browser, nicht gerechnet "
            "(../technik.md §8c, „Offene Punkte“)."
        ),
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--entries",
        type=int,
        action="append",
        help=f"Eintragszahl (mehrfach angebbar). Vorgabe: {DEFAULT_ENTRY_COUNTS}",
    )
    parser.add_argument(
        "--length",
        type=int,
        action="append",
        dest="lengths",
        help=(
            f"Ziellänge der Übersetzung in Zeichen (mehrfach angebbar). Vorgabe: {DEFAULT_LENGTHS}"
        ),
    )
    parser.add_argument(
        "--p99-length",
        type=int,
        default=DEFAULT_P99_LENGTH,
        help=(
            "p99-Länge für die Schlusszeile, wird immer mitgetestet "
            f"(Vorgabe: {DEFAULT_P99_LENGTH})"
        ),
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Pfad zur WikDict-Datenbank")
    parser.add_argument(
        "--browser", help="Pfad zum Browser (sonst automatische Suche, Edge zuerst)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Sekunden je Druckvorgang (Vorgabe: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.db):
        print(f"Wörterbuch nicht gefunden: {args.db}", file=sys.stderr)
        print(
            "Herunterladen mit: python tools/coverage_check.py --fetch-dictionary", file=sys.stderr
        )
        return 1

    browser = find_browser(args.browser)
    if browser is None:
        if args.browser:
            print(f"Angegebener Browser nicht gefunden: {args.browser}", file=sys.stderr)
        else:
            print("Kein Browser gefunden — gesucht wurde:", file=sys.stderr)
            for path, name in BROWSER_CANDIDATES:
                print(f"  {path} ({name})", file=sys.stderr)
            print(
                "  sowie über PATH: " + ", ".join(c for c, _ in WHICH_CANDIDATES), file=sys.stderr
            )
            print("Mit --browser <Pfad> angeben.", file=sys.stderr)
        return 1
    browser_path, browser_name = browser
    print(f"Browser: {browser_path} ({browser_name})")

    entry_counts = sorted(set(args.entries or DEFAULT_ENTRY_COUNTS))
    lengths = sorted(set((args.lengths or list(DEFAULT_LENGTHS)) + [args.p99_length]))
    print(f"Wörterbuch: {args.db}")
    print(f"Eintragszahlen: {entry_counts}")
    print(f"Ziellängen (Übersetzungszeichen): {lengths}")

    pairs = load_translation_pairs(args.db)

    results = []
    with tempfile.TemporaryDirectory(prefix="print_fit_check_") as tmp:
        tmp_dir = Path(tmp)
        for length in lengths:
            for count in entry_counts:
                results.append(measure(count, length, pairs, browser_path, tmp_dir, args.timeout))

    print()
    print(f"{'Einträge':>8}  {'Ziellänge':>9}  {'erreicht':>8}  {'Seiten':>6}")
    for result in results:
        print(
            f"{result['entries']:>8}  {result['ziel_laenge']:>9}  "
            f"{result['erreichte_laenge']:>8}  {result['seiten']:>6}"
        )

    fitting = [
        result["entries"]
        for result in results
        if result["ziel_laenge"] == args.p99_length and result["seiten"] == 1
    ]
    print()
    if fitting:
        print(
            f"Bei p99-Länge ({args.p99_length} Zeichen) passen bis {max(fitting)} Einträge "
            f"sicher auf ein Blatt (getestet: {entry_counts})."
        )
    else:
        print(
            f"Keine der getesteten Eintragszahlen {entry_counts} passt bei p99-Länge "
            f"({args.p99_length} Zeichen) auf ein Blatt."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
