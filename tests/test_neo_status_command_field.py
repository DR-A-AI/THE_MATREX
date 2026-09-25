"""Regression: live UI sends {'command': 'جاهز؟'} (not 'message').

Previously Neo._handle_user_command read only payload['message'], so the live
readiness probe arrived as an empty string, routed to general_chat (score=0.00),
missed the deterministic telemetry intercept, and fell through to free LLM
generation with canned English. This test sends the live-shaped payload
directly and asserts deterministic Arabic telemetry.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from agents.neo_agent import NeoAgent
from core import status_telemetry
from core.models import EventPayload, EventType


@pytest.fixture(autouse=True)
def _no_commander_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Name-whitelist fallback path (token path: test_bus_security.py)."""
    monkeypatch.delenv("COMMANDER_AUTH_TOKEN", raising=False)


def _fake_telemetry() -> dict[str, Any]:
    return {
        "bus": {"endpoint": "127.0.0.1:5555", "online": True},
        "ollama": {"endpoint": "http://127.0.0.1:11434", "online": True, "version": "0.34.4"},
        "bridge": {"endpoint": "127.0.0.1:8000", "online": True, "status": "online"},
        "dashboard": {"endpoint": "127.0.0.1:5173", "online": True},
    }


def _all_text(sent_events: list[EventPayload]) -> str:
    return "\n".join(str(e.payload.get("message", "")) for e in sent_events)


def _offline_router(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> Any:
        raise ConnectionError("telemetry tests run offline")

    monkeypatch.setattr("core.intent_parser.get_router", _boom)


@pytest.mark.asyncio
async def test_command_field_readiness_returns_arabic_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """{'command': 'جاهز؟'} must yield Arabic telemetry, never canned English."""
    _offline_router(monkeypatch)
    monkeypatch.setattr(status_telemetry, "collect_live_telemetry", _fake_telemetry)

    sent_events: list[EventPayload] = []

    class CapturingClient:
        async def send(self, event: EventPayload) -> None:
            sent_events.append(event)

    neo = NeoAgent(name="neo", bus_url="tcp://127.0.0.1:5555")
    neo.client = CapturingClient()  # type: ignore[assignment]

    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "neo", "command": "جاهز؟"},
    )
    await neo._handle_user_command(event)

    text = _all_text(sent_events)
    assert ("الباص" in text or "متصل" in text), f"expected Arabic telemetry, got: {text!r}"
    assert "started again without asking" not in text.lower()
    assert "what's on your mind" not in text.lower()
    for banned in status_telemetry.BANNED_PHRASES:
        assert banned not in text.lower()
    assert any(e.event_type == EventType.TASK_COMPLETED for e in sent_events)
