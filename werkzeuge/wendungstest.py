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
    python werkzeuge/wendungstest.py buch.txt
    python werkzeuge/wendungstest.py buch.txt --url http://127.0.0.1:8080
    python werkzeuge/wendungstest.py buch.txt --mindest-score 50
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
STANDARD_DB = os.path.join(HERE, "en-de.sqlite3")

WORT = re.compile(r"[^\W\d_](?:[^\W\d_]|['-])*")
SATZ = re.compile(r"[^.!?]*[.!?]")

# Grammatisches Rauschen liegt bei score 2–4, echte Wendungen bei 100+.
# Gemessen: "of the" 4.0, "in the" 2.0 · "of course" 128.6, "give up" 120.0
STANDARD_SCORE = 50.0

# Diese Wortarten sind keine Lernvokabeln (Eigennamen behandelt das Konzept separat).
UNERWUENSCHTE_WORTART = {"Proper_noun"}

# Partikeln, die bei Phrasal Verbs vom Verb getrennt stehen können.
PARTIKEL = {"up", "down", "out", "off", "on", "in", "away", "back", "over",
            "through", "along", "around", "about", "apart", "aside", "forward"}


def lade_wendungen(db: str, mindest_score: float) -> tuple[dict, dict]:
    """Gibt (alle_wendungen, gefilterte_wendungen) zurück, je Kleinschreibung → Infos."""
    con = sqlite3.connect(db)
    alle: dict[str, dict] = {}
    for wr, le, sinn, ue, score in con.execute(
            "SELECT written_rep, lexentry, sense, trans_list, score FROM translation "
            "WHERE written_rep LIKE '% %'"):
        try:
            s = float(score)
        except (TypeError, ValueError):
            s = 0.0
        wa = le.split("__")[1] if le and "__" in le else "?"
        schluessel = wr.lower()
        vorhanden = alle.get(schluessel)
        if vorhanden is None or s > vorhanden["score"]:
            alle[schluessel] = {"text": wr, "wortart": wa, "sinn": sinn,
                                "uebersetzung": ue, "score": s}
    gefiltert = {k: v for k, v in alle.items()
                 if v["score"] >= mindest_score and v["wortart"] not in UNERWUENSCHTE_WORTART}
    return alle, gefiltert


def finde_zusammenhaengend(tokens: list[str], wendungen: dict) -> collections.Counter:
    """Längster Treffer gewinnt, dann weiter hinter dem Treffer."""
    maxlen = max((len(w.split()) for w in wendungen), default=0)
    gefunden: collections.Counter = collections.Counter()
    i = 0
    while i < len(tokens):
        for n in range(min(maxlen, len(tokens) - i), 1, -1):
            kandidat = " ".join(tokens[i:i + n])
            if kandidat in wendungen:
                gefunden[kandidat] += 1
                i += n
                break
        else:
            i += 1
    return gefunden


def finde_getrennt(tokens: list[str], wendungen: dict, abstand: int = 4) -> collections.Counter:
    """Phrasal Verbs mit Einschub: „gave the idea up“ statt „gave up the idea“.

    Sucht Verb+Partikel-Wendungen, deren Teile bis zu `abstand` Wörter auseinander
    stehen. Bewusst grob — ohne Lemmatisierung werden nur die Grundformen erkannt,
    also eine Untergrenze.
    """
    zweiteilig = {}
    for schluessel, info in wendungen.items():
        teile = schluessel.split()
        # Nur Verben. Ohne diese Prüfung entstehen Scheintreffer wie „as … in“ oder
        # „way … in“, weil auch Präpositionen und Substantive auf Partikel enden.
        if len(teile) == 2 and teile[1] in PARTIKEL and info["wortart"] == "Verb":
            zweiteilig.setdefault(teile[0], set()).add(teile[1])

    gefunden: collections.Counter = collections.Counter()
    for i, wort in enumerate(tokens):
        partikel = zweiteilig.get(wort)
        if not partikel:
            continue
        # direkt danach wäre zusammenhängend — hier nur die getrennte Form
        for j in range(i + 2, min(i + 2 + abstand, len(tokens))):
            if tokens[j] in partikel:
                gefunden[f"{wort} … {tokens[j]}"] += 1
                break
    return gefunden


def frage_modell(url: str, modell: str, abschnitt: str, timeout: int) -> tuple[list[str], str]:
    prompt = (
        "You are helping build a vocabulary list for a German learner of English.\n"
        "List the idioms, phrasal verbs and fixed expressions in the passage below "
        "whose meaning a learner could NOT guess from the individual words.\n"
        "Do not list ordinary word combinations. Do not list proper names.\n\n"
        f"Passage:\n{abschnitt}\n\n"
        'Answer with JSON only: {"ausdruecke": ["...", "..."]}'
    )
    rumpf = {
        "model": modell,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "reasoning_effort": "none",
        "max_tokens": 512,
    }

    def sende(koerper):
        anfrage = urllib.request.Request(
            f"{url}/v1/chat/completions", data=json.dumps(koerper).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(anfrage, timeout=timeout) as r:
            return json.load(r)

    try:
        antwort = sende(rumpf)
    except urllib.error.HTTPError as e:
        if e.code in (400, 422):
            try:
                antwort = sende({k: v for k, v in rumpf.items() if k != "reasoning_effort"})
            except Exception as e2:
                return [], f"gescheitert: {e2}"
        else:
            return [], f"HTTP {e.code}"
    except Exception as e:
        return [], f"Fehler: {e}"

    text = (antwort["choices"][0]["message"].get("content") or "").strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
    try:
        return [str(a) for a in json.loads(text).get("ausdruecke", [])], text
    except Exception:
        klammer = re.search(r"\{.*\}", text, re.S)
        if klammer:
            try:
                return [str(a) for a in json.loads(klammer.group()).get("ausdruecke", [])], text
            except Exception:
                pass
    return [], text


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Misst die Erkennung von Mehrwortausdrücken.")
    p.add_argument("datei", help="Textdatei (UTF-8)")
    p.add_argument("--db", default=STANDARD_DB)
    p.add_argument("--mindest-score", type=float, default=STANDARD_SCORE,
                   help=f"Schwelle gegen grammatisches Rauschen (Vorgabe: {STANDARD_SCORE})")
    p.add_argument("--url", help="Modellserver — schaltet Teil 3 frei")
    p.add_argument("--modell")
    p.add_argument("--abschnitte", type=int, default=3, help="Textabschnitte für Teil 3")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        return 1

    text = open(args.datei, encoding="utf-8-sig", errors="replace").read()
    tokens = [w.lower() for w in WORT.findall(text)]

    alle, gefiltert = lade_wendungen(args.db, args.mindest_score)
    print(f"Wörterbuch: {len(alle):,} Mehrwortausdrücke, "
          f"davon {len(gefiltert):,} nach Filter "
          f"(score ≥ {args.mindest_score:g}, ohne {', '.join(UNERWUENSCHTE_WORTART)})")
    print(f"Text: {len(tokens):,} Wörter\n")

    # ---------------------------------------------------------------- Teil 1
    print("=" * 72)
    print("TEIL 1 — zusammenhängende Wendungen")
    print("=" * 72)
    roh = finde_zusammenhaengend(tokens, alle)
    fein = finde_zusammenhaengend(tokens, gefiltert)
    print(f"  ohne Filter: {sum(roh.values()):>7,} Vorkommen, {len(roh):>5,} verschiedene")
    print(f"  mit  Filter: {sum(fein.values()):>7,} Vorkommen, {len(fein):>5,} verschiedene")
    entfernt = sum(roh.values()) - sum(fein.values())
    if sum(roh.values()):
        print(f"  → Filter entfernt {entfernt:,} Vorkommen "
              f"({entfernt/sum(roh.values()):.0%} des Rauschens)")

    weg = sorted(set(roh) - set(fein), key=lambda m: -roh[m])[:12]
    print(f"\n  Vom Filter entfernt (häufigste): {', '.join(weg)}")
    print("\n  Häufigste verbleibende Wendungen:")
    for m, n in fein.most_common(20):
        info = gefiltert[m]
        print(f"    {n:>4}x  {m:<26} ({info['wortart']}) → {str(info['uebersetzung'])[:44]}")

    # ---------------------------------------------------------------- Teil 2
    print("\n" + "=" * 72)
    print("TEIL 2 — auseinandergerissene Phrasal Verbs")
    print("=" * 72)
    getrennt = finde_getrennt(tokens, gefiltert)
    zush_pv = {m: n for m, n in fein.items()
               if len(m.split()) == 2 and m.split()[1] in PARTIKEL
               and gefiltert[m]["wortart"] == "Verb"}
    print(f"  zusammenhängend gefunden: {sum(zush_pv.values()):>5,} Vorkommen")
    print(f"  getrennt gefunden:        {sum(getrennt.values()):>5,} Vorkommen")
    gesamt = sum(zush_pv.values()) + sum(getrennt.values())
    if gesamt:
        print(f"  → {sum(getrennt.values())/gesamt:.0%} aller Phrasal Verbs stehen getrennt "
              f"und entgehen dem n-Gramm-Abgleich")
    print("\n  Beispiele getrennter Vorkommen:")
    for m, n in getrennt.most_common(15):
        print(f"    {n:>4}x  {m}")

    # ---------------------------------------------------------------- Teil 3
    if args.url:
        print("\n" + "=" * 72)
        print("TEIL 3 — Modellprüfung")
        print("=" * 72)
        url = args.url.rstrip("/")
        modell = args.modell
        if not modell:
            try:
                with urllib.request.urlopen(f"{url}/v1/models", timeout=5) as r:
                    daten = json.load(r)
                modell = daten["data"][0]["id"]
            except Exception as e:
                print(f"  Modellliste nicht lesbar: {e}", file=sys.stderr)
                return 1
        print(f"  Modell: {modell}\n")

        saetze = [s.strip() for s in SATZ.findall(text) if 40 < len(s.strip()) < 400]
        schritt = max(1, len(saetze) // (args.abschnitte + 1))
        for k in range(args.abschnitte):
            abschnitt = " ".join(saetze[k * schritt: k * schritt + 5])
            if not abschnitt:
                continue
            treffer, roh_antwort = frage_modell(url, modell, abschnitt, args.timeout)
            print(f"  --- Abschnitt {k+1} ---")
            print(f"  {abschnitt[:300]}{'…' if len(abschnitt) > 300 else ''}")
            if not treffer:
                print(f"  → keine verwertbare Antwort: {roh_antwort[:160]}")
                continue
            klein = abschnitt.lower()
            for a in treffer:
                imtext = "im Text" if a.lower() in klein else "NICHT wörtlich im Text"
                imwb = "im Wörterbuch" if a.lower() in alle else "nicht im Wörterbuch"
                print(f"    • {a:<30} [{imtext}; {imwb}]")
            print()

    print("=" * 72)
    print("Der Filter löst das Rauschproblem; Teil 2 zeigt die Grenze des Verfahrens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
