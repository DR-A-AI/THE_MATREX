"""Ollama Client and Model Router Service for Sovereign Matrix."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Taxonomy
# ============================================================================


class OllamaError(RuntimeError):
    """Base exception for all Ollama-related failures."""


class OllamaConfigurationError(OllamaError):
    """Raised when base URL is non-loopback, invalid scheme, or malformed."""


class OllamaConnectionError(OllamaError):
    """Raised when the Ollama daemon cannot be reached."""


class OllamaTimeoutError(OllamaConnectionError):
    """Raised when an HTTP operation exceeds the configured timeout."""


class OllamaHTTPError(OllamaError):
    """Raised when Ollama returns an unexpected HTTP error code."""

    status: int

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Ollama HTTP {status}: {message}")
        self.status = status


class OllamaProtocolError(OllamaError):
    """Raised when Ollama returns invalid, truncated, or unparseable JSON."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when a requested model or alias is not installed."""


# ============================================================================
# URL Normalization & Helpers
# ============================================================================


def _get_resolv_conf_nameservers() -> set[str]:
    """Retrieve nameserver IPs from /etc/resolv.conf for WSL2 gateway discovery."""
    nameservers: set[str] = set()
    try:
        resolv_path = Path("/etc/resolv.conf")
        if resolv_path.exists():
            with open(resolv_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[0] == "nameserver":
                        nameservers.add(parts[1])
    except OSError:
        pass
    return nameservers


_ANY_IP: str = (
    "0.0.0.0"  # nosec: B104  # Used solely to normalize user-supplied 0.0.0.0 to 127.0.0.1
)


def _is_allowed_ollama_host(host: str, resolved_ip: str) -> bool:
    """Allow loopback (127.*, localhost, ::1, 0.0.0.0), WSL2 host gateway (172.*), and /etc/resolv.conf nameserver."""
    if host in {"localhost", "127.0.0.1", "::1", _ANY_IP}:
        return True
    if resolved_ip.startswith("127.") or resolved_ip in {"::1", _ANY_IP}:
        return True
    # WSL2 Windows host gateway IP range (172.*.*.*)
    if host.startswith("172.") or resolved_ip.startswith("172."):
        return True
    # WSL2 nameserver from /etc/resolv.conf
    nameservers = _get_resolv_conf_nameservers()
    return host in nameservers or resolved_ip in nameservers


def normalize_ollama_base_url(value: str | None = None) -> str:
    """Validate and normalize Ollama endpoint to loopback HTTP or WSL2 host gateway.

    Enforces loopback addresses (localhost, 127.*, [::1], 0.0.0.0), WSL2 host gateway (172.*
    or /etc/resolv.conf nameserver), and http scheme.
    Disallows external public IPs, https, and external non-loopback domains.
    Default: 'http://127.0.0.1:11434'
    """
    if value is not None:
        raw = value.strip()
        if not raw:
            raise OllamaConfigurationError("OLLAMA_HOST/OLLAMA_BASE_URL is empty")
    else:
        env_url = (os.getenv("OLLAMA_BASE_URL") or "").strip()
        env_host = (os.getenv("OLLAMA_HOST") or "").strip()
        raw = env_url or env_host or "127.0.0.1:11434"

    # Handle bare IPv6 loopback addresses e.g. ::1 or ::1:11434
    if raw in {"::1", "[::1]"}:
        raw = "http://[::1]:11434"
    elif raw.startswith("::1:"):
        port_part = raw[4:]
        raw = f"http://[::1]:{port_part}"
    elif raw.startswith("[::1]"):
        if "://" not in raw:
            raw = "http://" + raw
    elif "://" not in raw:
        raw = "http://" + raw

    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme != "http":
        raise OllamaConfigurationError(
            "Ollama endpoint must use local http:// (HTTPS is not required)"
        )

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise OllamaConfigurationError("Ollama endpoint host is missing or invalid")

    if host not in {"localhost", "127.0.0.1", "::1", _ANY_IP}:
        try:
            resolved_ip = socket.gethostbyname(host)
            if not _is_allowed_ollama_host(host, resolved_ip):
                raise OllamaConfigurationError(
                    f"Refusing non-loopback Ollama endpoint '{host}'; external connections are disabled"
                )
        except socket.gaierror as exc:
            raise OllamaConfigurationError(f"Invalid Ollama host '{host}'") from exc

    port = parsed.port if parsed.port is not None else 11434
    effective_host = "127.0.0.1" if host == _ANY_IP else host
    hostname = "[::1]" if effective_host == "::1" else effective_host
    return urlunsplit(("http", f"{hostname}:{port}", "", "", "")).rstrip("/")


def _json_object(payload: bytes, operation: str) -> dict[str, Any]:
    """Parse JSON bytes and ensure root element is a dictionary."""
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaProtocolError(f"{operation} returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise OllamaProtocolError(f"{operation} returned a JSON value instead of an object")
    return result


# ============================================================================
# Transport Interface
# ============================================================================


class UrllibTransport:
    """Injectable HTTP transport using standard library urllib.request."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        """Perform raw HTTP request via urllib.request and map socket/HTTP errors."""
        req = urllib.request.Request(
            url,
            data=body,
            headers=dict(headers),
            method=method,
        )
        try:
            # URL scheme is strictly validated as loopback http:// in normalize_ollama_base_url
            with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
                status_code: int = int(response.status)
                content: bytes = response.read()
                return status_code, content
        except urllib.error.HTTPError as exc:
            message = exc.read(1024).decode("utf-8", errors="replace").strip() or str(exc.reason)
            raise OllamaHTTPError(exc.code, message) from exc
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if isinstance(exc.reason, socket.timeout) or "timed out" in reason.lower():
                raise OllamaTimeoutError(f"Ollama request timed out after {timeout:g}s") from exc
            raise OllamaConnectionError(f"Cannot reach local Ollama at {url}: {reason}") from exc
        except TimeoutError as exc:
            raise OllamaTimeoutError(f"Ollama request timed out after {timeout:g}s") from exc
        except OSError as exc:
            raise OllamaConnectionError(f"Cannot reach local Ollama at {url}: {exc}") from exc


# ============================================================================
# Ollama Client
# ============================================================================


class OllamaClient:
    """HTTP-only Ollama client with tags, aliases, health, and chat support."""

    base_url: str
    timeout: float
    transport: Any

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = None,
        transport: Any | None = None,
    ) -> None:
        self.base_url = normalize_ollama_base_url(base_url)
        configured_timeout = timeout if timeout is not None else os.getenv("OLLAMA_TIMEOUT", "120")
        try:
            val = float(configured_timeout)
            if val <= 0:
                raise ValueError("timeout must be positive")
            self.timeout = val
        except (ValueError, TypeError) as exc:
            raise OllamaConfigurationError("OLLAMA_TIMEOUT must be a positive number") from exc
        self.transport = transport if transport is not None else UrllibTransport()
        self._models: dict[str, str] = {}
        self._tags: list[dict[str, Any]] = []

    def _transport_request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> tuple[int, bytes]:
        try:
            if hasattr(self.transport, "request"):
                result = self.transport.request(
                    method, url, headers=headers, body=body, timeout=self.timeout
                )
            else:
                result = self.transport(
                    method, url, headers=headers, body=body, timeout=self.timeout
                )
        except TimeoutError as exc:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout:g}s") from exc

        if isinstance(result, tuple):
            status, raw = result
            return int(status), bytes(raw)
        elif hasattr(result, "status") and hasattr(result, "read"):
            return int(result.status), bytes(result.read())
        else:
            raise OllamaProtocolError(f"Unexpected transport result type: {type(result)}")

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = (
            json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        )
        url = f"{self.base_url}{path}"
        status, raw = self._transport_request(
            method,
            url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            body=body,
        )
        if status < 200 or status >= 300:
            msg = raw.decode("utf-8", errors="replace")[:300]
            raise OllamaHTTPError(status, msg)
        return _json_object(raw, f"{method} {path}")

    def health(self) -> dict[str, Any]:
        """Check service availability without requiring a model or binary."""
        try:
            status, raw = self._transport_request(
                "GET",
                f"{self.base_url}/api/version",
                headers={"Accept": "application/json"},
                body=None,
            )
            if status == 404:
                return {"version": "unknown"}
            if status < 200 or status >= 300:
                msg = raw.decode("utf-8", errors="replace")[:300]
                raise OllamaHTTPError(status, msg)
            return _json_object(raw, "GET /api/version")
        except OllamaHTTPError as exc:
            if exc.status == 404:
                return {"version": "unknown"}
            raise

    def tags(self, *, refresh: bool = True) -> list[dict[str, Any]]:
        """Return list of installed model dictionaries from /api/tags."""
        if not refresh and self._tags:
            return list(self._tags)
        payload = self._request("GET", "/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaProtocolError("GET /api/tags response has no models list")
        self._tags = [item for item in models if isinstance(item, dict)]
        aliases: dict[str, str] = {}
        for item in self._tags:
            name = str(item.get("name") or item.get("model") or "").strip()
            if not name:
                continue
            aliases[name.lower()] = name
            base = name.split(":", 1)[0].lower()
            aliases.setdefault(base, name)
            extra_aliases = item.get("aliases")
            if isinstance(extra_aliases, list):
                for alias in extra_aliases:
                    alias_str = str(alias).strip()
                    if alias_str:
                        aliases[alias_str.lower()] = name
        self._models = aliases
        return list(self._tags)

    def model_names(self) -> list[str]:
        """Return list of installed model names and aliases."""
        return [
            str(item.get("name") or item.get("model"))
            for item in self.tags()
            if item.get("name") or item.get("model")
        ]

    def resolve_model(self, model: str) -> str:
        """Resolve an alias to a canonical installed model name."""
        requested = model.strip().lower()
        if not requested:
            raise OllamaModelNotFoundError("Ollama model name is empty")
        self.tags()
        resolved = self._models.get(requested)
        if not resolved:
            raise OllamaModelNotFoundError(
                f"Model '{model}' is not installed locally; run 'ollama list' to inspect installed tags"
            )
        return resolved

    def has_model(self, model: str) -> bool:
        """Return True if the model or alias is installed."""
        try:
            self.resolve_model(model)
            return True
        except OllamaError:
            return False

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call /api/chat with stream=False.

        Returns standardized response dict:
        {
            'response': str,
            'message': dict[str, Any],
            'tool_calls': list[dict[str, Any]],
            'model_used': str,
            'tier': 'local',
            'endpoint': str,
            'done': bool,
            'raw': dict[str, Any]
        }
        """
        resolved = self.resolve_model(model)
        if not messages:
            raise OllamaProtocolError("Ollama chat requires at least one message")
        payload: dict[str, Any] = {
            "model": resolved,
            "messages": list(messages),
            "stream": False,
        }
        if tools:
            payload["tools"] = list(tools)
        result = self._request("POST", "/api/chat", payload)
        message = result.get("message")
        if not isinstance(message, dict):
            raise OllamaProtocolError("POST /api/chat response has no message object")
        content = message.get("content", "")
        if not isinstance(content, str):
            raise OllamaProtocolError("POST /api/chat response has invalid message.content")
        return {
            "response": content,
            "message": message,
            "tool_calls": message.get("tool_calls", []),
            "model_used": str(result.get("model", resolved)),
            "tier": "local",
            "endpoint": self.base_url,
            "done": bool(result.get("done", True)),
            "raw": result,
        }


# ============================================================================
# Model Router
# ============================================================================


class ModelTier(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class AgentRole(str, Enum):
    NEO = "neo"
    MORPHEUS = "morpheus"
    ORACLE = "oracle"
    SMITH = "smith"
    GHOST = "ghost"
    TRINITY = "trinity"


@dataclass
class ModelEndpoint:
    name: str
    tier: ModelTier
    base_url: str
    model_id: str
    supports_tools: bool = True
    context_window: int = 8192
    requires_auth: bool = False
    auth_env_ref: str | None = None
    enabled: bool = True


class ModelRouter:
    """Local-first router mapping Matrix agent roles to preferred local models."""

    ROLE_MODELS: ClassVar[dict[AgentRole, tuple[str, ...]]] = {
        AgentRole.NEO: ("llama3.2", "gemma3"),
        AgentRole.MORPHEUS: ("qwen3-coder", "llama3.2"),
        AgentRole.ORACLE: ("deepseek-r1:8b", "llama3.2"),
        AgentRole.SMITH: ("qwen3-coder", "llama3.2"),
        AgentRole.GHOST: ("gemma3", "llama3.2"),
        AgentRole.TRINITY: ("llama3.2", "gemma3"),
    }

    client: OllamaClient
    endpoints: dict[str, ModelEndpoint]

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client if client is not None else OllamaClient()
        self.endpoints = self._build_endpoints()

    def _build_endpoints(self) -> dict[str, ModelEndpoint]:
        specs = {
            "local_qwen_coder": ("qwen3-coder", True, 32768),
            "local_llama": ("llama3.2", True, 8192),
            "local_gemma": ("gemma3", True, 8192),
            "local_deepseek": ("deepseek-r1:8b", True, 16384),
        }
        endpoints: dict[str, ModelEndpoint] = {
            key: ModelEndpoint(
                name=model,
                tier=ModelTier.LOCAL,
                base_url=f"{self.client.base_url}/api",
                model_id=model,
                supports_tools=tools,
                context_window=context,
            )
            for key, (model, tools, context) in specs.items()
        }

        # Safe decoupled check for optional external/cloud fallback
        if os.getenv("MATRIX_ENABLE_EXTERNAL_MODELS", "").lower() in {"1", "true", "yes", "on"}:
            try:
                # Decoupled optional import fallback
                import importlib

                cloud_mod = importlib.import_module("services.cloud_provider")
                load_cloud_config = getattr(cloud_mod, "load_cloud_config", None)
                if callable(load_cloud_config):
                    cloud: Any = load_cloud_config()
                    endpoints["cloud_default"] = ModelEndpoint(
                        name=cloud.model,
                        tier=ModelTier.CLOUD,
                        base_url=cloud.base_url,
                        model_id=cloud.model,
                        supports_tools=True,
                        context_window=8192,
                        requires_auth=True,
                        auth_env_ref=cloud.token_ref,
                    )
            except Exception as exc:  # noqa: BLE001
                # Fully decoupled from cloud_provider, pure local operation
                logger.debug("Optional cloud provider fallback not loaded: %s", exc)

        return endpoints

    def discover(self) -> dict[str, Any]:
        """Discover running Ollama service version and tags."""
        version = self.client.health()
        tags = self.client.tags()
        return {
            "healthy": True,
            "version": version.get("version", "unknown"),
            "models": tags,
            "base_url": self.client.base_url,
        }

    def _check_ollama_model(self, model: str) -> bool:
        return self.client.has_model(model)

    def get_endpoint(self, agent: AgentRole, prefer_local: bool = True) -> ModelEndpoint | None:
        """Find the preferred available endpoint for an agent role."""
        for model in self.ROLE_MODELS.get(agent, ()):
            if self._check_ollama_model(model):
                endpoint = next(
                    (ep for ep in self.endpoints.values() if ep.model_id == model),
                    None,
                )
                if endpoint:
                    return endpoint
                return ModelEndpoint(
                    name=model,
                    tier=ModelTier.LOCAL,
                    base_url=f"{self.client.base_url}/api",
                    model_id=model,
                    supports_tools=True,
                    context_window=8192,
                )
        return None

    def list_available(self) -> list[dict[str, Any]]:
        """List summary of all registered model endpoints."""
        return [
            {
                "name": key,
                "tier": ep.tier.value,
                "model_id": ep.model_id,
                "base_url": ep.base_url,
                "tools": ep.supports_tools,
                "context": ep.context_window,
                "auth_required": ep.requires_auth,
            }
            for key, ep in self.endpoints.items()
        ]

    async def chat(
        self,
        agent: AgentRole,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Dispatch chat request asynchronously to the agent's assigned local model."""
        endpoint = self.get_endpoint(agent)
        if endpoint:
            return await asyncio.to_thread(
                self.client.chat, endpoint.model_id, messages, tools=tools
            )

        if "cloud_default" in self.endpoints:
            try:
                import importlib

                cloud_mod = importlib.import_module("services.cloud_provider")
                cloud_chat: Any = getattr(cloud_mod, "chat", None)
                if callable(cloud_chat):
                    cloud_res: Any = await asyncio.to_thread(cloud_chat, messages, tools)
                    if isinstance(cloud_res, dict):
                        return cloud_res
            except Exception as exc:
                raise OllamaConnectionError(
                    f"No local model available and cloud fallback failed for {agent.value}: {exc}"
                ) from exc

        raise OllamaConnectionError(
            f"No installed local Ollama model available for agent {agent.value} at "
            f"{self.client.base_url}; cloud fallback is disabled"
        )


_default_router: ModelRouter | None = None


def get_router(client: OllamaClient | None = None, *, reset: bool = False) -> ModelRouter:
    """Return default or singleton ModelRouter instance."""
    global _default_router
    if _default_router is None or reset or client is not None:
        _default_router = ModelRouter(client=client)
    return _default_router


# ============================================================================
# Top-Level Health Probe
# ============================================================================


def probe() -> tuple[int, dict[str, Any]]:
    """Probe the local Ollama service. Returns (exit_code, result_dict).

    Guaranteed never to raise an unhandled exception.
    Catches OllamaError and general exceptions, returning (0, dict) or (1, dict).
    """
    base_url = "unknown"
    try:
        router = get_router()
        base_url = getattr(router.client, "base_url", "unknown")
        status = router.discover()
    except OllamaError as exc:
        return 1, {
            "ready": False,
            "service": "unavailable",
            "error": type(exc).__name__,
            "message": str(exc),
            "base_url": base_url,
        }
    except Exception as exc:  # noqa: BLE001
        return 1, {
            "ready": False,
            "service": "error",
            "error": type(exc).__name__,
            "message": str(exc),
            "base_url": base_url,
        }

    models = [
        str(item.get("name") or item.get("model"))
        for item in status.get("models", [])
        if item.get("name") or item.get("model")
    ]
    return 0, {
        "ready": True,
        "service": "ready",
        "version": status.get("version", "unknown"),
        "models": models,
        "base_url": status.get("base_url", base_url),
    }
