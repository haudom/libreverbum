"""Prüft `libreverbum/profile.py` — bauplan.md T8, Schema und Ereignisfolge."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from os import PathLike
from pathlib import Path
from typing import Any, cast

import pytest

from libreverbum import anki, profile
from libreverbum.entities import (
    Book,
    Card,
    CardDirection,
    Event,
    KnowledgeState,
    Lemma,
    Occurrence,
    Origin,
    Sense,
)

_BOOK = Book(title="Testbuch", author="Autorin")


def _event(sense: Sense, state: KnowledgeState, timestamp: datetime) -> Event:
    return Event(
        sense=sense,
        knowledge_state=state,
        origin=Origin.TRIAGE,
        timestamp=timestamp,
        book=_BOOK,
        chapter_number=1,
    )


def _add_chapter(con: sqlite3.Connection, book_id: int, chapter_number: int = 1) -> None:
    """Legt die Kapitelzeile an, die `event.chapter_number` seit Befund 6 (Review T8) als
    Fremdschlüssel braucht. Bewusst per Roh-SQL: `profile.py` bekommt dafür keine eigene
    Schreibfunktion (Regel 14, kein Vorbau) — das Schema allein reicht für T8."""
    con.execute(
        "INSERT INTO chapter (book_id, number, title) VALUES (?, ?, ?)",
        (book_id, chapter_number, "Testkapitel"),
    )
    con.commit()


def _occurrence(chapter_number: int = 1) -> Occurrence:
    return Occurrence(
        book=_BOOK,
        chapter_number=chapter_number,
        lemma=Lemma(text="watch", pos="NOUN"),
        word_form="watch",
        example_sentence="He checked his watch before leaving.",
        frequency=2,
        proper_noun_frequency=0,
    )


def _card_for(occurrence: Occurrence) -> Card:
    sense = Sense(
        lemma=occurrence.lemma,
        translation="Uhr",
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    direction = CardDirection.EN_DE
    guid = anki.new_card_guid(occurrence, sense, direction)
    return Card(sense=sense, occurrence=occurrence, card_direction=direction, guid=guid)


def test_rule_5_schema_version_is_set_on_a_fresh_profile(tmp_path: Path) -> None:
    """Regel 5 (dokumentation.md §4): PRAGMA user_version ist gesetzt und passt zum
    erwarteten Stand."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    version = con.execute("PRAGMA user_version").fetchone()[0]

    assert version == profile.SCHEMA_VERSION
    assert version != 0


def test_missing_profile_directory_is_a_visible_failure_with_a_german_message(
    tmp_path: Path,
) -> None:
    """A15 (nacharbeit.md): Liegt der Profilpfad in einem nicht vorhandenen Verzeichnis,
    bricht `open_profile` mit einer deutschen Meldung ab, die den Pfad nennt — statt
    sqlite3s englische Fremdmeldung `unable to open database file` unverändert
    durchzureichen (Regel 13, dokumentation.md §1)."""
    missing = tmp_path / "does_not_exist" / "profil.sqlite3"

    with pytest.raises(ValueError, match=r"does_not_exist.*existiert nicht"):
        profile.open_profile(missing)


def test_reopening_a_profile_does_not_recreate_or_erase_its_schema(tmp_path: Path) -> None:
    """bauplan.md T8: Ein zweiter `open_profile`-Aufruf auf derselbe Datei legt das Schema
    nicht erneut an und verwirft keine vorhandenen Daten."""
    path = tmp_path / "profil.sqlite3"
    first = profile.open_profile(path)
    lemma_id = profile.ensure_lemma(first, Lemma(text="bank", pos="NOUN"))
    first.close()

    second = profile.open_profile(path)

    assert second.execute("PRAGMA user_version").fetchone()[0] == profile.SCHEMA_VERSION
    row = second.execute(
        "SELECT id FROM lemma WHERE text = ? AND pos = ?", ("bank", "NOUN")
    ).fetchone()
    assert row is not None
    assert row[0] == lemma_id


def test_mismatched_schema_version_is_a_visible_failure(tmp_path: Path) -> None:
    """Regel 13 (dokumentation.md §4): Eine Profildatei mit einer anderen Schemaversion als
    der erwarteten bricht sichtbar ab, statt unbemerkt weiterverwendet zu werden."""
    path = tmp_path / "profil.sqlite3"
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA user_version = {profile.SCHEMA_VERSION + 1}")
    con.commit()
    con.close()

    with pytest.raises(ValueError):
        profile.open_profile(path)


def test_a_foreign_sqlite_file_is_rejected_instead_of_being_overwritten(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 2 (Review T8): `user_version = 0` ist der SQLite-Ausgangswert
    jeder neuen Datei, nicht nur einer frischen Profildatei — eine fremde Datei mit
    eigenen Tabellen (etwa eine Kopie von en-de.sqlite3) bekäme sonst zusätzlich das
    Profilschema hineingeschrieben (technik.md §4, „Getrennte Datei — nicht mit dem
    Wörterbuch mischen"). Legt hier eine eigene fremde Datei an, nicht
    `tools/en-de.sqlite3`, damit der Test ohne die unversionierte Datei läuft."""
    path = tmp_path / "fremd.sqlite3"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE translation (id INTEGER PRIMARY KEY, written_rep TEXT)")
    con.commit()
    con.close()

    with pytest.raises(ValueError):
        profile.open_profile(path)

    con = sqlite3.connect(path)
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    con.close()
    assert tables == {"translation"}


def test_a_versioned_file_missing_profile_tables_is_rejected(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 2 (Review T8): `user_version` allein ist keine Zusicherung —
    eine Datei mit passender Versionsnummer, aber ohne die sieben Profiltabellen (etwa
    eine vorversionierte fremde Datei), bricht sichtbar ab statt erst bei der nächsten
    Abfrage mit einer nichtssagenden `OperationalError: no such table`."""
    path = tmp_path / "unvollstaendig.sqlite3"
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA user_version = {profile.SCHEMA_VERSION}")
    con.commit()
    con.close()

    with pytest.raises(ValueError):
        profile.open_profile(path)


def test_rule_4_profile_access_never_opens_the_dictionary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regel 4 (dokumentation.md §4, technik.md §4 „Getrennte Datei"): Ein Profilzugriff
    öffnet nie en-de.sqlite3 — Profil und Wörterbuch bleiben getrennte Dateien."""
    profile_path = tmp_path / "profil.sqlite3"
    dictionary_path = tmp_path / "en-de.sqlite3"
    decoy_content = b"keine gueltige sqlite-datei"
    dictionary_path.write_bytes(decoy_content)

    opened_paths: list[str] = []
    real_connect = sqlite3.connect

    def spying_connect(
        database: str | bytes | PathLike[str] | PathLike[bytes], *args: Any, **kwargs: Any
    ) -> sqlite3.Connection:
        opened_paths.append(str(database))
        return cast("sqlite3.Connection", real_connect(database, *args, **kwargs))

    monkeypatch.setattr(sqlite3, "connect", spying_connect)

    con = profile.open_profile(profile_path)
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    lemma = Lemma(text="bank", pos="NOUN")
    sense = Sense(
        lemma=lemma,
        wikdict_sense="edge of river or lake",
        wikdict_trans_list="Ufer",
        wikdict_lexentry="eng/bank__Noun__2",
    )
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, datetime.now(UTC)))

    # (Befund 4, Review T8): eine falsche Umsetzung könnte denselben Pfad anders
    # geschrieben öffnen (as_posix(), relativ, os.path.abspath) und bliebe mit der alten,
    # rein negativen Zusicherung unbemerkt. Die positive Zusicherung fordert genau einen
    # Aufruf, genau mit diesem Pfad.
    assert opened_paths == [str(profile_path)]
    assert dictionary_path.read_bytes() == decoy_content


def test_knowledge_is_recorded_per_sense_not_per_lemma(tmp_path: Path) -> None:
    """technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro Wort": watch als
    Uhr und watch als Wache sind zwei Bedeutungen desselben Lemmas mit unabhängiger
    Ereignisfolge — wird nur die eine als bekannt eingestuft, bleibt die andere ohne
    Ereignis."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    lemma = Lemma(text="watch", pos="NOUN")
    watch_clock = Sense(
        lemma=lemma,
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    watch_guard = Sense(
        lemma=lemma,
        wikdict_sense="person or group of people who guard",
        wikdict_trans_list="Wache",
        wikdict_lexentry="eng/watch__Noun__1",
    )

    profile.record_event(con, _event(watch_clock, KnowledgeState.KNOWN, datetime.now(UTC)))

    clock_id = profile.ensure_sense(con, watch_clock)
    guard_id = profile.ensure_sense(con, watch_guard)
    assert clock_id != guard_id

    clock_events = profile.events_for_sense(con, clock_id)
    guard_events = profile.events_for_sense(con, guard_id)
    assert [e.knowledge_state for e in clock_events] == [KnowledgeState.KNOWN]
    assert guard_events == []


def test_sense_identity_uses_full_row_content_not_lexentry_alone(tmp_path: Path) -> None:
    """bauplan.md T8, Hinweis 1: Eine `sense`-Zeile wird über den vollen Zeileninhalt
    eindeutig, nicht über `wikdict_lexentry` allein — sonst kollabieren watch als Uhr und
    watch als Wache auf dieselbe Zeile (entities.Sense-Docstring, 22,7 % der Zeilen mit
    `lexentry`)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    lemma = Lemma(text="watch", pos="NOUN")
    watch_clock = Sense(
        lemma=lemma,
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    watch_guard = Sense(
        lemma=lemma,
        wikdict_sense="person or group of people who guard",
        wikdict_trans_list="Wache",
        wikdict_lexentry="eng/watch__Noun__1",
    )

    clock_id = profile.ensure_sense(con, watch_clock)
    guard_id = profile.ensure_sense(con, watch_guard)

    assert clock_id != guard_id
    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 2


def test_ensure_sense_is_idempotent(tmp_path: Path) -> None:
    """bauplan.md T8: Zweimaliges `ensure_sense` mit demselben Inhalt liefert dieselbe id
    und legt keine zweite Zeile an."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )

    first_id = profile.ensure_sense(con, sense)
    second_id = profile.ensure_sense(con, sense)

    assert first_id == second_id
    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 1


def test_ensure_sense_is_idempotent_when_wikdict_sense_is_null(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 1 (Review T8): `wikdict_sense` fehlt bei 36 % der
    Wörterbuchzeilen — systematisch die Hauptbedeutungen (Regel 1). SQLite hält NULL in
    einem gewöhnlichen UNIQUE-Constraint für unterschiedlich von jedem anderen NULL;
    viermaliges `ensure_sense` mit demselben Inhalt und `wikdict_sense=None` legt trotzdem
    nur eine Zeile an."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="watch", pos="NOUN"),
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )

    ids = [profile.ensure_sense(con, sense) for _ in range(4)]

    assert len(set(ids)) == 1
    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 1


def test_ensure_sense_is_idempotent_when_all_wikdict_fields_are_null(tmp_path: Path) -> None:
    """Regel 10 (dokumentation.md §4): Eine Wendung ohne Wörterbucheintrag trägt in allen
    drei `wikdict_`-Feldern `None`. Auch dieser Fall darf beim wiederholten Anlegen nicht
    zu mehreren `sense`-Zeilen führen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(lemma=Lemma(text="give it a whirl", pos="VERB"))

    ids = [profile.ensure_sense(con, sense) for _ in range(3)]

    assert len(set(ids)) == 1
    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 1


def test_events_accumulate_instead_of_being_overwritten(tmp_path: Path) -> None:
    """technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand": ein
    zweites Ereignis zu derselben Bedeutung ergänzt die Folge, statt das erste zu ersetzen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="give up", pos="VERB"),
        wikdict_sense="admit defeat",
        wikdict_trans_list="aufgeben | kapitulieren",
        wikdict_lexentry="eng/give_up__Verb__1",
    )
    first_timestamp = datetime(2026, 8, 10, tzinfo=UTC)
    second_timestamp = datetime(2026, 8, 17, tzinfo=UTC)

    profile.record_event(con, _event(sense, KnowledgeState.LEARNING, first_timestamp))
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, second_timestamp))

    sense_id = profile.ensure_sense(con, sense)
    events = profile.events_for_sense(con, sense_id)
    assert [e.knowledge_state for e in events] == [KnowledgeState.LEARNING, KnowledgeState.KNOWN]
    assert [e.timestamp for e in events] == [first_timestamp, second_timestamp]


def test_events_for_sense_are_ordered_by_timestamp_not_insertion_order(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 3 (Review T8): Ein nachgetragenes, älteres Ereignis steht in
    der Folge vor einem bereits vorhandenen jüngeren — `events_for_sense` sortiert nach
    `timestamp`, nicht nach der Reihenfolge des Eintragens. T9 liest `[-1]` als aktuellen
    Kenntnisstand und braucht dafür das jeweils jüngste Ereignis an letzter Stelle
    (entities.Event-Docstring)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )
    newer_timestamp = datetime(2026, 8, 17, tzinfo=UTC)
    older_timestamp = datetime(2026, 8, 10, tzinfo=UTC)

    # Erst das jüngere Ereignis eintragen, das ältere danach nachtragen.
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, newer_timestamp))
    profile.record_event(con, _event(sense, KnowledgeState.FORGOTTEN, older_timestamp))

    sense_id = profile.ensure_sense(con, sense)
    events = profile.events_for_sense(con, sense_id)

    assert [e.timestamp for e in events] == [older_timestamp, newer_timestamp]
    assert events[-1].knowledge_state == KnowledgeState.KNOWN


def test_record_event_rejects_a_naive_timestamp(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 5 (Review T8): `entities.Event` verlangt einen
    zeitzonenbehafteten Zeitstempel (UTC). Ein naiver Zeitstempel landete sonst unbemerkt
    als `…T00:00:00` neben zeitzonenbehafteten Werten wie `…+00:00` in derselben Spalte
    und ließe den Vergleich in einem späteren Modul scheitern."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )
    naive_timestamp = datetime(2026, 8, 18)

    with pytest.raises(ValueError):
        profile.record_event(con, _event(sense, KnowledgeState.KNOWN, naive_timestamp))


def test_record_event_normalizes_the_timestamp_to_utc_before_storing(tmp_path: Path) -> None:
    """Befund 1 (Review T9): `events_for_sense` sortiert den Zeitstempel lexikografisch als
    TEXT — über verschiedene UTC-Versätze hinweg ist das nur dann die zeitliche Reihenfolge,
    wenn `record_event` vor dem Speichern auf UTC normalisiert. Ein Ereignis um 10:30+02:00
    (= 08:30 UTC) ist älter als eines um 09:00+00:00, auch wenn es zuletzt eingetragen wird
    — der Kenntnisstand bleibt trotzdem der des früher eingetragenen, aber später liegenden
    Ereignisses."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )
    later_in_utc = datetime(2026, 8, 17, 9, 0, tzinfo=UTC)
    earlier_with_offset = datetime(2026, 8, 17, 10, 30, tzinfo=timezone(timedelta(hours=2)))

    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, later_in_utc))
    profile.record_event(con, _event(sense, KnowledgeState.DEFERRED, earlier_with_offset))

    sense_id = profile.ensure_sense(con, sense)
    assert profile.current_knowledge_state(con, sense_id) == KnowledgeState.KNOWN


def test_events_for_sense_breaks_a_timestamp_tie_by_insertion_order(tmp_path: Path) -> None:
    """technik.md §4, „jeweils jüngstes Ereignis je Bedeutung": Zwei Ereignisse mit
    identischem Zeitstempel werden über die Einfügereihenfolge entschieden — das zuletzt
    eingetragene Ereignis gilt als das jüngere (Befund 2, Review T9)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )
    timestamp = datetime(2026, 8, 17, tzinfo=UTC)

    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, timestamp))
    profile.record_event(con, _event(sense, KnowledgeState.DEFERRED, timestamp))

    sense_id = profile.ensure_sense(con, sense)
    assert profile.current_knowledge_state(con, sense_id) == KnowledgeState.DEFERRED


def test_recording_an_event_for_an_unknown_chapter_is_rejected(tmp_path: Path) -> None:
    """bauplan.md T8, Befund 6 (Review T8): `event.chapter_number` ist jetzt ein
    Fremdschlüssel auf `chapter(book_id, number)` — ein Ereignis zu einem Kapitel, das nie
    über `chapter` angelegt wurde, wird von SQLite zurückgewiesen, statt eine unverbundene
    Zahl in der Spalte stehen zu lassen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )

    with pytest.raises(sqlite3.IntegrityError):
        profile.record_event(con, _event(sense, KnowledgeState.KNOWN, datetime.now(UTC)))


def test_foreign_keys_pragma_is_enforced(tmp_path: Path) -> None:
    """dokumentation.md §5, Befund 7 (Review T8): `PRAGMA foreign_keys` muss tatsächlich
    wirken, nicht nur gesetzt sein — ein Ereignis ohne zugehörige Bedeutung und ohne
    zugehöriges Buch wird von SQLite selbst zurückgewiesen, nicht erst von einer
    Anwendungsprüfung."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO event "
            "(sense_id, knowledge_state, origin, timestamp, book_id, chapter_number) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (999, "known", "triage", "2026-08-17T00:00:00+00:00", 999, 1),
        )


def test_current_knowledge_state_is_none_for_a_sense_without_events(tmp_path: Path) -> None:
    """bauplan.md T9, „Kenntnisstand als Sicht auf die Ereignisse": Eine Bedeutung ohne
    jedes Ereignis hat keinen Kenntnisstand — das ist nicht dasselbe wie
    `KnowledgeState.FORGOTTEN`, das selbst ein Ereignis wäre."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )
    sense_id = profile.ensure_sense(con, sense)

    assert profile.current_knowledge_state(con, sense_id) is None


def test_current_knowledge_state_reflects_the_latest_event_by_timestamp(tmp_path: Path) -> None:
    """bauplan.md T9, „Kenntnisstand als Sicht auf die Ereignisse": Der abgeleitete Stand
    ist das jüngste Ereignis nach Zeitstempel, nicht das zuletzt eingetragene — ein
    nachgetragenes, älteres Ereignis darf den bereits vorhandenen jüngeren Stand nicht
    verdrängen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )
    newer = datetime(2026, 8, 17, tzinfo=UTC)
    older = datetime(2026, 8, 10, tzinfo=UTC)

    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, newer))
    profile.record_event(con, _event(sense, KnowledgeState.DEFERRED, older))

    sense_id = profile.ensure_sense(con, sense)
    assert profile.current_knowledge_state(con, sense_id) == KnowledgeState.KNOWN


def test_compare_chapter_vocabulary_marks_a_never_seen_sense_as_unknown(tmp_path: Path) -> None:
    """bauplan.md T9, Abgleich gegen den Kapitelwortschatz: Eine Bedeutung ohne jedes
    Ereignis im Profil gilt als unbekannt."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )

    result = profile.compare_chapter_vocabulary(con, [sense])

    assert result[sense] == profile.VocabularyStatus.UNKNOWN


def test_compare_chapter_vocabulary_marks_a_deferred_sense_as_unknown(tmp_path: Path) -> None:
    """Abnahmekriterium 6: „bekannt" ist der abgeschlossene Zustand, nicht der begonnene —
    eine zurückgestellte Bedeutung gilt beim Abgleich weiterhin als unbekannt und wird
    erneut abgefragt (Befund 3, Review T9; konzept.md, „Zurückgestellte Wörter —
    übersprungen, werden erneut gefragt")."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )
    profile.record_event(con, _event(sense, KnowledgeState.DEFERRED, datetime.now(UTC)))

    result = profile.compare_chapter_vocabulary(con, [sense])

    assert result[sense] == profile.VocabularyStatus.UNKNOWN


def test_compare_chapter_vocabulary_marks_a_forgotten_sense_as_unknown_again(
    tmp_path: Path,
) -> None:
    """konzept.md Phase 3: Ein zunächst bekanntes Wort, das später als vergessen markiert
    wurde, „wandert im Profil zurück auf unbekannt" — der Abgleich hält den zuletzt
    eingetragenen Rückschritt fest, nicht die frühere Kenntnis (Befund 3, Review T9)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )
    earlier = datetime(2026, 8, 10, tzinfo=UTC)
    later = datetime(2026, 8, 17, tzinfo=UTC)
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, earlier))
    profile.record_event(con, _event(sense, KnowledgeState.FORGOTTEN, later))

    result = profile.compare_chapter_vocabulary(con, [sense])

    assert result[sense] == profile.VocabularyStatus.UNKNOWN


def test_compare_chapter_vocabulary_does_not_treat_a_deferred_sibling_as_known(
    tmp_path: Path,
) -> None:
    """technik.md §4, „ob mindestens eine seiner Bedeutungen bekannt ist": Eine
    zurückgestellte Geschwisterbedeutung zählt nicht als bekannt — die andere Bedeutung
    bleibt unbekannt, statt als neue Bedeutung eines bekannten Wortes markiert zu werden
    (Befund 3, Review T9)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    lemma = Lemma(text="watch", pos="NOUN")
    watch_clock = Sense(
        lemma=lemma,
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    watch_guard = Sense(
        lemma=lemma,
        wikdict_sense="person or group of people who guard",
        wikdict_trans_list="Wache",
        wikdict_lexentry="eng/watch__Noun__2",
    )
    profile.record_event(con, _event(watch_clock, KnowledgeState.DEFERRED, datetime.now(UTC)))

    result = profile.compare_chapter_vocabulary(con, [watch_clock, watch_guard])

    assert result[watch_guard] == profile.VocabularyStatus.UNKNOWN


def test_acceptance_6_known_words_are_not_asked_again(tmp_path: Path) -> None:
    """Abnahmekriterium 6: Beim zweiten Durchlauf desselben Kapitels werden als bekannt
    markierte Wörter nicht erneut abgefragt — das Profil greift."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="bank", pos="NOUN"),
        wikdict_sense="financial institution",
        wikdict_trans_list="Bank",
        wikdict_lexentry="eng/bank__Noun__1",
    )

    # erster Durchlauf: die Triage stuft die Bedeutung als bekannt ein
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, datetime.now(UTC)))

    # zweiter Durchlauf desselben Kapitels: derselbe Kapitelwortschatz wird erneut abgeglichen
    result = profile.compare_chapter_vocabulary(con, [sense])

    assert result[sense] == profile.VocabularyStatus.KNOWN


def test_compare_chapter_vocabulary_marks_a_new_sense_of_a_known_lemma(tmp_path: Path) -> None:
    """bauplan.md T9, Kennzeichnung „neue Bedeutung eines bekannten Wortes" (konzept.md §5,
    „Mehrdeutigkeit"): watch als Uhr ist bekannt, watch als Wache noch nicht — die zweite
    Bedeutung wird als neue Bedeutung eines bekannten Wortes markiert, nicht als
    unbekanntes Wort."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    lemma = Lemma(text="watch", pos="NOUN")
    watch_clock = Sense(
        lemma=lemma,
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    watch_guard = Sense(
        lemma=lemma,
        wikdict_sense="person or group of people who guard",
        wikdict_trans_list="Wache",
        wikdict_lexentry="eng/watch__Noun__2",
    )
    profile.record_event(con, _event(watch_clock, KnowledgeState.KNOWN, datetime.now(UTC)))

    result = profile.compare_chapter_vocabulary(con, [watch_clock, watch_guard])

    assert result[watch_clock] == profile.VocabularyStatus.KNOWN
    assert result[watch_guard] == profile.VocabularyStatus.NEW_MEANING_OF_KNOWN_WORD


def test_compare_chapter_vocabulary_does_not_mark_an_unrelated_lemma_as_a_new_meaning(
    tmp_path: Path,
) -> None:
    """bauplan.md T9: Ein bekanntes Wort steckt eine andere Grundform nicht an — die
    Kennzeichnung „neue Bedeutung eines bekannten Wortes" gilt nur innerhalb **derselben**
    Grundform (konzept.md §5, „Mehrdeutigkeit"), nicht profilweit."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense_bank = Sense(
        lemma=Lemma(text="bank", pos="NOUN"),
        wikdict_sense="financial institution",
        wikdict_trans_list="Bank",
        wikdict_lexentry="eng/bank__Noun__1",
    )
    sense_forget = Sense(
        lemma=Lemma(text="forget", pos="VERB"),
        wikdict_sense="fail to remember",
        wikdict_trans_list="vergessen",
        wikdict_lexentry="eng/forget__Verb__1",
    )
    profile.record_event(con, _event(sense_bank, KnowledgeState.KNOWN, datetime.now(UTC)))

    result = profile.compare_chapter_vocabulary(con, [sense_bank, sense_forget])

    assert result[sense_forget] == profile.VocabularyStatus.UNKNOWN


def test_compare_chapter_vocabulary_does_not_mark_a_different_pos_as_a_new_meaning(
    tmp_path: Path,
) -> None:
    """bauplan.md T9, der `saw`-Fall (technik.md, „Warum die Reihenfolge zwingend ist"):
    `watch` als Substantiv (Uhr) bekannt zu markieren, steckt `watch` als Verb (beobachten)
    nicht an — dieselbe Grundform mit anderer Wortart ist eine andere Lemma-Identität
    (Befund 4, Review T9)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    watch_noun = Sense(
        lemma=Lemma(text="watch", pos="NOUN"),
        wikdict_sense=None,
        wikdict_trans_list="Uhr | Armbanduhr",
        wikdict_lexentry="eng/watch__Noun__1",
    )
    watch_verb = Sense(
        lemma=Lemma(text="watch", pos="VERB"),
        wikdict_sense="to look at attentively",
        wikdict_trans_list="beobachten | zusehen",
        wikdict_lexentry="eng/watch__Verb__1",
    )
    profile.record_event(con, _event(watch_noun, KnowledgeState.KNOWN, datetime.now(UTC)))

    result = profile.compare_chapter_vocabulary(con, [watch_verb])

    assert result[watch_verb] == profile.VocabularyStatus.UNKNOWN


def test_compare_chapter_vocabulary_does_not_create_a_row_for_an_unseen_sense(
    tmp_path: Path,
) -> None:
    """bauplan.md T9: Der Abgleich ist ein reiner Lesezugriff — eine Bedeutung, die im
    Profil noch nie ein Ereignis hatte, bekommt dadurch keine eigene Zeile."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )

    profile.compare_chapter_vocabulary(con, [sense])

    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 0


def test_ensure_occurrence_is_idempotent(tmp_path: Path) -> None:
    """Wie `ensure_sense`: Zweimaliges `ensure_occurrence` mit demselben Inhalt liefert
    dieselbe id und legt keine zweite Zeile an — dieselbe Bemessung wie das
    UNIQUE-Constraint auf `occurrence` (`book_id`, `chapter_number`, `lemma_id`)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    occurrence = _occurrence()

    first_id = profile.ensure_occurrence(con, occurrence)
    second_id = profile.ensure_occurrence(con, occurrence)

    assert first_id == second_id
    assert con.execute("SELECT count(*) FROM occurrence").fetchone()[0] == 1


def test_ensure_occurrence_without_a_chapter_row_is_rejected(tmp_path: Path) -> None:
    """`occurrence` trägt denselben Fremdschlüssel auf `chapter(book_id, number)` wie
    `event` (Befund 6, Review T8) — ein Vorkommen zu einem nie angelegten Kapitel wird
    von SQLite zurückgewiesen, nicht stillschweigend übernommen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    with pytest.raises(sqlite3.IntegrityError):
        profile.ensure_occurrence(con, _occurrence())


def test_record_card_writes_the_same_guid_that_the_card_carries(tmp_path: Path) -> None:
    """Regel 6 (dokumentation.md §4, „Anki-GUID beim Export in card mitschreiben"):
    Nach `record_card` steht zu der Karte eine Zeile in `card`, deren GUID mit
    `card.guid` übereinstimmt — genau die GUID, die auch im exportierten Anki-Deck
    steht (Befund mittel, Durchsicht T16: bislang landete sie nirgends im Profil)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    card = _card_for(_occurrence())

    card_id = profile.record_card(con, card)

    row = con.execute("SELECT guid FROM card WHERE id = ?", (card_id,)).fetchone()
    assert row is not None
    assert row[0] == card.guid


def test_record_card_links_the_occurrence_and_sense_rows(tmp_path: Path) -> None:
    """`record_card` legt Vorkommen und Bedeutung an, falls sie fehlen, und verknüpft
    genau diese Zeilen mit der Kartenzeile — kein verwaistes `card` ohne passendes
    `occurrence`/`sense`."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    card = _card_for(_occurrence())

    card_id = profile.record_card(con, card)

    occurrence_id, sense_id = con.execute(
        "SELECT occurrence_id, sense_id FROM card WHERE id = ?", (card_id,)
    ).fetchone()
    assert occurrence_id == profile.ensure_occurrence(con, card.occurrence)
    assert sense_id == profile.ensure_sense(con, card.sense)


def test_record_card_is_idempotent_for_a_second_export_of_the_same_meaning(tmp_path: Path) -> None:
    """Der Nutzen von Regel 6 ist erst eingelöst, wenn ein zweiter Export derselben
    Bedeutung sich darauf stützen kann: `anki.new_card_guid` liefert dafür stets
    dieselbe GUID (dokumentation.md, Bericht zu T16-Nachbesserung) — ein zweiter
    `record_card`-Aufruf mit derselben Karte legt keine zweite `card`-Zeile an."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    card = _card_for(_occurrence())

    first_id = profile.record_card(con, card)
    second_id = profile.record_card(con, card)

    assert first_id == second_id
    assert con.execute("SELECT count(*) FROM card").fetchone()[0] == 1


def test_record_card_without_a_chapter_row_is_rejected(tmp_path: Path) -> None:
    """Dasselbe Fremdschlüsselverhalten wie `record_event`: Ein Kapitel, das nie über
    `chapter` angelegt wurde, lässt `record_card` nicht stillschweigend eine Karte dazu
    anlegen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    card = _card_for(_occurrence())

    with pytest.raises(sqlite3.IntegrityError):
        profile.record_card(con, card)
