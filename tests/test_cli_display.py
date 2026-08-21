"""Prüft `cli/display.py` — Bildschirmausgabe auf einer eingeschränkten Konsole
(bauplan.md T16; CLAUDE.md, „Dateien immer mit encoding=utf-8 öffnen")."""

from __future__ import annotations

import io

from cli.display import safe_print


def test_safe_print_does_not_crash_on_a_restricted_console_codepage() -> None:
    """Ein Belegsatz mit typografischen Anführungszeichen darf die Triage auf einer
    Konsole mit eingeschränkter Kodierung nicht mit `UnicodeEncodeError` abbrechen
    lassen (dokumentation.md §4 Regel 13).

    `cp850` statt `cp1252`: cp1252 enthält „ “ und — bereits (Microsofts ANSI-Codepage
    ist für westeuropäische Typografie ausgelegt); `cp850`, die klassische
    DOS-/conhost-OEM-Codepage älterer Windows-Konsolen, dagegen nicht — an ihr greift
    die Gefahr, vor der dieser Test schützt, tatsächlich."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp850", errors="strict")

    safe_print(
        "„Curiouser and curiouser!“ cried Alice — a dash and typographic quotes.", stream=stream
    )

    stream.flush()  # löst einen zurückgehaltenen UnicodeEncodeError erst hier aus


def test_safe_print_writes_the_original_text_on_a_capable_console() -> None:
    """Auf einer Konsole, die das Zeichen darstellen kann, wird nichts verändert."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")

    safe_print("„Test“", stream=stream)
    stream.flush()

    stream.seek(0)
    assert stream.buffer.getvalue().decode("utf-8").strip() == "„Test“"
