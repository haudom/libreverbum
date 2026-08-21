"""Triage über die Tastatur — die eigentliche Bedienung von Schritt 4 (konzept.md §4).

Aufgabe
-------
Führt den Nutzer durch **eine** der beiden getrennten Listen aus `pipeline.
ChapterVocabulary` (Einzelwörter oder Wendungen, siehe „Festlegung: getrennte Decksel"
unten) mit den Erleichterungen aus konzept.md §4: Häufigkeitssortierung
(`libreverbum.triage.sort_by_frequency`), Sammelaktion „ab hier kenne ich alles"
(`libreverbum.triage.bulk_mark`) und Wortobergrenze
(`libreverbum.triage.defer_beyond_word_limit`). Diese drei Rechenschritte kommen
unverändert aus dem Kern — hier entsteht nur die Bedienung darum: Anzeige, Tastatureingabe
und die daraus folgenden Schreibzugriffe aufs Profil (`libreverbum.profile.record_event`)
und, bei „will ich lernen", der Modellaufruf (`libreverbum.translation.choose_sense`) samt
Kartenerzeugung (`libreverbum.anki.new_card_guid`).

Festlegung: getrennte Decksel für Wörter und Wendungen
-------------------------------------------------------
Entschieden am 21.08.2026 (Auftrag zu T16), von hier aus übernommen: Einzelwörter und
Wendungen laufen als **zwei** vollständig getrennte Durchläufe von `run_triage_pass`,
nicht als eine gemeinsame, nach Häufigkeit gemischte Liste. Begründung:

- Die Häufigkeitsskalen sind nicht vergleichbar. Ein häufiges Wort kommt im Kapitel
  fünfzigmal vor, eine Wendung ein- bis zweimal. In einer gemeinsamen, nach Häufigkeit
  sortierten Liste kämen die rund 213 Wendungen je Kapitel (bauplan.md, T16-Zeile) nie
  unter die ersten 25 — sie fielen still weg, derselbe Befund wie beim T15-Durchstich vor
  dessen Behebung (nacharbeit.md, A19: „213 Wendungen je Kapitel fehlten im Ergebnis")
- Eine Wendung, die zweimal vorkommt, ist mehr wert als ein Wort, das zweimal vorkommt:
  Sie lässt sich nicht aus ihren Teilen erschließen
- Abnahmekriterium 3 verlangt zwei Redewendungen in der Handstichprobe (konzept.md).
  Ohne eigenen Deckel wäre das dem Zufall überlassen

Die Wortobergrenze bleibt bei 25 (konzept.md §4, `WORD_LIMIT` unten) — sie wird laut
bauplan.md, T17-Zeile weder gestrichen noch zur Einstellung gemacht, sondern in der Praxis
beurteilt. `EXPRESSION_LIMIT` ist daraus **abgeleitet**, siehe der Kommentar dort.

Wie die Sammelaktion hier funktioniert
---------------------------------------
`triage.bulk_mark` markiert „alle in der Anzeige davorstehenden Wörter" — das trägt nur
dann etwas, wenn die volle, sortierte Liste **vor** jeder Einzelentscheidung sichtbar ist:
Würde jedes Wort einzeln der Reihe nach abgefragt, wären alle „davorstehenden" Wörter zum
Zeitpunkt der Sammelaktion bereits einzeln entschieden, und die Sammelaktion träfe nie
mehr als das aktuelle Wort — der eine Tastendruck für „hunderte Wörter"
(`entities.Origin`, Docstring zu `BULK_MARK`) bliebe unerreichbar. `run_triage_pass`
zeigt deshalb zuerst die vollständige, nummerierte Liste (`_bulk_phase`) und fragt nach
der letzten Position, bis zu der der Nutzer alles kennt — erst danach beginnt die
Einzelabfrage für den Rest (`_individual_phase`).

Voraussetzungen
---------------
`con` ist eine bereits geöffnete Profilverbindung (`libreverbum.profile.open_profile`);
die Kapitelzeile, die `profile.record_event` als Fremdschlüssel braucht, muss vorher
angelegt sein — `ensure_chapter_row` unten übernimmt das, weil `profile.py` dafür bewusst
keine eigene Schreibfunktion anbietet (Regel 14, siehe Bericht zu T16, „Beobachtungen zum
Ablauf"). `read_line`/`write_line` sind austauschbar (Vorgabe `input`/`cli.display.
safe_print`) — Tests ersetzen beide, statt die echte Konsole zu bedienen
(dokumentation.md §5: „Prüfe die Entscheidungen, die dabei fallen, nicht die
Bildschirmausgabe Zeichen für Zeichen").

Liefert
-------
`run_triage_pass` die Liste der `Card`-Objekte aus jeder „will ich lernen"-Entscheidung.
Jede Entscheidung — auch „kenne ich" und „überspringen" — schreibt sofort ein `Event`
ins Profil; ein Abbruch mitten in der Liste (`q`) verliert damit nur die noch nicht
gestellten Entscheidungen, keine bereits getroffenen.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from libreverbum import anki, dictionary, pipeline, printout, profile, translation, triage
from libreverbum.entities import (
    Book,
    Card,
    CardDirection,
    Event,
    KnowledgeState,
    Occurrence,
    Origin,
    Sense,
)

ReadLine = Callable[[str], str]
WriteLine = Callable[[str], None]

# konzept.md §4: „Obergrenze pro Kapitel — maximal 25 neue Wörter". Bleibt fest (bauplan.md,
# T17-Zeile: „erwogen zu streichen und unverändert gelassen … zeigt erst der erste echte
# Durchlauf") — kein Schalter dafür (dokumentation.md §4 Regel 14).
WORD_LIMIT = 25

# Herleitung, nicht geraten: Die Druckseite fasst printout.MAX_ENTRIES Einträge (technik.md
# §8c, „Gemessene Ergebnisse: »passt auf ein Blatt« ist gedeckt" — 36, echte Arial-Metrik
# gegen tools/en-de.sqlite3). Was die Triage durchlässt, muss zusammen auf dieses eine
# Blatt passen; WORD_LIMIT beansprucht 25 davon, der Rest bleibt für die Wendungen. Als
# Rechnung statt Literal notiert: Ändert sich WORD_LIMIT oder printout.MAX_ENTRIES, wandert
# diese Zahl automatisch mit, statt still zu veralten.
EXPRESSION_LIMIT = printout.MAX_ENTRIES - WORD_LIMIT


def ensure_chapter_row(
    con: sqlite3.Connection, book: Book, chapter_number: int, title: str
) -> None:
    """Legt die Kapitelzeile an, die `event.book_id, event.chapter_number` als
    Fremdschlüssel auf `chapter(book_id, number)` braucht (`profile._SCHEMA`).

    `profile.py` bietet dafür bewusst keine eigene Schreibfunktion (dokumentation.md §4
    Regel 14) — dieselbe Handhabung wie `tests/test_pipeline.py`, `_record_known`, dort
    ausdrücklich als Vorlage für „ein künftiger Schreibzugriff aus pipeline (nach T11)"
    benannt. Siehe Bericht zu T16, „Beobachtungen zum Ablauf": Der Kern erzwingt diese
    Kopplung nicht über seine öffentliche Schnittstelle, ein Aufrufer muss sie kennen.
    """
    book_id = profile.ensure_book(con, book)
    con.execute(
        "INSERT OR IGNORE INTO chapter (book_id, number, title) VALUES (?, ?, ?)",
        (book_id, chapter_number, title),
    )
    con.commit()


def _representative_sense(occurrence: Occurrence, candidates: Sequence[Sense]) -> Sense:
    """Die Hauptbedeutung für Entscheidungen ohne Karte (`dictionary.candidates` liefert
    nach `score` absteigend, Regel 1 — der erste Kandidat ist die Hauptbedeutung) — oder
    ein unsicherer Platzhalter ohne Wörterbucheintrag, dieselbe Rückfallregel wie in
    `translation.choose_sense` bei leerer Auswahlliste (Regel 11).

    Nur für „kenne ich", „überspringen" und die Sammelaktion: Eine dieser drei
    Entscheidungen braucht eine Bedeutung, an der das Profil die Kenntnis festmacht, aber
    keine kontextgetreue Übersetzung (die nur eine Karte trägt) — bei „will ich lernen"
    entscheidet stattdessen das Modell.
    """
    if not candidates:
        return Sense(lemma=occurrence.lemma, uncertain=True)
    return candidates[0]


def _record(
    con: sqlite3.Connection,
    sense: Sense,
    knowledge_state: KnowledgeState,
    origin: Origin,
    book: Book,
    chapter_number: int,
) -> None:
    profile.record_event(
        con,
        Event(
            sense=sense,
            knowledge_state=knowledge_state,
            origin=origin,
            timestamp=datetime.now(UTC),
            book=book,
            chapter_number=chapter_number,
        ),
    )


def _entry_lines(entry: pipeline.VocabularyEntry) -> list[str]:
    """Anzeige eines Eintrags: Wortform, Wortart, Häufigkeit, Belegsatz und die
    Auswahlliste (E10, bauplan.md Tor 0: „Die gewählte Bedeutung gehört aber in die
    Anzeige der Triage, nicht bloß das Wort") — hier, in der Standardstellung
    „Wörterbuch" (konzept.md §4), die volle Liste der möglichen Bedeutungen ohne
    Modell-Markierung; die endgültige, kontextgetreue Bedeutung entsteht erst bei „will
    ich lernen" (`translation.choose_sense`)."""
    occurrence = entry.occurrence
    pos_display = occurrence.lemma.pos or "MWE"
    lines = [f"{occurrence.word_form} ({pos_display}), {occurrence.frequency}x im Kapitel"]
    lines.append(f"  {occurrence.example_sentence}")
    if entry.candidates:
        for number, sense in enumerate(entry.candidates, start=1):
            translation_text = sense.wikdict_trans_list or "?"
            lines.append(f"  {number}. {dictionary.label(sense)} -> {translation_text}")
    else:
        lines.append("  (kein Wörterbucheintrag)")
    return lines


def _bulk_phase(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    ordered: list[Occurrence],
    entries_by_occurrence: dict[Occurrence, pipeline.VocabularyEntry],
    label: str,
    read_line: ReadLine,
    write_line: WriteLine,
) -> set[Occurrence]:
    """Sammelaktion „ab hier kenne ich alles" (konzept.md §4) — siehe Moduldocstring,
    „Wie die Sammelaktion hier funktioniert": zeigt `ordered` einmal vollständig und
    nummeriert, fragt nach der letzten Position, bis zu der alles bekannt ist, und
    markiert genau diesen Ausschnitt über `triage.bulk_mark`.

    Liefert die bulk-markierten Vorkommen, damit `run_triage_pass` sie aus der
    anschließenden Einzelabfrage herausnimmt."""
    if not ordered:
        return set()

    write_line(f"-- {label}: {len(ordered)} --")
    for number, occurrence in enumerate(ordered, start=1):
        pos_display = occurrence.lemma.pos or "MWE"
        write_line(f"  {number}. {occurrence.word_form} ({pos_display})")

    answer = read_line(
        f"Sammelaktion — bis zu welcher Nummer kennst du alles? (1-{len(ordered)}, Enter = keine) "
    ).strip()
    if not answer:
        return set()

    try:
        position = int(answer)
    except ValueError:
        write_line("Keine Zahl erkannt — Sammelaktion übersprungen.")
        return set()
    if not 1 <= position <= len(ordered):
        write_line("Außerhalb der Liste — Sammelaktion übersprungen.")
        return set()

    selected = ordered[position - 1]
    bulk = triage.bulk_mark(ordered, selected)
    for occurrence in bulk:
        entry = entries_by_occurrence[occurrence]
        sense = _representative_sense(occurrence, entry.candidates)
        _record(con, sense, KnowledgeState.KNOWN, Origin.BULK_MARK, book, chapter_number)
    write_line(f"{len(bulk)} als bekannt gebucht.")
    return set(bulk)


_ACTIONS = {
    "k": "known",
    "kenne": "known",
    "l": "learn",
    "lernen": "learn",
    "s": "skip",
    "skip": "skip",
    "": "skip",
    "q": "quit",
    "quit": "quit",
}


def _ask_action(read_line: ReadLine, write_line: WriteLine) -> str:
    """Fragt so lange nach, bis eine gültige Antwort steht — eine unbekannte Eingabe
    verwirft keine Entscheidung stillschweigend als „skip" (Regel 13), sondern führt zu
    einer erneuten Frage."""
    while True:
        raw = read_line("[k]enne ich  [l]ernen  [s]kip  [q]uit > ").strip().lower()
        action = _ACTIONS.get(raw)
        if action is not None:
            return action
        write_line("Ungültige Eingabe — k, l, s oder q erwartet.")


def _individual_phase(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    remaining: list[Occurrence],
    entries_by_occurrence: dict[Occurrence, pipeline.VocabularyEntry],
    card_direction: CardDirection,
    get_model_name: Callable[[], str],
    model_url: str,
    read_line: ReadLine,
    write_line: WriteLine,
) -> list[Card]:
    """Fragt `remaining` einzeln ab, in der übergebenen (nach Häufigkeit sortierten)
    Reihenfolge. `q` bricht die restliche Liste ab (Abnahmekriterium 7: „man kann
    jederzeit abbrechen, ohne das Wichtigste zu verpassen") — bereits getroffene
    Entscheidungen bleiben dabei im Profil stehen, ungestellte Fragen hinterlassen kein
    Ereignis und werden beim nächsten Durchlauf erneut gestellt."""
    cards: list[Card] = []
    for occurrence in remaining:
        entry = entries_by_occurrence[occurrence]
        for line in _entry_lines(entry):
            write_line(line)
        action = _ask_action(read_line, write_line)

        if action == "quit":
            write_line("Abgebrochen.")
            break
        if action == "known":
            sense = _representative_sense(occurrence, entry.candidates)
            _record(con, sense, KnowledgeState.KNOWN, Origin.TRIAGE, book, chapter_number)
        elif action == "learn":
            # REGEL (dokumentation.md §4 Regel 11, „Das Modell wählt aus einer Liste"):
            # Nur hier, bei einer Karte, die der Nutzer wiederholt sehen wird, lohnt der
            # Modellaufruf für eine kontextgetreue Übersetzung (Abnahmekriterium 3).
            # Ohne Auswahlliste bleibt `get_model_name()` dabei ungerufen: Python wertet
            # Funktionsargumente vor dem Aufruf aus, und translation.choose_sense selbst
            # bräuchte den Modellnamen bei leerer Liste nie — ein Kandidat ganz ohne
            # Wörterbucheintrag darf eine Triage-Sitzung deshalb nicht zwingen, den
            # Modellserver überhaupt zu erreichen (Regel 11, „Kandidaten ohne
            # Wörterbucheintrag werden uncertain markiert").
            if entry.candidates:
                sense = translation.choose_sense(
                    url=model_url,
                    model_name=get_model_name(),
                    occurrence=occurrence,
                    sense_candidates=entry.candidates,
                )
            else:
                sense = Sense(lemma=occurrence.lemma, uncertain=True)
            _record(con, sense, KnowledgeState.LEARNING, Origin.TRIAGE, book, chapter_number)
            guid = anki.new_card_guid(occurrence, sense, card_direction)
            cards.append(
                Card(sense=sense, occurrence=occurrence, card_direction=card_direction, guid=guid)
            )
        else:  # "skip"
            sense = _representative_sense(occurrence, entry.candidates)
            _record(con, sense, KnowledgeState.DEFERRED, Origin.TRIAGE, book, chapter_number)
    return cards


def run_triage_pass(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    entries: Sequence[pipeline.VocabularyEntry],
    limit: int,
    label: str,
    card_direction: CardDirection,
    get_model_name: Callable[[], str],
    model_url: str,
    read_line: ReadLine,
    write_line: WriteLine,
) -> list[Card]:
    """Ein vollständiger Triage-Deckel: Häufigkeitssortierung, Wortobergrenze,
    Sammelaktion, Einzelabfrage — für **eine** der beiden Listen aus
    `pipeline.ChapterVocabulary` (siehe Moduldocstring, „Festlegung: getrennte
    Decksel"). `limit` ist `WORD_LIMIT` für `entries` beziehungsweise
    `EXPRESSION_LIMIT` für `expressions` (`cli.main`)."""
    occurrences = [entry.occurrence for entry in entries]
    entries_by_occurrence = {entry.occurrence: entry for entry in entries}

    ordered = triage.sort_by_frequency(occurrences)
    deferred = triage.defer_beyond_word_limit(occurrences, limit)
    in_scope = ordered[: len(ordered) - len(deferred)]

    if deferred:
        write_line(f"{len(deferred)} {label} zurückgestellt (Obergrenze {limit}).")
    if not in_scope:
        return []

    bulk_marked = _bulk_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        ordered=in_scope,
        entries_by_occurrence=entries_by_occurrence,
        label=label,
        read_line=read_line,
        write_line=write_line,
    )
    remaining = [occurrence for occurrence in in_scope if occurrence not in bulk_marked]
    return _individual_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        remaining=remaining,
        entries_by_occurrence=entries_by_occurrence,
        card_direction=card_direction,
        get_model_name=get_model_name,
        model_url=model_url,
        read_line=read_line,
        write_line=write_line,
    )
