#!/usr/bin/env python3
"""Wendungstest: Werden Mehrwortausdrücke im echten Buchtext gefunden?

Hintergrund
-----------
Das Konzept (../konzept.md, Abschnitt 2) nennt Redewendungen und Phrasal Verbs „die
eigentliche Stärke des LLM-Ansatzes". 44 % der Wörterbuch-Stichwörter sind
Mehrwortausdrücke. Dieses Skript misst, was davon im Buchtext ankommt — und wo die
Grenze des rein wörterbuchbasierten Vorgehens liegt.

Drei Teile
----------
1. **Zusammenhängend**  — n-Gramm-Abgleich gegen das Wörterbuch. Deterministisch,
   ohne Modell. Zeigt das Rausch-Problem und wie gut der Filter es löst.
2. **Auseinandergerissen** — „he gave the idea up". Vom n-Gramm-Abgleich prinzipiell
   nicht auffindbar. Misst, wie viel dadurch verloren geht.
3. **Modellprüfung** — kann das LLM Wendungen in einem Textabschnitt benennen?
   Nur mit ``--url``.

Aufruf
------
    python tools/mwe_check.py buch.txt
    python tools/mwe_check.py buch.txt --url http://127.0.0.1:8080
    python tools/mwe_check.py buch.txt --min-score 50
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")
SENTENCE = re.compile(r"[^.!?]*[.!?]")

# Grammatisches Rauschen liegt bei score 2–4, echte Wendungen bei 100+.
# Gemessen: "of the" 4.0, "in the" 2.0 · "of course" 128.6, "give up" 120.0
DEFAULT_MIN_SCORE = 50.0

# Diese Wortarten sind keine Lernvokabeln (Eigennamen behandelt das Konzept separat).
EXCLUDED_POS = {"Proper_noun"}

# Partikeln, die bei Phrasal Verbs vom Verb getrennt stehen können.
PARTICLES = {"up", "down", "out", "off", "on", "in", "away", "back", "over",
             "through", "along", "around", "about", "apart", "aside", "forward"}


def load_mwes(db: str, min_score: float) -> tuple[dict, dict]:
    """Gibt (alle_wendungen, gefilterte_wendungen) zurück, je Kleinschreibung → Infos."""
    con = sqlite3.connect(db)
    all_mwes: dict[str, dict] = {}
    for written_rep, lexentry, wikdict_sense, translation, score in con.execute(
            "SELECT written_rep, lexentry, sense, trans_list, score FROM translation "
            "WHERE written_rep LIKE '% %'"):
        try:
            value = float(score)
        except (TypeError, ValueError):
            value = 0.0
        pos = lexentry.split("__")[1] if lexentry and "__" in lexentry else "?"
        key = written_rep.lower()
        existing = all_mwes.get(key)
        if existing is None or value > existing["score"]:
            all_mwes[key] = {"text": written_rep, "pos": pos, "wikdict_sense": wikdict_sense,
                             "translation": translation, "score": value}
    filtered = {k: v for k, v in all_mwes.items()
                if v["score"] >= min_score and v["pos"] not in EXCLUDED_POS}
    return all_mwes, filtered


def find_contiguous(tokens: list[str], mwes: dict) -> collections.Counter:
    """Längster Treffer gewinnt, dann weiter hinter dem Treffer."""
    max_len = max((len(m.split()) for m in mwes), default=0)
    found: collections.Counter = collections.Counter()
    i = 0
    while i < len(tokens):
        for n in range(min(max_len, len(tokens) - i), 1, -1):
            candidate = " ".join(tokens[i:i + n])
            if candidate in mwes:
                found[candidate] += 1
                i += n
                break
        else:
            i += 1
    return found


def find_separated(tokens: list[str], mwes: dict, max_gap: int = 4) -> collections.Counter:
    """Phrasal Verbs mit Einschub: „gave the idea up“ statt „gave up the idea“.

    Sucht Verb+Partikel-Wendungen, deren Teile bis zu `max_gap` Wörter auseinander
    stehen. Bewusst grob — ohne Lemmatisierung werden nur die Grundformen erkannt,
    also eine Untergrenze.
    """
    two_part = {}
    for key, info in mwes.items():
        parts = key.split()
        # Nur Verben. Ohne diese Prüfung entstehen Scheintreffer wie „as … in“ oder
        # „way … in“, weil auch Präpositionen und Substantive auf Partikel enden.
        if len(parts) == 2 and parts[1] in PARTICLES and info["pos"] == "Verb":
            two_part.setdefault(parts[0], set()).add(parts[1])

    found: collections.Counter = collections.Counter()
    for i, word in enumerate(tokens):
        particles = two_part.get(word)
        if not particles:
            continue
        # direkt danach wäre zusammenhängend — hier nur die getrennte Form
        for j in range(i + 2, min(i + 2 + max_gap, len(tokens))):
            if tokens[j] in particles:
                found[f"{word} … {tokens[j]}"] += 1
                break
    return found


def ask_model(url: str, model: str, passage: str, timeout: int) -> tuple[list[str], str]:
    prompt = (
        "You are helping build a vocabulary list for a German learner of English.\n"
        "List the idioms, phrasal verbs and fixed expressions in the passage below "
        "whose meaning a learner could NOT guess from the individual words.\n"
        "Do not list ordinary word combinations. Do not list proper names.\n\n"
        f"Passage:\n{passage}\n\n"
        'Answer with JSON only: {"expressions": ["...", "..."]}'
    )
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "reasoning_effort": "none",
        "max_tokens": 512,
    }

    def send(payload):
        request = urllib.request.Request(
            f"{url}/v1/chat/completions", data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as r:
            return json.load(r)

    try:
        response = send(body)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):
            try:
                response = send({k: v for k, v in body.items() if k != "reasoning_effort"})
            except Exception as e2:
                return [], f"gescheitert: {e2}"
        else:
            return [], f"HTTP {e.code}"
    except Exception as e:
        return [], f"Fehler: {e}"

    text = (response["choices"][0]["message"].get("content") or "").strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
    try:
        return [str(x) for x in json.loads(text).get("expressions", [])], text
    except Exception:
        braces = re.search(r"\{.*\}", text, re.S)
        if braces:
            try:
                return [str(x) for x in json.loads(braces.group()).get("expressions", [])], text
            except Exception:
                pass
    return [], text


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Misst die Erkennung von Mehrwortausdrücken.")
    p.add_argument("file", help="Textdatei (UTF-8)")
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                   help=f"Schwelle gegen grammatisches Rauschen (Vorgabe: {DEFAULT_MIN_SCORE})")
    p.add_argument("--url", help="Modellserver — schaltet Teil 3 frei")
    p.add_argument("--model")
    p.add_argument("--sections", type=int, default=3, help="Textabschnitte für Teil 3")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        return 1

    text = open(args.file, encoding="utf-8-sig", errors="replace").read()
    tokens = [w.lower() for w in WORD.findall(text)]

    all_mwes, filtered = load_mwes(args.db, args.min_score)
    print(f"Wörterbuch: {len(all_mwes):,} Mehrwortausdrücke, "
          f"davon {len(filtered):,} nach Filter "
          f"(score ≥ {args.min_score:g}, ohne {', '.join(EXCLUDED_POS)})")
    print(f"Text: {len(tokens):,} Wörter\n")

    # ---------------------------------------------------------------- Teil 1
    print("=" * 72)
    print("TEIL 1 — zusammenhängende Wendungen")
    print("=" * 72)
    raw_hits = find_contiguous(tokens, all_mwes)
    fine_hits = find_contiguous(tokens, filtered)
    print(f"  ohne Filter: {sum(raw_hits.values()):>7,} Vorkommen, {len(raw_hits):>5,} verschiedene")
    print(f"  mit  Filter: {sum(fine_hits.values()):>7,} Vorkommen, {len(fine_hits):>5,} verschiedene")
    removed = sum(raw_hits.values()) - sum(fine_hits.values())
    if sum(raw_hits.values()):
        print(f"  → Filter entfernt {removed:,} Vorkommen "
              f"({removed/sum(raw_hits.values()):.0%} des Rauschens)")

    dropped = sorted(set(raw_hits) - set(fine_hits), key=lambda m: -raw_hits[m])[:12]
    print(f"\n  Vom Filter entfernt (häufigste): {', '.join(dropped)}")
    print("\n  Häufigste verbleibende Wendungen:")
    for mwe, count in fine_hits.most_common(20):
        info = filtered[mwe]
        print(f"    {count:>4}x  {mwe:<26} ({info['pos']}) → {str(info['translation'])[:44]}")

    # ---------------------------------------------------------------- Teil 2
    print("\n" + "=" * 72)
    print("TEIL 2 — auseinandergerissene Phrasal Verbs")
    print("=" * 72)
    separated = find_separated(tokens, filtered)
    contiguous_pv = {m: n for m, n in fine_hits.items()
                     if len(m.split()) == 2 and m.split()[1] in PARTICLES
                     and filtered[m]["pos"] == "Verb"}
    print(f"  zusammenhängend gefunden: {sum(contiguous_pv.values()):>5,} Vorkommen")
    print(f"  getrennt gefunden:        {sum(separated.values()):>5,} Vorkommen")
    total = sum(contiguous_pv.values()) + sum(separated.values())
    if total:
        print(f"  → {sum(separated.values())/total:.0%} aller Phrasal Verbs stehen getrennt "
              f"und entgehen dem n-Gramm-Abgleich")
    print("\n  Beispiele getrennter Vorkommen:")
    for mwe, count in separated.most_common(15):
        print(f"    {count:>4}x  {mwe}")

    # ---------------------------------------------------------------- Teil 3
    if args.url:
        print("\n" + "=" * 72)
        print("TEIL 3 — Modellprüfung")
        print("=" * 72)
        url = args.url.rstrip("/")
        model = args.model
        if not model:
            try:
                with urllib.request.urlopen(f"{url}/v1/models", timeout=5) as r:
                    data = json.load(r)
                model = data["data"][0]["id"]
            except Exception as e:
                print(f"  Modellliste nicht lesbar: {e}", file=sys.stderr)
                return 1
        print(f"  Modell: {model}\n")

        sentences = [s.strip() for s in SENTENCE.findall(text) if 40 < len(s.strip()) < 400]
        step = max(1, len(sentences) // (args.sections + 1))
        for k in range(args.sections):
            passage = " ".join(sentences[k * step: k * step + 5])
            if not passage:
                continue
            hits, raw = ask_model(url, model, passage, args.timeout)
            print(f"  --- Abschnitt {k+1} ---")
            print(f"  {passage[:300]}{'…' if len(passage) > 300 else ''}")
            if not hits:
                print(f"  → keine verwertbare Antwort: {raw[:160]}")
                continue
            lowered = passage.lower()
            for hit in hits:
                in_text = "im Text" if hit.lower() in lowered else "NICHT wörtlich im Text"
                in_dict = "im Wörterbuch" if hit.lower() in all_mwes else "nicht im Wörterbuch"
                print(f"    • {hit:<30} [{in_text}; {in_dict}]")
            print()

    print("=" * 72)
    print("Der Filter löst das Rauschproblem; Teil 2 zeigt die Grenze des Verfahrens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
