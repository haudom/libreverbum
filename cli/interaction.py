"""Triage über die Tastatur — die eigentliche Bedienung von Schritt 4 (konzept.md §4).

Aufgabe
-------
Führt den Nutzer durch **eine** der beiden getrennten Listen aus `libreverbum.pipeline.
TriageResolution` (Einzelwörter oder Wendungen, siehe „Festlegung: getrennte Decksel"
unten) mit den Erleichterungen aus konzept.md §4: Sammelaktion „ab hier kenne ich alles"
(`libreverbum.triage.bulk_mark`, hier als `_bulk_phase`) und Anzeige samt Tastatureingabe.
Die restliche Rechnung — Profilabgleich, Häufigkeitssortierung, Bedeutungsauflösung durch
das Modell, Blockgröße — liegt seit der zweiten T16-Durchsicht (Befund schwer 1) im Kern:
`libreverbum.pipeline.resolve_triage_entries` liefert die fertige, höchstens
`WORD_BLOCK_SIZE`/`EXPRESSION_BLOCK_SIZE` lange Liste, **eine** Bedeutung je Eintrag statt
einer Auswahlliste. `run_triage_pass` bekommt dieses Ergebnis (`resolution`) und macht
daraus nur noch Anzeige, Tastatureingabe und die daraus folgenden Schreibzugriffe aufs
Profil (`libreverbum.profile.record_event`) samt Kartenerzeugung (`libreverbum.anki.
new_card_guid`) — kein Modellaufruf mehr an dieser Stelle, die Bedeutung steht bereits fest.
`run_triage_pass` ist damit **ein Block**. Die Blockschleife selbst — nach jedem
vollständig durchgeklickten Block die Fortsetzungsfrage stellen und bei „ja" mit
`resolution.remaining` weitermachen — ist `run_triage_blocks`, seit Bauschritt 2/4 der
blockweisen Triage (technik.md §12, „Blockweise Triage mit Vorladen — entschieden"). Seit
Bauschritt 3/4 entsteht der nächste Block dabei **im Hintergrund**, während der Nutzer den
aktuellen durchentscheidet (technik.md §12, „Vorladen: der nächste Block entsteht, während
der Nutzer entscheidet") — `run_triage_blocks` nimmt dafür zwei Rückrufe entgegen,
`resolve_visible_block` (mit Fortschrittsanzeige, nur für den allerersten Block, den der
Nutzer wirklich abwartet) und `resolve_silent_block` (ohne jede Ausgabe, für jeden
vorgeladenen Folgeblock — siehe `_BlockPrefetch` unten).

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

Aus der Wortobergrenze ist seit dem 01.09.2026 eine Blockgröße geworden (konzept.md §4,
„Nachtrag 01.09.2026 — aus der Obergrenze ist eine Blockgröße geworden"): `WORD_BLOCK_SIZE`
bleibt bei 25 — die Abnahme T17 hat die Zahl weder gestrichen noch zur Einstellung gemacht,
sondern in der Praxis beurteilt und bestätigt (konzept.md §4, „Nachtrag 26.08.2026") —, aber
sie begrenzt nichts mehr, sie portioniert. `EXPRESSION_BLOCK_SIZE` ist ein eigenes Literal
(11), siehe der Kommentar dort und technik.md §12, „Was die Blockgrößen bedeuten — und
warum 11 bleibt".

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

Das gilt seit der blockweisen Triage **je Block**: Jeder Block ist ein eigener Aufruf von
`run_triage_pass` mit seiner eigenen vollständigen, nummerierten Liste und seiner eigenen
Sammelaktion (technik.md §12, „Warum Blöcke und kein Nachrücken Platz für Platz"). Ein
Eintrag, der erst während der laufenden Einzelabfrage angehängt würde, bliebe für die
Sammelaktion unerreichbar — genau das leistet die Blockgrenze aus `run_triage_blocks`, statt
Einzelwörter Platz für Platz nachrücken zu lassen.

Voraussetzungen
---------------
`con` ist eine bereits geöffnete Profilverbindung (`libreverbum.profile.open_profile`);
die Kapitelzeile, die `profile.record_event` als Fremdschlüssel braucht, muss vorher
angelegt sein — `ensure_chapter_row` unten übernimmt das, weil `profile.py` dafür bewusst
keine eigene Schreibfunktion anbietet (Regel 14, siehe Bericht zu T16, „Beobachtungen zum
Ablauf"). `resolution` ist das Ergebnis von `libreverbum.pipeline.resolve_triage_entries`
für dieselbe Liste — `run_triage_blocks` unten ruft dafür `resolve_visible_block` (für den
ersten Block) beziehungsweise `resolve_silent_block` (für jeden vorgeladenen Folgeblock;
in `cli.main` die beiden Fortschritts-Helfer um `resolve_triage_entries`, mit
`WORD_BLOCK_SIZE`/`EXPRESSION_BLOCK_SIZE` als `limit`) auf. Der Hauptfaden verwendet dafür
weiterhin dieselbe `con` wie zum Schreiben der Triage-Entscheidungen; `resolve_silent_block`
läuft dagegen im Hintergrundfaden und öffnet dafür **seine eigene** Profilverbindung
(technik.md §12, Festlegung 1) — welche das ist, bleibt Sache des Rückrufs in `cli.main`,
nicht dieses Moduls. `read_line`/`write_line` sind austauschbar (Vorgabe
`input`/`cli.display.safe_print`) — Tests ersetzen beide, statt die echte Konsole zu
bedienen (dokumentation.md §5: „Prüfe die Entscheidungen, die dabei fallen, nicht die
Bildschirmausgabe Zeichen für Zeichen").

Liefert
-------
`run_triage_pass` ein `TriagePass`: die `Card`-Objekte aus jeder „will ich lernen"-
Entscheidung **dieses einen Blocks**, dazu `aborted` — wahr, wenn die Einzelabfrage mit `q`
abgebrochen wurde. Jede Entscheidung — auch „kenne ich" und „überspringen" — schreibt
sofort ein `Event` ins Profil; ein Abbruch mitten in der Liste verliert damit nur die noch
nicht gestellten Entscheidungen dieses Blocks, keine bereits getroffenen.

`run_triage_blocks` liefert die `Card`-Objekte **aller** durchlaufenen Blöcke als eine
flache Liste. Sie ruft `resolve_silent_block` erneut mit `resolution.remaining` auf, bis
entweder nichts mehr aussteht, die Einzelabfrage mit `q` abgebrochen wurde (dann **ohne**
Fortsetzungsfrage) oder der Nutzer die Fortsetzungsfrage verneint — Vorgabe bei Enter ist
„nein", dieselbe Handhabung wie bei der Sammelaktion (Regel 13).

**Nicht** jeder Eintrag lässt sich in jeder Kartenrichtung lernen: Was `anki.card_obstacle`
zurückweist — ein Wort ohne Wörterbucheintrag unter `de_en`, eine Wortform ohne Wortgrenze
im Belegsatz unter `cloze` — wird hier gar nicht erst zur Karte, sondern führt zu einer
erneuten Frage mit dem Grund als Meldung. Ohne diese Vorabfrage bräche erst der Export ab,
nach vollständig durchlaufener Triage und um den Preis aller übrigen Karten (Befund mittel,
Durchsicht 35736a9).
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from libreverbum import anki, dictionary, pipeline, profile, triage
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

# konzept.md §4, „Nachtrag 01.09.2026 — aus der Obergrenze ist eine Blockgröße geworden":
# WORD_BLOCK_SIZE beschränkt nichts mehr, sie portioniert. Die Zahl selbst (25) ist beurteilt
# und bestätigt (konzept.md §4, „Nachtrag 26.08.2026 — die Obergrenze bleibt bei 25") — kein
# Schalter dafür (dokumentation.md §4 Regel 14).
WORD_BLOCK_SIZE = 25

# technik.md §12, „Was die Blockgrößen bedeuten — und warum 11 bleibt": Wendungen sind
# seltener als Wörter (rund 213 Kandidaten je Kapitel gegen rund 1.400, „Messung:
# Mehrwortausdrücke"), sie stehen im Ablauf hinter dem Wortdurchlauf, und ein zweiter Block
# von 25 hielte den Nutzer dort länger fest, als er nach den Wörtern noch will. Literal statt
# Herleitung — die frühere Rechnung `printout.MAX_ENTRIES - WORD_LIMIT` trägt nicht mehr,
# seit die Druckseite umbricht statt abzubrechen (technik.md §12, „Folge: die Druckseite
# bricht um, statt abzubrechen").
EXPRESSION_BLOCK_SIZE = 11


@dataclass(frozen=True)
class TriagePass:
    """Ergebnis **eines** Blocks (`run_triage_pass`): die dabei erzeugten Karten, dazu
    `aborted` — wahr, wenn die Einzelabfrage (`_individual_phase`) mit `q` abgebrochen
    wurde. `run_triage_blocks` unten braucht diese Unterscheidung, um nach einem Abbruch
    die Fortsetzungsfrage zu **unterlassen** — ein `list[Card]` allein sagt nicht, ob der
    Block vollständig durchgeklickt oder vorzeitig verlassen wurde.

    `unasked` (Befund 1/9, Durchsicht 1cfb1e4): wie viele der in **diesem** Block bereits
    angezeigten Einträge nach einem Abbruch mit `q` nicht mehr entschieden wurden — 0,
    wenn der Block vollständig durchgeklickt oder gar nicht abgebrochen wurde.
    `run_triage_blocks` braucht diese Zahl, weil `resolution.remaining` allein nur den
    Rest für den *nächsten* Block zählt: Bricht der Nutzer mitten im laufenden Block ab,
    bleiben dessen eigene, noch nicht gestellte Einträge sonst ungezählt (Befund 9) — im
    Auftragsbeispiel „1310 Wörter noch nicht geprüft" statt tatsächlich 1334."""

    cards: list[Card]
    aborted: bool
    unasked: int = 0


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
    block_number: int,
    read_line: ReadLine,
    write_line: WriteLine,
) -> set[Occurrence]:
    """Sammelaktion „ab hier kenne ich alles" (konzept.md §4) — siehe Moduldocstring,
    „Wie die Sammelaktion hier funktioniert": zeigt `ordered` einmal vollständig und
    nummeriert, fragt nach der letzten Position, bis zu der alles bekannt ist, und
    markiert genau diesen Ausschnitt über `triage.bulk_mark`.

    Liefert die bulk-markierten Vorkommen, damit `run_triage_pass` sie aus der
    anschließenden Einzelabfrage herausnimmt.

    Die Kopfzeile nennt ab dem zweiten Block dessen Nummer (`block_number`) — sonst
    verliert ein Nutzer nach der dritten Fortsetzungsfrage die Orientierung. Beim ersten
    Block bleibt sie unverändert: Eine Gesamtzahl an Blöcken steht ohnehin nie fest."""
    if not ordered:
        return set()

    heading = f"{label} (Block {block_number})" if block_number > 1 else label
    write_line(f"-- {heading}: {len(ordered)} --")
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
    to_ask: list[Occurrence],
    entries_by_occurrence: dict[Occurrence, pipeline.ResolvedEntry],
    card_direction: CardDirection,
    read_line: ReadLine,
    write_line: WriteLine,
) -> tuple[list[Card], bool, int]:
    """Fragt `to_ask` einzeln ab, in der übergebenen (nach Häufigkeit sortierten)
    Reihenfolge. `q` bricht die restliche Liste ab (Abnahmekriterium 7: „man kann
    jederzeit abbrechen, ohne das Wichtigste zu verpassen") — bereits getroffene
    Entscheidungen bleiben dabei im Profil stehen, ungestellte Fragen hinterlassen kein
    Ereignis und werden beim nächsten Durchlauf erneut gestellt.

    Kein Modellaufruf mehr an dieser Stelle (Befund schwer 1, zweite T16-Durchsicht):
    `entry.sense` ist bereits die im Belegsatz gemeinte Bedeutung
    (`pipeline.resolve_triage_entries`) — „kenne ich", „will ich lernen" und „überspringen"
    buchen und verkarten alle dieselbe eine Bedeutung, statt „kenne ich"/„überspringen" auf
    einer geratenen ersten und nur „will ich lernen" auf der vom Modell gewählten.

    Liefert die Karten, als zweites Element, ob mit `q` abgebrochen wurde (Bauschritt
    2/4, blockweise Triage) — `run_triage_blocks` braucht das, um nach einem Abbruch die
    Fortsetzungsfrage zu unterlassen — und, als drittes Element, wie viele Einträge von
    `to_ask` dabei **nicht mehr entschieden** wurden (0, wenn nicht abgebrochen wurde;
    Befund 1/9, Durchsicht 1cfb1e4): der Eintrag, bei dem `q` fiel, zählt mit, weil auch er
    kein `Event` erhalten hat und beim nächsten Durchlauf erneut gestellt wird. `remaining`
    hieß der `to_ask`-Parameter bis Befund 5, Durchsicht d4f10fc — derselbe Name wie
    `TriageResolution.remaining` (dokumentation.md §2), aber eine andere Bedeutung: dort
    der Rest nach der Blockgrenze, hier der Rest innerhalb des laufenden Blocks nach der
    Sammelaktion."""
    cards: list[Card] = []
    for index, occurrence in enumerate(to_ask):
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
            # (Befund 9, Durchsicht 1cfb1e4): `to_ask[index]` (der gerade angezeigte
            # Eintrag) zählt zu den nicht entschiedenen mit — er hat kein `Event`
            # bekommen, genau wie jeder folgende.
            return cards, True, len(to_ask) - index
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
    return cards, False, 0


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
    block_number: int = 1,
) -> TriagePass:
    """Ein vollständiger Triage-Deckel für **einen Block**: Meldungen, Sammelaktion,
    Einzelabfrage — für **eine** der beiden Listen aus `pipeline.ChapterVocabulary` (siehe
    Moduldocstring, „Festlegung: getrennte Decksel"), bereits von `pipeline.
    resolve_triage_entries` zu `resolution` aufbereitet: Profilabgleich,
    Häufigkeitssortierung, Bedeutungsauflösung durch das Modell und Blockgröße liegen dort,
    nicht mehr hier (Befund schwer 1, zweite T16-Durchsicht). Die Blockschleife über mehrere
    Aufrufe hinweg ist `run_triage_blocks` unten, nicht Sache dieser Funktion.

    Abnahmekriterium 6: „Beim zweiten Durchlauf desselben Kapitels werden die als
    *bekannt* markierten Wörter **nicht erneut** abgefragt — das Profil greift"
    (konzept.md, „Abnahmekriterien"). Erfüllt seit der zweiten T16-Durchsicht
    `pipeline.resolve_triage_entries` selbst: Der Vorfilter dort prüft **alle** Kandidaten
    einer Grundform (`pipeline._all_candidates_known`) gegen dieselbe Bedeutung, die auch
    gebucht wird (`entry.sense` in `_individual_phase`/`_bulk_phase`) — vor der Behebung
    bucht(e) dieses Modul „kenne ich" auf `candidates[0]`, während der Vorfilter *alle*
    Kandidaten verlangte, und verfehlte bei 65,8 % mehrdeutigen Grundformen je Kapitel
    (technik.md §3, Nachtrag 18.08.2026) die meisten bereits bekannten Wörter.

    Zwei Zählungen werden gemeldet, nicht verschwiegen (Regel 13): laut Vorfilter bereits
    bekannt (`resolution.known`) und erst nach dem Auflösen als bekannt erkannt
    (`resolution.resolved_known`) in einer gemeinsamen Meldung — beide Wege buchen dieselbe
    Bedeutung als `KNOWN`, nur zu verschiedenen Zeitpunkten im Ablauf, und eine getrennte
    Zahl ohne die andere wäre wieder die Lücke aus Befund mittel, Durchsicht 46ef37b (im
    Auftragsbeispiel: „4 bereits bekannt" statt der tatsächlichen 25). Übersprungene
    Einträge (`resolution.skipped`, Befund schwer 1, Durchsicht 46ef37b): Kandidaten
    bestanden, aber das Modell wählte „keine passt" — kein Wort, über das der Nutzer hätte
    entscheiden können, deshalb weder Anzeige noch Buchung, nur diese Zählung.

    `resolution.remaining` — der Rest für den nächsten Block (technik.md §12, „Blockweise
    Triage mit Vorladen — entschieden") — wird hier bewusst **nicht** gemeldet (Befund 1,
    Durchsicht d4f10fc): Vor dieser Behebung stand die Meldung „N noch nicht geprüft" hier
    und erschien nach **jedem** Block, obwohl die Einträge sehr wohl geprüft werden, sobald
    der Nutzer fortsetzt. Sie gehört ausschließlich an das Ende der Blockschleife
    (`run_triage_blocks`), dorthin, wo tatsächlich feststeht, dass sie ungeprüft bleiben."""
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

    entries = resolution.entries
    if not entries:
        return TriagePass(cards=[], aborted=False)

    ordered = [entry.occurrence for entry in entries]
    entries_by_occurrence = {entry.occurrence: entry for entry in entries}

    bulk_marked = _bulk_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        ordered=ordered,
        entries_by_occurrence=entries_by_occurrence,
        label=label,
        block_number=block_number,
        read_line=read_line,
        write_line=write_line,
    )
    to_ask = [occurrence for occurrence in ordered if occurrence not in bulk_marked]
    cards, aborted, unasked = _individual_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        to_ask=to_ask,
        entries_by_occurrence=entries_by_occurrence,
        card_direction=card_direction,
        read_line=read_line,
        write_line=write_line,
    )
    return TriagePass(cards=cards, aborted=aborted, unasked=unasked)


def _ask_continue(read_line: ReadLine, write_line: WriteLine, remaining_count: int) -> bool:
    """Fortsetzungsfrage nach einem vollständig durchgeklickten Block (technik.md §12,
    „Blockweise Triage mit Vorladen — entschieden"): nennt, wie viele Einträge noch
    ausstehen, und fragt so lange nach, bis eine gültige Antwort steht. Enter bedeutet
    „nein" — Aufhören ist die sichere Vorgabe, dieselbe Handhabung wie bei der
    Sammelaktion (`_bulk_phase`, Enter = keine). Eine unbekannte Eingabe führt zu einer
    erneuten Frage statt zu einer stillschweigenden Annahme (Regel 13, wie `_ask_action`)."""
    while True:
        answer = (
            read_line(
                f"{remaining_count} weitere Einträge stehen aus — weitermachen? "
                "[j]a/[n]ein (Enter = nein) "
            )
            .strip()
            .lower()
        )
        if answer in ("", "n", "nein"):
            return False
        if answer in ("j", "ja"):
            return True
        write_line("Ungültige Eingabe — j oder n erwartet.")


_ResolveBlock = Callable[[Sequence[pipeline.VocabularyEntry]], pipeline.TriageResolution]

# (Befund 4, Durchsicht 1cfb1e4): Der vorgeladene Rückruf bekommt zusätzlich das
# Abbruchsignal, das `_BlockPrefetch.cancel` unten setzt — der Weg, auf dem
# `cli.main._resolve_silently` erfährt, dass sein Ergebnis niemand mehr ansieht, ohne dass
# dieses Modul den Rückruf selbst kennen muss oder `cli.main` diese Klasse. `threading.
# Event` ist dafür bewusst die Standardbibliothek, kein eigener Typ aus einem der beiden
# Module.
_ResolveSilentBlock = Callable[
    [Sequence[pipeline.VocabularyEntry], threading.Event], pipeline.TriageResolution
]


class _BlockPrefetch:
    """Löst einen Block im Hintergrund auf (technik.md §12, „Vorladen: der nächste Block
    entsteht, während der Nutzer entscheidet"), während der Hauptfaden den vorigen Block
    noch durchentscheidet.

    Ein einzelner `threading.Thread(daemon=True)` statt eines `ThreadPoolExecutor`
    (Festlegung 4): Die Fäden eines Executors werden beim Interpreterende **abgewartet**
    — ein Daemon-Faden dagegen nicht, und genau das braucht `run_triage_blocks` unten, um
    bei „nein" oder `q` sofort zu enden, ohne auf einen noch laufenden Vorladeblock zu
    warten, dessen Ergebnis niemand mehr ansieht.

    **Ein Fehlschlag wird nicht verschluckt** (Festlegung 2, Regel 13): Wirft `resolve`,
    hält `_run` die Ausnahme fest, statt sie zu protokollieren und weiterzulaufen — sie
    erreicht den Nutzer über `join`, an der Stelle, an der tatsächlich auf das Ergebnis
    gewartet wird, nicht im Hintergrund. Ein Vorladen, das bei einem Fehlschlag einfach
    eine leere `TriageResolution` lieferte, sähe aus wie „Kapitel fertig" — der teuerste
    stille Fehlschlag, den diese Stelle hergibt.

    **Abbestellen statt nur Nichtwarten** (Befund 4, Durchsicht 1cfb1e4): Vor dieser
    Behebung lief ein bereits gestarteter Vorladeblock nach „nein" oder `q` im Hintergrund
    einfach weiter und verbrauchte dabei genau die Modellaufrufe, die technik.md §12,
    Festlegung 4 als Grund für das Nichtwarten selbst nennt (gemessen: ein erster
    Wendungsblock brauchte dadurch 7,39 s statt 3,85 s, weil sich Wendungs- und verworfene
    Wortanfragen 1:1 auf demselben Modellserver abwechselten). `cancel()` setzt dafür ein
    eigenes Ereignis, das der Rückruf selbst nach jedem aufgelösten Eintrag prüft
    (`cli.main._resolve_silently`) — der Abbruch greift damit spätestens nach einem
    weiteren, bereits laufenden Modellaufruf, nicht erst am Ende des ganzen Blocks."""

    def __init__(
        self, resolve: _ResolveSilentBlock, entries: Sequence[pipeline.VocabularyEntry]
    ) -> None:
        self._resolve = resolve
        self._entries = entries
        self._result: pipeline.TriageResolution | None = None
        self._error: Exception | None = None
        self._done = threading.Event()
        self._cancelled = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        """(Befund 4, Durchsicht 1cfb1e4): Bestellt den Vorladeblock ab — zu rufen, sobald
        feststeht, dass sein Ergebnis niemand mehr ansieht (nach `q` oder nach „nein" in
        `run_triage_blocks` unten). Setzt nur das Ereignis, wartet nicht auf den Faden:
        Der bleibt Daemon und hört spätestens beim nächsten von `pipeline.
        resolve_triage_entries` aufgelösten Eintrag auf, weil sein `on_progress`-Rückruf
        genau dieses Ereignis prüft. Ein abgebrochener Vorladeblock ist kein Fehlschlag —
        `_run` unten hält seine Ausnahme zwar wie jede andere fest, aber `join` wird für
        ihn nie wieder aufgerufen, sie erreicht also nie den Nutzer."""
        self._cancelled.set()

    def _run(self) -> None:
        try:
            self._result = self._resolve(self._entries, self._cancelled)
        except Exception as error:  # im Hauptfaden erneut geworfen, siehe join unten
            self._error = error
        finally:
            self._done.set()

    def is_done(self) -> bool:
        """Ohne zu warten — für die Meldung aus Festlegung 3, bevor `join` tatsächlich
        blockiert."""
        return self._done.is_set()

    def join(self) -> pipeline.TriageResolution:
        """Wartet auf den Hintergrundfaden und liefert sein Ergebnis — oder wirft die dort
        aufgetretene Ausnahme erneut, im Hauptfaden, sichtbar für den Nutzer (Festlegung 2).

        (Befund 5, Durchsicht 1cfb1e4): Wartet in kurzen Abschnitten statt an einem Stück
        — ein einzelner `Thread.join()` ohne Frist ließ ein `KeyboardInterrupt` (Strg-C)
        erst nach dem *vollen* verbleibenden Block ankommen (gemessen: 15,0 s statt 1,5 s
        bei einem Kontrolllauf mit `time.sleep(15)`), weil CPython ein anstehendes Signal
        erst verarbeitet, wenn ein blockierender Aufruf zum Python-Bytecode zurückkehrt.
        Bei einem nicht mehr antwortenden Modellserver wären das bis zu 25 × 120 s
        Zeitüberschreitung — knapp 50 Minuten, in denen nur „Der nächste Block wird noch
        aufgelöst …" stand und nur ein Abschießen des Prozesses half."""
        while self._thread.is_alive():
            self._thread.join(timeout=0.1)
        if self._error is not None:
            raise self._error
        assert self._result is not None  # `_run` setzt _error oder _result, nie keins von beiden
        return self._result


def run_triage_blocks(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    entries: Sequence[pipeline.VocabularyEntry],
    resolve_visible_block: _ResolveBlock,
    resolve_silent_block: _ResolveSilentBlock,
    label: str,
    card_direction: CardDirection,
    read_line: ReadLine,
    write_line: WriteLine,
) -> list[Card]:
    """Die Blockschleife (technik.md §12, „Blockweise Triage mit Vorladen — entschieden"):
    löst einen Block auf, schickt ihn durch `run_triage_pass`, und macht mit
    `resolution.remaining` weiter, bis nichts mehr aussteht, die Einzelabfrage mit `q`
    abgebrochen wurde, oder der Nutzer die Fortsetzungsfrage verneint.

    **Zwei Rückrufe statt einem** (Bauschritt 3/4, technik.md §12, „Vorladen: der nächste
    Block entsteht, während der Nutzer entscheidet"), bewusst unterschiedlich benannt, damit
    beim Lesen keine Verwechslung möglich ist:

    - `resolve_visible_block` löst **nur den allerersten** Block auf — synchron, im
      Hauptfaden, bevor irgendetwas angezeigt wird. In `cli.main` ist das
      `_resolve_with_progress`, mit der sich fortschreibenden Statuszeile (Festlegung 3):
      Der Nutzer wartet hier tatsächlich, es gibt nichts zu vertuschen.
    - `resolve_silent_block` löst **jeden vorgeladenen Folgeblock** auf — im
      Hintergrundfaden (`_BlockPrefetch`), angestoßen, sobald der aktuelle Block feststeht
      und **bevor** `run_triage_pass` ihn anzeigt, nicht erst nach einem bejahten
      `_ask_continue`. In `cli.main` ist das `_resolve_silently`, ohne jede Ausgabe
      (Festlegung 3) und mit einer eigenen Profilverbindung (Festlegung 1) — beides bleibt
      dieser Funktion verborgen, sie ruft nur den Rückruf.

    **Die Reihenfolge der Fragen:** Zuerst die Fortsetzungsfrage, *dann* auf den
    vorgeladenen Block warten — nicht umgekehrt, sonst wartete der Nutzer auf etwas, das er
    vielleicht gar nicht mehr will (Festlegung 4). Ist der vorgeladene Block dabei noch
    nicht fertig, sagt eine Zeile das, bevor `_BlockPrefetch.join` tatsächlich blockiert.

    Nach `q` (`triage_pass.aborted`) folgt **keine** Fortsetzungsfrage: Der Nutzer hat den
    Abbruch bereits erklärt, eine weitere Frage danach wäre die Frage, die er gerade
    beantwortet hat. Diese Prüfung steht deshalb **vor** der auf ein leeres
    `resolution.remaining` (Befund 1, Durchsicht 1cfb1e4): Bricht der Nutzer im *letzten*
    Block ab, ist `resolution.remaining` dort ebenfalls leer — die vertauschte Reihenfolge
    meldete in genau diesem Fall fälschlich „Alle … durchgesehen", obwohl der laufende
    Block selbst nicht vollständig durchgeklickt war (bis zu `triage_pass.unasked` Einträge
    blieben ungesehen). Ist `resolution.remaining` dagegen **nicht** wegen eines Abbruchs,
    sondern schon nach einem vollständig durchgeklickten ersten Block leer, wird ebenfalls
    nicht gefragt — es gibt nichts, womit fortgesetzt werden könnte. In beiden verlassenden
    Fällen (`q`, „nein") ist ein bereits angestoßener Vorladeblock zu diesem Zeitpunkt
    möglicherweise noch nicht fertig — er wird dann nicht nur **nicht abgewartet**, sondern
    über `_BlockPrefetch.cancel` auch **abbestellt** (Festlegung 4, Befund 4, Durchsicht
    1cfb1e4): Der Faden ist Daemon und hält das Programmende nicht auf, läuft ohne die
    Abbestellung aber weiter und verbraucht dabei Modellaufrufe, deren Ergebnis niemand
    mehr ansieht."""
    cards: list[Card] = []
    resolution = resolve_visible_block(entries)
    block_number = 1
    while True:
        # Bauschritt 3/4: angestoßen, sobald der aktuelle Block feststeht — unmittelbar
        # bevor run_triage_pass ihn anzeigt, nicht erst nach der Fortsetzungsfrage. Ohne
        # Rest gibt es nichts vorzuladen, und die anschließende Prüfung auf ein leeres
        # `current` unten würde ohnehin sofort beenden.
        prefetch = (
            _BlockPrefetch(resolve_silent_block, resolution.remaining)
            if resolution.remaining
            else None
        )
        if prefetch is not None:
            prefetch.start()

        triage_pass = run_triage_pass(
            con=con,
            book=book,
            chapter_number=chapter_number,
            resolution=resolution,
            label=label,
            card_direction=card_direction,
            read_line=read_line,
            write_line=write_line,
            block_number=block_number,
        )
        cards.extend(triage_pass.cards)
        current = resolution.remaining

        if triage_pass.aborted:
            # (Befund 1, Durchsicht 1cfb1e4): Diese Prüfung muss vor der auf ein leeres
            # `current` stehen — sonst meldet ein Abbruch im letzten Block fälschlich
            # „Alle … durchgesehen", weil `resolution.remaining` dort ebenfalls leer ist.
            # (Befund 9, Durchsicht 1cfb1e4): Die gemeldete Zahl zählt zusätzlich
            # `triage_pass.unasked` — die im laufenden Block selbst noch nicht
            # entschiedenen Einträge, die `len(current)` allein nicht sieht.
            write_line(f"{len(current) + triage_pass.unasked} {label} noch nicht geprüft.")
            if prefetch is not None:
                prefetch.cancel()
            return cards
        if not current:
            write_line(f"Alle {label} für dieses Kapitel durchgesehen.")
            return cards
        if not _ask_continue(read_line, write_line, len(current)):
            write_line(f"{len(current)} {label} noch nicht geprüft.")
            assert (
                prefetch is not None
            )  # current ist nicht leer, siehe oben — also wurde vorgeladen
            prefetch.cancel()
            return cards

        assert prefetch is not None  # current ist nicht leer, siehe oben — also wurde vorgeladen
        if not prefetch.is_done():
            write_line("Der nächste Block wird noch aufgelöst — bitte einen Moment …")
        resolution = prefetch.join()
        block_number += 1
