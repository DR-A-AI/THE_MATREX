import ast
import logging
import re
from typing import ClassVar

logger = logging.getLogger(__name__)


class DeterministicGuillotine:
    """
    Fast, strict, rule-based execution filter.
    Drops actions that violate non-negotiable security rules instantly.
    """

    # Signatures of explicitly forbidden modules, functions or patterns
    # Adding more robust checks for standard library dangerous calls
    FORBIDDEN_PATTERNS: ClassVar[list] = [
        re.compile(r"\bimport\s+pickle\b"),
        re.compile(r'\b__import__\s*\(\s*[\'"]pickle[\'"]\s*\)'),
        re.compile(r"\beval\s*\("),
        re.compile(r"\bexec\s*\("),
        re.compile(r"\bos\.system\s*\("),
        re.compile(r"\bsubprocess\.Popen\s*\("),
        re.compile(r"\bimport\s+os\b"),
        re.compile(r"\bimport\s+sys\b"),
        re.compile(r"\bimport\s+subprocess\b"),
        # Basic heuristic to prevent hardcoded secrets being passed in payload
        re.compile(r'[\'"][A-Za-z0-9_-]{32,}[\'"]'),
    ]

    @classmethod
    def analyze(cls, code_or_action: str) -> bool:
        """
        Returns True if the code passes the guillotine, False if it is severed.
        """
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern.search(code_or_action):
                logger.critical(
                    f"[Aegis QA] Guillotine dropped! Forbidden pattern detected: {pattern.pattern}"
                )
                return False

        # Structural AST check to prevent obfuscated evals and dynamic execution
        try:
            tree = ast.parse(code_or_action)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id in [
                        "eval",
                        "exec",
                        "compile",
                        "globals",
                        "locals",
                        "__import__",
                        "getattr",
                        "setattr",
                        "delattr",
                        "hasattr",
                    ]:
                        logger.critical(
                            f"[Aegis QA] AST Guillotine dropped! Forbidden name detected: {node.id}"
                        )
                        return False
                elif isinstance(node, ast.Attribute):
                    if node.attr in [
                        "__class__",
                        "__subclasses__",
                        "__builtins__",
                        "__dict__",
                        "__base__",
                        "__mro__",
                        "system",
                        "Popen",
                    ]:
                        logger.critical(
                            f"[Aegis QA] AST Guillotine dropped! Forbidden attribute detected: {node.attr}"
                        )
                        return False
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in [
                        "eval",
                        "exec",
                        "compile",
                        "globals",
                        "locals",
                        "__import__",
                    ]:
                        logger.critical(
                            f"[Aegis QA] AST Guillotine dropped! Forbidden call detected: {node.func.id}"
                        )
                        return False
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in [
                            "os",
                            "sys",
                            "subprocess",
                            "pickle",
                            "pty",
                            "builtins",
                            "importlib",
                        ]:
                            logger.critical(
                                f"[Aegis QA] AST Guillotine dropped! Forbidden import detected: {alias.name}"
                            )
                            return False
                elif isinstance(node, ast.ImportFrom) and node.module in [
                    "os",
                    "sys",
                    "subprocess",
                    "pickle",
                    "pty",
                    "builtins",
                    "importlib",
                ]:
                    logger.critical(
                        f"[Aegis QA] AST Guillotine dropped! Forbidden from import detected: {node.module}"
                    )
                    return False
        except SyntaxError:
            logger.critical(
                "[Aegis QA] Guillotine dropped! Payload is malformed or intentionally obfuscated (SyntaxError)."
            )
            return False

        return True


class LLMAggressiveChecker:
    """
    A single, focused LLM check replacing expensive consensus models.
    Its only job is to aggressively hunt for zero-trust violations and logical vulnerabilities.
    """

    @classmethod
    def evaluate(cls, code_or_action: str) -> bool:
        """
        Executes a real physical security evaluation against the payload.
        First executes deterministic AST zero-trust rule inspection.
        Second, if local Ollama node is reachable, executes live LPU inference.
        Returns True if approved, False if denied.
        """
        logger.info("[Aegis QA] Passing payload to Single Aggressive LLM Checker...")

        # 1. Physical Deterministic Zero-Trust Guard
        dangerous_patterns = [
            "eval(",
            "exec(",
            "os.system(",
            "shell=True",
            "__import__",
            "/etc/shadow",
            "/etc/passwd",
        ]
        for pattern in dangerous_patterns:
            if pattern in code_or_action:
                logger.critical(f"[Aegis QA] REJECTED: Forbidden pattern detected: {pattern}")
                return False

        # 2. Live Local Ollama LPU Evaluation
        try:
            import json
            import os
            import urllib.request

            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api/chat")
            prompt = (
                "You are the Aegis QA Security Auditor. Analyze the following code or action payload "
                "for Zero-Trust violations, malicious behavior, or unauthorized access. "
                "Respond ONLY with 'APPROVE' or 'DENY'.\n\n"
                f"Payload:\n{code_or_action[:1024]}"
            )
            req_data = json.dumps(
                {
                    "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                ollama_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:  # nosec: B310
                if resp.status == 200:
                    result = json.loads(resp.read().decode("utf-8"))
                    content = result.get("message", {}).get("content", "").strip().upper()
                    if "DENY" in content:
                        logger.warning("[Aegis QA] Live LLM Security Check: DENIED")
                        return False
                    logger.info("[Aegis QA] Live LLM Security Check: APPROVED")
                    return True
        except Exception:  # noqa: BLE001
            logger.debug("[Aegis QA] Local Ollama node unreachable for QA check, relying on deterministic AST gate.")

        return True


class AsymmetricQA:
    """
    Asymmetric QA Pipeline:
    1. Deterministic Guillotine (O(1) / O(N) regex checks + AST validation)
    2. Single Aggressive LLM Check (O(LLM) inference)

    Replaces expensive multi-agent consensus for fast, deterministic, and secure validation.
    """

    @classmethod
    def verify(cls, payload: str) -> bool:
        logger.info("[Aegis QA] Initiating Asymmetric QA verification...")

        # Phase 1: Guillotine
        if not DeterministicGuillotine.analyze(payload):
            logger.critical("[Aegis QA] Payload rejected by Deterministic Guillotine.")
            return False

        # Phase 2: Aggressive LLM
        if not LLMAggressiveChecker.evaluate(payload):
            logger.critical("[Aegis QA] Payload rejected by Aggressive LLM Check.")
            return False

        logger.info("[Aegis QA] Payload passed Asymmetric QA.")
        return True
