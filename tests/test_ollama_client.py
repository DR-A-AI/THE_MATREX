"""Comprehensive unit tests for services/ollama_client.py.

All tests operate offline with deterministic mock transports.
"""

from __future__ import annotations

import ast
import io
import json
import os
import socket
import urllib.error
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.ollama_client import (
    AgentRole,
    ModelRouter,
    ModelTier,
    OllamaClient,
    OllamaConfigurationError,
    OllamaConnectionError,
    OllamaHTTPError,
    OllamaModelNotFoundError,
    OllamaProtocolError,
    OllamaTimeoutError,
    UrllibTransport,
    get_router,
    normalize_ollama_base_url,
    probe,
)


class MockTransport:
    """Deterministic in-memory transport mimicking the Ollama HTTP API."""

    def __init__(self, responses: dict[str, tuple[int, bytes]] | None = None) -> None:
        self.calls: list[tuple[str, str, bytes | None, float]] = []
        self.responses: dict[str, tuple[int, bytes]] = responses or {
            "/api/version": (200, b'{"version": "0.5.1"}'),
            "/api/tags": (
                200,
                json.dumps(
                    {
                        "models": [
                            {"name": "llama3.2:latest", "aliases": ["chat-model", "llama3"]},
                            {"name": "qwen3-coder:latest", "aliases": ["coder-model"]},
                            {"name": "deepseek-r1:8b:latest", "aliases": ["reasoner"]},
                            {"name": "gemma3:latest", "aliases": ["gemma"]},
                        ]
                    }
                ).encode("utf-8"),
            ),
            "/api/chat": (
                200,
                json.dumps(
                    {
                        "model": "llama3.2:latest",
                        "message": {
                            "role": "assistant",
                            "content": "I am the One.",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "read_vault",
                                        "arguments": {"key": "secret"},
                                    }
                                }
                            ],
                        },
                        "done": True,
                    }
                ).encode("utf-8"),
            ),
        }

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        self.calls.append((method, url, body, timeout))
        for path_suffix, resp in self.responses.items():
            if url.endswith(path_suffix):
                return resp
        raise OllamaHTTPError(404, f"No mock registered for URL: {url}")


# ============================================================================
# Scenario 1: Base URL normalization with valid loopback variants
# ============================================================================


def test_base_url_normalization_valid_loopbacks() -> None:
    assert normalize_ollama_base_url("127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert normalize_ollama_base_url("http://127.0.0.1:11434/api") == "http://127.0.0.1:11434"
    assert normalize_ollama_base_url("http://localhost:11434/v1") == "http://localhost:11434"
    assert normalize_ollama_base_url("localhost") == "http://localhost:11434"
    assert normalize_ollama_base_url("127.0.0.1") == "http://127.0.0.1:11434"
    assert normalize_ollama_base_url("[::1]:11434") == "http://[::1]:11434"
    assert normalize_ollama_base_url("::1:11434") == "http://[::1]:11434"
    assert normalize_ollama_base_url("::1") == "http://[::1]:11434"
    assert normalize_ollama_base_url("127.0.0.2:11434") == "http://127.0.0.2:11434"

    # Test reading default from environment variable
    with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://127.0.0.1:11434/api"}, clear=False):
        assert normalize_ollama_base_url(None) == "http://127.0.0.1:11434"

    with patch.dict(
        os.environ,
        {"OLLAMA_BASE_URL": "", "OLLAMA_HOST": "localhost:11434"},
        clear=False,
    ):
        assert normalize_ollama_base_url(None) == "http://localhost:11434"


# ============================================================================
# Scenario 2: Rejection of external hosts and HTTPS
# ============================================================================


def test_rejection_of_external_hosts_and_https() -> None:
    # HTTPS rejection
    with pytest.raises(OllamaConfigurationError, match="must use local http://"):
        normalize_ollama_base_url("https://localhost:11434")

    with pytest.raises(OllamaConfigurationError, match="must use local http://"):
        normalize_ollama_base_url("https://127.0.0.1:11434")

    # Non-loopback IP rejection
    with pytest.raises(OllamaConfigurationError, match="Refusing non-loopback"):
        normalize_ollama_base_url("10.0.0.1:11434")

    with pytest.raises(OllamaConfigurationError, match="Refusing non-loopback"):
        normalize_ollama_base_url("192.168.1.1:11434")

    with pytest.raises(OllamaConfigurationError, match="Refusing non-loopback"):
        normalize_ollama_base_url("http://8.8.8.8:11434")

    # External domain rejection
    with (
        patch("socket.gethostbyname", return_value="93.184.216.34"),
        pytest.raises(OllamaConfigurationError, match="Refusing non-loopback"),
    ):
        normalize_ollama_base_url("example.com:11434")

    # Unresolvable host rejection
    with (
        patch("socket.gethostbyname", side_effect=socket.gaierror("Name or service not known")),
        pytest.raises(OllamaConfigurationError, match="Invalid Ollama host"),
    ):
        normalize_ollama_base_url("unresolvable.matrix.internal:11434")


# ============================================================================
# Scenario 3: Rejection of empty/whitespace URL
# ============================================================================


def test_rejection_of_empty_or_whitespace_url() -> None:
    with pytest.raises(OllamaConfigurationError, match="is empty"):
        normalize_ollama_base_url("")

    with pytest.raises(OllamaConfigurationError, match="is empty"):
        normalize_ollama_base_url("   ")

    with pytest.raises(OllamaConfigurationError, match="is empty"):
        normalize_ollama_base_url("\t\r\n")


# ============================================================================
# Scenario 4: probe() success returning (0, dict) with ready=True
# ============================================================================


def test_probe_success_returns_zero_and_ready_true() -> None:
    mock_transport = MockTransport(
        {
            "/api/version": (200, b'{"version": "0.5.1"}'),
            "/api/tags": (
                200,
                json.dumps(
                    {
                        "models": [
                            {"name": "llama3.2:latest"},
                            {"name": "qwen3-coder:latest"},
                        ]
                    }
                ).encode("utf-8"),
            ),
        }
    )
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)
    get_router(client=client, reset=True)

    exit_code, payload = probe()
    assert exit_code == 0
    assert payload["ready"] is True
    assert payload["service"] == "ready"
    assert payload["version"] == "0.5.1"
    assert payload["models"] == ["llama3.2:latest", "qwen3-coder:latest"]
    assert payload["base_url"] == "http://127.0.0.1:11434"


# ============================================================================
# Scenario 5: probe() offline graceful returning (1, dict) with ready=False
# ============================================================================


def test_probe_offline_graceful_returns_one_and_ready_false() -> None:
    class OfflineTransport:
        def request(self, *args: Any, **kwargs: Any) -> tuple[int, bytes]:
            raise OllamaConnectionError("Connection refused by daemon")

    client = OllamaClient("127.0.0.1:11434", transport=OfflineTransport())
    get_router(client=client, reset=True)

    exit_code, payload = probe()
    assert exit_code == 1
    assert payload["ready"] is False
    assert payload["service"] == "unavailable"
    assert payload["error"] == "OllamaConnectionError"
    assert "Connection refused" in payload["message"]
    assert payload["base_url"] == "http://127.0.0.1:11434"

    # Test unexpected general exception in discover()
    class CrashingTransport:
        def request(self, *args: Any, **kwargs: Any) -> tuple[int, bytes]:
            raise RuntimeError("Fatal kernel fault")

    client_crash = OllamaClient("127.0.0.1:11434", transport=CrashingTransport())
    get_router(client=client_crash, reset=True)

    exit_code, payload = probe()
    assert exit_code == 1
    assert payload["ready"] is False
    assert payload["service"] == "error"
    assert payload["error"] == "RuntimeError"

    get_router(reset=True)


# ============================================================================
# Scenario 6: Model discovery and alias resolution
# ============================================================================


def test_model_discovery_and_alias_resolution() -> None:
    mock_transport = MockTransport(
        {
            "/api/version": (200, b'{"version": "0.5.1"}'),
            "/api/tags": (
                200,
                json.dumps(
                    {
                        "models": [
                            {
                                "name": "llama3.2:latest",
                                "aliases": ["chat-model", "local-llama"],
                            },
                            {
                                "name": "qwen3-coder:8b",
                                "aliases": ["coder"],
                            },
                        ]
                    }
                ).encode("utf-8"),
            ),
        }
    )
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)

    # tags() and model_names()
    tags = client.tags()
    assert len(tags) == 2
    names = client.model_names()
    assert "llama3.2:latest" in names
    assert "qwen3-coder:8b" in names

    # Exact name resolution
    assert client.resolve_model("llama3.2:latest") == "llama3.2:latest"

    # Prefix/base name resolution
    assert client.resolve_model("llama3.2") == "llama3.2:latest"
    assert client.resolve_model("qwen3-coder") == "qwen3-coder:8b"

    # Alias resolution
    assert client.resolve_model("chat-model") == "llama3.2:latest"
    assert client.resolve_model("local-llama") == "llama3.2:latest"
    assert client.resolve_model("coder") == "qwen3-coder:8b"

    # has_model()
    assert client.has_model("llama3.2") is True
    assert client.has_model("coder") is True
    assert client.has_model("nonexistent-model") is False


# ============================================================================
# Scenario 7: Model not found raises OllamaModelNotFoundError
# ============================================================================


def test_model_not_found_raises_ollama_model_not_found_error() -> None:
    mock_transport = MockTransport(
        {
            "/api/tags": (
                200,
                json.dumps({"models": [{"name": "llama3.2:latest"}]}).encode("utf-8"),
            )
        }
    )
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)

    with pytest.raises(OllamaModelNotFoundError, match="model name is empty"):
        client.resolve_model("")

    with pytest.raises(OllamaModelNotFoundError, match="is not installed locally"):
        client.resolve_model("nonexistent-model")


# ============================================================================
# Scenario 8: Chat success returning formatted response dict
# ============================================================================


def test_chat_success_returns_formatted_response_dict() -> None:
    mock_transport = MockTransport()
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)

    messages = [{"role": "user", "content": "What is the Matrix?"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_vault",
                "description": "Reads security token",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    res = client.chat("llama3.2", messages, tools=tools)

    assert res["response"] == "I am the One."
    assert res["tier"] == "local"
    assert res["model_used"] == "llama3.2:latest"
    assert res["message"]["role"] == "assistant"
    assert res["done"] is True
    assert res["endpoint"] == "http://127.0.0.1:11434"
    assert len(res["tool_calls"]) == 1
    assert res["tool_calls"][0]["function"]["name"] == "read_vault"

    # Check transport call payload
    chat_calls = [c for c in mock_transport.calls if c[1].endswith("/api/chat")]
    assert len(chat_calls) == 1
    assert chat_calls[0][0] == "POST"
    assert chat_calls[0][2] is not None
    body_data = json.loads(chat_calls[0][2].decode("utf-8"))
    assert body_data["model"] == "llama3.2:latest"
    assert body_data["stream"] is False
    assert body_data["messages"] == messages
    assert body_data["tools"] == tools


# ============================================================================
# Scenario 9: Chat empty messages raises OllamaProtocolError
# ============================================================================


def test_chat_empty_messages_raises_ollama_protocol_error() -> None:
    mock_transport = MockTransport()
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)

    with pytest.raises(OllamaProtocolError, match="requires at least one message"):
        client.chat("llama3.2", [])


# ============================================================================
# Scenario 10: Bad/truncated JSON raises OllamaProtocolError
# ============================================================================


def test_bad_or_truncated_json_raises_ollama_protocol_error() -> None:
    # 1. Truncated JSON
    transport_bad_json = MockTransport({"/api/tags": (200, b'{"models": [{"name":')})
    client1 = OllamaClient("127.0.0.1:11434", transport=transport_bad_json)
    with pytest.raises(OllamaProtocolError, match="returned invalid JSON"):
        client1.tags()

    # 2. JSON not an object
    transport_list_json = MockTransport({"/api/tags": (200, b'["item1", "item2"]')})
    client2 = OllamaClient("127.0.0.1:11434", transport=transport_list_json)
    with pytest.raises(OllamaProtocolError, match="returned a JSON value instead of an object"):
        client2.tags()

    # 3. Missing 'models' list
    transport_no_models = MockTransport({"/api/tags": (200, b'{"status": "ok"}')})
    client3 = OllamaClient("127.0.0.1:11434", transport=transport_no_models)
    with pytest.raises(OllamaProtocolError, match="has no models list"):
        client3.tags()

    # 4. Chat response missing 'message' object
    transport_bad_chat = MockTransport(
        {
            "/api/tags": (200, b'{"models": [{"name": "llama3.2:latest"}]}'),
            "/api/chat": (200, b'{"model": "llama3.2:latest"}'),
        }
    )
    client4 = OllamaClient("127.0.0.1:11434", transport=transport_bad_chat)
    with pytest.raises(OllamaProtocolError, match="has no message object"):
        client4.chat("llama3.2", [{"role": "user", "content": "hi"}])


# ============================================================================
# Scenario 11: Timeout raises OllamaTimeoutError
# ============================================================================


def test_timeout_raises_ollama_timeout_error() -> None:
    class TimeoutTransport:
        def request(self, *args: Any, **kwargs: Any) -> tuple[int, bytes]:
            raise TimeoutError("Socket timed out")

    client = OllamaClient("127.0.0.1:11434", transport=TimeoutTransport(), timeout=2.5)
    with pytest.raises(OllamaTimeoutError, match="timed out after 2.5s"):
        client.health()

    # Test UrllibTransport conversion of urllib.error.URLError with socket.timeout
    urllib_transport = UrllibTransport()
    with (
        patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError(TimeoutError("The read operation timed out")),
        ),
        pytest.raises(OllamaTimeoutError, match="timed out"),
    ):
        urllib_transport.request(
            "GET", "http://127.0.0.1:11434", headers={}, body=None, timeout=1.0
        )


# ============================================================================
# Scenario 12: HTTP 404/500 raises OllamaHTTPError
# ============================================================================


def test_http_error_handling() -> None:
    # 500 error on tags
    transport_500 = MockTransport({"/api/tags": (500, b"Internal server crash")})
    client = OllamaClient("127.0.0.1:11434", transport=transport_500)
    with pytest.raises(OllamaHTTPError) as exc_info:
        client.tags()
    assert exc_info.value.status == 500
    assert "Internal server crash" in str(exc_info.value)

    # 404 error on health endpoint returns {"version": "unknown"}
    transport_404_health = MockTransport({"/api/version": (404, b"Not Found")})
    client_health = OllamaClient("127.0.0.1:11434", transport=transport_404_health)
    health = client_health.health()
    assert health == {"version": "unknown"}

    # 404 on chat raises OllamaHTTPError
    transport_404_chat = MockTransport(
        {
            "/api/tags": (200, b'{"models": [{"name": "llama3.2:latest"}]}'),
            "/api/chat": (404, b"Chat endpoint missing"),
        }
    )
    client_chat = OllamaClient("127.0.0.1:11434", transport=transport_404_chat)
    with pytest.raises(OllamaHTTPError) as exc_info_chat:
        client_chat.chat("llama3.2", [{"role": "user", "content": "hi"}])
    assert exc_info_chat.value.status == 404


# ============================================================================
# Scenario 13: Async chat on ModelRouter
# ============================================================================


@pytest.mark.asyncio
async def test_async_chat_on_model_router() -> None:
    mock_transport = MockTransport()
    client = OllamaClient("127.0.0.1:11434", transport=mock_transport)
    router = ModelRouter(client=client)

    # Check endpoints registered for agent roles
    neo_ep = router.get_endpoint(AgentRole.NEO)
    assert neo_ep is not None
    assert neo_ep.model_id == "llama3.2"
    assert neo_ep.tier == ModelTier.LOCAL

    morpheus_ep = router.get_endpoint(AgentRole.MORPHEUS)
    assert morpheus_ep is not None
    assert morpheus_ep.model_id == "qwen3-coder"

    # Async chat execution
    res = await router.chat(
        AgentRole.NEO,
        [{"role": "user", "content": "Follow the white rabbit."}],
    )
    assert res["response"] == "I am the One."
    assert res["tier"] == "local"
    assert res["model_used"] == "llama3.2:latest"

    # Missing model for role raises OllamaConnectionError
    empty_transport = MockTransport(
        {
            "/api/tags": (200, b'{"models": []}'),
            "/api/version": (200, b'{"version": "0.5.1"}'),
        }
    )
    empty_client = OllamaClient("127.0.0.1:11434", transport=empty_transport)
    empty_router = ModelRouter(client=empty_client)
    with pytest.raises(OllamaConnectionError, match="No installed local Ollama model available"):
        await empty_router.chat(AgentRole.NEO, [{"role": "user", "content": "hello"}])


# ============================================================================
# Scenario 14: Zero shell=True AST and text check
# ============================================================================


def test_zero_shell_true_in_services() -> None:
    source_file = Path(__file__).resolve().parents[1] / "services" / "ollama_client.py"
    assert source_file.is_file(), f"Target file not found: {source_file}"

    source_text = source_file.read_text(encoding="utf-8")
    assert "shell=True" not in source_text, "Found literal shell=True in ollama_client.py"
    assert "shell = True" not in source_text, "Found spaced shell = True in ollama_client.py"

    parsed_ast = ast.parse(source_text, filename=str(source_file))

    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell":
                    val = keyword.value
                    if isinstance(val, ast.Constant) and val.value in (True, 1):
                        pytest.fail(f"AST node {node.lineno} specifies shell=True")


# ============================================================================
# Additional transport & timeout configuration checks
# ============================================================================


def test_ollama_client_timeout_validation() -> None:
    with pytest.raises(OllamaConfigurationError, match="must be a positive number"):
        OllamaClient("127.0.0.1:11434", timeout=-5.0)

    with pytest.raises(OllamaConfigurationError, match="must be a positive number"):
        OllamaClient("127.0.0.1:11434", timeout=0.0)

    with (
        patch.dict(os.environ, {"OLLAMA_TIMEOUT": "invalid_number"}),
        pytest.raises(OllamaConfigurationError, match="must be a positive number"),
    ):
        OllamaClient("127.0.0.1:11434")


def test_urllib_transport_request_mapping() -> None:
    transport = UrllibTransport()

    # Success case via mock urlopen
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"version": "1.0"}'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        status, data = transport.request(
            "GET", "http://127.0.0.1:11434/api/version", headers={}, body=None, timeout=5.0
        )
        assert status == 200
        assert data == b'{"version": "1.0"}'

    # HTTPError mapping
    http_err = urllib.error.HTTPError(
        "http://127.0.0.1:11434/api/tags",
        403,
        "Forbidden",
        {},
        io.BytesIO(b"Access Denied"),  # type: ignore[arg-type]
    )
    with (
        patch("urllib.request.urlopen", side_effect=http_err),
        pytest.raises(OllamaHTTPError) as exc_info,
    ):
        transport.request(
            "GET", "http://127.0.0.1:11434/api/tags", headers={}, body=None, timeout=5.0
        )
    assert exc_info.value.status == 403

    # URLError general mapping
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")),
        pytest.raises(OllamaConnectionError, match="Cannot reach local Ollama"),
    ):
        transport.request(
            "GET", "http://127.0.0.1:11434/api/tags", headers={}, body=None, timeout=5.0
        )

    # OSError mapping
    with (
        patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")),
        pytest.raises(OllamaConnectionError, match="Cannot reach local Ollama"),
    ):
        transport.request(
            "GET", "http://127.0.0.1:11434/api/tags", headers={}, body=None, timeout=5.0
        )
