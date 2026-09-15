"""Wörterbuch — Auswahlliste je Grundform und Wortart aus WikDict, samt Erstbezug.

Aufgabe
-------
Schritt 5 des Kernablaufs (konzept.md §5), erste Hälfte: der einzige Zugriff auf
`en-de.sqlite3` (technik.md §7, Modulkarte). `candidates` liefert die Kandidaten, aus
denen `translation` — Schritt 5, zweite Hälfte — die im Kontext passende Bedeutung wählt;
`candidate_lists` dieselbe Abfrage für mehrere Grundformen über eine geteilte Verbindung
(Befund 4, Review T15). `contiguous_candidates` und `particle_verb_candidates` gleichen
dazu die beiden Mehrwortausdruck-Kandidaten aus T4 gegen dieselbe Tabelle ab (bauplan.md
T7) — getrennt, weil sie verschieden viel behaupten (Abschnitt „Liefert" unten, Befund 1
Review T7). `pos_variants` und `pos_variant_lists` (Bauschritt 3/5 der Vorbelegung,
31.08.2026) kehren `candidates` um: Sie bestimmen die Wortart erst aus dem Fund, für eine
Grundform, deren Wortart noch niemand kennt (`wordfreq_en_5000.txt` trägt keine).
`fetch_dictionary` liefert dazu den Erstbezug der Datei selbst (bauplan.md T6):
Herunterladen, Prüfung, von Hand hinterlegte Datei, die beiden Indizes auf
`translation(written_rep)`.

Voraussetzungen
---------------
`candidates` und `candidate_lists` erwarten die Grundform(en) bereits wortartbestimmt
(`Lemma.pos`, spaCys `token.pos_`): Die Reihenfolge Wortart → Grundform → Nachschlagen ist
zwingend (technik.md, „Warum die Reihenfolge zwingend ist"). `pos_variants` und
`pos_variant_lists` kehren das um und erwarten deshalb nur einen bloßen Text, keine
`Lemma` — genau der Fall der eingefrorenen Grundwortschatzliste
(`wordfreq_en_5000.txt`, „Diese Datei trägt kein pos"). `contiguous_candidates`
erwartet die gesamte Liste der Kandidaten aus einem Aufruf von
`extraction.extract_contiguous_candidates`, `particle_verb_candidates` die aus
`extraction.extract_particle_verb_candidates` (T4) — welche der beiden Funktionen
aufgerufen wird, entscheidet der Aufrufer anhand der Herkunft der Kandidaten, nicht dieses
Modul (`extraction.py`, „T7 unterscheidet die zwei Arten daran, welche der beiden
Funktionen sie geliefert hat"). Alle Listenformen nehmen eine Liste statt eines
einzelnen Kandidaten entgegen und teilen sich dafür eine Verbindung (Befund 5, Review T7;
Befund 4, Review T15): Eine eigene Verbindung je Kandidat kostet ein Kapitel mit rund
23.600 Mehrwort-Kandidaten 14,3 s, eine gemeinsame Verbindung für die ganze Liste 1,7 s
(Bericht T7); bei den 1.465 Einzelwort-Vorkommen aus Kapitel 13 (Sherlock) sind es 1,43 s
gegen 0,20 s (Bericht T15) — mehr, als konzept.md §4 für das ganze Nachschlagen der
Standardstellung veranschlagt (rund 1,1 s). `fetch_dictionary` erwartet nur den Zielpfad;
welches Verzeichnis das ist, entscheidet allein der Aufrufer (technik.md §9).

Liefert
-------
Je Grundform und Wortart eine nach `score` absteigend sortierte Liste von `Sense`
(bauplan.md T5). Zeilen ohne `sense`-Text bleiben darin (Regel 1); `label` liefert für sie
die vorgeschriebene Beschriftung. `candidate_lists` liefert dieselbe Liste je Eingabe-
`Lemma`, in derselben Reihenfolge wie die Eingabe (Befund 4, Review T15) — kein
Zwischenspeicher (Regel 14), nur eine für den einen Aufruf geteilte Verbindung.
`pos_variants` liefert je Text alle `(Lemma, Bedeutungen)`-Paare, für die das Wörterbuch
unter einer der fünf erkannten Wortarten mindestens einen Eintrag führt — leer, wo keine
Wortart trifft, nie geraten (Bauschritt 3/5 der Vorbelegung: „Die Wortarten kommen deshalb
aus dem Wörterbuch"). `pos_variant_lists` dieselbe Abfrage über eine geteilte Verbindung,
wie `candidate_lists`.
`contiguous_candidates` und `particle_verb_candidates` liefern je Eingabe-`Lemma` ebenso
eine solche Liste — case-insensitiv gegen `written_rep` abgeglichen, gefiltert auf
`score ≥ 50` und Wortart nicht `Proper_noun` (technik.md, „Messung: Mehrwortausdrücke") —,
behandeln einen Kandidaten ohne bestandenen Filter aber verschieden (Befund 1, Review T7):
`extract_contiguous_candidates` liefert bloße Hypothesen aus einem n-Gramm-Abgleich, und
der Filter ist genau das Mittel, das `of the` und `in the` wieder aussortiert — ohne
Eintrag liefert `contiguous_candidates` deshalb an dieser Stelle eine **leere Liste**, der
Kandidat verschwindet. `extract_particle_verb_candidates` liefert dagegen ein tatsächlich
beobachtetes Phrasal Verb aus der Abhängigkeitsanalyse — ohne Eintrag liefert
`particle_verb_candidates` deshalb an dieser Stelle einen einzelnen `Sense` mit
`uncertain=True` (Regel 10, Regel 11): markiert, nicht verworfen. Alle wählen selbst keine
Bedeutung aus und übersetzen nichts frei — das bleibt `translation` vorbehalten.

`fetch_dictionary` lädt die Datei, falls sie fehlt, prüft Vollständigkeit und Schema und
legt die Indizes an — auch für eine bereits vorhandene, von Hand hinterlegte Datei, die sie
ebenfalls nicht mitbringt. `SOURCE_NOTICE` ist der Text zu Herkunft und Lizenz, den der
Aufrufer beim ersten Bezug anzeigen kann (technik.md §2, „Warum nicht mitgeliefert").
"""

from __future__ import annotations

import sqlite3
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from libreverbum.entities import Lemma, Sense

# REGEL (dokumentation.md §4 Regel 1, technik.md §3 „Datenfalle: Einträge ohne
# Bedeutungstext"): Zeilen ohne sense-Text nicht wegfiltern. 36 % aller Zeilen, systematisch
# die Hauptbedeutungen (watch → „Uhr", draw → „zeichnen"). Wer sie entfernt, erzeugt
# scheinbare Wörterbuchlücken. `entities.Sense` hält `wikdict_sense` für diese Zeilen
# bewusst auf `None` — die Beschriftung unten ist reine Anzeige, kein gespeicherter Wert.
NO_SENSE_LABEL = "Hauptbedeutung, ohne nähere Angabe"

# REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): Wortart vor Grundform vor
# Nachschlagen — `saw` als Verb darf nicht die Säge liefern. WikDicts `lexentry` trägt die
# Wortart als eigenes Segment (`eng/<wort>__<Wortart>__<n>`) unter deren eigenem Namen.
# Nur die fünf Wortarten, die T3s Inhaltswortfilter dieser Phase überhaupt vorlegt (Regel 14,
# kein Vorrat auf Vorrat): Substantiv, Verb, Adjektiv, Adverb, Interjektion. `PROPN` fehlt
# bewusst — T3 setzt `chosen_pos` nie darauf, und T7 filtert `Proper_noun` ohnehin weg.
_WIKDICT_POS = {
    "NOUN": "Noun",
    "VERB": "Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "INTJ": "Interjection",
}


# REGEL (dokumentation.md §4 Regel 13; Befund 3, Review T7): Der Platzhalter für einen
# Mehrwortausdruck-Kandidaten ohne Wörterbucheintrag (`uncertain=True`) trägt kein
# `wikdict_sense` — ohne eigene Beschriftung liefe er in `NO_SENSE_LABEL` und sähe aus wie
# eine echte Regel-1-Zeile mit Hauptbedeutung, obwohl kein `wikdict_trans_list` dahinter
# steht. `label` muss den Unterschied vor der Anzeige (T11, T13) sichtbar machen.
# (Befund 2, Review T11): `translation._sense_line` beschriftet einen so hereingegebenen
# Kandidaten im Prompt mit einer eigenen, gleichlautenden Konstante
# (`translation._UNCERTAIN_TEXT`) statt eines Imports — die Importregel verbietet
# `translation` den Zugriff auf `dictionary` (technik.md §7). Läuft der Text hier
# auseinander, sollte er dort mitgezogen werden.
UNCERTAIN_LABEL = "kein Wörterbucheintrag — unsicher"


def label(sense: Sense) -> str:
    """Beschriftung für die Auswahlliste: `UNCERTAIN_LABEL` für einen Platzhalter ohne
    Wörterbucheintrag (Befund 3, Review T7), sonst `wikdict_sense` — oder, fehlt er,
    Regel 1s feste Beschriftung `NO_SENSE_LABEL`."""
    if sense.uncertain:
        return UNCERTAIN_LABEL
    return sense.wikdict_sense or NO_SENSE_LABEL


def _wikdict_pos(lexentry: str | None) -> str | None:
    """Die Wortart aus WikDicts `lexentry`-Kennung (`eng/<wort>__<Wortart>__<n>`)."""
    if lexentry is None or "__" not in lexentry:
        return None
    return lexentry.split("__")[1]


def _single_word_matches(con: sqlite3.Connection, lemma: Lemma) -> list[Sense]:
    """Kern der Abfrage aus `candidates` (T5) für eine bereits offene Verbindung — gemeinsam
    mit `candidate_lists` (Befund 4, Review T15), das dieselbe Verbindung über mehrere
    Lemmas hinweg teilt, statt sie je Lemma neu aufzubauen. Dieselbe Bauart wie
    `_lookup_matches` für die Mehrwortausdrücke aus T7."""
    try:
        wikdict_pos = _WIKDICT_POS[lemma.pos]
    except KeyError as error:
        raise ValueError(f"Keine WikDict-Wortart für {lemma.pos!r} hinterlegt.") from error

    # REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): lexentry IS NOT NULL ist
    # eine ausdrückliche Entscheidung, keine Nebenwirkung. 29,7 % der Zeilen in
    # tools/en-de.sqlite3 haben lexentry = NULL und tragen damit keine Wortart —
    # _wikdict_pos gäbe für sie still None zurück, das nie einer WikDict-Wortart gleicht,
    # und die Zeile verschwände unbemerkt aus jeder Auswahlliste. Vertretbar, weil alle
    # betroffenen Zeilen bei score <= 48 liegen, deutlich unter den Hauptbedeutungen —
    # aber das gehört sichtbar in die Abfrage, nicht als stiller Filterausfall.
    rows: list[tuple[str | None, str | None, str | None]] = con.execute(
        "SELECT lexentry, sense, trans_list FROM translation "
        "WHERE written_rep = ? AND lexentry IS NOT NULL ORDER BY score DESC",
        (lemma.text,),
    ).fetchall()

    return [
        Sense(
            lemma=lemma,
            wikdict_sense=wikdict_sense,
            wikdict_trans_list=trans_list,
            wikdict_lexentry=lexentry,
        )
        for lexentry, wikdict_sense, trans_list in rows
        if _wikdict_pos(lexentry) == wikdict_pos
    ]


def candidates(dictionary_path: Path, lemma: Lemma) -> list[Sense]:
    """Auswahlliste für eine Grundform und Wortart, nach `score` absteigend.

    Regel 1 (dokumentation.md §4): Zeilen ohne `sense`-Text bleiben in der Liste — sie sind
    systematisch die Hauptbedeutungen, keine Lücken. Die Wortart ist Teil der Abfrage: `saw`
    als Verb liefert nur „sägen", nie die Säge (technik.md, „Warum die Reihenfolge zwingend
    ist"). Eine fehlende oder unlesbare Wörterbuchdatei bricht sichtbar ab (Regel 13) statt
    eine leere Liste zurückzugeben, die wie „kein Eintrag gefunden" aussähe.
    """
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    con = sqlite3.connect(dictionary_path)
    try:
        return _single_word_matches(con, lemma)
    finally:
        con.close()


def candidate_lists(dictionary_path: Path, lemmas: Sequence[Lemma]) -> list[list[Sense]]:
    """Auswahllisten für mehrere Grundformen über eine geteilte Verbindung (Befund 4,
    Review T15) — dieselbe Bauart wie `_lookup_matches` (T7): eine Verbindung, Schleife über
    die Lemmas, Rückgabe in Eingabereihenfolge.

    Gemessen an einer indizierten Kopie von `tools/en-de.sqlite3`, 1.465 Einzelwort-
    Vorkommen aus Kapitel 13 (Sherlock, das längste): eine eigene Verbindung je Vorkommen
    (wie `pipeline` vor dieser Behebung) kostet 1,43 s, eine geteilte 0,20 s — 7,2×, mehr
    Zeit allein für den Verbindungsaufbau, als konzept.md §4 für das ganze Nachschlagen der
    Standardstellung veranschlagt (rund 1,1 s). Kein Zwischenspeicher (Regel 14): Nichts
    wird über diesen einen Aufruf hinaus aufbewahrt, nur die Verbindung für seine Dauer
    geteilt. Dieselbe Regel 13 wie bei `candidates`: eine fehlende Wörterbuchdatei bricht
    sichtbar ab, statt je Lemma eine leere Liste vorzutäuschen."""
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    con = sqlite3.connect(dictionary_path)
    try:
        return [_single_word_matches(con, lemma) for lemma in lemmas]
    finally:
        con.close()


# --------------------------------------- Umkehrung: Wortart aus dem Fund (Bauschritt 3/5
# --------------------------------------- der Vorbelegung, 31.08.2026)

# Umkehrung von _WIKDICT_POS: WikDict-Wortart -> spaCy-Wortart. `pos_variants` bestimmt
# die Wortart erst aus dem Fund, anders als candidates()/candidate_lists(), die eine
# bereits bekannte Lemma.pos erwarten — genau der Fall der eingefrorenen
# Grundwortschatzliste, die kein pos trägt (wordfreq_en_5000.txt).
_SPACY_POS = {wikdict: spacy for spacy, wikdict in _WIKDICT_POS.items()}


def _pos_variants(con: sqlite3.Connection, text: str) -> list[tuple[Lemma, list[Sense]]]:
    """Kern von `pos_variants`/`pos_variant_lists` für eine bereits offene Verbindung —
    dieselbe Abfrage wie `_single_word_matches`, nur **eine** statt fünf: alle Zeilen zu
    `text` auf einmal, danach nach der in `lexentry` gefundenen Wortart gruppiert. Nur die
    fünf Wortarten aus `_WIKDICT_POS` zählen (dieselbe Einschränkung wie
    `_single_word_matches`) — eine Zeile mit einer anderen WikDict-Wortart (`Pronoun`,
    `Preposition`, `Determiner`, …) liefert `_wikdict_pos(...)` zwar zurück, aber
    `extraction.extract_vocabulary` vergibt `chosen_pos` nie an eine dieser Wortarten
    (Inhaltswortfilter, `dictionary.py`, „Warum die Reihenfolge zwingend ist"), ein
    Wortweg-Fund unter ihnen entspräche also keiner Grundform, die der Kern je bildet."""
    rows: list[tuple[str | None, str | None, str | None]] = con.execute(
        "SELECT lexentry, sense, trans_list FROM translation "
        "WHERE written_rep = ? AND lexentry IS NOT NULL ORDER BY score DESC",
        (text,),
    ).fetchall()

    senses_by_pos: dict[str, list[Sense]] = {}
    for lexentry, wikdict_sense, trans_list in rows:
        found_pos = _wikdict_pos(lexentry)
        if found_pos is None:
            continue
        spacy_pos = _SPACY_POS.get(found_pos)
        if spacy_pos is None:
            continue
        lemma = Lemma(text=text, pos=spacy_pos)
        senses_by_pos.setdefault(spacy_pos, []).append(
            Sense(
                lemma=lemma,
                wikdict_sense=wikdict_sense,
                wikdict_trans_list=trans_list,
                wikdict_lexentry=lexentry,
            )
        )
    return [(Lemma(text=text, pos=pos), senses) for pos, senses in senses_by_pos.items()]


def pos_variants(dictionary_path: Path, text: str) -> list[tuple[Lemma, list[Sense]]]:
    """Alle (Grundform, Wortart)-Paare, für die `text` als Einzelwort mindestens einen
    Wörterbucheintrag hat, samt deren Bedeutungen — die Umkehrung von `candidates()`
    (Bauschritt 3/5 der Vorbelegung, 31.08.2026): Dort ist `Lemma.pos` bereits bekannt, hier
    wird sie erst gesucht, weil die eingefrorene Grundwortschatzliste
    (`wordfreq_en_5000.txt`) keine Wortart trägt.

    Nur die fünf Wortarten aus `_WIKDICT_POS`, wie `candidates()`. `text` ohne Eintrag
    unter diesen Wortarten liefert eine **leere** Liste, keinen `uncertain`-Platzhalter:
    Anders als ein Kandidat aus einem echten Kapitel (`particle_verb_candidates`) ist eine
    Grundform aus der eingefrorenen Liste ohne Fund keine beobachtete, aber unbekannte
    Verwendung — es gibt keine Bedeutung, die als bekannt gebucht werden könnte.
    """
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")
    con = sqlite3.connect(dictionary_path)
    try:
        return _pos_variants(con, text)
    finally:
        con.close()


def pos_variant_lists(
    dictionary_path: Path, texts: Sequence[str]
) -> list[list[tuple[Lemma, list[Sense]]]]:
    """`pos_variants` für mehrere Grundformen über eine geteilte Verbindung (Bauschritt
    3/5 der Vorbelegung, 31.08.2026) — dieselbe Bauart wie `candidate_lists` (Befund 4,
    Review T15): Bei 5.000 Grundformen kostet eine eigene Verbindung je Grundform ein
    Vielfaches einer geteilten (vgl. `candidate_lists`-Docstring, 7,2× bei 1.465
    Vorkommen)."""
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")
    con = sqlite3.connect(dictionary_path)
    try:
        return [_pos_variants(con, text) for text in texts]
    finally:
        con.close()


# ---------------------------------------------------- Mehrwortausdrücke (bauplan.md T7)

# REGEL (technik.md, „Messung: Mehrwortausdrücke"): Die Schwelle trennt grammatisches
# Rauschen von echten Wendungen sauber — gemessen an tools/en-de.sqlite3, nicht geschätzt
# („in the" score 2,0, „of the" score 4,0 gegen „give up" score 120,0, „of course" score
# 128,6). Festlegung aus bauplan.md T7, keine Einstellung (Regel 14).
_MWE_MIN_SCORE = 50

# REGEL (technik.md, „Messung: Mehrwortausdrücke"; Nachtrag 18.08.2026, siehe dort): Der
# zweite Teil des Filters. Nötig, weil Eigennamen wie „New York" (Proper_noun, score 163,6)
# oder „Great Britain" (210,0) selbst als mehrwortiger Wörterbucheintrag mit hohem score
# geführt werden und sonst als Lernvokabel erschienen.
_EXCLUDED_MWE_POS = "Proper_noun"


def _lookup_matches(dictionary_path: Path, lemmas: Sequence[Lemma]) -> list[list[Sense]]:
    """Gemeinsamer Abgleichskern für `contiguous_candidates` und `particle_verb_candidates`
    (Befund 1, Review T7): beide filtern gleich, unterscheiden sich nur darin, was ein
    Kandidat ohne bestandenen Filter bedeutet — das entscheiden die beiden Funktionen
    selbst, nicht dieser Kern, der je Eingabe-`Lemma` deshalb schlicht eine leere Liste
    liefern kann.

    Filtert `score ≥ 50` und Wortart nicht `Proper_noun` (technik.md, „Messung:
    Mehrwortausdrücke") — anders als `candidates` nicht auf Übereinstimmung mit einer
    einzelnen Wortart: WikDicts Wendungen verteilen sich über eigene Wortarten (`Phrase`,
    `Prepositional_phrase`, `Proverb`, dazu gewöhnliche Nomen und Verben), während
    `Lemma.pos` aus T4 höchstens `VERB` trägt oder leer ist.

    # REGEL (Befund 2, Review T7): `COLLATE NOCASE`, weil T4 jede Grundform kleinschreibt
    # (`extraction.py`, `token.lemma_.lower()`), WikDicts `written_rep` aber schreibungsecht
    # ist — `new york` fände `New York` ohne diesen Vergleich nie (gemessen an
    # tools/en-de.sqlite3: `written_rep = 'new york'` liefert 0 Zeilen, `= 'new york'
    # COLLATE NOCASE` die echte Zeile). Der zugehörige Index (`ensure_index`,
    # `INDEX_NAME_NOCASE`) hält die Abfrage dabei auf `SEARCH` statt `SCAN` — ohne ihn
    # kollationiert SQLite bei jeder Zeile neu (technik.md §3, „Der Engpass ist das
    # Nachschlagen, nicht das Modell").

    # REGEL (Befund 5, Review T7): Eine einzige Verbindung für die gesamte Liste, nicht
    # eine je Kandidat — gemessen an einer Kopie von tools/en-de.sqlite3 mit Index, ein
    # Kapitel mit rund 23.600 Kandidaten: 14,3 s je eigener Verbindung gegen 1,7 s geteilt
    # (Bericht T7). Kein Zwischenspeicher (Regel 14) — es wird nichts über den Aufruf
    # hinaus aufbewahrt, nur die Verbindung für die Dauer dieses einen Aufrufs geteilt.
    """
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"Wörterbuch nicht lesbar: {dictionary_path}")

    results: list[list[Sense]] = []
    con = sqlite3.connect(dictionary_path)
    try:
        for lemma in lemmas:
            rows: list[tuple[str | None, str | None, str | None]] = con.execute(
                "SELECT lexentry, sense, trans_list FROM translation "
                "WHERE written_rep = ? COLLATE NOCASE AND score >= ? ORDER BY score DESC",
                (lemma.text, _MWE_MIN_SCORE),
            ).fetchall()
            results.append(
                [
                    Sense(
                        lemma=lemma,
                        wikdict_sense=wikdict_sense,
                        wikdict_trans_list=trans_list,
                        wikdict_lexentry=lexentry,
                    )
                    for lexentry, wikdict_sense, trans_list in rows
                    if _wikdict_pos(lexentry) != _EXCLUDED_MWE_POS
                ]
            )
    finally:
        con.close()

    return results


def contiguous_candidates(dictionary_path: Path, lemmas: Sequence[Lemma]) -> list[list[Sense]]:
    """Auswahllisten für die Kandidaten aus einem Aufruf von
    `extraction.extract_contiguous_candidates` (bauplan.md T7; Befund 1 und Befund 5,
    Review T7) — eine Liste je Eingabe-`Lemma`, in derselben Reihenfolge wie `lemmas`.

    Ein Kandidat aus dem n-Gramm-Weg ist bloß eine Hypothese — `of the` sieht vor dem
    Nachschlagen genauso aus wie `give up` (technik.md, „Messung: Mehrwortausdrücke", die
    Hälfte, die 6.202 rohe Vorkommen auf 2.958 senkt). Besteht für einen Kandidaten kein
    Eintrag den Filter (`_lookup_matches`), liefert diese Funktion an seiner Stelle deshalb
    eine **leere Liste** — der Kandidat verschwindet, das ist der Zweck dieses Wegs, keine
    Markierung wie bei `particle_verb_candidates`. Eine fehlende Wörterbuchdatei bricht
    dagegen sichtbar ab (Regel 13) — das ist ein anderer Fehlschlag als ein einzelner
    Kandidat ohne Eintrag.
    """
    return _lookup_matches(dictionary_path, lemmas)


def particle_verb_candidates(dictionary_path: Path, lemmas: Sequence[Lemma]) -> list[list[Sense]]:
    """Auswahllisten für die Kandidaten aus einem Aufruf von
    `extraction.extract_particle_verb_candidates` (bauplan.md T7; Befund 1 und Befund 5,
    Review T7) — eine Liste je Eingabe-`Lemma`, in derselben Reihenfolge wie `lemmas`.

    Ein Kandidat aus dem Verb-Partikel-Weg ist ein tatsächlich beobachtetes Phrasal Verb aus
    spaCys Abhängigkeitsanalyse, kein bloßer Wortfolgentreffer (technik.md §3, „Grenze: rund
    ein Fünftel der Phrasal Verbs steht getrennt": 394 Vorkommen ohne Eintrag). Besteht für
    einen Kandidaten kein Eintrag den Filter (`_lookup_matches`), liefert diese Funktion an
    seiner Stelle deshalb keine leere Liste, sondern einen einzelnen `Sense` mit
    `uncertain=True` (Regel 10, Regel 11): Der Kandidat wird markiert, nicht verworfen. Eine
    fehlende Wörterbuchdatei bricht dagegen sichtbar ab (Regel 13) wie bei
    `contiguous_candidates` — das ist ein anderer Fehlschlag als ein einzelner Kandidat ohne
    passenden Eintrag.
    """
    matches = _lookup_matches(dictionary_path, lemmas)
    return [
        matches_for_lemma or [Sense(lemma=lemma, uncertain=True)]
        for lemma, matches_for_lemma in zip(lemmas, matches, strict=True)
    ]


# --------------------------------------------------------------- Erstbezug (bauplan.md T6)

# REGEL (technik.md §2, „Warum nicht mitgeliefert"): Bezugsquelle laut Entscheidung 2,
# geprüft 11.08.2026. Ein Aufrufargument statt einer festen Verdrahtung, ausschließlich
# der Testbarkeit wegen (`fetch_dictionary` muss gegen eine örtliche Attrappe laufen können,
# dokumentation.md §5) — ein zweiter echter Anwendungsfall besteht nicht: `config.toml`
# (technik.md §9) sieht bewusst keinen eigenen Schlüssel für die Wörterbuchquelle vor, weil
# Entscheidung 2 sich auf genau eine Quelle festgelegt hat.
DICTIONARY_URL = "https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3"

# REGEL (technik.md §2, „Warum nicht mitgeliefert"): Hinweis auf Herkunft und Lizenz, den
# der Aufrufer beim ersten Bezug anzeigen kann. Die genaue CC-BY-SA-Version (3.0 oder 4.0)
# ist in technik.md §2 als offener Punkt vermerkt, nicht hier vorweggenommen.
SOURCE_NOTICE = (
    "Wörterbuch: WikDict, Sprachpaar Englisch-Deutsch, aus Wiktionary erzeugt über das "
    "DBnary-Projekt (https://wikdict.com). Lizenz: Creative Commons BY-SA. Bezug von "
    f"{DICTIONARY_URL}."
)

# Der Index aus technik.md §3, „Der Engpass ist das Nachschlagen, nicht das Modell" —
# siehe ensure_index für die Messung.
# Trägt `candidates` (T5); dessen Abfrage vergleicht `written_rep` binär, nicht case-
# insensitiv (Befund 2, Review T7, „nur berichtet, nicht geändert" — siehe Bericht).
INDEX_NAME = "idx_translation_written_rep"

# REGEL (Befund 2, Review T7): Zweiter Index, eigens für den case-insensitiven Vergleich in
# `_lookup_matches` (T7). Ein `COLLATE NOCASE`-Vergleich kann den Index ohne diese eigene
# Kollation nicht benutzen und fiele auf den vollen Scan zurück (technik.md §3, „Der
# Engpass ist das Nachschlagen, nicht das Modell": 32–44 s statt 1,1 s je Kapitel) —
# derselbe Kostenunterschied wie beim
# unindizierten `candidates`, nur ausgelöst durch die fehlende Kollation statt durch einen
# fehlenden Index.
INDEX_NAME_NOCASE = "idx_translation_written_rep_nocase"

_EXPECTED_TABLE = "translation"
_EXPECTED_COLUMNS = frozenset({"lexentry", "sense", "written_rep", "trans_list", "score"})

# REGEL (technik.md §2, „Keine Prüfsumme, weil WikDict keine veröffentlicht"): Untergrenze
# für _validate_schema, deutlich unter den 157.801 Zeilen der echten Datei (technik.md
# §3), aber hoch genug, dass eine leere oder grob unvollständige, aber schemarichtige
# Tabelle nicht als gültig durchgeht.
_MIN_TRANSLATION_ROWS = 100_000


def ensure_index(path: Path) -> None:
    """Legt beide Indizes auf `translation(written_rep)` an, falls sie fehlen (bauplan.md
    T6; zweiter Index Befund 2, Review T7).

    Ohne den ersten Index scannt jede Abfrage aus `candidates` die volle Tabelle mit
    anschließender Sortierung im Speicher; ohne den zweiten (`INDEX_NAME_NOCASE`) tut
    dasselbe jede case-insensitive Abfrage aus `_lookup_matches` (T7), weil `COLLATE
    NOCASE` den binären Index nicht benutzen kann. Größenordnung und Wirkung: technik.md
    §3, „Der Engpass ist das Nachschlagen, nicht das Modell". `CREATE INDEX IF NOT EXISTS`
    macht den Aufruf für beide ungefährlich, wenn er ein zweites Mal auf derselben Datei
    läuft — etwa weil die Datei
    schon von Hand hinterlegt war oder noch den alten, einzelnen Index aus einem früheren
    Aufruf trägt: Der zweite Index entsteht dann zusätzlich, nicht anstelle des ersten.

    Bricht sichtbar mit einer deutschen Meldung ab (Regel 13), wenn `path` nicht existiert
    — statt über `sqlite3.connect` still eine leere Datenbankdatei anzulegen — oder wenn
    die Datei beziehungsweise ihr Verzeichnis nicht beschreibbar ist, etwa weil eine von
    Hand hinterlegte Kopie (technik.md §2, „Warum nicht mitgeliefert") das
    Schreibschutz-Attribut trägt. Ohne diese Prüfung reichte die Funktion `sqlite3`s
    englische Fremdmeldung `attempt to write a readonly database` unverändert durch,
    entgegen der Sprachregel.
    """
    if not path.is_file():
        raise ValueError(f"Wörterbuch nicht lesbar: {path}")

    con = sqlite3.connect(path)
    try:
        try:
            con.execute(
                f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {_EXPECTED_TABLE}(written_rep)"
            )
            con.execute(
                f"CREATE INDEX IF NOT EXISTS {INDEX_NAME_NOCASE} "
                f"ON {_EXPECTED_TABLE}(written_rep COLLATE NOCASE)"
            )
            con.commit()
        except sqlite3.DatabaseError as error:
            raise ValueError(
                f"Index auf {path} konnte nicht angelegt werden: {error}. Datei oder "
                "Verzeichnis schreibgeschützt — Schreibrecht geben oder eine beschreibbare "
                "Kopie hinterlegen."
            ) from error
    finally:
        con.close()


def _validate_schema(path: Path) -> None:
    """Bricht sichtbar ab (Regel 13), wenn `path` keine lesbare SQLite-Datenbank mit der
    Tabelle `translation`, deren für `candidates` nötigen Spalten und einer plausiblen
    Zeilenzahl ist — sonst bliebe eine abgebrochene, leere oder falsche Datei unbemerkt als
    gültiges Wörterbuch liegen. `PRAGMA table_info` allein liest nur das Schema (Seite 1);
    eine schemarichtige, aber leere oder stark gekürzte Tabelle bestünde ohne die
    Zeilenzahlprüfung trotzdem. Was diese Prüfung leistet und was nicht: technik.md §2,
    „Keine Prüfsumme, weil WikDict keine veröffentlicht"."""
    try:
        con = sqlite3.connect(path)
        try:
            columns = {row[1] for row in con.execute(f"PRAGMA table_info({_EXPECTED_TABLE})")}
            row_count = (
                con.execute(f"SELECT COUNT(*) FROM {_EXPECTED_TABLE}").fetchone()[0]
                if columns
                else 0
            )
        finally:
            con.close()
    except sqlite3.DatabaseError as error:
        raise ValueError(f"{path} ist keine lesbare SQLite-Datenbank: {error}") from error

    if not columns:
        raise ValueError(
            f'{path} enthält keine Tabelle "{_EXPECTED_TABLE}" — kein WikDict-Wörterbuch '
            "im erwarteten Schema."
        )
    missing = _EXPECTED_COLUMNS - columns
    if missing:
        raise ValueError(
            f'{path}: Tabelle "{_EXPECTED_TABLE}" fehlen die Spalten '
            f"{', '.join(sorted(missing))} — kein WikDict-Wörterbuch im erwarteten Schema."
        )
    if row_count < _MIN_TRANSLATION_ROWS:
        raise ValueError(
            f'{path}: Tabelle "{_EXPECTED_TABLE}" enthält nur {row_count} Zeilen, erwartet '
            f"mindestens {_MIN_TRANSLATION_ROWS} — vermutlich ein abgebrochener oder "
            "beschädigter Bezug."
        )


def _download(url: str, target: Path) -> None:
    """Lädt `url` blockweise nach `target` und bricht sichtbar ab (Regel 13), wenn der
    Server keine `Content-Length` nennt oder weniger Bytes ankommen, als er angekündigt
    hat — ein abgebrochener Bezug bliebe sonst als kürzere, aber scheinbar vollständige
    Datei liegen. `response.read(n)` meldet ein solches vorzeitiges Verbindungsende bei
    blockweisem Lesen nicht selbst als Fehler, anders als bei `response.read()` ohne
    Grenze — die Prüfung unten ist deshalb notwendig, nicht nur zusätzliche Vorsicht.
    Fehlt `Content-Length` selbst (`Transfer-Encoding: chunked`, eine HTTP/1.0-Antwort mit
    Verbindungsende als Ende, ein Zwischenspeicher davor), ist die Vollständigkeit erst
    recht nicht prüfbar; das gilt hier ebenfalls als Fehlschlag, nicht als übersprungener
    Sonderfall."""
    try:
        with urllib.request.urlopen(url) as response:
            expected_length = response.headers.get("Content-Length")
            if expected_length is None:
                raise ValueError(
                    f"Bezug von {url}: Server nennt keine Content-Length, "
                    "Vollständigkeit nicht prüfbar."
                )
            expected = int(expected_length)
            written = 0
            with target.open("wb") as fh:
                while chunk := response.read(1024 * 1024):
                    fh.write(chunk)
                    written += len(chunk)
    except urllib.error.URLError as error:
        raise ValueError(f"Bezug von {url} fehlgeschlagen: {error}") from error

    if written != expected:
        raise ValueError(
            f"Bezug von {url} abgebrochen: erwartet {expected} Bytes, erhalten {written}."
        )


def fetch_dictionary(path: Path, *, url: str = DICTIONARY_URL) -> None:
    """Erstbezug der Wörterbuchdatei (bauplan.md T6).

    Existiert `path` bereits — heruntergeladen oder von Hand hinterlegt (technik.md §2,
    „Warum nicht mitgeliefert") —, wird nicht neu geladen, aber Schema und Index werden
    trotzdem geprüft beziehungsweise angelegt: Auch eine von Hand kopierte WikDict-Datei
    bringt den Index nicht mit (technik.md §3, „Der Engpass ist das Nachschlagen, nicht das
    Modell"). Fehlt sie, wird sie
    von `url` bezogen und geprüft — vollständig (`Content-Length` in `_download`), im
    erwarteten Schema und mit plausibler Zeilenzahl (`_validate_schema`) — und erst danach
    indiziert und an `path` sichtbar. Bis dahin liegt sie unter einer Nebendatei (`path`
    mit Endung `.part`), damit eine unvollständige oder ungültige Datei in keinem
    Fehlerfall als gültiges Wörterbuch liegen bleibt (Regel 13): Ein Fehlschlag räumt die
    Nebendatei auf und bricht danach mit einer deutschen Meldung ab, statt ihn nur zu
    protokollieren. Ohne veröffentlichten Referenzwert prüft dieser Bezug keine
    Prüfsumme — Begründung und was die Prüfungen stattdessen leisten: technik.md §2,
    „Keine Prüfsumme, weil WikDict keine veröffentlicht".
    """
    if path.is_file():
        _validate_schema(path)
        ensure_index(path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".part")
    try:
        _download(url, tmp_path)
        _validate_schema(tmp_path)
        ensure_index(tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    tmp_path.replace(path)
