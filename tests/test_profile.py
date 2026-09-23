"""Prüft `libreverbum/profile.py` — bauplan.md T8, Schema und Ereignisfolge."""

from __future__ import annotations

import json
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
    CefrLevel,
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


def _preset_event(sense: Sense, timestamp: datetime) -> Event:
    """Ein Vorbelegungs-Ereignis (technik.md §4, Schemafassung 2) — ohne Buch und
    Kapitel, anders als `_event` oben."""
    return Event(
        sense=sense,
        knowledge_state=KnowledgeState.KNOWN,
        origin=Origin.PRESET,
        timestamp=timestamp,
        book=None,
        chapter_number=None,
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
    """Liegt der Profilpfad in einem nicht vorhandenen Verzeichnis,
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
    eine Datei mit passender Versionsnummer, aber ohne die acht Profiltabellen (etwa
    eine vorversionierte fremde Datei), bricht sichtbar ab statt erst bei der nächsten
    Abfrage mit einer nichtssagenden `OperationalError: no such table`."""
    path = tmp_path / "unvollstaendig.sqlite3"
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA user_version = {profile.SCHEMA_VERSION}")
    con.commit()
    con.close()

    with pytest.raises(ValueError):
        profile.open_profile(path)


# Die acht Tabellennamen des Profilschemas (technik.md §4) — eigens hier gepflegt statt
# über profile._TABLE_NAMES importiert: Der folgende Test soll gerade prüfen, dass jede
# einzelne davon verlangt wird, nicht die Menge übernehmen, die er testet.
_PROFILE_TABLE_NAMES = (
    "book",
    "chapter",
    "lemma",
    "sense",
    "occurrence",
    "event",
    "card",
    "learner",
)


@pytest.mark.parametrize("missing_table", _PROFILE_TABLE_NAMES)
def test_a_versioned_file_missing_a_single_profile_table_is_rejected(
    tmp_path: Path, missing_table: str
) -> None:
    """Verschärfung von `test_a_versioned_file_missing_profile_tables_is_rejected` (Befund
    leicht, Durchsicht d8d5954): Jener Test legt eine Datei mit **gar keiner** Tabelle an —
    die Differenzmenge `_TABLE_NAMES - existing_tables` ist dann so oder so nicht leer,
    egal welche (oder wie viele) Tabellen `_TABLE_NAMES` tatsächlich nennt. Fiele eine
    einzelne Tabelle unbemerkt aus `_TABLE_NAMES`, bliebe jener Test unverändert grün. Hier
    fehlt gezielt **eine** Tabelle bei sonst vollständigem Schema — das prüft für jede der
    acht Tabellen einzeln, dass ihr Fehlen tatsächlich erkannt wird."""
    path = tmp_path / f"fehlt_{missing_table}.sqlite3"
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA user_version = {profile.SCHEMA_VERSION}")
    for table in _PROFILE_TABLE_NAMES:
        if table != missing_table:
            con.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY)")
    con.commit()
    con.close()

    with pytest.raises(ValueError, match=missing_table):
        profile.open_profile(path)


def test_open_profile_read_only_rejects_a_missing_file(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: `read_only=True` legt nie eine Datei
    an — eine fehlende Profildatei bricht mit derselben `FileNotFoundError` ab wie im
    Schreibzugriff, statt über die sqlite-URI eine neue Datei zu öffnen (SQLite legt eine
    fehlende Datei sonst anstandslos an, auch schreibgeschützt geöffnet)."""
    missing = tmp_path / "profil.sqlite3"

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        profile.open_profile(missing, read_only=True)

    assert not missing.exists()


def test_open_profile_read_only_treats_an_empty_file_as_no_profile_and_leaves_it_untouched(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: Eine vorhandene, aber 0 Byte große
    Datei — dieselbe `user_version == 0`-Lage wie eine echte neue Profildatei — gilt im
    Lesezugriff als „kein Profil" (`FileNotFoundError`), statt wie im Schreibzugriff das
    Schema angelegt zu bekommen. Die Datei bleibt dabei unverändert 0 Byte groß.

    Verfälschungsprobe (Bericht): `read_only`s Zweig in `open_profile` entfernt (jeder
    Aufruf läuft über den Schreibzweig) ließ diesen Test rot werden — die Datei wuchs auf
    65.536 Byte, und es kam keine Ausnahme."""
    path = tmp_path / "profil.sqlite3"
    path.touch()
    assert path.stat().st_size == 0

    with pytest.raises(FileNotFoundError, match="Profildatei nicht vorhanden"):
        profile.open_profile(path, read_only=True)

    assert path.stat().st_size == 0


def test_open_profile_read_only_rejects_a_zero_version_file_with_foreign_content(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: Eine fremde Datei mit eigenen Tabellen,
    aber Schemaversion 0 (etwa eine Kopie von `en-de.sqlite3`) ist weder „leer" noch ein
    gültiges Profil — dieselbe Unterscheidung wie im Schreibzugriff
    (`test_a_foreign_sqlite_file_is_rejected_instead_of_being_overwritten`), hier als
    `ValueError`, nicht als `FileNotFoundError`, weil die Datei ja nicht fehlt."""
    path = tmp_path / "fremd.sqlite3"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE translation (id INTEGER PRIMARY KEY, written_rep TEXT)")
    con.commit()
    con.close()

    with pytest.raises(ValueError, match="fremde"):
        profile.open_profile(path, read_only=True)


def test_open_profile_read_only_returns_a_connection_that_rejects_writes(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: `read_only=True` öffnet über die
    sqlite-URI `file:…?mode=ro` — ein Schreibversuch auf der zurückgegebenen Verbindung
    scheitert an SQLite selbst (`sqlite3.OperationalError`), nicht nur an einer
    Programmkonvention. Das unterscheidet diesen Zugriff von einer gewöhnlichen, im
    Schreibmodus geöffneten Verbindung, die schlicht nichts schreibt."""
    path = tmp_path / "profil.sqlite3"
    profile.open_profile(path).close()

    con = profile.open_profile(path, read_only=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("INSERT INTO learner (id) VALUES (1)")
    finally:
        con.close()


def test_open_profile_read_only_handles_a_directory_with_spaces_and_a_drive_letter(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht 3b1e201, Befund 2: Die sqlite-URI (`Path.resolve().
    as_uri()`) muss auch unter Windows mit Laufwerksbuchstaben und Leerzeichen im Pfad
    korrekt kodiert sein — `tmp_path` liegt unter Windows bereits unter einem Laufwerk
    (`C:\\…`), dieser Test legt zusätzlich ein Verzeichnis mit einem Leerzeichen im Namen
    an.

    Keine Verfälschungsprobe: Eine naive `f"file:{path}?mode=ro"`-Zusammensetzung ohne
    `Path.resolve().as_uri()` (der naheliegendste Stolperstein) besteht diesen Test unter
    Windows/SQLite ebenfalls — `sqlite3` nimmt Rückstriche und unkodierte Leerzeichen
    hier klaglos an, auch als relativer Pfad. Eine echte Unterscheidung bräuchte einen
    Pfad mit einem URI-Sonderzeichen (`?`, `#`), das ein Profilpfad in der Praxis nicht
    trägt — dieser Test bleibt deshalb ein reiner Regressionstest für die gewählte
    Bauweise, keine rot geprüfte Zusicherung (dokumentation.md §5)."""
    directory = tmp_path / "Verzeichnis mit Leerzeichen"
    directory.mkdir()
    path = directory / "profil.sqlite3"
    profile.open_profile(path).close()

    con = profile.open_profile(path, read_only=True)
    try:
        assert con.execute("PRAGMA user_version").fetchone()[0] == profile.SCHEMA_VERSION
    finally:
        con.close()


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
    dieselbe GUID (dokumentation.md, Bericht zu T16-Nachbesserung) — zwei **getrennt
    erzeugte** `Card`-Objekte desselben Eintrags (zwei eigene `_card_for`-Aufrufe, nicht
    dasselbe Objekt zweimal an `record_card` gereicht) legen zusammen keine zweite
    `card`-Zeile an (technik.md §4, offener Punkt „Die beiden Idempotenz-Tests prüfen
    nicht, was ihr Docstring behauptet")."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    first_card = _card_for(_occurrence())
    second_card = _card_for(_occurrence())

    first_id = profile.record_card(con, first_card)
    second_id = profile.record_card(con, second_card)

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


def test_an_event_without_book_and_chapter_can_be_written_and_read_back(tmp_path: Path) -> None:
    """technik.md §4, Schemafassung 2: `event.book_id`/`event.chapter_number` dürfen NULL
    sein — eine Vorbelegung gehört zu keinem Buch. Ein Ereignis ohne Buch und Kapitel
    lässt sich schreiben und über `events_for_sense` wieder lesen, mit `book=None` und
    `chapter_number=None` — keine Kapitelzeile ist dafür nötig."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="life", pos="NOUN"),
        wikdict_sense="the state of being alive",
        wikdict_trans_list="Leben",
        wikdict_lexentry="eng/life__Noun__1",
    )

    profile.record_event(con, _preset_event(sense, datetime.now(UTC)))

    sense_id = profile.ensure_sense(con, sense)
    events = profile.events_for_sense(con, sense_id)

    assert len(events) == 1
    assert events[0].book is None
    assert events[0].chapter_number is None


def test_recording_an_event_with_only_one_of_book_and_chapter_number_set_is_rejected(
    tmp_path: Path,
) -> None:
    """Regel 13: Buch ohne Kapitelnummer (oder umgekehrt) ist weder ein reguläres
    Kapitel-Ereignis noch eine Vorbelegung — `record_event` weist den gemischten Fall laut
    zurück, statt eine der beiden Spalten stillschweigend NULL zu lassen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)
    sense = Sense(
        lemma=Lemma(text="life", pos="NOUN"),
        wikdict_sense="the state of being alive",
        wikdict_trans_list="Leben",
        wikdict_lexentry="eng/life__Noun__1",
    )

    with pytest.raises(ValueError):
        profile.record_event(
            con,
            Event(
                sense=sense,
                knowledge_state=KnowledgeState.KNOWN,
                origin=Origin.TRIAGE,
                timestamp=datetime.now(UTC),
                book=_BOOK,
                chapter_number=None,
            ),
        )


def test_recording_an_event_with_only_chapter_number_set_is_rejected(tmp_path: Path) -> None:
    """Gegenrichtung zu `test_recording_an_event_with_only_one_of_book_and_chapter_number_
    set_is_rejected` oben (Befund leicht, Durchsicht d8d5954): Bislang war nur „Buch ohne
    Kapitelnummer" geprüft; `_record_event`s Bedingung `(event.book is None) !=
    (event.chapter_number is None)` weist aber auch „Kapitelnummer ohne Buch" zurück — bis
    hierher unbelegt, obwohl sie hält."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    sense = Sense(
        lemma=Lemma(text="life", pos="NOUN"),
        wikdict_sense="the state of being alive",
        wikdict_trans_list="Leben",
        wikdict_lexentry="eng/life__Noun__1",
    )

    with pytest.raises(ValueError):
        profile.record_event(
            con,
            Event(
                sense=sense,
                knowledge_state=KnowledgeState.KNOWN,
                origin=Origin.TRIAGE,
                timestamp=datetime.now(UTC),
                book=None,
                chapter_number=1,
            ),
        )


def test_the_database_check_constraint_rejects_a_mixed_row_directly(tmp_path: Path) -> None:
    """Der `CHECK ((book_id IS NULL) = (chapter_number IS NULL))` aus `_SCHEMA` greift auch
    am Python vorbei (Befund leicht, Durchsicht d8d5954): Bislang war nur `_record_event`s
    eigene Prüfung getestet, nicht der DB-seitige `CHECK` selbst — eine Zeile, direkt per
    SQL eingefügt, umgeht `_record_event` vollständig. `book_id` gehört zu einem echten
    Buch (der einspaltige Fremdschlüssel auf `book(id)` bliebe sonst die eigentliche
    Fehlerursache), `chapter_number` bleibt `NULL`: Der zusammengesetzte Fremdschlüssel auf
    `chapter(book_id, number)` greift bei einer `NULL`-Spalte nicht (SQLites `MATCH
    SIMPLE`), sodass ausschließlich der `CHECK` übrigbleibt, um den Fehlschlag zu
    erklären."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    sense = Sense(
        lemma=Lemma(text="life", pos="NOUN"),
        wikdict_sense="the state of being alive",
        wikdict_trans_list="Leben",
        wikdict_lexentry="eng/life__Noun__1",
    )
    sense_id = profile.ensure_sense(con, sense)

    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO event (sense_id, knowledge_state, origin, timestamp, book_id, "
            "chapter_number) VALUES (?, ?, ?, ?, ?, NULL)",
            (sense_id, "known", "triage", datetime.now(UTC).isoformat(), book_id),
        )


def test_origin_preset_stays_distinguishable_from_origin_triage_after_reading_back(
    tmp_path: Path,
) -> None:
    """`entities.Origin.PRESET` bleibt von `Origin.TRIAGE` unterscheidbar, wenn das Profil
    zurückgelesen wird — beide Herkünfte durchlaufen dieselbe TEXT-Spalte und dieselbe
    `Origin(...)`-Auflösung beim Lesen (Warnung aus dem Auftrag: ein per SQL an `Origin`
    vorbeigeschriebenes `'preset'` brach beim Zurücklesen mit `ValueError` ab, bevor der
    Wert Teil der Aufzählung war)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    preset_sense = Sense(
        lemma=Lemma(text="life", pos="NOUN"),
        wikdict_sense="the state of being alive",
        wikdict_trans_list="Leben",
        wikdict_lexentry="eng/life__Noun__1",
    )
    triage_sense = Sense(
        lemma=Lemma(text="portrait", pos="NOUN"),
        wikdict_sense="a painted or drawn likeness of a person",
        wikdict_trans_list="Porträt",
        wikdict_lexentry="eng/portrait__Noun__1",
    )
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    profile.record_event(con, _preset_event(preset_sense, datetime.now(UTC)))
    profile.record_event(con, _event(triage_sense, KnowledgeState.KNOWN, datetime.now(UTC)))

    preset_id = profile.ensure_sense(con, preset_sense)
    triage_id = profile.ensure_sense(con, triage_sense)

    assert profile.events_for_sense(con, preset_id)[0].origin == Origin.PRESET
    assert profile.events_for_sense(con, triage_id)[0].origin == Origin.TRIAGE


def test_a_version_1_profile_is_rejected_loudly_not_upgraded_silently(tmp_path: Path) -> None:
    """Ein Profil der Fassung 1 wird nicht stillschweigend als Fassung 2 weiterverwendet:
    `open_profile` bricht sichtbar ab (Regel 13). Entscheidung aus dem Bericht zu diesem
    Bauschritt: lauter Abbruch statt Wanderung, weil im Bestand noch kein Profil der
    Fassung 1 mit Wert existiert (`data/` gibt es im Arbeitsbaum nicht) — eine Migration
    ohne echten Altbestand wäre Vorratsarbeit (Regel 14)."""
    path = tmp_path / "profil.sqlite3"
    con = sqlite3.connect(path)
    con.execute("PRAGMA user_version = 1")
    # Das historische Schema selbst ist hier nicht der Prüfgegenstand — geprüft wird der
    # Versionsabgleich beim Öffnen, deshalb genügt eine Tabelle namens event.
    con.execute("CREATE TABLE event(id INTEGER PRIMARY KEY)")
    con.commit()
    con.close()

    with pytest.raises(ValueError, match=r"nicht stillschweigend weiterverwendet"):
        profile.open_profile(path)


def test_cefr_level_can_be_set_and_read_back(tmp_path: Path) -> None:
    """Das Sprachniveau lässt sich setzen und zurücklesen: Nach `set_cefr_level(con,
    CefrLevel.B1)` liefert `get_cefr_level` wieder `CefrLevel.B1`."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    profile.set_cefr_level(con, CefrLevel.B1)

    assert profile.get_cefr_level(con) == CefrLevel.B1


def test_cefr_level_defaults_to_no_answer_and_is_distinguishable_from_a_set_level(
    tmp_path: Path,
) -> None:
    """„keine Angabe" muss sich im Schema abbilden lassen und von jedem gesetzten Niveau
    unterscheidbar bleiben: Ein frisches Profil liefert `None`, ein gesetztes Niveau einen
    `CefrLevel`, und das Zurücksetzen auf `None` ist wieder „keine Angabe", nicht etwa
    ununterscheidbar von einem gültigen Niveau."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    assert profile.get_cefr_level(con) is None

    profile.set_cefr_level(con, CefrLevel.A2)
    assert profile.get_cefr_level(con) == CefrLevel.A2

    profile.set_cefr_level(con, None)
    assert profile.get_cefr_level(con) is None


def test_set_cefr_level_still_works_if_the_learner_row_is_missing(tmp_path: Path) -> None:
    """Befund leicht, Durchsicht d8d5954: `set_cefr_level` schrieb bislang ein bloßes
    `UPDATE learner SET cefr_level = ? WHERE id = 1` — betrifft die Zeile fehlt (etwa nach
    einem manuellen Eingriff außerhalb dieses Moduls) null Zeilen und kehrt wortlos zurück
    (gegen Regel 13). `INSERT … ON CONFLICT(id) DO UPDATE` legt die Zeile stattdessen neu
    an, das Niveau ist danach lesbar."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    con.execute("DELETE FROM learner WHERE id = 1")
    con.commit()

    profile.set_cefr_level(con, CefrLevel.B2)

    assert profile.get_cefr_level(con) == CefrLevel.B2


def test_get_cefr_level_reports_a_missing_learner_row_in_german(tmp_path: Path) -> None:
    """Befund leicht, Durchsicht d8d5954: Fehlt die Einzelzeile der Tabelle `learner`
    trotzdem (Regel 13), bricht `get_cefr_level` mit einer eigenen, deutschen Meldung ab —
    nicht mit einem nackten `assert`, das unter `python -O` entfällt und die Zeile
    darunter erst mit einem englischen `TypeError` an entfernter Stelle abbrechen ließe."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    con.execute("DELETE FROM learner WHERE id = 1")
    con.commit()

    with pytest.raises(ValueError, match="learner"):
        profile.get_cefr_level(con)


def test_get_cefr_level_wraps_an_invalid_stored_value_in_a_german_message(tmp_path: Path) -> None:
    """Befund leicht, Durchsicht d8d5954: Ein Wert außerhalb der `CefrLevel`-Aufzählung in
    der Spalte (etwa nach einem manuellen Eingriff) ließ bislang `CefrLevel(...)`s
    englische Fremdmeldung („'c2' is not a valid CefrLevel") unverändert durch — laut, aber
    gegen die Sprachregel (dokumentation.md §1). `get_cefr_level` kapselt sie jetzt wie das
    Modul es sonst mit sqlite3s englischen Meldungen tut."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    con.execute("UPDATE learner SET cefr_level = ? WHERE id = 1", ("c2",))
    con.commit()

    with pytest.raises(ValueError, match="c2") as excinfo:
        profile.get_cefr_level(con)
    assert "is not a valid" not in str(excinfo.value)


def test_event_sense_id_index_exists(tmp_path: Path) -> None:
    """Regel 14, gemessener Anlass (technik.md §4, Schemafassung 2): Bei rund 18.600
    Ereignissen kostet `compare_chapter_vocabulary` je Kapitel 2,1 s statt 0,4 s ohne
    einen Index auf `event(sense_id)`. Geprüft wird, dass der Index existiert — nicht
    seine Ausführungszeit, die gehört nicht in die Tests (dokumentation.md §5)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")

    indexes = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'event'"
        )
    }

    assert "event_sense_id" in indexes


# ----------------------------------------------- record_preset (Bauschritt 3/5 der
# ----------------------------------------------- Vorbelegung, 31.08.2026)


def test_record_preset_books_every_given_event_and_sets_the_level(tmp_path: Path) -> None:
    """`record_preset` schreibt jedes übergebene Ereignis und setzt das Sprachniveau in
    einer Transaktion. Auftragstext: „gebucht wird alle Wörterbuchbedeutungen einer
    vorbelegten Grundform" — beide Bedeutungen von `bank` (Geldinstitut, Flussufer) landen
    hier als zwei Ereignisse, nicht nur die bestbewertete."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    bank_institution = Sense(
        lemma=Lemma(text="bank", pos="NOUN"),
        wikdict_sense="institution",
        wikdict_trans_list="Bank",
        wikdict_lexentry="eng/bank__Noun__1",
    )
    bank_shore = Sense(
        lemma=Lemma(text="bank", pos="NOUN"),
        wikdict_sense="edge of river or lake",
        wikdict_trans_list="Ufer",
        wikdict_lexentry="eng/bank__Noun__2",
    )
    red_sense = Sense(
        lemma=Lemma(text="red", pos="ADJ"),
        wikdict_sense="having red as its colour",
        wikdict_trans_list="rot | Rot",
        wikdict_lexentry="eng/red__Adjective__1",
    )
    timestamp = datetime.now(UTC)
    events = [
        _preset_event(bank_institution, timestamp),
        _preset_event(bank_shore, timestamp),
        _preset_event(red_sense, timestamp),
    ]

    profile.record_preset(con, events, CefrLevel.A1)

    assert con.execute("SELECT count(*) FROM event").fetchone()[0] == 3
    assert profile.get_cefr_level(con) == CefrLevel.A1
    for sense in (bank_institution, bank_shore, red_sense):
        sense_id = profile.ensure_sense(con, sense)
        recorded = profile.events_for_sense(con, sense_id)
        assert len(recorded) == 1
        assert recorded[0].origin == Origin.PRESET
        assert recorded[0].knowledge_state == KnowledgeState.KNOWN
        assert recorded[0].book is None
        assert recorded[0].chapter_number is None


def test_record_preset_writes_nothing_if_one_event_fails_partway_through(tmp_path: Path) -> None:
    """Auftragstext: „Die Vorbelegung muss es ganz oder gar nicht geben — ein halb
    geschriebenes Profil ist schlimmer als keins." Ein naiver Zeitstempel im dritten von
    drei Ereignissen bricht `record_preset` ab (Regel 13, `_record_event`) — im Profil
    steht danach **nichts** von diesem Aufruf: weder die beiden zuvor gültigen Ereignisse
    noch die dafür angelegten lemma-/sense-Zeilen noch das Niveau."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    good_sense_1 = Sense(
        lemma=Lemma(text="bank", pos="NOUN"),
        wikdict_trans_list="Bank",
        wikdict_lexentry="eng/bank__Noun__1",
    )
    good_sense_2 = Sense(
        lemma=Lemma(text="red", pos="ADJ"),
        wikdict_trans_list="rot",
        wikdict_lexentry="eng/red__Adjective__1",
    )
    broken_sense = Sense(
        lemma=Lemma(text="street", pos="NOUN"),
        wikdict_trans_list="Straße",
        wikdict_lexentry="eng/street__Noun__1",
    )
    naive_timestamp = datetime(2026, 8, 31, 12, 0, 0)  # ohne Zeitzone
    events = [
        _preset_event(good_sense_1, datetime.now(UTC)),
        _preset_event(good_sense_2, datetime.now(UTC)),
        Event(
            sense=broken_sense,
            knowledge_state=KnowledgeState.KNOWN,
            origin=Origin.PRESET,
            timestamp=naive_timestamp,
            book=None,
            chapter_number=None,
        ),
    ]

    with pytest.raises(ValueError):
        profile.record_preset(con, events, CefrLevel.B1)

    assert con.execute("SELECT count(*) FROM event").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM sense").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM lemma").fetchone()[0] == 0
    assert profile.get_cefr_level(con) is None


# ----------------------------------------------- backup und dump (AP 13, Sicherung und
# ----------------------------------------------- Ausleiten)


class _FakeCursor:
    """Hilfsklasse für `_FakeSourceConnection` unten — liefert eine feste Zeile auf
    `fetchone()`, genau wie `sqlite3.Cursor` nach `PRAGMA database_list`."""

    def __init__(self, row: tuple[object, ...]) -> None:
        self._row = row

    def fetchone(self) -> tuple[object, ...]:
        return self._row


class _FakeSourceConnection:
    """Steh-Ersatz für `sqlite3.Connection`, nur für die beiden Reihenfolge-Proben unten
    (Nachbesserung Durchsicht b86c554, „Punkt 7 der Durchsicht"): Das echte
    `sqlite3.Connection.backup` liefe ohne eine der beiden Wachen in die gemessene
    endlose `SQLITE_BUSY`-Folge (siehe die beiden Tests oben, `timeout`-Probe im
    Bericht) — eine Verfälschungsprobe an der echten Verbindung würde also nicht rot,
    sondern **hängen** (dokumentation.md §5, „Ein hängender Test genügt nicht"). Dieser
    Ersatz wirft in `backup()` stattdessen sofort, damit eine entfernte Wache die Probe
    in Millisekunden rot macht."""

    def __init__(self, source_path: Path, *, in_transaction: bool) -> None:
        self.in_transaction = in_transaction
        self._source_path = source_path
        self.reached_backup = False

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> _FakeCursor:
        assert sql.strip() == "PRAGMA database_list", f"unerwarteter Aufruf: {sql!r}"
        return _FakeCursor((0, "main", str(self._source_path)))

    def backup(self, target: sqlite3.Connection) -> None:
        self.reached_backup = True
        raise AssertionError(
            "con.backup wurde erreicht — eine Wache hätte das vorher verhindern müssen"
        )


def test_backup_checks_the_target_guard_before_ever_touching_con_backup(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht b86c554, „Punkt 7 der Durchsicht": Die Ziel-Wache
    (B1) feuert, bevor `con.backup` überhaupt erreicht wird — mit dem Steh-Ersatz oben
    geprüft, damit das Entfernen der Wache diesen Test **rot** macht statt ihn hängen zu
    lassen. Welcher Test bei welcher Verfälschung fällt: `_reject_backup_target_equal_to_
    source` im Rumpf von `profile.backup` auskommentiert → dieser Test schlägt fehl, weil
    `fake.reached_backup` dann `True` wird (`AssertionError` statt der erwarteten
    `ValueError`), in Millisekunden, nicht nach einem Zeitlimit."""
    source_path = tmp_path / "profil.sqlite3"
    fake = _FakeSourceConnection(source_path, in_transaction=False)

    with pytest.raises(ValueError, match="dieselbe Datei"):
        profile.backup(cast(sqlite3.Connection, fake), source_path)

    assert not fake.reached_backup


def test_backup_checks_the_transaction_guard_before_ever_touching_con_backup(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht b86c554, „Punkt 7 der Durchsicht": Die
    Transaktions-Wache (B2) feuert ebenso, bevor `con.backup` erreicht wird. Welcher Test
    bei welcher Verfälschung fällt: `_reject_open_transaction` im Rumpf von
    `profile.backup` auskommentiert → dieser Test schlägt fehl (`AssertionError` statt
    `ValueError`), wieder in Millisekunden."""
    fake = _FakeSourceConnection(tmp_path / "profil.sqlite3", in_transaction=True)

    with pytest.raises(ValueError, match="offene Transaktion"):
        profile.backup(cast(sqlite3.Connection, fake), tmp_path / "sicherung.sqlite3")

    assert not fake.reached_backup


def test_backup_is_a_valid_profile_of_the_same_schema_version(tmp_path: Path) -> None:
    """AP 13, Prüfung: Die Sicherung ist wirklich ein gültiges Profil derselben
    Schemafassung — geöffnet mit `profile.open_profile` und inhaltlich gegen die Quelle
    verglichen, nicht nur als vorhandene, nicht-leere Datei angenommen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    sense = Sense(
        lemma=Lemma(text="draw", pos="VERB"),
        wikdict_sense="to pull out, unsheath",
        wikdict_trans_list="ziehen | herausziehen",
        wikdict_lexentry="eng/draw__Verb__1",
    )
    profile.record_event(con, _event(sense, KnowledgeState.KNOWN, datetime.now(UTC)))

    target = tmp_path / "sicherung.sqlite3"
    profile.backup(con, target)

    backup_con = profile.open_profile(target)
    assert backup_con.execute("PRAGMA user_version").fetchone()[0] == profile.SCHEMA_VERSION
    sense_id = profile.ensure_sense(backup_con, sense)
    events = profile.events_for_sense(backup_con, sense_id)
    assert [e.knowledge_state for e in events] == [KnowledgeState.KNOWN]
    assert events[0].book == _BOOK


def test_backup_aborts_on_a_still_open_transaction_instead_of_committing_it(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht b86c554, B2 `mittel`: Eine Sicherung ist dem Namen nach
    ein Lesevorgang. Steht auf `con` noch eine offene Transaktion (hier eine
    ungeschriebene `book`-Zeile), bricht `backup` sichtbar ab (Regel 13), statt sie
    ungefragt festzuschreiben — ein `con.rollback()` des Aufrufers muss danach noch
    wirksam sein können. Vorher committete `backup` an dieser Stelle still; das war die
    Berufung auf Regel 13 auf dem Kopf, denn die Regel verlangt einen sichtbaren
    Fehlschlag, nicht ein verdecktes Festschreiben."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)
    con.execute("INSERT INTO book (title, author) VALUES (?, ?)", ("Unbestätigtes Buch", "N. N."))
    # bewusst kein commit an dieser Stelle — die Verbindung bleibt mittendrin offen.

    target = tmp_path / "sicherung.sqlite3"
    with pytest.raises(ValueError, match="offene Transaktion"):
        profile.backup(con, target)

    assert not target.exists()
    con.rollback()
    titles = {row[0] for row in con.execute("SELECT title FROM book")}
    assert "Unbestätigtes Buch" not in titles


def test_backup_rejects_a_target_that_is_the_source_file_itself(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht b86c554, B1 `schwer`: Zeigt `target` auf dieselbe Datei,
    aus der `con` liest, verklemmt sich `sqlite3.Connection.backup` mit sich selbst —
    endlos, ohne Ausnahme, ohne Zeitlimit (gemessen: 20 s ohne jede Reaktion, siehe
    Bericht). `backup` prüft das vorab und bricht sichtbar ab (Regel 13), statt den
    Stillstand überhaupt zu erreichen — die Probe hier muss deshalb in Millisekunden
    laufen, nicht erst nach einem Zeitlimit."""
    path = tmp_path / "profil.sqlite3"
    con = profile.open_profile(path)
    profile.ensure_book(con, _BOOK)

    with pytest.raises(ValueError, match="dieselbe Datei"):
        profile.backup(con, path)

    with pytest.raises(ValueError, match="dieselbe Datei"):
        profile.backup(con, tmp_path / ".." / tmp_path.name / "profil.sqlite3")


def test_dump_aborts_on_a_still_open_transaction_instead_of_reading_it(tmp_path: Path) -> None:
    """Nachbesserung Durchsicht b86c554, B2 `mittel`, Nebenbefund: `dump` committet
    nirgends, liest aber klaglos die ungeschriebenen Zeilen der eigenen, noch offenen
    Transaktion mit — der Auszug enthielte dann Zeilen, die nach einem `rollback()` nie
    im Profil standen. Dieselbe Wache wie bei `backup` macht daraus einen sichtbaren
    Abbruch."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)
    con.execute("INSERT INTO book (title, author) VALUES (?, ?)", ("Unbestätigtes Buch", "N. N."))
    # bewusst kein commit an dieser Stelle — die Verbindung bleibt mittendrin offen.

    target = tmp_path / "auszug.json"
    with pytest.raises(ValueError, match="offene Transaktion"):
        profile.dump(con, target)

    assert not target.exists()


def test_backup_aborts_with_a_german_message_if_the_target_directory_is_missing(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht b86c554, B5 `leicht`: Fehlt das Zielverzeichnis der
    Sicherung, bricht `backup` mit einer deutschen Meldung ab — statt `sqlite3`s
    englische Fremdmeldung `unable to open database file` unverändert durchzureichen,
    dasselbe Muster wie `open_profile` (`test_missing_profile_directory_is_a_visible_
    failure_with_a_german_message` oben)."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)

    with pytest.raises(ValueError, match=r"does_not_exist.*existiert nicht"):
        profile.backup(con, tmp_path / "does_not_exist" / "sicherung.sqlite3")


def test_dump_aborts_with_a_german_message_if_the_target_directory_is_missing(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht b86c554, B5 `leicht`: Fehlt das Zielverzeichnis des
    Auszugs, bricht `dump` mit einer deutschen Meldung ab — statt Pythons englische
    `FileNotFoundError` unverändert durchzureichen."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)

    with pytest.raises(ValueError, match=r"does_not_exist.*existiert nicht"):
        profile.dump(con, tmp_path / "does_not_exist" / "auszug.json")


def test_dump_preserves_the_previous_export_if_writing_fails_partway_through(
    tmp_path: Path,
) -> None:
    """Nachbesserung Durchsicht b86c554, B4 `mittel`: Bricht das Schreiben mitten im
    JSON-Auszug ab — hier ein `BLOB`-Wert, den `json.dump` nicht serialisieren kann
    (über Roh-SQL eingeschleust, weil die öffentliche Schnittstelle nur `TEXT`/
    `INTEGER`-Spalten befüllt; jeder andere Schreibfehler, etwa eine volle Platte, träfe
    denselben Pfad) —, bleibt der zuvor am Zielort liegende, gültige Auszug unverändert.
    `dump` schreibt seit dieser Nachbesserung zuerst in eine Nachbardatei und zieht sie
    erst nach vollständigem Schreiben per `Path.replace` an den Zielort; vorher leerte
    `target.open("w")` die Datei sofort und hinterließ bei einem Abbruch ein
    abgeschnittenes Bruchstück mit `.json`-Namen statt des alten Auszugs. Welcher Test
    bei welcher Verfälschung fällt: `Path.replace`-Umweg entfernt, wieder direkt in
    `target` geschrieben → dieser Test schlägt fehl, weil `target` dann das Bruchstück
    `{"book": [...` statt des alten, vollständigen Auszugs enthält."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    profile.ensure_book(con, _BOOK)

    target = tmp_path / "auszug.json"
    profile.dump(con, target)
    previous_content = target.read_text(encoding="utf-8")

    con.execute("UPDATE book SET title = ? WHERE title = ?", (b"\x00\x01", _BOOK.title))
    con.commit()

    with pytest.raises(TypeError):
        profile.dump(con, target)

    assert target.read_text(encoding="utf-8") == previous_content
    assert not target.with_name(target.name + ".tmp").exists()


def test_dump_contains_every_table_and_column_of_the_live_schema(tmp_path: Path) -> None:
    """AP 13, Prüfung: Der Auszug enthält alle acht Tabellen mit allen ihren Spalten.
    Erwartungsmenge aus dem Schema selbst abgeleitet (`sqlite_master`, `PRAGMA
    table_info`), nicht hier noch einmal hingeschrieben — sonst schwiege dieser Test bei
    einer künftigen Schemafassung mit neunter Tabelle oder neuer Spalte
    (dokumentation.md §5). Die gefundene Tabellenzahl wird gegen die bekannte acht
    gehalten, damit eine leere Erwartungsmenge nicht grün durchginge (dokumentation.md
    §10, „ein eigenes Prüfskript wird gegen eine bekannte Größe gehalten")."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    card = _card_for(_occurrence())
    profile.record_card(con, card)
    profile.record_event(con, _event(card.sense, KnowledgeState.KNOWN, datetime.now(UTC)))
    profile.set_cefr_level(con, CefrLevel.B1)

    target = tmp_path / "auszug.json"
    profile.dump(con, target)

    with target.open(encoding="utf-8") as file:
        dumped = json.load(file)

    expected_tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert len(expected_tables) == 8
    assert set(dumped.keys()) == expected_tables

    for table in expected_tables:
        expected_columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        assert dumped[table], f"Tabelle {table} hat im Testaufbau keine Zeile"
        for row in dumped[table]:
            assert set(row.keys()) == expected_columns


def test_dump_contains_every_event_not_only_the_current_knowledge_state(tmp_path: Path) -> None:
    """AP 13, Prüfung: „JSON enthält jedes Ereignis" — die volle Ereignisfolge, nicht nur
    der aktuelle Kenntnisstand (technik.md §4, „Kernentscheidung: Ereignisfolge statt
    überschreibbarem Zustand"). Zwei Ereignisse zu derselben Bedeutung erscheinen beide im
    Auszug."""
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

    target = tmp_path / "auszug.json"
    profile.dump(con, target)

    with target.open(encoding="utf-8") as file:
        dumped = json.load(file)

    assert len(dumped["event"]) == 2
    assert {row["knowledge_state"] for row in dumped["event"]} == {"learning", "known"}


def test_dump_writes_valid_utf8_for_a_typographic_character_in_the_example_sentence(
    tmp_path: Path,
) -> None:
    """CLAUDE.md, „Dateien immer mit encoding=»utf-8« öffnen": Unter Windows zerstört die
    Systemkodierung sonst still typografische Zeichen aus dem Buchtext — hier ein
    typografischer Apostroph in `occurrence.example_sentence`, der den Auszug unlesbar
    machen würde, wenn `dump` die Datei nicht ausdrücklich als UTF-8 schriebe.

    Nachbesserung Durchsicht b86c554, B6 `leicht`: Der Apostroph muss zusätzlich **roh
    im Dateitext** stehen, nicht nur nach `json.load` zurückkommen — sonst hielte diese
    Zusicherung auch bei `ensure_ascii=True` (`\\u2019` statt `’`), obwohl der Auszug für
    einen Menschen dann unlesbar wäre und `dump`s eigene Begründung („lesbar") nicht mehr
    zuträfe. Welcher Test bei welcher Verfälschung fällt: `ensure_ascii=False` →
    `ensure_ascii=True` im Rumpf von `dump` lässt genau diese Zeile fehlschlagen, ohne
    dass `json.load(...)` das noch bemerken würde."""
    con = profile.open_profile(tmp_path / "profil.sqlite3")
    book_id = profile.ensure_book(con, _BOOK)
    _add_chapter(con, book_id)
    occurrence = Occurrence(
        book=_BOOK,
        chapter_number=1,
        lemma=Lemma(text="watch", pos="NOUN"),
        word_form="watch",
        example_sentence="He’d checked his watch — half past nine.",
        frequency=1,
        proper_noun_frequency=0,
    )
    profile.ensure_occurrence(con, occurrence)

    target = tmp_path / "auszug.json"
    profile.dump(con, target)

    raw_text = target.read_text(encoding="utf-8")
    assert "He’d checked his watch — half past nine." in raw_text

    with target.open(encoding="utf-8") as file:
        dumped = json.load(file)

    sentences = {row["example_sentence"] for row in dumped["occurrence"]}
    assert "He’d checked his watch — half past nine." in sentences
