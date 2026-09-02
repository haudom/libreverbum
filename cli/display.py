"""Bildschirmausgabe, die eine eingeschränkte Konsolenkodierung übersteht, und der
Ausgabestil der Triage-Anzeige.

Aufgabe
-------
Ein Belegsatz aus dem Buchtext kann typografische Anführungszeichen und Gedankenstriche
tragen (dokumentation.md §1). Unter Windows ist die Konsolenkodierung oft `cp1252` und
kann solche Zeichen nicht darstellen — ein bloßes `print()` bräche die Triage dort mit
einem `UnicodeEncodeError` ab. CLAUDE.md verlangt `encoding="utf-8"` nur ausdrücklich für
Dateien; dieselbe Gefahr gilt aber für die Bildschirmausgabe, und Regel 13
(dokumentation.md §4) verbietet ohnehin einen stillen Absturz mitten in der Triage.

Seit Bauschritt 2/2 der Konsolenausgabe (Auftragstext vom 02.09.2026, technik.md §13,
„Triage-Anzeige") liegt hier zusätzlich der **Ausgabestil**: eine einmal je Lauf ermittelte
Beschreibung dessen, was das Ausgabeziel kann (Farbe, die in `cli.interaction` verwendeten
Sonderzeichen, Breite), dazu Textbausteine, die sich danach richten. Alle Bausteine
**liefern Zeichenketten** und drucken selbst nichts — gedruckt wird weiterhin nur über
`safe_print`/den injizierten `write_line`, sonst wäre `cli.interaction` nicht mehr ohne
echtes Terminal zu prüfen (dokumentation.md §5).

Voraussetzungen
---------------
Keine.

Liefert
-------
`safe_print` schreibt `text` auf `stream` (Vorgabe `sys.stdout`) und weicht bei einem
`UnicodeEncodeError` auf eine verlustbehaftete, aber abbruchfreie Kodierung desselben
Zeichensatzes aus (`errors="replace"`) — auf einer cp1252-Konsole erscheint ein
Gedankenstrich dann als `?`, die Triage läuft aber weiter.

`safe_print_progress` und `finish_progress_line` sind das Gegenstück für eine sich
fortschreibende Statuszeile (Auftragstext vom 25.08.2026, Abschnitt 3): Ein Lauf, der
minutenlang ohne jede Ausgabe rechnet — `pipeline.resolve_triage_entries` bei `[triage]
order = "frequency"` und reifem Profil —, ist der stille Fehlschlag, den Regel 13
verbietet. Der Kern selbst gibt nichts aus (technik.md §7, „Kern ohne Bezug zur
Oberfläche"); `resolve_triage_entries` bekommt dafür nur einen Rückruf, den `cli.main`
über diese beiden Funktionen bedient.

`detect_style` ermittelt `Style` aus einem Strom (Vorgabe `sys.stdout`) — Farbe nur bei
einem echten Terminal, unter Windows zusätzlich nur bei eingeschaltetem VT-Modus;
Sonderzeichen nur, wenn die Zielkodierung sie trägt. `bold`/`dim`/`highlight` sind
Fettdruck, Dimmen und farbige Hervorhebung als Funktion von `Style` — ohne Farbfähigkeit
unverändert. `arrow`/`dot`/`quote` liefern die in `cli.interaction` verwendeten
Sonderzeichen samt ASCII-Ersatz. `entry_rule` ist die Trennlinie mit rechtsbündigem
Zähler vor jedem Triage-Eintrag, `cover` das Deckel-Banner für „Wörter"/„Wendungen".
`headline` bricht Wortform und Übersetzung eines Eintrags um **und** färbt sie ein
(Befund 3, Durchsicht e537273) — die einzige Anzeigeebene, die Umbruch und Farbe in einem
Schritt braucht, weil beides in einer Zeile gemischt ist. `wrap_indented` bricht eine
lange Zeile auf `Style.width` um, Folgezeilen mit derselben Einrückung. `PLAIN_STYLE` ist
die farb- und sonderzeichenlose Vorgabe für Aufrufer, denen der Ausgabestil gleichgültig
ist (etwa die meisten Tests von `cli.interaction`).
"""

from __future__ import annotations

import shutil
import sys
import textwrap
from dataclasses import dataclass
from typing import TextIO


def safe_print(text: str, *, stream: TextIO | None = None) -> None:
    """Schreibt `text` als Zeile auf `stream` (Vorgabe `sys.stdout`), ohne bei einer
    Konsole mit eingeschränkter Kodierung abzubrechen.

    `stream` wird spät ausgewertet (`sys.stdout` erst beim Aufruf, nicht als
    Vorgabewert der Funktion), weil Tests `sys.stdout` mitunter ersetzen, nachdem dieses
    Modul bereits importiert wurde.
    """
    target = stream if stream is not None else sys.stdout
    try:
        print(text, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), file=target)


def _write_raw(text: str, *, stream: TextIO | None, end: str) -> None:
    """Gemeinsame Fehlerbehandlung für `safe_print_progress` und `finish_progress_line`
    — dieselbe Ausweichkodierung wie `safe_print`, nur ohne den erzwungenen
    Zeilenumbruch, damit sich die Statuszeile per Wagenrücklauf selbst überschreibt."""
    target = stream if stream is not None else sys.stdout
    try:
        print(text, end=end, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding), end=end, file=target)


def safe_print_progress(text: str, *, stream: TextIO | None = None) -> None:
    """Schreibt `text` als sich selbst überschreibende Statuszeile: Wagenrücklauf (`\\r`)
    statt Zeilenumbruch, dieselbe Ausweichkodierung wie `safe_print` bei einer
    eingeschränkten Konsole.

    Aufeinanderfolgende Aufrufe innerhalb **eines** Laufs dürfen `text` nur wachsen
    lassen, nie kürzen — sonst blieben Reste der vorigen, längeren Zeile stehen, weil
    ein Wagenrücklauf nichts löscht, nur den Cursor zurücksetzt. Für
    `pipeline.resolve_triage_entries` ist das garantiert: Die geprüfte und die
    behaltene Zahl wachsen über einen Lauf hinweg nur, die Gesamtzahlen bleiben fest.
    `finish_progress_line` schließt die Zeile ab, bevor reguläre Ausgabe folgt — sonst
    verstümmelt der fehlende Zeilenumbruch die erste Triage-Frage danach."""
    _write_raw(f"\r{text}", stream=stream, end="")


def finish_progress_line(*, stream: TextIO | None = None) -> None:
    """Schließt eine mit `safe_print_progress` begonnene Zeile mit einem Zeilenumbruch
    ab — aufzurufen, sobald mindestens eine Statuszeile geschrieben wurde, bevor die
    nächste reguläre Ausgabe (etwa die erste Triage-Frage) folgt."""
    _write_raw("", stream=stream, end="\n")


# --------------------------------------------------------------------- Ausgabestil
#
# technik.md §13, „Triage-Anzeige": Format „kompakte Kopfzeile", Farbe sparsam und nur bei
# einem Ausgabeziel, das sie trägt. Zwei Fähigkeiten werden je Lauf **einmal** ermittelt
# (`detect_style`), nicht je Zeile — die Textbausteine unten richten sich danach.

_MIN_WIDTH = 40
_MAX_WIDTH = 100


def _terminal_width() -> int:
    """Breite für Trennlinien und Zeilenumbruch — `shutil.get_terminal_size(fallback=
    (80, 24))`, gedeckelt auf [40, 100]: Eine sehr schmale Konsole soll noch lesbar
    bleiben, eine sehr breite keine kilometerlangen Trennlinien ziehen."""
    columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    return max(_MIN_WIDTH, min(columns, _MAX_WIDTH))


@dataclass(frozen=True)
class Style:
    """Ausgabefähigkeit eines Ziels, einmal je Lauf ermittelt (`detect_style`) — ob es
    ANSI-Farbe trägt und ob seine Kodierung die in `cli.interaction` verwendeten
    Sonderzeichen (`─`, `═`, `→`, `·`, typografische Anführungszeichen) darstellen kann. Kein
    Konfigurationsschalter (dokumentation.md §4 Regel 14) — eine zur Laufzeit feststellbare
    Fähigkeit des Ziels, keine Einstellung."""

    supports_color: bool
    supports_unicode: bool
    width: int


PLAIN_STYLE = Style(supports_color=False, supports_unicode=False, width=80)
# Vorgabe für Aufrufer, denen der Ausgabestil gleichgültig ist — die meisten Tests von
# `cli.interaction` prüfen Entscheidungen, nicht die Bildschirmausgabe (dokumentation.md
# §5), und bekommen mit dieser Vorgabe eine deterministische, plattformunabhängige Form.

# Trennlinie (einfach ─, doppelt ═ im Deckel-Banner), Pfeil, Trennpunkt, deutsche
# Anführungszeichen (öffnend U+201E, schließend U+201C — dieselben Zeichen wie in
# cli/main.py, `_choose_chapter`).
# (Befund 2, Durchsicht e537273): `═` fehlte hier — `cover` zeichnet es, die Probe deckte
# es also nicht ab. Folgenlos an allen 14 Standard-Codecs, die die übrigen Zeichen tragen
# (sie tragen auch `═`), aber die Absicherung war unvollständig.
_SPECIAL_CHARS = "─═→·„“"


def _stream_supports_unicode(stream: TextIO) -> bool:
    """Prüft, ob die Kodierung von `stream` die oben genannten Sonderzeichen darstellen
    kann — nicht ob sie UTF-8 ist: `cp1252` etwa stellt „ “ und den Gedankenstrich bereits
    dar, aber nicht `─`/`═`/`→`/`·` (Auftragstext vom 02.09.2026). Eine fehlende oder
    unbekannte Kodierung gilt als unfähig — der sichere Fehlschlag ist der ASCII-Ersatz,
    nicht ein Bildschirm voller `?` (`safe_print`s eigentliche Gefahr, hier von vornherein
    vermieden statt erst hinterher ausgewichen)."""
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        _SPECIAL_CHARS.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _stream_is_a_terminal(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def _enable_windows_console_color(stream: TextIO) -> bool:
    """Schaltet unter Windows `ENABLE_VIRTUAL_TERMINAL_PROCESSING` (0x0004) auf dem
    Konsolen-Handle von `stream` ein — ohne das zeigt die alte conhost-Konsole `\\x1b[1m`
    wörtlich statt Fettdruck, `isatty()` allein genügt unter Windows also **nicht**
    (Auftragstext vom 02.09.2026). Auf anderen Systemen ist hier nichts zu tun, `isatty()`
    genügt dort bereits. Standardbibliothek (`ctypes`, `msvcrt`) — kein `colorama`, keine
    neue Abhängigkeit ohne Lizenzprüfung (Regel 15).

    Jeder Fehlschlag beim Ermitteln des echten Konsolen-Handles (kein `fileno()`, kein
    reales Konsolen-Handle dahinter — etwa ein Test-Double oder eine umgeleitete Datei)
    liefert `False`, statt die Ausnahme durchzureichen: Farbe ist hier eine Fähigkeit des
    Ziels, keine Voraussetzung für den Lauf. Das macht diese Funktion zugleich mit einem
    beliebigen Strom prüfbar, ohne ein echtes Terminal zu brauchen (Auftragstext, „Sorg
    dafür, dass Tests … prüfen können, ohne ein echtes Terminal zu brauchen").

    (Befund 1, Durchsicht e537273): Gefangen wird neben `OSError` (eine umgeleitete Datei
    ohne echtes Konsolen-Handle) auch `AttributeError` — ein Strom, der `isatty()` bejaht,
    aber gar kein `fileno()` hat (etwa ein Test-Double), warf sonst beim Aufruf von
    `stream.fileno()` durch, entgegen dem Versprechen oben. `cli.main.main` wertet
    `detect_style()` außerhalb seines eigenen `try`-Blocks aus — eine hier nicht gefangene
    Ausnahme liefe dort als englischer Traceback durch, an allen drei Fängen vorbei."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        kernel32 = ctypes.windll.kernel32
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(ctypes.c_void_p(handle), ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(ctypes.c_void_p(handle), mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def detect_style(stream: TextIO | None = None) -> Style:
    """Ermittelt `Style` für `stream` (Vorgabe `sys.stdout`) — **einmal** je Lauf
    aufzurufen, nicht je Zeile. `stream` ist austauschbar, damit Tests beide Spielarten
    (mit/ohne Farbe, mit/ohne Sonderzeichen) prüfen können, ohne ein echtes Terminal zu
    brauchen — `supports_color` und `supports_unicode` werden ausschließlich an diesem
    übergebenen Strom ermittelt.

    `width` dagegen nicht (Befund 4, Durchsicht e537273): Es kommt aus
    `shutil.get_terminal_size()` (`$COLUMNS` beziehungsweise `sys.__stdout__`) und ist
    damit bewusst eine Eigenschaft des Terminals selbst, nicht des übergebenen Stroms —
    ein Test, der die Breite prüfen will, gibt `style.width` deshalb selbst vor, statt
    `stream` dafür zu präparieren."""
    target = stream if stream is not None else sys.stdout
    supports_color = _stream_is_a_terminal(target) and _enable_windows_console_color(target)
    return Style(
        supports_color=supports_color,
        supports_unicode=_stream_supports_unicode(target),
        width=_terminal_width(),
    )


_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_HIGHLIGHT = "\x1b[36m"  # Cyan — für die deutsche Übersetzung und die Markierung „neue
# Bedeutung eines bekannten Wortes" (Auftragstext: „Farbe: ja, sparsam")
_RESET = "\x1b[0m"


def _decorate(text: str, code: str, style: Style) -> str:
    if not style.supports_color or not text:
        return text
    return f"{code}{text}{_RESET}"


def bold(text: str, style: Style) -> str:
    """Fettdruck — für die Wortform in der Kopfzeile eines Triage-Eintrags. Ohne
    Farbfähigkeit unverändert."""
    return _decorate(text, _BOLD, style)


def dim(text: str, style: Style) -> str:
    """Gedimmt — für Trennlinien und Nebendaten (Auftragstext: „Trennlinie und Nebendaten
    gedimmt")."""
    return _decorate(text, _DIM, style)


def highlight(text: str, style: Style) -> str:
    """Hervorgehoben — für die deutsche Übersetzung und die eigene Zeile „neue Bedeutung
    eines bekannten Wortes" (Auftragstext: „deutsche Bedeutung farbig")."""
    return _decorate(text, _HIGHLIGHT, style)


def arrow(style: Style) -> str:
    """Trennt Wortform und Übersetzung in der Kopfzeile eines Triage-Eintrags — `→` auf
    einem fähigen Ziel, sonst der ASCII-Ersatz `->`."""
    return "  →  " if style.supports_unicode else "  ->  "


def dot(style: Style) -> str:
    """Trennt die drei Angaben der Nebendaten-Zeile (Wortart, Häufigkeit,
    Bedeutungsangabe) — `·` oder der ASCII-Ersatz `|`."""
    return " · " if style.supports_unicode else " | "


def quote(text: str, style: Style) -> str:
    """Setzt `text` (den Belegsatz) in Anführungszeichen — typografisch (`„…“`) auf einem
    fähigen Ziel, sonst gerade ASCII-Anführungszeichen.

    (Befund 2, Durchsicht e537273): `cli.main._choose_chapter` schreibt für den Buchtitel
    dieselben typografischen Zeichen fest in den Quelltext, aber **ungeschützt** — ohne
    Rücksicht auf `Style` und ohne den ASCII-Ersatz. Das ist kein Vorbild für dieses
    Verhalten, nur derselbe Zeichensatz; die frühere Fassung dieses Docstrings behauptete
    das Gegenteil."""
    if style.supports_unicode:
        return f"„{text}“"
    return f'"{text}"'


def entry_rule(position: int, total: int, chosen: int, style: Style) -> str:
    """Trennlinie vor jedem Eintrag der Einzelabfrage, mit rechtsbündigem Zähler „N von M"
    (Auftragstext vom 02.09.2026, Format „kompakte Kopfzeile" — die ursprüngliche
    Beschwerde: „Man sieht klar, wo die vorherige Ausgabe aufhört, die nächste beginnt").
    Gedimmt wie die übrigen Nebendaten.

    `chosen` ist, wie viele Einträge im laufenden Kapitel bereits „lernen" bekommen haben —
    die Zahl **vor** der Entscheidung, die gerade ansteht (zweite Nutzermeldung vom
    02.09.2026: „Was mir irgendwie noch fehlt ist eine Anzeige, wie viele Vokabeln man bis
    jetzt zum Lernen ausgewählt hat"). Sie steht hier und nicht in einer eigenen Zeile,
    weil das Auge beim Blättern ohnehin auf die Trennlinie fällt: keine zusätzliche Zeile
    je Eintrag, und der Zähler wächst dort, wo auch der Positionszähler steht."""
    label = f"{position} von {total}{dot(style)}{chosen} zum Lernen"
    char = "─" if style.supports_unicode else "-"
    fill_width = max(style.width - len(label) - 2, 10)
    return dim(f"{char * fill_width}  {label}", style)


def cover(title: str, style: Style) -> list[str]:
    """Deckel-Banner — die stärkste der drei Anzeigeebenen der Triage (Auftragstext:
    „der Deckel … am stärksten"), ersetzt das bisherige `== Wörter ==`/`== Wendungen ==`
    in `cli.main`. Doppelte Trennlinie (`═`/`=`), damit sie sich von der einfachen
    Trennlinie vor jedem einzelnen Eintrag (`entry_rule`) klar unterscheidet."""
    char = "═" if style.supports_unicode else "="
    line = char * style.width
    return [line, f"  {bold(title, style)}", line]


def headline(word_form: str, translation: str, style: Style) -> list[str]:
    """Kopfzeile eines Triage-Eintrags — Wortform und Übersetzung, umgebrochen **und**
    eingefärbt in einem Baustein (Befund 3, Durchsicht e537273).

    Vor dieser Behebung war die Kopfzeile die einzige Zeile eines Eintrags, die nicht
    umbrach — Angabenzeile und Belegsatz liefen bereits durch `wrap_indented`, die
    Kopfzeile nicht, obwohl sie die längste Angabe trägt (`Sense.translation` ist die
    ganze `wikdict_trans_list`). Gemessen an `tools/en-de.sqlite3` über 110.868
    Kandidatenzeilen: 3,1 % der Kopfzeilen sind länger als 80 Spalten, die längste 245
    Zeichen — in etwa jedem Block lief eine Kopfzeile über den Rand.

    Die Kopfzeile mischt Fettdruck (Wortform) und Hervorhebung (Übersetzung) in **einer**
    Zeile; nach dem Umbrechen lässt sich das nicht mehr nachträglich einfärben, weil
    `textwrap` die ANSI-Steuersequenzen sonst als Breite mitzählte. Umbruch und Einfärbung
    laufen deshalb hier zusammen: `textwrap.wrap` bekommt nur die **unverfärbte**
    Übersetzung, mit der unverfärbten Wortform samt Pfeil als `initial_indent` (Zeile 1)
    und derselben Einrückung wie `wrap_indented` als `subsequent_indent` (Folgezeilen) —
    das hält die Wortform als erstes Wort der ersten Zeile fest (die ursprüngliche
    Nutzerbeschwerde) und gibt ihr denselben Breitenvorrang wie jedem anderen Wort. Erst
    danach wird pro Zeile eingefärbt: `bold` für die Wortform auf Zeile 1, `highlight` für
    den jeweiligen Übersetzungsanteil auf jeder Zeile."""
    indent = "  "
    prefix = f"{indent}{word_form}{arrow(style)}"
    wrapped = textwrap.wrap(
        translation, width=style.width, initial_indent=prefix, subsequent_indent=indent
    ) or [prefix]
    lines = []
    for index, line in enumerate(wrapped):
        if index == 0:
            body = line[len(prefix) :]
            lines.append(f"{indent}{bold(word_form, style)}{arrow(style)}{highlight(body, style)}")
        else:
            body = line[len(indent) :]
            lines.append(f"{indent}{highlight(body, style)}")
    return lines


def wrap_indented(text: str, style: Style, *, indent: str = "  ") -> list[str]:
    """Bricht `text` auf `style.width` um, Folgezeilen mit derselben Einrückung wie die
    erste (Auftragstext: „Lange Zeilen brechen um, statt über den Bildschirmrand zu
    laufen" — für Belegsatz und Angabenzeile in `cli.interaction`). Ein leerer Text ergibt
    eine einzelne, nur eingerückte Zeile statt einer leeren Liste."""
    width = max(style.width - len(indent), 20)
    wrapped = textwrap.wrap(text, width=width) or [""]
    return [f"{indent}{line}" for line in wrapped]
