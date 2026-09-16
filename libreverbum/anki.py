"""Anki-Export — Deck aus Karten, samt stabiler GUID (bauplan.md T13).

Aufgabe
-------
Schritt 6 des Kernablaufs (konzept.md §6, „Export"): aus `Card`-Objekten ein Anki-Deck
erzeugen, das sich fehlerfrei importieren lässt (Abnahmekriterium 4) und dessen GUID über
eine korrigierte Übersetzung und einen neuen Wörterbuchbezug hinweg **dieselbe bleibt**
(Regel 6). `genanki` liefert Notiz- und Paketformat; die Kartenvorlage je Kartenrichtung
(genankis `Model`, hier „Kartenvorlage" genannt — dokumentation.md §2, „Modell" bleibt dem
Sprachmodell vorbehalten, technik.md §3) entsteht in diesem Modul.

Voraussetzungen
---------------
`new_card_guid` wird aufgerufen, **bevor** die zugehörige `Card` gebaut wird: `Card.guid`
ist ein Pflichtfeld (`entities.Card`), es gibt also keinen Zeitpunkt, zu dem eine `Card`
ohne GUID existiert. Der Aufrufer (T15/T16, noch nicht gebaut) ruft
`new_card_guid(occurrence, sense, card_direction)` auf und übergibt das Ergebnis dem
`Card`-Konstruktor; erst danach kennt dieses Modul die Karte überhaupt. `export_deck`
erwartet Karten **eines** Exports; `sense.uncertain=True` schließt eine Karte **nicht**
aus — der Nutzer hat sie in der Triage bewusst gewählt, sie ist nur unbestätigt (Befund 3,
Review T13), und bekommt statt eines Ausschlusses den Tag `unsicher` (siehe `_tags`).
Fehlt einer solchen Karte auch die Übersetzung, tritt eine deutsche Textmarke an deren
Stelle statt eines Abbruchs — dieselbe Unterscheidung, die `printout.py` für die Druckseite
trifft (dort `_translation_html`, hier `_translation_text` unten). Dieses Modul importiert
aus dem Kern ausschließlich `entities` (technik.md §7, „Die Importregel") — insbesondere
nicht `profile`: Die GUID **zurückzuschreiben**, ist Sache des Aufrufers.

Liefert
-------
`new_card_guid` eine stabile Anki-GUID (Anki-Base91, über `genanki.guid_for`) aus Buch,
Kapitel, Grundform samt Wortart, der Bedeutung (`wikdict_lexentry`, `wikdict_sense`) und
Kartenrichtung — bewusst ohne die Übersetzung und ohne `wikdict_trans_list` (Regel 6,
Begründung am Funktionskopf unten). `export_deck` schreibt eine `.apkg`-Datei mit einer
Notiz je `Card`: Feldern nach konzept.md §6 (Wort, Grundform, Übersetzung, Wortart,
Belegsatz, Buch, Kapitel — beim Lückentext ersetzt die Cloze-Markierung im Belegsatz das
eigene Wort-Feld; `word_form` kann bei einem Mehrwortausdruck mehrere Wörter umfassen,
`extraction.py`, Befund 3 Review T4/Befund 8 Review T13 — Wort-Feld und Lückentext
behandeln es unverändert als eine Zeichenkette) und Verschlagwortung nach Buch, Autor und
Kapitel, dazu `unsicher` bei einer unbestätigten Bedeutung. Das Feld „Wortart" zeigt bei
einer Wendung ohne Einzelwortart „MWE" statt eines leeren Felds (`pos_display`, mittel 4,
Abnahme T17) — dieselbe Angabe wie `cli.interaction` auf dem Bildschirm.

Eine leere Kartenliste, zwei
Karten mit derselben GUID innerhalb desselben Exports (Befund 2, Review T13), eine
fehlende Übersetzung ohne die Marke `uncertain` oder ein Lückentext, dessen Wortform an
keiner Wortgrenze im Belegsatz steht (Befund 4, Review T13), sind sichtbare Fehlschläge
(Regel 13), keine leere oder unvollständige Datei.

`card_obstacle` beantwortet die beiden letzteren Fälle **vorab**, damit ein Aufrufer sie
nicht erst am Ende eines Durchlaufs erfährt — siehe dort.
"""

from __future__ import annotations

import hashlib
import html
from collections.abc import Sequence
from pathlib import Path

import genanki

from libreverbum.entities import Card, CardDirection, Occurrence, Sense

# ------------------------------------------------------------------------------- GUID


# REGEL (dokumentation.md §4 Regel 6, „Anki-GUID beim Export in card mitschreiben"):
# genanki bildet seine vorgegebene GUID vorgabemäßig aus dem Hash aller Feldwerte der
# Notiz (genanki.note.Note.guid, genanki.util.guid_for, ungesetzt bei `guid=None`). Eine
# korrigierte Übersetzung änderte damit die GUID — Anki legte beim nächsten Import eine
# zweite Notiz an, und der Lernfortschritt der alten hinge an einer Karteileiche, während
# Regel 6 formal erfüllt bliebe (eine Spalte `guid` stünde in `card`), aber faktisch
# verletzt wäre. `new_card_guid` verwendet deshalb `genanki.guid_for` nur als Hash- und
# Base91-Umrechnung, mit selbst gewählten Werten statt der Notiz-Feldwerte: Buch, Kapitel,
# Grundform samt Wortart, Kartenrichtung — und die Bedeutung selbst (Befund 1, Review
# T13):
#
# - `translation` bleibt draußen, weil genau dagegen diese Regel geschrieben ist: Eine
#   korrigierte Übersetzung darf keine neue GUID erzeugen. Das war der Grund für die
#   Eigenvergabe statt genankis Vorgabe
# - `wikdict_lexentry` und `wikdict_sense` kommen hinein, weil sie im Sinne von
#   `Sense.__eq__` die Bedeutung unterscheiden und dabei unabhängig von der Übersetzung
#   sind — `Sense` führt `translation` und `uncertain` mit `compare=False` ausdrücklich
#   außerhalb seiner Identität. Ohne sie bekämen zwei verschiedene Bedeutungen derselben
#   Grundform (`profile.compare_chapter_vocabulary`s `NEW_MEANING_OF_KNOWN_WORD`,
#   `profile.py`, Zeilen 427-456) dieselbe GUID, und Anki überschriebe beim Import die
#   erste Karte still mit der zweiten. `wikdict_lexentry` allein genügt dabei nicht
#   (`entities.Sense`-Docstring: 22,7 % der Zeilen mit `lexentry` fallen zusammen —
#   `watch` als Substantiv dreimal „Wache")
# - `wikdict_trans_list` bleibt draußen, obwohl es zu `Sense.__eq__` gehört: Es ist die
#   deutsche Seite und ändert sich zwischen Wörterbuchausgaben am ehesten, unterscheidet
#   im heutigen Bestand aber nichts, was `wikdict_sense` nicht schon unterscheidet
#   (gemessen über alle 157.801 Zeilen, `entities.Sense`-Docstring)
# - Der Preis: Ein neu bezogenes Wörterbuch, das den `sense`-Text ändert, erzeugt für
#   diese Bedeutung eine neue GUID und damit eine zweite Notiz. Bewusst in Kauf
#   genommen, weil die Gegenseite — eine still überschriebene Karte — der schwerere
#   Schaden ist: Die Doppelkarte ist sichtbar und korrigierbar, der überschriebene
#   Lernfortschritt nicht (offener Punkt, technik.md §2, „Warum nicht mitgeliefert")
#
# `occurrence.chapter_number` bleibt bewusst im Schlüssel (Befund 5, Review T13): Allein
# `KnowledgeState.KNOWN` gilt als bekannt (`profile.py`, `compare_chapter_vocabulary`), ein
# Wort im Zustand `learning` wird also in einem späteren Kapitel erneut angeboten und
# bekäme dort eine zweite Karte. Das ist keine Nebenwirkung, sondern stimmig mit
# `entities.Occurrence`: „Ein Eintrag je Kapitel und Grundform — dasselbe Wort hat in
# Kapitel 2 einen anderen Belegsatz als in Kapitel 9". Zwei Kapitel, zwei Belegsätze, zwei
# Karten.
def new_card_guid(occurrence: Occurrence, sense: Sense, card_direction: CardDirection) -> str:
    """Stabile Anki-GUID für eine Karte aus `occurrence`, `sense` und `card_direction`
    (Regel 6).

    Entsteht vor dem Bau der zugehörigen `Card` — Aufrufreihenfolge: `new_card_guid`,
    dann `Card(..., guid=…)`, dann `export_deck`. Buch, Kapitel und Grundform bestimmen
    ein `Occurrence` bereits eindeutig (`entities.Occurrence`, „Ein Eintrag je Kapitel und
    Grundform"); `sense.wikdict_lexentry` und `sense.wikdict_sense` unterscheiden
    zusätzlich zwei Bedeutungen **derselben** Grundform im selben Kapitel (Befund 1,
    Review T13) — ohne sie trüge die zweite Bedeutung aus
    `profile.compare_chapter_vocabulary`s `NEW_MEANING_OF_KNOWN_WORD` dieselbe GUID wie
    die erste, und Anki überschriebe beim Import die erste Karte kommentarlos.
    """
    return str(
        genanki.guid_for(
            occurrence.book.title,
            occurrence.book.author,
            occurrence.chapter_number,
            occurrence.lemma.text,
            occurrence.lemma.pos,
            sense.wikdict_lexentry,
            sense.wikdict_sense,
            card_direction.value,
        )
    )


# --------------------------------------------------------------------- Kartenvorlagen

_SHARED_FIELDS = [
    {"name": "Wort"},
    {"name": "Übersetzung"},
    {"name": "Grundform"},
    {"name": "Wortart"},
    {"name": "Belegsatz"},
    {"name": "Buch"},
    {"name": "Kapitel"},
]

_ANSWER_SUFFIX = (
    "{{Grundform}} ({{Wortart}})<br><i>{{Belegsatz}}</i><br>{{Buch}}, Kapitel {{Kapitel}}"
)

# REGEL (dokumentation.md §4 Regel 6, sinngemäß auf die Kartenvorlage übertragen): Feste
# Kennungen, wie genankis eigene builtin_models.py sie für „Basic" & Co. vergibt —
# wechselte die Kennung zwischen zwei Exporten, legte Anki beim zweiten Import eine
# zweite Kartenvorlage an, statt die bestehende zu verwenden. Einmalig zufällig gewählt
# (>10^9, wie genankis eigener Rat in builtin_models.py), danach unveränderlich.
_EN_DE_MODEL_ID = 1814874857
_DE_EN_MODEL_ID = 1573714139
_CLOZE_MODEL_ID = 1781948404

_EN_DE_MODEL = genanki.Model(
    _EN_DE_MODEL_ID,
    "LibreVerbum EN-DE (genanki)",
    fields=_SHARED_FIELDS,
    templates=[
        {
            "name": "Erkennen",
            "qfmt": "{{Wort}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{Übersetzung}}<br>" + _ANSWER_SUFFIX,
        }
    ],
)

_DE_EN_MODEL = genanki.Model(
    _DE_EN_MODEL_ID,
    "LibreVerbum DE-EN (genanki)",
    fields=_SHARED_FIELDS,
    templates=[
        {
            "name": "Produzieren",
            "qfmt": "{{Übersetzung}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{Wort}}<br>" + _ANSWER_SUFFIX,
        }
    ],
)

_CLOZE_FIELDS = [
    {"name": "Text"},
    {"name": "Übersetzung"},
    {"name": "Grundform"},
    {"name": "Wortart"},
    {"name": "Buch"},
    {"name": "Kapitel"},
]

_CLOZE_MODEL = genanki.Model(
    _CLOZE_MODEL_ID,
    "LibreVerbum Lückentext (genanki)",
    model_type=genanki.Model.CLOZE,
    fields=_CLOZE_FIELDS,
    templates=[
        {
            "name": "Lückentext",
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}<br>{{Übersetzung}}<br>{{Grundform}} ({{Wortart}})<br>"
            "{{Buch}}, Kapitel {{Kapitel}}",
        }
    ],
)

_NOTE_MODELS: dict[CardDirection, genanki.Model] = {
    CardDirection.EN_DE: _EN_DE_MODEL,
    CardDirection.DE_EN: _DE_EN_MODEL,
    CardDirection.CLOZE: _CLOZE_MODEL,
}


# --------------------------------------------------------------------------- Felder


def _escaped(value: str) -> str:
    """Escaped für ein Anki-Feld — nur `&`, `<` und `>` (`quote=False`), damit
    typografische Anführungszeichen und Apostroph aus dem Buchtext unangetastet bleiben
    (CLAUDE.md, „Dateien immer mit encoding=utf-8 öffnen")."""
    return html.escape(value, quote=False)


# Wortgleich mit `printout._UNCERTAIN_MARK` samt dessen Zusatz, aber eine eigene
# Konstante: `anki` und `printout` importieren aus dem Kern beide nur `entities`
# (technik.md §7, „Die Importregel"), keines der beiden darf das andere holen. Der gleiche
# Wortlaut ist dabei Absicht — dieselbe Lage soll auf der Karte heißen wie auf dem Papier.
_UNCERTAIN_TEXT = "unsicher – kein Wörterbucheintrag"


def _translation_text(card: Card) -> str:
    """Der Wert des Feldes „Übersetzung" — dieselben drei `uncertain`-Fälle, die
    `printout.py`, „Wie mit uncertain verfahren wird" für die Druckseite unterscheidet
    (Regel 10, Regel 13):

    - **Ohne Übersetzung, `uncertain`:** kein Fehlschlag, sondern `_UNCERTAIN_TEXT`. Genau
      diesen Platzhalter trägt ein Wort ohne Wörterbucheintrag (`pipeline.run_chapter` für
      eine leere Auswahlliste, `dictionary.particle_verb_candidates` für ein Phrasal Verb
      ohne Treffer), und der Nutzer hat ihn in der Triage bewusst gewählt: Es fehlt die
      Bedeutung, nicht die Karte. Sie trägt zusätzlich den Tag `unsicher` (`_tags`) und
      lässt sich in Anki von Hand ergänzen.
    - **Ohne Übersetzung, nicht `uncertain`:** ein echter Fehlschlag der Vorstufe,
      sichtbarer Abbruch (Regel 13) — wie bisher.
    - **Mit Übersetzung, `uncertain`:** die Übersetzung; die Unsicherheit trägt hier der
      Tag, nicht das Feld.

    Bis zum 01.09.2026 brach der erste Fall ebenso ab wie der zweite. Gemeldet aus einem
    Kapiteldurchlauf: Ein einziges „lernen" auf einem Wort ohne Wörterbucheintrag ließ den
    gesamten Export scheitern — Deck **und** Druckseite, denn `pipeline.export_cards`
    ruft `export_deck` zuerst. Der Fall ist häufig, nicht selten: Von 25 in der Triage
    gezeigten Einträgen tragen 2 (A1) bis 9 (C1) nur den Platzhalter (technik.md §11,
    „Warum C2 nicht angeboten wird"). Der Tag `unsicher` in `_tags` war unter der alten
    Prüfung damit unerreichbar, und konzept.md §5 verlangt für einen fehlenden
    Wörterbuchtreffer ausdrücklich, den Eintrag zu **markieren** statt ihn abzuweisen.

    Ausnahme `CardDirection.DE_EN`: Dort steht dieses Feld auf der **Vorderseite**
    (`_DE_EN_MODEL`, `qfmt`), und `_UNCERTAIN_TEXT` als Frage ergibt keine Karte, sondern
    eine leere Abfrage — bei mehreren solchen Wörtern sogar mehrmals dieselbe. Was keine
    deutsche Seite hat, lässt sich nicht produzieren; das bleibt ein sichtbarer Abbruch.
    Damit er nicht wieder einen ganzen Durchlauf kostet, lässt `cli.interaction`
    („lernen" in `_individual_phase`) einen solchen Eintrag in dieser Kartenrichtung gar
    nicht erst zur Karte werden — die Prüfung hier ist der Rückhalt, nicht der Regelweg.
    """
    sense = card.sense
    if sense.translation is not None:
        return sense.translation
    if sense.uncertain and card.card_direction is not CardDirection.DE_EN:
        return _UNCERTAIN_TEXT
    if sense.uncertain:
        raise ValueError(
            f"„{card.occurrence.lemma.text}“ ({card.occurrence.lemma.pos}) hat keinen "
            "Wörterbucheintrag — in Kartenrichtung de_en stünde die Marke „unsicher“ als "
            "Frage auf der Vorderseite. Solche Wörter mit --card-direction en_de oder "
            "cloze exportieren, oder in der Triage überspringen."
        )
    raise ValueError(
        f"„{card.occurrence.lemma.text}“ ({card.occurrence.lemma.pos}) hat keine "
        "aufgelöste Übersetzung (sense.translation ist None) und ist nicht als unsicher "
        "markiert (sense.uncertain) — Export nur für Karten mit aufgelöster oder als "
        "unsicher bestätigter Bedeutung."
    )


_WORD_CONTINUING_EXTRA = {"'", "’", "-"}


def _is_word_boundary(char: str | None) -> bool:
    """`char` setzt kein Wort fort — `None` an den Satzrändern, sonst weder
    Buchstabe/Ziffer noch Apostroph (gerade `'` oder typografisch `’`) noch Bindestrich
    (Befund 4, Review T13). Die beiden Letzteren zählen mit, weil eine Wortform selbst
    Apostroph oder Bindestrich enthalten kann (`don't`, `well-known`) — ein Zeichen davor
    oder danach darf das Vorkommen trotzdem nur dann als Wortgrenze gelten, wenn es die
    Wortform nicht fortsetzt."""
    return char is None or not (char.isalnum() or char in _WORD_CONTINUING_EXTRA)


def _find_word_at_boundary(sentence: str, word: str) -> int:
    """Erstes Vorkommen von `word` in `sentence`, das an beiden Enden an einer
    Wortgrenze steht — anders als `str.find` nicht die erste Zeichenkette (Befund 4,
    Review T13): `watch` in „The watchman watched his watch." trifft weder `watchman`
    noch `watched`. `-1`, wenn kein Vorkommen an einer Wortgrenze steht."""
    start = 0
    while True:
        index = sentence.find(word, start)
        if index == -1:
            return -1
        before = sentence[index - 1] if index > 0 else None
        after_index = index + len(word)
        after = sentence[after_index] if after_index < len(sentence) else None
        if _is_word_boundary(before) and _is_word_boundary(after):
            return index
        start = index + 1


def _cloze_text(occurrence: Occurrence) -> str:
    """Der Belegsatz mit der Wortform als Cloze-Lücke (`{{c1::…}}`) — sichtbarer
    Fehlschlag (Regel 13), wenn `word_form` an keiner Wortgrenze in `example_sentence`
    steht (Befund 4, Review T13), statt eines Teilworttreffers (`watch` in `watchman`)
    oder eines Belegsatzes ohne Lücke, der wie ein vollständiger Lückentext aussähe."""
    sentence = occurrence.example_sentence
    word = occurrence.word_form
    index = _find_word_at_boundary(sentence, word)
    if index == -1:
        raise ValueError(
            f"Wortform „{word}“ kommt im Belegsatz „{sentence}“ an keiner Wortgrenze "
            "wortwörtlich vor — Lückentext nicht bildbar."
        )
    before, after = sentence[:index], sentence[index + len(word) :]
    return f"{_escaped(before)}{{{{c1::{_escaped(word)}}}}}{_escaped(after)}"


# (mittel 4, Abnahme T17, 25.08.2026): `occurrence.lemma.pos` ist bei einem Kandidaten aus
# `extraction.extract_contiguous_candidates` leer (`extraction._NO_SINGLE_POS`) — eine
# Wendung ohne syntaktischen Kopf hat keine einzelne Wortart (`extraction.py`,
# „extract_contiguous_candidates"). `_fields` trug das bisher unverändert ins Kartenfeld
# „Wortart", die Kartenrückseite zeigte dann „… ({{Wortart}})" als sichtbar leere Klammer.
# `cli.interaction` zeigte an derselben Stelle bereits „MWE" (`_entry_lines`,
# `_bulk_phase`) — diese Funktion ist der eine Ort für beide Aufrufer, damit Karte und
# Bildschirm dieselbe Angabe zeigen, statt sie an zwei Stellen gepflegt zu haben.
def pos_display(pos: str) -> str:
    """Wortart-Anzeige für Karte und Bildschirm: „MWE" bei leerem `pos` (Mehrwortausdruck
    ohne Einzelwortart), sonst `pos` unverändert."""
    return pos or "MWE"


def _fields(card: Card) -> list[str]:
    """Feldwerte in der Reihenfolge der jeweiligen Kartenvorlage — `_SHARED_FIELDS` für
    `EN_DE`/`DE_EN`, `_CLOZE_FIELDS` für `CLOZE`."""
    occurrence = card.occurrence
    translation = _translation_text(card)
    chapter = str(occurrence.chapter_number)
    if card.card_direction == CardDirection.CLOZE:
        return [
            _cloze_text(occurrence),
            _escaped(translation),
            _escaped(occurrence.lemma.text),
            _escaped(pos_display(occurrence.lemma.pos)),
            _escaped(occurrence.book.title),
            chapter,
        ]
    return [
        _escaped(occurrence.word_form),
        _escaped(translation),
        _escaped(occurrence.lemma.text),
        _escaped(pos_display(occurrence.lemma.pos)),
        _escaped(occurrence.example_sentence),
        _escaped(occurrence.book.title),
        chapter,
    ]


def _tag(value: str) -> str:
    """Anki verweigert Leerzeichen im Tag (`genanki.note._TagList._validate_tag`) —
    ersetzt jeden Weißraum durch einen Unterstrich, statt den Titel zu kürzen oder die
    Verschlagwortung auszulassen. Nicht nur das Leerzeichen (Befund 7, Review T13):
    Tabulator und Zeilenumbruch aus `dc:title` überleben `epub._text_of` (die nur außen
    strippt) und träfen sonst dieselbe Anki-Prüfung — Tags werden an jedem Weißraum
    getrennt, nicht nur am Leerzeichen."""
    return "_".join(value.split())


def _tags(card: Card) -> list[str]:
    """Verschlagwortung nach Buch, Autor und Kapitel (konzept.md §6, „Export"), dazu
    `unsicher` bei einer unbestätigten Bedeutung (Befund 3, Review T13): `dictionary.py`
    (Zeilen 93-103) verlangt, dass der Unterschied „vor der Anzeige (T11, T13)" sichtbar
    wird. Kein Abbruch — der Nutzer hat die Karte in der Triage bewusst gewählt, nur die
    Bedeutung ist unbestätigt — sondern ein eigener, in Anki filterbarer Tag."""
    occurrence = card.occurrence
    tags = [
        f"buch::{_tag(occurrence.book.title)}",
        f"autor::{_tag(occurrence.book.author)}",
        f"kapitel::{occurrence.chapter_number}",
    ]
    if card.sense.uncertain:
        tags.append("unsicher")
    return tags


def _deck_id(deck_name: str) -> int:
    """Deck-Kennung aus dem Decknamen — deterministisch statt zufällig, damit ein
    zweiter Export desselben Buchs oder Kapitels in Anki denselben Stapel trifft, nicht
    einen weiteren anlegt (derselbe Beweggrund wie bei der GUID, hier auf Ebene des
    Decks statt der einzelnen Karte)."""
    digest = hashlib.sha256(deck_name.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big") % (1 << 63)


# ------------------------------------------------------------------------------ Export


def card_obstacle(
    occurrence: Occurrence, sense: Sense, card_direction: CardDirection
) -> str | None:
    """Was der Kartenerzeugung in dieser Kartenrichtung im Weg steht, als deutscher Satz —
    oder `None`, wenn nichts im Weg steht (Befund mittel, Durchsicht 35736a9).

    Beantwortet **vorab**, woran `export_deck` sonst erst am Ende scheitert. Beide
    Unmöglichkeiten hängen allein an `occurrence`, `sense` und der Kartenrichtung und
    brauchen weder Wörterbuch noch Modell:

    - **`DE_EN` ohne Übersetzung:** Das Feld steht dort auf der Vorderseite
      (`_DE_EN_MODEL`, `qfmt`) — eine Textmarke als Frage ergibt keine Karte, sondern eine
      leere Abfrage (`_translation_text`)
    - **`CLOZE`, dessen Wortform an keiner Wortgrenze des Belegsatzes steht:** Ohne Lücke
      kein Lückentext (`_cloze_text`, Befund 4, Review T13). Gemessen an
      `tools/dorian_gray.epub` trifft das 2.170 von 103.897 Wortvorkommen der Kapitel 1
      bis 12 (2,1 %), in Kapitel 10 allein 22 von 663 — Bindestrichkomposita wie
      `heart-broken` und Wortformen unmittelbar vor einem typografischen Apostroph
      (`the girl's mother`), beides Folgen von `_WORD_CONTINUING_EXTRA` und damit gewollt

    Warum diese Frage getrennt vom Abbruch existiert: `pipeline.export_cards` ruft
    `export_deck` **vor** `printout.write_printout`. Ein Abbruch dort kostet deshalb beide
    Dateien samt aller übrigen Karten eines Durchlaufs — nach vollständig durchlaufener
    Triage, also zum teuersten denkbaren Zeitpunkt. Genau das ist am 01.09.2026 aus der
    Praxis gemeldet worden (technik.md §8b, „Ein Wort ohne Wörterbucheintrag kostet nicht
    mehr den ganzen Export"). Der Aufrufer (`cli.interaction`)
    fragt deshalb **vor** der Entscheidung; die Abbrüche in `_translation_text` und
    `_cloze_text` bleiben der Rückhalt für jeden Weg, der hier nicht vorbeikommt (Regel
    13). Beide Seiten müssen sich einig sein — geprüft in `tests/test_anki.py`.

    Der Satz ist Oberflächentext und deshalb deutsch (dokumentation.md §1): Der Aufrufer
    gibt ihn unverändert aus, statt aus einem bloßen `bool` eine eigene Begründung zu
    bilden. Welche Kartenvorlage welches Feld auf die Vorderseite nimmt, weiß dieses
    Modul — nicht die Oberfläche.
    """
    if card_direction is CardDirection.DE_EN and sense.translation is None:
        return (
            f"„{occurrence.lemma.text}“ hat keinen Wörterbucheintrag — in Kartenrichtung "
            "de_en bliebe die Vorderseite ohne deutsche Bedeutung."
        )
    if (
        card_direction is CardDirection.CLOZE
        and _find_word_at_boundary(occurrence.example_sentence, occurrence.word_form) == -1
    ):
        return (
            f"„{occurrence.word_form}“ kommt im Belegsatz an keiner Wortgrenze wortwörtlich "
            "vor — daraus ist kein Lückentext zu bilden."
        )
    return None


def export_deck(path: Path, cards: Sequence[Card], *, deck_name: str) -> None:
    """Schreibt `cards` als `.apkg`-Datei nach `path` (bauplan.md T13, Abnahmekriterium
    4): eine Notiz je Karte, Kartenvorlage nach `card.card_direction`, Verschlagwortung
    nach Buch, Autor und Kapitel (dazu `unsicher` bei `sense.uncertain`, siehe `_tags`).

    Verwendet ausschließlich `card.guid` (Regel 6) — dieses Modul erfindet keine eigene
    GUID, `new_card_guid` erzeugt sie vor dem Bau der `Card`. Eine leere Kartenliste, ein
    nicht existierendes Zielverzeichnis und zwei Karten mit derselben GUID innerhalb
    desselben Aufrufs (Befund 2, Review T13 — genanki prüft, warnt und bricht dabei selbst
    nicht ab) sind sichtbare Fehlschläge (Regel 13; dasselbe Muster wie
    `profile.open_profile` für das Profilverzeichnis, technik.md §9, „Der Kern kennt keine
    Vorgabe") — ebenso jeder Fehlschlag aus `_translation_text` und `_cloze_text`.
    """
    if not cards:
        raise ValueError("Export ohne Karten ergibt kein sinnvolles Anki-Deck.")
    if not path.parent.is_dir():
        raise ValueError(f"Zielverzeichnis {path.parent} für den Export existiert nicht.")

    # (Befund 2, Review T13): genanki prüft Doppel-GUIDs innerhalb eines Exports nicht —
    # die zweite Notiz verschwände sonst erst beim Import in Anki, außerhalb der
    # Reichweite jeder Meldung. Deshalb hier, vor jedem Schreibzugriff.
    seen_guids: set[str] = set()
    for card in cards:
        if card.guid in seen_guids:
            raise ValueError(
                f"GUID „{card.guid}“ kommt mehrfach unter den zu exportierenden Karten "
                "vor — Anki verwürfe die zweite Notiz beim Import kommentarlos."
            )
        seen_guids.add(card.guid)

    deck = genanki.Deck(_deck_id(deck_name), deck_name)
    for card in cards:
        note = genanki.Note(
            model=_NOTE_MODELS[card.card_direction],
            fields=_fields(card),
            tags=_tags(card),
            guid=card.guid,
        )
        deck.add_note(note)

    genanki.Package(deck).write_to_file(path)
