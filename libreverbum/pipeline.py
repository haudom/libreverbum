"""Durchlauf — verkettet die ersten Schritte des Kernablaufs zu einem Durchstich für ein
Kapitel (bauplan.md T15).

Aufgabe
-------
Ein vollständiger Durchlauf für **ein** Kapitel, sinnvollerweise als Durchstich angelegt,
sobald T3, T5 und T8 stehen (bauplan.md T15): EPUB-Struktur lesen, das gewählte Kapitel
einlesen, den Wortschatz je Vorkommen extrahieren — Einzelwörter **und**
Mehrwortausdrücke —, dazu die Auswahllisten aus dem Wörterbuch beschaffen und den
Kenntnisstand jeder Bedeutung darin gegen das Profil abgleichen. `pipeline` ist nach
technik.md §7 der einzige Ort im Kern, der mehrere Schrittmodule kennen darf — hier
`epub`, `extraction`, `dictionary` und `profile`.

Voraussetzungen
---------------
`nlp` ist ein bereits geladenes spaCy-Modell (`extraction.load_nlp()`) — das Laden kostet
rund eine Sekunde (technik.md §5) und bleibt Sache des Aufrufers, damit es bei mehreren
Kapiteln nur einmal anfällt, genau wie schon bei `extraction` selbst. Alle Pfade (EPUB,
Wörterbuch, Profil) kommen als Argument; `pipeline` kennt so wenig eine Vorgabe wie jedes
andere Kernmodul (technik.md §9).

Die Wörterbuchdatei wird deshalb **vor** jeder teuren Arbeit geprüft (Befund 3, Review
T15), nicht erst beim ersten Nachschlagen: Ein Kapitel ohne ein einziges erkanntes
Vorkommen — etwa eines aus lauter Eigennamen — riefe `dictionary.candidate_lists` sonst
nie auf, und ein fehlendes Wörterbuch bliebe hinter einem leeren, aber scheinbar
erfolgreichen Ergebnis unbemerkt (Regel 13). Nebeneffekt: Der Fehlschlag kommt sofort,
statt erst nach dem teuren spaCy-Lauf.

Liefert
-------
`run_chapter` liefert `ChapterVocabulary`: das eingelesene Kapitel, den Hinweis aus
`epub.read_structure`, falls der Datei die Navigation fehlt, `entries` — je
Einzelwort-Vorkommen aus `extraction.extract_vocabulary` einen `VocabularyEntry` mit
dessen Auswahlliste aus dem Wörterbuch (`dictionary.candidate_lists`, Befund 4, Review
T15) und dem Kenntnisstand jeder einzelnen Bedeutung darin
(`profile.compare_chapter_vocabulary`) — und, als **eigenes** Feld daneben,
`expressions`: dieselbe Bauart für die Mehrwortausdruck-Kandidaten aus T4
(`extraction.extract_particle_verb_candidates`, `extract_contiguous_candidates`),
abgeglichen über `dictionary.particle_verb_candidates` und `contiguous_candidates` (T7).

Beide Felder stehen **nebeneinander**, nicht zu einer gemeinsamen Liste zusammengeführt
(Befund 1, Review T15): Wie eine Wendung und die Einzelwörter, aus denen sie besteht, bei
Überschneidung in einer Anzeige zueinanderstehen sollen — Reihenfolge, Vorrang
(`give up` neben `give` und `up`) —, ist eine inhaltliche Frage, keine reine
Verkettungsfrage, und Regel 14 entscheidet sie hier nicht auf Vorrat. Ohne diese
Zusammenführung fehlten die Wendungen im Ergebnis aber vollständig, nicht nur unsortiert
— deshalb liefert der Durchstich sie ab dieser Behebung als eigenes Feld, statt sie ganz
zu verschweigen. Was zu tun bleibt, steht in `nacharbeit.md`. Ein reiner Lesezugriff, es
wird kein Ereignis in das Profil geschrieben.

**Hier endet der Durchstich.** Die nächste Stufe des Kernablaufs ist `translation` (T11):
Sie wählt aus der Auswahlliste jedes `VocabularyEntry` — in `entries` wie in
`expressions` — die im Belegsatz gemeinte Bedeutung aus. T11 ist im Bauplan ausdrücklich
gesperrt, bis die zweite Messung aus E10 vorliegt (bauplan.md, Tor 0, „Skaliert das
Bündeln beim Modell?") — ohne sie müsste geraten werden, ob einzeln oder gebündelt
gefragt wird, und eine geratene Auswahl wäre genau der stille Fehlschlag, den Regel 13
verbietet. Gesperrt ist damit nur die *markierte* Bedeutung, nicht die Triage selbst
(Befund 10, Review T15): Für die Standardstellung „Wörterbuch" (konzept.md §4, Tabelle
„Stellung") liefert `run_chapter` bereits alles, was die Triage (Schritt 4) dort
braucht — die Liste der möglichen Bedeutungen ohne Markierung, rund 1,1 s, kein
Modellaufruf. T16 kann darauf aufbauen, ohne auf T11 zu warten.

Regeln
------
Der Abgleich gegen das Profil läuft **nach** dem Nachschlagen im Wörterbuch, nicht davor:
`profile.compare_chapter_vocabulary` erwartet aufgelöste Bedeutungen (`entities.Sense`
samt `wikdict_`-Feldern), weil Kenntnis pro Bedeutung geführt wird, nicht pro Wort
(technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort"). Begründet und
für T15 ausdrücklich festgehalten in konzept.md, Nachtrag 18.08.2026 beim Kernablauf:
„damit T15 die Reihenfolge nicht neu entscheidet."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from libreverbum import dictionary, epub, extraction, profile
from libreverbum.entities import Chapter, Occurrence, Sense
from libreverbum.profile import VocabularyStatus

if TYPE_CHECKING:
    from pathlib import Path

    from spacy.language import Language


@dataclass(frozen=True)
class VocabularyEntry:
    """Ein Vorkommen — Einzelwort oder Mehrwortausdruck — samt seiner Auswahlliste aus dem
    Wörterbuch und dem Kenntnisstand jeder einzelnen Bedeutung darin
    (`profile.compare_chapter_vocabulary`). Für `ChapterVocabulary.entries` liefert
    `dictionary.candidate_lists` die Auswahlliste, für `ChapterVocabulary.expressions`
    `dictionary.particle_verb_candidates` beziehungsweise `contiguous_candidates` (Befund
    1, Review T15) — derselbe Feldtyp für beide, weil er nichts über die Herkunft des
    Vorkommens behauptet.

    `status` trägt nur die Bedeutungen aus `candidates` — bei einer leeren Auswahlliste
    (kein Wörterbucheintrag für diese Grundform und Wortart) bleibt auch `status` leer,
    statt einen Kenntnisstand für eine nicht vorhandene Bedeutung zu behaupten."""

    occurrence: Occurrence
    candidates: list[Sense]
    status: dict[Sense, VocabularyStatus]


@dataclass(frozen=True)
class ChapterVocabulary:
    """Ergebnis eines Durchlaufs (`run_chapter`, bauplan.md T15): das gelesene Kapitel,
    der Hinweis aus `epub.read_structure`, falls der Datei die Navigation fehlt
    (`None`, wenn nicht), `entries` — je Einzelwort-Vorkommen ein `VocabularyEntry`, in
    der Reihenfolge des ersten Auftretens im Kapitel, wie `extraction.extract_vocabulary`
    sie liefert (Häufigkeitssortierung ist Sache von `triage`, nicht dieses Moduls) — und
    `expressions`: dieselbe Bauart für die Mehrwortausdruck-Kandidaten aus T4/T7, ein
    `VocabularyEntry` je Kandidat aus `extraction.extract_particle_verb_candidates` und,
    soweit er einen Wörterbucheintrag hat, je Kandidat aus
    `extract_contiguous_candidates` (Befund 1, Review T15) — ein Kandidat aus dem
    n-Gramm-Weg ohne bestandenen Filter erscheint hier nicht, wie `dictionary.
    contiguous_candidates` es für ihn selbst schon vorsieht (`dictionary.py`, „Liefert").
    `entries` und `expressions` stehen **nebeneinander**, nicht zu einer gemeinsamen Liste
    zusammengeführt — siehe Moduldocstring, Abschnitt „Liefert", und `nacharbeit.md`."""

    chapter: Chapter
    notice: str | None
    entries: list[VocabularyEntry]
    expressions: list[VocabularyEntry]


def run_chapter(
    *,
    epub_path: Path,
    chapter_number: int,
    dictionary_path: Path,
    profile_path: Path,
    nlp: Language,
) -> ChapterVocabulary:
    """Ein Durchlauf für ein Kapitel (bauplan.md T15): Wörterbuchdatei vorab prüfen (Befund
    3, Review T15), EPUB-Struktur lesen, das Kapitel mit `chapter_number` auswählen und
    einlesen, seinen Wortschatz je Einzelwort (`entries`) und je Mehrwortausdruck-Kandidat
    (`expressions`) extrahieren, die Auswahllisten aus dem Wörterbuch beschaffen und gegen
    das Profil abgleichen.

    Bricht sichtbar ab (Regel 13), wenn `dictionary_path` keine lesbare Datei ist — geprüft
    **vor** dem teuren spaCy-Lauf: Ein Kapitel ohne ein einziges erkanntes Vorkommen (etwa
    eines aus lauter Eigennamen) riefe `dictionary.candidate_lists` sonst nie auf, und ein
    fehlendes Wörterbuch bliebe hinter einem leeren, aber scheinbar erfolgreichen Ergebnis
    unbemerkt (Befund 3, Review T15) — oder wenn `chapter_number` in der Kapitelliste des
    Buchs nicht vorkommt, statt eines leeren Ergebnisses, das wie ein Kapitel ohne
    Wortschatz aussähe. Alle übrigen Fehlschläge (ungültige EPUB- oder Profildatei, oder
    eine Wörterbuchdatei, die zwar existiert, aber nicht im erwarteten Schema steht)
    stammen aus den verketteten Schrittmodulen selbst und werden hier nicht abgefangen,
    sondern reichen durch (Regel 13: kein `except`, das nur protokolliert und
    weiterläuft)."""
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    structure = epub.read_structure(epub_path)
    reference = next((c for c in structure.chapters if c.number == chapter_number), None)
    if reference is None:
        available = ", ".join(str(c.number) for c in structure.chapters)
        raise ValueError(
            f"{epub_path}: kein Kapitel Nummer {chapter_number} — vorhanden: {available}."
        )
    chapter = epub.read_chapter(epub_path, structure.book, reference)

    occurrences = extraction.extract_vocabulary(chapter, nlp)
    single_word_candidates = dictionary.candidate_lists(
        dictionary_path, [occurrence.lemma for occurrence in occurrences]
    )

    # Befund 1 (Review T15): Die Mehrwortausdruck-Kandidaten aus T4 werden abgeglichen,
    # nicht nur erwähnt — dictionary.particle_verb_candidates und contiguous_candidates
    # brauchen kein Modell, T11s Sperre betrifft nur die markierte Bedeutung (Regeln
    # oben). Ohne Aufrufer blieben `extraction.extract_particle_verb_candidates`,
    # `extract_contiguous_candidates` und die beiden T7-Abgleichsfunktionen tot, und
    # Abnahmekriterium 3 („mindestens … zwei Redewendungen") wäre über T16/T17 nicht
    # erfüllbar.
    particle_verb_occurrences = extraction.extract_particle_verb_candidates(chapter, nlp)
    particle_verb_matches = dictionary.particle_verb_candidates(
        dictionary_path, [occurrence.lemma for occurrence in particle_verb_occurrences]
    )
    contiguous_occurrences = extraction.extract_contiguous_candidates(chapter, nlp)
    contiguous_matches = dictionary.contiguous_candidates(
        dictionary_path, [occurrence.lemma for occurrence in contiguous_occurrences]
    )
    # dictionary.contiguous_candidates lässt einen Kandidaten ohne bestandenen Filter als
    # leere Liste verschwinden (`dictionary.py`, „Liefert") — dieselbe Regel gilt hier für
    # die Aufnahme in `expressions`: Ein Vorkommen ohne jede Bedeutung bleibt draußen,
    # anders als bei `particle_verb_candidates`, das für einen solchen Fall stets einen
    # `uncertain`-Platzhalter liefert und deshalb ungefiltert übernommen wird.
    expression_pairs = list(zip(particle_verb_occurrences, particle_verb_matches, strict=True)) + [
        (occurrence, matches)
        for occurrence, matches in zip(contiguous_occurrences, contiguous_matches, strict=True)
        if matches
    ]

    all_candidates = [sense for candidates in single_word_candidates for sense in candidates] + [
        sense for _, matches in expression_pairs for sense in matches
    ]

    con = profile.open_profile(profile_path)
    try:
        status_by_sense = profile.compare_chapter_vocabulary(con, all_candidates)
    finally:
        con.close()

    entries = [
        VocabularyEntry(
            occurrence=occurrence,
            candidates=candidates,
            status={sense: status_by_sense[sense] for sense in candidates},
        )
        for occurrence, candidates in zip(occurrences, single_word_candidates, strict=True)
    ]
    expressions = [
        VocabularyEntry(
            occurrence=occurrence,
            candidates=matches,
            status={sense: status_by_sense[sense] for sense in matches},
        )
        for occurrence, matches in expression_pairs
    ]

    return ChapterVocabulary(
        chapter=chapter, notice=structure.notice, entries=entries, expressions=expressions
    )
