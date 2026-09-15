"""Modellname auflösen — die Aufrufer-Pflicht aus `libreverbum.translation`.

Aufgabe
-------
`libreverbum.translation.choose_sense` erwartet einen bereits aufgelösten Modellnamen
(dessen Voraussetzungen-Abschnitt: „Ist in config.toml kein Modellname hinterlegt, ist
das Bestimmen des ersten vom Server genannten Modells Sache des Aufrufers, nicht dieses
Moduls"). Dieses Modul ist dieser Aufrufer.

Voraussetzungen
---------------
`url` ist bereits die fertige, in `config.toml` hinterlegte Adresse (technik.md §9) — hier
wird nur noch **dieser eine** Server nach seinen Modellen gefragt, keine Liste von
Kandidatenadressen durchprobiert. Das ist keine Autosuche im Sinn von technik.md §9,
„Die Autosuche aus tools/ ist ausdrücklich nicht das Vorbild": Dort werden mehrere
Adressen erraten, hier steht die Adresse bereits fest.

`url` trägt das `/v1` bereits selbst (technik.md §9, Tabelle „Einstellungen: config.toml":
`http://localhost:11434/v1`, die übliche `base_url`-Form OpenAI-kompatibler Server) —
dieses Modul hängt deshalb nur noch `/models` an, nicht erneut `/v1/models` (Befund schwer
2, Durchsicht T16: `…/v1/v1/models` beim echten Server ergab HTTP 404, das hier als
`URLError` gefangen wurde und fälschlich „nicht erreichbar“ statt eines Konfigurationsfehlers
meldete).

Liefert
-------
`resolve_model_name` den konfigurierten Namen unverändert, wenn er nicht leer ist —
sonst den ersten von `{url}/models` genannten. Bricht sichtbar ab (Regel 13), wenn der
Server unter `url` nicht antwortet oder keine Modelle nennt, statt eines leeren
Modellnamens, an dem der nachfolgende Aufruf erst unverständlich scheitern würde. Ein
HTTP-Fehlschlag (`HTTPError`) wird dabei **getrennt** von einem Netzwerkfehlschlag
(`URLError`) gemeldet — eine HTTP-Antwort beweist, dass der Server erreichbar ist, und die
Meldung muss auf Adresse oder Modellname zeigen, nicht auf das Netzwerk.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

_TIMEOUT = 10.0


def resolve_model_name(url: str, configured_name: str) -> str:
    """Liefert `configured_name`, wenn er nicht leer ist — sonst das erste Modell, das
    `{url}/models` nennt (technik.md §9, Tabelle „Einstellungen: config.toml",
    Spalte `model.name`; `url` trägt `/v1` bereits selbst, siehe Moduldocstring)."""
    if configured_name:
        return configured_name

    request = urllib.request.Request(f"{url.rstrip('/')}/models")
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        # REGEL (dokumentation.md §4 Regel 13; Befund schwer 2, Durchsicht T16):
        # HTTPError ist eine Unterklasse von URLError — dieser Zweig muss deshalb vor dem
        # allgemeinen URLError-Fang stehen. Eine HTTP-Antwort beweist, dass der Server
        # erreichbar ist; die Meldung zeigt auf Adresse/Modellname, nicht aufs Netzwerk.
        raise ValueError(
            f"Modellserver unter {url} antwortet auf /models mit Fehler {error.code} — "
            "model.url in config.toml prüfen (technik.md §9)."
        ) from error
    except urllib.error.URLError as error:
        raise ValueError(
            f"Modellserver unter {url} nicht erreichbar, um den Modellnamen zu bestimmen: {error}"
        ) from error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Modellserver unter {url} hat auf /models nicht mit gültigem JSON geantwortet: {error}"
        ) from error

    models = payload.get("data") or []
    if not models:
        raise ValueError(f"Modellserver unter {url} nennt kein Modell (/models ist leer).")

    model_id = models[0].get("id")
    if not model_id:
        raise ValueError(f'Modellserver unter {url}: erstes Modell in /models ohne „id".')
    return str(model_id)


def cached_resolver(url: str, configured_name: str) -> Callable[[], str]:
    """Liefert eine Funktion, die `resolve_model_name` erst bei ihrem ersten Aufruf
    ausführt und das Ergebnis danach unverändert zurückgibt.

    Eine Triage-Sitzung, in der jede Grundform laut Profil bereits vollständig bekannt ist
    (`pipeline._all_candidates_known`, der Vorfilter aus `pipeline.resolve_triage_entries`),
    braucht den Modellserver nie — diese Funktion wird trotzdem immer übergeben und erst
    dort aufgerufen, wo `pipeline._resolve_sense` tatsächlich eine Bedeutung auflöst. Seit
    der zweiten T16-Durchsicht (Befund schwer 1) ist das nicht mehr nur „will ich lernen":
    Die Bedeutung wird für jeden verbleibenden Eintrag vor der Triage aufgelöst, auch für
    „kenne ich" und „überspringen" (konzept.md, „Der Kernablauf"). Kein
    Zwischenspeicher über einen Lauf hinaus (dokumentation.md §4 Regel 14): Die Liste lebt
    nur in dieser einen Closure.
    """
    cache: list[str] = []

    def _get() -> str:
        if not cache:
            cache.append(resolve_model_name(url, configured_name))
        return cache[0]

    return _get
