"""Sammelt die echten Inhalte für den Mockup aus tools/sherlock.epub und tools/en-de.sqlite3.

Kein Blindtext und — das ist der Zweck — kein *schmeichelhafter* Fall: Gesucht wird
ausdrücklich der **längste** Belegsatz des Kapitels unter den häufigsten Wörtern und die
**längste** Übersetzungskette, weil der Mockup im ungünstigsten Datenfall zu rendern ist
(review_round1.md B24).

Das Ergebnis `data.json` ist **nicht versioniert**: Es trägt 1.486
WikDict-Bedeutungseinträge, und die CC-BY-SA-Datenbank gibt das Repositorium bewusst nicht
weiter (technik.md §2, „Warum nicht mitgeliefert"; §14, „Was vom Mockup versioniert ist und
was nicht"). Versioniert ist nur, was `build_content.py` daraus macht — und dort in
Zitatgröße, ausgewiesen in `NOTICE`, Abschnitt 6.

Aufruf aus dem Wurzelverzeichnis des Repositoriums:
    PYTHONPATH=. .venv/Scripts/python.exe <dieses Skript>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from libreverbum import dictionary, epub, extraction, triage

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "data.json"
EPUB = REPO / "tools" / "sherlock.epub"
DICT = REPO / "tools" / "en-de.sqlite3"
CHAPTER_NUMBER = 2


def main() -> None:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    structure = epub.read_structure(EPUB)
    reference = next(c for c in structure.chapters if c.number == CHAPTER_NUMBER)
    chapter = epub.read_chapter(EPUB, structure.book, reference)
    nlp = extraction.load_nlp()
    # Buchweite Eigennamenstatistik wie in `pipeline.run_chapter`: ohne sie zählt `miss`
    # 19× statt 1× (Occurrence-Docstring).
    all_chapters = []
    for ref in structure.chapters:
        try:
            all_chapters.append(epub.read_chapter(EPUB, structure.book, ref))
        except epub.ChapterWithoutTextError:
            continue
    ratios = extraction.book_proper_noun_ratios(all_chapters, nlp)
    result = extraction.extract_vocabulary(chapter, nlp, book_proper_noun_ratios=ratios)
    ranked = triage.sort_by_frequency(result.occurrences)

    # Profilfilter wie im echten Lauf: Wer auf B1 vorbelegt, kennt die ersten 2000
    # Grundformen der eingefrorenen Liste (`PRESET_WORD_COUNT[B1]`). Ohne diesen Schritt
    # bestuende der Block aus `have`, `said`, `then` — kein Fall, den die Triage je zeigt.
    preset = {
        line.strip().lower()
        for line in (REPO / "libreverbum" / "wordfreq_en_5000.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.startswith("#")
    }
    preset = set(list(preset)[:0]) | {
        w
        for i, w in enumerate(
            [
                line.strip().lower()
                for line in (REPO / "libreverbum" / "wordfreq_en_5000.txt")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip() and not line.startswith("#")
            ]
        )
        if i < 2000
    }
    unknown = [o for o in ranked if o.lemma.text.lower() not in preset]
    print(f"{len(ranked)} Grundformen, davon {len(unknown)} ausserhalb der B1-Vorbelegung")

    lemmas = [o.lemma for o in unknown]
    lists = dictionary.candidate_lists(DICT, lemmas)

    rows = []
    for occurrence, senses in zip(unknown, lists, strict=True):
        rows.append(
            {
                "form": occurrence.word_form,
                "lemma": occurrence.lemma.text,
                "pos": occurrence.lemma.pos,
                "frequency": occurrence.frequency,
                "sentence": occurrence.example_sentence,
                "sentence_len": len(occurrence.example_sentence),
                "senses": [
                    {
                        "trans": s.wikdict_trans_list,
                        "sense": dictionary.label(s),
                        "uncertain": s.uncertain,
                    }
                    for s in senses
                ],
            }
        )

    OUT.write_text(
        json.dumps(
            {
                "book": {"title": structure.book.title, "author": structure.book.author},
                "chapter": {"number": CHAPTER_NUMBER, "title": chapter.title},
                "token_count": result.token_count,
                "vocabulary_size": len(result.occurrences),
                "rows": rows,
                "labels": {
                    "no_sense": dictionary.NO_SENSE_LABEL,
                    "uncertain": dictionary.UNCERTAIN_LABEL,
                    "source_notice": dictionary.SOURCE_NOTICE,
                },
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    longest = max(rows, key=lambda r: r["sentence_len"])
    print(
        f"{len(rows)} Zeilen, längster Belegsatz {longest['sentence_len']} Zeichen "
        f"bei {longest['form']!r}"
    )


if __name__ == "__main__":
    main()
