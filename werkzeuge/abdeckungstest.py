#!/usr/bin/env python3
"""Abdeckungstest: Wie viel Wortschatz eines Buches deckt das WikDict-Wörterbuch ab?

Hintergrund
-----------
Die Wahl der Wörterbuchquelle (siehe ../technik.md, Abschnitt 2) stützt sich auf eine
gemessene Abdeckung, nicht auf eine Schätzung. Dieses Skript rechnet die Messung nach —
gegen einen neuen Datenstand, ein anderes Buch oder eine andere Quelle.

Verfahren und seine Grenzen
---------------------------
Das Skript arbeitet bewusst **ohne** spaCy, damit es ohne Projektumgebung läuft. Die
Rückführung auf die Grundform geschieht durch eine grobe Suffix-Heuristik. Sie trifft
unregelmäßige Formen nicht (``went``, ``geese``, ``paid``), weshalb die ausgewiesene
Restlücke eine **Obergrenze** ist — die echte Abdeckung liegt darüber.

Damit die Zahl trotzdem aussagekräftig bleibt, werden die Fehltreffer in vier Gruppen
zerlegt. Nur die letzte ist ein Problem der Datenquelle:

1. Eigennamen        -> entfernt später die Eigennamenerkennung
2. unregelmäßige Formen -> löst später die Lemmatisierung
3. Verkürzungen (``didn't`` -> ``didn``) -> löst später die Tokenisierung
4. verbleibende Lücken  -> echte Wörterbuchlücken

Sobald die Lemmatisierung im Kern steht, sollte ``grundformen()`` durch den echten
Lemmatisierer ersetzt werden; dann fällt Gruppe 2 weg und die Zahl wird scharf.

Aufruf
------
    python werkzeuge/abdeckungstest.py buch.txt [weitere.txt ...]
    python werkzeuge/abdeckungstest.py --db pfad/zu/en-de.sqlite3 buch.txt
    python werkzeuge/abdeckungstest.py --hole-woerterbuch      # nur herunterladen

Erwartet reinen Text (UTF-8). Bei Dateien von Project Gutenberg wird der
Lizenz-Vorspann automatisch abgeschnitten.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import sqlite3
import sys
import urllib.request

WOERTERBUCH_URL = "https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3"
STANDARD_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "en-de.sqlite3")

# Unregelmäßige Formen, die die Suffix-Heuristik nicht zurückführen kann.
# Keine vollständige Liste — sie muss nur die häufigsten Fälle abdecken, damit die
# Restlücke nicht künstlich aufgebläht wird.
UNREGELMAESSIG = set("""
be am is are was were been being have has had do does did done
go went gone come came become became get got gotten give gave given take took taken
make made say said see saw seen know knew known think thought find found
tell told bring brought buy bought catch caught teach taught seek sought
fight fought stand stood understand understood hold held run ran
begin began begun drink drank drunk sing sang sung ring rang rung
sink sank sunk spring sprang sprung shrink shrank shrunk swim swam swum
speak spoke spoken break broke broken choose chose chosen freeze froze frozen
steal stole stolen wake woke woken drive drove driven ride rode ridden
rise rose risen write wrote written strive strove striven
draw drew drawn grow grew grown blow blew blown throw threw thrown fly flew flown
fall fell fallen eat ate eaten forget forgot forgotten forgive forgave forgiven
shake shook shaken mistake mistook mistaken lie lay lain laid sit sat
set put cut hit let shut cost hurt burst cast spread
keep kept sleep slept sweep swept weep wept creep crept feel felt leave left
mean meant meet met read lead led feed fed flee fled speed sped
bleed bled breed bred send sent spend spent bend bent lend lent build built
sell sold win won shoot shot lose lost sting stung swing swung cling clung
fling flung hang hung dig dug stick stuck strike struck
wear wore worn tear tore torn bear bore borne swear swore sworn
can could will would shall should may might must ought
child children foot feet tooth teeth goose geese mouse mice man men woman women
person people ox oxen louse lice
""".split())

# Reste von Verkürzungen, die eine naive Tokenisierung übriglässt.
VERKUERZUNGEN = {
    "ll", "ve", "re", "t", "s", "d", "m", "n",
    "didn", "don", "isn", "wasn", "couldn", "wouldn", "shouldn", "doesn",
    "hadn", "hasn", "haven", "aren", "weren", "ain", "mustn", "needn", "shan",
}

# Buchstaben statt [A-Za-z], sonst zerfallen Ligaturen und Akzente in Bruchstücke:
# "encyclopædia" -> "encyclop" + "dia", "mediæval" -> "medi" + "val".
# [^\W\d_] ist "alles, was \w ist, aber weder Ziffer noch Unterstrich" — also Buchstabe.
WORT = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")

GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
GUTENBERG_ENDE = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)


def hole_woerterbuch(ziel: str) -> None:
    """Lädt die WikDict-Datenbank, falls sie noch nicht vorliegt (rund 20 MB)."""
    if os.path.exists(ziel):
        return
    print(f"Lade Wörterbuch nach {ziel} …", file=sys.stderr)
    os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
    urllib.request.urlretrieve(WOERTERBUCH_URL, ziel)
    groesse = os.path.getsize(ziel) / 1024 / 1024
    print(f"  fertig, {groesse:.1f} MB", file=sys.stderr)


def lade_stichwoerter(db_pfad: str) -> set[str]:
    with sqlite3.connect(db_pfad) as con:
        return {zeile[0].lower() for zeile in con.execute(
            "SELECT DISTINCT written_rep FROM translation")}


def grundformen(wort: str):
    """Grobe Kandidaten für die Grundform. Später durch echte Lemmatisierung ersetzen."""
    yield wort
    if wort.endswith("ies"):
        yield wort[:-3] + "y"
    if wort.endswith("es"):
        yield wort[:-2]
    if wort.endswith("s") and not wort.endswith("ss"):
        yield wort[:-1]
    if wort.endswith("ed"):
        yield wort[:-2]
        yield wort[:-1]
        if len(wort) > 4 and wort[-3] == wort[-4]:   # stopped -> stop
            yield wort[:-3]
    if wort.endswith("ing"):
        yield wort[:-3]
        yield wort[:-3] + "e"                        # shutting -> shut / making -> make
        if len(wort) > 5 and wort[-4] == wort[-5]:
            yield wort[:-4]
    for suffix in ("ly", "er", "est"):
        if wort.endswith(suffix):
            yield wort[:-len(suffix)]
    if "-" in wort:                                  # arm-chair -> armchair
        yield wort.replace("-", "")


def lies_text(pfad: str) -> str:
    text = open(pfad, encoding="utf-8-sig", errors="replace").read()
    if (start := GUTENBERG_START.search(text)):
        text = text[start.end():]
    if (ende := GUTENBERG_ENDE.search(text)):
        text = text[:ende.start()]
    return text


def pruefe(pfad: str, stichwoerter: set[str], anzahl_beispiele: int) -> None:
    text = lies_text(pfad)
    tokens = WORT.findall(text)
    if not tokens:
        print(f"{pfad}: kein Text gefunden", file=sys.stderr)
        return

    haeufigkeit = collections.Counter(t.lower() for t in tokens)
    grossgeschrieben = collections.Counter(t.lower() for t in tokens if t[0].isupper())

    treffer, fehltreffer = [], []
    for wort in haeufigkeit:
        ziel = treffer if any(k in stichwoerter for k in grundformen(wort)) else fehltreffer
        ziel.append(wort)

    gruppen: dict[str, list[str]] = {
        "Eigennamen": [], "unregelmäßige Formen": [],
        "Verkürzungen": [], "verbleibende Lücken": [],
    }
    for wort in fehltreffer:
        blank = wort.replace("-", "").replace("'", "")
        if wort in VERKUERZUNGEN:
            gruppen["Verkürzungen"].append(wort)
        elif wort in UNREGELMAESSIG or blank in UNREGELMAESSIG:
            gruppen["unregelmäßige Formen"].append(wort)
        elif grossgeschrieben[wort] / haeufigkeit[wort] > 0.85:
            gruppen["Eigennamen"].append(wort)
        else:
            gruppen["verbleibende Lücken"].append(wort)

    formen = len(haeufigkeit)
    tokens_gesamt = sum(haeufigkeit.values())
    tokens_treffer = sum(haeufigkeit[w] for w in treffer)
    luecken = gruppen["verbleibende Lücken"]
    tokens_luecke = sum(haeufigkeit[w] for w in luecken)

    print(f"\n=== {os.path.basename(pfad)} ===")
    print(f"  Wortformen (types)          {formen:>8,}")
    print(f"  Wörter gesamt (tokens)      {tokens_gesamt:>8,}")
    print(f"  Stichworttreffer            {len(treffer):>8,}  ({len(treffer)/formen:6.1%})")
    print(f"  Textabdeckung roh           {tokens_treffer/tokens_gesamt:>13.1%}")
    print("\n  Fehltreffer nach Ursache:")
    for name, liste in gruppen.items():
        print(f"    {name:<24} {len(liste):>6,}  ({len(liste)/formen:5.1%} der Wortformen)")

    print(f"\n  Restlücke nach Lemmatisierung + Eigennamenfilter: "
          f"{tokens_luecke/tokens_gesamt:.2%} der Wörter  (Obergrenze)")

    if luecken:
        haeufigste = sorted(luecken, key=lambda w: -haeufigkeit[w])[:anzahl_beispiele]
        print("  Häufigste verbleibende Lücken:")
        print("    " + ", ".join(f"{w} ({haeufigkeit[w]})" for w in haeufigste))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Misst die Wörterbuchabdeckung an echtem Buchtext.",
        epilog="Siehe technik.md, Abschnitt 2, für die Einordnung der Zahlen.")
    p.add_argument("dateien", nargs="*", help="Textdateien (UTF-8), z. B. aus Project Gutenberg")
    p.add_argument("--db", default=STANDARD_DB, help=f"Pfad zur WikDict-Datenbank (Vorgabe: {STANDARD_DB})")
    p.add_argument("--beispiele", type=int, default=30, help="Anzahl gezeigter Fehltreffer (Vorgabe: 30)")
    p.add_argument("--hole-woerterbuch", action="store_true", help="Datenbank herunterladen und beenden")
    args = p.parse_args()

    if args.hole_woerterbuch:
        hole_woerterbuch(args.db)
        return 0

    if not args.dateien:
        p.print_help()
        return 1

    hole_woerterbuch(args.db)
    stichwoerter = lade_stichwoerter(args.db)
    print(f"Wörterbuch: {args.db}\nStichwörter: {len(stichwoerter):,}")

    for pfad in args.dateien:
        if not os.path.exists(pfad):
            print(f"nicht gefunden: {pfad}", file=sys.stderr)
            continue
        pruefe(pfad, stichwoerter, args.beispiele)

    print("\nHinweis: Die Restlücke ist eine Obergrenze — die Suffix-Heuristik trifft")
    print("unregelmäßige Formen nicht. Siehe Modulbeschreibung im Skript.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
