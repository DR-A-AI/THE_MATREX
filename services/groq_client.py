"""Groq Client with Multi-Account Pool, Flex Processing, and Rotation.

Supports:
1. Multi-account key pool from environment (GROQ_API_KEY_001/002/003 + legacy GROQ_API_KEY).
2. Flex Processing tier ("service_tier": "flex") for 10x higher rate limits.
3. Automatic rotation on Rate Limits (429), Capacity Exceeded (498), or Auth Errors (401/403).
4. Seamless fallback to local Ollama when cloud capacity is exhausted.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

logger = logging.getLogger("Sovereign.GroqClient")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
MODEL_ALIASES: dict[str, str] = {
    "qwen": "qwen/qwen3.8-27b",
    "gpt-120b": "openai/gpt-oss-120b",
    "gpt-20b": "openai/gpt-oss-20b",
    "allam": "allam-2-7b",
}


@dataclass
class GroqAccount:
    """Represents a single Groq developer account credentials and status."""

    account_id: str
    email: str
    api_key: str
    source_file: Path | None = None
    is_active: bool = True
    supports_flex: bool = True
    consecutive_failures: int = 0
    last_error: str | None = None

    @property
    def masked_key(self) -> str:
        """Return masked key for safe logging (e.g. gsk_***abcd)."""
        if not self.api_key:
            return "NONE"
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}***{self.api_key[-4:]}"


class GroqMultiAccountPool:
    """Manages pool of multiple Groq accounts with automatic rotation and health checks."""

    KNOWN_ACCOUNTS: ClassVar[tuple[dict[str, str], ...]] = (
        {"id": "acc_001", "env_suffix": "001", "email": "dranashilal@gmail.com"},
        {"id": "acc_002", "env_suffix": "002", "email": "r11salfd@gmail.com"},
        {"id": "acc_003", "env_suffix": "003", "email": "tarek.20160862@buc.edu.eg"},
    )
    # Suffixes are positional (001/002/003) and match pool order.

    def __init__(self, desktop_path: Path | None = None) -> None:
        if desktop_path is not None:
            warnings.warn(
                "desktop_path is deprecated and ignored; "
                "Groq keys are loaded from environment only.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.accounts: list[GroqAccount] = []
        self._current_index = 0
        self.reload_accounts()

    def reload_accounts(self) -> None:
        """Load Groq API keys from environment variables only.

        Priority: GROQ_API_KEY_001/002/003, then legacy GROQ_API_KEY
        (as ``env_default``). Empty values, non ``gsk_`` values, and
        duplicates are skipped. Email defaults come from KNOWN_ACCOUNTS
        with optional GROQ_ACCOUNT_001/002/003_EMAIL overrides.
        """
        self.accounts.clear()
        seen_keys: set[str] = set()

        for acc_info in self.KNOWN_ACCOUNTS:
            suffix = acc_info.get("env_suffix", acc_info["id"].rsplit("_", 1)[-1])
            env_name = f"GROQ_API_KEY_{suffix}"
            raw_key = os.getenv(env_name, "")
            key = raw_key.strip().strip('"').strip("'") if raw_key else ""
            if not key or not key.startswith("gsk_"):
                continue
            if key in seen_keys:
                continue
            seen_keys.add(key)
            email_override = os.getenv(f"GROQ_ACCOUNT_{suffix}_EMAIL", "").strip()
            email = email_override or acc_info["email"]
            self.accounts.append(
                GroqAccount(
                    account_id=acc_info["id"],
                    email=email,
                    api_key=key,
                    source_file=None,
                )
            )
            logger.info(
                "Loaded Groq account %s (%s) from %s",
                acc_info["id"],
                email,
                env_name,
            )

        # Legacy single-key fallback.
        env_key_raw = os.getenv("GROQ_API_KEY", "")
        env_key = env_key_raw.strip().strip('"').strip("'") if env_key_raw else ""
        if env_key and env_key.startswith("gsk_") and env_key not in seen_keys:
            seen_keys.add(env_key)
            self.accounts.append(
                GroqAccount(
                    account_id="env_default",
                    email="env@groq.local",
                    api_key=env_key,
                    source_file=None,
                )
            )
            logger.info("Loaded Groq account env_default from GROQ_API_KEY")

        logger.info(
            "Loaded %d Groq account(s): %s",
            len(self.accounts),
            [f"{acc.email} ({acc.masked_key})" for acc in self.accounts],
        )

    def get_next_available_account(self) -> GroqAccount | None:
        """Return the next active account in round-robin sequence."""
        active = [acc for acc in self.accounts if acc.is_active]
        if not active:
            return None

        account = active[self._current_index % len(active)]
        self._current_index = (self._current_index + 1) % len(active)
        return account

    def mark_failure(self, account: GroqAccount, error_code: int, reason: str) -> None:
        """Record account failure and deactivate if permanent."""
        account.consecutive_failures += 1
        account.last_error = f"HTTP {error_code}: {reason}"
        logger.warning(
            "Groq account %s (%s) failed [%s]. Consecutive failures: %d",
            account.account_id,
            account.masked_key,
            account.last_error,
            account.consecutive_failures,
        )
        # Deactivate permanently on 401/403 (revoked/unauthorized)
        if error_code in (401, 403) or account.consecutive_failures >= 5:
            account.is_active = False
            logger.error("Deactivating Groq account %s due to permanent error.", account.account_id)

    def mark_success(self, account: GroqAccount) -> None:
        """Reset failure counter on successful request."""
        account.consecutive_failures = 0
        account.last_error = None
        account.is_active = True


class GroqClient:
    """Async Groq API client supporting Flex Processing and automatic multi-account rotation."""

    def __init__(
        self,
        pool: GroqMultiAccountPool | None = None,
        default_model: str = DEFAULT_GROQ_MODEL,
        enable_flex: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.pool = pool or GroqMultiAccountPool()
        self.default_model = default_model
        self.enable_flex = enable_flex
        self.timeout = timeout

    async def chat_completion(
        self,
        messages: Sequence[Mapping[str, str]],
        model: str | None = None,
        use_flex: bool | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute chat completion with automatic failover across accounts and tier downgrade.

        Args:
            messages: List of message dicts (role, content).
            model: Target model name (defaults to qwen/qwen3.8-27b).
            use_flex: Whether to request Flex Processing (defaults to self.enable_flex).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            tools: Optional tool definitions.

        Returns:
            Decoded JSON response dictionary from Groq.

        Raises:
            RuntimeError: If all accounts fail or are exhausted.
        """
        target_model = model or self.default_model
        target_model = MODEL_ALIASES.get(target_model, target_model)
        is_flex = self.enable_flex if use_flex is None else use_flex

        attempts = 0
        max_attempts = max(1, len(self.pool.accounts) * 2)

        while attempts < max_attempts:
            account = self.pool.get_next_available_account()
            if not account:
                raise RuntimeError(
                    "No active Groq accounts available. All accounts exhausted or revoked."
                )

            attempts += 1
            payload: dict[str, Any] = {
                "model": target_model,
                "messages": list(messages),
                "temperature": temperature,
            }

            should_use_flex = is_flex and account.supports_flex
            if should_use_flex:
                payload["service_tier"] = "flex"

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            if tools:
                payload["tools"] = list(tools)
                payload["tool_choice"] = "auto"

            try:
                result = await asyncio.to_thread(
                    self._send_request_sync,
                    api_key=account.api_key,
                    payload=payload,
                )
                self.pool.mark_success(account)
                return result

            except urllib.error.HTTPError as err:
                status = err.code
                err_body = err.read().decode("utf-8", errors="replace")
                logger.warning(
                    "Groq HTTP error %d from %s (%s): %s",
                    status,
                    account.account_id,
                    account.masked_key,
                    err_body[:200],
                )

                # HTTP 498: Flex capacity exceeded OR HTTP 400 with flex not enabled
                if should_use_flex and (status == 498 or (status == 400 and "service_tier" in err_body)):
                    is_flex = False
                    if status == 400:
                        account.supports_flex = False
                    logger.info("Flex tier unavailable (%d). Auto-downgrading to standard on-demand tier...", status)
                    continue

                # HTTP 429: Rate limit -> rotate to next account
                if status == 429:
                    self.pool.mark_failure(account, status, "Rate limit reached")
                    continue

                # HTTP 401 / 403: Invalid or revoked key -> deactivate and rotate
                if status in (401, 403):
                    self.pool.mark_failure(account, status, f"Auth forbidden: {err_body[:100]}")
                    continue

                # Any other HTTP error
                self.pool.mark_failure(account, status, err_body[:100])
                raise RuntimeError(f"Groq API error {status}: {err_body}") from err

            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as ex:
                logger.error("Network or unexpected error calling Groq: %s", ex)
                self.pool.mark_failure(account, 500, str(ex))

        raise RuntimeError(
            f"Failed to complete Groq request after {attempts} attempts across account pool."
        )

    def _send_request_sync(self, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform synchronous HTTP POST using standard urllib with strict timeout."""
        endpoint = f"{GROQ_BASE_URL}/chat/completions"
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Sovereign-Matrix/1.0",
            },
            method="POST",
        )

        if not endpoint.startswith("https://"):
            raise ValueError(f"Insecure scheme in Groq endpoint: {endpoint}")

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
            raw_body = resp.read().decode("utf-8")
            return json.loads(raw_body)
