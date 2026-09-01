"""Triage über die Tastatur — die eigentliche Bedienung von Schritt 4 (konzept.md §4).

Aufgabe
-------
Führt den Nutzer durch **eine** der beiden getrennten Listen aus `libreverbum.pipeline.
TriageResolution` (Einzelwörter oder Wendungen, siehe „Festlegung: getrennte Decksel"
unten) mit den Erleichterungen aus konzept.md §4: Sammelaktion „ab hier kenne ich alles"
(`libreverbum.triage.bulk_mark`, hier als `_bulk_phase`) und Anzeige samt Tastatureingabe.
Die restliche Rechnung — Profilabgleich, Häufigkeitssortierung, Bedeutungsauflösung durch
das Modell, Wortobergrenze — liegt seit der zweiten T16-Durchsicht (Befund schwer 1) im
Kern: `libreverbum.pipeline.resolve_triage_entries` liefert die fertige, höchstens
`WORD_LIMIT`/`EXPRESSION_LIMIT` lange Liste, **eine** Bedeutung je Eintrag statt einer
Auswahlliste. `run_triage_pass` bekommt dieses Ergebnis (`resolution`) und macht daraus nur
noch Anzeige, Tastatureingabe und die daraus folgenden Schreibzugriffe aufs Profil
(`libreverbum.profile.record_event`) samt Kartenerzeugung (`libreverbum.anki.
new_card_guid`) — kein Modellaufruf mehr an dieser Stelle, die Bedeutung steht bereits fest.

Warum die Auflösung nicht mehr hier liegt (Befund schwer 1, zweite T16-Durchsicht)
------------------------------------------------------------------------------------
Vor dieser Behebung bucht(e) dieses Modul „kenne ich" auf `candidates[0]`
(`_representative_sense`, entfallen), während der Vorfilter **alle** Kandidaten `KNOWN`
verlangte (`_is_known`, ebenfalls entfallen) — Schreib- und Leseseite maßen an
verschiedenen Bedeutungen. Da 65,8 % der Grundformen eines Kapitels mehrdeutig sind
(technik.md §3, Nachtrag 18.08.2026), verfehlte der Vorfilter die meisten bereits bekannten
Wörter: Abnahmekriterium 6 „beim zweiten Durchlauf … nicht erneut abgefragt" galt nur
zufällig, für eindeutige Wörter wie `watch`. Die Auflösung, welche Bedeutung ein Kapitel
tatsächlich meint, braucht das Modell (`translation.choose_sense`) — und *das* ist Sache des
Kerns (technik.md §7: „`translation` als einziger Ort mit Modellzugriff"), nicht der
Oberfläche. `pipeline.resolve_triage_entries` löst deshalb **vor** der Triage auf, wie es
konzept.md, Nachtrag 17.08.2026 verlangt: „Die Triage kommt nach dem Beschaffen der
Bedeutungen." Schreib- und Leseseite sind seither dieselbe Stelle: `resolve_triage_entries`
prüft den Kenntnisstand der aufgelösten Bedeutung selbst (`pipeline._all_candidates_known`
für den Vorfilter, ein frischer `profile.compare_chapter_vocabulary`-Aufruf je aufgelöster
Bedeutung danach), und dieses Modul bucht hier nur noch genau diese eine Bedeutung
(`entry.sense`), nie mehr eine geratene erste.

Festlegung: getrennte Decksel für Wörter und Wendungen
-------------------------------------------------------
Entschieden am 21.08.2026 (Auftrag zu T16), von hier aus übernommen: Einzelwörter und
Wendungen laufen als **zwei** vollständig getrennte Durchläufe von `resolve_triage_entries`
und `run_triage_pass`, nicht als eine gemeinsame, nach Häufigkeit gemischte Liste.
Begründung:

- Die Häufigkeitsskalen sind nicht vergleichbar. Ein häufiges Wort kommt im Kapitel
  fünfzigmal vor, eine Wendung ein- bis zweimal. In einer gemeinsamen, nach Häufigkeit
  sortierten Liste kämen die rund 213 Wendungen je Kapitel nie unter die ersten 25 — sie
  fielen still weg, derselbe Befund wie beim T15-Durchstich vor dessen Behebung, bei dem
  sie im Ergebnis ganz fehlten
- Eine Wendung, die zweimal vorkommt, ist mehr wert als ein Wort, das zweimal vorkommt:
  Sie lässt sich nicht aus ihren Teilen erschließen
- Abnahmekriterium 3 verlangt zwei Redewendungen in der Handstichprobe (konzept.md).
  Ohne eigenen Deckel wäre das dem Zufall überlassen

Die Wortobergrenze bleibt bei 25 (konzept.md §4, `WORD_LIMIT` unten) — die Abnahme T17 hat
sie weder gestrichen noch zur Einstellung gemacht, sondern in der Praxis beurteilt
(konzept.md §4, „Nachtrag 26.08.2026 — die Obergrenze bleibt bei 25"). `EXPRESSION_LIMIT`
ist daraus **abgeleitet**, siehe der Kommentar dort.

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
Ablauf"). `resolution` ist das Ergebnis von `libreverbum.pipeline.resolve_triage_entries`
für dieselbe Liste — `cli.main` ruft diese Funktion vor `run_triage_pass` auf, mit
derselben `con` und demselben `limit` (`WORD_LIMIT`/`EXPRESSION_LIMIT`). `read_line`/
`write_line` sind austauschbar (Vorgabe `input`/`cli.display.safe_print`) — Tests ersetzen
beide, statt die echte Konsole zu bedienen (dokumentation.md §5: „Prüfe die
Entscheidungen, die dabei fallen, nicht die Bildschirmausgabe Zeichen für Zeichen").

Liefert
-------
`run_triage_pass` die Liste der `Card`-Objekte aus jeder „will ich lernen"-Entscheidung.
Jede Entscheidung — auch „kenne ich" und „überspringen" — schreibt sofort ein `Event`
ins Profil; ein Abbruch mitten in der Liste (`q`) verliert damit nur die noch nicht
gestellten Entscheidungen, keine bereits getroffenen.

**Nicht** jeder Eintrag lässt sich in jeder Kartenrichtung lernen: Was `anki.card_obstacle`
zurückweist — ein Wort ohne Wörterbucheintrag unter `de_en`, eine Wortform ohne Wortgrenze
im Belegsatz unter `cloze` — wird hier gar nicht erst zur Karte, sondern führt zu einer
erneuten Frage mit dem Grund als Meldung. Ohne diese Vorabfrage bräche erst der Export ab,
nach vollständig durchlaufener Triage und um den Preis aller übrigen Karten (Befund mittel,
Durchsicht 35736a9).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime

from libreverbum import anki, dictionary, pipeline, printout, profile, triage
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
from libreverbum.profile import VocabularyStatus

ReadLine = Callable[[str], str]
WriteLine = Callable[[str], None]

# konzept.md §4: „Obergrenze pro Kapitel — maximal 25 neue Wörter". Bleibt fest — die Abnahme
# T17 hat die Zahl beurteilt und bestätigt (konzept.md §4, „Nachtrag 26.08.2026 — die
# Obergrenze bleibt bei 25") — kein Schalter dafür (dokumentation.md §4 Regel 14).
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


def _entry_lines(entry: pipeline.ResolvedEntry) -> list[str]:
    """Anzeige eines Eintrags: Wortform, Wortart, Häufigkeit, Belegsatz und die **eine**
    im Belegsatz gemeinte Bedeutung, wie `pipeline.resolve_triage_entries` sie aufgelöst
    hat (technik.md §3, Nachtrag 18.08.2026: „Die gewählte Bedeutung samt Belegsatz gehört
    also in die Anzeige — das ist Darstellung, keine zweite Entscheidung"). Vor der
    zweiten T16-Durchsicht stand hier stattdessen die volle Auswahlliste des Wörterbuchs,
    ohne Modell-Markierung.

    `VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD` trägt zusätzlich die Kennzeichnung „neue
    Bedeutung eines bekannten Wortes" (konzept.md §5, „Mehrdeutigkeit") — ohne sie sähe
    dieser Eintrag wie ein bereits bekanntes Wort aus, das grundlos erneut auftaucht."""
    occurrence = entry.occurrence
    pos_display = anki.pos_display(occurrence.lemma.pos)
    lines = [f"{occurrence.word_form} ({pos_display}), {occurrence.frequency}x im Kapitel"]
    lines.append(f"  {occurrence.example_sentence}")
    translation_text = entry.sense.translation or entry.sense.wikdict_trans_list or "?"
    line = f"  {dictionary.label(entry.sense)} -> {translation_text}"
    if entry.status is VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD:
        line += " [neue Bedeutung eines bekannten Wortes]"
    lines.append(line)
    return lines


def _bulk_phase(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    ordered: list[Occurrence],
    entries_by_occurrence: dict[Occurrence, pipeline.ResolvedEntry],
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
        pos_display = anki.pos_display(occurrence.lemma.pos)
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
        _record(con, entry.sense, KnowledgeState.KNOWN, Origin.BULK_MARK, book, chapter_number)
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
    entries_by_occurrence: dict[Occurrence, pipeline.ResolvedEntry],
    card_direction: CardDirection,
    read_line: ReadLine,
    write_line: WriteLine,
) -> list[Card]:
    """Fragt `remaining` einzeln ab, in der übergebenen (nach Häufigkeit sortierten)
    Reihenfolge. `q` bricht die restliche Liste ab (Abnahmekriterium 7: „man kann
    jederzeit abbrechen, ohne das Wichtigste zu verpassen") — bereits getroffene
    Entscheidungen bleiben dabei im Profil stehen, ungestellte Fragen hinterlassen kein
    Ereignis und werden beim nächsten Durchlauf erneut gestellt.

    Kein Modellaufruf mehr an dieser Stelle (Befund schwer 1, zweite T16-Durchsicht):
    `entry.sense` ist bereits die im Belegsatz gemeinte Bedeutung
    (`pipeline.resolve_triage_entries`) — „kenne ich", „will ich lernen" und „überspringen"
    buchen und verkarten alle dieselbe eine Bedeutung, statt „kenne ich"/„überspringen" auf
    einer geratenen ersten und nur „will ich lernen" auf der vom Modell gewählten."""
    cards: list[Card] = []
    for occurrence in remaining:
        entry = entries_by_occurrence[occurrence]
        for line in _entry_lines(entry):
            write_line(line)
        while True:
            action = _ask_action(read_line, write_line)
            if action != "learn":
                break
            obstacle = anki.card_obstacle(occurrence, entry.sense, card_direction)
            if obstacle is None:
                break
            # REGEL (dokumentation.md §4 Regel 13): Erneut fragen statt die Entscheidung
            # stillschweigend zu „skip" zu machen — dieselbe Handhabung wie `_ask_action`
            # bei einer unbekannten Eingabe. Der Nutzer soll wissen, warum sein „lernen"
            # nicht angenommen wurde, und selbst zwischen „kenne ich" und „skip" wählen.
            # Der Grund kommt aus `anki` selbst (Befund mittel, Durchsicht 35736a9): Welche
            # Kartenvorlage welches Feld auf die Vorderseite nimmt, weiß der Kern — diese
            # Stelle gäbe sonst für den zweiten Fall (Lückentext ohne Lücke) eine falsche
            # Begründung aus, und vor jener Durchsicht kannte sie ihn überhaupt nicht.
            write_line(obstacle)

        if action == "quit":
            write_line("Abgebrochen.")
            break
        if action == "known":
            _record(con, entry.sense, KnowledgeState.KNOWN, Origin.TRIAGE, book, chapter_number)
        elif action == "learn":
            guid = anki.new_card_guid(occurrence, entry.sense, card_direction)
            cards.append(
                Card(
                    sense=entry.sense,
                    occurrence=occurrence,
                    card_direction=card_direction,
                    guid=guid,
                )
            )
            _record(con, entry.sense, KnowledgeState.LEARNING, Origin.TRIAGE, book, chapter_number)
        else:  # "skip"
            _record(con, entry.sense, KnowledgeState.DEFERRED, Origin.TRIAGE, book, chapter_number)
    return cards


def run_triage_pass(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    resolution: pipeline.TriageResolution,
    label: str,
    card_direction: CardDirection,
    read_line: ReadLine,
    write_line: WriteLine,
) -> list[Card]:
    """Ein vollständiger Triage-Deckel: Meldungen, Sammelaktion, Einzelabfrage — für
    **eine** der beiden Listen aus `pipeline.ChapterVocabulary` (siehe Moduldocstring,
    „Festlegung: getrennte Decksel"), bereits von `pipeline.resolve_triage_entries` zu
    `resolution` aufbereitet: Profilabgleich, Häufigkeitssortierung, Bedeutungsauflösung
    durch das Modell und Wortobergrenze liegen dort, nicht mehr hier (Befund schwer 1,
    zweite T16-Durchsicht).

    Abnahmekriterium 6: „Beim zweiten Durchlauf desselben Kapitels werden die als
    *bekannt* markierten Wörter **nicht erneut** abgefragt — das Profil greift"
    (konzept.md, „Abnahmekriterien"). Erfüllt seit der zweiten T16-Durchsicht
    `pipeline.resolve_triage_entries` selbst: Der Vorfilter dort prüft **alle** Kandidaten
    einer Grundform (`pipeline._all_candidates_known`) gegen dieselbe Bedeutung, die auch
    gebucht wird (`entry.sense` in `_individual_phase`/`_bulk_phase`) — vor der Behebung
    bucht(e) dieses Modul „kenne ich" auf `candidates[0]`, während der Vorfilter *alle*
    Kandidaten verlangte, und verfehlte bei 65,8 % mehrdeutigen Grundformen je Kapitel
    (technik.md §3, Nachtrag 18.08.2026) die meisten bereits bekannten Wörter.

    Drei Zählungen und eine Restliste werden gemeldet, nicht verschwiegen (Regel 13): laut
    Vorfilter bereits bekannt (`resolution.known`) und erst nach dem Auflösen als bekannt
    erkannt (`resolution.resolved_known`) in einer gemeinsamen Meldung — beide Wege buchen
    dieselbe Bedeutung als `KNOWN`, nur zu verschiedenen Zeitpunkten im Ablauf, und eine
    getrennte Zahl ohne die andere wäre wieder die Lücke aus Befund mittel, Durchsicht
    46ef37b (im Auftragsbeispiel: „4 bereits bekannt" statt der tatsächlichen 25).
    Übersprungene Einträge (`resolution.skipped`, Befund schwer 1, Durchsicht 46ef37b):
    Kandidaten bestanden, aber das Modell wählte „keine passt" — kein Wort, über das der
    Nutzer hätte entscheiden können, deshalb weder Anzeige noch Buchung, nur diese
    Zählung. Noch nicht geprüfte Einträge (`resolution.remaining`, technik.md §12,
    „Blockweise Triage mit Vorladen — entschieden"): der Rest für den nächsten Block —
    die Blockschleife, die ihn erneut vorlegt, ist ein späterer Bauschritt, hier wird er
    nur gezählt und gemeldet."""
    if resolution.known or resolution.resolved_known:
        write_line(
            f"{resolution.known + resolution.resolved_known} {label} laut Profil bereits "
            f"bekannt ({resolution.resolved_known} davon erst nach Auflösen der Bedeutung) "
            "— nicht erneut abgefragt."
        )
    if resolution.skipped:
        write_line(
            f"{resolution.skipped} {label} übersprungen: keine der Wörterbuchbedeutungen "
            "war zuzuordnen."
        )
    if resolution.remaining:
        write_line(f"{len(resolution.remaining)} {label} noch nicht geprüft.")

    entries = resolution.entries
    if not entries:
        return []

    ordered = [entry.occurrence for entry in entries]
    entries_by_occurrence = {entry.occurrence: entry for entry in entries}

    bulk_marked = _bulk_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        ordered=ordered,
        entries_by_occurrence=entries_by_occurrence,
        label=label,
        read_line=read_line,
        write_line=write_line,
    )
    remaining = [occurrence for occurrence in ordered if occurrence not in bulk_marked]
    return _individual_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        remaining=remaining,
        entries_by_occurrence=entries_by_occurrence,
        card_direction=card_direction,
        read_line=read_line,
        write_line=write_line,
    )
