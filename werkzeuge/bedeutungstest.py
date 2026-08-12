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
    python werkzeuge/bedeutungstest.py                     # Server automatisch suchen
    python werkzeuge/bedeutungstest.py --url http://127.0.0.1:8080
    python werkzeuge/bedeutungstest.py --buch buch.txt     # eigene Textquelle
    python werkzeuge/bedeutungstest.py --wort bank --wort lie
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
STANDARD_DB = os.path.join(HERE, "en-de.sqlite3")

# Übliche Adressen lokaler Modellserver. llama-server zuerst, weil empfohlen.
KANDIDATEN = [
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
# 'erwartet' ist eine Menge zulässiger deutscher Wörter; None heisst: von Hand
# beurteilen.
TESTFAELLE = [
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
    ("watch", "He forgot to wind his watch before going to bed.",
     {"Uhr", "Armbanduhr", "Taschenuhr"}),
    ("draw", "She began to draw his portrait in charcoal.", {"zeichnen", "malen"}),
]


# --------------------------------------------------------------------------- Server

def finde_server(vorgabe: str | None) -> tuple[str, str, str] | None:
    """Sucht einen erreichbaren, OpenAI-kompatiblen Modellserver.

    Gibt (url, modellname, beschreibung) zurück. Der Modellname ist nötig, weil
    manche Server (Ollama) ihn zwingend verlangen, andere (llama-server) nicht.
    """
    kandidaten = [(vorgabe, "vorgegeben")] if vorgabe else KANDIDATEN
    for url, name in kandidaten:
        url = url.rstrip("/")
        try:
            with urllib.request.urlopen(f"{url}/v1/models", timeout=2) as r:
                daten = json.load(r)
            modelle = [m.get("id", "?") for m in daten.get("data", [])]
            return url, (modelle[0] if modelle else ""), f"{name} · {', '.join(modelle[:3]) or 'unbenannt'}"
        except Exception:
            continue
    return None


# Denkschritte mancher Modelle (Qwen3 u. a.) vor der eigentlichen Antwort
DENKBLOCK = re.compile(r"<think>.*?</think>", re.S | re.I)


def frage_modell(url: str, modell: str, prompt: str, anzahl: int,
                 timeout: int) -> tuple[int | None, str]:
    """Fragt das Modell nach einer Bedeutungsnummer. Gibt (nummer, rohantwort) zurück."""
    rumpf = {
        "model": modell,          # Ollama verlangt das Feld; llama-server ignoriert es
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
                "name": "auswahl",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"nummer": {"type": "integer",
                                              "minimum": 1, "maximum": anzahl}},
                    "required": ["nummer"],
                    "additionalProperties": False,
                },
            },
        },
    }
    def sende(koerper: dict):
        anfrage = urllib.request.Request(
            f"{url}/v1/chat/completions",
            data=json.dumps(koerper).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(anfrage, timeout=timeout) as r:
            return json.load(r)

    try:
        antwort = sende(rumpf)
    except urllib.error.HTTPError as e:
        # Server, die "reasoning_effort" oder das JSON-Schema nicht kennen, lehnen die
        # Anfrage ab. Dann ohne diese Felder erneut versuchen.
        if e.code in (400, 422):
            schlank = {k: v for k, v in rumpf.items()
                       if k not in ("reasoning_effort", "response_format")}
            try:
                antwort = sende(schlank)
            except Exception as e2:
                return None, f"auch ohne Zusatzfelder gescheitert: {e2}"
        else:
            return None, f"HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}"
    except Exception as e:
        return None, f"Fehler: {e}"

    nachricht = antwort["choices"][0]["message"]
    text = (nachricht.get("content") or "").strip()
    # Manche Server liefern den Denkschritt in einem eigenen Feld, andere inline.
    text = DENKBLOCK.sub("", text).strip()
    if not text and nachricht.get("reasoning_content"):
        text = str(nachricht["reasoning_content"]).strip()

    try:
        nummer = int(json.loads(text)["nummer"])
    except Exception:
        # Notnagel für Server ohne Schema-Zwang: letzte Zahl im gültigen Bereich nehmen —
        # die erste wäre oft eine Zahl aus dem Denkschritt.
        zahlen = [int(z) for z in re.findall(r"\d+", text)]
        gueltig = [z for z in zahlen if 1 <= z <= anzahl]
        nummer = gueltig[-1] if gueltig else None
    if nummer is not None and not 1 <= nummer <= anzahl:
        return None, f"ausserhalb 1..{anzahl}: {text!r}"
    return nummer, text


# --------------------------------------------------------------------------- Wörterbuch

# Beschriftung für Einträge ohne Bedeutungstext. Diese Zeilen NICHT wegzulassen ist
# wichtig: 36 % aller Einträge haben keinen sense-Text, und es sind systematisch die
# **Hauptbedeutungen** mit der höchsten Bewertung. Beispiele: watch → „Uhr“ (136,7),
# draw → „zeichnen“ (172,9) — beides die jeweils bestbewertete Zeile des Stichworts.
OHNE_SINN = "Hauptbedeutung, ohne nähere Angabe"


def bedeutungen(con: sqlite3.Connection, wort: str) -> list[tuple[str, str, str]]:
    """(Wortart, englische Kurzdefinition, deutsche Entsprechung) je Bedeutung.

    Nach Bewertung absteigend — die gebräuchlichsten Bedeutungen stehen oben.
    """
    zeilen = con.execute(
        "SELECT lexentry, sense, trans_list FROM translation "
        "WHERE written_rep = ? ORDER BY score DESC", (wort,)).fetchall()
    gesehen, ergebnis = set(), []
    for lexentry, sinn, uebersetzung in zeilen:
        wortart = lexentry.split("__")[1].replace("_", " ") if lexentry and "__" in lexentry else "?"
        schluessel = (sinn or "").strip().lower() or f"\0{wortart}"   # je Wortart nur einmal
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        ergebnis.append((wortart, (sinn or "").strip() or OHNE_SINN, uebersetzung))
    return ergebnis


def baue_prompt(wort: str, satz: str, liste: list[tuple[str, str, str]]) -> str:
    zeilen = [f"{i}. ({wa}) {sinn} → {ue}" for i, (wa, sinn, ue) in enumerate(liste, 1)]
    return (
        "You are helping a German learner of English.\n"
        f'In the sentence below, which listed meaning does the word "{wort}" have?\n\n'
        f"Sentence: {satz}\n\n"
        "Meanings:\n" + "\n".join(zeilen) + "\n\n"
        'Answer with JSON only: {"nummer": <number>}'
    )


# --------------------------------------------------------------------------- Ablauf

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(
        description="Prüft, ob das lokale Modell die richtige Wörterbuchbedeutung wählt.",
        epilog="Setzt Abnahmekriterium 3 aus konzept.md um.")
    p.add_argument("--url", help="Adresse des Modellservers (sonst automatische Suche)")
    p.add_argument("--db", default=STANDARD_DB, help="Pfad zur WikDict-Datenbank")
    p.add_argument("--modell", help="Modellname (sonst das erste, das der Server nennt)")
    p.add_argument("--wort", action="append", help="nur diese Wörter prüfen (mehrfach möglich)")
    p.add_argument("--timeout", type=int, default=120, help="Zeitgrenze je Anfrage in Sekunden")
    p.add_argument("--zeige-prompt", action="store_true", help="ersten Prompt vollständig ausgeben")
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"Wörterbuch fehlt: {args.db}", file=sys.stderr)
        print("Mit  python werkzeuge/abdeckungstest.py --hole-woerterbuch  herunterladen.",
              file=sys.stderr)
        return 1

    gefunden = finde_server(args.url)
    if not gefunden:
        print("Kein Modellserver erreichbar.\n", file=sys.stderr)
        print("Erwartet wird eine OpenAI-kompatible Schnittstelle, zum Beispiel:", file=sys.stderr)
        print("  llama-server -m modell.gguf -c 8192 --host 127.0.0.1 --port 8080",
              file=sys.stderr)
        print("\nGesucht wurde auf: " + ", ".join(u for u, _ in KANDIDATEN), file=sys.stderr)
        return 1

    url, modell, beschreibung = gefunden
    if args.modell:
        modell = args.modell
    print(f"Server: {url}  ({beschreibung})")
    print(f"Modell: {modell or '(vom Server bestimmt)'}")

    con = sqlite3.connect(args.db)
    faelle = [f for f in TESTFAELLE if not args.wort or f[0] in args.wort]
    if not faelle:
        print("Keine Testfälle für die angegebenen Wörter.", file=sys.stderr)
        return 1

    print(f"Testfälle: {len(faelle)}\n" + "=" * 72)

    geprueft = passend = unklar = 0
    erster = True
    for wort, satz, erwartet in faelle:
        liste = bedeutungen(con, wort)
        if len(liste) < 2:
            print(f"\n{wort!r}: nur {len(liste)} Bedeutung(en) im Wörterbuch — übersprungen")
            continue

        prompt = baue_prompt(wort, satz, liste)
        if erster and args.zeige_prompt:
            print("\n--- Prompt (Beispiel) ---\n" + prompt + "\n" + "-" * 24)
            erster = False

        nummer, roh = frage_modell(url, modell, prompt, len(liste), args.timeout)
        geprueft += 1

        print(f"\n„{satz}“")
        print(f"  Wort: {wort}   ({len(liste)} Bedeutungen zur Auswahl)")

        if nummer is None:
            print(f"  → KEINE gültige Antwort: {roh}")
            unklar += 1
            continue

        wortart, sinn, uebersetzung = liste[nummer - 1]
        # Bewertung am Ergebnis: reicht eine der gelieferten Übersetzungen aus?
        geliefert = {t.strip() for t in (uebersetzung or "").split("|")}
        if erwartet is None:
            marke = "?"          # von Hand zu beurteilen
            unklar += 1
        elif geliefert & erwartet:
            marke = "ok"
            passend += 1
        else:
            marke = "FALSCH"

        print(f"  → [{marke}] {nummer}. ({wortart}) {sinn} → {uebersetzung}")
        if marke == "FALSCH":
            print(f"       erwartet: {' / '.join(sorted(erwartet))}")

    print("\n" + "=" * 72)
    automatisch = geprueft - unklar
    if automatisch:
        print(f"Automatisch bewertbar: {passend}/{automatisch} richtig")
    print(f"Von Hand zu beurteilen: {unklar}")
    print("\nHinweis: Das Modell kann nur aus der vorgelegten Liste wählen — erfundene")
    print("Übersetzungen sind ausgeschlossen. Geprüft wird die Trefferqualität der Auswahl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
