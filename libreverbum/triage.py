"""Triage — Häufigkeitssortierung und Sammelaktion (bauplan.md T10).

Aufgabe
-------
Schritt 4 des Kernablaufs (konzept.md §4), soweit er reine Rechnung ist (technik.md §7,
Modulkarte, „triage liegt größtenteils nicht im Kern"): den Kapitelwortschatz nach
Häufigkeit ordnen und die Sammelaktion „ab hier kenne ich alles" mit allen in der Anzeige
davorstehenden Wörtern zugleich einlösen. Die einzelne Entscheidung je Wort trifft der
Nutzer und liegt außerhalb dieses Moduls.

(Befund 8, Durchsicht 1cfb1e4): Eine Wortobergrenze pro Kapitel gibt es seit dem
01.09.2026 nicht mehr (technik.md §12, konzept.md §4, „Blockweise Triage mit
Fortsetzungsfrage") — an ihre Stelle ist die Blockgröße aus
`cli.interaction` (`WORD_BLOCK_SIZE`, `EXPRESSION_BLOCK_SIZE`) getreten, die den
Kapitelwortschatz portioniert statt ihn zu kürzen. `defer_beyond_word_limit` unten
rechnet die abgeschaffte Obergrenze weiterhin korrekt aus, hat aber außerhalb ihrer
eigenen Tests keinen Aufrufer mehr — siehe ihren eigenen Docstring.

Voraussetzungen
---------------
Erwartet den bereits extrahierten Kapitelwortschatz als `Occurrence`-Liste (`extraction`,
T3) — vor dem Nachschlagen und vor der Übersetzung, die im Kernablauf erst danach folgen
(konzept.md, „Der Kernablauf"). Alle übergebenen Vorkommen gehören zu **einem** Kapitel;
`defer_beyond_word_limit` weist eine Liste mit mehreren Kapiteln zurück (Regel 13), weil
die Obergrenze, die sie berechnet, „pro Kapitel" galt — siehe den Absatz zu Befund 8 oben,
warum sie heute keinen Aufrufer mehr hat.

Liefert
-------
`sort_by_frequency` die deterministisch sortierte Liste. `defer_beyond_word_limit` und
`bulk_mark` liefern je eine Liste der betroffenen `Occurrence`-Objekte, kein `Event`:
Welcher `KnowledgeState` und welche `Origin` daraus werden, steht durch die aufgerufene
Funktion bereits fest — `defer_beyond_word_limit` liefert Kandidaten für
`KnowledgeState.DEFERRED` mit `Origin.WORD_LIMIT`, `bulk_mark` für `KnowledgeState.KNOWN`
mit `Origin.BULK_MARK` (siehe deren Docstring in `entities.py`). Die Umwandlung in ein
`Event` macht `pipeline` (T15), sobald eine Bedeutung aufgelöst ist. Kein I/O, kein
Zeitstempel: Beides liegt außerhalb reiner Rechnung, `timestamp` ist deshalb kein
Parameter dieses Moduls (Regel 14).

Offener Punkt (Befund 2, Review T10): Eine frühere Fassung erzeugte hier `Event`-Objekte
mit einer unaufgelösten `Sense(lemma=...)`. Das trägt nicht: Ohne `wikdict_`-Felder oder
`uncertain` fallen alle unaufgelösten Bedeutungen einer Grundform in `profile.ensure_sense`
auf **eine** Zeile zusammen — der `ifnull(...)`-Index trennt nur nach `lemma_id`, nicht
nach Kapitel, Herkunft oder Lauf. Kenntnis wäre damit faktisch wieder pro Wort geführt,
das Gegenteil von technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro
Wort". Wie eine Kenntnisangabe auf Wortebene — vor dem Nachschlagen einer Bedeutung — im
Schema abgelegt wird, ist eine Vorentscheidung für T9/T15 und wird hier nicht nebenbei
getroffen.
"""

from __future__ import annotations

from collections.abc import Iterable

from libreverbum.entities import Occurrence


def _sort_key(occurrence: Occurrence) -> tuple[int, str, str]:
    """Sortierschlüssel für `sort_by_frequency`: `frequency` absteigend, bei Gleichstand
    `(lemma.text, lemma.pos)` aufsteigend als zweiter, stabiler Schlüssel.

    Innerhalb eines Kapitels ist ein `Lemma` je `Occurrence` eindeutig (`entities.Occurrence`,
    „Ein Eintrag je Kapitel und Grundform"); der zweite Schlüssel legt damit bei gleicher
    Häufigkeit eine Ordnung fest, die nur vom Inhalt abhängt, nie von der Reihenfolge der
    Eingabe — sonst wäre ein Gleichstandstest nur zufällig grün (dokumentation.md §5, „Ein
    Test gilt erst als Test, wenn er einmal rot war").
    """
    return (-occurrence.frequency, occurrence.lemma.text, occurrence.lemma.pos)


def sort_by_frequency(occurrences: Iterable[Occurrence]) -> list[Occurrence]:
    """Sortiert den Kapitelwortschatz nach `frequency` absteigend (konzept.md §4: „nach
    Häufigkeit sortiert präsentiert, häufigste zuerst"). Zweiter Schlüssel siehe
    `_sort_key`."""
    return sorted(occurrences, key=_sort_key)


def _ensure_single_chapter(ordered: list[Occurrence]) -> None:
    """Bricht sichtbar ab, wenn `ordered` Vorkommen aus mehr als einem Kapitel enthält.

    (Befund 4, Review T10): Ohne diese Prüfung würde `defer_beyond_word_limit` aus der
    „Obergrenze pro Kapitel" (konzept.md §4) stillschweigend eine kapitelübergreifende
    machen.
    """
    chapters = {(occurrence.book, occurrence.chapter_number) for occurrence in ordered}
    if len(chapters) > 1:
        gefundene = ", ".join(
            f"„{book.title}“ Kapitel {chapter_number}"
            for book, chapter_number in sorted(chapters, key=lambda paar: (paar[0].title, paar[1]))
        )
        raise ValueError(
            "Die Wortobergrenze gilt pro Kapitel (konzept.md §4), die Liste enthält aber "
            f"Vorkommen aus mehreren Kapiteln: {gefundene}."
        )


def defer_beyond_word_limit(occurrences: Iterable[Occurrence], word_limit: int) -> list[Occurrence]:
    """Wortobergrenze (konzept.md §4): Was über `word_limit` liegt, wird zurückgestellt.

    Liefert die Vorkommen jenseits der `word_limit` häufigsten aus `sort_by_frequency` —
    Kandidaten für `KnowledgeState.DEFERRED` mit `Origin.WORD_LIMIT` (`entities.Origin`
    Docstring); der Nutzer hat hier nichts entschieden. Erwartet Vorkommen aus einem
    einzigen Kapitel (sonst Regel-13-Fehlschlag, siehe `_ensure_single_chapter`) und die
    volle Kapitelliste vor der Sammelaktion — wird bereits Gebuchtes mitgezählt, verbraucht
    es ein Kontingent der Obergrenze mit; das zu vermeiden ist Sache von `pipeline` (T15),
    nicht dieser Funktion.

    (Befund 8, Durchsicht 1cfb1e4): Die Obergrenze, die diese Funktion berechnet, ist seit
    dem 01.09.2026 kein Teil des Ablaufs mehr — `cli.interaction`s Blockgröße portioniert
    den Kapitelwortschatz, statt ihn an dieser Stelle zu kürzen. Diese Funktion hat deshalb
    außerhalb von `tests/test_triage.py` heute keinen Aufrufer mehr; ob sie ganz entfällt
    oder für einen künftigen Anwendungsfall (etwa ein Messwerkzeug in `tools/`) bleibt, ist
    hier nicht entschieden (Regel 14) und im Bericht zu dieser Durchsicht offen gemeldet.
    """
    # REGEL (dokumentation.md §4 Regel 13, „Kein except, das nur protokolliert…"): Eine
    # negative Obergrenze ist ein widersprüchliches Argument und damit ein sichtbarer
    # Fehlschlag, keine leere Rückgabe, die wie „nichts zurückgestellt" aussähe.
    if word_limit < 0:
        raise ValueError(f"Wortobergrenze darf nicht negativ sein, war {word_limit}.")
    ordered = sort_by_frequency(occurrences)
    _ensure_single_chapter(ordered)
    return ordered[word_limit:]


def bulk_mark(occurrences: Iterable[Occurrence], selected: Occurrence) -> list[Occurrence]:
    """Sammelaktion „ab hier kenne ich alles" (konzept.md §4): liefert `selected` und alle
    in der Anzeige davorstehenden Wörter (bauplan.md T10, Prüfung) — Kandidaten für
    `KnowledgeState.KNOWN` mit `Origin.BULK_MARK` (`entities.Origin` Docstring).

    „Davorstehend" ist die Position in `sort_by_frequency`, nicht `frequency >=
    selected.frequency` allein (Befund 1, Review T10): Bei Gleichstand entscheidet
    `_sort_key` (Grundform und Wortart), welche der gleich häufigen Wörter noch vor
    `selected` in der Anzeige stehen. Ein gleich häufiges Wort **hinter** `selected` bucht
    der Klick nicht mit — sonst bucht ein Klick mitten in einem großen Gleichstandsblock
    weit mehr, als der Nutzer gesehen hat (bei `tools/sherlock.txt` tragen 67 % aller
    Wortformen die Häufigkeit 1).
    """
    ordered = sort_by_frequency(occurrences)
    # REGEL (dokumentation.md §4 Regel 13): `selected` muss Teil von `occurrences` sein,
    # sonst sichtbarer Fehlschlag statt einer stillschweigend leeren Liste.
    if selected not in ordered:
        raise ValueError(f"{selected!r} ist nicht Teil der übergebenen Wortliste.")
    return ordered[: ordered.index(selected) + 1]
