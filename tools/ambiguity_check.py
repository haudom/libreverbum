#!/usr/bin/env python3
"""Mehrdeutigkeitstest: Wie viele Grundformen eines Kapitels haben mehr als eine Bedeutung?

Hintergrund
-----------
Entscheidung 10 (../konzept.md, Nachtrag beim Kernablauf) stellt die Bedeutungen vor die
Triage. Damit hängt an einer Zahl, *was* die Triage überhaupt anzeigt: Genügt eine
Entscheidung je Wort, oder muss sie bei einem nennenswerten Teil der Wörter je Bedeutung
getroffen werden? Die Frage steht wörtlich in ../bauplan.md, Tor 0, unter E10 und sperrt
dort T11 und T15. Sie lässt sich nicht ausrechnen, nur an echtem Material messen — das
tut dieses Skript.

Verfahren
---------
1. Buchtext an den Kapitelüberschriften trennen (``CHAPTER I.`` oder ``I. TITEL``)
2. Je Kapitel die Grundformen mit ``libreverbum.extraction.extract_vocabulary``
   bestimmen — Wortart, Lemmatisierung und Eigennamenfilter je Vorkommen wie in T3
3. Je Grundform die Auswahlliste mit ``libreverbum.dictionary.candidates`` holen — also
   nach den Regeln aus T5, insbesondere Regel 1: Zeilen ohne ``sense``-Text zählen mit
4. Auszählen: Anteil mehrdeutiger Grundformen, Median, Verteilung, die dicken Enden

Zusätzlich wird je Grundform gezählt, wie lang die Liste **ohne** den Wortartfilter wäre.
Das ist die Vorarbeit für den Messauftrag aus T18 (Wirkung der Wortart als Vorfilter auf
lange Auswahllisten, ../technik.md §3, ``run`` mit 48 Bedeutungen) und kostet hier nur
eine zweite Abfrage je Grundform.

Verfahren und seine Grenzen
---------------------------
Anders als die übrigen Werkzeuge hier braucht dieses Skript die **Projektumgebung**:
spaCy mit ``en_core_web_md`` und den Kern ``libreverbum`` selbst — dieselbe Ausnahme wie
bei ``nlp_check.py``. Sie ist unvermeidlich: Gemessen werden soll, was T3 und T5
tatsächlich liefern, nicht eine nachgebaute Näherung davon.

Es liest **nur**: Das Wörterbuch wird in ein temporäres Verzeichnis kopiert und der Index
aus ../technik.md §3, „Nachtrag 17.08.2026" auf der **Kopie** angelegt. Die Datei des
Nutzers bleibt unangetastet; ohne Index kostete ein Kapitel 32 bis 44 s statt 1,1 s.

Die Kapitelgrenzen stammen aus der Textfassung, nicht aus der EPUB-Navigation (T12). Für
diese Messung genügt das: Gefragt ist die Größenordnung je Kapitel, nicht die
Kapitelliste selbst.

Aufruf
------
    python tools/ambiguity_check.py buch.txt
    python tools/ambiguity_check.py buch.txt --chapter 1 --chapter 2
    python tools/ambiguity_check.py buch.txt --top 20
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import sqlite3
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# Der Kern ist nicht als Paket installiert (../technik.md §6: `pip` in die bestehende
# .venv/, kein `uv sync`) — deshalb das Repository-Wurzelverzeichnis von Hand auf den
# Suchpfad. Vor den Kern-Importen, nicht danach.
sys.path.insert(0, os.path.dirname(HERE))

from libreverbum import dictionary, extraction  # noqa: E402
from libreverbum.entities import Book, Chapter  # noqa: E402

DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

# Kapitelüberschrift in den gemeinfreien Textfassungen: entweder `CHAPTER I.` allein auf
# der Zeile (Dorian Gray) oder eine römische Zahl mit Titel dahinter (`I. A SCANDAL IN
# BOHEMIA`, Sherlock Holmes). Bewusst ohne führenden Leerraum: Das eingerückte
# Inhaltsverzeichnis derselben Dateien sähe sonst wie eine Kapitelfolge aus. Eine bloße
# `I.` auf eigener Zeile — die Abschnittsmarken innerhalb einer Sherlock-Erzählung —
# trennt kein Kapitel und steht deshalb nicht in diesem Muster.
CHAPTER_HEADING = re.compile(r"^(?:CHAPTER\s+[IVXLC]+\.?|[IVXLC]+\.\s+\S.*)$")

# Ende des Buchtextes in Gutenberg-Dateien. Ohne diesen Schnitt trüge das letzte Kapitel
# den vollständigen Lizenztext als Wortschatz.
GUTENBERG_END = "*** END OF THE PROJECT GUTENBERG"

# Die dicken Enden der Verteilung. Die Grenzen sind die Frage selbst: 1 ist eindeutig, 2
# ist der Grenzfall, ab 3 wird eine Liste zur Liste, über 10 ist sie nicht mehr
# überschaubar (../technik.md §3, offener Punkt „Sehr lange Auswahllisten").
BUCKETS = [(0, 0, "kein Eintrag"), (1, 1, "eindeutig"), (2, 2, "2"), (3, 5, "3-5"), (6, 10, "6-10")]
BUCKET_TAIL = "über 10"


def split_chapters(text: str) -> list[tuple[str, str]]:
    """Zerlegt den Buchtext an den Kapitelüberschriften. Liefert (Titel, Text) je Kapitel.

    Alles vor der ersten Überschrift (Titelei, Inhaltsverzeichnis) und alles ab der
    Gutenberg-Endmarke fällt weg.
    """
    end = text.find(GUTENBERG_END)
    if end != -1:
        text = text[:end]

    chapters: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if CHAPTER_HEADING.match(line.strip()) and line == line.strip():
            chapters.append((line.strip(), []))
        elif chapters:
            chapters[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in chapters]


def unfiltered_count(con: sqlite3.Connection, lemma_text: str) -> int:
    """Zahl der Wörterbuchzeilen zur Grundform **ohne** Wortartfilter — sonst dieselbe
    Abfrage wie in `dictionary.candidates` (Vorarbeit zum Messauftrag aus T18)."""
    row = con.execute(
        "SELECT COUNT(*) FROM translation WHERE written_rep = ? AND lexentry IS NOT NULL",
        (lemma_text,),
    ).fetchone()
    return int(row[0])


def describe(counts: list[int]) -> str:
    """Eine Zeile mit Median und Verteilung über eine Liste von Bedeutungszahlen."""
    parts = []
    for low, high, label in BUCKETS:
        hits = sum(1 for c in counts if low <= c <= high)
        parts.append(f"{label}: {hits} ({hits / len(counts):.1%})")
    tail = sum(1 for c in counts if c > BUCKETS[-1][1])
    parts.append(f"{BUCKET_TAIL}: {tail} ({tail / len(counts):.1%})")
    return "  ".join(parts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Zählt, wie viele Grundformen eines Kapitels mehr als eine Bedeutung haben.",
        epilog="Beantwortet die erste der beiden offenen Zahlen zu E10 in bauplan.md, Tor 0.",
    )
    p.add_argument("text", help="Buchtext als Textdatei")
    p.add_argument("--db", default=DEFAULT_DB, help="Pfad zur WikDict-Datenbank")
    p.add_argument(
        "--chapter", action="append", type=int, help="nur diese Kapitelnummern (mehrfach möglich)"
    )
    p.add_argument("--top", type=int, default=15, help="wie viele der längsten Listen zeigen")
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        print("Mit  python tools/coverage_check.py --fetch-dictionary  herunterladen.")
        return 1

    with open(args.text, encoding="utf-8") as fh:
        chapters = split_chapters(fh.read())
    if not chapters:
        print(f"Keine Kapitelüberschriften in {args.text} gefunden.", file=sys.stderr)
        return 1

    wanted = [
        (number, title, text)
        for number, (title, text) in enumerate(chapters, 1)
        if not args.chapter or number in args.chapter
    ]
    if not wanted:
        print("Keine Kapitel mit den angegebenen Nummern.", file=sys.stderr)
        return 1

    book = Book(title=os.path.basename(args.text), author="")
    print(f"Text: {args.text}   Kapitel: {len(chapters)}, gemessen: {len(wanted)}")

    with tempfile.TemporaryDirectory() as workspace:
        # Auf einer Kopie, nie auf der Datei des Nutzers: `ensure_index` schreibt.
        db_copy = os.path.join(workspace, "en-de.sqlite3")
        shutil.copyfile(args.db, db_copy)
        dictionary.ensure_index(pathlib.Path(db_copy))
        print(f"Wörterbuch: Kopie von {args.db}, mit Index (technik.md §3, Nachtrag 17.08.2026)")

        nlp = extraction.load_nlp()
        con = sqlite3.connect(db_copy)
        try:
            all_counts: list[int] = []
            all_unfiltered: list[int] = []
            # Je Grundform einmal, über alle Kapitel zusammengezählt: sonst füllte
            # dasselbe `break` die Liste der dicken Enden zwölfmal.
            longest: dict[tuple[str, str], tuple[int, int]] = {}
            print("\n" + "=" * 78)
            for number, title, text in wanted:
                chapter = Chapter(book=book, number=number, title=title, text=text)
                occurrences = extraction.extract_vocabulary(chapter, nlp)
                counts = []
                for occurrence in occurrences:
                    lemma = occurrence.lemma
                    count = len(dictionary.candidates(pathlib.Path(db_copy), lemma))
                    counts.append(count)
                    all_unfiltered.append(unfiltered_count(con, lemma.text))
                    seen = longest.get((lemma.text, lemma.pos), (count, 0))
                    longest[(lemma.text, lemma.pos)] = (count, seen[1] + occurrence.frequency)
                all_counts.extend(counts)

                ambiguous = sum(1 for c in counts if c > 1)
                print(
                    f"\nKapitel {number:>2}  {title[:44]:<44}  "
                    f"{len(counts):>5} Grundformen, davon {ambiguous:>5} mehrdeutig "
                    f"({ambiguous / len(counts):.1%})"
                )
                print("   " + describe(counts))
        finally:
            con.close()

    print("\n" + "=" * 78)
    total = len(all_counts)
    with_entry = [c for c in all_counts if c]
    ambiguous = [c for c in all_counts if c > 1]
    print(f"Grundformen insgesamt (Kapitel zusammengezählt): {total}")
    print(f"  mit Wörterbucheintrag: {len(with_entry)} ({len(with_entry) / total:.1%})")
    print(
        f"  mehrdeutig (mehr als eine Bedeutung): {len(ambiguous)} ({len(ambiguous) / total:.1%})"
    )
    if with_entry:
        print(
            f"  davon gemessen an den Grundformen mit Eintrag: "
            f"{len(ambiguous) / len(with_entry):.1%}"
        )
        print(f"  Median der Bedeutungszahl (mit Eintrag): {statistics.median(with_entry):g}")
    if ambiguous:
        print(f"  Median unter den mehrdeutigen: {statistics.median(ambiguous):g}")
    print("  " + describe(all_counts))
    # Die Entscheidungsfrage aus E10 in Zahlen: Eine Triage-Entscheidung je Bedeutung
    # statt je Wort vervielfacht die Zahl der Entscheidungen um genau diesen Faktor.
    print(
        f"  Bedeutungen insgesamt: {sum(all_counts)} — eine Entscheidung je Bedeutung statt "
        f"je Wort wäre der Faktor {sum(all_counts) / total:.1f}"
    )
    print(
        f"  je Kapitel im Mittel: {total / len(wanted):.0f} Grundformen, "
        f"{sum(all_counts) / len(wanted):.0f} Bedeutungen"
    )
    if all_unfiltered:
        without_pos = [c for c in all_unfiltered if c > 1]
        print(
            f"\nOhne Wortartfilter (Vorarbeit T18): {len(without_pos)} von {len(all_unfiltered)} "
            f"({len(without_pos) / len(all_unfiltered):.1%}) hätten mehr als eine Zeile, "
            f"Median {statistics.median([c for c in all_unfiltered if c]):g}"
        )

    print(f"\nDie {args.top} längsten Auswahllisten:")
    ranked = sorted(longest.items(), key=lambda item: (-item[1][0], item[0]))
    for (text, pos), (count, frequency) in ranked[: args.top]:
        print(f"  {count:>3} Bedeutungen  {text} ({pos}), {frequency}× im Text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
