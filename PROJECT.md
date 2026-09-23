# PROJECT SPECIFICATION — Sovereign Matrix

**System**: Sovereign Matrix Autonomous Agent Operating System  
**Repository**: `DR-A-AI/THE_MATREX` (`/mnt/e/matrex-dev`)  
**Specification Version**: 2.0.0  
**Status**: Active Production Specification  
**Authority**: Sovereign Constitution & Sovereign Commander (Dr. Anas Hilal)  

---

## 1. System Architecture Overview

The Sovereign Matrix is an air-gapped, zero-trust autonomous multi-agent operating environment designed for deterministic coordination, asynchronous event distribution, local neural inference, and strict security isolation.

```text
                               ┌─────────────────────────────────────────┐
                               │             USER / DASHBOARD            │
                               │  Vite/React Dashboard (:5173)           │
                               └────────────────────┬────────────────────┘
                                                    │ WebSocket / REST
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │           SERVICES / UI BRIDGE          │
                               │  FastAPI (:8000) - Clerk Auth           │
                               │  list(active_connections) under lock    │
                               └────────────────────┬────────────────────┘
                                                    │ ZMQ DEALER
                                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                ZERO-TRUST NEURAL BUS                                        │
 │   NeuralBusRouter (ZMQ ROUTER :5555)                                                        │
 │   - HMAC-SHA256 signature verification with mandatory SOVEREIGN_BUS_SECRET                 │
 │   - Anti-replay nonce cache (5s window) & message TTL check (60s limit)                     │
 └──────────────┬───────────────────────────┬─────────────────────────────┬────────────────────┘
                │                           │                             │
                ▼                           ▼                             ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
 │       AGENT CLUSTER       │ │     CRAWLER SUBSYSTEM     │ │     LOCAL BRAIN & RUNTIME │
 │ - Neo (Leader/Execution)  │ │ - AssistantCrawler        │ │ - OllamaClient            │
 │ - Trinity (Extractor)     │ │   (The Key Distributor)   │ │   (Loopback :11434 only)  │
 │ - Morpheus (Strategist)   │ │ - MemoryCrawler           │ │ - SafeShell               │
 │ - Smith (Enforcer)        │ │   (Sanitization & SQLite) │ │   (Strict allowlist)      │
 │ - Oracle (Synthesizer)    │ │ - LibrarianCrawler        │ │ - MCPGateway              │
 │ - Base Agent (Stash <= 2) │ │   (Skill file scanner)    │ │   (Stdio JSON-RPC 2.0)    │
 └───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
```

### 1.1 Constitutional Invariants (Immutable Architecture)
Per `SOVEREIGN_CONSTITUTION.md`:
1. **Supreme Rule**: Commander authority (Dr. Anas Hilal) is absolute. Zero autonomy on architectural governance.
2. **The Blind Extractors**: Neo and Trinity extract keys from external boundaries and broadcast `EventType.TOKEN_EXTRACTED`. They are strictly forbidden from storing keys in persistent memory.
3. **The Distributor**: `AssistantCrawler` is the sole authorized listener to `TOKEN_EXTRACTED`. It validates tokens, masks them as `***{last4}`, stores them in `AuthVault`, and broadcasts `EventType.KEY_INJECT`.
4. **Emergency Token Stash**: Every `MatrixAgent` base class maintains `self.emergency_token_stash` (`MAX_STASH_SIZE = 2`, `TTL = 300s`). Agents are strictly forbidden from JIT-requesting keys directly.
5. **Zero-Trust Neural Bus**: All inter-component ZMQ messages must be HMAC-SHA256 signed with `SOVEREIGN_BUS_SECRET`. Nonces are tracked with a 5-second replay window; messages older than 60 seconds TTL are discarded.
6. **Windows Event Loop Invariant**: On Windows (`win32`), `WindowsSelectorEventLoopPolicy` is required. The Proactor event loop is strictly forbidden due to ZMQ socket incompatibilities.
7. **Absolute Shell Isolation**: `shell=True` is prohibited across the entire repository without exception. All subprocesses run via argv lists with explicit bounds.

---

## 2. Complete Feature Inventory (Deduplicated)

Merged and deduplicated across all three Phase 0 Specification Miners (Core, Brain/Shell, and MCP/Skills/Crawlers):

| # | Subsystem | Feature Name | Description | Inputs | Outputs | Error / Guard Behavior |
|---|---|---|---|---|---|---|
| 1 | Bus Core | `NeuralBusClient` | HMAC-SHA256 authenticated ZMQ DEALER client with anti-replay and TTL checks | `EventPayload`, `SOVEREIGN_BUS_SECRET`, `endpoint` | Signed multipart ZMQ frames `[sig, payload]` | Drops unverified signatures, duplicate nonces, or expired TTL (>60s) with CRITICAL log |
| 2 | Bus Core | `NeuralBusRouter` | Central non-blocking ZMQ ROUTER binding to port 5555, client tracking and eviction | Inbound DEALER frames `[sender, sig, body]` | Multipart broadcast to all other registered clients | Evicts client on `zmq.ZMQError` (EAGAIN/unreachable), logs error |
| 3 | Bus Core | Event Registration Framing | DEALER identity handshake with ROUTER without leaking to bus broadcast | Frame `[b"REGISTER", b""]` | Client added to router `active_clients` set | Filtered by Router (`signature == b"REGISTER"` is never broadcast) |
| 4 | Schema | Pydantic Event Schema | Canonical `EventPayload` model with strict validation and UTC ISO timestamps | `event_type`, `source_agent_id`, `correlation_id`, `payload`, `metadata` | Validated Pydantic v2 `EventPayload` model | `pydantic.ValidationError` if types or structure invalid |
| 5 | Security | Aegis Topology Validator | Pre-commit AST static analyzer enforcing constitutional rules | Python files (`base_agent.py`, `assistant_crawler.py`) | Exit 0 if valid; error message and exit 1 if violated | Blocks execution if `emergency_token_stash` or `assistant_crawler.py` missing |
| 6 | Security | Deterministic Guillotine | Regex and AST filter rejecting dangerous dynamic code execution patterns | Arbitrary code/action string | `True` (allowed) or `False` (severed) | Detects and blocks `pickle`, `eval`, `exec`, `os.system`, `subprocess.Popen` |
| 7 | Security | Zero-Trust HMAC Signing | Cryptographic HMAC-SHA256 signature generator and verifier | Secret string, message bytes, 16-byte nonce, timestamp | Hex digest signature string | Rejects corrupted, tampered, or mismatched frames |
| 8 | UI Bridge | Snapshot WebSocket Broadcast | Broadcasts ZMQ agent events to connected WebSockets under thread lock | Inbound ZMQ events (`STATE_UPDATE`, `TASK_COMPLETED`, etc.) | JSON text frame over WebSocket | Iterates over `list(active_connections)` snapshot under lock; catches disconnects cleanly |
| 9 | UI Bridge | Clerk JWT WebSocket Auth | Authenticates dashboard UI client via Clerk token before accepting commands | JSON message `{"clerk_token": "<jwt>"}` | JSON `{"type": "auth", "status": "success"}` | Rejection with `{"type": "auth", "status": "failed"}` and socket closure |
| 10 | UI Bridge | Uninitialized Bus Guard | Protects against forwarding user commands before bus connection is active | Inbound UI text payload | Sends `USER_COMMAND` event to bus | Logs error `"bus_client is not initialized"` without raising unhandled crash |
| 11 | Agent Core | Emergency Token Stash | In-memory token storage in `MatrixAgent` base with TTL and bounded capacity | `KEY_INJECT` event payload with `scope` and `token` | Stashed token dictionary with expiry timestamp | Drops invalid tokens; purges expired; evicts oldest when stash exceeds `MAX_STASH_SIZE=2` |
| 12 | Agent Core | Agent Base Lifecycle | Managed startup, registration, topic subscription, and shutdown for agents | Agent ID, bus endpoint, subscriptions | Running async agent task loop | Graceful cancellation, bus unregistration, resource cleanup |
| 13 | Agent Core | Dynamic Workspace Resolution | Resolves workspace path dynamically across Linux and Windows | `MATRIX_ROOT` env var or `Path.cwd()` | Absolute resolved `Path` | Falls back to current working directory if env var unset |
| 14 | Agent Core | Safe Local Shell Tool | Subprocess execution using argv list, dynamic workspace root, and length limits | Command string (max 8192 chars) | Formatted string `STDOUT:\n...\nSTDERR:\n...` | Returns error on empty command, >8192 chars, or non-zero exit; uses `shell=False` |
| 15 | Key Routing | APIKeyRouter Round-Robin | Rotates available Gemini API keys from environment configuration | `.env` variables (`GEMINI_API_KEY`, backups) | Active API key string or `None` | Returns `None` if keys exhausted; logs rotation without leaking secret |
| 16 | Key Routing | JIT Token Provisioning Server | Responds to explicit `REQUEST_TOKEN:<scope>` requests via ZMQ ROUTER on port 5557 | ZMQ multipart request | ZMQ multipart `TOKEN_GRANTED:<token_id>` | Rejects invalid commands; tokens tracked in AuthVault |
| 17 | Crawlers | AssistantCrawler (The Distributor) | Intercepts `TOKEN_EXTRACTED` events and broadcasts `KEY_INJECT` | `TOKEN_EXTRACTED` event from Neo/Trinity | `KEY_INJECT` event broadcast to bus | Validates token string, masks token in logs as `***{last4}` |
| 18 | Crawlers | Memory Sanitization & Sorting | Strips conversational noise and greetings (Arabic & English) | Raw text string | Cleaned content string | Preserves code blocks and core facts; drops boilerplate |
| 19 | Crawlers | Isolated Per-Agent SQLite Storage | Stores permanent and temporary memories in per-agent SQLite databases | Memory key, category, content | Boolean success status; emits `MEMORY_STORED` | Emits `EventType.ERROR` if database insertion fails; uses parameterized SQL |
| 20 | Crawlers | Aegis QA Code Gate | Evaluates memory/skill content with code patterns (`def `, `import `, `eval(`) | Content string | Boolean pass/fail | Emits `EventType.ERROR` and rejects storage on violation |
| 21 | Crawlers | Async LibrarianCrawler | Asynchronous skill file scanner with path-traversal prevention | `target_dir` Path, Markdown files | JSON schema mapping skills and previews | Drops and logs `SECURITY BREACH: Path traversal` if outside target |
| 22 | Crawlers | Token Interception & Masking | Intercepts extracted tokens and guarantees masking across all log sinks | Inbound token string | Masked string `***{last4}` | Enforces minimal 4-character mask; replaces short tokens with `***` |
| 23 | R2 Ollama | `normalize_ollama_base_url` | Normalizes host/URL string into `http://<loopback>:<port>` and enforces loopback | `value: str \| None = None` | Normalized URL string (e.g. `http://127.0.0.1:11434`) | Raises `OllamaConfigurationError` if non-loopback, https, invalid, or empty |
| 24 | R2 Ollama | `UrllibTransport` | Injectable HTTP transport using stdlib `urllib.request` | `method, url, headers, body, timeout` | `tuple[int, bytes]` | Maps errors to `OllamaHTTPError`, `OllamaTimeoutError`, `OllamaConnectionError` |
| 25 | R2 Ollama | `OllamaClient.health` | Checks Ollama service availability without loading models | None | `dict[str, Any]` (e.g. `{"version": "..."}`) | Returns `{"version": "unknown"}` on 404; raises connection error on failure |
| 26 | R2 Ollama | `OllamaClient.tags` | Lists installed models and builds model alias index | `refresh: bool = True` | `list[dict[str, Any]]` | Raises `OllamaProtocolError` if response JSON missing `models` list |
| 27 | R2 Ollama | `OllamaClient.resolve_model` | Resolves requested model name or alias to canonical installed model tag | `model: str` | Canonical model tag string (e.g. `llama3.2:latest`) | Raises `OllamaModelNotFoundError` if not installed or empty |
| 28 | R2 Ollama | `OllamaClient.chat` | Sends `/api/chat` request with `stream=false` and optional tools | `model, messages, tools=None` | Standardized result dict with `response`, `message`, `tier="local"` | Raises `OllamaProtocolError` on empty messages/invalid response |
| 29 | R2 Ollama | `ModelRouter` | Local-first model router mapping Matrix agent roles to preferred local models | `client: OllamaClient \| None = None` | Router instance | Builds local endpoint catalog for Neo, Morpheus, Oracle, Smith, Ghost, Trinity |
| 30 | R2 Ollama | `probe()` | Top-level service health probe callable from CLI or python snippet | None | `tuple[int, dict[str, Any]]` | Never raises unhandled exception. Returns exit code 0 on healthy, 1 on unavailable |
| 31 | R3 Safe Shell | `ShellCapabilityValidator` | Validates command, arguments, and scripts against strict allowlists | `workspace_root: Path, timeout_s: int = 60` | Validator instance | Returns `(bool, str)` or raises `DisallowedCommandError` |
| 32 | R3 Safe Shell | Shell Allowlist (`python`, `git`) | Strictly constrains executable commands. `python` requires `-m <module>`. `git` restricted to `status, log, diff`. | `command: str, args: list[str]` | `tuple[bool, str]` | Rejects any non-allowlisted command, arbitrary scripts, write git subcommands |
| 33 | R3 Safe Shell | Bash Script Execution | Constrains bash execution to scripts physically located within workspace root | `script_path, args=None, cwd=None` | Result dict `{"ok": bool, "returncode": int, "output": str}` | Rejects path traversal (`../`), files >1MB, missing files, missing bash binary |
| 34 | R3 Safe Shell | CLI Command Allowlist | Validates and dispatches Matrix CLI commands (`check`, `verify`, `models`, `status`, `run`) | `command: str, args=None` | Result dict | Rejects non-allowlisted CLI commands; `run` requires task argument |
| 35 | R3 Safe Shell | Workspace Path Scoping | Enforces canonical path containment inside `workspace_root` | `path: str \| Path` | Canonical `Path` inside workspace | Raises `WorkspaceEscapeError` if path traverses or points outside root |
| 36 | R3 Safe Shell | Process Isolation (`shell=False`) | Executes commands strictly via argv lists without shell expansion | `cmd: list[str], cwd: Path, timeout: float` | `subprocess.CompletedProcess` | `shell=False` enforced; command timeouts caught and reported |
| 37 | R3 Safe Shell | Execution Audit Logging | Logs every command attempt (action, target, risk, result) via logger and audit sink | `action, target, risk, result, details` | None | Recorded regardless of whether command succeeded or was blocked |
| 38 | R3 Safe Shell | Ollama Tool Definitions | Exposes capabilities in OpenAI/Ollama function calling schema | None | `list[dict[str, Any]]` | Generates JSON schemas for `shell`, `bash`, `cli` tools |
| 39 | R4 MCP | Stdio JSON-RPC Handshake | Performs `initialize` and `notifications/initialized` protocol exchange over stdio | Child process stdin/stdout, JSON-RPC frames | Protocol version, capabilities, clientInfo | Raises `RuntimeError` on closed stdout or id mismatch |
| 40 | R4 MCP | Tool Discovery (`discover`) | Queries MCP servers for available tools and registers them as typed capabilities | Server instances conforming to `MCPServer` | List of function-calling tool definition dicts | Discards tools with invalid names; times out after `timeout_s` |
| 41 | R4 MCP | Automatic Risk & Approval Inference | Automatically infers `risk="HIGH"` and `requires_approval=True` for destructive verbs | Tool `inputSchema`, `annotations`, tool name | Updated `Capability.risk` and `Capability.requires_approval` | Defaults to `LOW`/`False` if no heuristics match |
| 42 | R4 MCP | Tool Calling (`call`) | Validates arguments against JSON schema and invokes tool on owning server | Tool name, arguments dict, approval_id | `{"ok": True, **output}` | Returns `{"ok": False, "error": str}` on validation error or timeout |
| 43 | R4 MCP | Argument & Buffer Limit Enforcement | Restricts argument and response size to prevent memory exhaustion (64KB default) | Serialized JSON payload bytes | Validated payload | Raises `ValueError` or `RuntimeError` if payload exceeds limit |
| 44 | R4 MCP | Environment Variable Isolation | Mandates manifest environment values use `*_REF` references resolved from host env | Manifest `environment` mapping | Cleaned child process env dict | Raises `ValueError` if environment value does not end with `_REF` |
| 45 | R4 MCP | Launcher Allowlist Guard | Restricts executable launchers for MCP servers to known safe binaries | Executable path/name from manifest command | Verified command list | Raises `ValueError` for unknown or missing launcher binaries |
| 46 | R4 MCP | Offline Smoke Test Pattern | Non-interactive verification running stdio MCP server via `sys.executable` | Local python script (`fake_mcp_stdio_server.py`) | Exit code 0, discovered tool name printed | Non-zero exit code if handshake or call fails |
| 47 | R5 Skills | Metadata Discovery (`discover`) | Reads skill manifest without code import/execution; computes sha256 skill ID | Path to manifest JSON file | Discovered record dict with `stage="DISCOVERED"` | Returns error dict if file unreadable or malformed |
| 48 | R5 Skills | SKILL_CONTRACT v1.0 Validation | Validates contract fields and restricts allowed tools to closed allowlist | Skill record, reviewer name | Validated record dict with `stage="VALIDATED"` | Returns record with `stage="REJECTED"` and specific rejection reason |
| 49 | R5 Skills | Closed Tool Allowlist | Limits tools to 6 declarative labels: `docs.read`, `memory.read`, `memory.search`, etc. | `record["allowed_tools"]` list | Validated tool set | Rejects skill if any unknown tool is requested |
| 50 | R5 Skills | Offensive Pattern Blocking | Flags offensive skills (`active-directory-attack`, `ransomware`, etc.) as HIGH risk | Name, capabilities, source ref | Assessed risk string (`LOW`, `MEDIUM`, `HIGH`) | HIGH risk skills rejected during validation |
| 51 | R5 Skills | Metadata Packaging (`prepare`) | Packages validated skill into `curated/{skill_id}` with manifests | Validated record | Prepared record with `stage="PREPARED"` | Raises `ValueError` if stage is not `VALIDATED` |
| 52 | R5 Skills | Curated Quarantine Gate (`validate_curated`) | Audits curated packages and moves incomplete, mismatched, or unsafe ones to `quarantine/` | Curated directory files | `{"valid": [...], "quarantined": [...]}` | Moves failing packages to `quarantine/` with collision suffix |
| 53 | R5 Skills | Dual Review Approval Bus Event | Smith and Morpheus emit approval event on neural bus | Skill review verdict | Neural bus `SKILL_REVIEW_APPROVED` event | Rejection / blocked promotion if approval event missing |
| 54 | R5 Skills | Promotion Approval (`promote`) | Promotes prepared skill with Commander approval; records audit | Prepared record, `commander_approval=True` | Promoted record with `stage="PROMOTED"` | Raises `PermissionError` if commander approval is missing |
| 55 | R5 Skills | Agent Binding Injection (`inject`) | Binds promoted skill to target agents via `bindings.json` access log | Promoted record, list of agent names | Injected record with `stage="INJECTED"` | Raises `ValueError` if stage is not `PROMOTED` |
| 56 | R5 Skills | Bus Schema Additions | Adds `SKILL_PROMOTED` and `SKILL_REVIEW_APPROVED` to `EventType` enum | Enum members in `core/models.py` | Validated Pydantic models on bus | Schema validation failure if unknown event emitted |

---

## 3. Milestones Table

| Milestone | Title | Owner | Dependencies | Core Deliverables | Exit Gate / Quality Check |
|---|---|---|---|---|---|
| **Phase 0** | Planning & Mining | Planning Engineer | Miner Reports | `MASTER_PLAN.md`, `PROJECT.md` | Complete architectural alignment & team approval |
| **R1** | Phase 1 Commit | Integration Engineer | Phase 0 | Branch `feat/engine-quality-and-bus-remediation`, Commit 62 files | `git status` clean, Ruff 0, Black clean, Bandit 0, Pytest 25/25 |
| **R2** | Ollama Client | Integration Engineer | R1 | `services/ollama_client.py`, `tests/test_ollama_client.py` | `probe()` exits 0/1 without crash, pytest 100%, 0 `shell=True` |
| **R3** | Safe Shell | Security Reviewer | R1 | `services/safe_shell.py`, `tests/test_safe_shell.py`, agent wiring | Disallowed command raises, path traversal raises, 0 `shell=True` |
| **R4** | MCP Gateway | Integration Engineer | R1, R3, `B3_mcp_audit.md` | `services/mcp_gateway.py`, `tests/test_mcp_smoke.py` | Non-interactive offline smoke test exits 0, prints >=1 tool name |
| **R5** | Skills & Crawlers | Crawler Auditor & Bus Architect | R1, `B4_skill_inventory.md` | `core/models.py` additions, `services/skill_loader.py`, `tests/test_skill_pipeline.py` | Crawlers 15/15 passed, Skill pipeline tests pass, bus event required |
| **Global Gate** | Final Verification | Security Reviewer & Team Lead | R1-R5 | `PHASE2_COMPLETE.md` authored, Zero merge to main | Ruff 0, Black clean, Bandit 0, Pytest >= 30 passed, Aegis pass |

---

## 4. Interface Contracts

All new services must implement these exact interface contracts, signatures, and exception taxonomies:

### 4.1 `services/ollama_client.py` (Local Brain Client)

```python
"""Ollama Client and Model Router Service for Sovereign Matrix."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

# Exception Hierarchy
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

# URL Normalization
def normalize_ollama_base_url(value: str | None = None) -> str:
    """Validates and normalizes Ollama endpoint to loopback HTTP only.
    Disallows external IPs, https, and non-loopback domains.
    Default: 'http://127.0.0.1:11434'
    """
    ...

# Transport Interface
class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        """Performs raw HTTP request via urllib.request and maps socket/HTTP errors."""
        ...

# Client Contract
class OllamaClient:
    base_url: str
    timeout: float
    transport: Any

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = None,
        transport: Any | None = None,
    ) -> None: ...

    def health(self) -> dict[str, Any]:
        """Returns {'version': str} from /api/version."""
        ...

    def tags(self, *, refresh: bool = True) -> list[dict[str, Any]]:
        """Returns list of installed model dictionaries from /api/tags."""
        ...

    def model_names(self) -> list[str]:
        """Returns list of installed model names and aliases."""
        ...

    def resolve_model(self, model: str) -> str:
        """Resolves an alias to a canonical installed model name."""
        ...

    def has_model(self, model: str) -> bool:
        """Returns True if the model or alias is installed."""
        ...

    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Calls /api/chat with stream=False.
        Returns standardized response dict:
        {
            'response': str,
            'message': dict[str, Any],
            'tool_calls': list[dict[str, Any]],
            'model_used': str,
            'tier': 'local'
        }
        """
        ...

# Model Router Contract
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
    ROLE_MODELS: dict[AgentRole, tuple[str, ...]] = {
        AgentRole.NEO: ("llama3.2", "gemma3"),
        AgentRole.MORPHEUS: ("qwen3-coder", "llama3.2"),
        AgentRole.ORACLE: ("deepseek-r1:8b", "llama3.2"),
        AgentRole.SMITH: ("qwen3-coder", "llama3.2"),
        AgentRole.GHOST: ("gemma3", "llama3.2"),
        AgentRole.TRINITY: ("llama3.2", "gemma3"),
    }

    client: OllamaClient

    def __init__(self, client: OllamaClient | None = None) -> None: ...
    def discover(self) -> dict[str, Any]: ...
    def get_endpoint(self, agent: AgentRole, prefer_local: bool = True) -> ModelEndpoint | None: ...
    def list_available(self) -> list[dict[str, Any]]: ...
    async def chat(
        self,
        agent: AgentRole,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

def get_router() -> ModelRouter: ...

# Top-level Health Probe
def probe() -> tuple[int, dict[str, Any]]:
    """Probes the local Ollama service. Returns (exit_code, result_dict).
    Guaranteed not to raise an unhandled exception.
    Exit code 0 on healthy service, 1 on unavailable or misconfigured.
    """
    ...
```

---

### 4.2 `services/safe_shell.py` (Sandboxed Shell Execution)

```python
"""Safe Shell Execution and Capability Validator for Sovereign Matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

# Exception Hierarchy
class SafeShellError(Exception):
    """Base exception for safe shell errors."""

class DisallowedCommandError(SafeShellError):
    """Raised when an executable command or argument is not on the allowlist."""

class WorkspaceEscapeError(SafeShellError):
    """Raised when a path escapes the designated workspace root."""

class CommandTimeoutError(SafeShellError):
    """Raised when execution exceeds the configured timeout."""

class ScriptExecutionError(SafeShellError):
    """Raised when a workspace script fails validation or execution."""

# Capability Validator Contract
class ShellCapabilityValidator:
    workspace_root: Path
    timeout_s: int

    SHELL_ALLOWLIST: dict[str, dict[str, Any]] = {
        "python": {
            "description": "Python executed with specific safe modules only",
            "allowed_modules": {"compileall", "pytest", "unittest"},
            "max_args": 10,
        },
        "git": {
            "description": "Git read-only diagnostic commands",
            "allowed_subcommands": {"status", "log", "diff"},
            "allowed_flags": {"--short", "--oneline", "-10", "--stat", "-n", "-s", "--name-only", "--name-status"},
        },
    }

    CLI_ALLOWLIST: dict[str, dict[str, Any]] = {
        "check": {"description": "Check workspace syntax", "approval": False},
        "verify": {"description": "Verify runtime state", "approval": False},
        "models": {"description": "List available models", "approval": False},
        "status": {"description": "Show runtime status", "approval": False},
        "run": {"description": "Run approved tasks", "approval": True},
    }

    def __init__(self, workspace_root: Path | str | None = None, timeout_s: int = 60) -> None: ...

    def resolve_workspace_path(self, path: str | Path) -> Path:
        """Resolves path against workspace_root, rejecting NUL bytes,
        path traversal (../), and directory escapes.
        Raises WorkspaceEscapeError on violation.
        """
        ...

    def validate_shell_command(self, command: str, args: list[str]) -> tuple[bool, str]: ...
    def validate_bash_command(self, script_path: str, args: list[str] | None = None) -> tuple[bool, str]: ...
    def validate_cli_command(self, command: str, args: list[str] | None = None) -> tuple[bool, str]: ...

    def execute_shell_command(
        self,
        command: str,
        args: list[str],
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]:
        """Executes allowlisted shell command with shell=False.
        Returns {'ok': bool, 'returncode': int, 'output': str, 'error': str | None}.
        """
        ...

    def execute_bash_command(
        self,
        script_path: str,
        args: list[str] | None = None,
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]: ...

    def execute_cli_command(
        self,
        command: str,
        args: list[str] | None = None,
        audit_sink: Callable[..., Any] | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any]: ...

    def run_safe_command(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: Path | str | None = None,
        audit_sink: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience execution method enforcing strict exception raising
        (DisallowedCommandError, WorkspaceEscapeError).
        """
        ...

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Returns JSON function schemas for Ollama tool calling."""
        ...
```

---

### 4.3 `services/mcp_gateway.py` (MCP Tool-Call Gateway)

```python
"""Model Context Protocol (MCP) Gateway Service for Sovereign Matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

# Exception Hierarchy
class MCPError(Exception):
    """Base exception for MCP operations."""

class MCPProtocolError(MCPError):
    """Raised on invalid JSON-RPC 2.0 frames or unexpected message types."""

class MCPValidationError(MCPError):
    """Raised when argument parameters violate the tool's JSON Schema."""

class MCPTimeoutError(MCPError):
    """Raised when an MCP server operation exceeds the configured timeout."""

class MCPApprovalRequiredError(MCPError):
    """Raised when a high-risk tool is invoked without sovereign pre-flight approval."""

# Server Protocols & Classes
class MCPServer(Protocol):
    async def list_tools(self) -> list[dict[str, Any]]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...
    async def close(self) -> None: ...

class StdioMCPServer:
    """Manages an external or in-process stdio MCP server process over JSON-RPC 2.0."""
    def __init__(self, command: list[str], env: dict[str, str] | None = None, timeout_s: float = 30.0) -> None: ...
    async def initialize(self) -> dict[str, Any]: ...
    async def list_tools(self) -> list[dict[str, Any]]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...
    async def close(self) -> None: ...

# Capability Dataclass
@dataclass
class Capability:
    name: str
    description: str
    server_name: str
    input_schema: dict[str, Any]
    risk: str = "LOW"               # "LOW" | "MEDIUM" | "HIGH"
    requires_approval: bool = False
    source: str = "mcp"

# Gateway Contract
class MCPGateway:
    servers: dict[str, MCPServer]
    capabilities: dict[str, Capability]
    timeout_s: float

    def __init__(self, timeout_s: float = 30.0) -> None: ...
    def register_server(self, name: str, server: MCPServer) -> None: ...
    async def discover(self) -> list[dict[str, Any]]:
        """Queries registered servers, extracts tools, infers risk,
        and registers capabilities.
        """
        ...

    async def call(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Validates arguments against JSON Schema, checks approval gate,
        and calls the tool on the owning server.
        Returns {'ok': True, 'content': list} or {'ok': False, 'error': str}.
        """
        ...

    async def close(self) -> None:
        """Closes all underlying server transports cleanly."""
        ...
```

---

### 4.4 `services/skill_loader.py` (Skill Absorption Pipeline)

```python
"""Declarative Skill Loader and Absorption Pipeline for Sovereign Matrix."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

class SkillStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    PREPARED = "PREPARED"
    PROMOTED = "PROMOTED"
    INJECTED = "INJECTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"

# Invariant: Allowed tools closed allowlist
ALLOWED_SKILL_TOOLS: frozenset[str] = frozenset({
    "docs.read",
    "memory.read",
    "memory.search",
    "planning.emit",
    "skills.discover",
    "skills.validate",
})

class SkillLoader:
    workspace_root: Path
    curated_dir: Path
    quarantine_dir: Path

    def __init__(self, workspace_root: Path | str | None = None) -> None: ...

    def discover(self, manifest_path: Path | str) -> dict[str, Any]:
        """Reads metadata JSON without code import; assigns deterministic
        skill_id = f"sk_{hashlib.sha256(name.encode()).hexdigest()[:12]}".
        Returns record with stage=DISCOVERED.
        """
        ...

    def validate(self, record: dict[str, Any], reviewer: str) -> dict[str, Any]:
        """Enforces SKILL_CONTRACT v1.0. Checks reviewer presence,
        verifies license, checks allowed tools against ALLOWED_SKILL_TOOLS,
        and blocks offensive patterns.
        Transitions stage to VALIDATED or REJECTED.
        """
        ...

    def prepare(self, record: dict[str, Any]) -> dict[str, Any]:
        """Packages validated skill into curated/{skill_id} with package_manifest.json
        and source_manifest.json. Transitions stage to PREPARED.
        """
        ...

    def validate_curated(self) -> dict[str, list[dict[str, Any]]]:
        """Audits curated packages. Moves packages with missing manifests,
        symlinks, or tool violations into quarantine/.
        Returns {'valid': [...], 'quarantined': [...]}.
        """
        ...

    def promote(self, record: dict[str, Any], commander_approval: bool = False) -> dict[str, Any]:
        """Promotes prepared skill. Requires commander_approval=True.
        Transitions stage to PROMOTED. Emits SKILL_PROMOTED on bus.
        """
        ...

    def inject(
        self,
        record: dict[str, Any],
        target_agents: list[str],
        has_bus_approval: bool = False,
    ) -> dict[str, Any]:
        """Binds promoted skill to target agents.
        MANDATORY INVARIANT: Rejects injection unless has_bus_approval=True
        (verified SKILL_REVIEW_APPROVED event on bus).
        Writes curated/{skill_id}/bindings.json. Transitions stage to INJECTED.
        """
        ...
```

---

### 4.5 `core/models.py` (Bus Schema Additions)

Add the following event types to `EventType(str, Enum)`:

```python
class EventType(str, Enum):
    # Existing Events
    SYSTEM_INIT = "system_init"
    AGENT_REGISTER = "agent_register"
    AGENT_ALIVE = "agent_alive"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    STATE_UPDATE = "state_update"
    TOKEN_EXTRACTED = "token_extracted"
    KEY_INJECT = "key_inject"
    USER_COMMAND = "user_command"
    SOVEREIGN_OVERRIDE = "sovereign_override"
    MEMORY_STORE_REQUEST = "memory_store_request"
    MEMORY_STORED = "memory_stored"
    MEMORY_RECALL_REQUEST = "memory_recall_request"
    MEMORY_INJECT = "memory_inject"
    ERROR = "error"

    # New Event Additions for Milestone R5
    SKILL_PROMOTED = "skill_promoted"
    SKILL_REVIEW_APPROVED = "skill_review_approved"
```

#### Event Payload Definitions:
- `SKILL_REVIEW_APPROVED`:
  ```python
  payload = {
      "skill_id": "sk_...",
      "skill_name": "...",
      "reviewers": ["smith", "morpheus"],
      "contract_version": "1.0",
      "verdict": "APPROVED"
  }
  ```
- `SKILL_PROMOTED`:
  ```python
  payload = {
      "skill_id": "sk_...",
      "skill_name": "...",
      "commander_approval": True,
      "allowed_tools": ["docs.read", "memory.read"],
      "timestamp": "2026-09-23T14:30:00Z"
  }
  ```

---

## 5. Code Layout & Write Ownership Boundaries

```text
/mnt/e/matrex-dev/
├── matrix_main.py                 # Core Engine Entrypoint (Read-Only during R2-R5)
├── pyproject.toml                 # Quality configurations (Black, Ruff, Bandit, Mypy)
├── requirements.txt               # Pinned Python dependencies
├── SOVEREIGN_CONSTITUTION.md      # Immutable constitution (READ-ONLY)
├── MASTER_PLAN.md                 # Master execution plan (Author: Planning Engineer)
├── PROJECT.md                     # System architecture & inventory (Author: Planning Engineer)
├── PHASE2_COMPLETE.md             # Final verification attestation (Author: Security Reviewer)
│
├── core/                          # [Ownership: Bus Architect / Security Reviewer]
│   ├── models.py                  # Bus EventType & EventPayload (Bus Architect only)
│   ├── neural_bus.py              # DEALER/ROUTER & HMAC signing (Protected, Read-Only)
│   ├── aegis_validator.py         # Static topology validator (Security Reviewer)
│   ├── memory_manager.py          # SQLite memory manager (Crawler Auditor)
│   ├── key_router.py              # APIKeyRouter (Integration Engineer)
│   ├── governance.py              # HitL approval layer (Security Reviewer)
│   ├── engine.py                  # SovereignEngineFSM
│   └── librarian_crawler.py       # Core skill crawler (Crawler Auditor)
│
├── agents/                        # [Ownership: Integration Engineer / Crawler Auditor]
│   ├── base_agent.py              # MatrixAgent & Emergency Token Stash (PROTECTED)
│   ├── neo_agent.py               # Neo Agent (Wiring to safe_shell)
│   ├── trinity_agent.py           # Blind Extractor (PROTECTED)
│   ├── morpheus_agent.py          # Reviewer & Strategist
│   ├── smith_agent.py             # Reviewer & Enforcer
│   ├── oracle_agent.py            # Synthesizer
│   └── aegis_qa.py                # Asymmetric QA & Deterministic Guillotine
│
├── services/                      # [Ownership: Integration Engineer / Crawler Auditor]
│   ├── ollama_client.py           # Milestone R2: Local brain client (Integration Engineer)
│   ├── safe_shell.py              # Milestone R3: Sandboxed shell execution (Security Reviewer)
│   ├── mcp_gateway.py             # Milestone R4: MCP Stdio JSON-RPC Gateway (Integration Engineer)
│   ├── skill_loader.py            # Milestone R5: Skill absorption pipeline (Integration Engineer)
│   ├── assistant_crawler.py       # The Blind Distributor (PROTECTED)
│   ├── memory_crawler.py          # Memory crawler (Crawler Auditor)
│   ├── librarian_crawler.py       # Service skill crawler (Crawler Auditor)
│   ├── librarian.py               # SecureLibrarian JIT server (Crawler Auditor)
│   └── ui_bridge.py               # FastAPI & WebSocket bridge (Protected)
│
├── tests/                         # [Ownership: Test Engineer]
│   ├── conftest.py                # Pytest fixtures & Windows loop policy
│   ├── test_ollama_client.py      # Milestone R2 tests
│   ├── test_safe_shell.py         # Milestone R3 tests
│   ├── fake_mcp_stdio_server.py   # Milestone R4 test fixture
│   ├── test_mcp_smoke.py          # Milestone R4 offline smoke test
│   ├── test_skill_pipeline.py     # Milestone R5 skill loader tests
│   ├── test_crawlers_integration.py # 15 crawler integration tests
│   └── ...                        # Baseline unit & integration suites
│
├── reports/                       # [Read-Only for Team A; Written by Team B OpenCode]
│   ├── proof_of_life.txt          # OpenCode heartbeat
│   ├── B1_phase1_commit.md        # Team B commit status
│   ├── B2_opencode_config.md      # Team B config
│   ├── B3_mcp_audit.md            # Team B MCP audit report
│   └── B4_skill_inventory.md      # Team B skill inventory report
│
└── .agents/teamwork/              # Metadata & Agent Workspaces ONLY
    ├── worker_phase0_plan/        # Planning Engineer workspace
    ├── spec_miner_phase0_1/       # Miner 1 handoff & analysis
    ├── spec_miner_phase0_2/       # Miner 2 handoff & analysis
    └── spec_miner_phase0_3/       # Miner 3 handoff & analysis
```

### 5.1 Write Ownership Matrix

| File / Directory | Authorized Role | Prohibited Roles | Invariant Constraint |
|---|---|---|---|
| `SOVEREIGN_CONSTITUTION.md` | NONE (Immutable) | ALL | Never modified |
| `core/models.py` | Bus Architect | All others | Only add `EventType` enum members; never change existing types |
| `agents/base_agent.py` | Bus Architect | All others | `emergency_token_stash` (`MAX_STASH_SIZE=2`, `TTL=300s`) must remain intact |
| `services/assistant_crawler.py`| Crawler Auditor | All others | Must remain the sole distributor listening to `TOKEN_EXTRACTED` |
| `services/ollama_client.py` | Integration Engineer | Crawler Auditor | Loopback only, stdlib urllib, zero cloud dependencies |
| `services/safe_shell.py` | Security Reviewer | All others | Absolute `shell=False`, strict allowlists, workspace scoping |
| `services/mcp_gateway.py` | Integration Engineer | Crawler Auditor | Stdio JSON-RPC 2.0, no Proactor loop, launcher allowlist |
| `services/skill_loader.py` | Integration Engineer | All others | 5-stage lifecycle, 6-tool allowlist, bus event required for injection |
| `tests/*` | Test Engineer | All others | Pre-integration suites; 100% offline, zero network dependencies |
| `.agents/teamwork/*` | Respective Agents | All others | Metadata only — NO source code, tests, or data files allowed here |
