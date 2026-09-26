"""Deterministic stdio MCP fixture for gateway tests.

Implements JSON-RPC 2.0 handshake, tool discovery, and tool execution
over standard input and output streams.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def read_frame() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    if line.strip() == b"":
        return {}
    if line.lower().startswith(b"content-length:"):
        headers = [line]
        while True:
            header_line = sys.stdin.buffer.readline()
            if not header_line or header_line in (b"\r\n", b"\n"):
                break
            headers.append(header_line)
        length_line = next(x for x in headers if x.lower().startswith(b"content-length:"))
        length = int(length_line.split(b":", 1)[1].strip())
        raw_body = sys.stdin.buffer.read(length)
        return json.loads(raw_body.decode("utf-8"))
    return json.loads(line.decode("utf-8"))


def main() -> None:
    for request in iter(read_frame, None):
        if not request or "id" not in request:
            continue
        method = request.get("method")
        req_id = request.get("id")
        if method == "initialize":
            result: dict[str, Any] = {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "fake-mcp-server", "version": "1.0"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "fixture_echo",
                        "description": "Echoes back the provided integer count",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"count": {"type": "integer"}},
                            "required": ["count"],
                            "additionalProperties": False,
                        },
                    }
                ]
            }
        elif method == "tools/call":
            params = request.get("params", {})
            args = params.get("arguments", {})
            count = args.get("count", 0)
            result = {"content": [{"type": "text", "text": str(count)}]}
        else:
            result = {}
        raw = json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
