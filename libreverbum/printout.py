"""Druckausgabe — Kapitelliste als druckfertige HTML-Seite (bauplan.md T14).

Aufgabe
-------
Schritt 6 des Kernablaufs (konzept.md §6, „Export"), zweite Hälfte: aus den in der Triage
zum Lernen ausgewählten Wörtern eine einzige, in sich geschlossene HTML-Datei erzeugen —
CSS eingebettet, kein Verweis nach außen (Abnahmekriterium 5) —, die auch auf einem
Rechner ohne Netz richtig druckt. Gedruckt wird im Browser, der Nutzer speichert dort bei
Bedarf auch als PDF (bauplan.md Tor 0, E8c, entschieden 21.08.2026): Für ein einzelnes
zweispaltiges Blatt ist jede geprüfte Bibliothek entweder eine Systemabhängigkeit
außerhalb von `uv.lock` (`weasyprint`), trägt eine Schriftfalle genau bei den
typografischen Zeichen aus dem Buchtext (`fpdf2`) oder eine Werkbank für ein Blatt
(`reportlab`) — die Standardbibliothek genügt.

Voraussetzungen
---------------
`entries` sind bereits übersetzt oder als `uncertain` bestätigt (Abschnitt „Wie mit
`uncertain` verfahren wird" unten) und gehören zu **einem** Kapitel: dieselbe Annahme wie
bei `triage.defer_beyond_word_limit` (konzept.md §4, „Obergrenze pro Kapitel"), hier
erneut geprüft (`_ensure_single_chapter`), weil dieses Modul nach technik.md §7, „Die
Importregel" nur `entities` importieren darf und weder `triage` noch `dictionary` selbst
kennen darf.

Liefert
-------
`write_printout` schreibt eine vollständige HTML-Datei mit eingebettetem `@page`- und
`columns`-CSS (bauplan.md T14: zweispaltig): Buch und Kapitel als Überschrift, darunter
Wort, Wortart-Kürzel bei Homographen (Befund 4, Review T14) und Übersetzung je Zeile,
alphabetisch nach `word_form` (Begründung unten, „Warum alphabetisch"). `<`, `>` und `&`
aus dem Buchtext werden maskiert (`html.escape`, `quote=False` wie `anki._escaped`) — ein
Belegsatz darf die Seite nicht zerlegen; typografische Anführungszeichen und Gedankenstrich
bleiben unangetastet (dokumentation.md §1).

Wie mit mehr als MAX_ENTRIES Einträgen verfahren wird
-------------------------------------------------------
Bis zum 01.09.2026 war das ein sichtbarer Fehlschlag: Die Wortobergrenze pro Kapitel
(konzept.md §4) garantierte, dass nie mehr als `MAX_ENTRIES` Einträge ankamen, also wies
`write_printout` mehr sichtbar zurück (Regel 13). Die blockweise Triage (konzept.md §4,
„Nachtrag 01.09.2026") hat diese Garantie aufgehoben — wer mehrere Blöcke durchgeht, kann
mehr als `MAX_ENTRIES` Karten haben. Der Abbruch ist deshalb zum **Seitenumbruch**
geworden (technik.md §12, „Folge: die Druckseite bricht um, statt abzubrechen";
Abnahmekriterium 5): `_group_entries` schneidet die sortierte Liste in Gruppen zu
höchstens `MAX_ENTRIES`, jede Gruppe bekommt einen eigenen Blatt-Container mit eigener
Kapitelüberschrift (sonst weiß der Leser beim zweiten Blatt nicht mehr, wozu es gehört)
und — bei mehr als einem Blatt — einer Blattzählung „Blatt n von m". Der Umbruch selbst
steht als erzwungene CSS-Regel zwischen den Containern (`div.blatt`), nicht dem
natürlichen Fließverhalten des Browsers überlassen: Nur ein expliziter Umbruch an genau
dieser Stelle hält die in `MAX_ENTRIES` gemessene Kapazität je Blatt ein, und ob der
Browser von sich aus richtig umbräche, ist nicht prüfbar.

Wie mit `uncertain` verfahren wird
-----------------------------------
`uncertain` unterscheidet drei Fälle (Befund 2, Review T14; Regel 10, Regel 13; siehe
`_translation_html`):

- **Ohne Übersetzung, `uncertain`:** kein Fehlschlag. Der Nutzer hat den Eintrag in der
  Triage bewusst gewählt — `dictionary.particle_verb_candidates` liefert für eine Wendung
  ohne Wörterbucheintrag genau so einen Platzhalter (Regel 10) —, es fehlt nur die
  Bestätigung. Er kommt auf die Seite, mit einer deutschen Textmarke statt der fehlenden
  Übersetzung: Auf Papier gibt es keinen Tag wie `anki`s `unsicher` (`anki._tags`), also
  braucht es einen Text, den ein Mensch versteht.
- **Ohne Übersetzung, nicht `uncertain`:** ein echter Fehlschlag der Vorstufe, sichtbar
  über einen Abbruch (Regel 13) — wie bisher.
- **Mit Übersetzung, `uncertain`:** heute in Phase 1 nicht erreichbar (der einzige
  `uncertain`-Platzhalter aus `dictionary.py` trägt nie eine `translation`), aber die
  Ausweichantwort des Modells öffnet den Weg. Auch sie bekommt die Textmarke, damit sie
  nicht ununterscheidbar wie eine gesicherte Bedeutung dasteht.

Warum alphabetisch, nicht in Vorkommensreihenfolge
---------------------------------------------------
konzept.md §6 nennt beide Reihenfolgen zulässig, Regel 14 verbietet aber einen Schalter
ohne zweiten Anwendungsfall. Die Triage sortiert bereits nach Häufigkeit; eine davon
verschiedene zweite Reihenfolge braucht einen eigenen Zweck, keinen zufällig anderen.
Die Druckseite dient „dem Lesen ohne jedes Gerät" (konzept.md §6) — dem Nachschlagen
also, nicht dem Wiederholen der Triage-Reihenfolge: Wer beim Lesen ein Wort wiederfindet,
sucht es alphabetisch, nicht an der Stelle, an der es im Kapitel zuerst auftrat. Sortiert
wird nach `word_form`, nicht nach der Grundform: Genau diese Beugungsform steht im Buch
und wird dort gesucht (`entities.Occurrence`, „word_form … steht später auf der Karte" —
dieselbe Wahl trifft bereits `anki._fields` für das Feld „Wort").

*Offener Punkt:* Vorkommensreihenfolge passt dort, wo das Blatt statt zum Nachschlagen zur
Vorschau vor dem Lesen dient. Für genau diesen zweiten Anwendungsfall sieht konzept.md §6
bereits eine eigene Druckvariante vor, das „Lesezeichen-Format" (Phase 2, „Lesezeichen-
Druck und weitere Druckvarianten") — ein Schalter in diesem Modul wäre die Abstraktung,
die Regel 14 untersagt.

Wohin die Liste „Figuren & Orte" gehört
----------------------------------------
Der Bauplan legt den offenen Punkt aus technik.md §7 hier vor. konzept.md §6 nennt sie
unter „Druckausgabe" als *optionalen* Anhang, in derselben Aufzählung wie das
„Lesezeichen-Format" — und der Phasenplan zählt „Lesezeichen-Druck und weitere
Druckvarianten" ausdrücklich zu Phase 2. Der Phase-1-Satz im Phasenplan („Anki-Deck und
Druckseite") und Abnahmekriterium 5 nennen beide nur die eine Kapitelliste. Die Liste
gehört damit **nicht** in T14, sondern nach Phase 2, „weitere Druckvarianten", und wird
hier nicht gebaut (Regel 14) — obwohl die Daten dafür schon vorlägen
(`Occurrence.proper_noun_frequency`, Regel 12).

Würde sie später gebaut, gehörte das Zusammenstellen nach `printout`, nicht nach
`extraction`: `extraction` liefert bereits je Vorkommen, wie oft es ein Eigenname war
(Regel 12) — mehr als diese Zahl braucht eine solche Liste nicht. Das Zusammenstellen
einer zweiten, separaten Ausgabeliste daraus ist Ausgabe, keine Extraktion, und gehört
damit an dieselbe Stelle wie die Kapitelliste selbst.

Offener Punkt
-------------
**Direkte PDF-Ausgabe ohne Handgriff** ist ausdrücklich Phase 2 (bauplan.md Tor 0, E8c):
Dieses Modul erzeugt HTML als Quelle dafür, wandelt selbst nicht um. Bis dahin druckt der
Nutzer im Browser oder speichert dort als PDF.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

from libreverbum.entities import Occurrence, Sense

# (Befund 1, Review T14): Kapazität ist eine Eigenschaft des Blattes (Satzspiegel und
# Zeilenhöhe), nicht der Triage — anders als zuvor hier angenommen, und verschieden von
# `triage.defer_beyond_word_limit(word_limit)`, das dieselbe Zahl über eine ganz andere
# Rechnung erreichte (Wortobergrenze pro Kapitel, konzept.md §4). Ob und wie `entries`
# und `expressions` aus `pipeline.run_chapter` zusammen auf diese eine Seite kommen, ist
# die noch offene T16-Entscheidung (bauplan.md T16, „213 Wendungen je Kapitel"); dieser
# Wert begrenzt nur, was `write_printout` je Blatt unterbringt, unabhängig davon, was T16
# am Ende hineinlegt.
#
# Nachtrag 01.09.2026 (technik.md §12, „Folge: die Druckseite bricht um, statt
# abzubrechen"): Mit der blockweisen Triage garantiert keine Wortobergrenze mehr, dass nie
# mehr als MAX_ENTRIES Einträge ankommen. Die Zahl bleibt unverändert und misst weiter
# dasselbe Blatt — sie sagt jetzt aber, **wo** `_group_entries` umbricht, nicht mehr, wo
# `write_printout` abbricht.
#
# Messung 21.08.2026, echte Arial-Metrik (C:/Windows/Fonts/arial.ttf) gegen alle 157.801
# `trans_list`-Werte aus `tools/en-de.sqlite3`, gegen das CSS dieses Moduls (`_CSS`
# unten): Satzspiegel 180 × 267 mm, Spalte 85 mm, nutzbare Gesamtspaltenlänge nach `h1`
# und `p.kapitel`: 491 mm. Zeilenhöhe 11 pt × 1,2 = 4,66 mm, dazu 4 mm `margin` je
# Eintrag. `trans_list`-Längen: Median 12 Zeichen, p90 32, p95 45, p99 76, Maximum 199.
# Bei p99-Länge (76 Zeichen) wickelt ein Eintrag in dieser Spaltenbreite auf
# durchschnittlich zwei Zeilen: 2 × 4,66 mm + 4 mm = 13,3 mm je Eintrag. 491 mm ÷ 13,3 mm
# = 36,9 — bei 37 Einträgen reichte selbst die p99-Länge nicht mehr sicher (37 × 13,3 mm
# = 492,1 mm > 491 mm), bei 36 schon (36 × 13,3 mm = 478,8 mm, 12,2 mm Rand). Zum
# Vergleich: 25 Einträge mit der jeweils längsten real vorkommenden `trans_list` (`draw`
# 103 Zeichen, `set` 65) füllen 277 mm (56 % des Blattes), 25 Einträge auf p99-Länge
# 333 mm (68 %) — die alte, aus der Wortobergrenze abgeleitete Zahl 25 lag damit weit
# unter der tatsächlichen Kapazität. Wer diese Zahl neu misst, misst gegen dieselbe
# Arial-Metrik und dasselbe CSS wie hier — ändert sich eines von beiden, ist die Rechnung
# neu zu ziehen.
MAX_ENTRIES = 36


def _escaped(value: str) -> str:
    """Maskiert `<`, `>` und `&` für die Einbettung in HTML-Fließtext — `quote=False` wie
    `anki._escaped`, damit typografische Anführungszeichen und Apostroph aus dem Buchtext
    unangetastet bleiben (dokumentation.md §1, CLAUDE.md „Dateien immer mit
    encoding=utf-8 öffnen")."""
    return html.escape(value, quote=False)


# (Befund 2, Review T14): Deutsche Textmarke statt eines Anki-Tags — auf Papier gibt es
# keinen Tag (anki._tags kennt „unsicher", diese Seite nicht), also muss die Marke als
# Text vor der Anzeige stehen (dictionary.py:93-103, Regel 10).
_UNCERTAIN_MARK = "unsicher"


def _translation_html(occurrence: Occurrence, sense: Sense) -> str:
    """Die aufgelöste Übersetzung eines Eintrags, bereits als maskiertes HTML-Fragment —
    die drei `uncertain`-Fälle aus dem Moduldocstring, „Wie mit uncertain verfahren
    wird"."""
    if sense.translation is None:
        if sense.uncertain:
            return f'<span class="unsicher">{_UNCERTAIN_MARK} – kein Wörterbucheintrag</span>'
        raise ValueError(
            f"„{occurrence.lemma.text}“ ({occurrence.lemma.pos}) hat keine aufgelöste "
            "Übersetzung (sense.translation ist None) und ist nicht als unsicher markiert "
            "(sense.uncertain) — Druckseite nur für Wörter mit aufgelöster oder als "
            "unsicher bestätigter Bedeutung."
        )
    translation = _escaped(sense.translation)
    if sense.uncertain:
        return f'{translation} <span class="unsicher">({_UNCERTAIN_MARK})</span>'
    return translation


# (Befund 4, Review T14): Eigene, kleine Zuordnung statt eines Imports aus `dictionary` —
# printout darf `dictionary` nicht importieren (Moduldocstring, „Voraussetzungen"; technik.md
# §7, „Die Importregel"). Dieselben fünf Wortarten wie `dictionary._WIKDICT_POS`
# (`extraction._CONTENT_POS`, Regel 14: kein Vorrat auf Vorrat), hier als kurzes deutsches
# Kürzel statt WikDicts englischem Namen — ein Mensch liest die Seite, `token.pos_` gehört
# nicht aufs Papier (dokumentation.md §1). „Wortart" ist bereits das verbindliche deutsche
# Wort für `pos` (dokumentation.md §2); ein neuer Begriff entsteht hier nicht.
_POS_LABELS = {"NOUN": "Subst.", "VERB": "Verb", "ADJ": "Adj.", "ADV": "Adv.", "INTJ": "Interj."}


def _pos_label(pos: str) -> str | None:
    """Kürzel für Homographen wie `saw` (NOUN/VERB, Befund 4, Review T14) — zwei
    `Occurrence` mit demselben `word_form`, aber verschiedener Wortart, wären sonst nur an
    der Übersetzung unterscheidbar. Wendungen aus T4/T7 tragen keine Einzelwortart
    (`extraction._NO_SINGLE_POS`, leerer String, siehe `extraction.py`,
    „extract_contiguous_candidates") und bekommen deshalb kein Kürzel (`None`)."""
    if pos == "":
        return None
    try:
        return _POS_LABELS[pos]
    except KeyError as error:
        raise ValueError(f"Kein Wortart-Kürzel für {pos!r} hinterlegt.") from error


def _ensure_single_chapter(entries: Sequence[tuple[Occurrence, Sense]]) -> None:
    """Bricht sichtbar ab, wenn `entries` Vorkommen aus mehr als einem Kapitel enthält —
    dieselbe Prüfung wie `triage._ensure_single_chapter`, hier eigenständig geschrieben,
    weil dieses Modul `triage` nicht importieren darf (technik.md §7, „Die
    Importregel"). Die Druckseite ist eine Kapitelliste (bauplan.md T14); Wörter aus zwei
    Kapiteln auf einem Blatt wären eine stillschweigend erweiterte Obergrenze
    (konzept.md §4, „pro Kapitel")."""
    chapters = {(occurrence.book, occurrence.chapter_number) for occurrence, _ in entries}
    if len(chapters) > 1:
        gefundene = ", ".join(
            f"„{book.title}“ Kapitel {chapter_number}"
            for book, chapter_number in sorted(chapters, key=lambda paar: (paar[0].title, paar[1]))
        )
        raise ValueError(
            "Die Druckseite ist eine Kapitelliste (bauplan.md T14), die übergebenen "
            f"Wörter stammen aber aus mehreren Kapiteln: {gefundene}."
        )


def _sort_key(entry: tuple[Occurrence, Sense]) -> tuple[str, str, str]:
    """Alphabetische Sortierung nach `word_form` (Moduldocstring, „Warum alphabetisch"),
    `casefold` gegen Groß-/Kleinschreibung am Satzanfang. Grundform und Wortart als
    zweiter, stabiler Schlüssel bei Gleichstand — dasselbe Muster wie `triage._sort_key`
    (dokumentation.md §5, „Ein Test gilt erst als Test, wenn er einmal rot war")."""
    occurrence, _ = entry
    return (occurrence.word_form.casefold(), occurrence.lemma.text, occurrence.lemma.pos)


_CSS = """
    @page { size: A4; margin: 15mm; }
    body { font-family: sans-serif; font-size: 11pt; margin: 0; }
    h1 { font-size: 16pt; margin: 0 0 2mm 0; }
    p.kapitel { margin: 0 0 8mm 0; color: #333333; }
    ul.wortliste {
      columns: 2;
      column-gap: 10mm;
      list-style: none;
      margin: 0;
      padding: 0;
    }
    /* (Befund 1, Review T14): overflow-wrap/hyphens gegen seitlich aus der Spalte
       herausragende Wörter — gemessen 21.08.2026 gegen tools/en-de.sqlite3 (siehe
       Kommentar bei MAX_ENTRIES): fünf Token im ganzen Wörterbuch sind breiter als
       diese 85-mm-Spalte. */
    ul.wortliste li {
      break-inside: avoid;
      page-break-inside: avoid;
      margin: 0 0 4mm 0;
      overflow-wrap: break-word;
      hyphens: auto;
    }
    span.wort { font-weight: bold; }
    span.wortart { font-size: 9pt; font-style: italic; color: #555555; }
    span.unsicher { font-style: italic; color: #555555; }
    /* Erzwungener Seitenumbruch zwischen den Blatt-Containern (Moduldocstring, „Wie mit
       mehr als MAX_ENTRIES Einträgen verfahren wird") — nicht dem natürlichen
       Fließverhalten des Browsers überlassen: Ohne `:last-of-type` bekäme auch das letzte
       Blatt einen Umbruch danach und der Ausdruck endete auf einer leeren Seite. */
    div.blatt {
      page-break-after: always;
      break-after: page;
    }
    div.blatt:last-of-type {
      page-break-after: auto;
      break-after: auto;
    }
    """


def _entry_html(occurrence: Occurrence, sense: Sense) -> str:
    word = _escaped(occurrence.word_form)
    pos_label = _pos_label(occurrence.lemma.pos)
    pos_html = f' <span class="wortart">({pos_label})</span>' if pos_label is not None else ""
    return (
        f'<li><span class="wort">{word}</span>{pos_html} – '
        f'<span class="uebersetzung">{_translation_html(occurrence, sense)}</span></li>'
    )


def _group_entries(
    ordered: Sequence[tuple[Occurrence, Sense]],
) -> list[Sequence[tuple[Occurrence, Sense]]]:
    """Schneidet die bereits sortierte Liste in Blätter zu höchstens `MAX_ENTRIES`
    Einträgen (Moduldocstring, „Wie mit mehr als MAX_ENTRIES Einträgen verfahren wird") —
    explizit hier in Python, nicht dem natürlichen Umbruch des Browsers überlassen. Die
    Reihenfolge aus `ordered` bleibt je Gruppe erhalten, Gruppen entstehen nur durch
    Schneiden, nicht durch Umsortieren."""
    return [ordered[start : start + MAX_ENTRIES] for start in range(0, len(ordered), MAX_ENTRIES)]


def _sheet_html(
    group: Sequence[tuple[Occurrence, Sense]],
    book_title: str,
    chapter_number: int,
    sheet_number: int,
    sheet_count: int,
) -> str:
    """Ein einzelner Blatt-Container mit eigener Kapitelüberschrift — sonst weiß der Leser
    beim zweiten Blatt nicht mehr, wozu es gehört — und, bei mehr als einem Blatt, einer
    Blattzählung „Blatt n von sheet_count"; bei genau einem Blatt entfällt sie, „Blatt 1
    von 1" wäre Lärm."""
    zaehlung = f" – Blatt {sheet_number} von {sheet_count}" if sheet_count > 1 else ""
    items = "\n    ".join(_entry_html(occurrence, sense) for occurrence, sense in group)
    return f"""<div class="blatt">
    <h1>{book_title}</h1>
    <p class="kapitel">Kapitel {chapter_number}{zaehlung}</p>
    <ul class="wortliste">
    {items}
    </ul>
    </div>"""


def write_printout(path: Path, entries: Sequence[tuple[Occurrence, Sense]]) -> None:
    """Schreibt die Kapitelliste als druckfertige HTML-Datei nach `path` (bauplan.md T14,
    Abnahmekriterium 5): Buch und Kapitel als Überschrift, darunter `entries` alphabetisch
    nach `word_form` (Moduldocstring, „Warum alphabetisch"), auf so viele Blätter verteilt,
    wie nötig — höchstens `MAX_ENTRIES` je Blatt (Moduldocstring, „Wie mit mehr als
    MAX_ENTRIES Einträgen verfahren wird").

    Sichtbare Fehlschläge statt einer leeren, stillschweigend gekürzten oder
    unvollständigen Datei (Regel 13): eine leere Liste, Wörter aus mehreren Kapiteln
    (`_ensure_single_chapter`) oder eine nicht aufgelöste und nicht als unsicher
    bestätigte Übersetzung (`_translation_html`, Moduldocstring „Wie mit uncertain
    verfahren wird").
    """
    if not entries:
        raise ValueError("Druckseite ohne Wörter ergibt keine sinnvolle Kapitelliste.")
    _ensure_single_chapter(entries)

    ordered = sorted(entries, key=_sort_key)
    book_title = _escaped(ordered[0][0].book.title)
    chapter_number = ordered[0][0].chapter_number
    groups = _group_entries(ordered)
    sheets = "\n    ".join(
        _sheet_html(group, book_title, chapter_number, sheet_number, len(groups))
        for sheet_number, group in enumerate(groups, start=1)
    )

    document = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>{book_title} — Kapitel {chapter_number}</title>
    <style>{_CSS}</style>
</head>
<body>
    {sheets}
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
