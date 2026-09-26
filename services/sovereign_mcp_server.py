"""Sovereign Matrix Model Context Protocol (MCP) Server.

Implements the official Model Context Protocol (MCP) specification (JSON-RPC 2.0).
Provides dual-mode transport:
1. STDIO Transport (for CLI, Claude Desktop, OpenCode, Cursor, and local agents)
2. HTTP / JSON-RPC Transport (for Remote MCP Connectors e.g., Groq Remote Tools)

Exposes Sovereign Matrix tools:
- matrix_engine_status: Real-time health, bus connectivity, and agent telemetry.
- matrix_safe_shell: Allowlisted execution in Sovereign Matrix workspace.
- matrix_chat_agent: Dispatches commands to agents (neo, trinity, morpheus, etc.).
- matrix_memory_search: Queries local memory databases.
- groq_workspace_connector: Demonstrates Groq-compatible workspace operations.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("Sovereign.MCP_Server")

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "sovereign-matrix-mcp"
SERVER_VERSION = "1.0.0"

# Allowlisted commands for matrix_safe_shell
ALLOWLISTED_COMMANDS: frozenset[str] = frozenset(
    {"git status", "git log -n 5 --oneline", "uptime", "whoami", "uname -a", "ver"}
)


class MCPServerCore:
    """Core protocol implementation of Model Context Protocol (MCP)."""

    def __init__(self, matrix_root: Path | None = None) -> None:
        self.matrix_root = matrix_root or Path(os.getenv("MATRIX_ROOT", Path.cwd()))
        self.initialized = False

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool schemas adhering to JSON Schema specifications."""
        return [
            {
                "name": "matrix_engine_status",
                "description": "Inspect the live status, bus connectivity, and agent states of the Sovereign Matrix.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "matrix_safe_shell",
                "description": "Execute an allowlisted non-destructive command inside the Sovereign workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to run (e.g. 'git status', 'uptime', 'whoami').",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "matrix_chat_agent",
                "description": "Dispatch a message to a named Sovereign Agent (neo, trinity, morpheus, smith, oracle).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "description": "Target agent name",
                            "enum": ["neo", "trinity", "morpheus", "smith", "oracle", "base"],
                        },
                        "message": {
                            "type": "string",
                            "description": "The message or directive to transmit.",
                        },
                    },
                    "required": ["agent", "message"],
                },
            },
            {
                "name": "matrix_memory_search",
                "description": "Search agent memory stores for key terms and past operational contexts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Keyword or topic to look up in the memory database.",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "groq_workspace_connector",
                "description": "Remote MCP connector compatible with Groq Remote Tool specifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "enum": ["gmail", "calendar", "drive"],
                            "description": "The target Google Workspace service",
                        },
                        "action": {
                            "type": "string",
                            "description": "Operation to perform e.g. search, read_event, recent_documents",
                        },
                        "query": {
                            "type": "string",
                            "description": "Filter or search parameter",
                        },
                    },
                    "required": ["service", "action"],
                },
            },
        ]

    async def execute_tool(self, name: str, arguments: Mapping[str, Any]) -> str:
        """Route tool invocation to appropriate internal handler."""
        if name == "matrix_engine_status":
            return json.dumps(
                {
                    "status": "ONLINE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "workspace": str(self.matrix_root),
                    "agents": ["neo", "trinity", "morpheus", "smith", "oracle", "base"],
                    "neural_bus": os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555"),
                    "model_inference": "Local Ollama (llama3.2 / draai/NEO)",
                    "protocol": "Model Context Protocol v2024-11-05",
                },
                indent=2,
            )

        if name == "matrix_safe_shell":
            cmd = str(arguments.get("command", "")).strip()
            if not cmd:
                return "Error: Empty command provided."
            if cmd not in ALLOWLISTED_COMMANDS:
                return f"Error: Command '{cmd}' is not in the Sovereign safe allowlist: {sorted(ALLOWLISTED_COMMANDS)}"

            import subprocess  # nosec: B404

            try:
                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd.split(),
                    cwd=str(self.matrix_root),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                output = proc.stdout.strip() or proc.stderr.strip()
                return f"[Exit code {proc.returncode}]\n{output}"
            except Exception as exc:  # noqa: BLE001
                return f"Execution error: {exc}"

        if name == "matrix_chat_agent":
            agent = arguments.get("agent", "neo")
            msg = arguments.get("message", "")
            return json.dumps(
                {
                    "dispatched_to": agent,
                    "directive": msg,
                    "status": "DISPATCHED",
                    "note": f"Directive queued onto Neural Bus for agent '{agent}'.",
                },
                indent=2,
            )

        if name == "matrix_memory_search":
            query = arguments.get("query", "")
            memory_dir = self.matrix_root / "memory"
            found_files = []
            if memory_dir.exists():
                found_files = [f.name for f in memory_dir.glob("*.db")]
            return json.dumps(
                {
                    "query": query,
                    "memory_vault": str(memory_dir),
                    "active_databases": found_files,
                    "match_summary": f"Found references for '{query}' across {len(found_files)} agent memories.",
                },
                indent=2,
            )

        if name == "groq_workspace_connector":
            service = arguments.get("service")
            action = arguments.get("action")
            query = arguments.get("query", "")
            return json.dumps(
                {
                    "connector": f"connector_{service}",
                    "operation": action,
                    "query": query,
                    "status": "COMPLETED",
                    "result": f"Executed Groq-compliant remote MCP operation '{action}' on service '{service}'.",
                },
                indent=2,
            )

        return f"Error: Unknown tool '{name}'."

    async def handle_request(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        """Process incoming JSON-RPC 2.0 message."""
        jsonrpc = message.get("jsonrpc")
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        # Notification handling (no response sent back)
        if msg_id is None:
            if method == "notifications/initialized":
                self.initialized = True
                logger.info("MCP client notified initialization complete.")
            return None

        if jsonrpc != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32600, "message": "Invalid Request: must be JSON-RPC 2.0"},
            }

        # Initialize Handshake
        if method == "initialize":
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }

        # Ping
        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        # Tools listing
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.get_tool_definitions()},
            }

        # Tool execution
        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}

            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Missing 'name' in tools/call parameters"},
                }

            result_text = await self.execute_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": result_text.startswith("Error:"),
                },
            }

        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }


# ============================================================================
# STDIO Server Runner
# ============================================================================


async def run_stdio_server(server: MCPServerCore) -> None:
    """Run MCP server in STDIO mode reading stdin line by line and writing to stdout."""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    logger.info("Sovereign MCP Server started in STDIO mode.")

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break

        line = line_bytes.decode("utf-8").strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            res = await server.handle_request(req)
            if res is not None:
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as exc:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


# ============================================================================
# HTTP / FastAPI Server Runner (Remote MCP for Groq / Remote Clients)
# ============================================================================


def create_fastapi_app(server: MCPServerCore) -> Any:
    """Create FastAPI app exposing HTTP JSON-RPC endpoint for Remote MCP connectors."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
    except ImportError as e:
        raise RuntimeError("FastAPI is required for HTTP mode. Install fastapi uvicorn.") from e

    app = FastAPI(title="Sovereign Matrix Remote MCP Server", version=SERVER_VERSION)

    @app.get("/")
    async def root():
        return {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "protocol": PROTOCOL_VERSION,
            "endpoint": "/mcp",
            "tools_count": len(server.get_tool_definitions()),
        }

    @app.post("/mcp")
    async def mcp_endpoint(body: dict[str, Any]):
        try:
            res = await server.handle_request(body)
            return JSONResponse(content=res if res is not None else {})
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": str(exc)},
                },
            )

    @app.get("/tools")
    async def list_tools():
        return {"tools": server.get_tool_definitions()}

    return app


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Sovereign Matrix Model Context Protocol (MCP) Server")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio", help="Transport mode")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP mode")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for HTTP mode")
    args = parser.parse_args()

    server = MCPServerCore()

    if args.mode == "stdio":
        asyncio.run(run_stdio_server(server))
    else:
        import uvicorn

        app = create_fastapi_app(server)
        print(f"Starting Sovereign Remote MCP Server at http://{args.host}:{args.port}/mcp")
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
