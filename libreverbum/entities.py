"""Die Gegenstände des Kernablaufs — die sieben aus technik.md §4 samt ihren Aufzählungen.

Voraussetzungen
---------------
Keine. Das Modul liest und schreibt nichts und importiert nichts aus dem Kern — es ist
das einzige, das jeder Schritt importieren darf (technik.md §7, „Die Importregel").

Liefert
-------
`Book`, `Chapter`, `Lemma`, `Sense`, `Occurrence`, `Event` und `Card` als Datenklassen,
dazu `KnowledgeState`, `Origin` und `CardDirection`. **Nicht** den Kenntnisstand: Der ist
die Ableitung aus der Ereignisfolge und entsteht in `profile`.

Alle Klassen sind `frozen`. Ein Vorkommen, ein Ereignis und eine Karte sind Feststellungen
zu einem Zeitpunkt; geändert wird nicht der Gegenstand, sondern es kommt ein neues Ereignis
dazu (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem Zustand").
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

# StrEnum und nicht Enum: Der Wert ist der Text, der später in der Spalte steht. Damit
# braucht das Profil keine Umrechnung beim Schreiben und keine beim Lesen.


class KnowledgeState(StrEnum):
    """Kenntnisstand einer Bedeutung. Zugleich die Art eines Ereignisses — „am 12.08.2026
    wurde diese Bedeutung als bekannt eingestuft" ist beides in einem."""

    KNOWN = "known"
    LEARNING = "learning"
    DEFERRED = "deferred"
    FORGOTTEN = "forgotten"


class Origin(StrEnum):
    """Herkunft einer Kenntnisangabe.

    Phase 1 kennt nur die drei Herkünfte der Triage. Sie sind zu unterscheiden, weil sie
    verschieden viel behaupten: Eine Sammelaktion stuft hunderte Wörter mit einem Tastendruck
    ein, die Wortobergrenze stellt zurück, ohne dass der Nutzer das Wort gesehen hat."""

    TRIAGE = "triage"
    BULK_MARK = "bulk_mark"
    WORD_LIMIT = "word_limit"


class CardDirection(StrEnum):
    """Kartenrichtung, je Export wählbar (konzept.md §6, „Export")."""

    EN_DE = "en_de"
    DE_EN = "de_en"
    CLOZE = "cloze"


@dataclass(frozen=True)
class Book:
    """Ein eingelesenes Buch. Mehr als Titel und Autor braucht Phase 1 nicht: Beides steht
    auf jeder Karte und in deren Verschlagwortung (konzept.md §6, „Export")."""

    title: str
    author: str


@dataclass(frozen=True)
class Chapter:
    """Ein Kapitel samt seinem Fließtext.

    `number` zählt ab 1 in der Reihenfolge des `spine`, auch wenn die Kapitelliste aus der
    Navigation stammt; fehlt die Navigation, ist jedes Dokument der Lesereihenfolge ein
    Kapitel (technik.md §8). `text` ist bereits von Inhaltsverzeichnis, Impressum und
    Fußnoten getrennt — das tut `epub`, nicht `extraction`. Er gehört zum eingelesenen
    Kapitel; ins Profil wandert davon nur, welches Kapitel verarbeitet wurde."""

    book: Book
    number: int
    title: str
    text: str


@dataclass(frozen=True)
class Lemma:
    """Grundform und Wortart — die Klammer um die Bedeutungen, nicht die Einheit, an der
    Kenntnis hängt (technik.md §4, „Kernentscheidung: Kenntnis pro Bedeutung, nicht pro
    Wort").

    `pos` ist spaCys `token.pos_` und bleibt deshalb unübersetzt (dokumentation.md §1).
    Mehrwortausdrücke sind dieselbe Klammer mit Leerzeichen im Text (`give up`), Eigennamen
    dieselbe Klammer mit `pos` `PROPN` (technik.md §4, „Tabellen im Überblick"). Ob ein Wort
    als Eigenname aussortiert wird, entscheidet nicht diese Klasse, sondern `Occurrence`."""

    text: str
    pos: str


@dataclass(frozen=True)
class Sense:
    """Eine Bedeutung eines Lemmas — die Einheit, an der Kenntnis hängt.

    `wikdict_sense` ist `None`, wo das Wörterbuch keinen Bedeutungstext führt. Das ist der
    Regelfall und nicht der Ausnahmefall: 36 % der Zeilen, systematisch die Hauptbedeutungen
    (Regel 1). Bei einer Wendung ohne Wörterbucheintrag fehlen alle `wikdict_`-Werte, und
    `uncertain` ist gesetzt.

    Identität (Gleichheit und Hash) bilden allein `lemma` und `wikdict_lexentry` — die
    Kennung der Wörterbuchzeile, nicht ihr Text. `translation` und `uncertain` sind
    Ergebnisfelder, die T11 erst während des Durchlaufs füllt, und `wikdict_sense` ist die
    Momentaufnahme des Bedeutungstexts; alle drei bleiben deshalb außerhalb von Gleichheit
    und Hash (`compare=False`), sonst wäre dieselbe Bedeutung vor und nach der Übersetzung
    oder nach einem Wörterbuch-Update ein anderes Objekt."""

    lemma: Lemma
    translation: str | None = field(default=None, compare=False)

    # REGEL (technik.md §4, „Getrennte Datei — nicht mit dem Wörterbuch mischen"):
    # wikdict_sense ist eine Momentaufnahme, nie Schlüssel. WikDict wird aus Wiktionary
    # erzeugt und formuliert Bedeutungen um; ein Fremdschlüssel dorthin zerbräche das Profil
    # beim nächsten Wörterbuch-Update, ohne dass es beim Schreiben auffiele. Aus demselben
    # Grund bleibt es außerhalb von Gleichheit und Hash: Sonst wäre nach einem
    # Wörterbuch-Update dieselbe Bedeutung ein anderes Objekt. wikdict_lexentry bleibt dabei
    # in Gleichheit und Hash — es ist die Kennung der Zeile und das einzige Feld, das zwei
    # Bedeutungen desselben Lemmas ohne Bedeutungstext unterscheidet (Regel 1).
    wikdict_sense: str | None = field(default=None, compare=False)
    wikdict_lexentry: str | None = None

    # REGEL (dokumentation.md §4 Regel 13 und 14, technik.md §3 „Die Falle: es scheitert
    # nicht laut, sondern leise"): Ein Fehlschlag beim Nachschlagen oder bei der
    # Bedeutungsauswahl bleibt im Ergebnis sichtbar statt still durchgereicht — sei es eine
    # Wendung ohne Wörterbucheintrag oder die Ausweichantwort des Modells. Phase 1 liest
    # den Grund nirgends unterschiedlich aus, deshalb genügt ein reiner Marker. Wie
    # `translation` ist es ein Ergebnisfeld und bleibt außerhalb von Gleichheit und Hash.
    uncertain: bool = field(default=False, compare=False)

    # REGEL (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem
    # Zustand"): Hier steht bewusst kein Kenntnisstand. Er ist das jüngste `Event` zu dieser
    # Bedeutung. Ein Feld daneben liefe beim ersten Rückkanal-Ereignis auseinander, und die
    # Vorgeschichte „schon einmal gekonnt" wäre überschrieben statt erhalten.


@dataclass(frozen=True)
class Occurrence:
    """Vorkommen einer Grundform in einem Kapitel: Belegsatz, Häufigkeit und wie oft davon
    ein Eigenname war.

    Ein Eintrag je Kapitel und Grundform — dasselbe Wort hat in Kapitel 2 einen anderen
    Belegsatz als in Kapitel 9 (technik.md §4, „Tabellen im Überblick"). `word_form` ist die
    Beugungsform aus `example_sentence`; sie steht später auf der Karte. `book` und
    `chapter_number` statt eines vollständigen `Chapter`: Ins Profil wandert nur, welches
    Kapitel verarbeitet wurde, nicht dessen Fließtext (siehe `Chapter`-Docstring)."""

    book: Book
    chapter_number: int
    lemma: Lemma
    word_form: str
    example_sentence: str
    frequency: int

    # REGEL (technik.md §5, „Neuer Befund: der Eigennamenfilter muss pro Vorkommen
    # greifen"): Deshalb eine Zahl hier und kein Kennzeichen am Lemma. 216 Wortformen gelten
    # manchmal als Eigenname und kommen daneben gewöhnlich vor; wer pro Grundform filtert,
    # verliert `red`, `orange` und `street` ganz aus der Triage. Lernvokabel bleibt, was
    # `proper_noun_frequency < frequency` erfüllt.
    proper_noun_frequency: int


@dataclass(frozen=True)
class Event:
    """Ein Eintrag im Verlauf: Diese Bedeutung wurde zu diesem Zeitpunkt aus dieser Herkunft
    so eingestuft.

    Ereignisse werden angehängt, nie geändert. Der Kenntnisstand ist das jüngste Ereignis je
    Bedeutung (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem
    Zustand"). `book` und `chapter_number` statt eines vollständigen `Chapter`, aus
    demselben Grund wie bei `Occurrence`. `timestamp` ist zeitzonenbehaftet (UTC) — der
    Kenntnisstand vergleicht nach dem jüngsten Ereignis, und dafür brauchen alle Ereignisse
    dieselbe Zeitbasis."""

    sense: Sense
    knowledge_state: KnowledgeState
    origin: Origin
    timestamp: datetime
    book: Book
    chapter_number: int


@dataclass(frozen=True)
class Card:
    """Eine exportierte Anki-Karte. Wort, Grundform, Wortart, Belegsatz, Buch und Kapitel
    stehen im `occurrence`, die Übersetzung im `sense` (konzept.md §6, „Export")."""

    sense: Sense
    occurrence: Occurrence
    card_direction: CardDirection

    # REGEL (technik.md §4, „Jetzt billig, später teuer: die Anki-Kennung"): Die GUID wird
    # beim Export mitgeschrieben, obwohl in Phase 1 niemand sie liest. Ohne sie lässt sich
    # der Rückkanal aus Phase 3 nur anschließen, indem alle bereits exportierten Decks neu
    # erzeugt werden — was beim Nutzer den Lernfortschritt in Anki zurücksetzt.
    guid: str
