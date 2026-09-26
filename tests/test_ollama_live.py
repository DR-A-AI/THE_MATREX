"""Live integration test for Ollama on Windows host gateway (llama3.2).

Performs genuine network probe and chat call against Windows host gateway.
Skips gracefully if the Ollama daemon is offline or unreachable.
Marked with @pytest.mark.live.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.ollama_client import (
    OllamaClient,
    get_router,
    probe,
)


def _discover_windows_host_ip() -> str:
    """Discover Windows host gateway IP from OLLAMA_HOST, localhost, or /etc/resolv.conf."""
    if os.getenv("OLLAMA_HOST"):
        return os.environ["OLLAMA_HOST"]

    # In WSL2 with mirrored networking or Windows host, 127.0.0.1 connects directly
    if _is_ollama_reachable("http://127.0.0.1:11434"):
        return "http://127.0.0.1:11434"

    try:
        resolv_path = Path("/etc/resolv.conf")
        if resolv_path.exists():
            with open(resolv_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[0] == "nameserver":
                        candidate = f"http://{parts[1]}:11434"
                        if _is_ollama_reachable(candidate):
                            return candidate
    except OSError:
        pass
    return "http://127.0.0.1:11434"


def _is_ollama_reachable(base_url: str) -> bool:
    """Check whether Ollama endpoint responds to HTTP request."""
    try:
        import urllib.error
        import urllib.request

        with urllib.request.urlopen(f"{base_url}/api/version", timeout=1.5):  # nosec: B310
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


HOST_URL = _discover_windows_host_ip()
OLLAMA_AVAILABLE = _is_ollama_reachable(HOST_URL)


@pytest.mark.live
@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason=f"Ollama daemon not reachable at {HOST_URL}")
def test_ollama_live_probe_and_chat() -> None:
    """Real live integration test against llama3.2 on Windows host."""
    os.environ["OLLAMA_HOST"] = HOST_URL
    os.environ["OLLAMA_DEFAULT_MODEL"] = "llama3.2"
    get_router(reset=True)

    # 1. Real probe
    code, result = probe()
    assert code == 0
    assert result.get("ready") is True

    # 2. Real chat with llama3.2
    client = OllamaClient(base_url=HOST_URL, timeout=30.0)
    response = client.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": "Say MATRIX_OK"}],
    )
    assert response.get("done") is True
    content = response.get("response") or response.get("message", {}).get("content", "")
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.live
def test_ollama_probe_graceful_handling() -> None:
    """Probe must always return clean status tuple without unhandled exceptions."""
    os.environ["OLLAMA_HOST"] = HOST_URL
    code, result = probe()
    assert code in (0, 1)
    assert isinstance(result, dict)
    assert "ready" in result
    assert "service" in result
