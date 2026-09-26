"""Decision Logger — Persistent per-agent decision trace store (SQLite).

Every agent logs its DecisionTrace after CognitiveGate.deliberate().
Records persist across restarts and are queryable per agent.

Schema: agent_id, task_hash, timestamp, complexity, confidence,
        should_proceed, flags_json, trace_json
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.cognitive_gate import DecisionTrace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB Path Resolution
# ---------------------------------------------------------------------------

_DB_FILENAME = "decision_log.db"


def _resolve_db_path() -> Path:
    """Resolve the SQLite DB path from env or cwd/memory fallback."""
    root_env = os.getenv("MATRIX_MEMORY_ROOT", "").strip()
    if root_env:
        db_dir = Path(root_env)
    else:
        db_dir = Path.cwd() / "memory"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / _DB_FILENAME


# ---------------------------------------------------------------------------
# DecisionLogger
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS decision_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT    NOT NULL,
    task_hash   TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    complexity  TEXT    NOT NULL,
    confidence  REAL    NOT NULL,
    should_proceed INTEGER NOT NULL,
    flags_json  TEXT    NOT NULL DEFAULT '[]',
    trace_json  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dl_agent ON decision_log (agent_id, timestamp DESC);
"""


class DecisionLogger:
    """Thread-safe SQLite-backed store for agent DecisionTrace records.

    Usage::

        dl = DecisionLogger(agent_id="neo")
        dl.log(trace)
        recent = dl.get_decisions(limit=5)
    """

    def __init__(
        self,
        agent_id: str,
        db_path: Path | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.db_path = db_path or _resolve_db_path()
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(self, trace: DecisionTrace) -> int:
        """Persist a DecisionTrace and return the new row id."""
        row = {
            "agent_id": self.agent_id,
            "task_hash": trace.task_hash,
            "timestamp": trace.timestamp,
            "complexity": trace.complexity,
            "confidence": trace.confidence,
            "should_proceed": int(trace.should_proceed),
            "flags_json": json.dumps(trace.flags),
            "trace_json": self._trace_to_json(trace),
        }
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO decision_log
                    (agent_id, task_hash, timestamp, complexity, confidence,
                     should_proceed, flags_json, trace_json)
                VALUES
                    (:agent_id, :task_hash, :timestamp, :complexity, :confidence,
                     :should_proceed, :flags_json, :trace_json)
                """,
                row,
            )
            conn.commit()
            row_id: int = cur.lastrowid  # type: ignore[assignment]
            logger.debug(
                "[DecisionLogger] %s logged trace %s (id=%d)",
                self.agent_id,
                trace.task_hash,
                row_id,
            )
            return row_id

    def get_decisions(
        self,
        limit: int = 10,
        only_blocked: bool = False,
    ) -> list[dict[str, Any]]:
        """Return the most recent DecisionTrace records for this agent.

        Args:
            limit:        Maximum number of records to return.
            only_blocked: If True, return only traces where should_proceed=False.
        """
        query = """
            SELECT id, task_hash, timestamp, complexity, confidence,
                   should_proceed, flags_json, trace_json
            FROM decision_log
            WHERE agent_id = ?
        """
        params: list[Any] = [self.agent_id]
        if only_blocked:
            query += " AND should_proceed = 0"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        """Return total decision count for this agent."""
        with self._connect() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM decision_log WHERE agent_id = ?",
                (self.agent_id,),
            ).fetchone()
        return int(result[0]) if result else 0

    def average_confidence(self) -> float:
        """Return mean confidence across all logged decisions for this agent."""
        with self._connect() as conn:
            result = conn.execute(
                "SELECT AVG(confidence) FROM decision_log WHERE agent_id = ?",
                (self.agent_id,),
            ).fetchone()
        return round(float(result[0] or 0.0), 3)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)
            conn.commit()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _trace_to_json(trace: DecisionTrace) -> str:
        return json.dumps(
            {
                "task_hash": trace.task_hash,
                "timestamp": trace.timestamp,
                "intent": trace.intent,
                "options": trace.options,
                "selected_option": trace.selected_option,
                "risks": trace.risks,
                "success_condition": trace.success_condition,
                "self_challenge": trace.self_challenge,
                "should_proceed": trace.should_proceed,
                "confidence": trace.confidence,
                "rationale": trace.rationale,
                "complexity": trace.complexity,
                "flags": trace.flags,
            }
        )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["flags"] = json.loads(d.pop("flags_json", "[]"))
        d["trace"] = json.loads(d.pop("trace_json", "{}"))
        d["should_proceed"] = bool(d["should_proceed"])
        return d


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def get_logger(agent_id: str, db_path: Path | None = None) -> DecisionLogger:
    """Return a DecisionLogger for the given agent."""
    return DecisionLogger(agent_id=agent_id, db_path=db_path)


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from core.cognitive_gate import CognitiveGate

    gate = CognitiveGate(agent_id="neo")
    dl = get_logger("neo")

    tasks = [
        "Refactor the neural bus to support streaming events",
        "Delete all files",
        "List registered agents",
    ]
    for t in tasks:
        trace = gate.deliberate(t)
        row_id = dl.log(trace)
        print(
            f"Logged trace {trace.task_hash} (row {row_id}) "
            f"proceed={trace.should_proceed} confidence={trace.confidence}"
        )

    print(f"\nTotal decisions: {dl.count()}")
    print(f"Average confidence: {dl.average_confidence()}")
    print("\nBlocked decisions:")
    for rec in dl.get_decisions(only_blocked=True):
        print(f"  {rec['task_hash']} flags={rec['flags']}")
