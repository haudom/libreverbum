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
bei `triage.defer_beyond_word_limit` (konzept.md §4, „Blockweise Triage mit
Fortsetzungsfrage"), hier erneut
geprüft (`_ensure_single_chapter`), weil dieses Modul nach technik.md §7, „Die
Importregel" nur `entities` importieren darf und weder `triage` noch `dictionary` selbst
kennen darf — aus demselben Grund auch nicht `extraction`: `proper_nouns` (seit
bauplan-phase2.md AP 8) kommt bereits als fertiges `entities.ProperNounEntry` herein,
nicht als spaCy-Entität. `proper_nouns`, falls angegeben, gehört ebenfalls zu demselben
einen Kapitel wie `entries` (`_ensure_proper_nouns_match_chapter`).

Liefert
-------
`write_printout` schreibt eine vollständige HTML-Datei mit eingebettetem `@page`- und
`columns`-CSS (bauplan.md T14: zweispaltig): Buch und Kapitel als Überschrift, darunter
Wort, Wortart-Kürzel bei Homographen (Befund 4, Review T14) und Übersetzung je Zeile,
alphabetisch nach `word_form` (Begründung unten, „Warum alphabetisch"). `<`, `>` und `&`
aus dem Buchtext werden maskiert (`html.escape`, `quote=False` wie `anki._escaped`) — ein
Belegsatz darf die Seite nicht zerlegen; typografische Anführungszeichen und Gedankenstrich
bleiben unangetastet (dokumentation.md §1). Seit bauplan-phase2.md AP 8 optional dazu der
Anhang „Figuren & Orte" (Abschnitt „Der Anhang »Figuren & Orte«" unten).

Wie mit mehr als MAX_ENTRIES Einträgen verfahren wird
-------------------------------------------------------
Bis zum 01.09.2026 war das ein sichtbarer Fehlschlag: Die Wortobergrenze pro Kapitel
(konzept.md §4) garantierte, dass nie mehr als `MAX_ENTRIES` Einträge ankamen, also wies
`write_printout` mehr sichtbar zurück (Regel 13). Die blockweise Triage (konzept.md §4,
„Blockweise Triage mit Fortsetzungsfrage") hat diese Garantie aufgehoben — wer mehrere
Blöcke durchgeht, kann mehr als `MAX_ENTRIES` Karten haben. Der Abbruch ist deshalb zum
**Seitenumbruch**
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

Der Anhang „Figuren & Orte" (bauplan-phase2.md AP 8)
-----------------------------------------------------
`write_printout(..., proper_nouns=None)` — bei Angabe (nicht-leere Sequenz) hängt sie den
Anhang „Figuren & Orte" an (konzept.md §6, „Export"; technik.md §7, „Die Liste »Figuren &
Orte« ist Phase 2"). Die Eingabe kommt aus `extraction.extract_proper_noun_list`
(`ChapterVocabulary.proper_nouns`) — Oberflächenform, Häufigkeit und Entitätstyp je
Vorkommen, ungruppiert. Das **Zusammenstellen** des Anhangs — Gruppierung in „Figuren"
(`ProperNounEntry.ent_type == "PERSON"`) und „Orte" (alles andere: GPE, LOC, FAC),
alphabetische Sortierung je Gruppe, HTML — liegt hier, nicht in `extraction`: Dieses
Modul kennt nach der Importregel keinen der vier spaCy-Entitätstypen selbst (es
importiert nur `entities`), sondern nur das fertig aufbereitete `ProperNounEntry`
(technik.md §7, „Die Importregel").

`proper_nouns=None` (Vorgabe) heißt: kein Anhang, unverändertes Verhalten — dieselbe
Vorgabe-Bedeutung wie `pipeline.run_chapter`s `cache_dir: Path | None = None`
(technik.md §5). Eine **leere** Sequenz wird wie `None` behandelt (kein Anhang): Ein
Kapitel ganz ohne erkannten Eigennamen ergäbe sonst einen Anhang ohne einen einzigen
Eintrag — Lärm wie „Blatt 1 von 1" oben, kein Fehlschlag. `proper_nouns` muss zum selben
Kapitel gehören wie `entries` (`_ensure_proper_nouns_match_chapter`, Regel 13, dieselbe
Prüfung wie `_ensure_single_chapter`).

Kapazität und Umbruch des Anhangs sind hier **nicht** gemessen (anders als `MAX_ENTRIES`
oben): Der Anhang bleibt ein einzelnes Blatt, ohne die für die Wortliste gemessene
Seitenkapazität — ein offener Punkt für eine künftige Messung mit `tools/
print_fit_check.py`, sollte ein Kapitel mit sehr vielen Eigennamen das sprengen
(Regel 14: keine Messung ohne gemessenen Anlass).

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

from libreverbum.entities import Occurrence, ProperNounEntry, Sense

# (Befund 1, Review T14): Kapazität ist eine Eigenschaft des Blattes (Satzspiegel und
# Zeilenhöhe), nicht der Triage — anders als zuvor hier angenommen, und verschieden von
# `triage.defer_beyond_word_limit(word_limit)`, das dieselbe Zahl über eine ganz andere
# Rechnung erreichte (Wortobergrenze pro Kapitel, konzept.md §4). Ob und wie `entries`
# und `expressions` aus `pipeline.run_chapter` zusammen in die Druckausgabe kommen, ist
# die noch offene T16-Entscheidung (bauplan.md T16, „213 Wendungen je Kapitel"); dieser
# Wert begrenzt nur, was `write_printout` je Blatt unterbringt, unabhängig davon, was T16
# am Ende hineinlegt.
#
# (technik.md §12, „Folge: die Druckseite bricht um, statt abzubrechen", entschieden am
# 01.09.2026): Mit der blockweisen Triage garantiert keine Wortobergrenze mehr, dass nie
# mehr als MAX_ENTRIES Einträge ankommen. Die Zahl bleibt unverändert und misst weiter
# dasselbe Blatt — sie sagt jetzt aber, **wo** `_group_entries` umbricht, nicht mehr, wo
# `write_printout` abbricht.
#
# Messung 01.09.2026, `tools/print_fit_check.py`: echt gedruckt (Edge headless), echte
# `trans_list`-Werte aus `tools/en-de.sqlite3`, PDF-Seiten gezählt — überschreibt die
# vorherige, nur gerechnete Zahl (technik.md §8c, „Gemessene Ergebnisse"; Herkunft der 36
# dort, nicht hier). Bei 33 Einträgen bleibt es lückenlos bei einem Blatt für jede
# getestete Übersetzungslänge bis 80 Zeichen (60/65/70/72/74/75/76/78/80 Zeichen),
# einschließlich der p99-Länge von 76 Zeichen, auf die diese Zahl auslegt (technik.md
# §8c). Erst 82 und 85 Zeichen ergeben zwei Blätter. Die gerechnete 97,5-%-Füllung, aus
# der 36 stammte, ließ dagegen keinen Spielraum für das, was ein echter Browser anders
# macht als eine Schriftmetrik-Rechnung: 36 Einträge kippen schon bei 74 und 75 Zeichen
# auf zwei Seiten.
#
# Die Messung ist über die Übersetzungslänge nicht monoton (bei 36 Einträgen ergeben 74
# und 75 Zeichen zwei Seiten, 76 wieder eine) — kein Messfehler, sondern die Wortformlänge
# der zu jeder Ziellänge gezogenen Wörterbucheinträge verschiebt die Zeilenzahl mindestens
# so stark wie die Übersetzung selbst. Wer diese Zahl neu zieht, zieht sie deshalb erneut
# mit `tools/print_fit_check.py` gegen echten Ausdruck, nicht mit einer Schriftmetrik —
# und ändert sich das CSS dieses Moduls (`_CSS` unten) oder die p99-Länge aus technik.md
# §8c, ist die Messung zu wiederholen.
#
# (Befund 5, Durchsicht 4fa3c8e): Der Verweis im Moduldocstring, Abschnitt
# „Voraussetzungen", nannte „konzept.md §4, »Obergrenze pro Kapitel«" — eine Festlegung,
# die mit der blockweisen Triage gefallen ist. Er steht jetzt auf „konzept.md §4,
# »Blockweise Triage mit Fortsetzungsfrage«".
MAX_ENTRIES = 33


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
    Kapiteln auf einem Blatt wären eine stillschweigend erweiterte Kapazität je Blatt
    (technik.md §12, „Folge: die Druckseite bricht um, statt abzubrechen")."""
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


def _ensure_proper_nouns_match_chapter(
    entries: Sequence[tuple[Occurrence, Sense]], proper_nouns: Sequence[ProperNounEntry]
) -> None:
    """Bricht sichtbar ab (Regel 13), wenn der Anhang „Figuren & Orte" Einträge aus einem
    anderen Kapitel enthält als die Wortliste selbst — dieselbe Prüfung wie
    `_ensure_single_chapter`, hier über `entries` und `proper_nouns` hinweg: Beide gehören
    zu demselben `run_chapter`-Aufruf (`ChapterVocabulary.entries` und `.proper_nouns`).
    Wird nur gerufen, wenn `proper_nouns` nicht leer ist — `entries` ist an dieser Stelle
    durch `_ensure_single_chapter` bereits auf ein einzelnes Kapitel geprüft, `entries[0]`
    trägt es deshalb verlässlich."""
    chapter_key = (entries[0][0].book, entries[0][0].chapter_number)
    fremde = {
        (p.book, p.chapter_number)
        for p in proper_nouns
        if (p.book, p.chapter_number) != chapter_key
    }
    if fremde:
        gefundene = ", ".join(
            f"„{book.title}“ Kapitel {chapter_number}"
            for book, chapter_number in sorted(fremde, key=lambda paar: (paar[0].title, paar[1]))
        )
        raise ValueError(
            f"Der Anhang „{_APPENDIX_TITLE}“ gehört zum selben Kapitel wie die Wortliste "
            f"(„{chapter_key[0].title}“ Kapitel {chapter_key[1]}), enthält aber Einträge "
            f"aus: {gefundene}."
        )


# (bauplan-phase2.md AP 8): Eigene, kleine Zuordnung statt eines Imports aus `extraction`
# — printout darf `extraction` nach der Importregel nicht importieren (Moduldocstring,
# „Voraussetzungen"; technik.md §7). PERSON wird „Figuren", jeder andere der vier
# Entitätstypen aus `extraction._PROPER_NOUN_ENTITY_TYPES` (GPE, LOC, FAC) wird „Orte" —
# über Ausschluss, nicht über eine zweite, hier gepflegte Liste, die mit der Liste in
# `extraction` auseinanderlaufen könnte.
_FIGURE_ENTITY_TYPE = "PERSON"
_APPENDIX_TITLE = "Figuren & Orte"
_FIGURES_HEADING = "Figuren"
_PLACES_HEADING = "Orte"


def _proper_noun_sort_key(entry: ProperNounEntry) -> tuple[str, str]:
    """Alphabetisch nach der Oberflächenform, `casefold` wie `_sort_key` — dieselbe
    Begründung: Wer im Anhang nachschlägt, sucht die Schreibung, nicht den Entitätstyp."""
    return (entry.text.casefold(), entry.text)


def _proper_noun_group_html(heading: str, group: Sequence[ProperNounEntry]) -> str:
    """Eine Gruppe des Anhangs („Figuren" oder „Orte") als Überschrift plus Liste —
    leer bleibt eine Gruppe ganz weg, statt einer Überschrift ohne einen einzigen
    Eintrag (dieselbe Lärmvermeidung wie `sheet_label` oben)."""
    if not group:
        return ""
    items = "\n    ".join(
        f'<li><span class="wort">{_escaped(entry.text)}</span> '
        f'<span class="anzahl">({entry.frequency})</span></li>'
        for entry in sorted(group, key=_proper_noun_sort_key)
    )
    return f"""<h2>{heading}</h2>
    <ul class="namensliste">
    {items}
    </ul>
    """


def _appendix_html(
    proper_nouns: Sequence[ProperNounEntry], book_title: str, chapter_number: int
) -> str:
    """Der Anhang „Figuren & Orte" als eigener Blatt-Container (`div class="blatt
    anhang"`) — trägt dieselbe Klasse `blatt` wie die Wortlisten-Blätter, damit ihn
    dasselbe CSS (`div.blatt:last-of-type`, Moduldocstring „Wie mit mehr als MAX_ENTRIES
    Einträgen verfahren wird") ohne eigene Regel als letztes Blatt ohne erzwungenen
    Umbruch danach behandelt."""
    figures = [entry for entry in proper_nouns if entry.ent_type == _FIGURE_ENTITY_TYPE]
    places = [entry for entry in proper_nouns if entry.ent_type != _FIGURE_ENTITY_TYPE]
    groups = _proper_noun_group_html(_FIGURES_HEADING, figures) + _proper_noun_group_html(
        _PLACES_HEADING, places
    )
    return f"""<div class="blatt anhang">
    <h1>{book_title}</h1>
    <p class="kapitel">Kapitel {chapter_number} – {_APPENDIX_TITLE}</p>
    {groups}
    </div>"""


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
    /* Anhang „Figuren & Orte" (bauplan-phase2.md AP 8): eigene Überschriften „Figuren"/
       „Orte" und eine schmalere Liste ohne Übersetzungstrennzeichen — nur Name und
       Häufigkeit. */
    div.anhang h2 { font-size: 12pt; margin: 6mm 0 2mm 0; }
    ul.namensliste {
      columns: 2;
      column-gap: 10mm;
      list-style: none;
      margin: 0 0 4mm 0;
      padding: 0;
    }
    ul.namensliste li {
      break-inside: avoid;
      page-break-inside: avoid;
      margin: 0 0 2mm 0;
      overflow-wrap: break-word;
      hyphens: auto;
    }
    span.anzahl { font-size: 9pt; color: #555555; }
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
    # (Befund 8, Durchsicht 4fa3c8e): `zaehlung` war ein deutscher Bezeichner
    # (dokumentation.md §1) — umbenannt, Begriff „Blattzählung" in dokumentation.md §2
    # nachgetragen.
    sheet_label = f" – Blatt {sheet_number} von {sheet_count}" if sheet_count > 1 else ""
    items = "\n    ".join(_entry_html(occurrence, sense) for occurrence, sense in group)
    return f"""<div class="blatt">
    <h1>{book_title}</h1>
    <p class="kapitel">Kapitel {chapter_number}{sheet_label}</p>
    <ul class="wortliste">
    {items}
    </ul>
    </div>"""


def write_printout(
    path: Path,
    entries: Sequence[tuple[Occurrence, Sense]],
    *,
    proper_nouns: Sequence[ProperNounEntry] | None = None,
) -> None:
    """Schreibt die Kapitelliste als druckfertige HTML-Datei nach `path` (bauplan.md T14,
    Abnahmekriterium 5): Buch und Kapitel als Überschrift, darunter `entries` alphabetisch
    nach `word_form` (Moduldocstring, „Warum alphabetisch"), auf so viele Blätter verteilt,
    wie nötig — höchstens `MAX_ENTRIES` je Blatt (Moduldocstring, „Wie mit mehr als
    MAX_ENTRIES Einträgen verfahren wird").

    `proper_nouns` (bauplan-phase2.md AP 8, Vorgabe `None`): eine nicht-leere Sequenz
    hängt den Anhang „Figuren & Orte" an (Moduldocstring, „Der Anhang »Figuren & Orte«");
    `None` oder eine leere Sequenz lassen die Ausgabe unverändert wie vor AP 8.

    Sichtbare Fehlschläge statt einer leeren, stillschweigend gekürzten oder
    unvollständigen Datei (Regel 13): eine leere Liste, Wörter aus mehreren Kapiteln
    (`_ensure_single_chapter`), ein Anhang aus einem anderen Kapitel als die Wortliste
    (`_ensure_proper_nouns_match_chapter`) oder eine nicht aufgelöste und nicht als
    unsicher bestätigte Übersetzung (`_translation_html`, Moduldocstring „Wie mit
    uncertain verfahren wird").
    """
    if not entries:
        raise ValueError("Druckseite ohne Wörter ergibt keine sinnvolle Kapitelliste.")
    _ensure_single_chapter(entries)
    if proper_nouns:
        _ensure_proper_nouns_match_chapter(entries, proper_nouns)

    ordered = sorted(entries, key=_sort_key)
    book_title = _escaped(ordered[0][0].book.title)
    chapter_number = ordered[0][0].chapter_number
    groups = _group_entries(ordered)
    sheets = "\n    ".join(
        _sheet_html(group, book_title, chapter_number, sheet_number, len(groups))
        for sheet_number, group in enumerate(groups, start=1)
    )
    appendix = _appendix_html(proper_nouns, book_title, chapter_number) if proper_nouns else ""

    document = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>{book_title} — Kapitel {chapter_number}</title>
    <style>{_CSS}</style>
</head>
<body>
    {sheets}
    {appendix}
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
