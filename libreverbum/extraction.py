"""Wortschatzextraktion — Kapiteltext zu Grundformen.

Aufgabe
-------
Schritt 2 des Kernablaufs (konzept.md, „2. Wortschatz extrahieren", bauplan.md T3):
Tokenisierung, Wortart, Lemmatisierung, Eigennamenfilter je Vorkommen, Häufigkeit je
Kapitel, Belegsatz. Dazu bauplan.md T4: Kandidaten für Mehrwortausdrücke aus zwei
verschiedenen Wegen — Verb-Partikel-Paare aus der Abhängigkeitsanalyse und
zusammenhängende Wortfolgen aus einem n-Gramm-Abgleich (technik.md, „Arbeitsteilung nach
der Messung").

Voraussetzungen
---------------
Erwartet Fließtext ohne Inhaltsverzeichnis, Impressum und Fußnoten. Das trennt der
EPUB-Leser (`epub`), nicht dieses Modul. `nlp` ist ein bereits geladenes spaCy-Modell
(`load_nlp()`) mit geladenem Lemmatisierer — das Laden kostet rund eine Sekunde
(technik.md §5) und soll für mehrere Kapitel nur einmal anfallen, nicht je Aufruf. Fehlt
der Lemmatisierer, bricht jede der drei Funktionen dieses Moduls ab (Regel 13, Befund 1
Review T4) statt den `saw`-Fall still zu wiederholen.

Liefert
-------
Ein `Occurrence` je Kapitel und Grundform: Beugungsformen sind zusammengefasst
(Abnahmekriterium 2), Häufigkeit und Anteil Eigenname stehen dabei, dazu ein Belegsatz.
Im Wörterbuch wird hier **nicht** nachgeschlagen — das tut `dictionary`.

Daneben, für bauplan.md T4, zwei getrennte Funktionen statt einer gemeinsamen — sie
behaupten verschieden viel und liefern deshalb getrennte Rückgaben statt eines
gemeinsamen Kandidatentyps (Regel 14, Befund 2 Review T4):

- `extract_particle_verb_candidates`: ein `Occurrence` je Kapitel und Verb-Partikel-Paar
  (`give up`), aus spaCys Abhängigkeitsanalyse. Ein beobachtetes Phrasal Verb — bleibt
  nach Regel 10 auch ohne Wörterbucheintrag `uncertain`, statt zu verschwinden
- `extract_contiguous_candidates`: ein `Occurrence` je Kapitel und zusammenhängender
  Wortfolge aus dem n-Gramm-Abgleich. Bloß eine Hypothese — `of the` sieht genauso aus
  wie `give up`, bevor T7 den Filter `score ≥ 50` und Wortart nicht `Proper_noun`
  anwendet (technik.md, „Messung: Mehrwortausdrücke")

Beide liefern nur Kandidaten und schlagen selbst nicht nach — der Wörterbuchabgleich
samt `uncertain`-Markierung ist T7 (Regel 14). T7 unterscheidet die zwei Arten daran,
welche der beiden Funktionen sie geliefert hat, nicht an einem Feld auf `Occurrence`.

Regeln
------
Reihenfolge Wortart → Grundform → Nachschlagen ist verbindlich (technik.md, „Warum die
Reihenfolge zwingend ist", Regel 2). spaCy bestimmt Wortart und Grundform in einem
Schritt (`token.pos_`, `token.lemma_`, in dieser Abhängigkeit), bevor irgendwo
nachgeschlagen wird — dieses Modul schlägt selbst gar nicht nach.

Nur Inhaltswörter werden zu Kandidaten (erlaubte Liste `_CONTENT_POS`, Review Runde 2) —
`PROPN` bleibt als Sonderfall trotzdem eingeschlossen, weil der Eigennamenfilter (Regel
12, technik.md §5, „Neuer Befund: der Eigennamenfilter muss pro Vorkommen greifen") erst
je Vorkommen weiter unten wirkt, nicht schon beim Einsammeln. Begründung der erlaubten
Liste bei `_CONTENT_POS`, der PROPN-Sonderfall bei `_PROPER_NOUN_POS`. Der Filter gilt nur
für `extract_vocabulary` — die beiden Mehrwortfunktionen brauchen gerade die Wortarten,
die er ausschließt (ADP, PART, DET), siehe deren Docstrings.

Mischt eine Grundform mehrere Wortarten unter ihren nicht-eigennamigen Vorkommen (etwa
„watch" als Nomen und als Verb), gewinnt die häufigere; bei Gleichstand die zuerst
gesehene. Wortform und Belegsatz stammen vom ersten Vorkommen dieser gewählten Wortart —
sonst schlägt `dictionary` eine andere Wortart nach, als der Belegsatz zeigt, aus dem
später das Modell wählt. Das vereinfacht eine im Kapitel seltene Mehrdeutigkeit zugunsten
einer einzigen Grundform je Wortliste — bauplan.md T3 verlangt keine feinere Auflösung,
und Regel 14 untersagt eine Erweiterung auf Vorrat.
"""

from __future__ import annotations

import collections
import re
from typing import TYPE_CHECKING, NamedTuple

from libreverbum.entities import Chapter, Lemma, Occurrence

if TYPE_CHECKING:
    from collections.abc import Iterator

    from spacy.language import Language
    from spacy.tokens import Span, Token

# REGEL (technik.md §5, offener Punkt „could, would, having"): AUX fehlt bewusst in
# dieser erlaubten Liste. spaCy markiert sowohl Modalverben als auch Hilfsverb-Gerundien
# (`having` in „Having finished the letter …") als AUX — beide sind Funktionswörter, die
# nie Lernvokabeln werden. Dasselbe Wort in Hauptverbstellung („having a hard time")
# trägt VERB und bleibt deshalb erhalten.
#
# Nur Inhaltswörter kommen in die Wortliste (Review Runde 2, erlaubte statt Sperrliste):
# Ohne diesen Filter führten Funktionswörter wie `the`, `his`, `by` mit hoher Häufigkeit
# die nach Häufigkeit sortierte Triage aus T10 an. PROPN steht absichtlich nicht in
# dieser Liste, wird aber weiterhin eingesammelt — siehe `_PROPER_NOUN_POS`.
_CONTENT_POS = frozenset({"NOUN", "VERB", "ADJ", "ADV", "INTJ"})

# REGEL (technik.md §5, „Neuer Befund: der Eigennamenfilter muss pro Vorkommen
# greifen", Regel 12): Ein einzelnes Vorkommen als PROPN gilt als Eigenname, die
# Grundform nie — sonst verschwänden „red", „orange" und „street" ganz aus der Triage,
# obwohl sie auch als gewöhnliches Wort vorkommen. Deshalb die einzige Ausnahme von
# `_CONTENT_POS` beim Einsammeln: PROPN-Vorkommen werden mitgenommen und erst weiter
# unten je Vorkommen bewertet, nicht schon hier verworfen.
_PROPER_NOUN_POS = "PROPN"

# REGEL (bauplan.md T4, technik.md „Messung: Mehrwortausdrücke", „Grenze: rund ein
# Fünftel der Phrasal Verbs steht getrennt"): spaCy zeichnet die Partikel eines Phrasal
# Verbs eigens als `prt` aus — unabhängig davon, ob sie direkt hinter dem Verb steht
# („gave up the idea") oder durch andere Wörter getrennt ist („gave the idea up").
# `prep` (eine gewöhnliche Präposition wie in „walked to the store", „ran into a
# friend") ist ausdrücklich nicht mit gemeint: Geprüft an `en_core_web_md` markiert es
# echte Präpositionalobjekte, keine Phrasal-Verb-Partikel, und ist auch in der Messung
# in technik.md nicht enthalten (dort nur `prt` bzw. Stanzas `compound:prt`). Wer `prep`
# mit aufnähme, erzeugte Kandidaten für praktisch jedes Verb mit Präpositionalphrase.
_PARTICLE_DEP = "prt"

# REGEL (bauplan.md T4, technik.md „Messung: Mehrwortausdrücke", „Arbeitsteilung nach der
# Messung"; Befund 2, Review T4): Obergrenze des n-Gramm-Wegs — gemessen gegen
# tools/en-de.sqlite3, nicht geraten (dokumentation.md §5, „Woran geprüft wird"). Gezählt
# am 17.08.2026: 22.840 mehrwortige `written_rep` mit `score ≥ 50`, davon 99,12 % höchstens
# sechs Wörter lang (18.196 mit zwei, 2.977 mit drei, 1.011 mit vier, 289 mit fünf, 167 mit
# sechs Wörtern). Länger wird fast nur noch die Wortart `Proverb` — vollständige
# Sprichwörter bis 26 Wörter („it is easier for a camel to go through the eye of a
# needle …"), die als wörtliches Zitat im Fließtext praktisch nie vorkommen. Sie
# mitzunehmen vervielfachte die Kandidatenzahl je Satz (siehe Bericht), ohne dass ein
# Treffer wahrscheinlicher würde — Regel 14 lässt das nicht zu.
_MAX_EXPRESSION_LENGTH = 6

# Ein n-Gramm-Kandidat ist eine beliebige Wortfolge ohne syntaktischen Kopf — anders als
# beim Verb-Partikel-Paar gibt es keine einzelne Wortart im Sinn von `token.pos_`.
# WikDicts eigene Wortart (`Phrase`, `Prepositional_phrase`, `Verb`, …) kommt erst mit dem
# Nachschlagen in T7 dazu; bis dahin bleibt `Lemma.pos` leer statt eines geratenen Werts.
_NO_SINGLE_POS = ""

_WHITESPACE = re.compile(r"\s+")


def load_nlp() -> Language:
    """Lädt das für Entscheidung 5 festgelegte Modell (technik.md §5, `en_core_web_md`)."""
    import spacy

    return spacy.load("en_core_web_md")


def _require_lemmatizer(nlp: Language) -> None:
    """Bricht ab, wenn `nlp` ohne Lemmatisierer geladen ist (Regel 2, Regel 13; Befund 1,
    Review T4). Ohne ihn liefert `token.lemma_` eine leere Zeichenkette — eine Grundform
    aus lauter Leerzeichen statt einer Fehlermeldung, und der `saw`-Fall wiederholte sich
    lautlos in allen drei Funktionen dieses Moduls. Wird einmal je Aufruf geprüft, nicht
    je Token."""
    if "lemmatizer" not in nlp.pipe_names:
        raise ValueError(
            "spaCy-Modell ohne Lemmatisierer geladen — Wortschatzextraktion abgebrochen, "
            "statt Wortformen still als Grundform zu verwenden."
        )


def _collapse_whitespace(text: str) -> str:
    """Zieht mehrfachen Leerraum zu einem Leerzeichen zusammen (Befund 3, Review T4):
    `Span.text` gibt den Quelltext zwischen zwei Token unverändert wieder, und der kann
    einen Zeilenumbruch aus dem Buchsatz enthalten (`'throwing himself\\ndown'`). Ohne
    diesen Schritt stünde das rohe `\\n` später unverändert auf der Karte (T13)."""
    return _WHITESPACE.sub(" ", text).strip()


class _CandidateOccurrence(NamedTuple):
    """Ein einzelnes Token-Vorkommen, vor der Zusammenführung zur Grundform."""

    pos: str
    word_form: str
    example_sentence: str


def extract_vocabulary(chapter: Chapter, nlp: Language) -> list[Occurrence]:
    """Extrahiert die Grundformen eines Kapitels (bauplan.md T3).

    Reihenfolge je Token: Wortart und Grundform kommen beide von spaCy, bevor dieses
    Modul irgendeine Entscheidung trifft — Nachschlagen findet an keiner Stelle statt
    (Regel 2). Die Rückgabe ist in der Reihenfolge des ersten Vorkommens im Kapitel,
    unsortiert: Häufigkeitssortierung ist Aufgabe von `triage`, nicht von diesem Modul.
    """
    _require_lemmatizer(nlp)

    doc = nlp(chapter.text)

    candidates_by_lemma: dict[str, list[_CandidateOccurrence]] = collections.defaultdict(list)
    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        for token in sentence:
            pos = token.pos_
            if not token.is_alpha:
                continue
            if pos not in _CONTENT_POS and pos != _PROPER_NOUN_POS:
                continue
            lemma_text = token.lemma_.lower()
            candidates_by_lemma[lemma_text].append(
                _CandidateOccurrence(pos=pos, word_form=token.text, example_sentence=sentence_text)
            )

    occurrences: list[Occurrence] = []
    for lemma_text, candidates in candidates_by_lemma.items():
        non_proper = [c for c in candidates if c.pos != _PROPER_NOUN_POS]
        if not non_proper:
            # Ausschließlich eigennamige Vorkommen: kein Vorkommen dieser Grundform war
            # ein gewöhnliches Wort, sie ist damit reiner Name und keine Lernvokabel
            # (siehe Moduldocstring, Abschnitt „Regeln").
            continue

        pos_counts: collections.Counter[str] = collections.Counter()
        first_seen_at: dict[str, int] = {}
        for index, candidate in enumerate(non_proper):
            pos_counts[candidate.pos] += 1
            first_seen_at.setdefault(candidate.pos, index)
        chosen_pos = min(pos_counts, key=lambda pos: (-pos_counts[pos], first_seen_at[pos]))

        # REGEL (dokumentation.md §4 Regel 2, „Warum die Reihenfolge zwingend ist"):
        # Wortform und Belegsatz müssen zur gewählten Wortart passen, sonst schlägt
        # dictionary eine andere Wortart nach, als der Belegsatz zeigt (etwa Verb
        # nachgeschlagen, aber ein Nomen-Belegsatz vorgelegt).
        representative = next(c for c in non_proper if c.pos == chosen_pos)
        occurrences.append(
            Occurrence(
                book=chapter.book,
                chapter_number=chapter.number,
                lemma=Lemma(text=lemma_text, pos=chosen_pos),
                word_form=representative.word_form,
                example_sentence=representative.example_sentence,
                frequency=len(candidates),
                proper_noun_frequency=len(candidates) - len(non_proper),
            )
        )

    return occurrences


def extract_particle_verb_candidates(chapter: Chapter, nlp: Language) -> list[Occurrence]:
    """Extrahiert Kandidaten für Verb-Partikel-Paare eines Kapitels (bauplan.md T4).

    Zusammenhängende Folgen („gave up the idea") und getrennte Paare („gave the idea
    up") kommen aus derselben Quelle: spaCys Abhängigkeitsanalyse (`token.dep_ ==
    "prt"`, siehe `_PARTICLE_DEP`) am geparsten Dokument selbst — nicht am Ergebnis von
    `extract_vocabulary`. Dessen Inhaltswortfilter (`_CONTENT_POS`) lässt ADP und PART
    weg, und genau diese Wortarten trägt die Partikel eines Phrasal Verbs; wer auf der
    gefilterten Liste aufbaut, findet den getrennten Fall nie — lautlos, weil dann
    einfach kein Kandidat entsteht (bauplan.md T4, Prüfung: „gave the idea up" wird
    gefunden). Das gilt nur für diesen Weg — `extract_contiguous_candidates` daneben
    nimmt beliebige Wortfolgen aus einem n-Gramm-Abgleich, nicht aus der
    Abhängigkeitsanalyse (Befund 2, Review T4).

    Der Kopf der Partikel muss ein Verb sein (`verb.pos_ == "VERB"`): spaCy zeichnet
    `prt` auch an substantivierten Fällen aus — „the washing up took forever" bekommt
    dieselbe Abhängigkeit, obwohl `washing` hier NOUN ist, kein Phrasal Verb. Ohne diese
    Prüfung entstünden Scheinkandidaten aus Nominalphrasen.

    Liefert nur Kandidaten und schlägt selbst nicht im Wörterbuch nach — das ist T7
    (Regel 14). Die Grundform trägt Leerzeichen (`give up`) und taugt so unmittelbar
    zum Nachschlagen gegen WikDicts `written_rep`.

    Offener Punkt (Befund 3, Review T4, für T13): Bei einem langen Einschub
    („chat this little matter over") umfasst `word_form` den ganzen Bereich zwischen
    Verb und Partikel, nicht nur die beiden Wörter selbst — auf der Karte stünde dann ein
    ganzer Satzteil als „Beugungsform". Das ist hier bewusst nicht entschieden: Ob T13
    den vollen Bereich oder nur Verb und Partikel braucht, hängt vom Kartenlayout ab, das
    diese Teilaufgabe nicht kennt.
    """
    _require_lemmatizer(nlp)

    doc = nlp(chapter.text)

    candidates_by_lemma: dict[str, list[_CandidateOccurrence]] = collections.defaultdict(list)
    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        for token in sentence:
            if token.dep_ != _PARTICLE_DEP:
                continue
            verb = token.head
            if verb.pos_ != "VERB":
                continue
            lemma_text = f"{verb.lemma_.lower()} {token.lemma_.lower()}"
            start, end = min(verb.i, token.i), max(verb.i, token.i)
            word_form = _collapse_whitespace(doc[start : end + 1].text)
            candidates_by_lemma[lemma_text].append(
                _CandidateOccurrence(
                    pos="VERB", word_form=word_form, example_sentence=sentence_text
                )
            )

    return _occurrences_from_candidates(chapter, candidates_by_lemma, pos="VERB")


def extract_contiguous_candidates(chapter: Chapter, nlp: Language) -> list[Occurrence]:
    """Extrahiert Kandidaten für zusammenhängende Mehrwortausdrücke eines Kapitels
    (bauplan.md T4, technik.md „Arbeitsteilung nach der Messung": „zusammenhängende
    Wendungen finden" ist Sache von „Wörterbuch + n-Gramm + Filter" — dieser Schritt
    liefert den n-Gramm-Teil, Wörterbuchabgleich und Filter (`score ≥ 50`, nicht
    `Proper_noun`, technik.md „Messung: Mehrwortausdrücke") folgen erst in T7 (Regel 14).

    Jede Wortfolge von zwei bis `_MAX_EXPRESSION_LENGTH` Wörtern innerhalb eines
    zusammenhängenden Abschnitts wird ein Kandidat — ohne Rücksicht auf Wortart, weil
    WikDicts Mehrwortausdrücke selbst über viele Wortarten verteilt sind (`Phrase`,
    `Prepositional_phrase`, `Proverb`, dazu gewöhnliche Nomen und Verben) und der
    `_CONTENT_POS`-Filter aus `extract_vocabulary` genau die Funktionswörter ausschlösse,
    aus denen viele dieser Wendungen bestehen (`out of the way`, `as a rule`, `at all`).
    Ein Abschnitt endet an jeder Satzgrenze (`doc.sents`) und an jedem
    Interpunktionszeichen (`token.is_alpha`, siehe `_alpha_runs`) — Kandidaten laufen
    also nicht über Kommata, Anführungszeichen oder Gedankenstriche hinweg (Befund 2,
    Review T4).

    Normalisiert wird auf die Grundform je Wort (`token.lemma_.lower()`), nicht die
    Oberflächenform: WikDicts `written_rep` führt Wendungen selbst in der Grundform
    (`give up`, nicht `gave up` — technik.md, „Warum die Reihenfolge zwingend ist").
    Gegen `tools/en-de.sqlite3` geprüft (Review T4), treffen `give up`, `put up with`,
    `out of the way`, `at all`, `all right`, `after all` und `as a rule` alle genau so auf
    `written_rep`. Nebeneffekt: Ein Dreiwortverb wie `put up with` (score 101,7) entsteht
    hier als eigener 3-Gramm-Kandidat, ohne dass er wie am `prt`-Weg auf `put up` verkürzt
    würde (Befund 6, Review T4).

    Liefert nur Kandidaten und schlägt selbst nicht im Wörterbuch nach — das ist T7
    (Regel 14). `Lemma.pos` bleibt leer (`_NO_SINGLE_POS`): Anders als beim
    Verb-Partikel-Paar gibt es für eine beliebige Wortfolge keine einzelne Wortart im
    Sinn von `token.pos_`; WikDicts eigene Wortart kommt erst mit dem Nachschlagen in T7.
    """
    _require_lemmatizer(nlp)

    doc = nlp(chapter.text)

    candidates_by_lemma: dict[str, list[_CandidateOccurrence]] = collections.defaultdict(list)
    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        for run in _alpha_runs(sentence):
            run_length = len(run)
            for start in range(run_length):
                max_n = min(_MAX_EXPRESSION_LENGTH, run_length - start)
                for n in range(2, max_n + 1):
                    span = run[start : start + n]
                    lemma_text = " ".join(token.lemma_.lower() for token in span)
                    word_form = _collapse_whitespace(doc[span[0].i : span[-1].i + 1].text)
                    candidates_by_lemma[lemma_text].append(
                        _CandidateOccurrence(
                            pos=_NO_SINGLE_POS, word_form=word_form, example_sentence=sentence_text
                        )
                    )

    return _occurrences_from_candidates(chapter, candidates_by_lemma, pos=_NO_SINGLE_POS)


def _alpha_runs(sentence: Span) -> Iterator[list[Token]]:
    """Zerlegt einen Satz in maximale Abschnitte aus alphabetischen Token — Satzzeichen,
    Anführungszeichen und Ziffern brechen einen Abschnitt (Befund 2, Review T4: Kandidaten
    laufen nicht über Satz- und Interpunktionsgrenzen). Dieselbe Grenze wie beim
    Inhaltswortfilter (`token.is_alpha`), aber ohne dessen Wortartfilter — hier zählt
    jedes Wort, nicht nur Inhaltswörter."""
    run: list[Token] = []
    for token in sentence:
        if token.is_alpha:
            run.append(token)
        else:
            if run:
                yield run
            run = []
    if run:
        yield run


def _occurrences_from_candidates(
    chapter: Chapter, candidates_by_lemma: dict[str, list[_CandidateOccurrence]], *, pos: str
) -> list[Occurrence]:
    """Baut `Occurrence`-Einträge aus gesammelten Mehrwort-Kandidaten: Häufigkeit ist die
    Anzahl der Vorkommen, Wortform und Belegsatz stammen vom **ersten** Vorkommen (Befund
    4, Review T4) — sonst zeigte der Belegsatz nicht das erste Auftreten im Kapitel, wie
    es der Docstring von `extract_vocabulary` für die einfachen Grundformen ebenfalls
    verlangt. Gemeinsam für `extract_particle_verb_candidates` und
    `extract_contiguous_candidates`, die sich nur in der Sammlung der Kandidaten
    unterscheiden, nicht in deren Zusammenführung."""
    occurrences: list[Occurrence] = []
    for lemma_text, candidates in candidates_by_lemma.items():
        representative = candidates[0]
        occurrences.append(
            Occurrence(
                book=chapter.book,
                chapter_number=chapter.number,
                lemma=Lemma(text=lemma_text, pos=pos),
                word_form=representative.word_form,
                example_sentence=representative.example_sentence,
                frequency=len(candidates),
                proper_noun_frequency=0,
            )
        )
    return occurrences
