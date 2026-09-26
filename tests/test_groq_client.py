"""Unit tests for services/groq_client.py (environment-only pool)."""

from __future__ import annotations

import io
import json
import logging
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.groq_client import (
    DEFAULT_GROQ_MODEL,
    GroqAccount,
    GroqClient,
    GroqMultiAccountPool,
)

GROQ_ENV_VARS: tuple[str, ...] = (
    "GROQ_API_KEY",
    "GROQ_API_KEY_001",
    "GROQ_API_KEY_002",
    "GROQ_API_KEY_003",
    "GROQ_ACCOUNT_001_EMAIL",
    "GROQ_ACCOUNT_002_EMAIL",
    "GROQ_ACCOUNT_003_EMAIL",
)


@pytest.fixture(autouse=True)
def _clean_groq_env(monkeypatch: pytest.MonkeyPatch):
    """Auto-clean all seven Groq env vars before/after each test."""
    for var in GROQ_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    yield


def test_groq_account_masked_key() -> None:
    acc = GroqAccount(
        account_id="acc1",
        email="test@example.com",
        api_key="gsk_1234567890abcdef",
    )
    assert acc.masked_key == "gsk_***cdef"

    short_acc = GroqAccount(
        account_id="acc2",
        email="short@example.com",
        api_key="short",
    )
    assert short_acc.masked_key == "***"


def test_groq_multi_account_pool_loading_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_account1111111111")
    monkeypatch.setenv("GROQ_API_KEY_002", "gsk_account2222222222")

    pool = GroqMultiAccountPool()
    assert len(pool.accounts) == 2
    assert pool.accounts[0].account_id == "acc_001"
    assert pool.accounts[0].email == "dranashilal@gmail.com"
    assert pool.accounts[0].api_key == "gsk_account1111111111"
    assert pool.accounts[0].source_file is None
    assert pool.accounts[1].account_id == "acc_002"
    assert pool.accounts[1].email == "r11salfd@gmail.com"
    assert pool.accounts[1].api_key == "gsk_account2222222222"
    assert pool.accounts[1].source_file is None

    # Test round robin
    a1 = pool.get_next_available_account()
    a2 = pool.get_next_available_account()
    a3 = pool.get_next_available_account()
    assert a1 is not None and a1.account_id == "acc_001"
    assert a2 is not None and a2.account_id == "acc_002"
    assert a3 is not None and a3.account_id == "acc_001"


def test_groq_pool_priority_dedup_and_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_uniqueAAA1111111")
    monkeypatch.setenv("GROQ_API_KEY_002", "gsk_uniqueAAA1111111")  # duplicate -> skipped
    monkeypatch.setenv("GROQ_API_KEY_003", "not-a-groq-key")  # non gsk_ -> skipped
    monkeypatch.setenv("GROQ_API_KEY", "gsk_legacysingle9999")

    pool = GroqMultiAccountPool()
    assert [a.account_id for a in pool.accounts] == ["acc_001", "env_default"]
    assert pool.accounts[0].api_key == "gsk_uniqueAAA1111111"
    assert pool.accounts[1].api_key == "gsk_legacysingle9999"


def test_groq_pool_email_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_override11111111")
    monkeypatch.setenv("GROQ_ACCOUNT_001_EMAIL", "custom@example.com")

    pool = GroqMultiAccountPool()
    assert len(pool.accounts) == 1
    assert pool.accounts[0].account_id == "acc_001"
    assert pool.accounts[0].email == "custom@example.com"


def test_groq_pool_failure_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_account1111111111")

    pool = GroqMultiAccountPool()
    acc = pool.get_next_available_account()
    assert acc is not None

    # Permanent failure (403 forbidden)
    pool.mark_failure(acc, 403, "Forbidden")
    assert not acc.is_active
    assert pool.get_next_available_account() is None


@pytest.mark.asyncio
async def test_groq_client_chat_completion_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_validkey12345678")

    pool = GroqMultiAccountPool()
    client = GroqClient(pool=pool, enable_flex=True)

    fake_response_data = {
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "Hello from Groq Flex!"}}],
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result["id"] == "chatcmpl-123"
        assert result["choices"][0]["message"]["content"] == "Hello from Groq Flex!"
        assert mock_urlopen.called

        # Check request sent service_tier = flex
        req_arg = mock_urlopen.call_args[0][0]
        payload = json.loads(req_arg.data.decode("utf-8"))
        assert payload["service_tier"] == "flex"
        assert payload["model"] == DEFAULT_GROQ_MODEL


@pytest.mark.asyncio
async def test_groq_client_flex_498_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_validkey12345678")

    pool = GroqMultiAccountPool()
    client = GroqClient(pool=pool, enable_flex=True)

    # First call throws HTTP 498 (capacity exceeded), second succeeds
    err_498 = urllib.error.HTTPError(
        url="https://api.groq.com",
        code=498,
        msg="Capacity Exceeded",
        hdrs=MagicMock(),
        fp=io.BytesIO(b'{"error": "capacity_exceeded"}'),
    )

    mock_resp_success = MagicMock()
    mock_resp_success.read.return_value = b'{"id": "fallback-success"}'
    mock_resp_success.__enter__.return_value = mock_resp_success

    with patch("urllib.request.urlopen", side_effect=[err_498, mock_resp_success]) as mock_urlopen:
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
        )
        assert result["id"] == "fallback-success"
        assert mock_urlopen.call_count == 2

        # Verify second call downgraded from flex (service_tier not present)
        req_2 = mock_urlopen.call_args_list[1][0][0]
        p2 = json.loads(req_2.data.decode("utf-8"))
        assert "service_tier" not in p2


def test_groq_pool_legacy_single_key_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy GROQ_API_KEY alone yields a single env_default account."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_legacysingle9999")

    pool = GroqMultiAccountPool()
    assert len(pool.accounts) == 1
    assert pool.accounts[0].account_id == "env_default"
    assert pool.accounts[0].api_key == "gsk_legacysingle9999"
    assert pool.accounts[0].source_file is None


def test_groq_pool_never_logs_raw_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Full key value must never appear in logs; only masked key + env name."""
    raw_key = "gsk_secrettestkey1234"
    monkeypatch.setenv("GROQ_API_KEY_001", raw_key)

    with caplog.at_level(logging.INFO, logger="Sovereign.GroqClient"):
        GroqMultiAccountPool()

    assert raw_key not in caplog.text
    assert "GROQ_API_KEY_001" in caplog.text


def test_groq_desktop_path_deprecated_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Transitional: desktop_path is accepted but silently ignored (env only)."""
    monkeypatch.setenv("GROQ_API_KEY_001", "gsk_account1111111111")

    with pytest.warns(DeprecationWarning):
        pool = GroqMultiAccountPool(desktop_path=tmp_path)

    assert len(pool.accounts) == 1
    assert pool.accounts[0].account_id == "acc_001"
    assert pool.accounts[0].source_file is None
