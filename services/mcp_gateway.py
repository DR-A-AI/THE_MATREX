"""Model Context Protocol (MCP) Gateway Service for Sovereign Matrix.

Provides stdio JSON-RPC 2.0 communication, capability registration,
schema validation, launcher allowlist verification, and risk/approval escalation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import types
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

logger = logging.getLogger("Sovereign.MCP_Gateway")

# Strict Launcher Allowlist
ALLOWED_LAUNCHERS: frozenset[str] = frozenset(
    {
        "github-mcp-server",
        "chrome-devtools-mcp",
        "syncfusion-mcp",
        "shell-mcp",
        "npx",
        "node",
        "node.exe",
        "uvx",
        "python",
        "python3",
        "powershell",
        "pwsh",
        "powershell.exe",
        Path(sys.executable).name.lower(),
    }
)

MAX_PAYLOAD_BYTES: int = 65536


# Exception Hierarchy
class MCPError(Exception):
    """Base exception for MCP operations."""


class MCPProtocolError(MCPError, RuntimeError):
    """Raised on invalid JSON-RPC 2.0 frames or unexpected message types."""


class MCPValidationError(MCPError, ValueError):
    """Raised when argument parameters violate the tool's JSON Schema."""


class MCPTimeoutError(MCPError, TimeoutError):
    """Raised when an MCP server operation exceeds the configured timeout."""


class MCPApprovalRequiredError(MCPError, PermissionError):
    """Raised when a high-risk tool is invoked without sovereign pre-flight approval."""


def _check_no_nul_bytes(val: Any, prefix: str) -> None:
    """Recursively checks that no string values contain NUL bytes."""
    if isinstance(val, str):
        if "\x00" in val:
            raise MCPValidationError(f"{prefix} contains a NUL byte")
    elif isinstance(val, Mapping):
        for k, v in val.items():
            _check_no_nul_bytes(v, f"{prefix}.{k}")
    elif isinstance(val, (list, tuple)):
        for i, item in enumerate(val):
            _check_no_nul_bytes(item, f"{prefix}[{i}]")


def _validate_json_schema(schema: Mapping[str, Any], value: Any, path: str = "$") -> None:
    """Fail-closed validation for the JSON-schema subset used by MCP tools."""
    kind = schema.get("type")
    valid = {
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if kind in valid and not valid[kind]:
        raise MCPValidationError(f"{path} must be {kind}")
    if kind == "object" and isinstance(value, Mapping):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, Mapping) or not isinstance(required, list):
            raise MCPValidationError(f"invalid object schema at {path}")
        missing = [key for key in required if key not in value]
        if missing:
            raise MCPValidationError(f"missing required argument(s): {missing}")
        if schema.get("additionalProperties", True) is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise MCPValidationError(f"unknown argument(s): {sorted(unknown)}")
        for key, child in properties.items():
            if key in value and isinstance(child, Mapping):
                _validate_json_schema(child, value[key], f"{path}.{key}")
    if "enum" in schema and value not in schema["enum"]:
        raise MCPValidationError(f"{path} is not an allowed value")


@dataclass(frozen=True)
class CapabilityInput:
    name: str
    kind: str = "text"
    required: bool = False


@dataclass
class Capability:
    name: str
    description: str = ""
    server_name: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    risk: str = "LOW"  # "LOW" | "MEDIUM" | "HIGH"
    requires_approval: bool = False
    source: str = "mcp"
    command: tuple[str, ...] = ()
    inputs: tuple[CapabilityInput, ...] = ()
    audit_action: str = ""

    def validate_values(self, values: Sequence[object] = ()) -> None:
        required_count = sum(input_.required for input_ in self.inputs)
        if len(values) < required_count or len(values) > len(self.inputs):
            raise MCPValidationError(
                f"{self.name} expects {required_count}-{len(self.inputs)} typed input(s), got {len(values)}"
            )
        for spec, value in zip(self.inputs, values):
            if not isinstance(value, str) or not value:
                raise MCPValidationError(f"{self.name}.{spec.name} must be a non-empty string")
            if "\x00" in value:
                raise MCPValidationError(f"{self.name}.{spec.name} contains a NUL byte")
            if spec.kind not in {"path", "text", "pattern"}:
                raise MCPValidationError(f"unsupported capability input kind: {spec.kind}")
            if spec.kind == "path" and value.startswith("-"):
                raise MCPValidationError(f"{self.name}.{spec.name} must be a workspace path")

    def build_command(self, values: Sequence[str] = ()) -> list[str]:
        self.validate_values(values)
        if not self.command:
            raise MCPValidationError(f"{self.name} is implemented by the execution hand")
        return [*self.command, *values]

    def tool_definition(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        if self.input_schema and "properties" in self.input_schema:
            properties = dict(self.input_schema.get("properties", {}))
            required = list(self.input_schema.get("required", []))
        elif self.inputs:
            for inp in self.inputs:
                properties[inp.name] = {"type": "string"}
                if inp.required:
                    required.append(inp.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description
                or f"Execute the registered {self.name} capability.",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }


class CapabilityRegistry:
    """Registry with explicit names and input schemas (default deny)."""

    def __init__(self, capabilities: Sequence[Capability] = ()) -> None:
        self._capabilities: dict[str, Capability] = {cap.name: cap for cap in capabilities}

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities))

    def describe(self, name: str) -> dict[str, Any]:
        cap = self._capabilities.get(name)
        if cap is None:
            raise KeyError(name)
        return {
            "name": cap.name,
            "description": cap.description,
            "server_name": cap.server_name,
            "inputs": tuple(
                {
                    "name": inp.name,
                    "kind": inp.kind,
                    "required": inp.required,
                }
                for inp in cap.inputs
            ),
            "risk": cap.risk,
            "requires_approval": cap.requires_approval,
            "audit_action": cap.audit_action,
        }

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [self._capabilities[name].tool_definition() for name in sorted(self._capabilities)]

    @property
    def capabilities(self) -> dict[str, Capability]:
        return self._capabilities

    def __contains__(self, name: str) -> bool:
        return name in self._capabilities

    def __len__(self) -> int:
        return len(self._capabilities)

    def __iter__(self) -> Iterator[Capability]:
        return iter(self._capabilities.values())


class MCPServer(Protocol):
    async def list_tools(self) -> list[dict[str, Any]]: ...
    async def call_tool(
        self, name: str, arguments: Mapping[str, Any] | dict[str, Any]
    ) -> dict[str, Any]: ...
    async def close(self) -> None: ...


class StdioMCPServer:
    """Manages an external or in-process stdio MCP server process over JSON-RPC 2.0."""

    def __init__(
        self,
        command: Sequence[str] | list[str],
        env: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        max_output_bytes: int = MAX_PAYLOAD_BYTES,
        environment: dict[str, str] | None = None,
        cwd: Path | str | None = None,
    ) -> None:
        # Cross-platform Windows adaptation: if command[0] is Unix path (e.g. /usr/bin/node),
        # but launcher (node) is found on Windows PATH, use the local executable.
        cmd_executable = command[0]
        launcher = Path(cmd_executable).name.lower()
        if sys.platform == "win32" and shutil.which(launcher):
            cmd_executable = launcher
            command = [cmd_executable, *command[1:]]

        if sys.platform == "win32":
            win_command = []
            for part in command:
                if isinstance(part, str) and part.startswith("/mnt/"):
                    p_parts = part.split("/")
                    if len(p_parts) >= 3 and len(p_parts[2]) == 1:
                        drive = p_parts[2].upper()
                        rest = "\\".join(p_parts[3:])
                        win_command.append(f"{drive}:\\{rest}")
                        continue
                win_command.append(part)
            command = win_command

        if launcher not in ALLOWED_LAUNCHERS or (
            shutil.which(cmd_executable) is None and not Path(cmd_executable).exists()
        ):
            raise ValueError(f"unavailable or disallowed MCP launcher: {command[0]}")

        target_env = env if env is not None else environment
        clean_env: dict[str, str] = {}
        if target_env is not None:
            if not isinstance(target_env, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) or not v.endswith("_REF")
                for k, v in target_env.items()
            ):
                raise ValueError("MCP environment must contain *_REF values only")
            clean_env = dict(target_env)

        self.command = tuple(command)
        self.timeout_s = float(timeout_s)
        self.max_output_bytes = int(max_output_bytes)
        self.environment = clean_env
        self.cwd = Path(cwd or Path(__file__).resolve().parent.parent)
        self.process: asyncio.subprocess.Process | None = None
        self._request_id: int = 0
        self._init_result: dict[str, Any] = {}

    async def _read(self) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None:
            raise MCPProtocolError("MCP server process is not running")

        while True:
            first = await self.process.stdout.readline()
            if not first:
                raise MCPProtocolError("MCP server closed stdout")
            if first.strip():
                break

        if first.lower().startswith(b"content-length:"):
            headers = [first]
            while True:
                line = await self.process.stdout.readline()
                headers.append(line)
                if line in (b"\r\n", b"\n"):
                    break
            length_line = next(x for x in headers if x.lower().startswith(b"content-length:"))
            length = int(length_line.split(b":", 1)[1].strip())
            if length < 0 or length > self.max_output_bytes:
                raise MCPProtocolError("MCP output exceeds limit")
            raw = await self.process.stdout.readexactly(length)
        else:
            raw = first

        if len(raw) > self.max_output_bytes:
            raise MCPProtocolError("MCP output exceeds limit")

        try:
            value = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MCPProtocolError(f"invalid JSON from MCP server: {exc}") from exc

        if not isinstance(value, dict):
            raise MCPProtocolError("MCP response must be an object")
        return value

    async def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise MCPProtocolError("MCP server process is not running")

        raw = json.dumps(message, separators=(",", ":")).encode("utf-8")
        if len(raw) > self.max_output_bytes:
            raise MCPProtocolError("MCP request exceeds limit")

        self.process.stdin.write(raw + b"\n")
        await self.process.stdin.drain()

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._request_id += 1
        req_id = self._request_id
        await self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        try:
            response = await asyncio.wait_for(self._read(), self.timeout_s)
        except asyncio.TimeoutError as exc:
            raise MCPTimeoutError(
                f"MCP request '{method}' timed out after {self.timeout_s}s"
            ) from exc

        if response.get("id") != req_id:
            raise MCPProtocolError("MCP response id mismatch")
        if "error" in response:
            raise MCPProtocolError(f"MCP error: {response['error']}")
        result = response.get("result", {})
        if not isinstance(result, dict):
            raise MCPProtocolError("MCP result must be an object")
        return result

    async def _start(self) -> None:
        env = os.environ.copy()
        for name, ref in self.environment.items():
            ref_target = ref[:-4]
            if ref_target not in os.environ:
                raise RuntimeError(f"missing environment reference: {ref}")
            env[name] = os.environ[ref_target]

        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=False,
            env=env,
            cwd=str(self.cwd),
            limit=max(self.max_output_bytes * 2, 1_048_576),
        )  # nosec: B603

        self._init_result = await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "matrix-local-gateway", "version": "1.0"},
            },
        )
        # Notify server initialization completed (notification frame without id)
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    async def initialize(self) -> dict[str, Any]:
        if self.process is None:
            await self._start()
        return self._init_result

    async def list_tools(self) -> list[dict[str, Any]]:
        if self.process is None:
            await self._start()
        result = await self._request("tools/list", {})
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise MCPProtocolError("MCP tools/list result must contain a 'tools' list")
        return tools

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any] | dict[str, Any]
    ) -> dict[str, Any]:
        if self.process is None:
            await self._start()
        result = await self._request("tools/call", {"name": name, "arguments": dict(arguments)})
        if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > self.max_output_bytes:
            raise MCPProtocolError("MCP result exceeds limit")
        return result

    async def close(self) -> None:
        process = self.process
        if process is not None:
            if process.stdin and not process.stdin.is_closing():
                process.stdin.close()
                try:
                    await process.stdin.wait_closed()
                except (ConnectionError, RuntimeError, BrokenPipeError):
                    pass
            if process.returncode is None:
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                except ProcessLookupError:
                    pass
            transport = getattr(process, "_transport", None)
            if transport is not None:
                transport.close()
            self.process = None

    async def __aenter__(self) -> Self:
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.close()


class MCPGateway:
    """Model Context Protocol Gateway for Sovereign Matrix."""

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        servers: Mapping[str, MCPServer] | None = None,
        audit_sink: Any = None,
        timeout_s: float = 30.0,
        sovereignty: Any = None,
        max_payload_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> None:
        self.registry = registry if registry is not None else CapabilityRegistry()
        self.servers: dict[str, MCPServer] = dict(servers or {})
        self.audit_sink = audit_sink
        self.timeout_s = float(timeout_s)
        self.sovereignty = sovereignty
        self.max_payload_bytes = int(max_payload_bytes)
        self._owners: dict[str, str] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._tool_defs: dict[str, dict[str, Any]] = {}

    @property
    def capabilities(self) -> dict[str, Capability]:
        return self.registry.capabilities

    def register_server(self, name: str, server: MCPServer) -> None:
        self.servers[name] = server

    @classmethod
    def from_manifest(cls, manifest: Path | str | None = None, **kwargs: Any) -> MCPGateway:
        """Build a gateway from workspace manifest (all servers default off)."""
        path = Path(manifest or Path(__file__).resolve().parent.parent / "workspace.manifest.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        section = data.get("mcp_gateway", {})
        servers: dict[str, MCPServer] = {}
        for server_name, config in section.get("servers", {}).items():
            if server_name not in {"github", "chrome_devtools", "syncfusion", "shell"}:
                raise ValueError(f"unknown MCP server: {server_name}")
            if not config.get("enabled", False):
                continue
            command = config.get("command")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(part, str) or not part for part in command)
            ):
                raise ValueError(f"invalid command for {server_name}")

            cmd_executable = command[0]
            launcher = Path(cmd_executable).name.lower()
            if sys.platform == "win32" and shutil.which(launcher):
                cmd_executable = launcher
                command = [cmd_executable, *command[1:]]

            if sys.platform == "win32":
                win_command = []
                for part in command:
                    if isinstance(part, str) and part.startswith("/mnt/"):
                        p_parts = part.split("/")
                        if len(p_parts) >= 3 and len(p_parts[2]) == 1:
                            drive = p_parts[2].upper()
                            rest = "\\".join(p_parts[3:])
                            win_command.append(f"{drive}:\\{rest}")
                            continue
                    win_command.append(part)
                command = win_command

            if launcher not in ALLOWED_LAUNCHERS or (
                shutil.which(cmd_executable) is None and not Path(cmd_executable).exists()
            ):
                raise ValueError(f"unavailable or disallowed MCP launcher: {command[0]}")

            env = config.get("environment", {})
            if not isinstance(env, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) or not v.endswith("_REF")
                for k, v in env.items()
            ):
                raise ValueError("MCP environment must contain *_REF values only")

            server_timeout = float(
                config.get("timeout_seconds", section.get("timeout_seconds", 15.0))
            )
            server_max_output = int(
                config.get("max_output_bytes", section.get("max_output_bytes", MAX_PAYLOAD_BYTES))
            )
            servers[server_name] = StdioMCPServer(
                command,
                timeout_s=server_timeout,
                max_output_bytes=server_max_output,
                environment=env,
            )
        return cls(CapabilityRegistry(), servers, **kwargs)

    def _audit(self, action: str, target: str, result: str, risk: str = "LOW") -> None:
        if self.audit_sink:
            try:
                self.audit_sink(action=action, target=target, result=result, risk=risk)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"MCP audit sink error: {exc}")

    async def discover(self) -> list[dict[str, Any]]:
        """Queries registered servers, extracts tools, infers risk, and registers capabilities."""
        discovered: list[dict[str, Any]] = []
        for server_name, server in self.servers.items():
            tools = await asyncio.wait_for(server.list_tools(), self.timeout_s)
            for tool in tools:
                name = tool.get("name")
                if not isinstance(name, str) or not name:
                    continue

                input_schema = tool.get("inputSchema") or {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                }
                props = input_schema.get("properties", {})
                required = set(input_schema.get("required", []))
                annotations = tool.get("annotations") or {}

                inferred_risk = str(tool.get("risk", "LOW")).upper()
                inferred_approval = bool(tool.get("requires_approval", False))
                inferred_approval = inferred_approval or bool(annotations.get("destructiveHint"))
                inferred_approval = inferred_approval or (annotations.get("readOnlyHint") is False)
                inferred_approval = inferred_approval or name.lower().startswith(
                    ("delete", "write", "create", "update", "send", "execute")
                )
                if inferred_approval and inferred_risk == "LOW":
                    inferred_risk = "HIGH"

                inputs = tuple(
                    CapabilityInput(key, kind="text", required=key in required) for key in props
                )

                cap = self.registry.get(name)
                if cap is None:
                    cap = Capability(
                        name=name,
                        description=str(tool.get("description", "")),
                        server_name=server_name,
                        input_schema=input_schema,
                        risk=inferred_risk,
                        requires_approval=inferred_approval,
                        source="mcp",
                        inputs=inputs,
                        audit_action=f"mcp.{server_name}.{name}",
                    )
                    self.registry.register(cap)
                else:
                    cap.risk = inferred_risk
                    cap.requires_approval = inferred_approval
                    cap.server_name = server_name
                    cap.input_schema = input_schema

                self._schemas[name] = input_schema
                self._tool_defs[name] = tool
                self._owners[name] = server_name
                discovered.append(cap.tool_definition())

        return discovered

    def has_tool(self, name: str) -> bool:
        return name in self._owners and self.registry.get(name) is not None

    async def call(
        self,
        name: str,
        arguments: Mapping[str, Any] | dict[str, Any],
        *,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Validates arguments against JSON Schema, checks approval gate, and calls the tool."""
        capability = self.registry.get(name)
        owner = self._owners.get(name)
        if capability is None or owner is None or owner not in self.servers:
            self._audit("mcp.tool_call", name, "unknown")
            return {"ok": False, "error": f"capability not registered: {name}"}

        try:
            if not isinstance(arguments, Mapping):
                raise TypeError("arguments must be an object")

            # Check NUL bytes
            _check_no_nul_bytes(arguments, name)

            # Check argument payload size limit
            raw_args = json.dumps(arguments, ensure_ascii=False).encode("utf-8")
            if len(raw_args) > self.max_payload_bytes:
                raise MCPValidationError("MCP arguments exceed output limit")

            # Validate against schema
            schema = self._schemas.get(name, {"type": "object"})
            _validate_json_schema(schema, arguments)

            # Validate typed input values if capability specifies them
            expected_keys = {spec.name for spec in capability.inputs}
            if expected_keys and capability.inputs:
                unknown = set(arguments) - expected_keys
                if unknown and schema.get("additionalProperties", True) is False:
                    raise MCPValidationError(f"unknown typed input(s): {sorted(unknown)}")
                values = [
                    arguments[spec.name] for spec in capability.inputs if spec.name in arguments
                ]
                if all(isinstance(v, str) for v in values):
                    capability.validate_values(values)
                elif len(values) < sum(spec.required for spec in capability.inputs):
                    raise MCPValidationError(f"missing required input(s) for {name}")

            # Risk and Sovereign Pre-Flight Gate check
            if capability.requires_approval:
                reason: Any = None
                if self.sovereignty is None:
                    reason = "sovereignty gate required for approved capability"
                else:
                    check = self.sovereignty.pre_flight(
                        "execution_hand",
                        "command_allowlisted",
                        target=name,
                        risk=capability.risk,
                        approval_id=approval_id or "",
                    )
                    reason = None if check.get("granted") else check.get("reason", "denied")
                if reason:
                    self._audit("mcp.tool_call", name, "blocked", capability.risk)
                    return {"ok": False, "error": reason}

            self._audit("mcp.tool_call.requested", name, "requested", capability.risk)
            result = await asyncio.wait_for(
                self.servers[owner].call_tool(name, arguments), self.timeout_s
            )
            output = result if isinstance(result, dict) else {"result": result}
            self._audit("mcp.tool_call.executed", name, "success", capability.risk)
            return {"ok": True, **output}

        except asyncio.TimeoutError:
            self._audit("mcp.tool_call.executed", name, "timeout", capability.risk)
            return {"ok": False, "error": f"timeout after {self.timeout_s}s"}
        except (ValueError, TypeError, KeyError, MCPValidationError) as exc:
            self._audit("mcp.tool_call.executed", name, "blocked", capability.risk)
            return {"ok": False, "error": str(exc)[:200]}
        except Exception as exc:  # noqa: BLE001
            self._audit("mcp.tool_call.executed", name, "error", capability.risk)
            return {"ok": False, "error": str(exc)[:200]}

    async def close(self) -> None:
        """Closes all underlying server transports cleanly."""
        for server in self.servers.values():
            close_fn = getattr(server, "close", None)
            if close_fn is not None:
                res = close_fn()
                if asyncio.iscoroutine(res):
                    await res

    def run_allowed(
        self,
        server: str,
        tool: str,
        arguments: Mapping[str, Any] | None = None,
        approval_id: str = "",
    ) -> dict[str, Any]:
        """Synchronous execution-hand adapter for non-async callers."""

        async def execute() -> dict[str, Any]:
            if server not in self.servers:
                return {"ok": False, "error": f"MCP server is not configured: {server}"}
            await self.discover()
            if self._owners.get(tool) != server:
                return {"ok": False, "error": f"tool is not owned by server: {tool}"}
            return await self.call(tool, arguments or {}, approval_id=approval_id)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(execute())
        return {"ok": False, "error": "MCP run_allowed cannot block an active event loop"}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.close()


async def run_sovereign_mcp_gateway() -> None:
    """Standalone launcher entrypoint for Sovereign MCP Gateway."""
    logger.info("=" * 50)
    logger.info("🛡️ SOVEREIGN MCP GATEWAY INITIATED 🛡️")
    logger.info("=" * 50)
    gateway = MCPGateway()
    manifest_path = Path(__file__).resolve().parent.parent / "workspace.manifest.json"
    if manifest_path.exists():
        try:
            gateway = MCPGateway.from_manifest(manifest_path)
            tools = await gateway.discover()
            logger.info(f"Discovered {len(tools)} MCP capabilities from manifest.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Manifest discovery bypassed: {exc}")

    logger.info("✅ Sovereign MCP Gateway Online. Awaiting requests...")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Sovereign MCP Gateway shutting down.")
    finally:
        await gateway.close()


if __name__ == "__main__":
    asyncio.run(run_sovereign_mcp_gateway())
