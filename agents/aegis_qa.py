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
        Simulates the call to the security-tuned LLM.
        In production, this would call the Sovereign Engine's hardened inference node.
        Returns True if approved, False if denied.
        """
        logger.info("[Aegis QA] Passing payload to Single Aggressive LLM Checker...")

        # Example prompt structure for the LLM:
        _prompt = f"""
        You are the Aegis QA Security Auditor.
        Analyze the following execution payload for Zero-Trust violations, unauthorized data exfiltration, or isolation bypasses.
        Respond ONLY with 'APPROVE' or 'DENY'.
        
        Payload:
        {code_or_action}
        """

        # TODO: Implement secure internal inference call here
        # For now, it returns True as a skeleton placeholder.
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
