"""Prüft `cli/display.py` — Bildschirmausgabe auf einer eingeschränkten Konsole
(bauplan.md T16; CLAUDE.md, „Dateien immer mit encoding=utf-8 öffnen") und, seit
Bauschritt 2/2 der Konsolenausgabe (Auftragstext vom 02.09.2026), den Ausgabestil der
Triage-Anzeige (technik.md §13, „Triage-Anzeige")."""

from __future__ import annotations

import io

from cli.display import (
    _SPECIAL_CHARS,
    Style,
    _enable_windows_console_color,
    arrow,
    bold,
    cover,
    detect_style,
    dim,
    dot,
    entry_rule,
    finish_progress_line,
    headline,
    highlight,
    quote,
    safe_print,
    safe_print_progress,
    wrap_indented,
)


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


def test_safe_print_progress_does_not_crash_on_a_restricted_console_codepage() -> None:
    """Auftragstext vom 25.08.2026, Abschnitt 3: Die Fortschrittszeile muss auf einer
    cp850-Konsole überleben, genau wie `safe_print` (Regel 13, dokumentation.md §4) —
    dieselbe Bauart wie
    `test_safe_print_does_not_crash_on_a_restricted_console_codepage`."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp850", errors="strict")

    safe_print_progress(
        "Bedeutungen werden aufgelöst: 37 von 412 geprüft, 12 von 25 behalten.", stream=stream
    )

    stream.flush()  # löst einen zurückgehaltenen UnicodeEncodeError erst hier aus


def test_safe_print_progress_writes_a_carriage_return_instead_of_a_newline() -> None:
    """Eine sich fortschreibende Statuszeile schreibt sich per Wagenrücklauf (`\\r`) selbst
    über sich — kein Zeilenumbruch, sonst entstünden „keine 400 Zeilen Protokoll", sondern
    eine wachsende Anzahl echter Zeilen (Auftragstext, Abschnitt 3)."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")

    safe_print_progress("1 von 10 geprüft, 0 von 5 behalten.", stream=stream)
    safe_print_progress("2 von 10 geprüft, 0 von 5 behalten.", stream=stream)
    stream.flush()

    stream.seek(0)
    written = stream.buffer.getvalue().decode("utf-8")
    assert written == "\r1 von 10 geprüft, 0 von 5 behalten.\r2 von 10 geprüft, 0 von 5 behalten."
    assert "\n" not in written


def test_finish_progress_line_closes_the_line_before_the_next_regular_output() -> None:
    """Ohne diesen Aufruf verstümmelt der fehlende Zeilenumbruch die erste reguläre
    Ausgabe danach (etwa die erste Triage-Frage) — der Wagenrücklauf setzt den Cursor nur
    zurück, er löscht nichts (Auftragstext, Abschnitt 3, „sauber abschließen, bevor die
    erste Frage kommt")."""
    # newline="": ohne Übersetzung von "\n" in os.linesep — sonst hinge das erwartete
    # Ergebnis unten vom Betriebssystem ab (Windows übersetzt sonst in "\r\n").
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")

    safe_print_progress("5 von 10 geprüft, 2 von 5 behalten.", stream=stream)
    finish_progress_line(stream=stream)
    safe_print("== Wörter ==", stream=stream)
    stream.flush()

    stream.seek(0)
    written = stream.buffer.getvalue().decode("utf-8")
    assert written == "\r5 von 10 geprüft, 2 von 5 behalten.\n== Wörter ==\n"


# ---------------------------------------------------------- Ausgabestil (detect_style)


class _FakeStream:
    """Ein Strom, dessen `isatty()` und `encoding` sich für einen Test vorgeben lassen —
    ohne echtes Terminal, wie der Auftragstext es verlangt („Sorg dafür, dass Tests …
    prüfen können, ohne ein echtes Terminal zu brauchen")."""

    def __init__(self, *, isatty: bool, encoding: str = "utf-8") -> None:
        self._isatty = isatty
        self.encoding = encoding

    def isatty(self) -> bool:
        return self._isatty


def test_detect_style_disables_color_without_a_terminal() -> None:
    """Kein echtes Terminal (`isatty()` falsch, etwa eine umgeleitete Datei) — keine Farbe,
    unabhängig vom Betriebssystem.

    Verfälschungsprobe: `supports_color = True` fest statt `_stream_is_a_terminal(target)
    and …` ausgewertet ließ diesen Test rot werden (siehe Bericht)."""
    style = detect_style(_FakeStream(isatty=False))  # type: ignore[arg-type]

    assert style.supports_color is False


def test_detect_style_disables_unicode_on_a_restricted_console_codepage() -> None:
    """Dieselbe gefährliche Codepage wie bei `safe_print` (`cp850`, siehe oben) — sie
    stellt `─`/`→`/`·` nicht dar, `supports_unicode` muss deshalb falsch sein.

    Verfälschungsprobe: `_stream_supports_unicode` fest `True` liefern lassen (statt den
    `encode`-Versuch auszuwerten) ließ diesen Test rot werden."""
    style = detect_style(_FakeStream(isatty=False, encoding="cp850"))  # type: ignore[arg-type]

    assert style.supports_unicode is False


def test_detect_style_enables_unicode_on_a_capable_console() -> None:
    """Eine Kodierung, die die Sonderzeichen trägt (`utf-8`), liefert `supports_unicode =
    True` — das Gegenstück zur vorigen Prüfung, sonst wäre nur die Ausweichrichtung
    geprüft, nicht die eigentliche Fähigkeit."""
    style = detect_style(_FakeStream(isatty=False, encoding="utf-8"))  # type: ignore[arg-type]

    assert style.supports_unicode is True


def test_detect_style_treats_a_missing_encoding_as_unable_to_render_special_characters() -> None:
    """Ein Strom ohne `encoding`-Attribut (etwa ein einfaches Test-Double) gilt als
    unfähig, nicht als fähig — der sichere Fehlschlag ist der ASCII-Ersatz, nicht ein
    Bildschirm voller `?`."""

    class _NoEncoding:
        def isatty(self) -> bool:
            return False

    style = detect_style(_NoEncoding())  # type: ignore[arg-type]

    assert style.supports_unicode is False


class _TTYWithoutFileno:
    """Bejaht `isatty()` wie ein echtes Terminal, hat aber kein `fileno()` — das
    Test-Double, das der eigene Docstring von `_enable_windows_console_color` ausdrücklich
    als Beispiel nennt („kein `fileno()` … etwa ein Test-Double")."""

    def __init__(self, *, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    def isatty(self) -> bool:
        return True


def test_enable_windows_console_color_returns_false_for_a_tty_without_fileno() -> None:
    """Befund 1 (Durchsicht e537273): Der Docstring von `_enable_windows_console_color`
    versprach, jeder Fehlschlag beim Ermitteln des Konsolen-Handles liefere `False` statt
    einer durchgereichten Ausnahme — gefangen wurde aber nur `OSError`, nicht
    `AttributeError`. Ein Ziel, das `isatty()` bejaht und kein `fileno()` hat, brach damit
    mit `AttributeError` ab. Vor dieser Behebung gab es dafür **keinen** Test: In
    `tests/` rief nichts `_enable_windows_console_color` auf, und `_FakeStream` wurde nur
    mit `isatty=False` benutzt — die conhost-Falle aus technik.md §13 war unbelegt.

    Verfälschungsprobe: `except OSError` statt `except (AttributeError, OSError)` (der
    Stand vor dieser Behebung) lässt diesen Test mit einer durchgereichten
    `AttributeError` statt einem Rückgabewert fehlschlagen — siehe Bericht."""
    assert _enable_windows_console_color(_TTYWithoutFileno()) is False  # type: ignore[arg-type]


def test_detect_style_does_not_crash_for_a_terminal_like_double_without_fileno() -> None:
    """Dieselbe Zusicherung wie oben, über den vollen Weg (`detect_style` statt der
    privaten Funktion direkt) — `cli.main.main` wertet `detect_style()` außerhalb seines
    eigenen `try`-Blocks aus (Befund 1), eine hier durchgereichte Ausnahme liefe also als
    englischer Traceback durch, an allen drei Fängen vorbei."""
    style = detect_style(_TTYWithoutFileno())  # type: ignore[arg-type]

    assert style.supports_color is False


def test_special_chars_probe_covers_the_double_rule_drawn_by_cover() -> None:
    """Befund 2 (Durchsicht e537273): `cover` zeichnet die doppelte Trennlinie `═`
    (U+2550) — vor dieser Behebung stand sie nicht in `_SPECIAL_CHARS`, die Probe deckte
    also nicht ab, was `cli.interaction` über `cover` tatsächlich auf den Bildschirm
    bringt. Folgenlos an jeder der 14 Standard-Codecs, die die übrigen vier Zeichen
    tragen (sie tragen auch `═`), aber die Absicherung war unvollständig.

    Verfälschungsprobe: `═` wieder aus `_SPECIAL_CHARS` entfernt lässt diesen Test rot
    werden."""
    assert "═" in _SPECIAL_CHARS


# --------------------------------------------------------- Textbausteine (Style-Funktionen)

_COLOR = Style(supports_color=True, supports_unicode=True, width=80)
_PLAIN = Style(supports_color=False, supports_unicode=False, width=80)


def test_bold_dim_highlight_are_unchanged_without_color() -> None:
    """Ohne Farbfähigkeit bleiben `bold`/`dim`/`highlight` unverändert — die Zusicherung,
    auf der die farblose Spielart der Triage-Anzeige beruht.

    Verfälschungsprobe: `_decorate` fest die ANSI-Codes anhängen lassen, ohne
    `style.supports_color` zu prüfen, ließ diesen Test rot werden."""
    assert bold("lurid", _PLAIN) == "lurid"
    assert dim("3 von 13", _PLAIN) == "3 von 13"
    assert highlight("grell", _PLAIN) == "grell"


def test_bold_dim_highlight_wrap_ansi_codes_with_color() -> None:
    """Mit Farbfähigkeit tragen die drei Bausteine je einen eigenen ANSI-Code und enden
    mit dem Rücksetz-Code — unterschiedliche Codes, damit Fettdruck, Dimmen und
    Hervorhebung optisch auseinanderzuhalten sind."""
    assert bold("lurid", _COLOR) == "\x1b[1mlurid\x1b[0m"
    assert dim("3 von 13", _COLOR) == "\x1b[2m3 von 13\x1b[0m"
    assert highlight("grell", _COLOR) == "\x1b[36mgrell\x1b[0m"
    codes = {bold("x", _COLOR)[:4], dim("x", _COLOR)[:4], highlight("x", _COLOR)[:5]}
    assert len(codes) == 3


def test_bold_does_not_wrap_an_empty_string() -> None:
    """Ein leerer Text bleibt leer, statt in ein bedeutungsloses `\\x1b[1m\\x1b[0m` zu
    münden — relevant für `display.dim`, das eine leere Angabenzeile sonst mit
    Steuersequenzen füllte, wo keine sichtbare Zeile stünde."""
    assert bold("", _COLOR) == ""


def test_arrow_dot_quote_use_ascii_fallback_without_unicode() -> None:
    """Auf einem Ziel, das die Sonderzeichen nicht trägt, stehen die ASCII-Ersatzzeichen
    aus dem Auftragstext: `->`, `|`, gerade Anführungszeichen — kein `?`.

    Verfälschungsprobe: `arrow`/`dot`/`quote` fest die Unicode-Zeichen liefern lassen, ohne
    `style.supports_unicode` auszuwerten, ließ diesen Test rot werden."""
    assert arrow(_PLAIN) == "  ->  "
    assert dot(_PLAIN) == " | "
    assert quote("Hallo", _PLAIN) == '"Hallo"'


def test_arrow_dot_quote_use_special_characters_with_unicode() -> None:
    """Auf einem fähigen Ziel stehen die eigentlichen Sonderzeichen — das Gegenstück zur
    vorigen Prüfung."""
    assert arrow(_COLOR) == "  →  "
    assert dot(_COLOR) == " · "
    assert quote("Hallo", _COLOR) == "„Hallo“"


def test_entry_rule_right_aligns_the_counter() -> None:
    """Die Trennlinie vor einem Eintrag endet rechtsbündig mit „N von M" — die
    ursprüngliche Beschwerde: „Man sieht klar, wo die vorherige Ausgabe aufhört, die
    nächste beginnt"."""
    line = entry_rule(3, 13, 5, _PLAIN)

    assert line.endswith("3 von 13 | 5 zum Lernen")
    assert line.startswith("-" * 10)  # Trennlinie füllt den Rest der Breite


def test_entry_rule_names_how_many_are_already_chosen_for_learning() -> None:
    """Zweite Nutzermeldung vom 02.09.2026: „Was mir irgendwie noch fehlt ist eine Anzeige,
    wie viele Vokabeln man bis jetzt zum Lernen ausgewählt hat." Die Zahl steht in der
    Trennlinie, hinter dem Positionszähler, und ist der Stand **vor** der anstehenden
    Entscheidung.

    Verfälschungsprobe: `chosen` in `entry_rule` ignoriert (nur „N von M" gebaut) — beide
    Zusicherungen unten wurden rot."""
    assert entry_rule(1, 13, 0, _PLAIN).endswith("0 zum Lernen")
    assert entry_rule(9, 13, 7, _PLAIN).endswith("7 zum Lernen")


def test_cover_returns_a_bold_title_between_two_double_rules() -> None:
    """Das Deckel-Banner (`cover`) — die stärkste der drei Anzeigeebenen — ersetzt
    `== Wörter ==`/`== Wendungen ==` in `cli.main` und muss sich optisch von der
    einfachen Trennlinie eines einzelnen Eintrags (`entry_rule`, einfaches `-`/`─`)
    unterscheiden: doppelte Trennlinie (`=`/`═`)."""
    lines = cover("Wörter", _PLAIN)

    assert len(lines) == 3
    assert lines[0] == lines[2]
    assert set(lines[0]) == {"="}
    assert lines[1] == "  Wörter"


def test_headline_matches_the_previous_single_line_format_when_it_fits() -> None:
    """Befund 3 (Durchsicht e537273): Für den häufigen Fall, dass Wortform und Übersetzung
    zusammen auf eine Zeile passen, muss `headline` denselben Wortlaut wie die frühere,
    von Hand gebaute Kopfzeile liefern (`  {bold(word_form)}{arrow}{highlight(translation)}`)
    — der Auftrag verlangt nur den Umbruch der langen Fälle, nicht ein neues Format."""
    style = Style(supports_color=True, supports_unicode=True, width=80)

    lines = headline("bank", "Ufer", style)

    assert lines == [f"  {bold('bank', style)}{arrow(style)}{highlight('Ufer', style)}"]


def test_headline_wraps_a_long_translation_and_keeps_the_word_form_first() -> None:
    """Befund 3 (Durchsicht e537273): Vor dieser Behebung war die Kopfzeile die einzige
    Zeile eines Eintrags, die nicht umbrach — gemessen an `tools/en-de.sqlite3` liefen
    3,1 % der Kopfzeilen über 80 Spalten, die längste über 245 Zeichen. `headline`
    umbricht wie `wrap_indented`, hält aber die Wortform als erstes Wort der ersten Zeile
    fest (die ursprüngliche Nutzerbeschwerde) und rückt Folgezeilen gleich ein.

    Verfälschungsprobe: `headline` durch eine Fassung ersetzt, die nur
    `[f"  {bold(word_form)}{arrow}{highlight(translation)}"]` liefert (der Stand vor
    dieser Behebung, unverändert für lange Übersetzungen) — `len(lines) > 1` schlägt fehl,
    dieser Test war daran rot."""
    style = Style(supports_color=False, supports_unicode=False, width=40)
    translation = " | ".join(f"variante{i}" for i in range(12))

    lines = headline("reproachfully", translation, style)

    assert len(lines) > 1
    assert lines[0].startswith("  reproachfully")
    assert all(len(line) <= style.width for line in lines)
    assert all(line.startswith("  ") for line in lines[1:])


def test_headline_colors_the_word_form_and_the_translation_on_every_line() -> None:
    """Die Kopfzeile mischt Fettdruck (Wortform) und Hervorhebung (Übersetzung) — nach dem
    Umbrechen lässt sich das nicht mehr nachträglich einfärben (`textwrap` zählte
    Steuersequenzen sonst als Breite mit), `headline` färbt deshalb **vor** dem Zählen der
    Breite pro Zeile ein: Zeile 1 trägt `bold` für die Wortform, jede Zeile (auch die
    erste) `highlight` für ihren Übersetzungsanteil.

    Verfälschungsprobe: `highlight` nur auf die erste Zeile angewandt (Folgezeilen
    unverfärbt) lässt die zweite Zusicherung unten rot werden."""
    style = Style(supports_color=True, supports_unicode=False, width=30)
    translation = " ".join(f"wort{i}" for i in range(10))

    lines = headline("word", translation, style)

    assert len(lines) > 1
    assert lines[0].startswith(f"  {bold('word', style)}")
    assert all("\x1b[36m" in line for line in lines)  # highlight-Code auf jeder Zeile


def test_wrap_indented_keeps_the_indent_on_every_continuation_line() -> None:
    """Eine lange Zeile bricht auf `style.width` um, jede Folgezeile mit derselben
    Einrückung wie die erste — sonst liefe ein langer Belegsatz über den Bildschirmrand
    (Auftragstext: „Lange Zeilen brechen um").

    Verfälschungsprobe: `textwrap.wrap` ohne anschließendes Voranstellen von `indent`
    aufgerufen (Folgezeilen also uneingerückt) ließ diesen Test rot werden."""
    style = Style(supports_color=False, supports_unicode=False, width=40)
    text = " ".join(f"wort{i}" for i in range(20))

    lines = wrap_indented(text, style)

    assert len(lines) > 1
    assert all(line.startswith("  ") for line in lines)
    assert all(len(line) <= style.width for line in lines)


def test_wrap_indented_returns_one_indented_line_for_empty_text() -> None:
    """Ein leerer Text ergibt eine einzelne, nur eingerückte Zeile statt einer leeren
    Liste — sonst fiele die Angabenzeile bei einer leeren Bedeutungsangabe ganz weg."""
    style = Style(supports_color=False, supports_unicode=False, width=40)

    assert wrap_indented("", style) == ["  "]
