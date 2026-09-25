"""Live status telemetry + reply-path intent helpers (AR/EN) for Matrix agents.

Backend-only helper (no UI code, no secrets). Purpose: answer status /
readiness questions with probed live telemetry instead of free LLM
generation. Free generation from weak local models produced canned
disclaimers ("hypothetical ... simplified example") and Arabic
hallucinations (e.g. answering readiness with unrelated content and then
defending the bad answer instead of accepting correction).

All probes are best-effort with short timeouts and NEVER raise: an
unreachable service is reported as offline, which is still honest
telemetry.
"""

from __future__ import annotations

import logging
import os
import re
import socket
import urllib.request
from typing import Any

logger = logging.getLogger("Matrix.StatusTelemetry")

# Phrases that must NEVER appear in a status/readiness reply. Their presence
# proves the answer was canned instead of grounded in live telemetry.
BANNED_PHRASES: tuple[str, ...] = (
    "hypothetical",
    "simplified example",
    "as a language model",
    "language model trained by",
    "i don't have access to real-time",
    "i cannot access real-time data",
)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

_STATUS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bstatus\b", re.IGNORECASE),
    re.compile(r"\bhealth\b", re.IGNORECASE),
    re.compile(r"\bping\b", re.IGNORECASE),
    re.compile(r"\buptime\b", re.IGNORECASE),
    re.compile(r"are you (online|ready|up|alive|working|ok|okay)\b", re.IGNORECASE),
    re.compile(r"is the system (online|up|working|ready)\b", re.IGNORECASE),
    re.compile(r"(system|server) (status|health)\b", re.IGNORECASE),
    re.compile(r"(report|check|show|give|verify).{0,20}(status|health)\b", re.IGNORECASE),
    re.compile(r"جاهز|مستعد|جاهزي|استعداد"),
    re.compile(r"حالت?ك|الحالة|حالة النظام|صحة النظام|فحص الحالة"),
    re.compile(r"هل (أنت|انت|النظام|الباص).{0,30}(متصل|جاهز|مستعد|يعمل|شغال|بخير)"),
    re.compile(r"(الباص|الجسر|اللوحة|النظام).{0,20}(يعمل|شغال|متصل)"),
    re.compile(r"طمني|شغال"),
)

_CORRECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(لا|لأ|كلا)\s*[,،]?\s*(أقصد|اقصد|انا أقصد|أنا أقصد|قصدي)"),
    re.compile(r"^(لا|لأ|كلا)\s*[,،]?\s*(خطأ|غلط|خاطئ|غلطان|مش صح|مو صح)"),
    re.compile(r"^(خطأ|غلط|خاطئ|غلطان)\s*[!؟?.]*$"),
    re.compile(r"(أقصد أن|اقصد ان|قصدي أن|ليس قصدي|مو قصدي)"),
    re.compile(r"(تصحيح|صحح|تصحح|هذا خطأ|هذا غلط|إجابة خاطئة|اجابة خاطئة|جواب غلط)"),
    re.compile(r"(فهمت خطأ|فهمتني غلط|أعد الفهم|اعد الفهم|راجع نفسك)"),
    re.compile(r"\bi (meant|mean)\b", re.IGNORECASE),
    re.compile(
        r"\b(correction|correct yourself|that's wrong|that is wrong|wrong answer)\b", re.IGNORECASE
    ),
    re.compile(r"\b(you misunderstood|not what i meant|misunderstood)\b", re.IGNORECASE),
)

# Leading correction lead-in stripped to recover the corrected remainder.
_BARE_DENIAL_RE = re.compile(r"^\s*(لا|لأ|كلا)\s*[,،:]?\s*", re.IGNORECASE)
_CORRECTION_PREFIX_RE = re.compile(
    r"^\s*"
    r"(أقصد|اقصد|انا أقصد|أنا أقصد|قصدي|تصحيح|صحح|خطأ|غلط|ليس قصدي|مو قصدي|"
    r"i meant?|correction|correct yourself|that's wrong|that is wrong|wrong|"
    r"you misunderstood|not what i meant)\b\s*[,،:]?\s*",
    re.IGNORECASE,
)

# Shared grounding rules appended to agent system prompts.
GROUNDING_SUFFIX = (
    " Grounding rules: (1) NEVER describe a hypothetical or simplified-example audit — "
    "for any status/readiness/health question answer ONLY from live probed telemetry. "
    "(2) Speak Arabic when the Commander speaks Arabic. "
    "(3) If the Commander corrects you, discard your previous answer without defending it "
    "and reinterpret the corrected intent from scratch."
)


def detect_language(text: str) -> str:
    """Return 'ar' when the text contains Arabic script, else 'en'."""
    return "ar" if _ARABIC_RE.search(text or "") else "en"


def is_status_query(text: str) -> bool:
    """Return True when the message asks about system/agent status or readiness."""
    if not text or not isinstance(text, str):
        return False
    return any(p.search(text) for p in _STATUS_PATTERNS)


def is_correction(text: str) -> bool:
    """Return True when the Commander is correcting the agent's previous answer."""
    if not text or not isinstance(text, str):
        return False
    return any(p.search(text) for p in _CORRECTION_PATTERNS)


def strip_correction_prefix(text: str) -> str:
    """Remove the leading correction lead-in, returning the corrected remainder."""
    remainder = _BARE_DENIAL_RE.sub("", text or "")
    remainder = _CORRECTION_PREFIX_RE.sub("", remainder)
    return remainder.strip(" ,،:;.")


def contains_banned_phrase(text: str) -> str | None:
    """Return the first banned canned-response phrase found, else None."""
    lowered = (text or "").lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def prune_last_assistant_turn(history: list[Any]) -> int:
    """Drop the trailing assistant/tool exchange so a correction is not defended.

    Keeps the system prompt at index 0. Returns the number of dropped entries.
    """
    if not history:
        return 0
    dropped = 0
    while (
        len(history) > 1
        and isinstance(history[-1], dict)
        and history[-1].get("role")
        in (
            "assistant",
            "tool",
        )
    ):
        history.pop()
        dropped += 1
    return dropped


def _tcp_probe(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_get_json(url: str, timeout: float) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            if resp.status < 200 or resp.status >= 300:
                return None
            import json

            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("Telemetry HTTP probe failed for %s", url, exc_info=True)
        return None


def _split_host_port(endpoint: str, default_port: int) -> tuple[str, int]:
    cleaned = (endpoint or "").replace("tcp://", "").replace("http://", "")
    cleaned = cleaned.rstrip("/").split("/")[0]
    if ":" in cleaned:
        host, _, port_str = cleaned.rpartition(":")
        try:
            return host.strip("[]") or "127.0.0.1", int(port_str)
        except ValueError:
            return host.strip("[]") or "127.0.0.1", default_port
    return cleaned or "127.0.0.1", default_port


def collect_live_telemetry(timeout: float = 1.5) -> dict[str, Any]:
    """Probe bus / Ollama / bridge / dashboard. NEVER raises; offline is data."""
    bus_host, bus_port = _split_host_port(
        os.getenv("ZMQ_BUS_URL") or os.getenv("ZMQ_ROUTER_URL", "tcp://127.0.0.1:5555"), 5555
    )
    ollama_base = (os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    bridge_host = os.getenv("UI_HOST") or os.getenv("HOST") or "127.0.0.1"
    try:
        bridge_port = int(os.getenv("UI_PORT", "8000"))
    except ValueError:
        bridge_port = 8000
    dash_port = 5173

    telemetry: dict[str, Any] = {
        "bus": {
            "endpoint": f"{bus_host}:{bus_port}",
            "online": _tcp_probe(bus_host, bus_port, timeout),
        },
        "ollama": {"endpoint": ollama_base, "online": False, "version": None},
        "bridge": {"endpoint": f"{bridge_host}:{bridge_port}", "online": False},
        "dashboard": {
            "endpoint": f"127.0.0.1:{dash_port}",
            "online": _tcp_probe("127.0.0.1", dash_port, timeout),
        },
    }

    version_payload = _http_get_json(f"{ollama_base}/api/version", timeout)
    if version_payload is not None:
        telemetry["ollama"]["online"] = True
        telemetry["ollama"]["version"] = str(version_payload.get("version", "unknown"))

    health_payload = _http_get_json(f"http://{bridge_host}:{bridge_port}/api/health", timeout)
    if health_payload is not None:
        telemetry["bridge"]["online"] = True
        telemetry["bridge"]["status"] = str(health_payload.get("status", "unknown"))

    return telemetry


def build_status_reply(telemetry: dict[str, Any], lang: str) -> str:
    """Render a short telemetry-grounded status reply. Contains no banned phrases."""
    bus = telemetry.get("bus", {})
    ollama = telemetry.get("ollama", {})
    bridge = telemetry.get("bridge", {})
    dashboard = telemetry.get("dashboard", {})

    def mark(online: bool) -> str:
        return (
            "متصل ✅"
            if (online and lang == "ar")
            else ("✅ online" if online else ("غير متصل ❌" if lang == "ar" else "❌ offline"))
        )

    ollama_detail = ollama.get("version") or ("متصل" if ollama.get("online") else "غير متصل")
    if lang == "ar":
        return (
            "نعم أيها القائد، أنا جاهز — Neo متصل الآن.\n"
            f"• الباص العصبي ({bus.get('endpoint', '?')}): {mark(bool(bus.get('online')))}\n"
            f"• Ollama ({ollama.get('endpoint', '?')}): v{ollama_detail}\n"
            f"• الجسر ({bridge.get('endpoint', '?')}): {mark(bool(bridge.get('online')))}\n"
            f"• اللوحة ({dashboard.get('endpoint', '?')}): {mark(bool(dashboard.get('online')))}"
        )
    return (
        "Yes Commander, ready — Neo is online.\n"
        f"• Neural bus ({bus.get('endpoint', '?')}): {mark(bool(bus.get('online')))}\n"
        f"• Ollama ({ollama.get('endpoint', '?')}): v{ollama_detail}\n"
        f"• Bridge ({bridge.get('endpoint', '?')}): {mark(bool(bridge.get('online')))}\n"
        f"• Dashboard ({dashboard.get('endpoint', '?')}): {mark(bool(dashboard.get('online')))}"
    )
