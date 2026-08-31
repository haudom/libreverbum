"""Prüft die eingefrorene Grundwortschatzliste `libreverbum/wordfreq_en_5000.txt` gegen
konzept.md, „Bewusst offen" (erster Punkt) und gegen `tools/build_wordfreq_preset.py`.

Die Datei selbst ist Bauschritt 1 von fünf: Sie wird hier erzeugt, eingefroren und mit
Lizenzunterlagen versehen. `Origin.PRESET` und das Einlesen beim Anlegen des Profils
kommen in einem späteren Schritt (Bauschritt 2) — diese Tests prüfen ausschließlich die
Datei und das Erzeugungsskript, nicht deren spätere Verwendung im Kern.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRESET_PATH = REPO_ROOT / "libreverbum" / "wordfreq_en_5000.txt"
BUILD_SCRIPT = REPO_ROOT / "tools" / "build_wordfreq_preset.py"
EXPECTED_N = 5000


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split("\n")


def _entries(path: Path) -> list[str]:
    """Grundformen ohne den Kopf — jede Zeile, die nicht mit ``#`` beginnt und nicht leer
    ist. Dieselbe Regel, mit der ein späterer Leser die Datei einliest."""
    return [line for line in _lines(path) if line and not line.startswith("#")]


def test_wordfreq_preset_file_exists() -> None:
    """Bauschritt 1: `libreverbum/wordfreq_en_5000.txt` liegt im Repository, nicht in
    `data/` — sie gehört zum ausgelieferten Programm, nicht zu den Nutzerdaten
    (technik.md §9)."""
    assert PRESET_PATH.is_file()


def test_wordfreq_preset_has_exactly_n_entries() -> None:
    """Die eingefrorene Liste hält genau N=5.000 Grundformen — die Länge des größten
    vorgesehenen Niveau-Präfixes (C1), nicht mehr und nicht weniger."""
    assert len(_entries(PRESET_PATH)) == EXPECTED_N


def test_wordfreq_preset_entries_have_no_duplicates() -> None:
    """Jede Grundform steht genau einmal — Regel 4 der Bildungsregeln (Rang der
    häufigsten Oberflächenform) fasst alle Formen einer Grundform zu einem Eintrag
    zusammen."""
    entries = _entries(PRESET_PATH)
    assert len(entries) == len(set(entries))


def test_wordfreq_preset_entries_are_lowercase() -> None:
    """Grundformen stehen klein — `token.lemma_.lower()` aus Bildungsregel 3."""
    entries = _entries(PRESET_PATH)
    assert all(entry == entry.lower() for entry in entries)


def test_wordfreq_preset_order_is_rank_order() -> None:
    """Die Liste steht in Rangfolge, häufigste zuerst: `the` (Rang 1) steht vor `never`
    (Rang 108, aus der Messung), das wiederum vor `seem` (Rang 468)."""
    entries = _entries(PRESET_PATH)
    assert entries.index("the") < entries.index("never") < entries.index("seem")


def test_wordfreq_preset_known_ranks_match_the_measurement() -> None:
    """Stichprobe aus der Messung, die die Entscheidung für `wordfreq` trägt: `the` auf
    Rang 1, `never` auf Rang 108, `seem` auf Rang 468 (1-gezählt)."""
    entries = _entries(PRESET_PATH)
    assert entries.index("the") == 0
    assert entries.index("never") == 107
    assert entries.index("seem") == 467


def test_wordfreq_preset_excludes_book_specific_vocabulary() -> None:
    """Ein Grundwortschatz aus `wordfreq` ist kein Buchvokabular: `tawdry`, `lurid`,
    `courteously` und `listlessly` — die Wörter, die ein echtes Kapitel schwer machen
    (konzept.md, „Bewusst offen") — stehen **nicht** in den 5.000 häufigsten
    Grundformen (gemessen)."""
    entries = set(_entries(PRESET_PATH))
    for word in ("tawdry", "lurid", "courteously", "listlessly"):
        assert word not in entries


def test_wordfreq_preset_header_precedes_all_entries() -> None:
    """Der Kopf besteht ausschließlich aus mit ``#`` beginnenden Zeilen **vor** der ersten
    Grundform — ein Leser, der solche Zeilen überspringt, verliert dadurch keinen
    Eintrag und gewinnt keine Kopfzeile versehentlich als Wort dazu."""
    lines = [line for line in _lines(PRESET_PATH) if line]
    first_entry_index = next(i for i, line in enumerate(lines) if not line.startswith("#"))
    assert all(line.startswith("#") for line in lines[:first_entry_index])
    assert not any(line.startswith("#") for line in lines[first_entry_index:])
    assert first_entry_index > 0


def test_wordfreq_preset_header_names_its_own_beauty_flaw() -> None:
    """Der Kopf nennt die Mehrworteinträge, die durch die Lemmatisierung entstehen (tote
    Plätze, die nie auf eine Grundform des Kerns treffen können) — sonst hält ein
    späterer Leser sie für einen Fehler."""
    header = "\n".join(line for line in _lines(PRESET_PATH) if line.startswith("#"))
    assert "Mehrworteinträge" in header or "Mehrworteintr" in header
    multiword_entries = [entry for entry in _entries(PRESET_PATH) if " " in entry]
    assert multiword_entries  # der Schönheitsfehler existiert tatsächlich
    for entry in multiword_entries:
        assert entry in header


def test_wordfreq_preset_header_names_license_and_source() -> None:
    """Der Kopf trägt Lizenzhinweis und Herkunft, damit die Datei ohne das
    Erzeugungsskript verständlich bleibt (Auftrag, „Format")."""
    header = "\n".join(line for line in _lines(PRESET_PATH) if line.startswith("#"))
    assert "wordfreq" in header
    assert "CC BY-SA" in header
    assert "NOTICE" in header
    assert "en_core_web_md" in header


@pytest.mark.needs_wordfreq
def test_build_wordfreq_preset_reproduces_the_shipped_wordlist(tmp_path: Path) -> None:
    """Regel (dokumentation.md §5, „Woran geprüft wird"): Was über den Inhalt einer
    Fremdquelle behauptet wird, wird zusätzlich gegen das echte Gegenüber geprüft —
    `tools/build_wordfreq_preset.py` erzeugt aus dem echten `wordfreq`-Paket dieselbe
    Grundformenliste wie die im Repository eingefrorene Datei."""
    forms_path = tmp_path / "formen.json"
    out_path = tmp_path / "wordfreq_en_5000.txt"

    subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "export-forms", str(forms_path)],
        check=True,
        cwd=REPO_ROOT,
    )
    subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "build",
            str(forms_path),
            "--out",
            str(out_path),
            "--n",
            str(EXPECTED_N),
        ],
        check=True,
        cwd=REPO_ROOT,
    )

    assert _entries(out_path) == _entries(PRESET_PATH)
