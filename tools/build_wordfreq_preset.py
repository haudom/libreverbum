#!/usr/bin/env python3
"""Erzeugt die eingefrorene Grundwortschatzliste für die Vorbelegung des Profils.

Hintergrund
-----------
konzept.md, „Bewusst offen" (erster Punkt): Beim Anlegen des Profils soll der Nutzer
gefragt werden, ob die häufigsten englischen Grundformen einmalig als bekannt eingetragen
werden. Datenquelle ist `wordfreq` 3.1.1 — aber **als eingefrorene Datei im Repository**,
nicht als Abhängigkeit des Projekts: Wer die Vorbelegung nutzt, braucht `wordfreq` zur
Laufzeit nicht, und die Liste bleibt reproduzierbar, ohne dass ein späteres `wordfreq`-
Update sie stillschweigend verschiebt. Dieses Skript erzeugt genau die Datei, die im
Repository liegt (`libreverbum/wordfreq_en_5000.txt`) — es ist damit kein Messskript wie
seine Nachbarn (`*_check.py`), sondern das Bauskript für einen ausgelieferten Bestandteil
des Programms.

Warum zwei Umgebungen und zwei Stufen
--------------------------------------
`wordfreq` wird bewusst **nicht** Abhängigkeit des Projekts und darf deshalb nicht in
`.venv/` landen. Die Lemmatisierung muss dagegen über **denselben** spaCy-Lemmatisierer
laufen wie der Kern (`en_core_web_md`), sonst beschriebe die eingefrorene Liste eine andere
Grundform-Bildung als `libreverbum.extraction`. Beides zugleich gibt es in keiner der
beiden vorhandenen Umgebungen — das Skript läuft deshalb in zwei getrennten Aufrufen:

    Stufe 1 — in einer Wegwerfumgebung MIT wordfreq, OHNE .venv/ zu berühren:
        pip install wordfreq==3.1.1
        python tools/build_wordfreq_preset.py export-forms formen.json

    Stufe 2 — in .venv/ (spaCy und en_core_web_md liegen dort bereits, siehe
    CLAUDE.md, „Aktueller Stand"; in einer nackten Umgebung stattdessen
        pip install spacy
        <Modell-Wheel aus pyproject.toml, dependencies, `en_core_web_md`>):
        python tools/build_wordfreq_preset.py build formen.json \
            --out ../libreverbum/wordfreq_en_5000.txt

Fünf Bildungsregeln — verbindlich, nicht bei jedem Lauf neu zu entscheiden
---------------------------------------------------------------------------
1. Quelle: `wordfreq`s englische Liste `large_en` (`wordlist="best"`), 60.000 Formen
   exportiert
2. Nichtalphabetische Formen (`it's`, `don't`, `1`, `2`, `you're`, …) werden übersprungen
   und verbrauchen keinen Platz von N — sie können an der `is_alpha`-Bedingung des Kerns
   (`libreverbum/extraction.py`, `token.is_alpha`) nie treffen
3. Grundform = `token.lemma_.lower()` über spaCy `en_core_web_md`, jede Form einzeln ohne
   Satzkontext
4. Der Rang einer Grundform ist der Rang ihrer häufigsten Oberflächenform, nicht die Summe
   über alle Formen
5. Von oben durchgehen, bis N verschiedene Grundformen beisammen sind

Bekannter Schönheitsfehler
---------------------------
Ein Teil der Grundformen zerfällt bei der Lemmatisierung in mehrere Token und wird dadurch
zu einem Mehrworteintrag (`cannot` -> „can not", `gonna` -> „go to", …). Der Grund steht in
Regel 3: Sie nennt `token.lemma_.lower()` in der Einzahl, umgesetzt ist die Verkettung über
**alle** Token einer Form (`" ".join(…)`) — bei einer einformigen Eingabe dasselbe, bei
einer zerfallenden nicht.

**Tote Plätze sind das nicht.** `extraction.extract_expression_candidates` bildet je Satz
aus jedem n-Gramm alphabetischer Token eine Grundform nach genau derselben Vorschrift; „go
to", „get to", „do not", „can not" und „will not" entstehen dort laufend. Die Einträge
wirken also — auf dem Wendungsweg statt auf dem Wortweg. Sie bleiben bewusst drin: Die
Messwerte, auf denen die Entscheidung für die Vorbelegung beruht, stammen von genau dieser
Liste, und eine nachträgliche Bereinigungsregel gäbe es nirgends sonst im Projekt. Der Kopf
der erzeugten Datei nennt die tatsächlich gefundenen Einträge — ausgezählt bei diesem Lauf,
nicht aus einer früheren Messung übernommen.

Was diese Datei nicht entscheidet: den Abgleichschlüssel
---------------------------------------------------------
Die Datei trägt **kein `pos`**, nur Grundformen. Im Profil ist der Abgleichschlüssel
dagegen `(text, pos)` (`libreverbum/profile.py`), und die beiden Wege des Kerns füllen ihn
verschieden: Wortgrundformen tragen eine echte Wortart, Wendungsgrundformen den leeren Wert
(`extraction._NO_SINGLE_POS`). Welches `pos` die Vorbelegung beim Einlesen schreibt,
entscheidet deshalb der Bauschritt, der sie einliest — nicht diese Datei und nicht dieses
Skript. Ein einziger fester Wert träfe entweder nur die Mehrworteinträge oder keinen der N.

Aufruf
------
    python tools/build_wordfreq_preset.py export-forms formen.json
    python tools/build_wordfreq_preset.py export-forms formen.json --limit 60000
    python tools/build_wordfreq_preset.py build formen.json
    python tools/build_wordfreq_preset.py build formen.json --out ziel.txt --n 5000

Erwartet und schreibt Textdateien ausschließlich mit `encoding="utf-8"`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
from importlib.metadata import version
from pathlib import Path
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FORMS_LIMIT = 60_000
DEFAULT_N = 5_000
DEFAULT_OUT = os.path.normpath(os.path.join(HERE, "..", "libreverbum", "wordfreq_en_5000.txt"))
DEFAULT_LANGUAGE = "en"


def _export_forms(out_path: str, limit: int, language: str) -> None:
    """Stufe 1: exportiert die rohe `wordfreq`-Rangliste als JSON. Braucht `wordfreq`."""
    import wordfreq

    wordfreq_version = version("wordfreq")
    list_path = wordfreq.available_languages("best").get(language, "?")
    # available_languages liefert den vollen Pfad zur Datendatei (…/large_en.msgpack.gz).
    # Der Listenname aus Regel 1 ("large_en") ist nur der Dateiname ohne die Endungen.
    list_name = os.path.basename(list_path).removesuffix(".msgpack.gz")
    forms = wordfreq.top_n_list(language, limit, wordlist="best")
    payload: dict[str, Any] = {
        "wordfreq_version": wordfreq_version,
        "language": language,
        "wordlist": "best",
        "list_name": list_name,
        "forms": forms,
    }
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    meldung = (
        f"wordfreq {wordfreq_version}, Liste „{list_name}“ "
        f"(wordlist=best, {language}): {len(forms)} Formen exportiert -> {out_path}"
    )
    print(meldung)


def _build(forms_path: str, out_path: str, n: int) -> None:
    """Stufe 2: lemmatisiert die Rohliste über spaCy und schreibt die eingefrorene Datei.
    Braucht `spacy` samt `en_core_web_md`."""
    import spacy

    payload = json.loads(Path(forms_path).read_text(encoding="utf-8"))
    forms: list[str] = payload["forms"]
    total = len(forms)
    alpha_forms = [f for f in forms if f.isalpha()]
    # Der Rang jeder alphabetischen Form in der ungefilterten Rangliste (1-gezählt). Ohne
    # ihn ließe sich der Kopf nicht widerspruchsfrei schreiben: Die übersprungenen
    # nichtalphabetischen Formen über den ganzen Export gezählt passen nicht zu den
    # verbrauchten Formen, die nur bis zum Erreichen von N reichen (leicht-Befund 2,
    # Review Bauschritt 1).
    alpha_ranks = [i + 1 for i, f in enumerate(forms) if f.isalpha()]
    skipped_nonalpha = total - len(alpha_forms)

    nlp = spacy.load("en_core_web_md")
    lemma_order: list[str] = []
    seen: set[str] = set()
    consumed = 0
    for doc in nlp.pipe(alpha_forms, batch_size=500):
        consumed += 1
        lemma = " ".join(t.lemma_.lower() for t in doc).strip()
        if lemma and lemma not in seen:
            seen.add(lemma)
            lemma_order.append(lemma)
            if len(lemma_order) >= n:
                break

    if len(lemma_order) < n:
        raise SystemExit(
            f"nur {len(lemma_order)} verschiedene Grundformen erreicht, N={n} verlangt "
            f"mehr — --limit bei »export-forms« erhöhen und Stufe 1 erneut laufen lassen"
        )

    last_rank = alpha_ranks[consumed - 1]
    skipped_within = last_rank - consumed

    multiword = [w for w in lemma_order if " " in w]
    header = _build_header(
        payload=payload,
        n=n,
        total_forms=total,
        skipped_nonalpha=skipped_nonalpha,
        consumed=consumed,
        last_rank=last_rank,
        skipped_within=skipped_within,
        multiword=multiword,
    )
    Path(out_path).write_text(header + "\n".join(lemma_order) + "\n", encoding="utf-8")
    print(
        f"{len(lemma_order)} Grundformen aus {consumed} verbrauchten alphabetischen Formen "
        f"(Ränge 1 bis {last_rank}, darin {skipped_within} nichtalphabetische übersprungen; "
        f"über den ganzen Export {skipped_nonalpha} von {total}) -> {out_path}"
    )
    print(f"Mehrworteinträge ({len(multiword)}): {', '.join(multiword)}")


def _build_header(
    *,
    payload: dict[str, Any],
    n: int,
    total_forms: int,
    skipped_nonalpha: int,
    consumed: int,
    last_rank: int,
    skipped_within: int,
    multiword: list[str],
) -> str:
    heute = datetime.date.today().strftime("%d.%m.%Y")
    spacy_version = version("spacy")
    model_version = version("en_core_web_md")
    anfuehrung = "„{0}“"
    multiword_text = ", ".join(anfuehrung.format(w) for w in multiword) if multiword else "keine"
    quelle = anfuehrung.format(payload["list_name"])
    lines = [
        "# Eingefrorene Grundwortschatzliste für die Vorbelegung des Profils.",
        "#",
        f"# Quelle: wordfreq {payload['wordfreq_version']}, Liste {quelle}",
        f'# (wordlist="best", Sprache {payload["language"]}), {total_forms} Formen exportiert.',
        f"# Lemmatisiert über spaCy {spacy_version} mit en_core_web_md {model_version} —",
        "# dieselbe Fassung wie libreverbum/extraction.py.",
        "#",
        "# Bildungsregeln:",
        f"#  1. Quelle: wordfreq {quelle} (wordlist=best), {total_forms} Formen exportiert.",
        "#  2. Nichtalphabetische Formen werden übersprungen und verbrauchen keinen Platz",
        "#     von N — sie treffen die is_alpha-Bedingung des Kerns nie. Innerhalb der",
        f"#     dafür durchlaufenen Ränge 1 bis {last_rank} sind das {skipped_within};",
        f"#     über den ganzen Export gerechnet {skipped_nonalpha} von {total_forms}.",
        "#  3. Grundform = token.lemma_.lower() über spaCy, jede Form einzeln ohne",
        "#     Satzkontext.",
        "#  4. Der Rang einer Grundform ist der Rang ihrer häufigsten Oberflächenform,",
        "#     nicht die Summe über alle Formen.",
        f"#  5. Von oben durchgehen, bis N={n} verschiedene Grundformen beisammen sind",
        f"#     (verbraucht dafür: {consumed} alphabetische Formen, Ränge 1 bis {last_rank}).",
        "#",
        f"# Bekannter Schönheitsfehler: {len(multiword)} Einträge zerfallen bei der",
        "# Lemmatisierung in mehrere Token und werden dadurch zu Mehrworteinträgen —",
        "# Bildungsregel 3 nennt token.lemma_.lower() in der Einzahl, umgesetzt ist die",
        "# Verkettung über alle Token einer Form. Tote Plätze sind sie nicht: Der Kern",
        "# bildet auf dem Wendungsweg (extraction.extract_expression_candidates) nach",
        "# genau derselben Vorschrift Grundformen aus mehreren Token, sie können also",
        "# treffen. Sie bleiben stehen, weil die Messwerte der Entscheidung auf genau",
        f"# dieser Liste beruhen: {multiword_text}.",
        "#",
        "# Diese Datei trägt kein pos. Der Abgleichschlüssel des Profils ist (text, pos),",
        "# und Wortweg und Wendungsweg des Kerns füllen ihn verschieden — welches pos die",
        "# Vorbelegung schreibt, entscheidet der Bauschritt, der diese Datei einliest,",
        "# nicht die Datei selbst.",
        "#",
        "# Die Liste steht in Rangfolge (häufigste zuerst). Ein Präfix beliebiger Länge",
        f"# daraus (die ersten k von {n} Zeilen) ist eine gültige Auswahl der k häufigsten",
        "# Grundformen — welches Niveau welche Länge bekommt, entscheidet nicht diese",
        "# Datei.",
        "#",
        f"# Erzeugt am {heute} mit tools/build_wordfreq_preset.py.",
        "#",
        "# Lizenz: Die wordfreq-Häufigkeitsdaten stehen unter CC BY-SA 4.0, ebenso diese",
        "# bearbeitete Auswahl daraus (Top N, auf Grundformen gefaltet, nichtalphabetische",
        "# Formen entfernt) — abweichend von der MIT-Lizenz des übrigen Repositoriums.",
        "# Herkunft und Nennungen: siehe NOTICE im Wurzelverzeichnis.",
        "#",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_export = sub.add_parser(
        "export-forms", help="Stufe 1: wordfreq-Rangliste als JSON exportieren (braucht wordfreq)"
    )
    p_export.add_argument("out", help="Zieldatei für die JSON-Rohliste")
    p_export.add_argument("--limit", type=int, default=DEFAULT_FORMS_LIMIT)
    p_export.add_argument("--language", default=DEFAULT_LANGUAGE)

    p_build = sub.add_parser(
        "build", help="Stufe 2: lemmatisieren und die eingefrorene Liste schreiben (braucht spaCy)"
    )
    p_build.add_argument("forms", help="JSON-Rohliste aus Stufe 1")
    p_build.add_argument("--out", default=DEFAULT_OUT)
    p_build.add_argument("--n", type=int, default=DEFAULT_N)

    args = parser.parse_args()
    if args.mode == "export-forms":
        _export_forms(args.out, args.limit, args.language)
    else:
        _build(args.forms, args.out, args.n)


if __name__ == "__main__":
    main()
