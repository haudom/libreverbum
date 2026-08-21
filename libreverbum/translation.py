"""Übersetzung — wählt aus der Auswahlliste des Wörterbuchs die im Belegsatz gemeinte
Bedeutung (bauplan.md T11).

Aufgabe
-------
Schritt 5 des Kernablaufs (konzept.md §5), zweite Hälfte: der einzige Ort, an dem das
Modell angesprochen wird (technik.md §7, Modulkarte). Das Modell **wählt** aus der von
`dictionary` gelieferten Auswahlliste, es erzeugt nie frei (Regel 11) — je Wort eine
Anfrage über die OpenAI-kompatible Schnittstelle, `/v1/chat/completions`, mit
`reasoning_effort: "none"` (Regel 7) und der Antwortform per JSON-Schema erzwungen. Ein
Bündelmechanismus ist bewusst nicht gebaut: Er wählt bei 23 bis 37 % der Wörter eine
andere Bedeutung als der Einzellauf und entfällt deshalb ersatzlos (technik.md §3,
Nachtrag 19.08.2026; bauplan.md, Tor 0, E10).

Voraussetzungen
---------------
`sense_candidates` ist die bereits nach Wortart gefilterte Auswahlliste aus
`dictionary.candidates` beziehungsweise `dictionary.candidate_lists` (T5) — dieses Modul
schlägt selbst nicht im Wörterbuch nach und importiert dafür nichts als `entities`
(technik.md §7, „Die Importregel"). Ein Kandidat, der schon als `uncertain` markiert
hereinkommt (der Verb-Partikel-Platzhalter aus T7, `dictionary.particle_verb_candidates`),
kann in dieser Liste stehen — `dictionary.py` legt das ausdrücklich so an (Befund 2,
Review T11). Ob ein solcher Kandidat überhaupt zur Übersetzung vorgelegt wird, entscheidet
der Aufrufer (T15/T16); kommt er an, behandelt ihn dieses Modul wie unten unter „Liefert"
beschrieben — durchgereicht, nicht stillschweigend zur sicheren Bedeutung gemacht.
`model_name` ist bereits aufgelöst: Ist in `config.toml` (technik.md §9) kein Modellname
hinterlegt, ist das Bestimmen des ersten vom Server genannten Modells Sache des Aufrufers,
nicht dieses Moduls — bauplan.md T11 verlangt nur den Aufruf über die Schnittstelle, keine
Serversuche, und die Autosuche aus `tools/` ist ausdrücklich nicht das Vorbild
(technik.md §9). `url` trägt das `/v1` der OpenAI-kompatiblen Schnittstelle bereits selbst
(technik.md §9, `http://localhost:11434/v1`) — `_ask_model` hängt deshalb nur noch
`/chat/completions` an (Befund schwer 2, Durchsicht T16: ein zusätzliches `/v1` ergab beim
echten Server `…/v1/v1/chat/completions` und HTTP 404).

Liefert
-------
`choose_sense` liefert einen `Sense` aus `sense_candidates` mit gesetztem `translation`
(WikDicts `trans_list` der gewählten Zeile) und `uncertain=False` — oder, wenn keine der
vorgelegten Bedeutungen passt, einen `Sense` mit `uncertain=True` und `translation=None`.
Wählt das Modell einen Kandidaten, der selbst schon als `uncertain` hereinkam (kein
Wörterbucheintrag, `translation=None`), bleibt diese Marke am Ergebnis erhalten statt auf
`False` zurückgesetzt zu werden — eine plausible, aber unbestätigte Wahl wird nicht durch
den bloßen Zusammenbau des Ergebnisses zu einer sicheren Bedeutung (Befund 2, Review T11;
Regel 10). Eine leere Auswahlliste führt **nicht** zu einem Modellaufruf, sondern
unmittelbar zu `uncertain` (Regel 11; Begründung an der Stelle im Code). Jeder Fehlschlag aus
technik.md §3 und bauplan.md T11 — HTTP-Fehler, unformbare Antwort, `finish_reason:
"length"` mit leerem Inhalt, eine Nummer außerhalb von 1..N+1, ein zu langer Prompt —
bricht sichtbar mit einer deutschen Meldung ab statt eines `uncertain`-Eintrags; die
Begründung je Fall steht an der jeweiligen Stelle in `_ask_model` und `choose_sense`
(Regel 13: kein `except`, das nur protokolliert und weiterläuft).

Regeln
------
Die Ausweichantwort „keine passt" ist ein **regulärer** letzter Listeneintrag (Nummer
N+1 bei N echten Bedeutungen), kein Sonderwert außerhalb von 1..N+1 — ein Sonderwert wie
`0` läge auf dem üblichen ersten Listenindex und ließe „keine passt" still als „erste
Bedeutung" durchgehen, genau der stille Fehlschlag aus dem `saw`-Fall (technik.md §3,
offener Punkt; `tests/conftest.py`, `ModelServerDouble`). Wählt das Modell sie, ist das
**kein** Fehlschlag, sondern die Meldung einer Störung der Vorstufe.
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any

from libreverbum.entities import Occurrence, Sense

# REGEL (dokumentation.md §4 Regel 1, technik.md §3 „Datenfalle: Einträge ohne
# Bedeutungstext"): Zeilen ohne sense-Text bleiben in der Auswahlliste und tragen diese
# Beschriftung — dieselbe wie `dictionary.NO_SENSE_LABEL`, hier noch einmal definiert statt
# importiert, weil die Importregel `translation` auf `entities` beschränkt (technik.md §7).
_NO_SENSE_TEXT = "Hauptbedeutung, ohne nähere Angabe"

# (Befund 2, Review T11): Ein Kandidat, der schon als uncertain hereinkommt (der
# Verb-Partikel-Platzhalter aus T7, `dictionary.particle_verb_candidates`) trägt kein
# wikdict_sense und sähe im Prompt ohne eigene Beschriftung wie eine echte Regel-1-Zeile
# (_NO_SENSE_TEXT) aus — ununterscheidbar von einer bestätigten Hauptbedeutung. Dieselbe
# Bedeutung wie `dictionary.UNCERTAIN_LABEL`, hier noch einmal definiert statt importiert
# (Importregel, technik.md §7) — dort steht ein Kommentar, der hierher zurückverweist,
# damit ein Auseinanderlaufen der beiden Texte auffällt.
_UNCERTAIN_TEXT = "kein Wörterbucheintrag — unsicher"

# Deutlich über der gemessenen rund einen Sekunde je Wort (technik.md §3, „Gemessene
# Ergebnisse") — Reserve für einen langsameren Rechner oder eine ungewöhnlich lange
# Auswahlliste, kein Vertrauen in einen bestimmten Wert. (Befund 3, Review T11): 30 s
# deckt die erste Anfrage eines Kapitels nicht sicher ab, wenn der Server das Modell erst
# in den Speicher laden muss — der Lauf stürbe dann schon beim ersten Wort mit „timed out",
# obwohl nichts kaputt ist, und der Auftraggeber betreibt Ollama übers Netz, nicht auf
# localhost, was das Nachladen eher langsamer als schneller macht. 120 s ist eine
# Schätzung, keine Messung: großzügig genug für den Kaltstart eines mittelgroßen Modells,
# ohne bei einer echten Störung minutenlang stumm zu warten.
DEFAULT_TIMEOUT: float = 120

# Grobe, bewusst konservative Schätzung der Promptgröße vor dem Senden — rund 4 Zeichen
# je Token, aufgerundet, damit die Schätzung eher zu groß als zu klein ausfällt (wie
# tools/bundle_check.py, `estimate_prompt_tokens`, Auftrag Befund 1: eine Unterschätzung
# würde eine drohende Kürzung gerade verdecken).
_CHARS_PER_TOKEN = 4

# REGEL (technik.md §3, „Datenfalle: der Server kürzt zu lange Prompts still", Nachtrag
# 19.08.2026): Ollama kürzt Prompts über rund 4.096 Token still und meldet dabei den
# gekürzten Wert in usage.prompt_tokens — eine Prüfung danach kann die Kürzung deshalb nie
# sehen, die Promptgröße muss vor dem Senden geschätzt werden. Gemessen: 3.000 gesendete
# Token kamen noch unverändert an (prompt_tokens 3.015), 5.000 wurden auf rund 2.050
# gekürzt. Die Schwelle bleibt deshalb an der letzten gemessenen sicheren Stelle, nicht
# am Kontextfenster selbst — der Bereich dazwischen ist nicht vermessen.
_MAX_ESTIMATED_PROMPT_TOKENS = 3000


def _pos_label(lexentry: str | None) -> str:
    """Die Wortart aus WikDicts `lexentry`-Kennung, wie in `tools/sense_check.py`,
    `senses()` — reine Anzeige im Prompt, keine Filterung (die hat `dictionary` T5 schon
    erledigt)."""
    if lexentry is None or "__" not in lexentry:
        return "?"
    return lexentry.split("__")[1].replace("_", " ")


def _sense_line(number: int, sense: Sense) -> str:
    """Eine nummerierte Zeile der Auswahlliste für den Prompt: Wortart, Bedeutungstext
    (oder Regel 1s feste Beschriftung, oder — bei einem schon als uncertain hereingegebenen
    Kandidaten, Befund 2 Review T11 — dessen eigene, davon unterscheidbare Beschriftung)
    und WikDicts deutsche Entsprechungen."""
    sense_text = _UNCERTAIN_TEXT if sense.uncertain else sense.wikdict_sense or _NO_SENSE_TEXT
    translations = sense.wikdict_trans_list or "?"
    return f"{number}. ({_pos_label(sense.wikdict_lexentry)}) {sense_text} → {translations}"


def _build_prompt(occurrence: Occurrence, sense_candidates: Sequence[Sense]) -> str:
    """Baut den Prompt: Belegsatz, nummerierte Auswahlliste, Ausweichantwort als Eintrag
    N+1. Anfrageform an `tools/sense_check.py`, `build_prompt` angelehnt — der Vorlage für
    Prompt und JSON-Schema (bauplan.md T11), hier um die Ausweichantwort erweitert."""
    lines = [_sense_line(n, sense) for n, sense in enumerate(sense_candidates, 1)]
    lines.append(f"{len(sense_candidates) + 1}. none of the listed meanings fits")
    return (
        "You are helping a German learner of English.\n"
        f'In the sentence below, which listed meaning does the word "{occurrence.word_form}" '
        "have?\n\n"
        f"Sentence: {occurrence.example_sentence}\n\n"
        "Meanings:\n" + "\n".join(lines) + "\n\n"
        'Answer with JSON only: {"choice": <number>}'
    )


def _estimate_prompt_tokens(prompt: str) -> int:
    """Aufgerundete Schätzung: rund `_CHARS_PER_TOKEN` Zeichen je Token."""
    return -(-len(prompt) // _CHARS_PER_TOKEN)


def _request_body(model_name: str, prompt: str, option_count: int) -> dict[str, Any]:
    """Der Anfragekörper für `/v1/chat/completions`: `reasoning_effort: "none"` (Regel 7)
    und die Antwortform per JSON-Schema auf eine Zahl zwischen 1 und `option_count`
    (die Ausweichantwort eingeschlossen) erzwungen."""
    return {
        "model": model_name,  # Ollama verlangt das Feld (tools/sense_check.py, „send")
        "messages": [{"role": "user", "content": prompt}],
        # REGEL (dokumentation.md §4 Regel 7, technik.md §3 „Zwingende Einstellung:
        # Denkschritt abschalten"): Ohne das verbraucht das Modell sein Budget mit
        # Nachdenken und liefert keine Antwort (finish_reason "length"). Gemessen:
        # 1,0 s statt 28,3 s bei gleichem Ergebnis, an fünf Modellen nachgeprüft.
        "reasoning_effort": "none",
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


def _ask_model(*, url: str, model_name: str, prompt: str, option_count: int, timeout: float) -> int:
    """Fragt den Modellserver nach einer Nummer zwischen 1 und `option_count` und liefert
    sie geprüft zurück.

    Jeder Fehlschlag bricht sichtbar mit einer deutschen Meldung ab (Regel 13) statt eines
    `uncertain`-Eintrags — die hier unterschiedenen Fälle sagen alle nichts über dieses
    eine Wort aus, sondern über den Server oder die Betriebsart, und träten bei jedem
    weiteren Aufruf erneut auf. Als `uncertain` markiert, verwechselte sich ein solcher
    Ausfall über ein Kapitel hinweg unbemerkt mit echten Modell-Unsicherheiten und dem
    Gutfall „keine passt" (Regel 13, „Die Falle: es scheitert nicht laut, sondern
    leise"). Dazu gehören auch die drei Fälle aus Befund 3, Review T11 — Lesezeit-
    überschreitung, ein HTTP-200-Körper ohne JSON und ein Abbruch mitten in der Antwort —,
    die ohne eigene Behandlung als englische, nicht als `ValueError` eingeordnete
    Ausnahmen durchgereicht worden wären."""
    # REGEL (technik.md §9, „Einstellungen: config.toml"; Befund schwer 2, Durchsicht
    # T16): url trägt /v1 bereits selbst (base_url-Form OpenAI-kompatibler Server,
    # http://localhost:11434/v1) — ein zusätzliches /v1 hier ergab .../v1/v1/... und beim
    # echten Server HTTP 404.
    request = urllib.request.Request(
        f"{url.rstrip('/')}/chat/completions",
        data=json.dumps(_request_body(model_name, prompt, option_count)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        # Ein HTTP-Fehler betrifft den Server, nicht dieses Wort.
        raise ValueError(
            f"Modellserver antwortet mit Fehler {error.code}: "
            f"{error.read()[:200].decode('utf-8', 'replace')}"
        ) from error
    except urllib.error.URLError as error:
        raise ValueError(f"Modellserver unter {url} nicht erreichbar: {error}") from error
    except TimeoutError as error:
        # (Befund 3, Review T11): Eine Lesezeitüberschreitung nach dem Verbindungsaufbau
        # kommt als rohes TimeoutError an, nicht als URLError — urllib bettet nur
        # Fehlschläge beim Verbindungsaufbau selbst ein. Dieselbe Einordnung wie oben:
        # eine Störung des Servers oder der Betriebsart, keine Aussage über dieses Wort.
        raise ValueError(
            f"Modellserver unter {url} hat nicht innerhalb von {timeout} s geantwortet."
        ) from error
    except json.JSONDecodeError as error:
        # (Befund 3, Review T11): HTTP 200 mit einem Körper, der kein JSON ist (etwa
        # Ollamas Wurzelseite über einen falsch konfigurierten Proxy) — der Server hat
        # geantwortet, aber nicht mit der zugesagten Schnittstelle.
        raise ValueError(
            f"Antwort des Modellservers unter {url} ist kein gültiges JSON: {error}"
        ) from error
    except (http.client.IncompleteRead, http.client.RemoteDisconnected) as error:
        # (Befund 3, Review T11): Die Verbindung bricht mitten in der Antwort ab — weder
        # ein HTTP-Fehlercode noch fehlende Erreichbarkeit, sondern ein Abriss dazwischen.
        raise ValueError(
            f"Verbindung zum Modellserver unter {url} brach mitten in der Antwort ab: {error}"
        ) from error

    try:
        completion = payload["choices"][0]
        message = completion["message"]
        finish_reason = completion.get("finish_reason")
        content = str(message.get("content") or "").strip()
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(
            f"Antwort des Modellservers hat nicht die erwartete Form: {payload!r}"
        ) from error

    if finish_reason == "length" and not content:
        # Der gemessene Fehlschlag aus technik.md §3, „Zwingende Einstellung: Denkschritt
        # abschalten": reasoning_effort: none wurde nicht befolgt. Status 200 und
        # wohlgeformte choices sehen wie ein Erfolg aus, sind aber keiner.
        raise ValueError(
            'Modellserver hat mit finish_reason "length" und leerem Inhalt geantwortet — '
            "der Denkschritt war vermutlich nicht abgeschaltet (technik.md §3, „Zwingende "
            "Einstellung: Denkschritt abschalten“)."
        )

    try:
        raw_choice = json.loads(content)["choice"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        # Der Server soll die Antwortform per JSON-Schema erzwingen (bauplan.md T11) —
        # eine Antwort, die trotzdem nicht passt, ist ein Vertragsbruch des Servers,
        # keine Aussage über dieses Wort.
        raise ValueError(
            f'Antwort des Modellservers ist kein gültiges JSON mit "choice": {content!r}'
        ) from error

    # (Befund 4, Review T11): int() rundete eine Bruchzahl wie 1.9 still auf 1 ab —
    # derselbe Weltzustand, den die Bereichsprüfung zwei Zeilen weiter unten laut
    # behandelt. Der Typ wird deshalb geprüft statt konvertiert; bool zählt trotz Pythons
    # int-Unterklasse nicht mit, weil ein JSON-Wahrheitswert keine ganze Zahl ist.
    if not isinstance(raw_choice, int) or isinstance(raw_choice, bool):
        raise ValueError(
            f'"choice" in der Antwort des Modellservers ist keine ganze Zahl: {content!r}'
        )
    choice: int = raw_choice

    if not 1 <= choice <= option_count:
        # Das JSON-Schema erzwingt minimum/maximum bereits — eine Nummer außerhalb
        # bedeutet, dass der Server das Schema nicht wirklich durchsetzt.
        raise ValueError(
            f"Modellserver hat Nummer {choice} gewählt, gültig ist nur 1..{option_count}."
        )
    return choice


def choose_sense(
    *,
    url: str,
    model_name: str,
    occurrence: Occurrence,
    sense_candidates: Sequence[Sense],
    timeout: float = DEFAULT_TIMEOUT,
) -> Sense:
    """Wählt für `occurrence` die im Belegsatz gemeinte Bedeutung aus `sense_candidates`
    (bauplan.md T11). Je Wort eine Anfrage, kein Bündeln (technik.md §3, Nachtrag
    19.08.2026).

    Ist `sense_candidates` leer, wird **nicht** angefragt, sondern unmittelbar `uncertain`
    zurückgegeben (Regel 11: „Kandidaten ohne Wörterbucheintrag werden uncertain
    markiert"). Ein zweiter Versuch ohne Wortartfilter ist bewusst nicht gebaut: Der
    Anteil betroffener Grundformen ist mit 3,3 % gemessen, die Wirkung des Filters auf
    lange Auswahllisten aber nicht — das misst erst T18 (technik.md §3, offener Punkt
    „Die Wortart als Filter"). Regel 14 verbietet den Mechanismus ohne gemessenen Anlass;
    der offene Punkt bleibt hier als Verweis stehen, nicht als Code.
    """
    if not sense_candidates:
        return Sense(lemma=occurrence.lemma, uncertain=True)

    prompt = _build_prompt(occurrence, sense_candidates)
    estimated_tokens = _estimate_prompt_tokens(prompt)
    if estimated_tokens > _MAX_ESTIMATED_PROMPT_TOKENS:
        # Abbruch, nicht uncertain: Ein zu langer Prompt würde der Server still auf rund
        # 2.050 Token kürzen und dabei den gekürzten Wert als korrekt melden (technik.md
        # §3, s. o.) — die Auswahl des Modells stünde dann auf einer unvollständigen
        # Liste, ohne dass das im Ergebnis sichtbar würde. Die Ursache ist eine zu lange
        # Auswahlliste (z. B. `run` mit 48 Bedeutungen ohne Wortartfilter), kein Merkmal
        # dieses einen Wortes — als uncertain markiert, wäre sie von einer echten
        # Modell-Unsicherheit nicht zu unterscheiden.
        raise ValueError(
            f"Auswahlliste für „{occurrence.word_form}“ zu lang für eine verlässliche "
            f"Anfrage (rund {estimated_tokens} Token geschätzt, mehr als "
            f"{_MAX_ESTIMATED_PROMPT_TOKENS}) — der Server würde sie ohne sichtbaren "
            "Hinweis kürzen (technik.md §3, „Datenfalle: der Server kürzt zu lange "
            "Prompts still“)."
        )

    option_count = len(sense_candidates) + 1
    choice = _ask_model(
        url=url, model_name=model_name, prompt=prompt, option_count=option_count, timeout=timeout
    )

    if choice == option_count:
        # Die Ausweichantwort „keine passt" — kein Fehlschlag, sondern die Meldung einer
        # Störung der Vorstufe (der `saw`-Fall, technik.md §3).
        return Sense(lemma=occurrence.lemma, uncertain=True)

    chosen = sense_candidates[choice - 1]
    # (Befund 2, Review T11): uncertain wird vom gewählten Kandidaten übernommen statt fest
    # auf False gesetzt — sonst verlöre ein Wörterbuch-loser Platzhalter (T7,
    # dictionary.particle_verb_candidates) beim Zusammenbau des Ergebnisses genau die
    # Markierung, die ihn von einer sicheren Bedeutung unterscheidet (Regel 10).
    return Sense(
        lemma=chosen.lemma,
        translation=chosen.wikdict_trans_list,
        wikdict_sense=chosen.wikdict_sense,
        wikdict_trans_list=chosen.wikdict_trans_list,
        wikdict_lexentry=chosen.wikdict_lexentry,
        uncertain=chosen.uncertain,
    )
