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
`extract_vocabulary` liefert `VocabularyExtraction`: ein `Occurrence` je Kapitel und
Grundform — Beugungsformen sind zusammengefasst (Abnahmekriterium 2), Häufigkeit und
Anteil Eigenname stehen dabei, dazu ein Belegsatz —, daneben `token_count` (jedes
alphabetische Token des Kapitels, bauplan-phase2.md AP 6, Nenner für `pipeline.coverage`).
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

Dazu, seit bauplan-phase2.md AP 8, `extract_proper_noun_list`: ein `ProperNounEntry` je
Kapitel und Oberflächenform für die Liste „Figuren & Orte" (konzept.md §6, „Export"),
über spaCys eigene Entitätserkennung (`doc.ents`), nicht über den Wortart-/Grundform-Weg
der Funktionen oben — eine Entität wie „Sherlock Holmes" ist keine Grundform, und die
Liste braucht ausdrücklich die Oberflächenform, nie die lemmatisierte (technik.md §5,
offener Punkt „Über-Lemmatisierung von Eigennamen"). Das Zusammenstellen des gedruckten
Anhangs selbst liegt bei `printout`, nicht hier (technik.md §7, „Die Liste »Figuren &
Orte« ist Phase 2").

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
gesehene. Wortform und Belegsatz stammen vom ersten **wendungsfreien** Vorkommen dieser
gewählten Wortart — oder, wenn keines wendungsfrei ist, vom ersten überhaupt (siehe REGEL
bei `_EXPRESSION_PARTICLE_WORDS`, T17-Nachbesserung 26.08.2026): sonst schlägt `dictionary`
eine andere Wortart nach, als der Belegsatz zeigt, aus dem später das Modell wählt — und
zeigt der Belegsatz eine Wendung statt der gewöhnlichen Verwendung, kann das Modell selbst
bei richtiger Wortart nicht mehr richtig wählen. Das vereinfacht eine im Kapitel seltene
Mehrdeutigkeit zugunsten einer einzigen Grundform je Wortliste — bauplan.md T3 verlangt
keine feinere Auflösung, und Regel 14 untersagt eine Erweiterung auf Vorrat.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

from libreverbum.entities import Chapter, Lemma, Occurrence, ProperNounEntry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

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

# REGEL (technik.md §5, „Eigennamen"; T17-Nachbesserung, schwer 1, zweiter Anlauf,
# 26.08.2026): Der Schwellwert selbst ist unverändert (0,90, siehe unten) — verändert hat
# sich, **worauf** er angewendet wird. Der erste Anlauf (25.08.2026) wandte ihn je Kapitel
# an und ließ damit „Sibyl" in tools/dorian_gray.epub Kapitel 10 durch: spaCy vertaggt dort
# drei elliptische Ausrufe („Sibyl dead!", „Did Sibyl—?", „Sibyl!") als NOUN statt PROPN —
# Tagger-Fehler in Ein-Wort-Ausrufen, kein Sprachbefund —, der Anteil sinkt dadurch auf
# 13/16 = 0,81 und bleibt unter der Schwelle, obwohl dieselbe Grundform buchweit fast
# durchgängig ein Eigenname ist (80/85 = 0,94, `book_proper_noun_ratios`). Angewendet wird
# der Schwellwert seither auf den **buchweiten** Anteil (über alle Kapitel des Buchs), nicht
# den Anteil des einzelnen Kapitels — drei fehlgetaggte Vorkommen in einem Kapitel fallen
# dann nicht mehr ins Gewicht. Siehe `book_proper_noun_ratios` und die Anwendung in
# `extract_vocabulary`.
_PROPER_NOUN_RATIO_THRESHOLD = 0.90

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

# REGEL (bauplan-phase2.md AP 8: „PERSON, GPE, LOC, FAC — Vermutung, am Bestand zu
# prüfen"): Geprüft an tools/sherlock.epub Kapitel 2 und tools/dorian_gray.epub Kapitel 1
# (siehe Bericht zu diesem Arbeitspaket). PERSON und GPE tragen die drei geforderten
# Fundstellen „Holmes"/„Sherlock Holmes", „Irene Adler" und „Bohemia"; LOC und FAC liefern
# an Sherlock Kapitel 2 zusätzliche, offensichtlich sinnvolle Fundstellen („Baker Street"
# FAC, „Europe" LOC), auch wenn an Dorian Gray Kapitel 1 keiner von beiden einen einzigen
# Treffer beisteuert — an einem einzelnen, entitätsarmen Kapitel zu verwerfen wäre
# verfrüht. spaCys NER tastet dabei auch daneben (an Sherlock Kapitel 2 etwa „landau",
# „chin", „sally", „marm", „Pshaw" fälschlich als PERSON, „Bohemia" selbst überwiegend als
# PERSON statt GPE) — kein Befund gegen diese vier Typen, sondern die bekannte
# Fehlerquote der Entitätserkennung selbst; eine Bereinigung auf Vorrat verbietet Regel 14.
_PROPER_NOUN_ENTITY_TYPES = frozenset({"PERSON", "GPE", "LOC", "FAC"})


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


def _require_ner(nlp: Language) -> None:
    """Bricht ab, wenn `nlp` ohne Entitätserkennung geladen ist (Regel 13, analog
    `_require_lemmatizer`): Ohne `ner` liefert `doc.ents` stillschweigend eine leere
    Sequenz — eine Liste „Figuren & Orte" aus lauter Nullfunden sähe dann wie ein
    Kapitel ganz ohne Eigennamen aus, statt einen falsch geladenen `nlp` zu melden."""
    if "ner" not in nlp.pipe_names:
        raise ValueError(
            "spaCy-Modell ohne Entitätserkennung (ner) geladen — Liste »Figuren & Orte« "
            "abgebrochen, statt eine leere Liste als vollständiges Ergebnis auszugeben."
        )


def _collapse_whitespace(text: str) -> str:
    """Zieht mehrfachen Leerraum zu einem Leerzeichen zusammen (Befund 3, Review T4):
    `Span.text` gibt den Quelltext zwischen zwei Token unverändert wieder, und der kann
    einen Zeilenumbruch aus dem Buchsatz enthalten (`'throwing himself\\ndown'`). Ohne
    diesen Schritt stünde das rohe `\\n` später unverändert auf der Karte (T13)."""
    return _WHITESPACE.sub(" ", text).strip()


def book_proper_noun_ratios(
    chapters: Sequence[Chapter],
    nlp: Language,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, float]:
    """Anteil eigennamiger Belege am Gesamtvorkommen je Grundform, gezählt über **alle**
    übergebenen Kapitel hinweg (T17-Nachbesserung, schwer 1, zweiter Anlauf, 26.08.2026 —
    siehe die REGEL bei `_PROPER_NOUN_RATIO_THRESHOLD`). `chapters` ist üblicherweise das
    ganze Buch; diese Funktion trifft dazu keine Annahme und liest selbst kein EPUB — das
    Zusammenstellen der Kapitelliste bleibt Sache des Aufrufers (`pipeline.run_chapter`),
    genau wie es die Importregel aus technik.md §7 verlangt (`extraction` kennt nur
    `entities`, nicht `epub`).

    Dasselbe Universum an Vorkommen wie beim Einsammeln in `extract_vocabulary`
    (`_CONTENT_POS` ∪ `_PROPER_NOUN_POS`, `token.is_alpha`) — sonst zählte die buchweite
    Statistik andere Vorkommen als die Stelle, die sie anwendet.

    Liefert nur Grundformen mit mindestens einem Vorkommen im übergebenen Ausschnitt; eine
    Grundform ganz ohne Eigennamen-Vorkommen bliebe ohnehin unter jedem sinnvollen
    Schwellwert, eine eigene Nullzeile dafür lohnt sich nicht.

    Kosten: ein voller spaCy-Lauf je Kapitel (technik.md §5, rund eine Sekunde) — bei einem
    ganzen Buch also im Bereich von dessen Kapitelzahl in Sekunden, einmal je Aufruf von
    `pipeline.run_chapter`. Gemessen an `tools/dorian_gray.epub` (22 Kapitel) und
    `tools/sherlock.epub` (13 Kapitel mit Fließtext): rund 22 s beziehungsweise 29 s. Das
    ist der Preis der buchweiten Betrachtung — mit ihm entfällt der stille Fehlschlag aus
    dem ersten Anlauf, ohne ihn ließe sich der `Sibyl`-Fall aus Kapitel 10 nicht auflösen
    (siehe Bericht zur Abnahme).

    `on_progress`, falls übergeben, wird nach **jedem** verarbeiteten Kapitel mit (fertig,
    gesamt) aufgerufen — Vorgabe `None` heißt keine Meldung, unverändertes Verhalten. Genau
    dieser stumme Abschnitt war bislang der stille Fehlschlag aus Regel 13: Die
    Kommandozeile zeigte noch „Lade Sprachmodell …", während hier tatsächlich 22 bis 29 s
    ohne jede Rückmeldung vergingen (technik.md §13). Der Kern gibt selbst nichts aus
    (technik.md §7) — die Textzuordnung bleibt Sache des Aufrufers."""
    _require_lemmatizer(nlp)

    counts: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    total_chapters = len(chapters)
    for done, chapter in enumerate(chapters, start=1):
        doc = nlp(chapter.text)
        for token in doc:
            if not token.is_alpha:
                continue
            pos = token.pos_
            if pos not in _CONTENT_POS and pos != _PROPER_NOUN_POS:
                continue
            entry = counts[token.lemma_.lower()]
            entry[1] += 1
            if pos == _PROPER_NOUN_POS:
                entry[0] += 1
        if on_progress is not None:
            on_progress(done, total_chapters)

    return {lemma: proper / total for lemma, (proper, total) in counts.items()}


# REGEL (technik.md, „Warum die Wortart trotzdem nicht genügt", „Nur der Belegsatz klärt
# den Fall"): Der Belegsatz eines Einzelworts muss dessen gewöhnliche Verwendung zeigen —
# zeigt er stattdessen eine Wendung, sieht das Modell einen Satz, der zur Auswahlliste des
# Einzelworts gar nicht passt, und kann selbst bei richtiger Wortart nicht mehr richtig
# wählen. T17-Nachbesserung (26.08.2026, Abnahme `tools/dorian_gray.epub` Kapitel 10):
# „gone" (19 Vorkommen) bekam durchweg den Beleg „…that he had gone through." — die
# Auswahlliste zu „go" bietet dafür nur „verschwinden" u. Ä., richtig wäre „durchgemacht"
# gewesen; „taken" (11 Vorkommen) ebenso mit „…having taken part in…" statt „teilgenommen".
# Beide Wendungen stehen als eigener Kandidat in `expressions` (`extract_particle_verb_
# candidates`, `extract_contiguous_candidates`), erreichen aber wegen ihrer geringen
# Häufigkeit den Wendungsdeckel nie (`cli/interaction.py`, `EXPRESSION_BLOCK_SIZE`) — das
# Einzelwort bleibt der einzige Ort, an dem der Nutzer sie überhaupt zu sehen bekommt, und
# zeigt dabei die falsche Bedeutung.
#
# Ohne Wörterbuchabgleich (Importregel, technik.md §7: dieses Modul importiert nur
# `entities`) lässt sich eine Wendung hier nicht bestätigen, nur ihr syntaktisches Muster
# erkennen: ein unmittelbar angehängtes, selbst unverzweigtes Satellitenwort (kein eigenes
# Kind-Token, `_is_bare`). Drei Fälle, an Kapitel 10 gegen das echte `en-de.sqlite3`
# nachgeprüft:
# - eine Partikel (`_PARTICLE_DEP`, wie bei `extract_particle_verb_candidates`) oder ein
#   Adverb aus dieser geschlossenen Liste gängiger Phrasal-Verb-Partikel — spaCy markiert
#   dieselbe Konstruktion je nach Satz uneinheitlich als `prt` oder `advmod` („go
#   through." bekommt `advmod`, „went over" `prt`). Ohne die Liste träfe die advmod-Regel
#   auch echte Adverbien wie „late" in „She was running late." — dort bliebe „late" ohne
#   die Liste ein falscher Treffer (geprüft: `test_running_late_keeps_its_belegsatz`)
# - eine Präposition ohne eigenes Objekt
# - ein unbestimmtes Akkusativobjekt: ein bloßes Substantiv ohne Artikel oder Attribut
#   (`taken part` gegenüber `took a great part`, das mit „a" und „great" eigene
#   Kind-Token trägt)
# „went into the library" bleibt unberührt, weil „into" dort ein eigenes Objekt („library")
# trägt — nur der auf sich allein gestellte Fall zählt als Wendungsbeteiligung.
_EXPRESSION_PARTICLE_WORDS = frozenset(
    {
        "up",
        "down",
        "in",
        "out",
        "on",
        "off",
        "away",
        "back",
        "through",
        "over",
        "along",
        "round",
        "forward",
        "across",
        "by",
        "apart",
        "aside",
        "ahead",
        "behind",
    }
)


def _is_bare(token: Token) -> bool:
    """Kein eigenes Kind-Token — das Satellitenwort trägt keine weitere Ergänzung
    (Artikel, Attribut, eigenes Objekt). Unterscheidet „gone through." (kein Kind an
    „through") von „walked through London." (Kind „London" an „through")."""
    return next(token.children, None) is None


def _has_only_a_bare_pronoun_object(token: Token) -> bool:
    """`token`s einziges Kind ist ein unmodifiziertes Personalpronomen (T17-Nachbesserung,
    mittel 3, zweiter Anlauf, 26.08.2026): „to" in „came to him" und „at" in „looked at
    him" haben mit `him` ein eigenes Kind-Token und bestehen `_is_bare` deshalb nicht,
    obwohl ein bloßes Pronomen den idiomatischen Charakter der Wortfolge nicht ändert —
    anders als ein echtes Objekt mit eigenem Inhalt („into the **library**", Kind „the" an
    „library"). Geprüft an `en_core_web_md`: das Pronomen trägt dabei stets `dep_ ==
    "pobj"` und selbst keine weiteren Kinder."""
    children = list(token.children)
    if len(children) != 1:
        return False
    (child,) = children
    return child.dep_ == "pobj" and child.pos_ == "PRON" and _is_bare(child)


def _is_expression_satellite(verb: Token, satellite: Token) -> bool:
    """Bildet `satellite` mit `verb` eher eine Wendung als eine gewöhnliche Wortfolge?
    Siehe die REGEL bei `_EXPRESSION_PARTICLE_WORDS`.

    Der Vergleich läuft über `==`, nicht `is`: spaCy erzeugt bei jedem Zugriff auf
    `token.head` oder `doc[i]` ein neues Wrapper-Objekt für dasselbe Token — `is` liefert
    dabei still `False`, obwohl beide dasselbe Token meinen, und die Prüfung fände nie
    eine Wendung. Beim Bau dieser Funktion tatsächlich mit `is` versucht: die eigens dafür
    geschriebenen Tests (`test_expression_free_occurrence_is_preferred_for_the_example_
    sentence`, `test_falls_back_to_a_wendung_occurrence_when_none_is_free`) fielen beide
    sofort rot, weil „taken part" nie als Wendung erkannt wurde.

    T17-Nachbesserung (mittel 3, zweiter Anlauf, 26.08.2026): Die Bareness-Prüfung galt
    bisher pauschal für alle vier Satellitenarten und ließ „came **to him**" und „looked
    **at him**" durch, weil das Objekt „him" ein eigenes Kind-Token ist. Beide Wortfolgen
    stehen im selben Kapitel (`tools/dorian_gray.epub` Kapitel 10) als eigener
    Wendungskandidat mit anderer Bedeutung (`extract_particle_verb_candidates`,
    `extract_contiguous_candidates`) — der Belegsatz des Einzelworts „came"/„looked" zeigte
    also dieselbe Wendung wie beim `taken part`-Fall oben, nur über ein anderes
    syntaktisches Muster. Die Bareness-Prüfung ist deshalb jetzt je Satellitenart einzeln
    formuliert: Partikel, `advmod` und das unbestimmte Akkusativobjekt bleiben strikt bare
    (unverändert), eine Präposition gilt zusätzlich als Wendungssatellit, wenn ihr einziges
    Kind ein bloßes Personalpronomen ist (`_has_only_a_bare_pronoun_object`) — „went into
    **the library**" bleibt dagegen unberührt, weil „library" kein Pronomen ist."""
    if satellite.head != verb or verb.pos_ != "VERB":
        return False
    if satellite.dep_ == _PARTICLE_DEP:
        return _is_bare(satellite)
    if satellite.dep_ == "advmod":
        return _is_bare(satellite) and satellite.lemma_.lower() in _EXPRESSION_PARTICLE_WORDS
    if satellite.dep_ == "dobj":
        return _is_bare(satellite) and satellite.pos_ == "NOUN"
    if satellite.dep_ == "prep":
        return _is_bare(satellite) or _has_only_a_bare_pronoun_object(satellite)
    return False


def _is_expression_member(token: Token) -> bool:
    """Steht unmittelbar vor oder nach `token` ein Wort, mit dem es eine Wendung statt
    einer gewöhnlichen Wortfolge bildet? Geprüft in beide Richtungen, weil das Vorkommen
    sowohl das Verb als auch das Satellitenwort sein kann."""
    doc = token.doc
    left = doc[token.i - 1] if token.i > 0 else None
    right = doc[token.i + 1] if token.i + 1 < len(doc) else None
    pairs = ((token, right), (right, token), (token, left), (left, token))
    return any(
        verb is not None and satellite is not None and _is_expression_satellite(verb, satellite)
        for verb, satellite in pairs
    )


class _CandidateOccurrence(NamedTuple):
    """Ein einzelnes Token-Vorkommen, vor der Zusammenführung zur Grundform.
    `in_expression` zählt nur in `extract_vocabulary` (REGEL bei
    `_EXPRESSION_PARTICLE_WORDS`) — die beiden Mehrwortausdruck-Funktionen lassen es auf
    der Vorgabe `False`, weil ihre Repräsentantenwahl (`_occurrences_from_candidates`)
    stets das erste Vorkommen nimmt."""

    pos: str
    word_form: str
    example_sentence: str
    in_expression: bool = False


@dataclass(frozen=True)
class VocabularyExtraction:
    """Rückgabe von `extract_vocabulary` (bauplan-phase2.md AP 6): `occurrences` wie vor
    dieser Erweiterung, dazu `token_count` — jedes alphabetische Token des Kapitels
    (`token.is_alpha`), nicht nur die in `occurrences` verbliebenen Inhaltswörter. Nenner
    von `pipeline.coverage` (bauplan-phase2.md, E5, Festlegung 1: „alle Wortformen des
    Kapitels, jedes alphabetische Token — nicht nur die Inhaltswörter der fünf
    Wortarten"): Funktionswörter fehlen in `occurrences` vollständig (siehe
    Moduldocstring, „Nur Inhaltswörter werden zu Kandidaten"), ebenso Grundformen, deren
    Eigennamenanteil die Schwelle `_PROPER_NOUN_RATIO_THRESHOLD` erreicht oder
    überschreitet — nicht nur die ganz eigennamigen, sondern auch die mit einem
    Restanteil gewöhnlicher Vorkommen darunter (Befund 4, Durchsicht 3e71fb8; siehe die
    REGEL bei `_PROPER_NOUN_RATIO_THRESHOLD`). Beide zählen für die Abdeckung als
    verstanden — der Nenner braucht deshalb die volle Tokenzahl, nicht `len(occurrences)`
    oder eine Summe aus deren Häufigkeiten."""

    occurrences: list[Occurrence]
    token_count: int


def extract_vocabulary(
    chapter: Chapter, nlp: Language, *, book_proper_noun_ratios: Mapping[str, float] | None = None
) -> VocabularyExtraction:
    """Extrahiert die Grundformen eines Kapitels (bauplan.md T3), dazu seit
    bauplan-phase2.md AP 6 `token_count` (siehe `VocabularyExtraction`).

    Reihenfolge je Token: Wortart und Grundform kommen beide von spaCy, bevor dieses
    Modul irgendeine Entscheidung trifft — Nachschlagen findet an keiner Stelle statt
    (Regel 2). `occurrences` ist in der Reihenfolge des ersten Vorkommens im Kapitel,
    unsortiert: Häufigkeitssortierung ist Aufgabe von `triage`, nicht von diesem Modul.

    `book_proper_noun_ratios` (T17-Nachbesserung, schwer 1, zweiter Anlauf, 26.08.2026):
    das Ergebnis von `book_proper_noun_ratios()` über das ganze Buch, von
    `pipeline.run_chapter` vorberechnet und hier nur angewendet — siehe die REGEL bei
    `_PROPER_NOUN_RATIO_THRESHOLD`. Fehlt der Wert (`None`, die Vorgabe) oder führt er
    eine Grundform nicht, weicht die Prüfung auf den Anteil **dieses** Kapitels aus — den
    einzigen Wert, der ohne Buchkenntnis zur Verfügung steht. Das hält die Funktion
    rückwärts kompatibel für einen Aufruf mit einem einzelnen, erfundenen Kapitel (etwa in
    Unit-Tests) und ist zugleich der frühere, jetzt nur noch als Rückfall geltende
    Rechenweg.
    """
    _require_lemmatizer(nlp)

    doc = nlp(chapter.text)

    candidates_by_lemma: dict[str, list[_CandidateOccurrence]] = collections.defaultdict(list)
    token_count = 0
    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        for token in sentence:
            if not token.is_alpha:
                continue
            # (bauplan-phase2.md AP 6): zählt jedes alphabetische Token, auch die
            # Funktionswörter und ganz eigennamigen Grundformen, die der Inhaltswortfilter
            # unten aus candidates_by_lemma aussteuert — siehe VocabularyExtraction.
            #
            # (Durchsicht 3e71fb8, Commit 3): token.is_alpha trifft E5s Begründung
            # ("entspricht dem, was der Leser auf der Seite erlebt") an echtem Text bis
            # auf rund ein halbes Prozent — selbst nachgemessen an tools/sherlock.epub
            # Kapitel 2: token_count = 8579 gegen 8542 spaCy-unabhängig gezählte
            # "Leserwörter" (Buchstabenfolgen mit Bindestrich-/Apostroph-Erweiterung),
            # +0,43 %, aus zwei sich teilweise aufhebenden Ursachen. Doppelt gezählt:
            # Bindestrichwörter (`bell-pull`, `Saxe-Meningen`) — spaCy trennt sie in
            # mehrere Token, ein Leser liest ein Wort. Gar nicht gezählt: Token mit
            # Buchstaben, aber `is_alpha` falsch — Klitika (`'s`, `n't`, unschädlich, sie
            # gehören zum Nachbartoken) und echte Ausfälle wie Abkürzungen mit Punkt
            # (`Mr.`, `St.`) und `o'clock`. Ziffern zählen nie.
            token_count += 1
            pos = token.pos_
            if pos not in _CONTENT_POS and pos != _PROPER_NOUN_POS:
                continue
            lemma_text = token.lemma_.lower()
            candidates_by_lemma[lemma_text].append(
                _CandidateOccurrence(
                    pos=pos,
                    word_form=token.text,
                    example_sentence=sentence_text,
                    in_expression=_is_expression_member(token),
                )
            )

    occurrences: list[Occurrence] = []
    for lemma_text, candidates in candidates_by_lemma.items():
        proper_count = sum(1 for c in candidates if c.pos == _PROPER_NOUN_POS)
        # (T17-Nachbesserung, schwer 1, zweiter Anlauf, 26.08.2026): `proper_count`-Wächter
        # zuerst — bei 0 ist der Anteil ohnehin 0 und die Grundform bleibt so oder so
        # erhalten. Zugleich die notwendige Bedingung, die den `frank`-Fall verhindert
        # (siehe Bericht): Hat **dieses** Kapitel kein einziges PROPN-Vorkommen dieser
        # Grundform, gibt es hier keinen Namensbeleg, der buchweit bestätigt werden
        # könnte — ein Kapitel, in dem ein sonst meist eigennamiges Wort ausnahmsweise
        # ganz gewöhnlich vorkommt, verliert es dadurch nicht.
        #
        # (Nachbesserung am eigenen Fund, 26.08.2026): Sind **alle** Vorkommen dieses
        # Kapitels eigennamig (proper_count == len(candidates)), gibt es in diesem Kapitel
        # keinen einzigen Beleg für die gewöhnliche Verwendung — unabhängig vom buchweiten
        # Anteil, der anderswo im Buch gemessen sein mag. Ohne diese Prüfung stürzte
        # `min(pos_counts, ...)` weiter unten auf einer leeren Liste ab, sobald der
        # buchweite Anteil unter der Schwelle blieb (etwa „march", „duke" in
        # tools/sherlock.epub Kapitel 2: dort ausschließlich als PROPN vertaggt, buchweit
        # aber überwiegend gewöhnliche Wörter) — Regel 13 verbietet, das als Absturz statt
        # als erkannten Fall zu behandeln.
        if proper_count == len(candidates):
            continue
        if proper_count:
            ratio = (
                book_proper_noun_ratios[lemma_text]
                if book_proper_noun_ratios is not None and lemma_text in book_proper_noun_ratios
                else proper_count / len(candidates)
            )
            if ratio >= _PROPER_NOUN_RATIO_THRESHOLD:
                # Ganz oder weit überwiegend eigennamige Vorkommen (Regel 12,
                # _PROPER_NOUN_RATIO_THRESHOLD): Bleibt trotzdem mindestens ein
                # nicht-eigennamiges Vorkommen übrig (sonst hätte der Zweig oben schon
                # eingegriffen), taugt es allein noch nicht als Lernkontext, wenn Buch oder
                # Kapitel überwiegend den Namen meinen.
                continue

        non_proper = [c for c in candidates if c.pos != _PROPER_NOUN_POS]
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
        same_pos = [c for c in non_proper if c.pos == chosen_pos]
        # Bevorzugt ein wendungsfreies Vorkommen (REGEL bei `_EXPRESSION_PARTICLE_WORDS`)
        # und weicht nur dann auf eines mit Wendungsbeteiligung aus, wenn keines frei
        # davon ist — same_pos ist nie leer, chosen_pos stammt aus genau dieser Liste.
        representative = next((c for c in same_pos if not c.in_expression), same_pos[0])
        occurrences.append(
            Occurrence(
                book=chapter.book,
                chapter_number=chapter.number,
                lemma=Lemma(text=lemma_text, pos=chosen_pos),
                word_form=representative.word_form,
                example_sentence=representative.example_sentence,
                # (T17-Nachbesserung, mittel 1, 26.08.2026): frequency zählt nur die
                # nicht-eigennamigen Vorkommen — siehe REGEL bei `Occurrence.frequency`.
                frequency=len(non_proper),
                proper_noun_frequency=len(candidates) - len(non_proper),
            )
        )

    return VocabularyExtraction(occurrences=occurrences, token_count=token_count)


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

    Befund 3, Review T4 (entschieden in Review T13, Befund 8): Bei einem langen Einschub
    („chat this little matter over") umfasst `word_form` den ganzen Bereich zwischen Verb
    und Partikel, nicht nur die beiden Wörter selbst — auf der Karte steht dann ein ganzer
    Satzteil als „Beugungsform". Das bleibt so: `libreverbum.anki` behandelt `word_form`
    als beliebig lange Zeichenkette, das Wort-Feld zeigt sie unverändert, und der
    Lückentext findet sie über Wortgrenzen hinweg an ihrer Stelle im Belegsatz (Befund 4,
    Review T13) — unabhängig davon, ob sie ein Wort oder mehrere umfasst. Das Kartenlayout
    erzwingt also keine engere Wortform; eine Eingrenzung auf Verb und Partikel bliebe eine
    eigene, hier nicht getroffene Entscheidung über den *Inhalt* der Karte, keine
    technische Notwendigkeit.
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


def extract_proper_noun_list(chapter: Chapter, nlp: Language) -> list[ProperNounEntry]:
    """Extrahiert die rohen Eigennamen-Vorkommen eines Kapitels für die Liste „Figuren &
    Orte" (bauplan-phase2.md AP 8) — über spaCys eigene Entitätserkennung (`doc.ents`,
    `ent.label_` in `_PROPER_NOUN_ENTITY_TYPES`), unabhängig vom Wortart-/Grundform-Weg
    von `extract_vocabulary`: Eine mehrwortige Entität wie „Sherlock Holmes" ist keine
    Grundform, und die Liste braucht ausdrücklich die **Oberflächenform**, nie die
    lemmatisierte (technik.md §5, offener Punkt „Über-Lemmatisierung von Eigennamen" —
    „Holmes" → „holme"). Liefert nur die rohen, je Kapitel gezählten Vorkommen; Sortierung
    und Gruppierung („Figuren" gegen „Orte") sind Sache von `printout`, nicht dieser
    Funktion (technik.md §7, „Die Liste »Figuren & Orte« ist Phase 2").

    Mehrere Vorkommen derselben Oberflächenform im Kapitel werden zu einem Eintrag
    zusammengezählt (`frequency`), unabhängig vom beobachteten Entitätstyp: spaCy tastet
    bei sonst gleicher Textstelle uneinheitlich (an `tools/sherlock.epub` Kapitel 2 etwa
    „Briony Lodge" als GPE, FAC **und** PERSON, „Bohemia" überwiegend als PERSON statt
    GPE, siehe REGEL bei `_PROPER_NOUN_ENTITY_TYPES`) — ohne diese Zusammenfassung
    erschiene dieselbe Oberflächenform mehrfach in der Liste. `ent_type` des
    zusammengeführten Eintrags ist der häufigste beobachtete Typ dieser Oberflächenform,
    bei Gleichstand der zuerst gesehene — dieselbe Regel wie die Wortartwahl in
    `extract_vocabulary` (siehe dort, „Mischt eine Grundform mehrere Wortarten …").

    Zeilenumbrüche aus dem Buchsatz innerhalb einer Entitätsspanne (`Span.text`, wie bei
    `extract_particle_verb_candidates`) werden wie dort zu einem Leerzeichen
    zusammengezogen (`_collapse_whitespace`).

    Reihenfolge: erstes Auftreten im Kapitel, unsortiert (wie `extract_vocabulary`s
    `occurrences`)."""
    _require_ner(nlp)

    doc = nlp(chapter.text)

    labels_by_text: dict[str, list[str]] = collections.defaultdict(list)
    order: list[str] = []
    for ent in doc.ents:
        if ent.label_ not in _PROPER_NOUN_ENTITY_TYPES:
            continue
        text = _collapse_whitespace(ent.text)
        if text not in labels_by_text:
            order.append(text)
        labels_by_text[text].append(ent.label_)

    entries: list[ProperNounEntry] = []
    for text in order:
        labels = labels_by_text[text]
        type_counts: collections.Counter[str] = collections.Counter()
        first_seen_at: dict[str, int] = {}
        for index, label in enumerate(labels):
            type_counts[label] += 1
            first_seen_at.setdefault(label, index)
        chosen_type = min(
            type_counts, key=lambda label: (-type_counts[label], first_seen_at[label])
        )
        entries.append(
            ProperNounEntry(
                book=chapter.book,
                chapter_number=chapter.number,
                text=text,
                ent_type=chosen_type,
                frequency=len(labels),
            )
        )
    return entries
