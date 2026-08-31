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

Dazu, seit Bauschritt 3/5 der Vorbelegung (31.08.2026), `write_vocabulary_preset`: trägt
die häufigsten Grundformen des beim Anlegen des Profils gewählten Sprachniveaus als
bekannt ein (konzept.md, „Bewusst offen", „Woher der Nutzer seinen Grundwortschatz
bekommt"). Auch dafür kennt nur `pipeline` `dictionary` (die Wortarten und Bedeutungen
der eingefrorenen Liste, `wordfreq_en_5000.txt`) **und** `profile` (das Sammelschreiben,
`profile.record_preset`) zugleich.

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
zu verschweigen. Beantwortet ist die inhaltliche Frage seit T16: Beide Listen laufen als
**zwei getrennte Durchläufe** mit je eigenem Deckel (`cli/interaction.py`, „Festlegung:
getrennte Decksel für Wörter und Wendungen"). Was an `pipeline` darüber hinaus offen
bleibt, steht in technik.md §7, „Offene Punkte". Ein reiner Lesezugriff, es wird kein
Ereignis in das Profil geschrieben.

**`run_chapter` bleibt der netzlose Teil**, auch wenn ihre Laufzeit das seit der
T17-Nachbesserung (schwer 1, zweiter Anlauf, 26.08.2026) nicht mehr vermuten lässt: Sie
liest inzwischen **das ganze Buch** ein, um den buchweiten Eigennamenanteil vorzuberechnen
(`extraction.book_proper_noun_ratios`, technik.md §5, REGEL bei `extraction.
_PROPER_NOUN_RATIO_THRESHOLD`) — ein voller spaCy-Lauf je Kapitel, rund 22 respektive 29 s
für die beiden EPUBs unter `tools/` (siehe Bericht zur Abnahme), statt der zuvor rund 1,1 s
(technik.md §3, „Nachtrag 17.08.2026") für Nachschlagen und Profilabgleich allein. Ohne
diese Vorarbeit ließe sich der `Sibyl`-Fall aus Kapitel 10 nicht auflösen: Ein Tagger-Fehler
in drei Vorkommen eines einzelnen Kapitels verfälscht dessen eigenen Anteil, der buchweite
Anteil bleibt davon unberührt. **Netzlos** bleibt sie trotzdem — kein Modellserver ist dafür
nötig, nur spaCy und die beiden lokalen Dateien. Was aus der Auswahlliste für die Triage
wird, macht seit der zweiten T16-Durchsicht (Befund schwer 1) eine zweite Funktion,
`resolve_triage_entries`: Sie ruft `translation.choose_sense` auf — den einzigen Ort mit
Modellzugriff (technik.md §7) — und ist deshalb bewusst **nicht** Teil von `run_chapter`.
Zwei Gründe:

1. `run_chapter` bleibt ohne Netzabhängigkeit, statt für jeden Aufrufer verbindlich
   Modellanfragen mitzubringen — bei `[triage] order = "new_words_first"` (technik.md §9,
   Vorgabe) rund `limit` Stück, bei `"frequency"` unter Umständen mehrere Hundert
   (Auftragstext vom 25.08.2026, „Der Anlass": acht Messungen desselben Kapitels ergaben 36
   bis 206 Aufrufe, weil ein als `KNOWN` aufgelöster Eintrag zwar einen Aufruf kostet, aber
   keinen Platz von `limit` belegt). Ein künftiger Aufrufer, der nur die Auswahllisten
   braucht (etwa ein Messwerkzeug), bekommt sie weiterhin ohne Modellserver
2. `resolve_triage_entries` bekommt `limit` **je Decksel** (`cli.interaction.WORD_LIMIT` für
   `entries`, `EXPRESSION_LIMIT` für `expressions`, „Festlegung: getrennte Decksel",
   `cli/interaction.py`) — zwei verschiedene Aufrufe mit zwei verschiedenen Obergrenzen. In
   `run_chapter` selbst gäbe es dafür keinen natürlichen Ort, ohne dass das Modul plötzlich
   von `cli`-Konstanten wüsste

Regeln
------
Der Abgleich gegen das Profil in `run_chapter` läuft **nach** dem Nachschlagen im
Wörterbuch, nicht davor: `profile.compare_chapter_vocabulary` erwartet aufgelöste
Bedeutungen (`entities.Sense` samt `wikdict_`-Feldern), weil Kenntnis pro Bedeutung geführt
wird, nicht pro Wort (technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro
Wort"). Begründet und für T15 ausdrücklich festgehalten in konzept.md, Nachtrag 18.08.2026
beim Kernablauf: „damit T15 die Reihenfolge nicht neu entscheidet."

Eine Grundform ganz ohne Wörterbucheintrag (7,2 % je Kapitel, technik.md §3, Nachtrag
18.08.2026) bekommt in `entries` denselben Platzhalter wie `dictionary.
particle_verb_candidates` für ein Phrasal Verb ohne Treffer: einen einzelnen `Sense` mit
`uncertain=True` und ohne jedes `wikdict_`-Feld, statt einer leeren `candidates`-Liste
(Befund mittel, zweite T16-Durchsicht). Vor dieser Behebung stand dieser Platzhalter nur in
`cli.interaction._representative_sense`, nie in `candidates`/`status` — ein als „kenne ich"
gebuchtes Wort ohne Wörterbucheintrag (etwa „sunset") wurde dadurch bei jedem weiteren
Durchlauf erneut gefragt, weil der Vorfilter aus `resolve_triage_entries`
(`_all_candidates_known`) eine leere `candidates`-Liste nie als „bekannt" werten kann. Mit
dem Platzhalter in `candidates` **und** `status` (`profile.compare_chapter_vocabulary`
bekommt ihn wie jeden anderen Kandidaten) greift derselbe Vorfilter wie bei jedem
Wörterbucheintrag auch hier.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from libreverbum import dictionary, epub, extraction, profile, translation, triage
from libreverbum.entities import (
    CefrLevel,
    Chapter,
    Event,
    KnowledgeState,
    Lemma,
    Occurrence,
    Origin,
    Sense,
)
from libreverbum.profile import VocabularyStatus

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable, Sequence
    from datetime import datetime

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
    zusammengeführt — siehe Moduldocstring, Abschnitt „Liefert"."""

    chapter: Chapter
    notice: str | None
    entries: list[VocabularyEntry]
    expressions: list[VocabularyEntry]


def _drop_prefix_dominated_expressions(
    pairs: list[tuple[Occurrence, list[Sense]]],
) -> list[tuple[Occurrence, list[Sense]]]:
    """Entdoppelt Wendungspaare, bei denen die kürzere Wortfolge ein echtes Wortpräfix der
    längeren ist **und** dieselben Textstellen deckt (mittel 4, Abnahme T17, zweiter
    Anlauf, 26.08.2026) — siehe die Erläuterung am Aufrufer in `run_chapter`.

    „Dieselben Textstellen" wird über gleiche Häufigkeit geprüft, nicht über eine eigene
    Positionsspur (die dieses Modul nicht führt, `entities.Occurrence` trägt nur Häufigkeit
    und einen Belegsatz): `extraction.extract_contiguous_candidates` bildet jedes n-Gramm
    eines Laufs, jedes Vorkommen der längeren Wendung erzeugt also notwendig auch ein
    Vorkommen ihres Präfixes an derselben Stelle. Gleiche Häufigkeit heißt deshalb, dass die
    kürzere Fassung **kein** Vorkommen außerhalb der längeren hat — ungleiche Häufigkeit
    heißt, sie hat eigene, unabhängige Vorkommen und bleibt bestehen."""
    dominated: set[int] = set()
    for index, (occurrence, _) in enumerate(pairs):
        words = occurrence.lemma.text.split()
        for other_index, (other_occurrence, _) in enumerate(pairs):
            if index == other_index:
                continue
            other_words = other_occurrence.lemma.text.split()
            if (
                len(other_words) > len(words)
                and other_words[: len(words)] == words
                and other_occurrence.frequency == occurrence.frequency
            ):
                dominated.add(index)
                break
    return [pair for index, pair in enumerate(pairs) if index not in dominated]


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

    # (T17-Nachbesserung, schwer 1, zweiter Anlauf, 26.08.2026): Der Eigennamenfilter aus
    # extraction.extract_vocabulary braucht den buchweiten Anteil je Grundform (technik.md
    # §5, REGEL bei extraction._PROPER_NOUN_RATIO_THRESHOLD) — dafür müssen alle Kapitel des
    # Buchs gelesen und geparst werden, nicht nur das gewählte. `pipeline` ist nach
    # technik.md §7 der einzige Ort, der `epub` und `extraction` gemeinsam kennen darf;
    # die Vorberechnung gehört deshalb hierher, nicht nach `extraction` (das kennt kein
    # EPUB) und nicht nach `cli` (das läuft nach Regel 9 nie im selben Thread wie die
    # Oberfläche, hat mit dieser Funktion aber ohnehin keinen eigenen Berührungspunkt).
    # Kostet einen vollen spaCy-Lauf je Kapitel des Buchs (siehe Bericht zur Abnahme,
    # rund 22 respektive 29 s für die beiden tools/-EPUBs) — der Preis dafür, dass ein
    # Tagger-Fehler in drei Vorkommen eines einzelnen Kapitels („Sibyl dead!", „Sibyl!")
    # den je Kapitel berechneten Anteil nicht mehr verfälschen kann.
    all_chapters = [chapter]
    for other_reference in structure.chapters:
        if other_reference.number == chapter_number:
            continue
        try:
            all_chapters.append(epub.read_chapter(epub_path, structure.book, other_reference))
        except ValueError as error:
            # Vorspann-/Impressum- und reine Bildband-Kapitel (epub.read_chapter, „Bricht
            # mit einer deutschen Meldung ab") tragen keinen Wortschatz bei und dürfen bei
            # der buchweiten Zählung fehlen — jeder andere ValueError (kaputtes Archiv,
            # falsche Kodierung, fehlendes Dokument im Archiv) bleibt dagegen sichtbar
            # (Regel 13) statt die Statistik lautlos zu verfälschen.
            message = str(error)
            if "besteht nur aus Vorspann bzw. Impressum" not in message and (
                "Bildband ohne Text" not in message
            ):
                raise
    book_proper_noun_ratios = extraction.book_proper_noun_ratios(all_chapters, nlp)

    occurrences = extraction.extract_vocabulary(
        chapter, nlp, book_proper_noun_ratios=book_proper_noun_ratios
    )
    single_word_candidates = dictionary.candidate_lists(
        dictionary_path, [occurrence.lemma for occurrence in occurrences]
    )
    # (Befund mittel, zweite T16-Durchsicht): Eine leere Auswahlliste bekommt hier
    # denselben Platzhalter wie dictionary.particle_verb_candidates für ein Phrasal Verb
    # ohne Treffer (Sense(lemma=..., uncertain=True), kein wikdict_-Feld) — siehe
    # Moduldocstring, letzter Absatz. Ohne diese Angleichung stünde der Platzhalter nur
    # auf der Schreibseite (früher `cli.interaction._representative_sense`), nie in
    # `candidates`/`status`, und ein Wort ohne Wörterbucheintrag könnte nie als „bekannt"
    # erkannt werden.
    single_word_candidates = [
        candidates or [Sense(lemma=occurrence.lemma, uncertain=True)]
        for occurrence, candidates in zip(occurrences, single_word_candidates, strict=True)
    ]

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
    #
    # (mittel 5, Abnahme T17, 25.08.2026): Beide Wege können dieselbe Wortfolge liefern —
    # ein Verb-Partikel-Paar, das im Satz nicht getrennt steht („sat down"), ist zugleich
    # ein zusammenhängendes 2-Gramm und trifft, sofern die Wendung im Wörterbuch steht, in
    # beiden Kandidatenlisten. Gemessen an tools/dorian_gray.epub Kapitel 10 mit dem echten
    # tools/en-de.sqlite3 (der im Auftrag genannte Fall, 25.08.2026): 19 von 139 Wendungen
    # kamen doppelt vor, und in allen 19 war die Häufigkeit aus
    # `particle_verb_occurrences` mindestens so hoch wie die aus `contiguous_occurrences`
    # (18-mal gleich, einmal höher — „find out": 2 gegen 1, weil die Abhängigkeitsanalyse
    # die Wendung auch dann noch findet, wenn sie ausnahmsweise getrennt geschrieben ist,
    # der n-Gramm-Weg dagegen nur bei zusammenhängender Schreibung überhaupt einen
    # Kandidaten bildet, `extraction.py`, „extract_particle_verb_candidates"). Beide Wege
    # zählen für dieselbe Wortfolge also dieselben Textstellen, nicht verschiedene —
    # zusammenzuzählen buchte sie doppelt, statt fehlende Information zu ergänzen. Gewinnt
    # deshalb die Partikelverb-Fassung: Sie trägt zusätzlich die Wortart (`VERB` statt
    # `extraction._NO_SINGLE_POS`, mehr Information für die Anzeige, siehe `anki.
    # pos_display`) und ihre Häufigkeit ist die vollständigere der beiden.
    particle_verb_lemma_texts = {occurrence.lemma.text for occurrence in particle_verb_occurrences}
    expression_pairs = list(zip(particle_verb_occurrences, particle_verb_matches, strict=True)) + [
        (occurrence, matches)
        for occurrence, matches in zip(contiguous_occurrences, contiguous_matches, strict=True)
        if matches and occurrence.lemma.text not in particle_verb_lemma_texts
    ]
    # (mittel 4, Abnahme T17, zweiter Anlauf, 26.08.2026): Die Entdopplung oben vergleicht
    # nur identische Wortfolgen — „in front" und „in front of" sind aber verschiedene
    # Lemmatexte und blieben beide stehen, mit demselben Belegsatz („…curtains … hung in
    # front of the three tall windows"), weil jedes Vorkommen der längeren Wendung
    # zugleich ein Vorkommen ihres Präfixes erzeugt (`extraction.extract_contiguous_
    # candidates`, jedes n-Gramm eines Laufs). Deckt eine längere Wendung dieselben
    # Textstellen ab wie eine kürzere, deren Wortfolge-Präfix sie ist — erkennbar an
    # gleicher Häufigkeit, denn dann hat die kürzere Fassung kein einziges Vorkommen
    # außerhalb der längeren —, gewinnt die längere, genauere Fassung. Bei
    # unterschiedlicher Häufigkeit hat die kürzere eigenständige Vorkommen und bleibt
    # erhalten („give up" neben „give up on", siehe Bericht).
    expression_pairs = _drop_prefix_dominated_expressions(expression_pairs)

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


@dataclass(frozen=True)
class ResolvedEntry:
    """Ein für die Triage aufbereiteter Eintrag (`resolve_triage_entries`): das Vorkommen
    und die im Belegsatz **gemeinte** Bedeutung — eine einzelne `Sense`, nicht mehr die
    volle Auswahlliste aus `VocabularyEntry.candidates` —, dazu ihr Kenntnisstand.

    Ersetzt die Auswahlliste in der Anzeige durch die aufgelöste Bedeutung (technik.md §3,
    Nachtrag 18.08.2026: „Die gewählte Bedeutung samt Belegsatz gehört also in die
    Anzeige — das ist Darstellung, keine zweite Entscheidung"). `status` ist nie `KNOWN`:
    Eine auf `KNOWN` aufgelöste Bedeutung fällt in `resolve_triage_entries` weg, bevor ein
    `ResolvedEntry` für sie entsteht (konzept.md, Abnahmekriterium 6)."""

    occurrence: Occurrence
    sense: Sense
    status: VocabularyStatus


@dataclass(frozen=True)
class TriageResolution:
    """Ergebnis von `resolve_triage_entries` für **einen** Decksel (Wörter oder Wendungen,
    `cli/interaction.py`, „Festlegung: getrennte Decksel"): `entries` — höchstens `limit`
    aufgelöste Einträge, in Häufigkeitsreihenfolge, bereit für die interaktive Triage —,
    dazu vier Zählungen für deren Meldungen davor, die zusammen mit `len(entries)` wieder
    die volle Eingabemenge ergeben (`resolve_triage_entries`, Schritte 1, 3, 4, 6; Befund
    mittel, Durchsicht 46ef37b — vorher verschwand `resolved_known` unbeziffert).

    `known`: wie viele Einträge der kostenlose Vorfilter bereits verworfen hat, weil jede
    ihrer Bedeutungen bekannt war (Abnahmekriterium 6, Schritt 1). `resolved_known`: wie
    viele weitere Einträge erst **nach** dem Auflösen als `KNOWN` verworfen wurden
    (Schritt 4) — der Vorfilter allein sieht das bei einem mehrdeutigen Wort nicht, weil
    nicht *jede* Bedeutung bekannt sein muss, nur die vom Modell aufgelöste (Befund mittel,
    Durchsicht 46ef37b: Vorher zählte nur `known`, und 21 von 25 im Auftragsbeispiel
    gebuchten „bereits bekannt"-Wörtern fehlten in jeder gemeldeten Zahl). `skipped`: wie
    viele Einträge trotz echter Wörterbuchkandidaten übersprungen wurden, weil das Modell
    „keine passt" wählte (Schritt 3; Befund schwer 1, Durchsicht 46ef37b — siehe
    `_resolve_sense`); anders als `known` und `resolved_known` steht dahinter **keine**
    Bedeutung, die gebucht werden könnte. `deferred`: wie viele der übrigen, nach
    Häufigkeit sortierten Einträge die Wortobergrenze gar nicht mehr erreicht hat
    (Schritt 6) — unangetastet wie das bisherige Verhalten von
    `triage.defer_beyond_word_limit`, nur an **behaltenen** statt an gesehenen Einträgen
    gezählt."""

    entries: list[ResolvedEntry]
    known: int
    resolved_known: int
    skipped: int
    deferred: int


def _all_candidates_known(entry: VocabularyEntry) -> bool:
    """Der kostenlose Vorfilter aus technik.md §3, Nachtrag 18.08.2026 („eine
    Triage-Entscheidung je Wort genügt"): Ein Eintrag gilt als vollständig bekannt, wenn er
    mindestens einen Kandidaten hat und **jeder** davon `VocabularyStatus.KNOWN` trägt. Ist
    jede mögliche Bedeutung bereits bekannt, ist es auch die, die das Modell wählen würde —
    ohne dass dafür eine Anfrage nötig wäre.

    Geprüft über `bool(entry.candidates)`, weil `all()` über eine leere Menge
    stillschweigend wahr wäre (Befund schwer 1, zweite T16-Durchsicht: die vormalige
    `cli.interaction._is_known` verglich stattdessen `any(...)` gegen dieses `all(...)` auf
    der Schreibseite — bei 65,8 % mehrdeutigen Grundformen je Kapitel [technik.md §3,
    Nachtrag 18.08.2026] traf das die meisten Wörter). Seit `run_chapter` auch für eine
    leere Auswahlliste einen Platzhalter in `candidates` führt (Moduldocstring, letzter
    Absatz), deckt dieselbe Prüfung auch ein Wort ganz ohne Wörterbucheintrag ab."""
    return bool(entry.candidates) and all(
        entry.status.get(sense) is VocabularyStatus.KNOWN for sense in entry.candidates
    )


def _no_candidate_known(entry: VocabularyEntry) -> bool:
    """Die zweite Hälfte der zweistufigen Auswahl (Auftragstext vom 25.08.2026, Abschnitt
    1): Ein Eintrag gilt als **sicherer Treffer**, wenn kein einziger seiner Kandidaten
    bereits `KNOWN` ist — welche Bedeutung das Modell in `_resolve_sense` auch wählt, sie
    ist damit garantiert nicht bekannt, und der Aufruf ist nie an einem `KNOWN`-Ergebnis
    verschwendet (anders als bei einem *teilweise* bekannten Eintrag, den erst der frische
    Profilabgleich in `resolve_triage_entries` als `resolved_known` verwirft).

    Zusammen mit `_all_candidates_known` zerlegt dieses Prädikat `entries` in die drei
    Gruppen aus dem Auftrag: **vollständig bekannt** (`_all_candidates_known`, kostenlos),
    **sicher** (kein Kandidat bekannt, dieses Prädikat) und **teilweise bekannt** (der
    Rest — weder das eine noch das andere)."""
    return all(entry.status.get(sense) is not VocabularyStatus.KNOWN for sense in entry.candidates)


def _resolve_sense(
    entry: VocabularyEntry, *, url: str, get_model_name: Callable[[], str]
) -> Sense | None:
    """Löst die im Belegsatz gemeinte Bedeutung eines einzelnen Eintrags auf — oder liefert
    `None`, wenn keine zuordenbar ist (siehe unten).

    Besteht `entry.candidates` **nur** aus dem Platzhalter ohne Wörterbucheintrag
    (`uncertain=True`, kein `wikdict_`-Feld — derselbe, den `run_chapter` für eine leere
    Auswahlliste einsetzt, und derselbe, den `dictionary.particle_verb_candidates` für ein
    Phrasal Verb ohne Treffer liefert), gibt es nichts zu wählen: kein Modellaufruf (Regel
    11), der Platzhalter bleibt die Bedeutung — `translation.py` überlässt diese
    Entscheidung ausdrücklich dem Aufrufer („Ob ein solcher Kandidat überhaupt zur
    Übersetzung vorgelegt wird, entscheidet der Aufrufer"). Sonst eine Anfrage an
    `translation.choose_sense`, auch bei genau einem echten Kandidaten: Dieselbe Funktion
    gilt für jede Kandidatenzahl, und die Kostenrechnung aus technik.md §3 (rund 1 s je
    Wort, „Naiv wäre das Modell für alle ~1.000 Grundformen … zu fragen") geht von genau
    dieser Zählweise aus. `get_model_name` wird deshalb erst hier aufgerufen, nicht vom
    Aufrufer vorab — eine Kette aus lauter Platzhaltern braucht den Modellserver nie."""
    # (Befund schwer 1, Durchsicht 46ef37b): Wählt das Modell hier die Ausweichantwort
    # „keine passt" (`choose_sense` liefert dafür denselben bloßen `Sense(uncertain=True)`
    # wie für eine leere Auswahlliste — translation.py, „Regeln"), gibt diese Funktion
    # `None` zurück statt des Platzhalters. `entry.candidates` besteht an dieser Stelle
    # ausschließlich aus echten, nicht-uncertain Wörterbuchkandidaten: Der einzige Weg, wie
    # ein VocabularyEntry hier je einen uncertain-Kandidaten führt (`run_chapter`s
    # Platzhalter für eine leere Auswahlliste, `dictionary.particle_verb_candidates` für
    # ein Phrasal Verb ohne Treffer), liefert ihn stets als **einzigen** Eintrag der Liste
    # — und der ist durch die frühe Rückgabe oben bereits abgedeckt. Ein `uncertain`-Ergebnis
    # von `choose_sense` kann in diesem Zweig deshalb nur aus dessen eigener
    # „keine passt"-Antwort stammen, nie aus einem übernommenen Kandidaten (anders als der
    # allgemeinere Fall, den translation.py, „Voraussetzungen" für sich offenhält). Vorher
    # schrieb dieser Platzhalter — ohne jeden `wikdict_`-Wert — als „kenne ich"/„überspringen"
    # gebuchte Bedeutung dauerhaft ins Profil und machte jede echte Bedeutung desselben
    # Lemmas fortan fälschlich zur „neuen Bedeutung eines bekannten Wortes" (Auftragstext,
    # „bank"-Beispiel). Ohne zuordenbare Bedeutung gibt es nichts, worauf eine
    # Triage-Entscheidung gebucht werden könnte — eine falsche Buchung im Profil ist teurer
    # als ein ausgelassenes Wort. Der Aufrufer (`resolve_triage_entries`) zählt diesen Fall
    # gesondert (`TriageResolution.skipped`) und meldet ihn, statt ihn stillschweigend wie
    # „kein Wörterbucheintrag" zu behandeln (Regel 13).
    if len(entry.candidates) == 1 and entry.candidates[0].uncertain:
        return entry.candidates[0]
    chosen = translation.choose_sense(
        url=url,
        model_name=get_model_name(),
        occurrence=entry.occurrence,
        sense_candidates=entry.candidates,
    )
    if chosen.uncertain:
        return None
    return chosen


_VALID_TRIAGE_ORDERS = ("new_words_first", "frequency")


def resolve_triage_entries(
    *,
    con: sqlite3.Connection,
    entries: Sequence[VocabularyEntry],
    limit: int,
    url: str,
    get_model_name: Callable[[], str],
    order: str = "new_words_first",
    on_progress: Callable[[int, int, int, int], None] | None = None,
) -> TriageResolution:
    """Bereitet einen Decksel aus `ChapterVocabulary` (`entries` oder `expressions`) für
    die interaktive Triage vor (Befund schwer 1, zweite T16-Durchsicht) — Vorfilter,
    zweistufige Auswahl, Bedeutungsauflösung durch das Modell, Wortobergrenze, in dieser
    Reihenfolge, damit das Budget aus technik.md §3 („Bei rund einer Sekunde je Wort … im
    Bereich einer halben Minute" bei höchstens 25 neuen Wörtern) hält, statt für alle rund
    1.000 Grundformen eines Kapitels zu fragen — das wären bei rund 1 s je Wort rund
    17 Minuten, bevor der Nutzer überhaupt etwas sieht. `order` steuert dabei, **welche**
    Einträge dem Modell zuerst vorgelegt werden (`[triage] order` aus `config.toml`,
    technik.md §9); ein anderer Wert als `"new_words_first"` oder `"frequency"` bricht
    sofort mit einer deutschen Meldung ab, statt still auf die Vorgabe zurückzufallen
    (Regel 13, dokumentation.md §4):

    1. **Vorfilter, kostenlos:** Ein Eintrag, dessen sämtliche Kandidaten bereits `KNOWN`
       sind, fällt ohne Modellaufruf weg (`_all_candidates_known`), gezählt in
       `TriageResolution.known`.
    2. **Zweistufige Auswahl** (Auftragstext vom 25.08.2026, Abschnitt 1) statt einer
       einzigen, gemeinsam sortierten Liste — der eigentliche Anlass: Acht Messungen
       desselben Kapitels ergaben unter der alten, einstufigen Häufigkeitsreihenfolge 36
       bis 206 Modellaufrufe, weil ein Eintrag, dessen aufgelöste Bedeutung sich als
       `KNOWN` herausstellt (Schritt 4 unten), zwar einen Aufruf kostet, aber keinen Platz
       von `limit` belegt — im Grenzfall (reifes Profil, neues Kapitel) fast jede der rund
       1.000 bis 1.400 Grundformen eines Kapitels. Der Rest aus Schritt 1 zerfällt deshalb
       in zwei weitere Gruppen (`_no_candidate_known`): **sichere Treffer** (kein Kandidat
       `KNOWN` — welche Bedeutung das Modell auch wählt, sie ist nicht bekannt, ein Aufruf
       hier ist nie an einem `KNOWN`-Ergebnis verschwendet) und **teilweise bekannte**
       (mindestens ein, aber nicht jeder Kandidat `KNOWN` — zugleich die Kandidaten für
       „neue Bedeutung eines bekannten Wortes", konzept.md §5). Bei `order =
       "new_words_first"` (Vorgabe) füllen die `limit` Plätze zuerst die sicheren Treffer,
       je Gruppe nach Häufigkeit (`triage.sort_by_frequency`) — erst wenn sie nicht
       reichen, geht es in die teilweise bekannten hinein; ein Kapitel mit genug sicheren
       Treffern kostet damit rund `limit` Modellaufrufe statt mehrerer Hundert. Bei `order
       = "frequency"` — dem bisherigen Verhalten — laufen beide Gruppen gemeinsam in
       einer einzigen Häufigkeitsreihenfolge, wie vor dieser Behebung; findet dabei mehr
       neue Bedeutungen bekannter Wörter, kostet bei reifem Profil aber wieder bis zu
       mehrere Hundert Aufrufe. Gemessen (`granite4.1:8b`, `sherlock.epub` Kapitel 2, 1410
       Worteinträge, vier Durchläufe je Einstellung mit wachsendem Profil, 25.08.2026):
       `new_words_first` 39 bis 44 Aufrufe (44 bis 64 s), `frequency` 39 bis 112 (21 bis
       37 s) — die Folge, die aus der Theorie oben nicht hervorgeht: Bei so vielen
       Worteinträgen liefern die sicheren Treffer allein schon mehr als `limit` Plätze, die
       teilweise bekannten werden unter `new_words_first` deshalb **nie** erreicht (in allen
       vier Läufen 0 Einträge „neue Bedeutung eines bekannten Wortes", konzept.md §5; unter
       `frequency` dagegen 0, 5, 1 und 8). Der `bank`-Fall aus konzept.md §5 ist auf der
       Vorgabe damit faktisch abgeschaltet, nicht nur seltener.
    3. In dieser Reihenfolge löst `_resolve_sense` je Eintrag die gemeinte Bedeutung auf
       (eine Anfrage je Wort, kein Bündeln — technik.md §3, Nachtrag 19.08.2026). Wählt das
       Modell dabei „keine passt", obwohl echte Wörterbuchkandidaten vorlagen, liefert
       `_resolve_sense` `None`: Der Eintrag wird übersprungen, ohne einen Platz von `limit`
       zu verbrauchen, ohne Profilabgleich und ohne Buchung — gezählt in
       `TriageResolution.skipped` (Befund schwer 1, Durchsicht 46ef37b). Anders als bei
       einem Wort ganz ohne Wörterbucheintrag (Schritt „Voraussetzungen" oben) gibt es hier
       nichts, worauf eine Triage-Entscheidung gebucht werden könnte.
    4. Sonst entscheidet der frisch gegen das Profil abgeglichene Kenntnisstand dieser
       **einen** aufgelösten Bedeutung weiter: `KNOWN` heißt, der Nutzer hat genau diese
       Bedeutung schon gebucht — der Eintrag fällt weg, ohne einen Platz von `limit` zu
       verbrauchen, gezählt in `TriageResolution.resolved_known`. Sonst bleibt er, markiert
       als `UNKNOWN` oder `NEW_MEANING_OF_KNOWN_WORD` (konzept.md §5, „Mehrdeutigkeit"; der
       `bank`-Fall: Ufer bekannt, Kapitel meint das Geldhaus — der Vorfilter aus Schritt 1
       greift nicht, weil nicht *jede* Bedeutung bekannt ist, das Modell löst auf, und die
       Geldhaus-Bedeutung erscheint markiert).
    5. Abbruch, sobald auf diese Art `limit` Einträge **behalten** wurden.
    6. Was danach in der sortierten Liste noch steht, wird nicht mehr angerührt: kein
       Modellaufruf, keine Anzeige, kein Ereignis — dieselbe Wirkung wie die bisherige
       Wortobergrenze, nur an behaltenen statt an gesehenen Einträgen gezählt
       (`TriageResolution.deferred`).

    Die **Anzeigereihenfolge** bleibt in beiden Fällen Häufigkeit: Die behaltenen Einträge
    werden am Ende erneut nach `triage.sort_by_frequency` sortiert, unabhängig davon, in
    welcher Reihenfolge sie beim Auflösen verarbeitet wurden — sonst schlüge die
    Auswahlstrategie aus Schritt 2 in die Triage durch, in der weiterhin die häufigsten
    Wörter zuerst stehen sollen (konzept.md §4).

    `known + resolved_known + skipped + deferred + len(resolution.entries)` ergibt wieder
    `len(entries)` — die Zahl der hier übergebenen Einträge, unabhängig davon, wie sie sich
    auf die vier Zählungen und die behaltene Liste verteilen. Die Zusicherung dazu steht in
    `tests/test_pipeline.py` (Auftrag zu Befund mittel, Durchsicht 46ef37b) — die
    zweistufige Auswahl führt keine neue Zählung ein, sie ändert nur die Reihenfolge, in
    der Schritt 3 die Einträge vorlegt.

    `on_progress`, falls übergeben, wird nach **jedem** Schritt 3/4-Durchlauf mit vier
    Zahlen aufgerufen — geprüfte Einträge, insgesamt zu prüfende (`len(ordered)`, vor
    Schritt 5 feststehend), bisher behaltene, `limit` —, damit die Kommandozeile eine sich
    fortschreibende Statuszeile zeigen kann (Auftragstext, Abschnitt 3): Ein Lauf, der bei
    `order = "frequency"` und reifem Profil minutenlang ohne jede Ausgabe rechnet, ist
    sonst der stille Fehlschlag, den Regel 13 verbietet. Der Kern selbst gibt nichts aus
    (technik.md §7) — `cli.main` bedient den Rückruf über `cli.display.safe_print_progress`.
    Ohne `on_progress` (Vorgabe `None`) verhält sich die Funktion wie vor dieser Behebung.

    Ein reiner Lese- und Netzzugriff auf `con`: Es wird kein Ereignis geschrieben, nur
    `profile.compare_chapter_vocabulary` befragt — das Schreiben bleibt Sache der
    interaktiven Triage (`cli.interaction.run_triage_pass`), die über jede getroffene
    Entscheidung entscheidet, nicht über die hier schon aufgelöste Bedeutung."""
    if order not in _VALID_TRIAGE_ORDERS:
        # REGEL (dokumentation.md §4 Regel 13): ein unzulässiger Wert bricht sichtbar ab
        # und nennt die zulässigen Werte, statt still auf die Vorgabe zurückzufallen.
        # `cli.config.load_config` prüft denselben Wert bereits beim Einlesen von
        # config.toml — diese Prüfung greift zusätzlich, weil resolve_triage_entries auch
        # unabhängig von der Kommandozeile aufrufbar bleibt (etwa aus einem Testwerkzeug).
        erlaubt = " oder ".join(f'"{wert}"' for wert in _VALID_TRIAGE_ORDERS)
        raise ValueError(f'order = "{order}" ist unzulässig — erlaubt sind {erlaubt}.')

    known_entries = [entry for entry in entries if _all_candidates_known(entry)]
    remaining = [entry for entry in entries if not _all_candidates_known(entry)]
    entries_by_occurrence = {entry.occurrence: entry for entry in remaining}

    if order == "new_words_first":
        certain_entries = [entry for entry in remaining if _no_candidate_known(entry)]
        partial_entries = [entry for entry in remaining if not _no_candidate_known(entry)]
        ordered = triage.sort_by_frequency(
            entry.occurrence for entry in certain_entries
        ) + triage.sort_by_frequency(entry.occurrence for entry in partial_entries)
    else:  # "frequency" — das bisherige Verhalten, geprüft ist order oben bereits
        ordered = triage.sort_by_frequency(entry.occurrence for entry in remaining)

    resolved: list[ResolvedEntry] = []
    resolved_known = 0
    skipped = 0
    examined = 0
    total_to_check = len(ordered)

    def _report_progress() -> None:
        if on_progress is not None:
            on_progress(examined, total_to_check, len(resolved), limit)

    for occurrence in ordered:
        if len(resolved) >= limit:
            break
        examined += 1
        entry = entries_by_occurrence[occurrence]
        sense = _resolve_sense(entry, url=url, get_model_name=get_model_name)
        if sense is None:
            # (Befund schwer 1, Durchsicht 46ef37b): entry.candidates enthielt echte
            # Wörterbuchkandidaten, das Modell wählte aber „keine passt" — siehe
            # _resolve_sense. Kein Profilabgleich, keine Buchung, nur gezählt.
            skipped += 1
            _report_progress()
            continue
        status = profile.compare_chapter_vocabulary(con, [sense])[sense]
        if status is VocabularyStatus.KNOWN:
            # (Befund mittel, Durchsicht 46ef37b): vorher ungezählt weggeworfen — die
            # Meldung „N bereits bekannt" verschwieg dadurch genau die Wörter, die erst
            # nach dem Auflösen als bekannt erkannt wurden (Auftragstext: 21 von 25).
            resolved_known += 1
            _report_progress()
            continue
        resolved.append(ResolvedEntry(occurrence=occurrence, sense=sense, status=status))
        _report_progress()

    # Auftragstext, Abschnitt 1: Die Anzeigereihenfolge bleibt Häufigkeit, unabhängig von
    # der Verarbeitungsreihenfolge aus Schritt 2 oben — sonst schlüge die Auswahlstrategie
    # in die Triage durch.
    display_order = triage.sort_by_frequency(entry.occurrence for entry in resolved)
    resolved_by_occurrence = {entry.occurrence: entry for entry in resolved}
    resolved_sorted = [resolved_by_occurrence[occurrence] for occurrence in display_order]

    return TriageResolution(
        entries=resolved_sorted,
        known=len(known_entries),
        resolved_known=resolved_known,
        skipped=skipped,
        deferred=len(ordered) - examined,
    )


# --------------------------------------- Vorbelegung des Profils (Bauschritt 3/5, 31.08.2026)

# (31.08.2026, Bauschritt 3/5 der Vorbelegung): Aus der Sprachlehrforschung geliehen und
# nicht in diesem Projekt gemessen — eine Faustregel für den rezeptiven Grundwortschatz je
# GER-Niveau, keine eigene Auszählung von LibreVerbum. „Keine Angabe" (kein Eintrag hier)
# bedeutet keine Vorbelegung; das entscheidet der Aufrufer von `write_vocabulary_preset`,
# nicht diese Tabelle.
_PRESET_WORD_COUNT: dict[CefrLevel, int] = {
    CefrLevel.A1: 500,
    CefrLevel.A2: 1000,
    CefrLevel.B1: 2000,
    CefrLevel.B2: 3500,
    CefrLevel.C1: 5000,
}

# Programmbestandteil im Paket, nicht Nutzerdaten — der Kern findet ihn relativ zu sich
# selbst (technik.md §9, „Die Regel gilt für Nutzerdaten, nicht für Programmbestandteile").
_WORDFREQ_PRESET_PATH = Path(__file__).parent / "wordfreq_en_5000.txt"


def _load_wordfreq_lemmas(count: int) -> list[str]:
    """Liest die ersten `count` Grundformen aus der eingefrorenen Grundwortschatzliste
    (`wordfreq_en_5000.txt`) — Kommentarkopf überspringen (jede mit „#" beginnende oder
    leere Zeile), Rangfolge beibehalten. Die Datei selbst versichert: Ein Präfix
    beliebiger Länge ist eine gültige Auswahl der `count` häufigsten Grundformen — welche
    Länge ein Niveau bekommt, entscheidet `_PRESET_WORD_COUNT`, nicht diese Funktion."""
    lemmas = []
    with _WORDFREQ_PRESET_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lemmas.append(stripped)
    return lemmas[:count]


def write_vocabulary_preset(
    *, dictionary_path: Path, profile_path: Path, cefr_level: CefrLevel | None, timestamp: datetime
) -> int:
    """Vorbelegung des Profils beim Anlegen (Bauschritt 3/5, 31.08.2026, konzept.md,
    „Bewusst offen", „Woher der Nutzer seinen Grundwortschatz bekommt"): trägt **alle**
    Wörterbuchbedeutungen der häufigsten Grundformen des gewählten Sprachniveaus als
    `KnowledgeState.KNOWN` mit `Origin.PRESET` ein, ohne Buch und Kapitel
    (`entities.Event`, „book und chapter_number sind None bei Origin.PRESET").

    `cefr_level is None` heißt „keine Angabe": Diese Funktion schreibt dann **nichts** —
    kein Ereignis, kein Aufruf von `profile.record_preset`, das Sprachniveau bleibt
    unverändert (nicht einmal auf `None` gesetzt: „keine Angabe" beim Anlegen ist kein
    Zurücksetzen eines vorhandenen Niveaus, das ist Sache einer anderen Bedienhandlung).
    Sonst werden `_PRESET_WORD_COUNT[cefr_level]` Grundformen aus `wordfreq_en_5000.txt`
    gelesen (`_load_wordfreq_lemmas`).

    Die Liste trägt keine Wortart — eine geratene, feste Wortart träfe entweder nur die
    neun Mehrworteinträge der Liste oder gar keine der übrigen (Auftragstext). Die
    Wortarten kommen deshalb aus dem Wörterbuch, mit derselben Vorrichtung wie
    `run_chapter`: Eine Grundform ohne Leerzeichen ist ein Einzelwort und läuft über
    `dictionary.pos_variant_lists` (die Umkehrung von `candidate_lists` — hier ist die
    Wortart nicht bekannt, sondern wird gesucht), für jede im Wörterbuch gefundene Wortart
    ein eigenes `(Lemma, Bedeutungen)`-Paar. Eine Grundform mit Leerzeichen ist ein
    Mehrwortausdruck und läuft über `dictionary.contiguous_candidates` mit `Lemma.pos =
    ""`, wie `extraction.extract_contiguous_candidates` es für einen echten Kapiteldurchlauf
    vergäbe (`tools/build_wordfreq_preset.py`: die neun „Schönheitsfehler" der Liste
    entstehen auf demselben Wendungsweg) — bewusst **nicht**
    `dictionary.particle_verb_candidates`, dessen `uncertain`-Platzhalter für eine
    Wortfolge ohne Eintrag hier nie entstehen darf (siehe unten).

    Beide Wege liefern für eine Grundform ohne Fund **keine** Bedeutung:
    `pos_variant_lists` eine leere Liste je Grundform ohne erkannte Wortart,
    `contiguous_candidates` eine leere Liste ohne bestandenen Filter — nie einen
    `uncertain`-Platzhalter. Was der Kern beim Nachschlagen nicht findet, wird nicht
    vorbelegt: Eine Grundform ohne Wörterbucheintrag hat keine Bedeutung, die man als
    bekannt buchen könnte, und ein `uncertain`-Eintrag darf nie als bekannt gebucht werden
    (Auftragstext).

    Schreibt über `profile.record_preset` in einer einzigen Transaktion (ganz oder gar
    nicht) und liefert die Zahl der gebuchten Ereignisse."""
    if cefr_level is None:
        return 0

    lemma_texts = _load_wordfreq_lemmas(_PRESET_WORD_COUNT[cefr_level])
    single_word_texts = [text for text in lemma_texts if " " not in text]
    expression_texts = [text for text in lemma_texts if " " in text]

    single_word_variants = dictionary.pos_variant_lists(dictionary_path, single_word_texts)
    expression_matches = dictionary.contiguous_candidates(
        dictionary_path, [Lemma(text=text, pos="") for text in expression_texts]
    )

    senses: list[Sense] = []
    for variants in single_word_variants:
        for _lemma, group in variants:
            senses.extend(group)
    for matches in expression_matches:
        senses.extend(matches)

    events = [
        Event(
            sense=sense,
            knowledge_state=KnowledgeState.KNOWN,
            origin=Origin.PRESET,
            timestamp=timestamp,
            book=None,
            chapter_number=None,
        )
        for sense in senses
    ]

    con = profile.open_profile(profile_path)
    try:
        profile.record_preset(con, events, cefr_level)
    finally:
        con.close()
    return len(events)
