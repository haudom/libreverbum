#!/usr/bin/env python3
"""Bedeutungstest: Wählt das lokale Modell die im Kontext richtige Bedeutung?

Hintergrund
-----------
Das Konzept (../konzept.md, Abschnitt 5) beruht darauf, dass das Modell aus den
Bedeutungen des Wörterbuchs **auswählt**, statt zu **erfinden**. Ob das Modell das
kann, entscheidet über die Qualität des ganzen Programms — und lässt sich nicht
ausrechnen, nur messen. Dieses Skript ist die Messung.

Es setzt Abnahmekriterium 3 aus dem Konzept um: mehrdeutige Wörter im echten
Buchzusammenhang, Ergebnis von Hand gegenprüfbar.

Verfahren
---------
1. Mehrdeutige Wörter im Buchtext suchen (mehrere Bedeutungen in WikDict)
2. Den Originalsatz aus dem Buch als Belegsatz nehmen
3. Modell die passende Bedeutung **aus der Liste** wählen lassen
4. Ergebnis anzeigen — mit Erwartungswert, wo einer hinterlegt ist

Entscheidend: Die Antwort wird auf die Nummern der vorgelegten Bedeutungen
eingeschränkt. Das Modell *kann* nichts erfinden. Wo der Server ein JSON-Schema
unterstützt, wird das erzwungen; sonst wird die Antwort streng geprüft.

Aufruf
------
    python tools/sense_check.py                     # Server automatisch suchen
    python tools/sense_check.py --url http://127.0.0.1:8080
    python tools/sense_check.py --word bank --word lie
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "en-de.sqlite3")

# Übliche Adressen lokaler Modellserver. llama-server zuerst, weil empfohlen.
SERVER_CANDIDATES = [
    ("http://127.0.0.1:8080", "llama-server"),
    ("http://127.0.0.1:1234", "LM Studio"),
    ("http://127.0.0.1:11434", "Ollama"),
    ("http://127.0.0.1:8000", "vLLM / sonstige"),
    ("http://127.0.0.1:5001", "KoboldCpp"),
]

# Testfälle: Wörter, deren Bedeutung erst der Satz klärt.
#
# Bewertet wird die **deutsche Übersetzung**, nicht die Bedeutungsnummer. Das ist
# Absicht: `bank` hat neun Bedeutungen, von denen sechs auf „Bank" hinauslaufen.
# Für eine Vokabelkarte zählt das Ergebnis, nicht welche Zeile das Modell traf.
# Die Aufgabe ist damit leichter, als die Länge der Liste vermuten lässt.
#
# 'expected' ist eine Menge zulässiger deutscher Wörter; None heisst: von Hand
# beurteilen.
TEST_CASES = [
    ("bank", "He sat on the bank of the river and watched the water flow past.", {"Ufer"}),
    ("bank", "She deposited the cheque at the bank on Monday morning.", {"Bank"}),
    ("saw", "He saw her standing at the window.", None),
    ("saw", "He cut the plank in half with a rusty saw.", {"Säge"}),
    ("lie", "He would lie on the grass for hours, staring at the clouds.", {"liegen"}),
    ("lie", "Do not lie to me — I know exactly where you were.", {"lügen", "täuschen"}),
    ("light", "The room was filled with a soft golden light.", {"Licht"}),
    ("light", "The parcel was surprisingly light for its size.", {"leicht"}),
    ("spring", "In spring the whole valley turns green.", {"Frühling", "Frühjahr", "Lenz"}),
    ("spring", "The spring in the old clock had snapped.", {"Feder", "Sprungfeder"}),
    (
        "watch",
        "He forgot to wind his watch before going to bed.",
        {"Uhr", "Armbanduhr", "Taschenuhr"},
    ),
    ("draw", "She began to draw his portrait in charcoal.", {"zeichnen", "malen"}),
]


# --------------------------------------------------------------------------- Server


def find_server(preset: str | None) -> tuple[str, str, str] | None:
    """Sucht einen erreichbaren, OpenAI-kompatiblen Modellserver.

    Gibt (url, modellname, beschreibung) zurück. Der Modellname ist nötig, weil
    manche Server (Ollama) ihn zwingend verlangen, andere (llama-server) nicht.
    """
    candidates = [(preset, "vorgegeben")] if preset else SERVER_CANDIDATES
    for url, name in candidates:
        url = url.rstrip("/")
        try:
            with urllib.request.urlopen(f"{url}/v1/models", timeout=2) as r:
                data = json.load(r)
            models = [m.get("id", "?") for m in data.get("data", [])]
            label = f"{name} · {', '.join(models[:3]) or 'unbenannt'}"
            return url, (models[0] if models else ""), label
        except Exception:
            continue
    return None


# Denkschritte mancher Modelle (Qwen3 u. a.) vor der eigentlichen Antwort
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S | re.I)


def ask_model(
    url: str, model: str, prompt: str, option_count: int, timeout: int
) -> tuple[int | None, str]:
    """Fragt das Modell nach einer Bedeutungsnummer. Gibt (nummer, rohantwort) zurück."""
    body = {
        "model": model,  # Ollama verlangt das Feld; llama-server ignoriert es
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        # Denkschritt abschalten. Ohne das verbrauchen Modelle wie Qwen3.5 ihr ganzes
        # Token-Budget mit Nachdenken und liefern nie eine Antwort (finish_reason
        # "length"). Gemessen: 1,0 s statt 28,3 s — bei gleichem Ergebnis. Die Aufgabe
        # ist eine Auswahl aus einer Liste, dafür ist Nachdenken unnötig.
        "reasoning_effort": "none",
        # Reserve, falls ein Server den Schalter oben nicht kennt.
        "max_tokens": 512,
        # Erzwingt die Antwortform, wo der Server es unterstützt (llama-server, LM Studio).
        # Server, die das Feld nicht kennen, ignorieren es in aller Regel.
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sense_choice",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "choice": {"type": "integer", "minimum": 1, "maximum": option_count}
                    },
                    "required": ["choice"],
                    "additionalProperties": False,
                },
            },
        },
    }

    def send(payload: dict):
        request = urllib.request.Request(
            f"{url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as r:
            return json.load(r)

    try:
        response = send(body)
    except urllib.error.HTTPError as e:
        # Server, die "reasoning_effort" oder das JSON-Schema nicht kennen, lehnen die
        # Anfrage ab. Dann ohne diese Felder erneut versuchen.
        if e.code in (400, 422):
            reduced = {
                k: v for k, v in body.items() if k not in ("reasoning_effort", "response_format")
            }
            try:
                response = send(reduced)
            except Exception as e2:
                return None, f"auch ohne Zusatzfelder gescheitert: {e2}"
        else:
            return None, f"HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}"
    except Exception as e:
        return None, f"Fehler: {e}"

    message = response["choices"][0]["message"]
    text = (message.get("content") or "").strip()
    # Manche Server liefern den Denkschritt in einem eigenen Feld, andere inline.
    text = THINK_BLOCK.sub("", text).strip()
    if not text and message.get("reasoning_content"):
        text = str(message["reasoning_content"]).strip()

    try:
        choice = int(json.loads(text)["choice"])
    except Exception:
        # Notnagel für Server ohne Schema-Zwang: letzte Zahl im gültigen Bereich nehmen —
        # die erste wäre oft eine Zahl aus dem Denkschritt.
        numbers = [int(n) for n in re.findall(r"\d+", text)]
        valid = [n for n in numbers if 1 <= n <= option_count]
        choice = valid[-1] if valid else None
    if choice is not None and not 1 <= choice <= option_count:
        return None, f"ausserhalb 1..{option_count}: {text!r}"
    return choice, text


# --------------------------------------------------------------------------- Wörterbuch

# Beschriftung für Einträge ohne Bedeutungstext. Diese Zeilen NICHT wegzulassen ist
# wichtig: 36 % aller Einträge haben keinen sense-Text, und es sind systematisch die
# **Hauptbedeutungen** mit der höchsten Bewertung. Beispiele: watch → „Uhr“ (136,7),
# draw → „zeichnen“ (172,9) — beides die jeweils bestbewertete Zeile des Stichworts.
NO_SENSE_TEXT = "Hauptbedeutung, ohne nähere Angabe"


def senses(con: sqlite3.Connection, word: str) -> list[tuple[str, str, str]]:
    """(Wortart, englische Kurzdefinition, deutsche Entsprechung) je Bedeutung.

    Nach Bewertung absteigend — die gebräuchlichsten Bedeutungen stehen oben.
    """
    rows = con.execute(
        "SELECT lexentry, sense, trans_list FROM translation "
        "WHERE written_rep = ? ORDER BY score DESC",
        (word,),
    ).fetchall()
    seen, result = set(), []
    for lexentry, wikdict_sense, translation in rows:
        pos = lexentry.split("__")[1].replace("_", " ") if lexentry and "__" in lexentry else "?"
        key = (wikdict_sense or "").strip().lower() or f"\0{pos}"  # je Wortart nur einmal
        if key in seen:
            continue
        seen.add(key)
        result.append((pos, (wikdict_sense or "").strip() or NO_SENSE_TEXT, translation))
    return result


def build_prompt(word: str, sentence: str, options: list[tuple[str, str, str]]) -> str:
    lines = [
        f"{i}. ({pos}) {sense} → {translation}"
        for i, (pos, sense, translation) in enumerate(options, 1)
    ]
    return (
        "You are helping a German learner of English.\n"
        f'In the sentence below, which listed meaning does the word "{word}" have?\n\n'
        f"Sentence: {sentence}\n\n"
        "Meanings:\n" + "\n".join(lines) + "\n\n"
        'Answer with JSON only: {"choice": <number>}'
    )


# --------------------------------------------------------------------------- Ablauf


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Prüft, ob das lokale Modell die richtige Wörterbuchbedeutung wählt.",
        epilog="Setzt Abnahmekriterium 3 aus konzept.md um.",
    )
    p.add_argument("--url", help="Adresse des Modellservers (sonst automatische Suche)")
    p.add_argument("--db", default=DEFAULT_DB, help="Pfad zur WikDict-Datenbank")
    p.add_argument("--model", help="Modellname (sonst das erste, das der Server nennt)")
    p.add_argument("--word", action="append", help="nur diese Wörter prüfen (mehrfach möglich)")
    p.add_argument("--timeout", type=int, default=120, help="Zeitgrenze je Anfrage in Sekunden")
    p.add_argument("--show-prompt", action="store_true", help="ersten Prompt vollständig ausgeben")
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        print(
            "Mit  python tools/coverage_check.py --fetch-dictionary  herunterladen.",
            file=sys.stderr,
        )
        return 1

    found = find_server(args.url)
    if not found:
        print("Kein Modellserver erreichbar.\n", file=sys.stderr)
        print("Erwartet wird eine OpenAI-kompatible Schnittstelle, zum Beispiel:", file=sys.stderr)
        print("  llama-server -m modell.gguf -c 8192 --host 127.0.0.1 --port 8080", file=sys.stderr)
        print("\nGesucht wurde auf: " + ", ".join(u for u, _ in SERVER_CANDIDATES), file=sys.stderr)
        return 1

    url, model, description = found
    if args.model:
        model = args.model
    print(f"Server: {url}  ({description})")
    print(f"Modell: {model or '(vom Server bestimmt)'}")

    con = sqlite3.connect(args.db)
    cases = [c for c in TEST_CASES if not args.word or c[0] in args.word]
    if not cases:
        print("Keine Testfälle für die angegebenen Wörter.", file=sys.stderr)
        return 1

    print(f"Testfälle: {len(cases)}\n" + "=" * 72)

    checked = correct = manual = 0
    first = True
    for word, sentence, expected in cases:
        options = senses(con, word)
        if len(options) < 2:
            print(f"\n{word!r}: nur {len(options)} Bedeutung(en) im Wörterbuch — übersprungen")
            continue

        prompt = build_prompt(word, sentence, options)
        if first and args.show_prompt:
            print("\n--- Prompt (Beispiel) ---\n" + prompt + "\n" + "-" * 24)
            first = False

        choice, raw = ask_model(url, model, prompt, len(options), args.timeout)
        checked += 1

        print(f"\n„{sentence}“")
        print(f"  Wort: {word}   ({len(options)} Bedeutungen zur Auswahl)")

        if choice is None:
            print(f"  → KEINE gültige Antwort: {raw}")
            manual += 1
            continue

        pos, sense, translation = options[choice - 1]
        # Bewertung am Ergebnis: reicht eine der gelieferten Übersetzungen aus?
        offered = {t.strip() for t in (translation or "").split("|")}
        if expected is None:
            mark = "?"  # von Hand zu beurteilen
            manual += 1
        elif offered & expected:
            mark = "ok"
            correct += 1
        else:
            mark = "FALSCH"

        print(f"  → [{mark}] {choice}. ({pos}) {sense} → {translation}")
        if mark == "FALSCH":
            print(f"       erwartet: {' / '.join(sorted(expected))}")

    print("\n" + "=" * 72)
    auto_scored = checked - manual
    if auto_scored:
        print(f"Automatisch bewertbar: {correct}/{auto_scored} richtig")
    print(f"Von Hand zu beurteilen: {manual}")
    print("\nHinweis: Das Modell kann nur aus der vorgelegten Liste wählen — erfundene")
    print("Übersetzungen sind ausgeschlossen. Geprüft wird die Trefferqualität der Auswahl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
