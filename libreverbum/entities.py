"""Die Gegenstände des Kernablaufs — die sieben aus technik.md §4 samt ihren Aufzählungen.

Voraussetzungen
---------------
Keine. Das Modul liest und schreibt nichts und importiert nichts aus dem Kern — es ist
das einzige, das jeder Schritt importieren darf (technik.md §7, „Die Importregel").

Liefert
-------
`Book`, `Chapter`, `Lemma`, `Sense`, `Occurrence`, `ProperNounEntry`, `Event` und `Card`
als Datenklassen, dazu `KnowledgeState`, `Origin`, `CardDirection` und `CefrLevel`.
**Nicht** den Kenntnisstand: Der ist die Ableitung aus der Ereignisfolge und entsteht in
`profile`.

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

    Die Herkünfte benennen den **Akt**, nicht das Ergebnis: Eine Sammelaktion stuft
    hunderte Wörter mit einem Tastendruck ein, die Wortobergrenze stellt zurück, ohne dass
    der Nutzer das Wort gesehen hat, und die Vorbelegung (`PRESET`) trägt Bedeutungen des
    Grundwortschatzes beim Anlegen des Profils pauschal als bekannt ein, bevor der Nutzer
    das Wort je gesehen hat (konzept.md, „Bewusst offen", „Woher der Nutzer seinen
    Grundwortschatz bekommt")."""

    TRIAGE = "triage"
    BULK_MARK = "bulk_mark"
    WORD_LIMIT = "word_limit"
    PRESET = "preset"


class CardDirection(StrEnum):
    """Kartenrichtung, je Export wählbar (konzept.md §6, „Export")."""

    EN_DE = "en_de"
    DE_EN = "de_en"
    CLOZE = "cloze"


class CefrLevel(StrEnum):
    """Sprachniveau nach dem Gemeinsamen europäischen Referenzrahmen (GER), wie es der
    Nutzer beim Anlegen des Profils angibt (konzept.md, „Bewusst offen", „Woher der Nutzer
    seinen Grundwortschatz bekommt").

    Bezeichner bewusst `CefrLevel`/`cefr_level`, nicht `level`: Der Bezeichner `level` ist
    in dokumentation.md §2 bereits für die Gliederungsebene der Navigation vergeben
    (`epub.ChapterReference.level`) — ein zweiter, andersartiger Gebrauch verwechselte
    beides (dokumentation.md §1).

    **`C2` wird bewusst nicht angeboten** — nicht, weil ein C2-Lernender wenig vorzu-
    belegen hätte (das Gegenteil ist der Fall: Er hätte am meisten davon). Zwei echte
    Gründe (Befund leicht, Durchsicht d8d5954): Erstens trägt `wordfreq_en_5000.txt` nur
    5.000 Grundformen — oberhalb von C1 (`PRESET_WORD_COUNT[CefrLevel.C1] == 5000` in
    `pipeline.py`) ist aus der eingefrorenen Liste schlicht nichts mehr auszugeben.
    Zweitens wächst gemessen der Anteil der Grundformen ohne Wörterbucheintrag mit N (2
    von 25 bei A1, 6 bei B1, 9 bei C1) — ein C2-Kontingent träfe auf einen noch größeren
    Anteil ungedeckter Grundformen."""

    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"


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
    Kapitel (technik.md §8). `text` ist bei Project-Gutenberg-Dateien um Vorspann und
    Lizenz gekürzt (`epub._remove_boilerplate`); Inhaltsverzeichnis und Fußnoten bleiben
    enthalten, eine allgemeine Trennung ist mangels `epub:type` nicht gebaut (technik.md
    §8). Er gehört zum eingelesenen Kapitel; ins Profil wandert davon nur, welches Kapitel
    verarbeitet wurde."""

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
    (Regel 1). `wikdict_trans_list` ist der Inhalt der Auswahlliste aus T5 — WikDicts deutsche
    Entsprechungen dieser einen Wörterbuchzeile (Spalte `trans_list`, mit „|" getrennt), aus der
    `translation` (T11) später wählt. Ohne dieses Feld trüge eine Zeile ohne `sense`-Text
    überhaupt keinen Inhalt. Bei einer Wendung ohne Wörterbucheintrag fehlen alle
    `wikdict_`-Werte, und `uncertain` ist gesetzt.

    Identität (Gleichheit und Hash) bilden `lemma`, `wikdict_lexentry`, `wikdict_sense` und
    `wikdict_trans_list` gemeinsam — der Inhalt der Wörterbuchzeile, nicht ein Verweis darauf.
    `wikdict_lexentry` allein genügt nicht: Gemessen an `tools/en-de.sqlite3` fielen unter
    dieser Identität 22,7 % der Zeilen mit `lexentry` weg — `watch` als Substantiv etwa
    dreimal „Wache" mit verschiedenem `wikdict_sense` (Wächter, Wachdienst-Zeitraum,
    Mannschaft der Wache). `wikdict_trans_list` unterscheidet im heutigen Bestand nichts,
    was `wikdict_sense` nicht schon unterscheidet (gemessen über alle 157.801 Zeilen); es
    steht mit in der Identität, damit ein neu bezogenes Wörterbuch das Zusammenfallen nicht
    unbemerkt wieder einführen kann. `translation` und `uncertain` sind Ergebnisfelder, die T11 erst
    während des Durchlaufs füllt, und bleiben deshalb außerhalb von Gleichheit und Hash
    (`compare=False`)."""

    lemma: Lemma
    translation: str | None = field(default=None, compare=False)

    # REGEL (technik.md §4, „Getrennte Datei — nicht mit dem Wörterbuch mischen"): Alle drei
    # wikdict_-Felder bleiben Momentaufnahmen, nie Schlüssel in die Datei — kein rowid, kein
    # anderer Verweis, nur der Zeileninhalt zum Zeitpunkt der Abfrage. Dass wikdict_sense und
    # wikdict_trans_list jetzt an der Identität mitwirken, ändert daran nichts: Verglichen wird
    # weiterhin nur Text gegen Text, nicht gegen die Wörterbuchdatei. wikdict_lexentry allein
    # unterscheidet zwei Zeilen desselben Lemmas nicht (siehe Klassen-Docstring) — erst der
    # volle Zeileninhalt tut das.
    wikdict_sense: str | None = None
    wikdict_trans_list: str | None = None
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
    """Vorkommen einer Grundform in einem Kapitel: Belegsatz, Häufigkeit als Lernvokabel
    (`frequency`, ohne eigennamige Vorkommen) und daneben eigens, wie oft ein Vorkommen
    dieser Grundform ein Eigenname war (`proper_noun_frequency`, mittel 1, Abnahme T17,
    26.08.2026).

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

    # (T17-Nachbesserung, mittel 1, 26.08.2026): Häufigkeit **als Lernvokabel** — gezählt
    # sind nur die nicht-eigennamigen Vorkommen dieser Grundform in diesem Kapitel. Wer
    # nur „Miss" in „Miss Stoner" gebraucht (18 von 19 Vorkommen in `tools/sherlock.epub`
    # Kapitel 9), lernt dabei keine 19 Verwendungen von „miss" als Wort — die angezeigte
    # Anzahl und die Wortobergrenze (`triage.sort_by_frequency`, `WORD_LIMIT`) setzen
    # beide hier auf. Vor dieser Behebung zählte `frequency` alle Vorkommen einschließlich
    # der eigennamigen mit; drei Belege aus dem Abnahmelauf (`miss`, Sherlock K9: 19 statt
    # 1; `lady`, Dorian K17: 30 statt 6; `king`, Sherlock K2: 18 statt 1) zeigten dieselbe
    # falsche Zahl an zwei Stellen — Anzeige und Rangfolge.
    frequency: int

    # REGEL (technik.md §5, „Neuer Befund: der Eigennamenfilter muss pro Vorkommen
    # greifen"): Deshalb eine Zahl hier und kein Kennzeichen am Lemma. 216 Wortformen gelten
    # manchmal als Eigenname und kommen daneben gewöhnlich vor; wer pro Grundform filtert,
    # verliert `red`, `orange` und `street` ganz aus der Triage. Lernvokabel bleibt, was
    # `proper_noun_frequency / (proper_noun_frequency + frequency) <
    # extraction._PROPER_NOUN_RATIO_THRESHOLD` erfüllt (0,90, T17-Nachbesserung
    # 25.08.2026) — das frühere strikte Kleiner-Zeichen (mindestens ein
    # nicht-eigennamiges Vorkommen genügte) ließ Titelfiguren wie „Dorian" durch, deren
    # Grundform fast, aber nicht ganz nur als Name auftritt.
    #
    # (T17-Nachbesserung, mittel 1, 26.08.2026): Die Formel steht bewusst weiter in
    # `frequency` und `proper_noun_frequency` statt in den lokalen Zählgrößen aus
    # `extraction.extract_vocabulary`, die die Entscheidung tatsächlich treffen — beide
    # Felder tragen nach außen genau diese Bedeutung, und `frequency` ist seit dieser
    # Behebung schon um die eigennamigen Vorkommen bereinigt, nicht mehr die Summe mit
    # `proper_noun_frequency`.
    proper_noun_frequency: int


@dataclass(frozen=True)
class ProperNounEntry:
    """Ein Eigenname aus der Liste „Figuren & Orte" (bauplan-phase2.md AP 8; konzept.md
    §6, „Export"; technik.md §7, „Die Liste »Figuren & Orte« ist Phase 2"):
    Oberflächenform und Häufigkeit eines von spaCy erkannten Entitätsvorkommens (PERSON,
    GPE, LOC oder FAC), nie über die Grundform (technik.md §5, offener Punkt
    „Über-Lemmatisierung von Eigennamen") — „Holmes" bliebe sonst „holme".

    Ein Eintrag je Kapitel und Oberflächenform, wie bei `Occurrence`: dasselbe „Holmes"
    zählt in Kapitel 2 anders als in Kapitel 9. `book` und `chapter_number` statt eines
    vollständigen `Chapter`, aus demselben Grund wie bei `Occurrence` — ins Ergebnis
    wandert nur, welches Kapitel verarbeitet wurde.

    `ent_type` ist spaCys `ent.label_` und bleibt deshalb unübersetzt (dokumentation.md
    §1) — wie `Lemma.pos` bei `token.pos_`. Diese Klasse behauptet nichts über eine
    Anzeigegruppe; `printout` übersetzt daraus die beiden deutschen Gruppen „Figuren" und
    „Orte" (technik.md §7, „Die Importregel": das Zusammenstellen des gedruckten Anhangs
    liegt bei `printout`, nicht hier)."""

    book: Book
    chapter_number: int
    text: str
    ent_type: str
    frequency: int


@dataclass(frozen=True)
class Event:
    """Ein Eintrag im Verlauf: Diese Bedeutung wurde zu diesem Zeitpunkt aus dieser Herkunft
    so eingestuft.

    Ereignisse werden angehängt, nie geändert. Der Kenntnisstand ist das jüngste Ereignis je
    Bedeutung (technik.md §4, „Kernentscheidung: Ereignisfolge statt überschreibbarem
    Zustand"). `book` und `chapter_number` statt eines vollständigen `Chapter`, aus
    demselben Grund wie bei `Occurrence`. `timestamp` ist zeitzonenbehaftet (UTC) — der
    Kenntnisstand vergleicht nach dem jüngsten Ereignis, und dafür brauchen alle Ereignisse
    dieselbe Zeitbasis.

    `book` und `chapter_number` sind `None` bei `Origin.PRESET`: Eine Vorbelegung des
    Grundwortschatzes (konzept.md, „Bewusst offen", „Woher der Nutzer seinen
    Grundwortschatz bekommt") gehört zu keinem Buch. Beide sind gemeinsam gesetzt oder
    gemeinsam `None` — nie nur eines von beiden, `profile.record_event` weist die
    gemischte Kombination zurück (Regel 13). Wer `book`/`chapter_number` liest, ohne den
    `None`-Fall zu behandeln, verliert Vorbelegungs-Ereignisse still aus jeder Auswertung,
    die nach Buch filtert oder gruppiert."""

    sense: Sense
    knowledge_state: KnowledgeState
    origin: Origin
    timestamp: datetime
    book: Book | None
    chapter_number: int | None


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
