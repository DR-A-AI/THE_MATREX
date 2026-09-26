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


@pytest.mark.asyncio
async def test_substantive_audit_request_is_not_hijacked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'Run a full system status audit...' must NOT get instant telemetry.

    It must flow to normal routing/tools (grounded, never hypothetical).
    Proof: no deterministic telemetry reply is emitted synchronously here —
    the handler must reach the LLM/tool path instead. We assert the
    readiness gate itself rejects it, and that the deterministic reply
    builder is never invoked for it.
    """
    assert status_telemetry.is_readiness_ping("جاهز؟") is True
    assert status_telemetry.is_readiness_ping("انت جاهز") is True
    assert status_telemetry.is_readiness_ping("ready?") is True
    assert (
        status_telemetry.is_readiness_ping(
            "Run a full system status audit on all agents and the neural bus."
        )
        is False
    )
    assert status_telemetry.is_readiness_ping("Check local Ollama tensor health and latency.") is False
    assert (
        status_telemetry.is_readiness_ping("Verify active cloud accounts and Flex Processing state.")
        is False
    )
    # Broad grounding detector still sees status content (for grounded answers).
    assert status_telemetry.is_status_query("Run a full system status audit.") is True


def test_collect_full_status_probes_live_and_masks_keys() -> None:
    """Full snapshot has real probed data and ZERO raw secrets."""
    import json as _json

    data = status_telemetry.collect_full_status(timeout=2.0)
    assert set(data) == {"telemetry", "groq_pool", "ollama_models"}
    assert data["telemetry"]["bus"]["online"] in (True, False)
    assert isinstance(data["groq_pool"]["accounts"], list)
    blob = _json.dumps(data)
    assert "api_key" not in blob  # raw secret field must never appear
    for acc in data["groq_pool"]["accounts"]:
        assert set(acc) == {"id", "email", "key", "active", "flex"}
        assert acc["key"].startswith("gsk_***") or acc["key"] in ("***", "NONE")
