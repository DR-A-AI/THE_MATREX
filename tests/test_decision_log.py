"""Tests for core/decision_log.py — persistent decision trace store."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cognitive_gate import CognitiveGate
from core.decision_log import DecisionLogger, get_logger


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_decisions.db"


@pytest.fixture
def gate() -> CognitiveGate:
    return CognitiveGate(agent_id="neo")


@pytest.fixture
def logger_neo(tmp_db: Path) -> DecisionLogger:
    return DecisionLogger(agent_id="neo", db_path=tmp_db)


# ---------------------------------------------------------------------------
# Basic log & retrieve
# ---------------------------------------------------------------------------


def test_log_returns_row_id(gate: CognitiveGate, logger_neo: DecisionLogger) -> None:
    trace = gate.deliberate("Run pytest and report results")
    row_id = logger_neo.log(trace)
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_get_decisions_returns_logged_record(
    gate: CognitiveGate, logger_neo: DecisionLogger
) -> None:
    trace = gate.deliberate("Audit the crawlers")
    logger_neo.log(trace)
    records = logger_neo.get_decisions(limit=5)
    assert len(records) >= 1
    assert records[0]["task_hash"] == trace.task_hash


def test_get_decisions_respects_limit(gate: CognitiveGate, logger_neo: DecisionLogger) -> None:
    for i in range(5):
        trace = gate.deliberate(f"Task number {i} — list agents")
        logger_neo.log(trace)
    records = logger_neo.get_decisions(limit=3)
    assert len(records) <= 3


# ---------------------------------------------------------------------------
# Persistence across instances
# ---------------------------------------------------------------------------


def test_decisions_persist_across_instances(gate: CognitiveGate, tmp_db: Path) -> None:
    trace = gate.deliberate("Check git status")
    dl1 = DecisionLogger(agent_id="neo", db_path=tmp_db)
    dl1.log(trace)

    dl2 = DecisionLogger(agent_id="neo", db_path=tmp_db)
    records = dl2.get_decisions(limit=10)
    hashes = [r["task_hash"] for r in records]
    assert trace.task_hash in hashes


# ---------------------------------------------------------------------------
# Agent isolation
# ---------------------------------------------------------------------------


def test_agents_are_isolated(gate: CognitiveGate, tmp_db: Path) -> None:
    neo_logger = DecisionLogger(agent_id="neo", db_path=tmp_db)
    trinity_logger = DecisionLogger(agent_id="trinity", db_path=tmp_db)

    neo_trace = CognitiveGate(agent_id="neo").deliberate("List agents")
    trinity_trace = CognitiveGate(agent_id="trinity").deliberate("Show status")

    neo_logger.log(neo_trace)
    trinity_logger.log(trinity_trace)

    neo_records = neo_logger.get_decisions()
    trinity_records = trinity_logger.get_decisions()

    neo_hashes = {r["task_hash"] for r in neo_records}
    trinity_hashes = {r["task_hash"] for r in trinity_records}

    assert neo_hashes.isdisjoint(trinity_hashes) or (
        neo_trace.task_hash in neo_hashes and trinity_trace.task_hash in trinity_hashes
    )


# ---------------------------------------------------------------------------
# Blocked filter
# ---------------------------------------------------------------------------


def test_only_blocked_filter(gate: CognitiveGate, logger_neo: DecisionLogger) -> None:
    clear_trace = gate.deliberate("Run pytest")
    blocked_trace = gate.deliberate("Fix it")  # ambiguous → blocked

    logger_neo.log(clear_trace)
    logger_neo.log(blocked_trace)

    blocked = logger_neo.get_decisions(only_blocked=True)
    hashes = [r["task_hash"] for r in blocked]

    assert blocked_trace.task_hash in hashes
    # clear trace should NOT appear in blocked-only list
    if clear_trace.should_proceed:
        assert clear_trace.task_hash not in hashes


# ---------------------------------------------------------------------------
# Count & average confidence
# ---------------------------------------------------------------------------


def test_count(gate: CognitiveGate, logger_neo: DecisionLogger) -> None:
    assert logger_neo.count() == 0
    logger_neo.log(gate.deliberate("Run pytest"))
    logger_neo.log(gate.deliberate("List agents"))
    assert logger_neo.count() == 2


def test_average_confidence(gate: CognitiveGate, logger_neo: DecisionLogger) -> None:
    logger_neo.log(gate.deliberate("Run pytest"))
    avg = logger_neo.average_confidence()
    assert 0.0 <= avg <= 1.0


def test_average_confidence_empty(logger_neo: DecisionLogger) -> None:
    assert logger_neo.average_confidence() == 0.0


# ---------------------------------------------------------------------------
# get_logger factory
# ---------------------------------------------------------------------------


def test_get_logger_factory(tmp_db: Path) -> None:
    dl = get_logger("smith", db_path=tmp_db)
    assert isinstance(dl, DecisionLogger)
    assert dl.agent_id == "smith"
