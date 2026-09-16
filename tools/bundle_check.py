#!/usr/bin/env python3
"""Bündeltest: Skaliert das Bündeln mehrerer Bedeutungsurteile in einer Modellanfrage?

Hintergrund
-----------
technik.md §3, „Beurteilen statt erzeugen" hat gemessen: 16 Urteile in einer einzigen
Anfrage brauchen 12 Sekunden. Ob das auch für 32 und 64 gilt, ist offen (technik.md §3,
„Offene Punkte", „Skaliert das Bündeln beim Modell?") und sperrte unter Entscheidung 10
die Teilaufgabe **T11**: Ohne die Zahl müsste T11 raten, ob es je Wort einzeln
oder gebündelt beim Modell nachfragt. Dieses Skript liefert die Zahl.

Zweiter Zweck derselben Messung: `tools/sense_check.py` ist gesättigt (vier von fünf
Modellen 11/11 bei Einzelfragen) und trennt die Modelle nicht mehr. Unter Bündellast ist
das anders zu erwarten.

Verfahren
---------
1. Buchtext mit `tools/ambiguity_check.py`s `split_chapters` in Kapitel zerlegen (dieselbe
   Kapitelgrenze, derselbe Gutenberg-Schnitt — nicht abgeschrieben, sondern eingebunden,
   wie `tools/nlp_check.py` es mit seinen Nachbarskripten vormacht)
2. Je Kapitel `libreverbum.extraction.extract_vocabulary` aufrufen und über alle Kapitel
   je Grundform und Wortart zusammenzählen — Häufigkeit summiert, Wortform und Belegsatz
   vom ersten Vorkommen im Buch
3. Je Grundform `libreverbum.dictionary.candidates` aufrufen; nur Grundformen mit mehr als
   einer Bedeutung sind ein Fall für diesen Test — Eindeutiges hat nichts zu bündeln
4. **Stichprobe**: die ersten 64 dieser mehrdeutigen Grundformen, nach Häufigkeit im Buch
   absteigend sortiert, bei Gleichstand nach Text und Wortart. Häufigkeitssortierung statt
   einer zufälligen Auswahl, damit dieselbe Stichprobe ohne gespeicherten Zufallskern aus
   jedem Aufruf erneut entsteht — und weil sie die Wörter zuerst zeigt, die im Betrieb auch
   zuerst gebündelt würden (häufige Wörter füllen die Triage). Dieselben 64 Wörter, in
   derselben Reihenfolge, für jedes Modell und jede Bündelgröße — sonst sind die Zahlen
   nicht vergleichbar
5. Je Modell ein Wegwerf-Aufruf zum Warmladen, dann das Kontextfenster (`context_length`)
   des geladenen Modells abfragen. Je Bündelgröße (Vorgabe 1, 8, 16, 32, 64) die 64 Wörter
   in Blöcke dieser Größe teilen und blockweise anfragen: N Wörter, je mit Belegsatz und
   nummerierter Bedeutungsliste samt Ausweichantwort 0 „keine der vorgelegten Bedeutungen
   passt" (technik.md §3, offener Punkt „Ausweichantwort «keine passt»"). Antwortform per
   JSON-Schema erzwungen: eine Liste von `{"index": ..., "word": ..., "choice": ...}` —
   `word` echot das vorgelegte Wort zurück, das ist die einzige verlässliche Prüfung gegen
   eine verrutschte Zuordnung, wenn das Modell ein Wort überspringt und danach fortlaufend
   weiternummeriert. Größe 1 läuft zuerst und ist die Grundlinie, gegen die die größeren
   Bündel verglichen werden
6. Je Modell × Größe auswerten: Zeit je Anfrage und je Wort — getrennt für erfolgreiche und
   gescheiterte Blöcke, damit ein schneller Fehlschlag keinen Mittelwert verfälscht —,
   Vollständigkeit (fehlende, doppelte, unbekannte `index`, formfehlerhafte Objekte),
   Zuordnungsfehler (`word` passt nicht zu `index`), Gültigkeit (`choice` außerhalb der
   vorgelegten Liste), Übereinstimmung mit der Grundlinie, Häufigkeit der Ausweichantwort,
   Abbrüche, `prompt_tokens` und `finish_reason` (Kontextfenster-Kürzung wird sonst als
   Modellversagen fehlgedeutet), sowie Rückfälle ohne `response_format`

Verfahren und seine Grenzen
---------------------------
Wie `tools/ambiguity_check.py` braucht dieses Skript die **Projektumgebung**: spaCy mit
`en_core_web_md` und den Kern `libreverbum` selbst (`extraction`, `dictionary`) — gemessen
wird, was T3 und T5 tatsächlich liefern, nicht eine nachgebaute Näherung. Das Wörterbuch
wird wie dort auf eine Kopie im temporären Verzeichnis indiziert; die Datei des Nutzers
bleibt unangetastet.

Der Modellserver steht unter `192.168.2.129:11434`, nicht `localhost` — die automatische
Suche aus `sense_check.py` fände ihn nicht, deshalb hier fest als Vorgabe statt Suche.

Aufruf
------
    python tools/bundle_check.py sherlock.txt
    python tools/bundle_check.py sherlock.txt --model granite4.1:8b --model gemma4:e4b
    python tools/bundle_check.py sherlock.txt --words 32 --sizes 1,8,16,32
    python tools/bundle_check.py sherlock.txt --url http://127.0.0.1:11434 --timeout 600
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.language import Language

HERE = os.path.dirname(os.path.abspath(__file__))
# tools/ selbst auf den Suchpfad, um ambiguity_check.py als Nachbarskript einzubinden
# (dieselbe Kapitelzerlegung, nicht zweimal geschrieben — wie nlp_check.py es mit
# coverage_check.py und mwe_check.py vormacht), danach die Projektwurzel für den Kern,
# genau wie ambiguity_check.py es selbst für sich tut.
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import ambiguity_check  # noqa: E402

from libreverbum import dictionary, extraction  # noqa: E402
from libreverbum.entities import Book, Chapter, Lemma, Sense  # noqa: E402

DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

# Nicht localhost (siehe Moduldocstring, „Verfahren und seine Grenzen").
DEFAULT_URL = "http://192.168.2.129:11434"

# Vorgabe aus dem Auftrag: genau diese drei, per --model mehrfach überschreibbar.
DEFAULT_MODELS = ("granite4.1:8b", "gemma4:e4b", "qwen3.5:9b")

DEFAULT_WORD_COUNT = 64
DEFAULT_SIZES = (1, 8, 16, 32, 64)

# Großzügig, weil ein Bündel aus 64 Wörtern deutlich länger braucht als eines aus 16
# (technik.md §3, „12 Sekunden für alle 16") — und weil diese Zahl gerade erst gemessen
# werden soll, nicht schon feststeht.
DEFAULT_TIMEOUT = 300

# Auftrag, Befund 1: grobe, bewusst konservative Schätzung der Promptgröße vor dem Senden
# — der Prompt ist englischer Text, rund 4 Zeichen je Token. Ganzzahlige Aufrundung statt
# Abrundung, damit die Schätzung eher zu groß als zu klein ausfällt: eine Unterschätzung
# würde eine tatsächliche Kürzung gerade verdecken, die diese Schätzung aufdecken soll.
CHARS_PER_TOKEN = 4

# Auftrag, Befund 1: Schwelle für die zweite, von der Fenstergröße unabhängige Erkennung.
# Ein ungekürzter Prompt liegt in `prompt_tokens` nahe an der Schätzung oder leicht
# darüber (Chat-Vorlage kommt hinzu); eine stille Kürzung reißt den Wert auf einen Bruchteil
# davon (gemessen: Verhältnis 0,23 bis 0,41 bei Kürzung gegen rund 1,0 bis 1,02 ohne). 0,6
# liegt deutlich zwischen beiden und lässt der ungenauen Zeichen-Näherung Spielraum.
TOKEN_MISMATCH_RATIO = 0.6

# Denkschritte mancher Modelle (Qwen u. a.) vor der eigentlichen Antwort — wie in
# sense_check.py.
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S | re.I)

# Antwortform: eine Liste von Objekten. `index` gibt die Position des Wortes in dieser
# Anfrage zurück; er allein erkennt nur Umsortierung oder eine ehrliche Auslassung mit
# Lücke in der Nummerierung — **nicht** den Regelfall, dass das Modell ein Wort
# überspringt und danach fortlaufend weiternummeriert (dann bleiben alle index-Werte im
# gültigen Bereich, nur die Zuordnung verrutscht). Die echte Prüfung dagegen ist `word`:
# das zurückgeechote Wort wird gegen `chunk[index-1]` abgeglichen (Auftrag, Befund 4).
# `choice` ist die Nummer der gewählten Bedeutung oder 0 für die Ausweichantwort. Bewusst
# ohne Schranken für `index`/`choice` im Schema: Die gültige Spanne ist je Wort
# verschieden (Zahl der Bedeutungen), und Vollständigkeit/Gültigkeit sind gerade die
# Kennzahlen, die gemessen werden sollen — ein zu enges Schema verhinderte genau die
# Fehler, die gezählt werden.
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "bundle_choices",
        "strict": True,
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "word": {"type": "string"},
                    "choice": {"type": "integer"},
                },
                "required": ["index", "word", "choice"],
                "additionalProperties": False,
            },
        },
    },
}


@dataclass
class _MergedOccurrence:
    """Ein Vorkommen einer Grundform, über alle Kapitel des Buches zusammengezählt."""

    lemma: Lemma
    word_form: str
    example_sentence: str
    frequency: int


@dataclass(frozen=True)
class WordCase:
    """Ein Fall für die Messung: eine mehrdeutige Grundform samt Auswahlliste."""

    lemma: Lemma
    word_form: str
    example_sentence: str
    frequency: int
    senses: list[Sense]


@dataclass
class Result:
    """Auswertung eines Durchlaufs für ein Modell bei einer Bündelgröße."""

    model: str
    size: int
    word_count: int
    # Zeit und Anfragezahl getrennt für erfolgreiche und gescheiterte Blöcke (Befund 2):
    # ein schneller Fehlschlag darf `s/Anfr.`/`s/Wort` nicht wie ein gutes Ergebnis
    # aussehen lassen, eine Zeitüberschreitung nicht wie ein echter Messwert.
    ok_requests: int = 0
    ok_time: float = 0.0
    aborted: int = 0
    failed_time: float = 0.0
    answered: int = 0
    missing: int = 0
    duplicate: int = 0
    unknown: int = 0
    malformed: int = 0
    word_mismatch: int = 0
    invalid: int = 0
    none_fits: int = 0
    agree: int = 0
    compared: int = 0
    schema_dropped: int = 0
    finish_length: int = 0
    max_prompt_tokens: int | None = None
    truncated: int = 0
    # Auftrag, Befund 1: `prompt_tokens >= window` schlägt bei Ollama nie an, weil der
    # Server einen gekürzten Prompt still kürzt und den gekürzten Wert meldet. Zwei
    # unabhängige Erkennungen treten an die Stelle: die Schätzung der Promptgröße vor dem
    # Senden gegen das Fenster (`exceeds_window`) und der Abgleich der Schätzung gegen die
    # tatsächlich gemeldeten `prompt_tokens` danach (`token_mismatch`) — letzteres kommt
    # ohne Kenntnis der Fenstergröße aus.
    max_estimated_tokens: int = 0
    exceeds_window: int = 0
    token_mismatch: int = 0
    window_unknown: bool = False
    # Auftrag, „Ausreißer bei den Anfragezeiten sind unsichtbar": die längste einzelne
    # erfolgreiche Anfrage, damit ein Mittelwert aus wenigen, sehr verschiedenen Werten
    # nicht als Messwert durchgeht.
    max_request_time: float = 0.0
    # Auftrag, „Spalte Größe, zweiter Anlauf": die kürzeste tatsächliche Blocklänge. `min`
    # statt `max` deckt sowohl den Fall ab, dass die Stichprobe insgesamt kleiner ist als
    # die Bündelgröße, als auch den Regelfall voller Block plus kürzerer letzter Block —
    # bei `max` bleibt Letzterer unsichtbar, weil der volle erste Block `max == size` ergibt.
    min_block_length: int = 0
    choices: dict[int, int | None] = field(default_factory=dict)


# --------------------------------------------------------------------------- Wortliste


def collect_words(chapters: list[tuple[str, str]], nlp: Language) -> list[_MergedOccurrence]:
    """Sammelt je Grundform und Wortart ein `_MergedOccurrence`, über alle Kapitel des
    Buches summiert (Häufigkeit) beziehungsweise vom ersten Vorkommen (Wortform,
    Belegsatz) — dieselben Aufrufe wie in ambiguity_check.py, hier über das ganze Buch
    statt je Kapitel ausgewertet."""
    book = Book(title="Bündeltest", author="")
    merged: dict[tuple[str, str], _MergedOccurrence] = {}
    for number, (title, text) in enumerate(chapters, 1):
        chapter = Chapter(book=book, number=number, title=title, text=text)
        for occurrence in extraction.extract_vocabulary(chapter, nlp).occurrences:
            key = (occurrence.lemma.text, occurrence.lemma.pos)
            existing = merged.get(key)
            if existing is None:
                merged[key] = _MergedOccurrence(
                    lemma=occurrence.lemma,
                    word_form=occurrence.word_form,
                    example_sentence=occurrence.example_sentence,
                    frequency=occurrence.frequency,
                )
            else:
                existing.frequency += occurrence.frequency
    return list(merged.values())


def ambiguous_sample(
    merged: list[_MergedOccurrence], db_copy: pathlib.Path, count: int
) -> list[WordCase]:
    """Die `count` häufigsten mehrdeutigen Grundformen (mehr als eine Bedeutung), nach
    Häufigkeit absteigend, bei Gleichstand nach Text und Wortart — deterministisch
    (Moduldocstring, Schritt 4)."""
    cases: list[WordCase] = []
    for occurrence in merged:
        senses = dictionary.candidates(db_copy, occurrence.lemma)
        if len(senses) > 1:
            cases.append(
                WordCase(
                    lemma=occurrence.lemma,
                    word_form=occurrence.word_form,
                    example_sentence=occurrence.example_sentence,
                    frequency=occurrence.frequency,
                    senses=senses,
                )
            )
    cases.sort(key=lambda c: (-c.frequency, c.lemma.text, c.lemma.pos))
    return cases[:count]


# --------------------------------------------------------------------------- Modellaufruf


class ReasoningEffortRejected(RuntimeError):
    """Der Server lehnt `reasoning_effort` ab. Ein Lauf ohne dieses Feld misst laut
    technik.md §3 bis zum 28-fachen und beantwortet damit eine andere Frage als die
    Bündelmessung — er darf nicht stillschweigend als Messwert durchgehen (Regel 7 und
    Regel 13, CLAUDE.md; Auftrag, Befund 3)."""


def build_prompt(chunk: list[WordCase]) -> str:
    """Baut die Anfrage für einen Block: `chunk` Wörter, je mit Belegsatz und nummerierter
    Bedeutungsliste samt Ausweichantwort 0 (technik.md §3, offener Punkt „Ausweichantwort
    «keine passt»"). Die Nummerierung beginnt in jeder Anfrage neu bei 1 — dasselbe `index`,
    das die Antwort zurückgibt."""
    blocks = []
    for position, word in enumerate(chunk, 1):
        options = [
            f"  {n}. {dictionary.label(sense)} → {sense.wikdict_trans_list}"
            for n, sense in enumerate(word.senses, 1)
        ]
        options.append("  0. none of the above meanings fits")
        blocks.append(
            f'{position}. word "{word.word_form}" in: "{word.example_sentence}"\n'
            + "\n".join(options)
        )
    return (
        "You are helping a German learner of English build vocabulary cards.\n"
        f"Below are {len(chunk)} numbered words, each with its sentence and a numbered "
        "list of possible meanings. For each word, choose the number of the meaning it "
        "has in its sentence. If none of the listed meanings fits, choose 0.\n\n"
        + "\n\n".join(blocks)
        + "\n\nAnswer with JSON only: a list of objects "
        '{"index": <word number above>, "word": <the exact word from that line, echoed '
        'back>, "choice": <meaning number>}, one per word.'
    )


def estimate_prompt_tokens(prompt: str) -> int:
    """Grobe, konservativ aufgerundete Schätzung der Promptgröße vor dem Senden — rund
    `CHARS_PER_TOKEN` Zeichen je Token (Auftrag, Befund 1). Nicht exakt, aber genug, um
    eine stille Kürzung durch den Server zu erkennen, die `usage.prompt_tokens` sonst
    verschleiert."""
    return -(-len(prompt) // CHARS_PER_TOKEN)


@dataclass
class CallOutcome:
    """Ergebnis eines einzelnen Modellaufrufs für einen Block."""

    parsed: list | None  # type: ignore[type-arg]
    raw: str
    duration: float
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    # Befund 3: response_format allein durfte wegfallen und weiterlaufen — anders als
    # reasoning_effort, dessen Wegfall zum Abbruch führt (ReasoningEffortRejected).
    schema_dropped: bool = False


def call_model(url: str, model: str, prompt: str, chunk_length: int, timeout: int) -> CallOutcome:
    """Fragt das Modell nach einem Block.

    Rückfall bei HTTP 400/422 wie in sense_check.py, aber enger gefasst (Auftrag,
    Befund 3): Zuerst nur `response_format` weglassen und erneut versuchen — das fängt
    Server, die ein Array als Wurzelschema ablehnen. Lehnt der Server auch das ab, liegt
    es an `reasoning_effort`; dessen Wegfall würde eine andere Frage messen als die
    Bündelmessung, deshalb wird dann mit `ReasoningEffortRejected` abgebrochen statt
    lautlos weiterzulaufen.
    """
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        # REGEL (CLAUDE.md, „Bei jedem Modellaufruf reasoning_effort"): bei jedem Modellaufruf.
        "reasoning_effort": "none",
        # Reserve für ein Antwortobjekt je Wort — großzügig, damit ein Bündel aus 64
        # Wörtern nicht am Tokenlimit abgeschnitten wird.
        "max_tokens": 64 + 40 * chunk_length,
        "response_format": RESPONSE_FORMAT,
    }

    def send(payload: dict) -> dict:  # type: ignore[type-arg]
        request = urllib.request.Request(
            f"{url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as r:
            return json.load(r)  # type: ignore[no-any-return]

    start = time.perf_counter()
    schema_dropped = False
    try:
        response = send(body)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):
            reduced = {k: v for k, v in body.items() if k != "response_format"}
            try:
                response = send(reduced)
                schema_dropped = True
            except urllib.error.HTTPError as e2:
                if e2.code in (400, 422):
                    raise ReasoningEffortRejected(
                        f"Server unter {url} lehnt reasoning_effort ab (HTTP {e2.code} "
                        f"auch ohne response_format) — Modell {model!r}."
                    ) from e2
                body_text = e2.read()[:200].decode("utf-8", "replace")
                return CallOutcome(
                    None, f"HTTP {e2.code}: {body_text}", time.perf_counter() - start
                )
            except Exception as e2:
                return CallOutcome(
                    None,
                    f"auch ohne response_format gescheitert: {e2}",
                    time.perf_counter() - start,
                )
        else:
            body_text = e.read()[:200].decode("utf-8", "replace")
            return CallOutcome(None, f"HTTP {e.code}: {body_text}", time.perf_counter() - start)
    except Exception as e:
        return CallOutcome(None, f"Fehler: {e}", time.perf_counter() - start)
    duration = time.perf_counter() - start

    usage = response.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    choice0 = response["choices"][0]
    finish_reason = choice0.get("finish_reason")
    message = choice0["message"]
    text = (message.get("content") or "").strip()
    text = THINK_BLOCK.sub("", text).strip()
    if not text and message.get("reasoning_content"):
        text = str(message["reasoning_content"]).strip()

    def outcome(parsed: list | None) -> CallOutcome:  # type: ignore[type-arg]
        return CallOutcome(
            parsed, text, duration, finish_reason, prompt_tokens, completion_tokens, schema_dropped
        )

    try:
        parsed = json.loads(text)
    except Exception:
        brackets = re.search(r"\[.*\]", text, re.S)
        if brackets is None:
            return outcome(None)
        try:
            parsed = json.loads(brackets.group())
        except Exception:
            return outcome(None)
    if not isinstance(parsed, list):
        return outcome(None)
    return outcome(parsed)


def context_length(url: str, model: str) -> int | None:
    """Fenstergröße (`context_length`) des geladenen Modells über `GET /api/ps` — Ollama
    fährt Modelle serverseitig mit einer festen Fenstergröße, unabhängig davon, was das
    Modell selbst könnte (Auftrag, Befund 1). `None`, wenn sie sich nicht ermitteln lässt
    — dann wird das gesagt, statt einen Wert zu erfinden."""
    try:
        with urllib.request.urlopen(f"{url}/api/ps", timeout=5) as r:
            data = json.load(r)
    except Exception:
        return None
    for entry in data.get("models", []):
        if entry.get("model") == model or entry.get("name") == model:
            value = entry.get("context_length")
            if isinstance(value, int):
                return value
    return None


def run_size(
    url: str,
    model: str,
    words: list[WordCase],
    size: int,
    timeout: int,
    baseline: dict[int, int | None] | None,
    window: int | None,
) -> Result:
    """Fragt alle `words` in Blöcken von `size` ab und wertet je Wort aus — Übereinstimmung
    gegen `baseline` (die Wahl von Größe 1 je Wort), falls vorhanden. `window` ist die
    Fenstergröße des Modells (Befund 1), zur Erkennung eines gekürzten Prompts; `None`,
    wenn sie sich nicht ermitteln ließ — dann bleibt nur die von der Fenstergröße
    unabhängige Erkennung über `TOKEN_MISMATCH_RATIO` übrig, und die Zeile sagt das
    (Regel 13, CLAUDE.md; `Result.window_unknown`)."""
    result = Result(model=model, size=size, word_count=len(words), window_unknown=window is None)
    for start in range(0, len(words), size):
        chunk = words[start : start + size]
        result.min_block_length = (
            len(chunk) if result.min_block_length == 0 else min(result.min_block_length, len(chunk))
        )
        prompt = build_prompt(chunk)
        request_no = result.ok_requests + result.aborted + 1

        # Auftrag, Befund 1: Erkennung vor dem Senden. `usage.prompt_tokens` verschleiert
        # eine Kürzung (Ollama meldet den gekürzten, nicht den gesendeten Wert) — die
        # Schätzung gegen das Fenster schlägt deshalb an, wo die alte Prüfung unten
        # (`prompt_tokens >= window`) es nie könnte.
        estimated_tokens = estimate_prompt_tokens(prompt)
        result.max_estimated_tokens = max(result.max_estimated_tokens, estimated_tokens)
        if window is not None and estimated_tokens >= window:
            result.exceeds_window += 1
            print(
                f"    Block {request_no}: WARNUNG — Prompt geschätzt {estimated_tokens} Token "
                f"gegen Fenster {window}, vermutlich vom Server gekürzt — Antwort unbrauchbar."
            )

        outcome = call_model(url, model, prompt, len(chunk), timeout)

        if outcome.prompt_tokens is not None:
            result.max_prompt_tokens = max(result.max_prompt_tokens or 0, outcome.prompt_tokens)
            if window is not None and outcome.prompt_tokens >= window:
                result.truncated += 1
                print(
                    f"    Block {request_no}: WARNUNG — prompt_tokens {outcome.prompt_tokens} "
                    f"erreicht die Fenstergröße {window}, Prompt vermutlich vorne gekürzt."
                )
            # Auftrag, Befund 1: zweite, von der Fenstergröße unabhängige Erkennung — liegt
            # der gemeldete Wert deutlich unter der Schätzung, wurde gekürzt, ganz gleich,
            # ob die Fenstergröße bekannt ist.
            if outcome.prompt_tokens < estimated_tokens * TOKEN_MISMATCH_RATIO:
                result.token_mismatch += 1
                print(
                    f"    Block {request_no}: WARNUNG — prompt_tokens {outcome.prompt_tokens} "
                    f"liegt deutlich unter der Schätzung {estimated_tokens}, vermutlich vom "
                    "Server gekürzt — Antwort unbrauchbar."
                )

        if outcome.parsed is None:
            result.aborted += 1
            result.failed_time += outcome.duration
            result.missing += len(chunk)
            print(f"    Block {request_no} ({len(chunk)} Wörter): ABBRUCH — {outcome.raw[:160]!r}")
            continue

        result.ok_requests += 1
        result.ok_time += outcome.duration
        result.max_request_time = max(result.max_request_time, outcome.duration)
        if outcome.schema_dropped:
            result.schema_dropped += 1
        if outcome.finish_reason == "length":
            result.finish_length += 1

        seen: dict[int, int] = {}
        block_duplicate = block_unknown = block_malformed = block_mismatch = 0
        for item in outcome.parsed:
            try:
                index = int(item["index"])
                choice = int(item["choice"])
                word_echo = str(item["word"])
            except (KeyError, TypeError, ValueError):
                # Befund 5: formfehlerhafte Objekte sind kein "fehlend" (Modell hat
                # nicht geantwortet), sondern ein eigener Fall — sonst nicht von einem
                # echten Ausbleiben zu unterscheiden.
                block_malformed += 1
                continue
            if not (1 <= index <= len(chunk)):
                block_unknown += 1
                continue
            expected_word = chunk[index - 1].word_form
            if word_echo.strip().lower() != expected_word.strip().lower():
                # Befund 4: die eigentliche Prüfung gegen eine verrutschte Zuordnung.
                block_mismatch += 1
                continue
            if index in seen:
                block_duplicate += 1
                continue
            seen[index] = choice
        if block_malformed:
            print(
                f"    Block {request_no}: {block_malformed} formfehlerhafte Objekte — "
                f"Rohantwort: {outcome.raw[:300]!r}"
            )
        result.malformed += block_malformed
        result.word_mismatch += block_mismatch
        result.duplicate += block_duplicate
        result.unknown += block_unknown
        result.answered += len(seen)
        result.missing += len(chunk) - len(seen)

        for index, choice in seen.items():
            word = chunk[index - 1]
            global_index = start + index - 1
            if not (0 <= choice <= len(word.senses)):
                result.invalid += 1
                result.choices[global_index] = None
                continue
            result.choices[global_index] = choice
            if choice == 0:
                result.none_fits += 1
            if baseline is not None:
                base_choice = baseline.get(global_index)
                if base_choice is not None:
                    result.compared += 1
                    if base_choice == choice:
                        result.agree += 1

        tokens_note = (
            f", prompt_tokens={outcome.prompt_tokens}" if outcome.prompt_tokens is not None else ""
        )
        schema_note = " [ohne response_format]" if outcome.schema_dropped else ""
        print(
            f"    Block {request_no} ({len(chunk)} Wörter) in {outcome.duration:6.2f} s, "
            f"{len(seen)}/{len(chunk)} Antworten{tokens_note}{schema_note}"
        )
    return result


def _notes(r: Result) -> str:
    """Freitext-Hinweise, die eine Zeile als unbrauchbar oder als Sonderfall kenntlich
    machen (Befunde 1, 3, 7; Auftrag Runde 3, Befund 1) — Zahlen allein in Spalten wären
    hier zu leicht zu übersehen. `UNBRAUCHBAR` markiert wörtlich die Fälle, in denen der
    Prompt vermutlich vom Server gekürzt wurde."""
    parts = []
    if r.window_unknown:
        parts.append("FENSTER UNBEKANNT")
    if r.exceeds_window:
        parts.append(f"UNBRAUCHBAR (Prompt geschätzt über Fenster):{r.exceeds_window}")
    if r.token_mismatch:
        parts.append(f"UNBRAUCHBAR (prompt_tokens ≪ Schätzung):{r.token_mismatch}")
    if r.truncated:
        parts.append(f"GEKÜRZT:{r.truncated}")
    if r.finish_length:
        parts.append(f"FR=Länge:{r.finish_length}")
    if r.schema_dropped:
        parts.append(f"Schema-Rückfall:{r.schema_dropped}")
    if r.ok_requests == 1:
        parts.append("n=1")
    return " ".join(parts) if parts else "-"


def print_table(results: list[Result]) -> None:
    header = (
        f"{'Modell':<14} {'Größe':>9} {'Anfr.':>5} {'s/Anfr.':>8} {'max s':>7} {'s/Wort':>7} "
        f"{'gesch.Tok':>9} {'p.Tok':>6} {'fehlend':>7} {'doppelt':>7} {'unbek.':>6} "
        f"{'malform.':>8} {'Wort≠':>6} {'ungült.':>7} {'keine':>5} {'Übereinst.':>11} "
        f"{'Abbr.':>5}  Hinweise"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        # Befund 2: Zeit/Mittelwerte nur aus erfolgreichen Blöcken, über die tatsächlich
        # beantworteten Wörter — nicht über die Stichprobengröße. Auftrag Runde 3, „s/Anfr.
        # und s/Wort zeigen 0.00, wenn der Nenner 0 ist": bei leerem Nenner „-" wie bei
        # `p.Tok` und `Übereinst.`, statt einer irreführenden Null.
        per_request = f"{r.ok_time / r.ok_requests:.2f}" if r.ok_requests else "-"
        per_word = f"{r.ok_time / r.answered:.2f}" if r.answered else "-"
        # Auftrag Runde 3, „Ausreißer bei den Anfragezeiten sind unsichtbar": die längste
        # einzelne erfolgreiche Anfrage neben dem Mittelwert.
        max_request = f"{r.max_request_time:.2f}" if r.ok_requests else "-"
        agreement = f"{r.agree}/{r.compared}" if r.compared else "-"
        prompt_tok = str(r.max_prompt_tokens) if r.max_prompt_tokens is not None else "-"
        est_tok = str(r.max_estimated_tokens) if r.max_estimated_tokens else "-"
        # Befund 8, korrigiert (Auftrag Runde 3, „Spalte Größe, zweiter Anlauf"): `min`
        # statt `max` — sonst verdeckt ein voller erster Block den kürzeren letzten.
        size_label = (
            str(r.size) if r.min_block_length == r.size else f"{r.size}({r.min_block_length})"
        )
        total_requests = r.ok_requests + r.aborted
        print(
            f"{r.model:<14} {size_label:>9} {total_requests:>5} {per_request:>8} "
            f"{max_request:>7} {per_word:>7} {est_tok:>9} {prompt_tok:>6} {r.missing:>7} "
            f"{r.duplicate:>7} {r.unknown:>6} {r.malformed:>8} {r.word_mismatch:>6} "
            f"{r.invalid:>7} {r.none_fits:>5} {agreement:>11} {r.aborted:>5}  {_notes(r)}"
        )


def server_models(url: str) -> list[str] | None:
    """Modellnamen, die der Server anbietet (`GET /v1/models`). `None`, wenn der Server
    nicht erreichbar ist (Regel 13, CLAUDE.md: Ohne diese Prüfung liefe ein unerreichbarer
    Server erst nach etlichen Zeitüberschreitungen sichtbar auf). Der Abgleich gegen die
    angeforderten Modellnamen gehört Aufruferseite — ein fehlendes Modell ergibt sonst pro
    Anfrage HTTP 404, fällt nicht in den 400/422-Rückfall, und das Skript arbeitet trotzdem
    alle Größen erfolglos durch (Auftrag, Befund 6)."""
    try:
        with urllib.request.urlopen(f"{url}/v1/models", timeout=5) as r:
            data = json.load(r)
        return [m.get("id", "") for m in data.get("data", [])]
    except Exception:
        return None


# --------------------------------------------------------------------------------- Ablauf


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Misst, ob das Bündeln mehrerer Bedeutungsurteile in einer Anfrage skaliert.",
        epilog="Beantwortet die zweite der beiden offenen Zahlen zu Entscheidung 10.",
    )
    p.add_argument("text", help="Buchtext als Textdatei")
    p.add_argument("--db", default=DEFAULT_DB, help="Pfad zur WikDict-Datenbank")
    p.add_argument("--url", default=DEFAULT_URL, help="Adresse des Modellservers")
    p.add_argument(
        "--model",
        action="append",
        dest="models",
        help="zu prüfendes Modell (mehrfach möglich; ohne Angabe: die drei Vorgabemodelle)",
    )
    p.add_argument(
        "--words", type=int, default=DEFAULT_WORD_COUNT, help="Stichprobengröße (Vorgabe 64)"
    )
    p.add_argument(
        "--sizes",
        default=",".join(str(s) for s in DEFAULT_SIZES),
        help="Bündelgrößen, kommagetrennt (Vorgabe 1,8,16,32,64)",
    )
    p.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, help="Zeitgrenze je Anfrage in Sekunden"
    )
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        print("Mit  python tools/coverage_check.py --fetch-dictionary  herunterladen.")
        return 1

    if not os.path.exists(args.text):
        print(f"Textdatei fehlt: {args.text}", file=sys.stderr)
        return 1

    models = args.models if args.models else list(DEFAULT_MODELS)
    sizes = sorted({int(s) for s in args.sizes.split(",")})

    available = server_models(args.url)
    if available is None:
        print(f"Modellserver unter {args.url} nicht erreichbar.", file=sys.stderr)
        return 1
    missing_models = [m for m in models if m not in available]
    if missing_models:
        print(
            f"Modell(e) nicht auf dem Server geladen: {', '.join(missing_models)}\n"
            f"Verfügbar: {', '.join(available) or '(keine)'}",
            file=sys.stderr,
        )
        return 1

    with open(args.text, encoding="utf-8") as fh:
        chapters = ambiguity_check.split_chapters(fh.read())
    if not chapters:
        print(f"Keine Kapitelüberschriften in {args.text} gefunden.", file=sys.stderr)
        return 1

    print(f"Text: {args.text}   Kapitel: {len(chapters)}")
    print(f"Server: {args.url}   Modelle: {', '.join(models)}")
    print(f"Bündelgrößen: {sizes}   Stichprobengröße: {args.words}")

    with tempfile.TemporaryDirectory() as workspace:
        # Auf einer Kopie, nie auf der Datei des Nutzers (wie ambiguity_check.py).
        db_copy = pathlib.Path(workspace) / "en-de.sqlite3"
        shutil.copyfile(args.db, db_copy)
        dictionary.ensure_index(db_copy)
        print(
            f"Wörterbuch: Kopie von {args.db}, mit Index (technik.md §3, "
            '„Der Engpass ist das Nachschlagen, nicht das Modell")'
        )

        nlp = extraction.load_nlp()
        merged = collect_words(chapters, nlp)
        words = ambiguous_sample(merged, db_copy, args.words)

    if not words:
        print("Keine mehrdeutigen Grundformen im Text gefunden.", file=sys.stderr)
        return 1
    if len(words) < args.words:
        print(
            f"Hinweis: nur {len(words)} mehrdeutige Grundformen gefunden, "
            f"angefordert waren {args.words}."
        )

    print(f"\nStichprobe ({len(words)} Wörter, häufigste zuerst):")
    for word in words[:10]:
        print(
            f"  {word.frequency:>4}×  {word.word_form:<20} ({word.lemma.pos}, "
            f"{len(word.senses)} Bedeutungen)"
        )
    if len(words) > 10:
        print(f"  … und {len(words) - 10} weitere")

    results: list[Result] = []
    try:
        for model in models:
            print(f"\n{'=' * 78}\nModell: {model}\n{'=' * 78}")

            print("  Warmlauf (Ladezeit, zählt nicht in die Messung) ...")
            warmup = call_model(args.url, model, build_prompt(words[:1]), 1, args.timeout)
            if warmup.parsed is None:
                print(f"  Warmlauf gescheitert: {warmup.raw[:160]!r}")

            window = context_length(args.url, model)
            if window is not None:
                print(f"  Kontextfenster (context_length): {window} Token")
            else:
                print("  Kontextfenster (context_length): nicht ermittelbar")

            baseline: dict[int, int | None] | None = None
            for size in sizes:
                print(f"\n-- Bündelgröße {size} --")
                result = run_size(args.url, model, words, size, args.timeout, baseline, window)
                results.append(result)
                if size == 1:
                    baseline = result.choices

            print(f"\nZwischenstand nach Modell {model}:")
            print_table(results)
    except ReasoningEffortRejected as e:
        print(f"\nAbbruch: {e}", file=sys.stderr)
        if results:
            print("\nTeilergebnis bis zum Abbruch:")
            print_table(results)
        return 1

    print(f"\n{'=' * 78}\nÜbersicht\n{'=' * 78}")
    print_table(results)
    print(
        "\nÜbereinstimmung ist gemessen gegen Bündelgröße 1 (Grundlinie); '-' heißt, es lag "
        "keine Grundlinie vor (Größe 1 nicht in --sizes)."
    )
    print(
        "Hinweise: FENSTER UNBEKANNT = context_length nicht ermittelbar, Kürzungserkennung "
        "gegen das Fenster fällt aus; UNBRAUCHBAR (Prompt geschätzt über Fenster) = die vor "
        "dem Senden geschätzte Promptgröße erreichte oder überschritt das Fenster; "
        "UNBRAUCHBAR (prompt_tokens ≪ Schätzung) = die gemeldeten prompt_tokens liegen "
        "deutlich unter der Schätzung, unabhängig von der Fenstergröße; beides heißt: der "
        "Server hat den Prompt vermutlich still gekürzt (Auftrag, Befund 1). GEKÜRZT = "
        "prompt_tokens erreichte die gemeldete Fenstergröße (Rückfallprüfung, schlägt bei "
        "Ollama praktisch nie an, siehe oben); "
        'FR=Länge = finish_reason "length" (Antwort abgeschnitten); '
        "Schema-Rückfall = ohne response_format gemessen; n=1 = Mittelwert aus einer "
        "einzigen Anfrage; max s = längste einzelne erfolgreiche Anfrage."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
