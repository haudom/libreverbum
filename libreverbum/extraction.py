"""Wortschatzextraktion — Kapiteltext zu Grundformen.

Aufgabe
-------
Schritt 2 des Kernablaufs (konzept.md, „2. Wortschatz extrahieren", bauplan.md T3):
Tokenisierung, Wortart, Lemmatisierung, Eigennamenfilter je Vorkommen, Häufigkeit je
Kapitel, Belegsatz.

Voraussetzungen
---------------
Erwartet Fließtext ohne Inhaltsverzeichnis, Impressum und Fußnoten. Das trennt der
EPUB-Leser (`epub`), nicht dieses Modul. `nlp` ist ein bereits geladenes spaCy-Modell
(`load_nlp()`) mit geladenem Lemmatisierer — das Laden kostet rund eine Sekunde
(technik.md §5) und soll für mehrere Kapitel nur einmal anfallen, nicht je Aufruf. Fehlt
der Lemmatisierer, bricht die Extraktion ab (Regel 13) statt den `saw`-Fall still zu
wiederholen.

Liefert
-------
Ein `Occurrence` je Kapitel und Grundform: Beugungsformen sind zusammengefasst
(Abnahmekriterium 2), Häufigkeit und Anteil Eigenname stehen dabei, dazu ein Belegsatz.
Im Wörterbuch wird hier **nicht** nachgeschlagen — das tut `dictionary`.
Mehrwortausdrücke liefert dieses Modul ebenfalls nicht — das ist T4.

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
Liste bei `_CONTENT_POS`, der PROPN-Sonderfall bei `_PROPER_NOUN_POS`.

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
from typing import TYPE_CHECKING, NamedTuple

from libreverbum.entities import Chapter, Lemma, Occurrence

if TYPE_CHECKING:
    from spacy.language import Language

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


def load_nlp() -> Language:
    """Lädt das für Entscheidung 5 festgelegte Modell (technik.md §5, `en_core_web_md`)."""
    import spacy

    return spacy.load("en_core_web_md")


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
    # REGEL (technik.md, „Warum die Reihenfolge zwingend ist", Regel 2): Ohne
    # Lemmatisierer liefert token.lemma_ eine leere Zeichenkette, und ein Rückfall auf
    # token.text ergäbe „saw" statt „see" — der saw-Fall scheiterte dann leise. Die
    # Vorbedingung wird einmal je Aufruf geprüft, nicht je Token.
    if "lemmatizer" not in nlp.pipe_names:
        raise ValueError(
            "spaCy-Modell ohne Lemmatisierer geladen — Wortschatzextraktion abgebrochen, "
            "statt Wortformen still als Grundform zu verwenden."
        )

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
