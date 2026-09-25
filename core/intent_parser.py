"""Intent Parser & Semantic Router — Translates raw task strings into structured Intent objects.

Combines declarative semantic routing (inspired by Aurelio AI's semantic-router)
with structured intent extraction:
- literal:           what was literally said
- inferred:          what is actually wanted
- success_condition: how we verify the intent was fulfilled
- complexity:        simple | moderate | complex
- route:             semantic cluster (system_ops, file_ops, web_vision_ops, dev_mcp_ops, general_chat)
- selected_tools:    minimal allowlist of tools pruned dynamically for this route
- route_score:       similarity score (0.0 - 1.0)
- confidence:        0.0 – 1.0
- source:            "ollama" | "rule_based"

When OLLAMA_HOST is set and the Ollama service responds, llama3.2 is used
for intent extraction via a structured prompt. Falls back to rule-based
parsing when Ollama is unavailable or the request is simple.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field

from services.ollama_client import get_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Route:
    """A declarative semantic route mapping intent patterns to specific agent capabilities."""

    name: str
    utterances: list[str]
    tools: list[str]
    threshold: float = 0.20


@dataclass
class Intent:
    """Structured interpretation of a raw task request with dynamic tool routing."""

    raw: str
    literal: str
    inferred: str
    success_condition: str
    complexity: str  # simple | moderate | complex
    confidence: float  # 0.0 – 1.0
    source: str  # "ollama" | "rule_based"
    route: str = "general_chat"
    selected_tools: list[str] = field(default_factory=list)
    route_score: float = 0.0


# ---------------------------------------------------------------------------
# Pre-configured Semantic Routes (Bilingual: Arabic / English)
# ---------------------------------------------------------------------------

_DEFAULT_ROUTES: list[Route] = [
    Route(
        name="system_ops",
        utterances=[
            "run command",
            "execute command",
            "run shell",
            "bash",
            "terminal",
            "cli",
            "cmd",
            "powershell",
            "echo",
            "execute script",
            "run local",
            "شغل أمر",
            "نفذ أمر",
            "تشغيل كود في الشل",
            "طرفية",
            "سطر الأوامر",
            "نفذ في التيرمينال",
            "شغل السكربت",
        ],
        tools=["run_local_command", "execute_command"],
        threshold=0.20,
    ),
    Route(
        name="file_ops",
        utterances=[
            "read file",
            "view file",
            "write file",
            "edit file",
            "create file",
            "save file",
            "list directory",
            "search code",
            "grep",
            "find files",
            "read lines",
            "modify file",
            "اقرأ ملف",
            "عرض ملف",
            "اكتب في ملف",
            "عدل الملف",
            "أنشئ ملف",
            "قائمة المجلد",
            "ابحث في الكود",
            "تعديل الكود",
            "استعرض الملفات",
        ],
        tools=[
            "read_local_file",
            "write_local_file",
            "edit_local_file",
            "list_local_dir",
            "search_local_code",
        ],
        threshold=0.20,
    ),
    Route(
        name="web_vision_ops",
        utterances=[
            "open browser",
            "visit website",
            "open url",
            "web page",
            "capture screen",
            "take screenshot",
            "see screen",
            "show screen",
            "click",
            "type text",
            "افتح المتصفح",
            "افتح الرابط",
            "شاهد الشاشة",
            "خذ لقطة شاشة",
            "صور الشاشة",
            "تصفح الموقع",
            "انقر",
        ],
        tools=["open_browser", "capture_screen", "safe_click", "safe_type_text"],
        threshold=0.20,
    ),
    Route(
        name="dev_mcp_ops",
        utterances=[
            "mcp",
            "mcp tool",
            "mcp server",
            "matrix_shell",
            "chrome devtools",
            "github tool",
            "syncfusion",
            "call mcp",
            "أداة mcp",
            "خادم mcp",
            "بروتوكول mcp",
        ],
        tools=["run_local_command", "execute_command"],
        threshold=0.20,
    ),
    Route(
        # Status/readiness inquiries are answered deterministically from live
        # telemetry (core.status_telemetry) instead of free LLM generation.
        # Placed BEFORE general_chat so an explicit status/readiness match
        # (exact/substring, score>=0.85) always wins over general_chat on ties:
        # the router keeps the first route on equal scores, and a readiness
        # probe such as 'جاهز؟' must never fall through to general_chat.
        name="status_readiness",
        utterances=[
            "status",
            "system status",
            "health",
            "health check",
            "healthcheck",
            "ping",
            "uptime",
            "are you ready",
            "ready",
            "are you up",
            "are you alive",
            "is the system online",
            "is the system up",
            "report status",
            "system health",
            "server status",
            "جاهز",
            "هل أنت جاهز",
            "انت جاهز",
            "مستعد",
            "هل أنت مستعد",
            "جاهزية",
            "الحالة",
            "ما هي حالتك",
            "حالة النظام",
            "صحة النظام",
            "هل النظام يعمل",
            "هل الباص يعمل",
            "فحص الحالة",
            "هل انت شغال",
            "شغال",
            "طمني عن النظام",
        ],
        tools=[],  # Empty list: deterministic telemetry handler answers, no tools needed
        threshold=0.15,
    ),
    Route(
        name="general_chat",
        utterances=[
            "hello",
            "hi",
            "hey",
            "who are you",
            "what is your role",
            "are you online",
            "how are you",
            "thank you",
            "thanks",
            "good morning",
            "help",
            "مرحبا",
            "أهلا",
            "السلام عليكم",
            "من أنت",
            "ما هو دورك",
            "هل أنت متصل",
            "كيف حالك",
            "شكرا",
            "صباح الخير",
            "ما هي مهامك",
        ],
        tools=[],  # Empty list: triggers zero-tool mode for ultra-fast generation
        threshold=0.15,
    ),
]


# ---------------------------------------------------------------------------
# Zero-Dependency Semantic Router Engine
# ---------------------------------------------------------------------------


class SemanticRouterEngine:
    """Pure-Python, zero-overhead semantic routing engine inspired by Aurelio AI's semantic-router.

    Uses tokenization, Arabic morphological normalization, character 3-grams,
    and Jaccard / token-overlap similarity to achieve <0.3ms route selection
    without GPU, VRAM, or external network latency.
    """

    def __init__(self, routes: list[Route] | None = None) -> None:
        self.routes = routes if routes is not None else _DEFAULT_ROUTES

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize Arabic and English text for robust semantic comparison."""
        text = text.lower().strip()
        # Normalize Arabic alef variants
        text = re.sub(r"[إأآا]", "ا", text)
        # Normalize Arabic yaa / taa marbuta
        text = re.sub(r"ى", "ي", text)
        text = re.sub(r"ة", "ه", text)
        # Remove diacritics / tashkeel
        text = re.sub(r"[\u064B-\u0652]", "", text)
        # Replace non-word chars with space
        text = re.sub(r"[^\w\s]", " ", text)
        return text

    @classmethod
    def _get_features(cls, text: str, n: int = 3) -> set[str]:
        """Extract word tokens and character n-grams for subword matching."""
        norm = cls._normalize(text)
        words = norm.split()
        features: set[str] = set(words)
        for word in words:
            if len(word) >= n:
                for i in range(len(word) - n + 1):
                    features.add(word[i : i + n])
        return features

    def route(self, query: str) -> tuple[Route, float, list[str]]:
        """Match query against all routes and return (best_route, score, selected_tools)."""
        query_norm = self._normalize(query)
        query_features = self._get_features(query)

        chat_fallback = next((r for r in self.routes if r.name == "general_chat"), self.routes[-1])

        if not query_features:
            return chat_fallback, 0.0, []

        best_route: Route | None = None
        best_score = 0.0
        status_route: Route | None = None
        status_score = 0.0

        for candidate_route in self.routes:
            route_max_score = 0.0
            for utterance in candidate_route.utterances:
                u_norm = self._normalize(utterance)
                # Exact or substring match boost
                if u_norm == query_norm or (len(u_norm) > 3 and u_norm in query_norm):
                    similarity = 0.95
                elif len(query_norm) > 3 and query_norm in u_norm:
                    similarity = 0.85
                else:
                    u_features = self._get_features(utterance)
                    if not u_features:
                        continue
                    intersection = len(query_features & u_features)
                    union = len(query_features | u_features)
                    similarity = (intersection / union) if union > 0 else 0.0

                route_max_score = max(route_max_score, similarity)

            if candidate_route.name == "status_readiness":
                status_route = candidate_route
                status_score = route_max_score

            if route_max_score > best_score:
                best_score = route_max_score
                best_route = candidate_route

        # Explicit status/readiness match (exact/substring, score>=0.85) always
        # wins: a readiness probe must never tie at 0.00 into general_chat.
        if status_route is not None and status_score >= 0.85:
            return status_route, status_score, list(status_route.tools)

        # Enforce threshold
        if best_route is None or best_score < best_route.threshold:
            return chat_fallback, best_score, []

        return best_route, best_score, list(best_route.tools)


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_VERB_OBJECT = re.compile(
    r"^\s*(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?"
    r"(?:i\s+(?:want|need)\s+(?:you\s+)?(?:to\s+)?)?"
    r"([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(.+?)[\.\?!]?\s*$",
    re.IGNORECASE,
)
_COMPLEX_KW = re.compile(
    r"\b(integrate|refactor|migrate|architect|design|pipeline|orchestrate"
    r"|coordinate|multi|parallel|distributed|overhaul|redesign)\b",
    re.IGNORECASE,
)
_MODERATE_KW = re.compile(
    r"\b(function|method|class|validate|implement|create|build|write|parse"
    r"|generate|convert|transform|process|handle|manage|configure)\b",
    re.IGNORECASE,
)
_SIMPLE_KW = re.compile(
    r"\b(list|show|get|read|print|check|status|version|help|ping|describe)\b",
    re.IGNORECASE,
)
_AMBIGUOUS = re.compile(
    r"\b(it|this|that|them|those|something|stuff|thing)\b",
    re.IGNORECASE,
)

_SUCCESS_TEMPLATES: dict[str, str] = {
    "test": "All tests pass with zero failures.",
    "commit": "Commit exists on target branch and quality gates are green.",
    "push": "Branch is pushed to remote and CI passes.",
    "refactor": "Refactored code passes all existing tests with no regressions.",
    "install": "Package is installed and importable without errors.",
    "delete": "Target is removed; system remains functional.",
    "remove": "Target is removed; system remains functional.",
    "read": "Accurate data returned with no side effects.",
    "list": "Complete list returned with no side effects.",
    "fix": "The reported issue no longer reproduces.",
    "build": "Build succeeds and artifact is produced.",
    "deploy": "Service is running and health check passes.",
    "audit": "Audit report produced with all findings documented.",
    "write": "File exists with the correct content.",
    "create": "Artifact created and verified to be functional.",
    "update": "Target updated; existing functionality unaffected.",
    "run": "Process completes successfully with expected output.",
}


# ---------------------------------------------------------------------------
# IntentParser
# ---------------------------------------------------------------------------


class IntentParser:
    """Parse raw task strings into structured Intent objects.

    Integrates SemanticRouterEngine for dynamic tool pruning and minimal context bloat.

    Usage::

        parser = IntentParser()
        intent = parser.parse("Refactor the neural bus to support streaming")
        print(intent.inferred)         # "Restructure neural_bus.py for streaming support"
        print(intent.complexity)       # "complex"
        print(intent.route)            # "system_ops"
        print(intent.selected_tools)   # ['run_local_command', 'execute_command']
    """

    def __init__(self, routes: list[Route] | None = None) -> None:
        self.router = SemanticRouterEngine(routes=routes)

    def parse(self, raw: str, context: dict | None = None) -> Intent:
        """Return a structured Intent for the given raw task string.

        Tries Ollama first (if OLLAMA_HOST is set and service is up),
        falls back to rule-based parsing.
        """
        raw = (raw or "").strip()
        ctx = context or {}

        if not raw:
            return Intent(
                raw=raw,
                literal="",
                inferred="No task provided.",
                success_condition="Nothing to verify — task is empty.",
                complexity="simple",
                confidence=0.0,
                source="rule_based",
                route="general_chat",
                selected_tools=[],
                route_score=0.0,
            )

        # Route dynamically via SemanticRouterEngine
        route_obj, route_score, selected_tools = self.router.route(raw)

        # Try Ollama-backed parsing first
        ollama_intent = self._parse_via_ollama(raw, ctx)
        if ollama_intent is not None:
            ollama_intent.route = route_obj.name
            ollama_intent.selected_tools = selected_tools
            ollama_intent.route_score = route_score
            return ollama_intent

        # Rule-based fallback
        intent = self._parse_rule_based(raw, ctx)
        intent.route = route_obj.name
        intent.selected_tools = selected_tools
        intent.route_score = route_score
        return intent

    # ------------------------------------------------------------------
    # Ollama-backed parsing
    # ------------------------------------------------------------------

    def _parse_via_ollama(self, raw: str, ctx: dict) -> Intent | None:
        """Attempt to parse intent using the local Ollama model via sync chat.

        Uses the router's underlying synchronous ``OllamaClient`` (the async
        ``ModelRouter.chat`` requires an ``AgentRole`` and an event loop, so it
        can never be awaited from this sync method).

        Returns None if Ollama is unavailable or returns malformed JSON.
        """
        try:
            router = get_router()
            client = getattr(router, "client", None)
            if client is None:
                return None
            model_name = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")
            prompt = (
                "You are an intent parser for an AI agent system. "
                "Given the following task, respond with ONLY valid JSON "
                "(no markdown, no explanation) in this exact schema:\n"
                '{"literal": "...", "inferred": "...", '
                '"success_condition": "...", "complexity": "simple|moderate|complex"}\n\n'
                f"Task: {raw}"
            )
            res = client.chat(
                model_name,
                [{"role": "user", "content": prompt}],
            )
            if asyncio.iscoroutine(res):
                return None
            if not isinstance(res, dict):
                return None
            response = res
            message = response.get("message", {})
            if not isinstance(message, dict):
                return None
            text = message.get("content", "")
            if not isinstance(text, str) or not text.strip():
                return None
            text = text.strip()

            # Strip markdown fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            data = json.loads(text)
            complexity = data.get("complexity", "moderate")
            if complexity not in ("simple", "moderate", "complex"):
                complexity = "moderate"

            return Intent(
                raw=raw,
                literal=str(data.get("literal", raw)),
                inferred=str(data.get("inferred", raw)),
                success_condition=str(data.get("success_condition", "")),
                complexity=complexity,
                confidence=0.9,
                source="ollama",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ollama intent parsing unavailable: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Rule-based parsing
    # ------------------------------------------------------------------

    def _parse_rule_based(self, raw: str, ctx: dict) -> Intent:
        """Fast, dependency-free intent parsing using regex heuristics."""
        literal = self._extract_literal(raw)
        inferred = self._infer_intent(raw, literal)
        success_condition = self._derive_success(raw)
        complexity = self._assess_complexity(raw)
        confidence = self._score_confidence(raw, complexity)

        return Intent(
            raw=raw,
            literal=literal,
            inferred=inferred,
            success_condition=success_condition,
            complexity=complexity,
            confidence=confidence,
            source="rule_based",
        )

    def _extract_literal(self, raw: str) -> str:
        """Extract a clean literal restatement of the task."""
        cleaned = re.sub(
            r"^(please\s+|can\s+you\s+|could\s+you\s+|i\s+want\s+(you\s+)?to\s+|"
            r"i\s+need\s+(you\s+)?to\s+)",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned[:200] if cleaned else raw[:200]

    def _infer_intent(self, raw: str, literal: str) -> str:
        """Produce an inferred intent from verb-object extraction."""
        match = _VERB_OBJECT.match(raw)
        if match:
            action = match.group(1).strip()
            subject = match.group(2).strip()[:100]
            is_amb = bool(_AMBIGUOUS.search(subject))
            suffix = " [CLARIFICATION NEEDED: ambiguous reference]" if is_amb else ""
            return f"{action.capitalize()} → {subject}{suffix}"
        return literal

    def _derive_success(self, raw: str) -> str:
        """Map the first matching keyword to a success template."""
        raw_lower = raw.lower()
        for keyword, template in _SUCCESS_TEMPLATES.items():
            if re.search(rf"\b{re.escape(keyword)}\b", raw_lower):
                return template
        return "Task completed as described with no degradation to existing functionality."

    def _assess_complexity(self, raw: str) -> str:
        if _COMPLEX_KW.search(raw):
            return "complex"
        if _MODERATE_KW.search(raw):
            return "moderate"
        if _SIMPLE_KW.search(raw):
            return "simple"
        return "moderate"

    def _score_confidence(self, raw: str, complexity: str) -> float:
        score = 0.8
        if _AMBIGUOUS.search(raw):
            score -= 0.3
        if complexity == "complex":
            score -= 0.05
        if complexity == "simple":
            score += 0.1
        return round(max(0.0, min(1.0, score)), 2)
