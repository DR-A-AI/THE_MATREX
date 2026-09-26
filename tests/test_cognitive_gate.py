"""Tests for core/cognitive_gate.py — mandatory pre-execution deliberation."""

from __future__ import annotations

import pytest

from core.cognitive_gate import CognitiveGate, DecisionTrace


@pytest.fixture
def gate() -> CognitiveGate:
    return CognitiveGate(agent_id="test_agent")


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_deliberate_returns_decision_trace(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Run the test suite")
    assert isinstance(trace, DecisionTrace)
    assert trace.task_hash
    assert trace.timestamp
    assert trace.intent
    assert isinstance(trace.options, list)
    assert isinstance(trace.risks, list)
    assert isinstance(trace.flags, list)
    assert 0.0 <= trace.confidence <= 1.0


def test_trace_has_all_six_fields(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Refactor the neural bus")
    assert trace.intent
    assert len(trace.options) >= 1
    assert trace.selected_option
    assert len(trace.risks) >= 1
    assert trace.success_condition
    assert trace.self_challenge


# ---------------------------------------------------------------------------
# should_proceed logic
# ---------------------------------------------------------------------------


def test_clear_task_proceeds(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Run pytest and report results")
    assert trace.should_proceed is True
    assert trace.confidence >= 0.5


def test_empty_task_blocked(gate: CognitiveGate) -> None:
    trace = gate.deliberate("")
    assert trace.should_proceed is False
    assert trace.confidence < 0.5
    assert "EMPTY_TASK" in trace.flags


def test_ambiguous_task_blocked(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Fix it and make it work")
    assert trace.should_proceed is False
    assert "AMBIGUOUS_INTENT" in trace.flags


def test_high_risk_task_blocked(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Delete all files in the project directory")
    assert trace.should_proceed is False
    assert "HIGH_RISK_OPERATION" in trace.flags


def test_irreversible_task_blocked(gate: CognitiveGate) -> None:
    trace = gate.deliberate("merge to main and push --force")
    assert trace.should_proceed is False
    assert "HIGH_RISK_OPERATION" in trace.flags


# ---------------------------------------------------------------------------
# Complexity detection
# ---------------------------------------------------------------------------


def test_simple_task_complexity(gate: CognitiveGate) -> None:
    trace = gate.deliberate("List all registered agents")
    assert trace.complexity == "simple"


def test_complex_task_complexity(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Integrate the Ollama model router with the neural bus pipeline")
    assert trace.complexity == "complex"


# ---------------------------------------------------------------------------
# Determinism — same task → same hash
# ---------------------------------------------------------------------------


def test_same_task_same_hash(gate: CognitiveGate) -> None:
    t1 = gate.deliberate("Run pytest")
    t2 = gate.deliberate("Run pytest")
    assert t1.task_hash == t2.task_hash


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


def test_deliberate_accepts_context(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Audit the crawlers", context={"priority": "high"})
    assert isinstance(trace, DecisionTrace)
    assert trace.should_proceed is True


# ---------------------------------------------------------------------------
# Risk content
# ---------------------------------------------------------------------------


def test_safe_task_has_low_risk(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Show git status")
    risk_text = " ".join(trace.risks).upper()
    assert "LOW" in risk_text or "MEDIUM" not in risk_text or "HIGH" not in risk_text


def test_destructive_task_has_high_risk(gate: CognitiveGate) -> None:
    trace = gate.deliberate("Wipe the database")
    risk_text = " ".join(trace.risks)
    assert "HIGH" in risk_text
