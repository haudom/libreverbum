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

Sobald die Lemmatisierung im Kern steht, sollte ``lemma_candidates()`` durch den echten
Lemmatisierer ersetzt werden; dann fällt Gruppe 2 weg und die Zahl wird scharf.

Aufruf
------
    python tools/coverage_check.py buch.txt [weitere.txt ...]
    python tools/coverage_check.py --db pfad/zu/en-de.sqlite3 buch.txt
    python tools/coverage_check.py --fetch-dictionary      # nur herunterladen

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

DICTIONARY_URL = "https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3"
DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "en-de.sqlite3")

# Unregelmäßige Formen, die die Suffix-Heuristik nicht zurückführen kann.
# Keine vollständige Liste — sie muss nur die häufigsten Fälle abdecken, damit die
# Restlücke nicht künstlich aufgebläht wird.
IRREGULAR_FORMS = set(
    """
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
""".split()
)

# Reste von Verkürzungen, die eine naive Tokenisierung übriglässt.
CONTRACTIONS = set(
    """
ll ve re t s d m n
didn don isn wasn couldn wouldn shouldn doesn hadn hasn haven aren weren ain mustn
needn shan
""".split()
)

# Buchstaben statt [A-Za-z], sonst zerfallen Ligaturen und Akzente in Bruchstücke:
# "encyclopædia" -> "encyclop" + "dia", "mediæval" -> "medi" + "val".
# [^\W\d_] ist "alles, was \w ist, aber weder Ziffer noch Unterstrich" — also Buchstabe.
WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")

GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
GUTENBERG_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)


def fetch_dictionary(target: str) -> None:
    """Lädt die WikDict-Datenbank, falls sie noch nicht vorliegt (rund 20 MB)."""
    if os.path.exists(target):
        return
    print(f"Lade Wörterbuch nach {target} …", file=sys.stderr)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    urllib.request.urlretrieve(DICTIONARY_URL, target)
    size_mb = os.path.getsize(target) / 1024 / 1024
    print(f"  fertig, {size_mb:.1f} MB", file=sys.stderr)


def load_headwords(db_path: str) -> set[str]:
    with sqlite3.connect(db_path) as con:
        return {
            row[0].lower() for row in con.execute("SELECT DISTINCT written_rep FROM translation")
        }


def lemma_candidates(word: str):
    """Grobe Kandidaten für die Grundform. Später durch echte Lemmatisierung ersetzen."""
    yield word
    if word.endswith("ies"):
        yield word[:-3] + "y"
    if word.endswith("es"):
        yield word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        yield word[:-1]
    if word.endswith("ed"):
        yield word[:-2]
        yield word[:-1]
        if len(word) > 4 and word[-3] == word[-4]:  # stopped -> stop
            yield word[:-3]
    if word.endswith("ing"):
        yield word[:-3]
        yield word[:-3] + "e"  # shutting -> shut / making -> make
        if len(word) > 5 and word[-4] == word[-5]:
            yield word[:-4]
    for suffix in ("ly", "er", "est"):
        if word.endswith(suffix):
            yield word[: -len(suffix)]
    if "-" in word:  # arm-chair -> armchair
        yield word.replace("-", "")


def read_text(path: str) -> str:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        text = fh.read()
    if start := GUTENBERG_START.search(text):
        text = text[start.end() :]
    if end := GUTENBERG_END.search(text):
        text = text[: end.start()]
    return text


def check_file(path: str, headwords: set[str], example_count: int) -> None:
    text = read_text(path)
    tokens = WORD.findall(text)
    if not tokens:
        print(f"{path}: kein Text gefunden", file=sys.stderr)
        return

    frequency = collections.Counter(t.lower() for t in tokens)
    capitalized = collections.Counter(t.lower() for t in tokens if t[0].isupper())

    hits, misses = [], []
    for word in frequency:
        bucket = hits if any(c in headwords for c in lemma_candidates(word)) else misses
        bucket.append(word)

    groups: dict[str, list[str]] = {
        "Eigennamen": [],
        "unregelmäßige Formen": [],
        "Verkürzungen": [],
        "verbleibende Lücken": [],
    }
    for word in misses:
        plain = word.replace("-", "").replace("'", "")
        if word in CONTRACTIONS:
            groups["Verkürzungen"].append(word)
        elif word in IRREGULAR_FORMS or plain in IRREGULAR_FORMS:
            groups["unregelmäßige Formen"].append(word)
        elif capitalized[word] / frequency[word] > 0.85:
            groups["Eigennamen"].append(word)
        else:
            groups["verbleibende Lücken"].append(word)

    word_forms = len(frequency)
    total_tokens = sum(frequency.values())
    hit_tokens = sum(frequency[w] for w in hits)
    gaps = groups["verbleibende Lücken"]
    gap_tokens = sum(frequency[w] for w in gaps)

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"  Wortformen (types)          {word_forms:>8,}")
    print(f"  Wörter gesamt (tokens)      {total_tokens:>8,}")
    print(f"  Stichworttreffer            {len(hits):>8,}  ({len(hits) / word_forms:6.1%})")
    print(f"  Textabdeckung roh           {hit_tokens / total_tokens:>13.1%}")
    print("\n  Fehltreffer nach Ursache:")
    for name, words in groups.items():
        print(f"    {name:<24} {len(words):>6,}  ({len(words) / word_forms:5.1%} der Wortformen)")

    print(
        f"\n  Restlücke nach Lemmatisierung + Eigennamenfilter: "
        f"{gap_tokens / total_tokens:.2%} der Wörter  (Obergrenze)"
    )

    if gaps:
        most_frequent = sorted(gaps, key=lambda w: -frequency[w])[:example_count]
        print("  Häufigste verbleibende Lücken:")
        print("    " + ", ".join(f"{w} ({frequency[w]})" for w in most_frequent))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Misst die Wörterbuchabdeckung an echtem Buchtext.",
        epilog="Siehe technik.md, Abschnitt 2, für die Einordnung der Zahlen.",
    )
    p.add_argument("files", nargs="*", help="Textdateien (UTF-8), z. B. aus Project Gutenberg")
    p.add_argument(
        "--db", default=DEFAULT_DB, help=f"Pfad zur WikDict-Datenbank (Vorgabe: {DEFAULT_DB})"
    )
    p.add_argument(
        "--examples", type=int, default=30, help="Anzahl gezeigter Fehltreffer (Vorgabe: 30)"
    )
    p.add_argument(
        "--fetch-dictionary", action="store_true", help="Datenbank herunterladen und beenden"
    )
    args = p.parse_args()

    if args.fetch_dictionary:
        fetch_dictionary(args.db)
        return 0

    if not args.files:
        p.print_help()
        return 1

    fetch_dictionary(args.db)
    headwords = load_headwords(args.db)
    print(f"Wörterbuch: {args.db}\nStichwörter: {len(headwords):,}")

    for path in args.files:
        if not os.path.exists(path):
            print(f"nicht gefunden: {path}", file=sys.stderr)
            continue
        check_file(path, headwords, args.examples)

    print("\nHinweis: Die Restlücke ist eine Obergrenze — die Suffix-Heuristik trifft")
    print("unregelmäßige Formen nicht. Siehe Modulbeschreibung im Skript.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
