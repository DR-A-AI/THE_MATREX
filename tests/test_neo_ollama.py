"""Tests for NeoAgent's Ollama inference integration and graceful fallback.

Validates the complete_with_ollama wiring, user command routing,
fallback when offline, and strict shell=False enforcement.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

from agents.neo_agent import NeoAgent
from core.models import EventPayload, EventType
from services.ollama_client import (
    OllamaClient,
    get_router,
)


@pytest.fixture(autouse=True)
def _no_commander_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the name-whitelist fallback: base_agent.load_dotenv() would
    otherwise pull the real COMMANDER_AUTH_TOKEN into the test env and force
    the token path (covered explicitly in test_bus_security.py)."""
    monkeypatch.delenv("COMMANDER_AUTH_TOKEN", raising=False)


class TransportEndpoint:
    """Standard HTTP transport for testing NeoAgent's Ollama chat integration."""

    def __init__(self, response_text: str = "MATRIX_ONLINE") -> None:
        self.response_text = response_text
        self.calls: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Any,
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        self.calls.append((method, url))
        if url.endswith("/api/tags"):
            return (
                200,
                b'{"models": [{"name": "llama3.2:latest", "aliases": ["llama3.2"]}]}',
            )
        if url.endswith("/api/chat"):
            return (
                200,
                f'{{"model": "llama3.2", "message": {{"role": "assistant", "content": "{self.response_text}"}}, "done": true}}'.encode(),
            )
        return 200, b'{"status": "ok"}'


@pytest.mark.asyncio
async def test_neo_user_command_routes_to_ollama_when_configured() -> None:
    """Verify _handle_user_command executes Ollama inference when OLLAMA_HOST is set."""
    transport = TransportEndpoint(response_text="Sovereign confirmation from llama3.2")
    client = OllamaClient(base_url="http://127.0.0.1:11434", transport=transport)
    get_router(client=client, reset=True)

    sent_events: list[EventPayload] = []

    class CapturingClient:
        async def send(self, event: EventPayload) -> None:
            sent_events.append(event)

    neo = NeoAgent(name="neo", bus_url="tcp://127.0.0.1:5555")
    neo.client = CapturingClient()  # type: ignore[assignment]

    # NOTE: status/readiness questions are answered deterministically from live
    # telemetry and never reach the LLM, so this routing test uses a plain
    # coding request to exercise the Ollama path.
    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "neo", "message": "Write a short sovereign greeting rhyme"},
    )

    old_env = os.environ.get("OLLAMA_HOST")
    try:
        os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
        await neo._handle_user_command(event)
    finally:
        if old_env is not None:
            os.environ["OLLAMA_HOST"] = old_env
        else:
            os.environ.pop("OLLAMA_HOST", None)

    assert any(
        e.event_type == EventType.STATE_UPDATE
        and "Sovereign confirmation from llama3.2" in str(e.payload.get("message", ""))
        for e in sent_events
    )


def test_neo_agent_has_no_shell_true() -> None:
    """Ensure shell=True is never used in neo_agent.py."""
    neo_path = os.path.join(os.path.dirname(__file__), "..", "agents", "neo_agent.py")
    with open(neo_path, encoding="utf-8") as f:
        content = f.read()
    assert "shell=True" not in content


# ---------------------------------------------------------------------------
# Deterministic status / correction path (anti-hallucination)
# ---------------------------------------------------------------------------

from core import status_telemetry


def _offline_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force rule-based intent parsing (no live Ollama call) for determinism."""

    def _boom() -> Any:
        raise ConnectionError("telemetry tests run offline")

    monkeypatch.setattr("core.intent_parser.get_router", _boom)


def _fake_telemetry() -> dict[str, Any]:
    return {
        "bus": {"endpoint": "127.0.0.1:5555", "online": True},
        "ollama": {"endpoint": "http://127.0.0.1:11434", "online": True, "version": "0.34.4"},
        "bridge": {"endpoint": "127.0.0.1:8000", "online": True, "status": "online"},
        "dashboard": {"endpoint": "127.0.0.1:5173", "online": True},
    }


def _all_text(sent_events: list[EventPayload]) -> str:
    return "\n".join(str(e.payload.get("message", "")) for e in sent_events)


@pytest.mark.asyncio
async def test_neo_arabic_readiness_returns_live_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'هل أنت جاهز؟' must yield probed telemetry, never a canned disclaimer."""
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
        payload={"target_agent": "neo", "message": "هل أنت جاهز؟"},
    )
    await neo._handle_user_command(event)

    text = _all_text(sent_events)
    assert "الباص" in text  # real telemetry marker (Arabic)
    assert "0.34.4" in text  # probed Ollama version flows through
    for banned in status_telemetry.BANNED_PHRASES:
        assert banned not in text.lower()
    assert any(e.event_type == EventType.TASK_COMPLETED for e in sent_events)


@pytest.mark.asyncio
async def test_neo_english_status_returns_live_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'are you ready?' must yield probed telemetry, never a canned disclaimer."""
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
        payload={"target_agent": "neo", "message": "are you ready?"},
    )
    await neo._handle_user_command(event)

    text = _all_text(sent_events)
    assert "Neural bus" in text
    for banned in status_telemetry.BANNED_PHRASES:
        assert banned not in text.lower()


@pytest.mark.asyncio
async def test_neo_correction_prunes_bad_turn_without_defense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bare correction discards the previous answer and asks for restatement."""
    _offline_router(monkeypatch)

    sent_events: list[EventPayload] = []

    class CapturingClient:
        async def send(self, event: EventPayload) -> None:
            sent_events.append(event)

    neo = NeoAgent(name="neo", bus_url="tcp://127.0.0.1:5555")
    neo.client = CapturingClient()  # type: ignore[assignment]
    neo.chat_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "جاهز؟"},
        {"role": "assistant", "content": "BAD STALE ANSWER"},
    ]

    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "neo", "message": "لا، خطأ"},
    )
    await neo._handle_user_command(event)

    assert all(m.get("content") != "BAD STALE ANSWER" for m in neo.chat_history)
    text = _all_text(sent_events)
    assert "BAD STALE ANSWER" not in text
    for banned in status_telemetry.BANNED_PHRASES:
        assert banned not in text.lower()


@pytest.mark.asyncio
async def test_neo_correction_with_status_remainder_answers_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'لا، أقصد هل أنت جاهز؟' reinterprets into a telemetry-grounded reply."""
    _offline_router(monkeypatch)
    monkeypatch.setattr(status_telemetry, "collect_live_telemetry", _fake_telemetry)

    sent_events: list[EventPayload] = []

    class CapturingClient:
        async def send(self, event: EventPayload) -> None:
            sent_events.append(event)

    neo = NeoAgent(name="neo", bus_url="tcp://127.0.0.1:5555")
    neo.client = CapturingClient()  # type: ignore[assignment]
    neo.chat_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "جاهز؟"},
        {"role": "assistant", "content": "BAD STALE ANSWER"},
    ]

    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "neo", "message": "لا، أقصد هل أنت جاهز؟"},
    )
    await neo._handle_user_command(event)

    assert all(m.get("content") != "BAD STALE ANSWER" for m in neo.chat_history)
    text = _all_text(sent_events)
    assert "الباص" in text
    for banned in status_telemetry.BANNED_PHRASES:
        assert banned not in text.lower()
