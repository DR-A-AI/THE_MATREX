"""Unit and integration tests for Sovereign Matrix MCP Server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.sovereign_mcp_server import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    MCPServerCore,
    create_fastapi_app,
)


@pytest.fixture
def mcp_server(tmp_path: Path) -> MCPServerCore:
    return MCPServerCore(matrix_root=tmp_path)


@pytest.mark.asyncio
async def test_mcp_initialize(mcp_server: MCPServerCore) -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    res = await mcp_server.handle_request(req)
    assert res is not None
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 1
    result = res["result"]
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == SERVER_NAME
    assert result["serverInfo"]["version"] == SERVER_VERSION
    assert "tools" in result["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list(mcp_server: MCPServerCore) -> None:
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    res = await mcp_server.handle_request(req)
    assert res is not None
    assert res["id"] == 2
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "matrix_engine_status" in tool_names
    assert "matrix_safe_shell" in tool_names
    assert "matrix_chat_agent" in tool_names
    assert "matrix_memory_search" in tool_names
    assert "groq_workspace_connector" in tool_names


@pytest.mark.asyncio
async def test_mcp_tool_call_engine_status(mcp_server: MCPServerCore) -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "matrix_engine_status", "arguments": {}},
    }
    res = await mcp_server.handle_request(req)
    assert res is not None
    assert res["id"] == 3
    assert res["result"]["isError"] is False
    content = json.loads(res["result"]["content"][0]["text"])
    assert content["status"] == "ONLINE"
    assert "agents" in content


@pytest.mark.asyncio
async def test_mcp_tool_call_groq_connector(mcp_server: MCPServerCore) -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "groq_workspace_connector",
            "arguments": {
                "service": "gmail",
                "action": "search_emails",
                "query": "is:unread",
            },
        },
    }
    res = await mcp_server.handle_request(req)
    assert res is not None
    assert res["id"] == 4
    content = json.loads(res["result"]["content"][0]["text"])
    assert content["connector"] == "connector_gmail"
    assert content["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_mcp_tool_call_safe_shell_allowlist(mcp_server: MCPServerCore) -> None:
    # Denied command
    req_denied = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "matrix_safe_shell", "arguments": {"command": "rm -rf /"}},
    }
    res = await mcp_server.handle_request(req_denied)
    assert res is not None
    assert res["result"]["isError"] is True
    assert "not in the Sovereign safe allowlist" in res["result"]["content"][0]["text"]

    # Allowed command
    req_allowed = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {"name": "matrix_safe_shell", "arguments": {"command": "git status"}},
    }
    res = await mcp_server.handle_request(req_allowed)
    assert res is not None
    assert "[Exit code" in res["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_notifications_handled(mcp_server: MCPServerCore) -> None:
    req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    res = await mcp_server.handle_request(req)
    assert res is None
    assert mcp_server.initialized is True


def test_fastapi_remote_mcp_app(mcp_server: MCPServerCore) -> None:
    from fastapi.testclient import TestClient

    app = create_fastapi_app(mcp_server)
    client = TestClient(app)

    # 1. Health root
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert root_res.json()["name"] == SERVER_NAME

    # 2. Tools GET endpoint
    tools_res = client.get("/tools")
    assert tools_res.status_code == 200
    assert len(tools_res.json()["tools"]) >= 5

    # 3. JSON-RPC POST /mcp endpoint
    rpc_res = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
    )
    assert rpc_res.status_code == 200
    data = rpc_res.json()
    assert data["id"] == 10
    assert len(data["result"]["tools"]) >= 5
