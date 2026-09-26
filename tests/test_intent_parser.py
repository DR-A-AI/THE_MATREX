"""Tests for core/intent_parser.py — structured intent extraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.intent_parser import Intent, IntentParser


@pytest.fixture(autouse=True)
def disable_ollama():
    with patch("core.intent_parser.get_router") as mock_router:
        router = MagicMock()
        router.chat.side_effect = Exception("Offline")
        mock_router.return_value = router
        yield


@pytest.fixture
def parser() -> IntentParser:
    return IntentParser()


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_parse_returns_intent(parser: IntentParser) -> None:
    intent = parser.parse("Run the test suite")
    assert isinstance(intent, Intent)
    assert intent.raw == "Run the test suite"
    assert intent.literal
    assert intent.inferred
    assert intent.success_condition
    assert intent.complexity in ("simple", "moderate", "complex")
    assert 0.0 <= intent.confidence <= 1.0
    assert intent.source in ("ollama", "rule_based")


def test_empty_task_returns_low_confidence(parser: IntentParser) -> None:
    intent = parser.parse("")
    assert intent.confidence == 0.0
    assert "empty" in intent.inferred.lower() or "no task" in intent.inferred.lower()


# ---------------------------------------------------------------------------
# Complexity detection
# ---------------------------------------------------------------------------


def test_simple_task_complexity(parser: IntentParser) -> None:
    intent = parser.parse("List all agents")
    assert intent.complexity == "simple"


def test_complex_task_complexity(parser: IntentParser) -> None:
    intent = parser.parse("Integrate the Ollama router with the neural bus pipeline")
    assert intent.complexity == "complex"


def test_moderate_task_complexity(parser: IntentParser) -> None:
    intent = parser.parse("Write a function to validate API keys")
    assert intent.complexity == "moderate"


# ---------------------------------------------------------------------------
# Confidence reduction for ambiguous tasks
# ---------------------------------------------------------------------------


def test_ambiguous_task_lower_confidence(parser: IntentParser) -> None:
    clear = parser.parse("Audit all crawler services")
    ambiguous = parser.parse("Fix it and make this thing work")
    assert ambiguous.confidence < clear.confidence


# ---------------------------------------------------------------------------
# Success condition mapping
# ---------------------------------------------------------------------------


def test_test_task_success_condition(parser: IntentParser) -> None:
    intent = parser.parse("Run the pytest test suite")
    assert "test" in intent.success_condition.lower() or "pass" in intent.success_condition.lower()


def test_commit_task_success_condition(parser: IntentParser) -> None:
    intent = parser.parse("Commit the changes to the feature branch")
    lower = intent.success_condition.lower()
    assert "commit" in lower or "branch" in lower or "quality" in lower


def test_refactor_task_success_condition(parser: IntentParser) -> None:
    intent = parser.parse("Refactor the memory manager for async IO")
    lower = intent.success_condition.lower()
    assert "test" in lower or "refactor" in lower or "regression" in lower


# ---------------------------------------------------------------------------
# Ollama fallback — no OLLAMA_HOST set in test env
# ---------------------------------------------------------------------------


def test_falls_back_to_rule_based_without_ollama(
    parser: IntentParser, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    intent = parser.parse("Integrate the skill loader with the neural bus")
    assert intent.source == "rule_based"


# ---------------------------------------------------------------------------
# Literal vs inferred distinction
# ---------------------------------------------------------------------------


def test_literal_preserves_request(parser: IntentParser) -> None:
    raw = "Please refactor the neural bus module"
    intent = parser.parse(raw)
    # literal should not contain filler phrases
    assert "please" not in intent.literal.lower() or len(intent.literal) < len(raw)


def test_inferred_adds_context(parser: IntentParser) -> None:
    intent = parser.parse("Read the AGENTS.md file")
    assert intent.inferred  # must not be empty


# ---------------------------------------------------------------------------
# Semantic Router & Dynamic Tool Pruning Tests (Bilingual)
# ---------------------------------------------------------------------------


def test_semantic_routing_general_chat(parser: IntentParser) -> None:
    for phrase in ["Hello", "Are you online?", "مرحبا", "من أنت", "How are you"]:
        intent = parser.parse(phrase)
        assert intent.route == "general_chat"
        # Zero-tool pruning guarantee for general chat
        assert intent.selected_tools == []


def test_semantic_routing_system_ops(parser: IntentParser) -> None:
    intent_en = parser.parse("Please run command echo hello in terminal")
    assert intent_en.route == "system_ops"
    assert "run_local_command" in intent_en.selected_tools

    intent_ar = parser.parse("نفذ أمر في الشل")
    assert intent_ar.route == "system_ops"
    assert "run_local_command" in intent_ar.selected_tools


def test_semantic_routing_file_ops(parser: IntentParser) -> None:
    intent_en = parser.parse("Read file AGENTS.md and search code for ZMQ")
    assert intent_en.route == "file_ops"
    assert "read_local_file" in intent_en.selected_tools

    intent_ar = parser.parse("اقرأ ملف الكود وابحث في المجلد")
    assert intent_ar.route == "file_ops"
    assert "read_local_file" in intent_ar.selected_tools


def test_semantic_routing_web_vision_ops(parser: IntentParser) -> None:
    intent_en = parser.parse("Open browser to view the dashboard")
    assert intent_en.route == "web_vision_ops"
    assert "open_browser" in intent_en.selected_tools

    intent_ar = parser.parse("شاهد الشاشة وخذ لقطة سريعة")
    assert intent_ar.route == "web_vision_ops"
    assert "capture_screen" in intent_ar.selected_tools


def test_semantic_routing_dev_mcp_ops(parser: IntentParser) -> None:
    intent = parser.parse("Execute task using the mcp server tool")
    assert intent.route in ("dev_mcp_ops", "system_ops")
    assert any(t in intent.selected_tools for t in ("execute_command", "run_local_command"))


# ---------------------------------------------------------------------------
# Status / readiness routing (AR/EN) — deterministic telemetry path
# ---------------------------------------------------------------------------


def test_status_readiness_routing_arabic(parser: IntentParser) -> None:
    for phrase in [
        "جاهز؟",
        "هل أنت جاهز؟",
        "انت جاهز",
        "مستعد؟",
        "ما هي حالة النظام؟",
        "هل الباص يعمل؟",
        "فحص الحالة",
    ]:
        intent = parser.parse(phrase)
        assert intent.route == "status_readiness", phrase
        assert intent.selected_tools == []


def test_status_readiness_routing_english(parser: IntentParser) -> None:
    for phrase in [
        "are you ready?",
        "system status",
        "health check",
        "ping",
        "is the system online?",
        "report status",
    ]:
        intent = parser.parse(phrase)
        assert intent.route == "status_readiness", phrase
        assert intent.selected_tools == []


def test_general_chat_tie_winners_unchanged(parser: IntentParser) -> None:
    """Pre-existing general_chat utterances must keep winning ties."""
    for phrase in ["Hello", "Are you online?", "مرحبا", "من أنت", "How are you"]:
        intent = parser.parse(phrase)
        assert intent.route == "general_chat", phrase


def test_status_telemetry_reply_has_no_banned_phrases() -> None:
    """Telemetry-grounded replies must never contain canned disclaimers."""
    from core.status_telemetry import (
        BANNED_PHRASES,
        build_status_reply,
        contains_banned_phrase,
    )

    telemetry = {
        "bus": {"endpoint": "127.0.0.1:5555", "online": True},
        "ollama": {"endpoint": "http://127.0.0.1:11434", "online": True, "version": "0.34.4"},
        "bridge": {"endpoint": "127.0.0.1:8000", "online": True},
        "dashboard": {"endpoint": "127.0.0.1:5173", "online": False},
    }
    for lang in ("ar", "en"):
        reply = build_status_reply(telemetry, lang)
        assert contains_banned_phrase(reply) is None
        for banned in BANNED_PHRASES:
            assert banned not in reply.lower()
