"""Prüft `cli/model.py` — den Modellnamen auflösen (bauplan.md T16).

Regressionstest zu Befund schwer 2 (Durchsicht T16): `config.toml` trägt `model.url`
bereits mit angehängtem `/v1` (technik.md §9, `http://localhost:11434/v1`), der üblichen
`base_url`-Form OpenAI-kompatibler Server. Ein zusätzliches `/v1` in diesem Modul
verdoppelte den Pfad zu `.../v1/v1/models`, der echte Server antwortete mit HTTP 404, und
`resolve_model_name` fing das als `URLError` und meldete fälschlich „nicht erreichbar" —
ein Konfigurationsfehler sah damit wie ein Netzwerkfehler aus.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING

import pytest

from cli import model

if TYPE_CHECKING:
    from conftest import ModelServerDouble


def test_resolve_model_name_reaches_the_v1_models_endpoint_without_doubling_v1(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund schwer 2, Durchsicht T16: `model_server_double.url` trägt `/v1` bereits,
    wie die dokumentierte Form aus technik.md §9 — `resolve_model_name` darf kein
    zweites `/v1` anhängen, sonst träfe die Anfrage `.../v1/v1/models` und schlüge fehl,
    statt den ersten genannten Modellnamen zu liefern."""
    resolved = model.resolve_model_name(model_server_double.url, "")

    assert resolved == model_server_double.model_name


def test_resolve_model_name_keeps_the_configured_name_without_any_request() -> None:
    """Ist ein Modellname in `config.toml` hinterlegt, fragt `resolve_model_name` den
    Server gar nicht erst — auch nicht bei einer unerreichbaren Adresse."""
    resolved = model.resolve_model_name("http://unerreichbar.invalid", "granite4")

    assert resolved == "granite4"


def test_resolve_model_name_http_error_names_the_address_not_the_network(
    model_server_double: ModelServerDouble,
) -> None:
    """Befund schwer 2, Durchsicht T16: Eine HTTP-Antwort beweist, dass der Server
    erreichbar ist — die Meldung muss auf Adresse oder Modellname zeigen, nicht auf das
    Netzwerk. Hier absichtlich ohne das `/v1`-Suffix aufgerufen: `/models` trifft dann
    keinen der beiden von `_ModelServerHandler` beantworteten Pfade und liefert HTTP 404
    — genau der Fall, den das doppelte `/v1` beim echten Server auslöste."""
    url_without_v1 = model_server_double.url.removesuffix("/v1")

    with pytest.raises(ValueError) as excinfo:
        model.resolve_model_name(url_without_v1, "")

    message = str(excinfo.value)
    assert "404" in message
    assert "nicht erreichbar" not in message


def test_resolve_model_name_unreachable_server_says_nicht_erreichbar() -> None:
    """Regel 13 (dokumentation.md §4): Ein echter Netzwerkfehlschlag — kein Server am
    Port — bleibt bei der Meldung „nicht erreichbar", anders als der HTTP-Fehlschlag
    oben. Beide dürfen nicht zur selben Meldung führen (Befund schwer 2, Durchsicht
    T16), sonst verwechselte ein falsch konfiguriertes `model.url` sich mit einem echten
    Netzwerkausfall."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]

    with pytest.raises(ValueError) as excinfo:
        model.resolve_model_name(f"http://127.0.0.1:{unused_port}/v1", "")

    assert "nicht erreichbar" in str(excinfo.value)
