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

Anzeigeform (Bauschritt 2/2 der Konsolenausgabe, Auftragstext vom 02.09.2026, technik.md
§13, „Triage-Anzeige"): Trennlinie mit Zähler, Wortform und Bedeutung in einer Kopfzeile,
Nebendaten und Belegsatz eingerückt darunter (`_entry_lines`) — der Grund steht dort, nicht
hier. Sämtliche stilabhängigen Textbausteine (Farbe, Umbruch, Pfeil, Trennpunkt,
Anführungszeichen, Trennlinien) kommen aus `cli.display` (`Style`, `bold`/`dim`/`highlight`,
`entry_rule`, `cover`, `headline`, `wrap_indented`); dieses Modul schreibt keinen Farbcode
und keines dieser Zeichen von Hand, damit die farb- und sonderzeichenlose Spielart
(`cli.display.PLAIN_STYLE`, Vorgabe für `run_triage_pass`/`run_triage_blocks` unten)
automatisch dieselbe Struktur trägt. (Befund 2, Durchsicht e537273, korrigiert: eine
frühere Fassung dieses Satzes behauptete das uneingeschränkt.) Ausgenommen sind
Gedankenstrich und Auslassungspunkte in den eigenen Meldungen dieses Moduls (etwa
„Ungültige Eingabe — k, l, s oder q erwartet.") — das ist gewöhnliche
Oberflächentext-Typografie (dokumentation.md §1), kein stilabhängiges Sonderzeichen im Sinn
von `cli.display._SPECIAL_CHARS`, und `safe_print`s Ausweichkodierung fängt eine Konsole
ohne sie ohnehin ab (kein Absturz, nur `?` statt des Zeichens) — anders als bei `─`/`═`/
`→`/`·` und den typografischen Anführungszeichen lohnt sich dafür keine eigene, vorab
prüfende Ausweichlogik.

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
„nein", dieselbe Handhabung wie bei der Sammelaktion (Regel 13). Scheitert stattdessen ein
Block (etwa der Modellserver im Vorladen), läuft die Ausnahme unverändert durch — dieselbe
Liste steht dann bereits, unvollständig, aber gültig, im optionalen `partial_cards` (siehe
dort), für den Teilexport in `cli.main._run` (technik.md §12, „Entschieden 15.09.2026 …").

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

from cli import display
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

# (Befund B, Durchsicht 5fda1b9): `label` ist stets ein Plural ("Wörter"/"Wendungen",
# `cli.main`) — bei genau einem Eintrag liest „1 Wörter noch nicht geprüft." grammatisch
# falsch. Nur diese Werte kommen als `label` vor — seit der Kapitelbilanz (`run_triage_pass`)
# zusätzlich „Vokabeln", das Wörter und Wendungen zusammenfasst; eine dreistellige
# Übersetzungstabelle für den Singularfall genügt dafür, keine allgemeine
# Pluralmaschinerie (dokumentation.md §4 Regel 14).
_SINGULAR_LABEL = {"Wörter": "Wort", "Wendungen": "Wendung", "Vokabeln": "Vokabel"}


def _count_label(count: int, label: str) -> str:
    """`count` mit `label` im passenden Numerus — „1 Wort", aber „0 Wörter"/„2 Wörter"
    (Befund B, Durchsicht 5fda1b9). Ein `label`, das nicht in `_SINGULAR_LABEL` steht,
    bleibt unverändert im Plural stehen, statt eine Ausnahme zu werfen — diese Funktion
    kennt nur die beiden heute tatsächlich vorkommenden Werte, keine allgemeine Regel."""
    word = _SINGULAR_LABEL.get(label, label) if count == 1 else label
    return f"{count} {word}"


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
    Auftragsbeispiel „1310 Wörter noch nicht geprüft" statt tatsächlich 1334.

    `known` und `deferred` zählen die Entscheidungen dieses Blocks für die Blockbilanz
    (zweite Nutzermeldung vom 02.09.2026, siehe `run_triage_pass`): wie viele Einträge
    „kenne ich" beziehungsweise „überspringen" bekommen haben. Die Sammelaktion zählt
    **nicht** mit — sie meldet ihre eigene Zahl, und `run_triage_pass` zählt beide
    zusammen. Wie viele „lernen" bekamen, steht bereits in `len(cards)`."""

    cards: list[Card]
    aborted: bool
    unasked: int = 0
    known: int = 0
    deferred: int = 0


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


def _entry_lines(
    entry: pipeline.ResolvedEntry, position: int, total: int, chosen: int, style: display.Style
) -> list[str]:
    """Anzeige eines Eintrags im Format „kompakte Kopfzeile" (Auftragstext vom 02.09.2026,
    Nutzermeldung: „Man muss immer das Wort … zwischen dem Zitat … und der Ausgabe aus dem
    vorherigen Wort suchen"; Begründung technik.md §13, „Triage-Anzeige"): eine Trennlinie
    mit Zähler `position`/`total` (`display.entry_rule`), Wortform und Übersetzung in
    einer — bei Bedarf umgebrochenen — Kopfzeile (`display.headline`, Befund 3, Durchsicht
    e537273), Nebendaten (Wortart, Häufigkeit, Bedeutungsangabe) und Belegsatz eingerückt
    darunter. Kein Inhalt geht dabei verloren, nur die Anordnung ändert sich —
    Regel 1 (dokumentation.md §4): `dictionary.label` liefert weiterhin `NO_SENSE_LABEL`
    beziehungsweise `UNCERTAIN_LABEL`, wenn `entry.sense` keinen `sense`-Text trägt, statt
    dass diese Zeilen wegfielen.

    `VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD` bekommt seit dieser Umstellung eine
    **eigene, hervorgehobene Zeile** (konzept.md §5, „Mehrdeutigkeit") statt an die
    Bedeutungszeile angehängt zu werden, wo sie am Zeilenende unterging (Auftragstext)."""
    occurrence = entry.occurrence
    pos_display = anki.pos_display(occurrence.lemma.pos)
    translation_text = entry.sense.translation or entry.sense.wikdict_trans_list or "?"

    lines = [display.entry_rule(position, total, chosen, style)]
    # (Befund 3, Durchsicht e537273): `display.headline` bricht die Kopfzeile um — vor
    # dieser Behebung lief sie als einzige Zeile eines Eintrags über den Bildschirmrand,
    # weil `Sense.translation` die ganze `wikdict_trans_list` trägt (bis zu 245 Zeichen).
    lines.extend(display.headline(occurrence.word_form, translation_text, style))
    if entry.status is VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD:
        lines.append(f"  {display.highlight('[neue Bedeutung eines bekannten Wortes]', style)}")

    info = (
        f"{pos_display}{display.dot(style)}{occurrence.frequency}x im Kapitel"
        f"{display.dot(style)}{dictionary.label(entry.sense)}"
    )
    lines.extend(display.dim(line, style) for line in display.wrap_indented(info, style))
    lines.extend(display.wrap_indented(display.quote(occurrence.example_sentence, style), style))
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
    style: display.Style,
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
    Block bleibt sie unverändert: Eine Gesamtzahl an Blöcken steht ohnehin nie fest.

    Die nummerierte Liste (Auftragstext vom 02.09.2026, Bauschritt 2/2 der
    Konsolenausgabe): rechtsbündige Nummern und eine ausgerichtete Wortartspalte, damit sie
    überfliegbar ist — dieselbe Spaltenrechnung wie `cli.main._choose_chapter` für die
    Kapitelliste, hier über die maximale Länge von Nummer und Wortartangabe. Sie wird genau
    **einmal** gedruckt, auch bei einer ungültigen Antwort (Regel 13, Entscheidung vom
    14.09.2026, technik.md §9, „Offene Punkte"): Bis dahin überging eine vertippte Zahl
    („1O" statt „10") die Sammelaktion ganz, mit der Meldung „Sammelaktion übersprungen" —
    für den Nutzer 25 Einzelfragen statt eines Tastendrucks, und beim ersten Durchlauf je
    Buch ist genau dieser Tastendruck der ganze Zweck. Nur eine **leere** Antwort bleibt
    die ausdrückliche Ablehnung „keine Sammelaktion" und liefert sofort `set()` — jede
    andere ungültige Antwort (keine Zahl, außerhalb von `1..len(ordered)`) fragt stattdessen
    erneut, ohne die bereits gedruckte Liste zu wiederholen, und nennt dabei die
    eingegangene Zeichenfolge (`display.quote`, passend zu `style`)."""
    if not ordered:
        return set()

    heading = f"{label} (Block {block_number})" if block_number > 1 else label
    write_line(f"  {display.bold(heading, style)}{display.dim(f': {len(ordered)}', style)}")
    number_width = len(str(len(ordered)))
    pos_labels = [anki.pos_display(occurrence.lemma.pos) for occurrence in ordered]
    pos_width = max(len(value) for value in pos_labels)
    for number, (occurrence, pos_label) in enumerate(
        zip(ordered, pos_labels, strict=True), start=1
    ):
        write_line(f"  {number:>{number_width}}. {pos_label:<{pos_width}}  {occurrence.word_form}")

    while True:
        answer = read_line(
            f"  Sammelaktion — bis zu welcher Nummer kennst du alles? "
            f"(1-{len(ordered)}, Enter = keine) "
        ).strip()
        if not answer:
            return set()

        try:
            position = int(answer)
        except ValueError:
            write_line(
                f"  {display.quote(answer, style)} ist keine Zahl — "
                f"1 bis {len(ordered)} oder Enter für keine."
            )
            continue
        if not 1 <= position <= len(ordered):
            write_line(
                f"  {display.quote(answer, style)} liegt außerhalb der Liste — "
                f"1 bis {len(ordered)} oder Enter für keine."
            )
            continue

        selected = ordered[position - 1]
        bulk = triage.bulk_mark(ordered, selected)
        for occurrence in bulk:
            entry = entries_by_occurrence[occurrence]
            _record(con, entry.sense, KnowledgeState.KNOWN, Origin.BULK_MARK, book, chapter_number)
        write_line(f"  {len(bulk)} als bekannt gebucht.")
        return set(bulk)


_ACTIONS = {
    "k": "known",
    "kenne": "known",
    "l": "learn",
    "lernen": "learn",
    "s": "skip",
    "skip": "skip",
    "q": "quit",
    "quit": "quit",
}


def _ask_action(read_line: ReadLine, write_line: WriteLine, *, style: display.Style) -> str:
    """Fragt so lange nach, bis eine gültige Antwort steht — weder eine unbekannte noch
    eine leere Eingabe verwirft eine Entscheidung stillschweigend als „skip" (Regel 13,
    Entscheidung vom 14.09.2026, technik.md §9, „Offene Punkte"): Bis dahin bildete
    `_ACTIONS` eine Leereingabe auf `skip` ab — eine Vorrichtung oder ein versehentlicher
    Zeilenumbruch buchte dadurch „überspringen", ohne dass etwas meldete, und hat zwei
    Abnahmeläufe gekostet, bevor die Ursache feststand. Beide Fälle führen jetzt zu einer
    erneuten Frage, die nennt, was tatsächlich ankam: die eingegebene Zeichenfolge in
    Anführungszeichen (`display.quote`, passend zu `style` — typografisch auf einem
    fähigen Ziel, sonst ASCII) bei nicht-leerer Eingabe, ein eigener Hinweis „Keine
    Eingabe" bei leerer, wo ein leeres Zitat sinnlos wäre. Gezeigt wird die Eingabe **vor**
    dem `.lower()` (nach `.strip()`), damit der Nutzer liest, was er tatsächlich getippt
    hat — die Auswertung selbst bleibt case-insensitiv.

    Die Leerzeile vor jedem Prompt setzt die Eingabezeile vom Eintrag darüber ab
    (Auftragstext vom 02.09.2026, „Man sieht klar, wo die vorherige Ausgabe aufhört") —
    `tests/test_cli_main.py` erkennt die Frage weiterhin am Wortlaut `[k]enne ich`, die
    Einrückung ändert daran nichts."""
    while True:
        write_line("")
        typed = read_line("  [k]enne ich  [l]ernen  [s]kip  [q]uit > ").strip()
        action = _ACTIONS.get(typed.lower())
        if action is not None:
            return action
        if typed:
            write_line(
                f"  {display.quote(typed, style)} ist keine der Antworten — "
                "k, l, s oder q erwartet."
            )
        else:
            write_line("  Keine Eingabe — k, l, s oder q erwartet.")


def _individual_phase(
    *,
    con: sqlite3.Connection,
    book: Book,
    chapter_number: int,
    to_ask: list[Occurrence],
    entries_by_occurrence: dict[Occurrence, pipeline.ResolvedEntry],
    card_direction: CardDirection,
    chosen_before: int,
    style: display.Style,
    read_line: ReadLine,
    write_line: WriteLine,
) -> TriagePass:
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

    Liefert einen `TriagePass`: die Karten, ob mit `q` abgebrochen wurde (Bauschritt
    2/4, blockweise Triage) — `run_triage_blocks` braucht das, um nach einem Abbruch die
    Fortsetzungsfrage zu unterlassen —, die Zahl der „kenne ich"- und „überspringen"-
    Entscheidungen für die Blockbilanz, und wie viele Einträge von
    `to_ask` dabei **nicht mehr entschieden** wurden (0, wenn nicht abgebrochen wurde;
    Befund 1/9, Durchsicht 1cfb1e4): der Eintrag, bei dem `q` fiel, zählt mit, weil auch er
    kein `Event` erhalten hat und beim nächsten Durchlauf erneut gestellt wird. `remaining`
    hieß der `to_ask`-Parameter bis Befund 5, Durchsicht d4f10fc — derselbe Name wie
    `TriageResolution.remaining` (dokumentation.md §2), aber eine andere Bedeutung: dort
    der Rest nach der Blockgrenze, hier der Rest innerhalb des laufenden Blocks nach der
    Sammelaktion.

    Die Leerzeile nach jeder abgeschlossenen Entscheidung ist der Trenner zur nächsten
    Trennlinie (`_entry_lines`, `display.entry_rule`) — Auftragstext vom 02.09.2026: „Zwei
    aufeinanderfolgende Einträge sind durch einen Trenner geschieden". `position`/`total`
    für `_entry_lines` sind `index + 1`/`len(to_ask)` — die Zählung bezieht sich auf das,
    was in der Einzelabfrage tatsächlich noch zu entscheiden ist, nicht auf den ganzen
    Block vor der Sammelaktion."""
    cards: list[Card] = []
    known = 0
    deferred = 0
    total = len(to_ask)
    for index, occurrence in enumerate(to_ask):
        entry = entries_by_occurrence[occurrence]
        # `chosen_before + len(cards)` ist der Stand **vor** der Entscheidung, die gleich
        # ansteht — die Zahl wächst also erst mit der nächsten Trennlinie (zweite
        # Nutzermeldung vom 02.09.2026, siehe `display.entry_rule`).
        for line in _entry_lines(entry, index + 1, total, chosen_before + len(cards), style):
            write_line(line)
        while True:
            action = _ask_action(read_line, write_line, style=style)
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
            write_line(f"  {obstacle}")
        write_line("")  # Trenner zum nächsten Eintrag, siehe Docstring oben

        if action == "quit":
            write_line("  Abgebrochen.")
            # (Befund 9, Durchsicht 1cfb1e4): `to_ask[index]` (der gerade angezeigte
            # Eintrag) zählt zu den nicht entschiedenen mit — er hat kein `Event`
            # bekommen, genau wie jeder folgende.
            return TriagePass(
                cards=cards,
                aborted=True,
                unasked=len(to_ask) - index,
                known=known,
                deferred=deferred,
            )
        if action == "known":
            known += 1
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
            deferred += 1
            _record(con, entry.sense, KnowledgeState.DEFERRED, Origin.TRIAGE, book, chapter_number)
    return TriagePass(cards=cards, aborted=False, known=known, deferred=deferred)


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
    chosen_before: int = 0,
    style: display.Style = display.PLAIN_STYLE,
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
    (`run_triage_blocks`), dorthin, wo tatsächlich feststeht, dass sie ungeprüft bleiben.

    `style` (Vorgabe `display.PLAIN_STYLE`, Auftragstext vom 02.09.2026, Bauschritt 2/2):
    reicht bis in `_bulk_phase`/`_individual_phase`/`_entry_lines` durch — diese Funktion
    wählt selbst keine Farbe, sie fügt nur ihre eigenen Meldungen in dieselbe Einrückung
    wie die übrige Anzeige ein („Auch … die Zusammenfassungszeilen aus run_triage_pass
    fügen sich in die Einrückung ein")."""
    if resolution.known or resolution.resolved_known:
        write_line(
            f"  {_count_label(resolution.known + resolution.resolved_known, label)} laut "
            f"Profil bereits bekannt ({resolution.resolved_known} davon erst nach Auflösen "
            "der Bedeutung) — nicht erneut abgefragt."
        )
    if resolution.skipped:
        write_line(
            f"  {_count_label(resolution.skipped, label)} übersprungen: keine der "
            "Wörterbuchbedeutungen war zuzuordnen."
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
        style=style,
        read_line=read_line,
        write_line=write_line,
    )
    to_ask = [occurrence for occurrence in ordered if occurrence not in bulk_marked]
    triage_pass = _individual_phase(
        con=con,
        book=book,
        chapter_number=chapter_number,
        to_ask=to_ask,
        entries_by_occurrence=entries_by_occurrence,
        card_direction=card_direction,
        chosen_before=chosen_before,
        style=style,
        read_line=read_line,
        write_line=write_line,
    )
    _write_block_summary(triage_pass, len(bulk_marked), chosen_before, write_line)
    return triage_pass


def _write_block_summary(
    triage_pass: TriagePass, bulk_marked: int, chosen_before: int, write_line: WriteLine
) -> None:
    """Bilanz am Blockende (zweite Nutzermeldung vom 02.09.2026): was dieser Block
    gebracht hat, und — sobald `chosen_before` etwas beiträgt — der Kapitelstand.

    Die als bekannt gebuchten zählen die Sammelaktion mit: Für den Nutzer ist „als bekannt
    gebucht" eine Zahl, nicht zwei Wege dorthin (`bulk_mark` und die Einzelabfrage buchen
    beide `KnowledgeState.KNOWN`, nur mit anderer `Origin`).

    Die Kapitelzeile erscheint nur, wenn `chosen_before` etwas beiträgt — beim allerersten
    Block stünde sonst zweimal dieselbe Zahl untereinander. (Befund 5, Durchsicht e537273,
    berichtigt: „sobald schon ein Block oder der Wörter-Deckel davorliegt" traf das
    Prädikat nicht wörtlich — ein erster Block ohne einzige „lernen"-Entscheidung lässt
    `chosen_before` bei 0, obwohl ein ganzer Block bereits lief; die Zeile erscheint dann
    im zweiten Block trotzdem nicht.)

    Nach einem Abbruch mit `q` (`triage_pass.aborted`) steht statt „Block beendet:" die
    Überschrift „Bis hierher:" (Befund 5, Durchsicht e537273): Auf dem Bildschirm folgte
    diese Zeile bislang unmittelbar auf „Abgebrochen." — der Block wurde in diesem Fall
    gerade nicht beendet, sondern verlassen. Die Zahlen und ihre Reihenfolge bleiben
    unverändert, nur dieses eine Wort wechselt."""
    chosen_now = len(triage_pass.cards)
    heading = "Bis hierher" if triage_pass.aborted else "Block beendet"
    write_line("")
    write_line(
        f"  {heading}: {chosen_now} zum Lernen, "
        f"{triage_pass.known + bulk_marked} als bekannt gebucht, "
        f"{triage_pass.deferred} übersprungen."
    )
    if chosen_before:
        write_line(
            f"  Insgesamt {_count_label(chosen_before + chosen_now, 'Vokabeln')} "
            "zum Lernen in diesem Kapitel."
        )


def _ask_continue(read_line: ReadLine, write_line: WriteLine, remaining_count: int) -> bool:
    """Fortsetzungsfrage nach einem vollständig durchgeklickten Block (technik.md §12,
    „Blockweise Triage mit Vorladen — entschieden"): nennt, wie viele Einträge noch
    ausstehen, und fragt so lange nach, bis eine gültige Antwort steht. Enter bedeutet
    „nein" — Aufhören ist die sichere Vorgabe, dieselbe Handhabung wie bei der
    Sammelaktion (`_bulk_phase`, Enter = keine). Eine unbekannte Eingabe führt zu einer
    erneuten Frage statt zu einer stillschweigenden Annahme (Regel 13, wie `_ask_action`)."""
    while True:
        write_line("")
        answer = (
            read_line(
                f"  {remaining_count} weitere Einträge stehen aus — weitermachen? "
                "[j]a/[n]ein (Enter = nein) "
            )
            .strip()
            .lower()
        )
        if answer in ("", "n", "nein"):
            return False
        if answer in ("j", "ja"):
            return True
        write_line("  Ungültige Eingabe — j oder n erwartet.")


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
    chosen_before: int = 0,
    style: display.Style = display.PLAIN_STYLE,
    partial_cards: list[Card] | None = None,
) -> list[Card]:
    """Die Blockschleife (technik.md §12, „Blockweise Triage mit Vorladen — entschieden"):
    löst einen Block auf, schickt ihn durch `run_triage_pass`, und macht mit
    `resolution.remaining` weiter, bis nichts mehr aussteht, die Einzelabfrage mit `q`
    abgebrochen wurde, oder der Nutzer die Fortsetzungsfrage verneint.

    `partial_cards` (technik.md §12, „Entschieden 15.09.2026: ein abgebrochener Lauf
    exportiert, was er hat") ist eine vom Aufrufer übergebene Sammelliste, die diese
    Funktion nach **jedem abgeschlossenen Block** um dessen Karten ergänzt — abgeschlossen
    heißt: `run_triage_pass` hat einen `TriagePass` zurückgeliefert, ob vollständig
    durchgeklickt oder mit `q` verlassen. Scheitert ein späterer Block (etwa der
    Vorladeblock über `prefetch.join()` unten), läuft die Ausnahme unverändert durch
    (Regel 13, dokumentation.md §4) — `partial_cards` enthält zu diesem Zeitpunkt aber
    bereits die Karten jedes zuvor abgeschlossenen Blocks. Aus dem **Export** verloren
    gehen auch schon getroffene Entscheidungen des noch nicht abgeschlossenen Blocks: Sie
    stehen zwar bereits als `Event` im Profil (`_record`), tragen aber zu keinem `Card` in
    `partial_cards` bei, weil `run_triage_pass` für diesen Block nie zurückkehrt (gemessen,
    Befund 2, Durchsicht b91a56e: Blockgröße 3, erste Entscheidung „lernen", danach
    `EOFError` — Exit 1, keine Exportdatei, Profil `[('learning', 1)]`, aber null
    `card`-Zeilen). Am **Verhalten** ändert das nichts: `learning` gilt weiterhin nicht als
    `known` (Abschnitt 4), der nächste Lauf über dasselbe Kapitel fragt diese Grundform
    erneut ab. `cli.main._run` übergibt für die Wörter- und
    die Wendungsschleife **dieselbe** Liste, damit ein Fehlschlag im Wendungsteil die
    Wörterkarten mitnimmt. Vorgabe `None` legt intern eine eigene, leere Liste an — für
    jeden Aufrufer, dem der Teilexport gleichgültig ist (etwa die Tests in dieser Datei),
    ändert sich damit nichts am bisherigen Rückgabewert.

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
    mehr ansieht.

    Die hier gemeldete Restzahl steht in derselben Bilanz wie in `pipeline.
    resolve_triage_entries` (Docstring dort: „ergibt wieder len(entries)"), nur über alle
    Blöcke dieses Aufrufs aufsummiert statt über einen einzigen: gemeldeter Rest (`len(
    current)`, bei einem Abbruch zusätzlich `triage_pass.unasked`) + entschiedene
    Einträge (jede erzeugte `Card` und jedes „kenne ich"/„überspringen" aus Sammel- und
    Einzelabfrage, über alle Blöcke) + `known` + `skipped` (ebenfalls über alle Blöcke,
    aus `resolution.known`/`resolution.resolved_known`/`resolution.skipped`) ergibt wieder
    `len(entries)`, die Kapitelmenge, mit der dieser Aufruf begonnen hat. Ohne diesen
    Hinweis hat ein Prüfer der Durchsicht von 5fda1b9 erst gegen eine um `known` und
    `skipped` zu kurze Formel gerechnet und einen Fehlbetrag von 934 Einträgen eine Weile
    für einen eigenen Befund gehalten.

    `style` (Vorgabe `display.PLAIN_STYLE`, Auftragstext vom 02.09.2026, Bauschritt 2/2)
    reicht bis in `run_triage_pass` durch; die eigenen Meldungen dieser Funktion (Blockende,
    Fortsetzungsfrage) fügen sich in dieselbe Einrückung ein wie die übrige Anzeige."""
    if partial_cards is None:
        partial_cards = []
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
            chosen_before=chosen_before + len(cards),
            style=style,
        )
        cards.extend(triage_pass.cards)
        # technik.md §12, „Entschieden 15.09.2026 …": Dieser Block ist mit dem
        # zurückgelieferten TriagePass abgeschlossen — seine Karten dürfen jetzt in die
        # Sammelliste, unabhängig davon, ob ein späterer Block gleich scheitert.
        partial_cards.extend(triage_pass.cards)
        current = resolution.remaining

        if triage_pass.aborted:
            # (Befund 1, Durchsicht 1cfb1e4): Diese Prüfung muss vor der auf ein leeres
            # `current` stehen — sonst meldet ein Abbruch im letzten Block fälschlich
            # „Alle … durchgesehen", weil `resolution.remaining` dort ebenfalls leer ist.
            # (Befund 9, Durchsicht 1cfb1e4): Die gemeldete Zahl zählt zusätzlich
            # `triage_pass.unasked` — die im laufenden Block selbst noch nicht
            # entschiedenen Einträge, die `len(current)` allein nicht sieht.
            write_line(
                f"  {_count_label(len(current) + triage_pass.unasked, label)} noch nicht geprüft."
            )
            if prefetch is not None:
                prefetch.cancel()
            return cards
        if not current:
            write_line(f"  Alle {label} für dieses Kapitel durchgesehen.")
            return cards
        if not _ask_continue(read_line, write_line, len(current)):
            write_line(f"  {_count_label(len(current), label)} noch nicht geprüft.")
            assert (
                prefetch is not None
            )  # current ist nicht leer, siehe oben — also wurde vorgeladen
            prefetch.cancel()
            return cards

        assert prefetch is not None  # current ist nicht leer, siehe oben — also wurde vorgeladen
        if not prefetch.is_done():
            write_line("  Der nächste Block wird noch aufgelöst — bitte einen Moment …")
        resolution = prefetch.join()
        block_number += 1
