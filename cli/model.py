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

Liefert
-------
`resolve_model_name` den konfigurierten Namen unverändert, wenn er nicht leer ist —
sonst den ersten von `{url}/v1/models` genannten. Bricht sichtbar ab (Regel 13), wenn der
Server unter `url` nicht antwortet oder keine Modelle nennt, statt eines leeren
Modellnamens, an dem der nachfolgende Aufruf erst unverständlich scheitern würde.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

_TIMEOUT = 10.0


def resolve_model_name(url: str, configured_name: str) -> str:
    """Liefert `configured_name`, wenn er nicht leer ist — sonst das erste Modell, das
    `{url}/v1/models` nennt (technik.md §9, Tabelle „Einstellungen: config.toml",
    Spalte `model.name`)."""
    if configured_name:
        return configured_name

    request = urllib.request.Request(f"{url.rstrip('/')}/v1/models")
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            payload = json.load(response)
    except urllib.error.URLError as error:
        raise ValueError(
            f"Modellserver unter {url} nicht erreichbar, um den Modellnamen zu bestimmen: {error}"
        ) from error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Modellserver unter {url} hat auf /v1/models nicht mit gültigem JSON "
            f"geantwortet: {error}"
        ) from error

    models = payload.get("data") or []
    if not models:
        raise ValueError(f"Modellserver unter {url} nennt kein Modell (/v1/models ist leer).")

    model_id = models[0].get("id")
    if not model_id:
        raise ValueError(f'Modellserver unter {url}: erstes Modell in /v1/models ohne „id".')
    return str(model_id)


def cached_resolver(url: str, configured_name: str) -> Callable[[], str]:
    """Liefert eine Funktion, die `resolve_model_name` erst bei ihrem ersten Aufruf
    ausführt und das Ergebnis danach unverändert zurückgibt.

    Eine Triage-Sitzung, in der nie „will ich lernen" gewählt wird, braucht den
    Modellserver nie — `cli.interaction.run_triage_pass` bekommt diese Funktion
    trotzdem immer übergeben und ruft sie nur dort auf, wo eine Karte entsteht. Kein
    Zwischenspeicher über einen Lauf hinaus (dokumentation.md §4 Regel 14): Die Liste
    lebt nur in dieser einen Closure.
    """
    cache: list[str] = []

    def _get() -> str:
        if not cache:
            cache.append(resolve_model_name(url, configured_name))
        return cache[0]

    return _get
