"""C6 security scenarios: router gates + commander token auth (no live bus needed)."""

import json
import time
from typing import Any

import pytest

from agents.base_agent import MatrixAgent
from core.models import EventPayload, EventType
from core.neural_bus import (
    FLOOD_MAX_MSGS,
    MAX_FRAME_BYTES,
    NeuralBusRouter,
)


class _StubClient:
    """Minimal stand-in for NeuralBusClient.send (captures alerts)."""

    def __init__(self) -> None:
        self.sent: list[EventPayload] = []

    async def send(self, event: EventPayload) -> None:
        self.sent.append(event)


def _agent(name: str = "neo") -> MatrixAgent:
    agent = MatrixAgent.__new__(MatrixAgent)
    agent.name = name
    agent.client = _StubClient()  # type: ignore[attr-defined]
    agent._unauth_alert_at = {}  # type: ignore[attr-defined]
    return agent


def _payload(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "target_agent": "neo",
        "message": "ping",
        "nonce": "n" * 32,
        "timestamp": time.time(),
    }
    base.update(kw)
    return base


def _frame(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _command_event(source: str = "Commander_UI", **payload_kw: Any) -> EventPayload:
    return EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id=source,
        correlation_id="sec-test",
        payload=_payload(**payload_kw),
    )


# --- Router gates (pure unit, no sockets) ---


def test_router_rejects_unsigned_frame() -> None:
    router = NeuralBusRouter.__new__(NeuralBusRouter)
    assert router._valid_signature(b"fakesignature", _frame(_payload())) is False


def test_router_rejects_oversized_frame() -> None:
    router = NeuralBusRouter.__new__(NeuralBusRouter)
    assert router._acceptable_size(b"x" * (MAX_FRAME_BYTES + 1)) is False
    assert router._acceptable_size(b"x" * 64) is True


def test_router_rejects_stale_frame() -> None:
    router = NeuralBusRouter.__new__(NeuralBusRouter)
    stale = _frame(_payload(timestamp=time.time() - 600))
    assert router._fresh_enough(stale) is False
    assert router._fresh_enough(_frame(_payload())) is True


def test_router_rejects_malformed_frame() -> None:
    router = NeuralBusRouter.__new__(NeuralBusRouter)
    assert router._fresh_enough(b"not-json{{{") is False


def test_router_flood_guard_mutes_burster() -> None:
    router = NeuralBusRouter.__new__(NeuralBusRouter)
    router._sender_hits = {}
    router._sender_muted_until = {}
    sender = b"burster"
    for _ in range(FLOOD_MAX_MSGS):
        assert router._flood_ok(sender) is True
    assert router._flood_ok(sender) is False  # muted
    assert router._flood_ok(sender) is False  # still muted


# --- Passwordless commander auth (whitelist on signed localhost bus) ---


@pytest.mark.asyncio
async def test_commander_whitelisted_name_accepts_without_token() -> None:
    agent = _agent()
    assert await agent._validate_commander(_command_event()) is True
    assert await agent._validate_commander(_command_event(source="dr-anas-hilal")) is True


@pytest.mark.asyncio
async def test_commander_intruder_rejected(caplog: pytest.LogCaptureFixture) -> None:
    agent = _agent()
    with caplog.at_level("CRITICAL"):
        assert await agent._validate_commander(_command_event(source="intruder")) is False
    assert "UNAUTHORIZED" in caplog.text


@pytest.mark.asyncio
async def test_commander_rejection_rate_limited(caplog: pytest.LogCaptureFixture) -> None:
    agent = _agent()
    with caplog.at_level("CRITICAL"):
        assert await agent._validate_commander(_command_event(source="scanner")) is False
        assert await agent._validate_commander(_command_event(source="scanner")) is False
    assert caplog.text.count("UNAUTHORIZED") == 1
