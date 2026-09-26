"""Unit tests for Sovereign MCP Gateway (Milestone R4).

Covers stdio JSON-RPC handshake, discovery, tool calls, JSON schema validation,
payload limits, launcher allowlist, environment isolation, risk escalation,
sovereignty pre-flight gate, and process lifecycle.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from services.mcp_gateway import (
    MAX_PAYLOAD_BYTES,
    MCPGateway,
    StdioMCPServer,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests" / "fake_mcp_stdio_server.py"


class InMemoryMCPServer:
    """Deterministic in-memory MCP server for protocol and risk testing."""

    def __init__(self, tools: Sequence[dict[str, Any]]) -> None:
        self._tools = list(tools)
        self.calls: list[tuple[str, Mapping[str, Any]]] = []
        self.closed: bool = False

    async def list_tools(self) -> list[dict[str, Any]]:
        return list(self._tools)

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any] | dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append((name, dict(arguments)))
        return {"content": [{"type": "text", "text": f"Executed {name}"}]}

    async def close(self) -> None:
        self.closed = True


class MockSovereigntyGate:
    """Mock sovereignty gate for pre-flight capability approval testing."""

    def __init__(self, granted: bool = True, reason: str = "Authorized by commander") -> None:
        self.granted = granted
        self.reason = reason
        self.checks: list[dict[str, Any]] = []

    def pre_flight(
        self, hand: str, action: str, target: str, risk: str, approval_id: str
    ) -> dict[str, Any]:
        self.checks.append(
            {
                "hand": hand,
                "action": action,
                "target": target,
                "risk": risk,
                "approval_id": approval_id,
            }
        )
        return {"granted": self.granted, "reason": self.reason}


# -------------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stdio_handshake_and_discovery() -> None:
    """Verify JSON-RPC 2.0 handshake (initialize/notifications) and tool discovery."""
    server = StdioMCPServer(
        command=[sys.executable, str(FIXTURE_PATH)],
        cwd=ROOT,
        timeout_s=5.0,
    )
    gateway = MCPGateway(timeout_s=5.0)
    gateway.register_server("fake_stdio", server)

    try:
        # Handshake verification
        init_res = await server.initialize()
        assert init_res.get("protocolVersion") == "2024-11-05"

        # Discovery verification
        tools = await gateway.discover()
        assert len(tools) >= 1
        tool_names = [t["function"]["name"] for t in tools]
        assert "fixture_echo" in tool_names

        # Registry checks
        assert gateway.has_tool("fixture_echo") is True
        cap = gateway.registry.get("fixture_echo")
        assert cap is not None
        assert cap.name == "fixture_echo"
        assert cap.risk == "LOW"
        assert cap.requires_approval is False
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stdio_tool_call_success() -> None:
    """Verify invoking a discovered tool over stdio returns the expected result."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    gateway = MCPGateway()
    gateway.register_server("fake_stdio", server)

    try:
        await gateway.discover()
        result = await gateway.call("fixture_echo", {"count": 42})
        assert result["ok"] is True
        assert "content" in result
        assert result["content"] == [{"type": "text", "text": "42"}]
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_argument_schema_validation_type_mismatch() -> None:
    """Verify argument type mismatch fails validation without server execution."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    gateway = MCPGateway()
    gateway.register_server("fake_stdio", server)

    try:
        await gateway.discover()
        # count must be integer, not string
        result = await gateway.call("fixture_echo", {"count": "42"})
        assert result["ok"] is False
        assert "must be integer" in result["error"]
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_argument_schema_validation_missing_required() -> None:
    """Verify missing required argument fails validation."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    gateway = MCPGateway()
    gateway.register_server("fake_stdio", server)

    try:
        await gateway.discover()
        result = await gateway.call("fixture_echo", {})
        assert result["ok"] is False
        assert "missing required argument" in result["error"]
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_argument_schema_validation_unknown_property() -> None:
    """Verify unexpected property when additionalProperties=False fails validation."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    gateway = MCPGateway()
    gateway.register_server("fake_stdio", server)

    try:
        await gateway.discover()
        result = await gateway.call("fixture_echo", {"count": 10, "extra": "forbidden"})
        assert result["ok"] is False
        assert "unknown argument" in result["error"]
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_nul_byte_rejection_in_arguments() -> None:
    """Verify NUL byte anywhere in arguments dictionary is rejected fail-closed."""
    fake_server = InMemoryMCPServer(
        [
            {
                "name": "echo_text",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            }
        ]
    )
    gateway = MCPGateway()
    gateway.register_server("mem", fake_server)
    await gateway.discover()

    result = await gateway.call("echo_text", {"text": "hello\x00world"})
    assert result["ok"] is False
    assert "NUL byte" in result["error"]
    assert len(fake_server.calls) == 0


@pytest.mark.asyncio
async def test_argument_payload_limit_enforced() -> None:
    """Verify arguments exceeding MAX_PAYLOAD_BYTES (64KB) are rejected."""
    fake_server = InMemoryMCPServer(
        [
            {
                "name": "echo_text",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            }
        ]
    )
    gateway = MCPGateway()
    gateway.register_server("mem", fake_server)
    await gateway.discover()

    huge_text = "A" * (MAX_PAYLOAD_BYTES + 100)
    result = await gateway.call("echo_text", {"text": huge_text})
    assert result["ok"] is False
    assert "output limit" in result["error"]
    assert len(fake_server.calls) == 0


@pytest.mark.asyncio
async def test_unregistered_tool_returns_error() -> None:
    """Verify calling an unregistered tool returns an error dict."""
    gateway = MCPGateway()
    result = await gateway.call("unknown_tool", {})
    assert result["ok"] is False
    assert "capability not registered" in result["error"]


def test_launcher_allowlist_enforcement() -> None:
    """Verify only allowlisted launchers can be configured for StdioMCPServer."""
    # Disallowed binary name
    with pytest.raises(ValueError, match="unavailable or disallowed MCP launcher"):
        StdioMCPServer(command=["malicious_launcher", "arg1"])

    # Disallowed shell scripts
    with pytest.raises(ValueError, match="unavailable or disallowed MCP launcher"):
        StdioMCPServer(command=["bash", "script.sh"])

    # Valid allowlisted launcher (python executable)
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)])
    assert server.command[0] == sys.executable


def test_environment_variable_isolation() -> None:
    """Verify manifest environment mappings strictly enforce *_REF naming."""
    # Invalid: literal value without _REF suffix
    with pytest.raises(ValueError, match="MCP environment must contain \\*_REF values only"):
        StdioMCPServer(
            command=[sys.executable, str(FIXTURE_PATH)],
            env={"API_KEY": "raw_secret_value"},
        )

    # Valid: ends with _REF
    server = StdioMCPServer(
        command=[sys.executable, str(FIXTURE_PATH)],
        env={"API_KEY": "HOST_API_KEY_REF"},
    )
    assert server.environment == {"API_KEY": "HOST_API_KEY_REF"}


@pytest.mark.asyncio
async def test_risk_and_approval_inference() -> None:
    """Verify destructive verbs and annotations automatically escalate risk to HIGH."""
    test_tools = [
        {
            "name": "delete_resource",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "write_file",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "create_user",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "execute_task",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "custom_query",
            "annotations": {"readOnlyHint": False},
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "destructive_tool",
            "annotations": {"destructiveHint": True},
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_status",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]

    server = InMemoryMCPServer(test_tools)
    gateway = MCPGateway()
    gateway.register_server("test_srv", server)
    await gateway.discover()

    # Destructive verbs -> HIGH risk & requires_approval=True
    for verb_tool in ["delete_resource", "write_file", "create_user", "execute_task"]:
        cap = gateway.registry.get(verb_tool)
        assert cap is not None
        assert cap.risk == "HIGH", f"{verb_tool} risk should be HIGH"
        assert cap.requires_approval is True, f"{verb_tool} requires_approval should be True"

    # Annotations -> HIGH risk & requires_approval=True
    for anno_tool in ["custom_query", "destructive_tool"]:
        cap = gateway.registry.get(anno_tool)
        assert cap is not None
        assert cap.risk == "HIGH", f"{anno_tool} risk should be HIGH"
        assert cap.requires_approval is True, f"{anno_tool} requires_approval should be True"

    # Non-destructive read tool -> LOW risk & requires_approval=False
    read_cap = gateway.registry.get("get_status")
    assert read_cap is not None
    assert read_cap.risk == "LOW"
    assert read_cap.requires_approval is False


@pytest.mark.asyncio
async def test_sovereignty_pre_flight_gate() -> None:
    """Verify tool requiring approval checks sovereignty gate."""
    server = InMemoryMCPServer(
        [
            {
                "name": "delete_database",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]
    )

    # 1. No sovereignty gate configured -> Fail closed
    gateway_no_gate = MCPGateway(servers={"srv": server})
    await gateway_no_gate.discover()
    result_no_gate = await gateway_no_gate.call("delete_database", {})
    assert result_no_gate["ok"] is False
    assert "sovereignty gate required" in result_no_gate["error"]

    # 2. Gate denies approval -> Blocked
    gate_denied = MockSovereigntyGate(granted=False, reason="Safety override: blocked")
    gateway_denied = MCPGateway(servers={"srv": server}, sovereignty=gate_denied)
    await gateway_denied.discover()
    result_denied = await gateway_denied.call("delete_database", {}, approval_id="app-1")
    assert result_denied["ok"] is False
    assert result_denied["error"] == "Safety override: blocked"
    assert len(gate_denied.checks) == 1
    assert gate_denied.checks[0]["risk"] == "HIGH"

    # 3. Gate grants approval -> Executed
    gate_allowed = MockSovereigntyGate(granted=True)
    gateway_allowed = MCPGateway(servers={"srv": server}, sovereignty=gate_allowed)
    await gateway_allowed.discover()
    result_allowed = await gateway_allowed.call("delete_database", {}, approval_id="app-2")
    assert result_allowed["ok"] is True
    assert len(server.calls) == 1


@pytest.mark.asyncio
async def test_clean_process_shutdown() -> None:
    """Verify child processes are cleanly terminated and resources released upon close()."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    await server.initialize()
    assert server.process is not None
    proc = server.process

    await server.close()
    assert server.process is None
    # Wait briefly to confirm process is no longer running
    await asyncio.sleep(0.1)
    assert proc.returncode is not None


@pytest.mark.asyncio
async def test_from_manifest_loader() -> None:
    """Verify MCPGateway.from_manifest correctly reads configuration."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        manifest_data = {
            "mcp_gateway": {
                "timeout_seconds": 12.0,
                "servers": {
                    "shell": {
                        "enabled": True,
                        "command": [sys.executable, str(FIXTURE_PATH)],
                    },
                    "github": {
                        "enabled": False,
                        "command": ["npx", "dummy"],
                    },
                },
            }
        }
        json.dump(manifest_data, f)
        temp_path = f.name

    try:
        gateway = MCPGateway.from_manifest(temp_path)
        assert "shell" in gateway.servers
        assert "github" not in gateway.servers  # disabled

        tools = await gateway.discover()
        assert any(t["function"]["name"] == "fixture_echo" for t in tools)
        res = await gateway.call("fixture_echo", {"count": 7})
        assert res["ok"] is True
        assert res["content"] == [{"type": "text", "text": "7"}]
        await gateway.close()
    finally:
        os.unlink(temp_path)


def test_run_allowed_synchronous_adapter() -> None:
    """Verify run_allowed executes synchronously when no event loop is active."""
    server = InMemoryMCPServer(
        [
            {
                "name": "sync_tool",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]
    )
    gateway = MCPGateway(servers={"mem": server})
    result = gateway.run_allowed("mem", "sync_tool", {})
    assert result["ok"] is True
    assert "Executed sync_tool" in str(result)


@pytest.mark.asyncio
async def test_mcp_smoke() -> None:
    """Full end-to-end smoke test function verifying fixture discovery and invocation."""
    server = StdioMCPServer(command=[sys.executable, str(FIXTURE_PATH)], cwd=ROOT)
    gateway = MCPGateway()
    gateway.register_server("fake_stdio", server)

    try:
        tools = await gateway.discover()
        assert len(tools) >= 1
        tool_name = tools[0]["function"]["name"]
        assert tool_name == "fixture_echo"

        call_res = await gateway.call(tool_name, {"count": 99})
        assert call_res["ok"] is True
        assert call_res["content"][0]["text"] == "99"
    finally:
        await gateway.close()
