"""Cognitive Gate — Mandatory pre-execution deliberation layer for all agents.

Every agent MUST call CognitiveGate.deliberate() before executing any task.
The gate runs a six-question self-interrogation and returns a DecisionTrace.
If confidence < 0.5 or intent is unclear, should_proceed is False and the
agent must clarify before acting.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass
class DecisionTrace:
    """Complete record of an agent's deliberation before task execution."""

    task_hash: str
    timestamp: str
    intent: str
    options: list[str]
    selected_option: str
    risks: list[str]
    success_condition: str
    self_challenge: str
    should_proceed: bool
    confidence: float  # 0.0 – 1.0
    rationale: str
    complexity: str = "moderate"  # simple | moderate | complex
    flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Keyword Heuristics
# ---------------------------------------------------------------------------

_HIGH_RISK_PATTERNS = re.compile(
    r"\b(delete|drop|rm\s+-rf|format|wipe|destroy|kill|shutdown|overwrite"
    r"|truncate|purge|nuke|remove\s+all)\b",
    re.IGNORECASE,
)
_IRREVERSIBLE_PATTERNS = re.compile(
    r"\b(commit\s+to\s+main|merge\s+to\s+main|push\s+--force"
    r"|deploy\s+to\s+production|migrate\s+database)\b",
    re.IGNORECASE,
)
_AMBIGUOUS_PATTERNS = re.compile(
    r"\b(it|this|that|them|those|something|stuff|thing|fix\s+it"
    r"|make\s+it\s+work|handle\s+it)\b",
    re.IGNORECASE,
)
_COMPLEX_PATTERNS = re.compile(
    r"\b(integrate|refactor|migrate|architect|design|pipeline"
    r"|orchestrate|coordinate|multi|parallel|distributed)\b",
    re.IGNORECASE,
)
_SIMPLE_PATTERNS = re.compile(
    r"\b(list|show|get|read|print|check|status|version|help|ping)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# CognitiveGate
# ---------------------------------------------------------------------------


class CognitiveGate:
    """Mandatory deliberation gate — agents call this before any execution.

    Usage::

        gate = CognitiveGate(agent_id="neo")
        trace = gate.deliberate(task="Refactor the neural bus", context={})
        if not trace.should_proceed:
            # emit STATE_UPDATE with trace.rationale and halt
            return
        # proceed with execution
    """

    def __init__(self, agent_id: str = "unknown") -> None:
        self.agent_id = agent_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deliberate(self, task: str, context: dict[str, Any] | None = None) -> DecisionTrace:
        """Run the six-question self-interrogation and return a DecisionTrace.

        Questions answered internally:
        1. What is actually being asked? (intent)
        2. What are all possible approaches? (options)
        3. What is the best approach and why? (selected + rationale)
        4. What could go wrong? (risks)
        5. What does success look like? (success_condition)
        6. Is there a better way I haven't considered? (self_challenge)
        """
        ctx = context or {}
        task = task.strip()

        task_hash = hashlib.sha256(f"{self.agent_id}:{task}".encode()).hexdigest()[:16]
        timestamp = datetime.now(timezone.utc).isoformat()

        # Q1 — Intent
        intent, is_ambiguous = self._parse_intent(task, ctx)

        # Q2 — Options
        options = self._generate_options(task, ctx)

        # Q3 — Selected + rationale
        selected, rationale = self._select_option(options, task, ctx)

        # Q4 — Risks
        risks, has_high_risk = self._assess_risks(task, ctx)

        # Q5 — Success condition
        success_condition = self._define_success(task, intent, ctx)

        # Q6 — Self-challenge
        self_challenge = self._self_challenge(task, selected, risks)

        # Complexity
        complexity = self._assess_complexity(task)

        # Confidence & proceed flag
        confidence, flags = self._score_confidence(
            is_ambiguous=is_ambiguous,
            has_high_risk=has_high_risk,
            task_empty=not task,
            options_count=len(options),
            complexity=complexity,
        )
        should_proceed = confidence >= 0.5 and not is_ambiguous and bool(task) and not has_high_risk

        return DecisionTrace(
            task_hash=task_hash,
            timestamp=timestamp,
            intent=intent,
            options=options,
            selected_option=selected,
            risks=risks,
            success_condition=success_condition,
            self_challenge=self_challenge,
            should_proceed=should_proceed,
            confidence=confidence,
            rationale=rationale,
            complexity=complexity,
            flags=flags,
        )

    # ------------------------------------------------------------------
    # Private helpers — Q1 Intent
    # ------------------------------------------------------------------

    def _parse_intent(self, task: str, ctx: dict[str, Any]) -> tuple[str, bool]:
        if not task:
            return "No task provided — intent is unknown.", True

        is_ambiguous = bool(_AMBIGUOUS_PATTERNS.search(task))

        # Try to extract a verb-object pair as intent summary
        verb_match = re.match(r"^\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(.+?)[\.\?!]?\s*$", task)
        if verb_match:
            action, subject = verb_match.group(1), verb_match.group(2)
            intent = f"Perform '{action}' on '{subject[:80]}'"
        else:
            intent = f"Execute task: '{task[:120]}'"

        if is_ambiguous:
            intent += " [WARNING: ambiguous pronouns detected — clarification needed]"

        return intent, is_ambiguous

    # ------------------------------------------------------------------
    # Private helpers — Q2 Options
    # ------------------------------------------------------------------

    def _generate_options(self, task: str, ctx: dict[str, Any]) -> list[str]:
        options: list[str] = []
        task_lower = task.lower()

        options.append("Direct execution: implement the task as literally described.")

        if "test" in task_lower or "verify" in task_lower:
            options.append("Test-first: write tests before implementation.")

        if _COMPLEX_PATTERNS.search(task):
            options.append("Incremental: break into sub-tasks and execute sequentially.")
            options.append("Parallel: split independent sub-tasks across workers.")

        if "refactor" in task_lower or "improve" in task_lower:
            options.append("Audit first: read existing code, then refactor with full context.")

        if not options or len(options) == 1:
            options.append("Clarify first: ask for more context before executing.")

        return options

    # ------------------------------------------------------------------
    # Private helpers — Q3 Selection
    # ------------------------------------------------------------------

    def _select_option(self, options: list[str], task: str, ctx: dict[str, Any]) -> tuple[str, str]:
        if not options:
            return "No viable option identified.", "Task cannot be executed safely."

        task_lower = task.lower()

        # Prefer test-first for test tasks
        for opt in options:
            if "test-first" in opt.lower() and "test" in task_lower:
                return opt, "Test-first approach ensures correctness before implementation."

        # Prefer audit for refactors
        for opt in options:
            if "audit first" in opt.lower() and (
                "refactor" in task_lower or "improve" in task_lower
            ):
                return opt, "Reading existing code first prevents regressions."

        # Prefer incremental for complex tasks
        for opt in options:
            if "incremental" in opt.lower() and _COMPLEX_PATTERNS.search(task):
                return opt, "Complex tasks benefit from incremental delivery with checkpoints."

        # Default: direct execution
        return options[0], "Direct execution is appropriate for this task's scope."

    # ------------------------------------------------------------------
    # Private helpers — Q4 Risks
    # ------------------------------------------------------------------

    def _assess_risks(self, task: str, ctx: dict[str, Any]) -> tuple[list[str], bool]:
        risks: list[str] = []
        has_high_risk = False

        if _HIGH_RISK_PATTERNS.search(task):
            risks.append("HIGH: Destructive operation detected — data loss possible.")
            has_high_risk = True

        if _IRREVERSIBLE_PATTERNS.search(task):
            risks.append("HIGH: Irreversible operation detected — requires explicit approval.")
            has_high_risk = True

        if _AMBIGUOUS_PATTERNS.search(task):
            risks.append("MEDIUM: Ambiguous task description — misinterpretation risk.")

        if _COMPLEX_PATTERNS.search(task):
            risks.append("MEDIUM: Complex task — partial completion may leave system inconsistent.")

        if not risks:
            risks.append("LOW: No significant risks detected for this task.")

        return risks, has_high_risk

    # ------------------------------------------------------------------
    # Private helpers — Q5 Success condition
    # ------------------------------------------------------------------

    def _define_success(self, task: str, intent: str, ctx: dict[str, Any]) -> str:
        task_lower = task.lower()

        if "test" in task_lower:
            return "All tests pass with no failures or errors."
        if "commit" in task_lower or "push" in task_lower:
            return "Commit exists on the target branch and quality gates pass."
        if "refactor" in task_lower:
            return "Refactored code passes all existing tests and quality gates."
        if "install" in task_lower or "add" in task_lower:
            return "The component is installed, importable, and functional."
        if "delete" in task_lower or "remove" in task_lower:
            return "Target is removed, system remains functional, no regressions."
        if "read" in task_lower or "list" in task_lower or "show" in task_lower:
            return "Accurate information is returned without side effects."

        return (
            "The task is completed as described, verified by observable output "
            "and no degradation to existing functionality."
        )

    # ------------------------------------------------------------------
    # Private helpers — Q6 Self-challenge
    # ------------------------------------------------------------------

    def _self_challenge(self, task: str, selected: str, risks: list[str]) -> str:
        challenges = []

        if any("HIGH" in r for r in risks):
            challenges.append(
                "Have I considered a safer, reversible alternative before proceeding?"
            )
        if "direct execution" in selected.lower():
            challenges.append(
                "Would a test-first or incremental approach yield better results here?"
            )
        if _COMPLEX_PATTERNS.search(task):
            challenges.append(
                "Can I decompose this further to reduce the blast radius of any failure?"
            )

        if not challenges:
            challenges.append(
                "Is there domain expertise or a reference implementation I should consult first?"
            )

        return " | ".join(challenges)

    # ------------------------------------------------------------------
    # Private helpers — Complexity & Confidence
    # ------------------------------------------------------------------

    def _assess_complexity(self, task: str) -> str:
        if _SIMPLE_PATTERNS.search(task) and not _COMPLEX_PATTERNS.search(task):
            return "simple"
        if _COMPLEX_PATTERNS.search(task):
            return "complex"
        return "moderate"

    def _score_confidence(
        self,
        *,
        is_ambiguous: bool,
        has_high_risk: bool,
        task_empty: bool,
        options_count: int,
        complexity: str,
    ) -> tuple[float, list[str]]:
        score = 1.0
        flags: list[str] = []

        if task_empty:
            score -= 0.6
            flags.append("EMPTY_TASK")
        if is_ambiguous:
            score -= 0.35
            flags.append("AMBIGUOUS_INTENT")
        if has_high_risk:
            score -= 0.25
            flags.append("HIGH_RISK_OPERATION")
        if options_count < 2:
            score -= 0.1
            flags.append("LIMITED_OPTIONS")
        if complexity == "complex":
            score -= 0.05
            flags.append("HIGH_COMPLEXITY")

        return round(max(0.0, min(1.0, score)), 2), flags


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    gate = CognitiveGate(agent_id="neo")

    tasks = [
        "Refactor the neural bus to support streaming events",
        "Delete all files in the project",
        "Fix it",
        "",
        "Run pytest and report results",
    ]

    for t in tasks:
        trace = gate.deliberate(t)
        print(f"\nTask: {t!r}")
        print(f"  Intent:    {trace.intent[:80]}")
        print(f"  Proceed:   {trace.should_proceed}  (confidence={trace.confidence})")
        print(f"  Flags:     {trace.flags}")
        print(f"  Risks:     {trace.risks[0]}")
