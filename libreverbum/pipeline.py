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

**`run_chapter` bleibt der netzlose Teil.** Sie schlägt im Wörterbuch nach und gleicht
gegen das Profil ab (rund 1,1 s, technik.md §3, „Nachtrag 17.08.2026") — die Liste der
möglichen Bedeutungen je Vorkommen, ohne dass dafür ein Modellserver erreichbar sein
müsste. Was daraus für die Triage wird, macht seit der zweiten T16-Durchsicht (Befund
schwer 1) eine zweite Funktion, `resolve_triage_entries`: Sie ruft `translation.
choose_sense` auf — den einzigen Ort mit Modellzugriff (technik.md §7) — und ist deshalb
bewusst **nicht** Teil von `run_chapter`. Zwei Gründe:

1. `run_chapter`s Kosten (rund 1,1 s) bleiben unverändert und ohne Netzabhängigkeit, statt
   für jeden Aufrufer verbindlich rund 25 bis 40 Modellanfragen mitzubringen. Ein künftiger
   Aufrufer, der nur die Auswahllisten braucht (etwa ein Messwerkzeug), bekommt sie weiterhin
   ohne Modellserver
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
from typing import TYPE_CHECKING

from libreverbum import dictionary, epub, extraction, profile, translation, triage
from libreverbum.entities import Chapter, Occurrence, Sense
from libreverbum.profile import VocabularyStatus

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable, Sequence
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


def resolve_triage_entries(
    *,
    con: sqlite3.Connection,
    entries: Sequence[VocabularyEntry],
    limit: int,
    url: str,
    get_model_name: Callable[[], str],
) -> TriageResolution:
    """Bereitet einen Decksel aus `ChapterVocabulary` (`entries` oder `expressions`) für
    die interaktive Triage vor (Befund schwer 1, zweite T16-Durchsicht) — Vorfilter,
    Häufigkeitssortierung, Bedeutungsauflösung durch das Modell, Wortobergrenze, in dieser
    Reihenfolge, damit das Budget aus konzept.md §4 („eine halbe Minute" bei höchstens 25
    neuen Wörtern) hält, statt für alle rund 1.000 Grundformen eines Kapitels zu fragen —
    das wären bei rund 1 s je Wort (technik.md §3) rund 17 Minuten, bevor der Nutzer
    überhaupt etwas sieht:

    1. **Vorfilter, kostenlos:** Ein Eintrag, dessen sämtliche Kandidaten bereits `KNOWN`
       sind, fällt ohne Modellaufruf weg (`_all_candidates_known`), gezählt in
       `TriageResolution.known`.
    2. Der Rest wird nach Häufigkeit sortiert (`triage.sort_by_frequency`) — häufigste
       zuerst, wie in der Triage selbst (konzept.md §4).
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
    5. Abbruch, sobald auf diese Art `limit` Einträge **behalten** wurden — typisch 25 bis
       40 Modellaufrufe (`TriageResolution.entries` plus die dabei verworfenen `KNOWN`-
       Treffer aus Schritt 4 und die übersprungenen aus Schritt 3), nicht mehrere Hundert.
    6. Was danach in der sortierten Liste noch steht, wird nicht mehr angerührt: kein
       Modellaufruf, keine Anzeige, kein Ereignis — dieselbe Wirkung wie die bisherige
       Wortobergrenze, nur an behaltenen statt an gesehenen Einträgen gezählt
       (`TriageResolution.deferred`).

    `known + resolved_known + skipped + deferred + len(resolution.entries)` ergibt wieder
    `len(entries)` — die Zahl der hier übergebenen Einträge, unabhängig davon, wie sie sich
    auf die vier Zählungen und die behaltene Liste verteilen. Die Zusicherung dazu steht in
    `tests/test_pipeline.py` (Auftrag zu Befund mittel, Durchsicht 46ef37b).

    Ein reiner Lese- und Netzzugriff auf `con`: Es wird kein Ereignis geschrieben, nur
    `profile.compare_chapter_vocabulary` befragt — das Schreiben bleibt Sache der
    interaktiven Triage (`cli.interaction.run_triage_pass`), die über jede getroffene
    Entscheidung entscheidet, nicht über die hier schon aufgelöste Bedeutung."""
    known_entries = [entry for entry in entries if _all_candidates_known(entry)]
    remaining = [entry for entry in entries if not _all_candidates_known(entry)]
    ordered = triage.sort_by_frequency(entry.occurrence for entry in remaining)
    entries_by_occurrence = {entry.occurrence: entry for entry in remaining}

    resolved: list[ResolvedEntry] = []
    resolved_known = 0
    skipped = 0
    examined = 0
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
            continue
        status = profile.compare_chapter_vocabulary(con, [sense])[sense]
        if status is VocabularyStatus.KNOWN:
            # (Befund mittel, Durchsicht 46ef37b): vorher ungezählt weggeworfen — die
            # Meldung „N bereits bekannt" verschwieg dadurch genau die Wörter, die erst
            # nach dem Auflösen als bekannt erkannt wurden (Auftragstext: 21 von 25).
            resolved_known += 1
            continue
        resolved.append(ResolvedEntry(occurrence=occurrence, sense=sense, status=status))

    return TriageResolution(
        entries=resolved,
        known=len(known_entries),
        resolved_known=resolved_known,
        skipped=skipped,
        deferred=len(ordered) - examined,
    )
