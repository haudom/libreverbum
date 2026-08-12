#!/usr/bin/env python3
"""Lemmatisierungstest: Welche NLP-Bibliothek trägt die Wortschatzextraktion?

Hintergrund
-----------
../technik.md, Abschnitt 2, endet mit der Folgerung: „Die Datenquelle ist nicht der
Engpass — die Lemmatisierung ist es." Welche Bibliothek diese Aufgabe übernimmt, ist in
Abschnitt 1 unter „Noch nicht entschieden" offen geblieben, mit dem Zusatz, die Frage
entscheide sich „am besten an echtem Buchtext". Dieses Skript ist dieser Buchtext.

Es beantwortet zwei weitere offene Punkte gleich mit: die getrennten Phrasal Verbs, die
die Wendungsmessung nur auf „rund 51 %" schätzen konnte, und den Wortart-Vorfilter gegen
sehr lange Auswahllisten aus Abschnitt 3.

Ausnahme von der Regel für dieses Verzeichnis
---------------------------------------------
Die drei Nachbarskripte kommen mit der Standardbibliothek aus. Dieses nicht: Ein
Vergleich von spaCy und Stanza lässt sich nur an den echten Modellen führen, nicht
nachbilden. Installation siehe „Aufruf".

Fünf Teile
----------
1. **Grundformen** — dieselbe Restlücke wie in coverage_check.py, echt statt geschätzt
2. **Reihenfolge** — der ``saw``-Fall und die anderen stillen Fehlschläge (Regel 2)
3. **Eigennamen** — Abnahmekriterium 2, in beiden Fehlerrichtungen
4. **Getrennte Phrasal Verbs** — über die Abhängigkeitsanalyse statt n-Gramm-Abgleich
5. **Kosten** — Ladezeit, Durchsatz, Speicher je Modell

Aufruf
------
    pip install spacy
    python -m spacy download en_core_web_sm
    python -m spacy download en_core_web_md
    pip install stanza
    python -c "import stanza; stanza.download('en')"

    python tools/nlp_check.py buch.txt
    python tools/nlp_check.py buch.txt --models spacy:en_core_web_sm,spacy:en_core_web_md
    python tools/nlp_check.py buch.txt --models stanza:default --limit 0
    python tools/nlp_check.py                       # nur Teil 2 und 5, ohne Buchtext

Erwartet reinen Text (UTF-8); der Lizenz-Vorspann von Project Gutenberg wird
abgeschnitten. Die Wörterbuchdatei wird neben diesem Skript erwartet.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import sys
import time
from typing import Callable, Iterable, Iterator, NamedTuple

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

# Die Nachbarskripte werden eingebunden statt abgeschrieben: gleiche Stichwortliste,
# gleiche Suffix-Heuristik, gleicher Wendungsfilter. Sonst wären die Zahlen hier nicht
# mit technik.md §2 und „Messung: Mehrwortausdrücke" vergleichbar, und genau der
# Vergleich ist der Zweck.
sys.path.insert(0, HERE)
import coverage_check  # noqa: E402
import mwe_check  # noqa: E402

DEFAULT_MODELS = "spacy:en_core_web_sm"
DEFAULT_LIMIT = 25_000

# Lizenzlage, vor der Aufnahme zu prüfen — CLAUDE.md, „Architektur". Angegeben ist, was
# die Projekte selbst nennen; die Modellpakete tragen eigene Lizenzen und sind der
# eigentlich heikle Teil.
LICENSES = {
    "spacy": ("spaCy: MIT · Modelle en_core_web_*: MIT",
              "unkritisch, auch für eine spätere Veröffentlichung"),
    "stanza": ("Stanza: Apache 2.0 · Modelle aus UD-Baumbanken",
               "Baumbank-Lizenzen weichen voneinander ab — vor Aufnahme einzeln prüfen"),
}

# spaCy nennt die Verbpartikel „prt", Stanza folgt Universal Dependencies mit
# „compound:prt". Gemeint ist dasselbe: das „up" in „gave up".
PARTICLE_DEPS = {"prt", "compound:prt"}

# Keine Vokabeln. PUNCT und SPACE fielen ohnehin durch die Wortprüfung, SYM und X nicht
# immer.
SKIPPED_POS = {"PUNCT", "SPACE", "SYM", "X"}

# Ein übersehener Eigenname stünde als Inhaltswort da, nie als Pronomen oder Artikel.
# Ohne diese Einschränkung meldet die Prüfung „I" und „Then" als Namen.
CONTENT_POS = {"NOUN", "PROPN", "ADJ", "VERB"}

# Wie oft ein Wort großgeschrieben stehen muss, damit es als Eigenname gilt. Dieselbe
# Schwelle wie in coverage_check.py — sie dient hier als unabhängiger Vergleichsmaßstab
# gegen die Wortartbestimmung des Modells.
CAPITAL_RATIO = 0.85

# REGEL (technik.md, „Warum die Reihenfolge zwingend ist"): Wortart vor Grundform,
# Grundform vor Nachschlagen. Diese Fälle sind der Testpunkt dazu (dokumentation.md §5).
# Gefährlich sind die Zeilen, deren Wortform selbst im Wörterbuch steht: Dort liefert ein
# Nachschlagen ohne Lemmatisierung keine Fehlermeldung, sondern eine falsche Übersetzung.
ORDER_CASES = [
    ("He saw her standing at the window.", "saw", "see", "VERB"),
    ("He cut the plank in half with a rusty saw.", "saw", "saw", "NOUN"),
    ("He had gone out before dawn.", "gone", "go", "VERB"),
    ("He was running towards the gate.", "running", "run", "VERB"),
    ("They went home before the storm broke.", "went", "go", "VERB"),
    ("He paid the bill and asked for the key.", "paid", "pay", "VERB"),
    ("She heard the mice behind the wall.", "heard", "hear", "VERB"),
    ("She heard the mice behind the wall.", "mice", "mouse", "NOUN"),
    ("The children had already eaten.", "children", "child", "NOUN"),
    ("The geese flew over the frozen pond.", "geese", "goose", "NOUN"),
    ("The banks of the river were steep and wet.", "banks", "bank", "NOUN"),
    ("He left the room without a word.", "left", "leave", "VERB"),
    ("He held the lamp in his left hand.", "left", "left", "ADJ"),
    ("The wound had not been dressed.", "wound", "wound", "NOUN"),
    ("She wound the clock before going to bed.", "wound", "wind", "VERB"),
    ("He had shown her the letter that morning.", "shown", "show", "VERB"),
    ("He carried the lamp into the hall.", "carried", "carry", "VERB"),
    ("A larger house would have suited them better.", "larger", "large", "ADJ"),
]


class Token(NamedTuple):
    """Ein Wort nach der Analyse — das, was beide Bibliotheken gemeinsam liefern."""

    text: str
    lemma: str
    pos: str     # UPOS (NOUN, VERB, PROPN …); spaCy und Stanza stimmen hier überein
    dep: str
    head: int    # satzinterner Index des Kopfes
    index: int   # satzinterner Index dieses Wortes


class Engine(NamedTuple):
    """Ein geladenes Modell samt dem, was seine Auswahl kostet."""

    spec: str
    library: str
    analyze: Callable[[Iterable[str]], Iterator[list[Token]]]
    load_seconds: float
    size_mb: float


# --------------------------------------------------------------------------- Modelle

def directory_size_mb(path: str | None) -> float:
    """Belegter Platz eines Modellverzeichnisses; 0, wenn nicht bestimmbar."""
    if not path or not os.path.isdir(path):
        return 0.0
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total / 1024 / 1024


def build_spacy(model: str) -> tuple[Callable, float]:
    import spacy

    nlp = spacy.load(model)

    def analyze(chunks: Iterable[str]) -> Iterator[list[Token]]:
        for doc in nlp.pipe(chunks):
            for sentence in doc.sents:
                start = sentence.start
                yield [Token(t.text, (t.lemma_ or t.text), t.pos_, t.dep_,
                             max(0, t.head.i - start), t.i - start)
                       for t in sentence]

    return analyze, directory_size_mb(str(nlp.path) if nlp.path else None)


def build_stanza(package: str) -> tuple[Callable, float]:
    import stanza

    # Ohne Abhängigkeitsanalyse fiele Teil 4 aus; Eigennamen liefert bereits die
    # Wortart, deshalb kein eigener NER-Schritt — das hielte den Vergleich mit spaCy
    # nicht sauber und kostete nur Zeit.
    nlp = stanza.Pipeline("en", processors="tokenize,pos,lemma,depparse",
                          package=package, download_method=None, verbose=False)

    def analyze(chunks: Iterable[str]) -> Iterator[list[Token]]:
        for chunk in chunks:
            for sentence in nlp(chunk).sentences:
                tokens = []
                for i, word in enumerate(sentence.words):
                    # Stanza zählt ab 1, die Wurzel trägt den Kopf 0.
                    head = word.head - 1 if word.head > 0 else i
                    tokens.append(Token(word.text, word.lemma or word.text, word.upos,
                                        word.deprel, head, i))
                yield tokens

    model_dir = os.path.join(os.path.expanduser("~"), "stanza_resources", "en")
    return analyze, directory_size_mb(model_dir)


def load_engine(spec: str) -> Engine:
    """Lädt „spacy:en_core_web_sm" oder „stanza:default"."""
    library, _, model = spec.partition(":")
    library = library.lower()
    if library not in ("spacy", "stanza"):
        raise SystemExit(f"Unbekannte Bibliothek in {spec!r} — erwartet spacy: oder stanza:")

    started = time.perf_counter()
    try:
        if library == "spacy":
            analyze, size = build_spacy(model or "en_core_web_sm")
        else:
            analyze, size = build_stanza(model or "default")
    except ImportError as e:
        hint = ("pip install spacy && python -m spacy download en_core_web_sm"
                if library == "spacy" else
                'pip install stanza && python -c "import stanza; stanza.download(\'en\')"')
        raise SystemExit(f"{spec}: {e}\nInstallation:  {hint}")
    except Exception as e:
        hint = (f"python -m spacy download {model}" if library == "spacy" else
                'python -c "import stanza; stanza.download(\'en\')"')
        raise SystemExit(f"{spec}: Modell nicht ladbar ({e})\nVermutlich nötig:  {hint}")

    return Engine(spec, library, analyze, time.perf_counter() - started, size)


def peak_memory_mb() -> float | None:
    """Aktueller Speicherbedarf des Prozesses, sofern messbar."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        pass
    try:
        import resource   # nur unter Linux/macOS, dort in KiB bzw. Byte
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / 1024 if sys.platform != "darwin" else peak / 1024 / 1024
    except Exception:
        return None


# --------------------------------------------------------------------------- Text

def split_chunks(text: str, limit_words: int, chunk_chars: int = 40_000) -> tuple[list[str], int]:
    """Zerlegt an Absatzgrenzen, damit kein Satz zerschnitten wird.

    `limit_words` = 0 heißt: der ganze Text. Sonst wird beim ersten Absatz abgebrochen,
    der die Grenze überschreitet — die Grenze ist also ungefähr, nicht exakt.
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_chars = 0
    words = 0
    for paragraph in re.split(r"\n\s*\n", text):
        if limit_words and words >= limit_words:
            break
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        words += len(coverage_check.WORD.findall(paragraph))
        buffer.append(paragraph)
        buffer_chars += len(paragraph)
        if buffer_chars >= chunk_chars:
            chunks.append("\n\n".join(buffer))
            buffer, buffer_chars = [], 0
    if buffer:
        chunks.append("\n\n".join(buffer))
    return chunks, words


def is_word(token: Token) -> bool:
    return token.pos not in SKIPPED_POS and bool(coverage_check.WORD.fullmatch(token.text))


def analyze_one(engine: Engine, text: str) -> list[Token]:
    """Alle Wörter eines einzelnen Satzes — für die Testfälle in Teil 2."""
    return [t for sentence in engine.analyze([text]) for t in sentence]


# --------------------------------------------------------------------------- Teil 1

def part_lemmas(sentences: list[list[Token]], headwords: set[str], examples: int) -> dict:
    """Restlücke mit echter Lemmatisierung, gegen Rohform und Suffix-Heuristik."""
    forms: collections.Counter = collections.Counter()
    lemma_hit_tokens = 0
    lemma_hit_forms: set[str] = set()
    lemmas: set[str] = set()
    gaps: collections.Counter = collections.Counter()
    proper_tokens = 0

    for sentence in sentences:
        for token in sentence:
            if not is_word(token):
                continue
            if token.pos == "PROPN":
                proper_tokens += 1
                continue
            form = token.text.lower()
            lemma = token.lemma.lower()
            forms[form] += 1
            lemmas.add(lemma)
            if lemma in headwords:
                lemma_hit_tokens += 1
                lemma_hit_forms.add(form)
            else:
                gaps[lemma] += 1

    total = sum(forms.values())
    if not total:
        return {}

    raw_forms = {f for f in forms if f in headwords}
    suffix_forms = {f for f in forms
                    if any(c in headwords for c in coverage_check.lemma_candidates(f))}

    def row(hit_forms: set[str]) -> tuple[float, float]:
        hit_tokens = sum(forms[f] for f in hit_forms)
        return len(hit_forms) / len(forms), hit_tokens / total

    print("=" * 72)
    print("TEIL 1 — Grundformen und Restlücke")
    print("=" * 72)
    print(f"  Wörter gesamt (ohne Eigennamen)  {total:>8,}")
    print(f"  davon als Eigenname erkannt      {proper_tokens:>8,}  (nicht mitgezählt)")
    print(f"  Wortformen (types)               {len(forms):>8,}")
    print(f"  Grundformen (lemma types)        {len(lemmas):>8,}"
          f"   → {1 - len(lemmas)/len(forms):.0%} weniger Einträge in der Triage")

    print(f"\n  {'Rückführung auf die Grundform':<34}{'Treffer':>10}{'Abdeckung':>12}"
          f"{'Restlücke':>12}")
    for label, hits in (("gar keine, Wortform direkt", raw_forms),
                        ("Suffix-Heuristik (coverage_check)", suffix_forms)):
        types_rate, token_rate = row(hits)
        print(f"  {label:<34}{types_rate:>9.1%}{token_rate:>12.1%}{1-token_rate:>12.2%}")
    lemma_type_rate = len(lemma_hit_forms) / len(forms)
    lemma_token_rate = lemma_hit_tokens / total
    print(f"  {'Lemmatisierung (dieses Modell)':<34}{lemma_type_rate:>9.1%}"
          f"{lemma_token_rate:>12.1%}{1-lemma_token_rate:>12.2%}")

    print(f"\n  Restlücke: {1-lemma_token_rate:.2%} der Wörter"
          f"   (Schätzung in technik.md §2: ≈ 1,0 %)")

    if gaps:
        print("\n  Häufigste verbleibende Lücken (Grundform, Vorkommen):")
        top = ", ".join(f"{lemma} ({count})" for lemma, count in gaps.most_common(examples))
        print("    " + top)

    return {"gap": 1 - lemma_token_rate, "forms": len(forms), "lemmas": len(lemmas),
            "tokens": total}


# --------------------------------------------------------------------------- Teil 2

def part_order(engine: Engine, headwords: set[str]) -> dict:
    """Der `saw`-Fall: Führt Wortart → Grundform an der richtigen Stelle vorbei?"""
    print("\n" + "=" * 72)
    print("TEIL 2 — Reihenfolge Wortart → Grundform → Nachschlagen")
    print("=" * 72)
    print("  Regel 2 (dokumentation.md §4). Gefährlich sind die mit ! markierten Zeilen:")
    print("  Dort steht die Wortform selbst im Wörterbuch, ein Nachschlagen ohne")
    print("  Lemmatisierung liefert also still eine falsche Übersetzung.\n")

    correct = silent_failures = prevented = 0
    for sentence, form, expected_lemma, expected_pos in ORDER_CASES:
        found = next((t for t in analyze_one(engine, sentence)
                      if t.text.lower() == form.lower()), None)
        if found is None:
            print(f"  [??]   {form:<10} nicht im analysierten Satz gefunden")
            continue

        lemma_ok = found.lemma.lower() == expected_lemma
        pos_ok = found.pos == expected_pos
        trap = form.lower() in headwords and form.lower() != expected_lemma
        if trap:
            silent_failures += 1
        if lemma_ok and pos_ok:
            correct += 1
            if trap:
                prevented += 1
            mark = "ok"
        else:
            mark = "FALSCH"

        marker = "!" if trap else " "
        print(f"  {marker}[{mark:<6}] {form:<10} → ({found.pos}) {found.lemma}")
        if not (lemma_ok and pos_ok):
            print(f"            erwartet: ({expected_pos}) {expected_lemma}"
                  f"   „{sentence}“")

    print(f"\n  {correct}/{len(ORDER_CASES)} richtig")
    print(f"  Stille Fehlschläge: {prevented}/{silent_failures} verhindert"
          f" — Fälle, in denen die falsche Grundform ohne Fehlermeldung durchgelaufen wäre")
    return {"order": f"{correct}/{len(ORDER_CASES)}", "prevented": prevented,
            "traps": silent_failures}


# --------------------------------------------------------------------------- Teil 3

def part_proper_nouns(sentences: list[list[Token]], examples: int) -> dict:
    """Abnahmekriterium 2: keine Figurennamen als Lernvokabeln — und keine Verluste."""
    proper: collections.Counter = collections.Counter()
    other: collections.Counter = collections.Counter()
    capitalized: collections.Counter = collections.Counter()
    total: collections.Counter = collections.Counter()

    content: set[str] = set()
    for sentence in sentences:
        first = True
        for token in sentence:
            if not is_word(token):
                continue
            form = token.text.lower()
            total[form] += 1
            # Großschreibung am Satzanfang sagt nichts über einen Eigennamen aus.
            # coverage_check.py kann das nicht trennen und zählt „Then" mit; hier liegen
            # Satzgrenzen vor, also wird der erste Wortplatz übersprungen.
            if token.text[0].isupper() and not first:
                capitalized[form] += 1
            if token.pos == "PROPN":
                proper[form] += 1
            else:
                other[form] += 1
            if token.pos in CONTENT_POS:
                content.add(form)
            first = False

    print("\n" + "=" * 72)
    print("TEIL 3 — Eigennamen")
    print("=" * 72)
    print(f"  Als Eigenname erkannt: {sum(proper.values()):,} Vorkommen,"
          f" {len(proper):,} verschiedene")
    print("\n  Häufigste — diese Wörter erscheinen nicht in der Triage:")
    print("    " + ", ".join(f"{w} ({n})" for w, n in proper.most_common(examples)))

    # Fehlerrichtung 1: übersehen. Wörter, die fast immer großgeschrieben stehen, aber
    # nie als Eigenname bestimmt wurden — Kandidaten, die als Lernvokabel durchrutschen.
    missed = [w for w, n in total.items()
              if w not in proper and w in content and n >= 3
              and capitalized[w] / n > CAPITAL_RATIO]
    missed.sort(key=lambda w: -total[w])
    print(f"\n  Übersehen (immer groß, nie als Eigenname bestimmt): {len(missed)}")
    if missed:
        print("    " + ", ".join(f"{w} ({total[w]})" for w in missed[:examples]))

    # Fehlerrichtung 2: zu viel. Wörter, die auch kleingeschrieben im Text vorkommen und
    # trotzdem irgendwo als Eigenname gelten — dort geht eine echte Vokabel verloren.
    overreach = [w for w in proper
                 if other[w] and capitalized[w] / total[w] < CAPITAL_RATIO]
    overreach.sort(key=lambda w: -proper[w])
    print(f"  Zu viel (kommt auch klein vor, gilt aber teils als Eigenname):"
          f" {len(overreach)}")
    if overreach:
        print("    " + ", ".join(f"{w} ({proper[w]}/{total[w]})" for w in overreach[:examples]))

    return {"proper": len(proper), "missed": len(missed), "overreach": len(overreach)}


# --------------------------------------------------------------------------- Teil 4

def part_phrasal_verbs(sentences: list[list[Token]], mwes: dict, examples: int) -> dict:
    """Die auseinandergerissenen Phrasal Verbs — diesmal gemessen, nicht geschätzt."""
    contiguous: collections.Counter = collections.Counter()
    separated: collections.Counter = collections.Counter()
    unknown: collections.Counter = collections.Counter()
    separated_examples: list[str] = []

    for sentence in sentences:
        for token in sentence:
            if token.dep not in PARTICLE_DEPS:
                continue
            if not 0 <= token.head < len(sentence):
                continue
            verb = sentence[token.head]
            key = f"{verb.lemma.lower()} {token.text.lower()}"
            gap = token.index - verb.index - 1
            if key not in mwes:
                unknown[key] += 1
                continue
            if gap <= 0:
                contiguous[key] += 1
            else:
                separated[key] += 1
                if len(separated_examples) < examples:
                    span = " ".join(t.text for t in sentence[verb.index:token.index + 1])
                    separated_examples.append(f"{key:<18} „{span}“")

    total = sum(contiguous.values()) + sum(separated.values())

    print("\n" + "=" * 72)
    print("TEIL 4 — getrennte Phrasal Verbs, über die Abhängigkeitsanalyse")
    print("=" * 72)
    print(f"  zusammenhängend („gave up the idea“):   {sum(contiguous.values()):>6,}")
    print(f"  getrennt      („gave the idea up“):     {sum(separated.values()):>6,}")
    if total:
        print(f"  → {sum(separated.values())/total:.0%} stehen getrennt"
              f"   (Schätzung in technik.md, „Messung: Mehrwortausdrücke“: ~51 %)")
    print(f"\n  Ohne Wörterbucheintrag: {sum(unknown.values()):,} Vorkommen,"
          f" {len(unknown):,} verschiedene")
    print("  Diese gehören nach Regel 10 als `uncertain` markiert, nicht verworfen.")
    if unknown:
        print("    " + ", ".join(f"{k} ({n})" for k, n in unknown.most_common(examples)))

    if separated_examples:
        print("\n  Beispiele getrennter Vorkommen:")
        for line in separated_examples:
            print("    " + line)

    return {"contiguous": sum(contiguous.values()), "separated": sum(separated.values()),
            "separated_share": sum(separated.values()) / total if total else 0.0,
            "unknown": sum(unknown.values())}


# --------------------------------------------------------------------------- Ablauf

def measure(engine: Engine, chunks: list[str], words: int, headwords: set[str],
            mwes: dict, examples: int) -> dict:
    print("\n\n" + "#" * 72)
    print(f"# {engine.spec}")
    print("#" * 72)

    memory_before = peak_memory_mb()
    result: dict = {"spec": engine.spec, "load": engine.load_seconds,
                    "size": engine.size_mb}

    sentences: list[list[Token]] = []
    if chunks:
        started = time.perf_counter()
        sentences = list(engine.analyze(chunks))
        elapsed = time.perf_counter() - started
        result["rate"] = words / elapsed if elapsed else 0.0
        result["seconds"] = elapsed
        result.update(part_lemmas(sentences, headwords, examples))

    result.update(part_order(engine, headwords))

    if sentences:
        result.update(part_proper_nouns(sentences, examples))
        result.update(part_phrasal_verbs(sentences, mwes, examples))

    print("\n" + "=" * 72)
    print("TEIL 5 — Kosten")
    print("=" * 72)
    print(f"  Modell laden           {engine.load_seconds:>8.1f} s")
    print(f"  Modell auf der Platte  {engine.size_mb:>8.0f} MB")
    if "rate" in result:
        rate = result["rate"]
        print(f"  Durchsatz              {rate:>8,.0f} Wörter/s"
              f"   ({result['seconds']:.1f} s für {words:,} Wörter)")
        if rate:
            print(f"  Hochrechnung           {5_000/rate:>8.1f} s je Kapitel (5.000 Wörter)")
            print(f"                         {108_163/rate:>8.1f} s je Buch"
                  f" (Sherlock Holmes, 108.163 Wörter)")
    memory_after = peak_memory_mb()
    if memory_before is not None and memory_after is not None:
        result["memory"] = memory_after - memory_before
        print(f"  Speicher (Zuwachs)     {result['memory']:>8.0f} MB")
    return result


def print_summary(results: list[dict], licensed: set[str]) -> None:
    print("\n\n" + "=" * 72)
    print("ZUSAMMENFASSUNG")
    print("=" * 72)
    header = (f"  {'Modell':<26}{'Restlücke':>11}{'Reihenf.':>10}{'übersehen':>11}"
              f"{'getrennt':>10}{'Wörter/s':>10}")
    print(header)
    for r in results:
        gap = f"{r['gap']:.2%}" if "gap" in r else "—"
        missed = str(r["missed"]) if "missed" in r else "—"
        share = f"{r['separated_share']:.0%}" if "separated_share" in r else "—"
        rate = f"{r['rate']:,.0f}" if "rate" in r else "—"
        print(f"  {r['spec']:<26}{gap:>11}{r.get('order', '—'):>10}{missed:>11}"
              f"{share:>10}{rate:>10}")

    print("\n  Lizenzlage — vor der Aufnahme zu prüfen:")
    for library in sorted(licensed):
        text, note = LICENSES[library]
        print(f"    {text}\n      → {note}")

    if len(results) > 1:
        print("\n  Hinweis: Der Speicherzuwachs ist nur bei einem Modell je Lauf")
        print("  aussagekräftig — frühere Modelle bleiben im Prozess geladen.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Vergleicht spaCy und Stanza an echtem Buchtext.",
        epilog="Bereitet Entscheidung 5 in technik.md vor.")
    p.add_argument("file", nargs="?", help="Textdatei (UTF-8); ohne sie laufen nur Teil 2 und 5")
    p.add_argument("--models", default=DEFAULT_MODELS,
                   help=f"kommagetrennt, z. B. spacy:en_core_web_md,stanza:default "
                        f"(Vorgabe: {DEFAULT_MODELS})")
    p.add_argument("--db", default=DEFAULT_DB, help="Pfad zur WikDict-Datenbank")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                   help=f"Wörter je Lauf, 0 = ganzer Text (Vorgabe: {DEFAULT_LIMIT:,})")
    p.add_argument("--min-score", type=float, default=mwe_check.DEFAULT_MIN_SCORE,
                   help="Schwelle für Wendungen, wie in mwe_check.py")
    p.add_argument("--examples", type=int, default=15, help="Anzahl gezeigter Beispiele")
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        print("Mit  python tools/coverage_check.py --fetch-dictionary  herunterladen.",
              file=sys.stderr)
        return 1

    headwords = coverage_check.load_headwords(args.db)
    _, mwes = mwe_check.load_mwes(args.db, args.min_score)
    print(f"Wörterbuch: {args.db}")
    print(f"Stichwörter: {len(headwords):,} · Wendungen nach Filter: {len(mwes):,}")

    chunks: list[str] = []
    words = 0
    if args.file:
        if not os.path.exists(args.file):
            print(f"nicht gefunden: {args.file}", file=sys.stderr)
            return 1
        text = coverage_check.read_text(args.file)
        chunks, words = split_chunks(text, args.limit)
        available = len(coverage_check.WORD.findall(text))
        print(f"Text: {os.path.basename(args.file)} · {words:,} Wörter"
              f"{f' von {available:,} (gekürzt durch --limit)' if words < available else ''}")
    else:
        print("Kein Buchtext angegeben — nur Teil 2 und 5.")

    results = []
    libraries = set()
    for spec in [s.strip() for s in args.models.split(",") if s.strip()]:
        engine = load_engine(spec)
        libraries.add(engine.library)
        results.append(measure(engine, chunks, words, headwords, mwes, args.examples))

    print_summary(results, libraries)
    print("\nDie Zahlen gehören als Entscheidung 5 nach technik.md — mit Datum,")
    print("wie die vier davor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
