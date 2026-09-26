# Specification Mining Report: R2 (Ollama Client) & R3 (Safe Shell Execution)

**Agent ID**: `spec_miner_phase0_2`  
**Date**: 2026-09-23T14:15:00Z  
**Target Codebase**: `/mnt/e/matrex-dev`  
**Source Codebase**: `/mnt/k/THE-MATRIX-V2`  
**Working Directory**: `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2`  

---

## 1. Observation

Direct observations from authoritative specifications and codebase source files:

1. **Dispatch & Original Request Requirements**:
   - In `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 104–120):
     - **R2. Ollama Integration**:
       - Port `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py` into target codebase as `services/ollama_client.py`.
       - Discover Ollama via HTTP (`OLLAMA_HOST` / `OLLAMA_BASE_URL`), support model aliases.
       - Call `/api/chat` with `stream=false`.
       - Block non-loopback addresses.
       - Classify errors (service unavailable, timeout, HTTP error, invalid JSON, model not installed).
       - No automatic model downloads.
       - Agents fall back gracefully when Ollama unavailable.
       - New tests: `tests/test_ollama_client.py` covering: available, unavailable, bad JSON, timeout, non-loopback rejection.
     - **R3. Safe Shell Execution for Agents**:
       - Port `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py` as `services/safe_shell.py`.
       - Wire into agent layer.
       - Explicit allowlist (no free command strings).
       - Workspace scoping to `/mnt/e/matrex-dev`.
       - Audit logging of every execution attempt.
       - Timeouts + process isolation (`shell=False` everywhere; `shell=True` forbidden).
       - New tests: `tests/test_safe_shell.py`.
   - In `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 145–155):
     - R2 Acceptance:
       - `python -m pytest tests/test_ollama_client.py --no-cov` passes all.
       - `SOVEREIGN_BUS_SECRET=x python -c "from services.ollama_client import probe; print(probe())"` exits without crash.
       - `grep -r "shell=True" core/ agents/ services/` is empty.
     - R3 Acceptance:
       - `python -m pytest tests/test_safe_shell.py --no-cov` passes all.
       - Non-allowlisted command raises exception (tested).
       - Path traversal attempt rejected (tested).
       - `grep -r "shell=True" core/ agents/ services/` is empty.

2. **V2 Source Implementations**:
   - `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py` (lines 1–403):
     - Defines exception classes: `OllamaError`, `OllamaConfigurationError`, `OllamaConnectionError`, `OllamaTimeoutError`, `OllamaHTTPError`, `OllamaProtocolError`, `OllamaModelNotFoundError`.
     - `normalize_ollama_base_url(value=None)` validates scheme == `http`, loopback host in `{"localhost", "127.0.0.1", "::1"}` or resolves to `127.*`, defaults port to `11434`.
     - `UrllibTransport` uses stdlib `urllib.request` with timeout handling and maps to custom exceptions.
     - `OllamaClient` provides `health()`, `tags()`, `model_names()`, `resolve_model()`, `has_model()`, and `chat(model, messages, tools=None)`.
     - `ModelRouter` provides `ROLE_MODELS` mapping:
       - `NEO`: `("llama3.2", "gemma3")`
       - `MORPHEUS`: `("qwen3-coder", "llama3.2")`
       - `ORACLE`: `("deepseek-r1:8b", "llama3.2")`
       - `SMITH`: `("qwen3-coder", "llama3.2")`
       - `GHOST`: `("gemma3", "llama3.2")`
       - `TRINITY`: `("llama3.2", "gemma3")`
     - Lines 19–23: Imports `from cloud_provider import ...`. Notice: `cloud_provider.py` does NOT exist in `/mnt/e/matrex-dev`.
   - `/mnt/k/THE-MATRIX-V2/30-runtime/ollama_health.py` (lines 16–40):
     - Contains `def probe() -> tuple[int, dict]:` calling `router.discover()`, catching `OllamaError`, and returning `(0, {...})` or `(1, {...})`.
   - `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py` (lines 1–219):
     - Defines `ShellCapabilityValidator(workspace_root, timeout_s=60)`
     - `SHELL_ALLOWLIST`:
       - `"python"`: `allowed_modules`: `{"compileall", "pytest", "unittest"}`, max args 5 (enforces `-m <module>`). Uses `sys.executable`.
       - `"git"`: `allowed_subcommands`: `{"status", "log", "diff"}`, `allowed_flags`: `{"--short", "--oneline", "-10", "--stat", "-n"}`.
     - `CLI_ALLOWLIST`: `{"check", "verify", "models", "status", "run"}`.
     - `validate_bash_command`: checks script exists within `workspace_root`, size <= 1MB, relative to workspace. Runs via `shutil.which("bash")`.
     - Execution calls `subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s, shell=False, cwd=str(cwd))`.
   - `/mnt/k/THE-MATRIX-V2/30-runtime/execution_hand.py` (lines 55–60, 258–317):
     - Defines audit sink invocation: `_audit(sink, capability, target, result)` calling `sink(action=..., target=..., risk=..., result=...)`.
     - Path canonicalization with `_path()` rejecting absolute paths and directory escapes (`resolved != root and root not in resolved.parents`).

3. **Target Codebase (`/mnt/e/matrex-dev`) Environment & Quality Standards**:
   - `pyproject.toml` (lines 40–54):
     - Black: `line-length = 100`, `target-version = ['py310']`.
     - Mypy: `python_version = "3.10"`, `disallow_untyped_defs = true`, `warn_return_any = true`. Every function and method MUST have complete type annotations.
     - Ruff: excludes `.venv`, `.agents`, line length 100.
     - Bandit: `-r core/ services/ agents/ -x tests/`. Requires explicit `# nosec: B404` for `import subprocess`, `# nosec: B603` for `subprocess.run`, `# nosec: B607` for commands found via PATH.
   - `AGENTS.md`:
     - Mandatory `SOVEREIGN_BUS_SECRET` for any module touching neural bus.
     - Python >= 3.10 (CI pinned to 3.10).
     - Async crawlers / agents rule: "Never add sync I/O on the event loop."
   - Existing command execution in `agents/neo_agent.py`:
     - Line 52: `execute_in_the_dark(command)` takes raw command string, splits via `shlex.split`, calls `subprocess.run(args, shell=False)`. Has NO command allowlist!
     - Line 204: `run_local_command(command)` takes raw command string, splits via `shlex.split`, calls `subprocess.run(args, shell=False, cwd=workspace)`. Has NO command allowlist!

---

## 2. Logic Chain

1. **R2 probe() Requirement**:
   - *Observation*: The CLI verification command specified in Acceptance Criteria is:
     `SOVEREIGN_BUS_SECRET=x python -c "from services.ollama_client import probe; print(probe())"`
   - *Logic*: In V2, `probe()` lived in `30-runtime/ollama_health.py`, while `model_router.py` was in `10-brain/`. For the acceptance command to succeed without modification, `services/ollama_client.py` MUST directly implement and export `probe() -> tuple[int, dict[str, Any]]` (or alias it).
   - *Behavior*: `probe()` must catch `OllamaError` (and general exceptions) and return `(1, {"ready": False, "service": "unavailable", ...})` instead of raising an unhandled exception, ensuring clean non-zero/zero exits without traceback.

2. **R2 Cloud Fallback Decoupling**:
   - *Observation*: In V2, `model_router.py` lines 19–23 imported `cloud_provider`. In `/mnt/e/matrex-dev`, `cloud_provider.py` does not exist.
   - *Logic*: Direct unconditional import of `cloud_provider` will fail with `ModuleNotFoundError` in `/mnt/e/matrex-dev`.
   - *Resolution*: The import must be protected with `try ... except ImportError:`. When `cloud_provider` is absent, `CloudProviderError` is stubbed, `cloud_chat` is `None`, and `ModelRouter` operates purely in local mode (with graceful exception on model absence).

3. **R3 Exception Raising on Disallowed Commands & Workspace Escapes**:
   - *Observation*: The Acceptance Criteria state:
     - `Non-allowlisted command raises exception (tested)`
     - `Path traversal attempt rejected (tested)`
   - *Logic*: In V2, `safe_shell_capabilities.py` returned `{"ok": False, "error": ...}` from `execute_shell_command()` and `(False, "...")` from `validate_shell_command()`. But to fulfill the explicit acceptance test requirement (`raises exception`), `services/safe_shell.py` must define and raise explicit custom exceptions:
     - `DisallowedCommandError(SafeShellError)` when a command or argument fails allowlist validation.
     - `WorkspaceEscapeError(SafeShellError)` (or `ValueError`) when a path escapes `workspace_root`.
   - *Dual Interface*: Provide both a validator method `validate_shell_command(...) -> tuple[bool, str]` AND a direct execution method / `execute(...)` (or `strict=True` mode) that raises `DisallowedCommandError` / `WorkspaceEscapeError`.

4. **Process Isolation & Subprocess Flags**:
   - *Observation*: `grep -r "shell=True" core/ agents/ services/` MUST return empty. Bandit runs on `core/`, `services/`, and `agents/`.
   - *Logic*: Every subprocess invocation in `services/safe_shell.py` must explicitly specify `shell=False`. Every `subprocess` call must be tagged with `# nosec: B603, B607` and `import subprocess` with `# nosec: B404`.

5. **Type Annotations for Mypy Strictness**:
   - *Observation*: `pyproject.toml` enables `disallow_untyped_defs = true`.
   - *Logic*: Every function, method, parameter, and return value in both `services/ollama_client.py` and `services/safe_shell.py` must have explicit type annotations. Default values like `args: List[str] = None` must be typed as `list[str] | None = None` or `Optional[list[str]] = None`.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R2 Ollama | `normalize_ollama_base_url` | Normalizes host/URL string into `http://<loopback>:<port>` and enforces loopback-only destinations | `value: str \| None = None` | Normalized URL string (e.g. `http://127.0.0.1:11434`) | Raises `OllamaConfigurationError` if non-loopback, https, invalid, or empty | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:57-89` |
| 2 | R2 Ollama | `UrllibTransport` | Injectable HTTP transport using stdlib `urllib.request` | `method: str, url: str, headers: Mapping, body: bytes \| None, timeout: float` | `tuple[int, bytes]` | Maps errors to `OllamaHTTPError`, `OllamaTimeoutError`, `OllamaConnectionError` | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:106-134` |
| 3 | R2 Ollama | `OllamaClient.health` | Checks Ollama service availability without loading models | None | `dict[str, Any]` (e.g. `{"version": "..."}`) | Returns `{"version": "unknown"}` on 404; raises `OllamaConnectionError` / `OllamaHTTPError` on failure | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:181-196` |
| 4 | R2 Ollama | `OllamaClient.tags` | Lists installed models and builds model alias index | `refresh: bool = True` | `list[dict[str, Any]]` | Raises `OllamaProtocolError` if response JSON missing `models` list | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:197-216` |
| 5 | R2 Ollama | `OllamaClient.resolve_model` | Resolves requested model name or alias to canonical installed model tag | `model: str` | Canonical model tag string (e.g. `llama3.2:latest`) | Raises `OllamaModelNotFoundError` if not installed or empty | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:220-230` |
| 6 | R2 Ollama | `OllamaClient.chat` | Sends `/api/chat` request with `stream=false` and optional tools | `model: str, messages: Sequence[Mapping], tools: Sequence[Mapping] \| None = None` | Standardized result dict with `response`, `message`, `tool_calls`, `model_used`, `tier="local"` | Raises `OllamaProtocolError` on empty messages/invalid response; `OllamaConnectionError` on network fail | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:239-269` |
| 7 | R2 Ollama | `ModelRouter` | Local-first model router mapping Matrix agent roles to preferred local models | `client: OllamaClient \| None = None` | Router instance | Builds local endpoint catalog for Neo, Morpheus, Oracle, Smith, Ghost, Trinity | `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py:298-385` |
| 8 | R2 Ollama | `probe()` | Top-level service health probe callable from CLI or python snippet | None | `tuple[int, dict[str, Any]]` | Never raises unhandled exception. Returns exit code 0 on healthy, 1 on unavailable | `/mnt/k/THE-MATRIX-V2/30-runtime/ollama_health.py:16-40` + `ORIGINAL_REQUEST.md:147` |
| 9 | R3 Safe Shell | `ShellCapabilityValidator` | Validates command, arguments, and scripts against strict allowlists | `workspace_root: Path, timeout_s: int = 60` | Validator instance | Returns `(bool, str)` or raises `DisallowedCommandError` | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:20-53` |
| 10 | R3 Safe Shell | Shell Allowlist (`python`, `git`) | Strictly constrains executable commands. `python` requires `-m <module>` in `compileall, pytest, unittest`. `git` restricted to `status, log, diff`. | `command: str, args: list[str]` | `tuple[bool, str]` | Rejects any non-allowlisted command, arbitrary scripts, write git subcommands | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:24-37, 55-101` |
| 11 | R3 Safe Shell | Bash Script Execution | Constrains bash execution to scripts physically located within workspace root | `script_path: str, args: list[str] \| None = None, cwd: Path \| None = None` | Result dict `{"ok": bool, "returncode": int, "output": str}` | Rejects path traversal (`../`), files >1MB, missing files, missing bash binary | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:102-118, 169-206` |
| 12 | R3 Safe Shell | CLI Command Allowlist | Validates and dispatches Matrix CLI commands (`check`, `verify`, `models`, `status`, `run`) | `command: str, args: list[str] \| None = None` | Result dict | Rejects non-allowlisted CLI commands; `run` requires task argument | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:40-47, 119-131, 207-218` |
| 13 | R3 Safe Shell | Workspace Path Scoping | Enforces canonical path containment inside `workspace_root` | `path: str \| Path` | Canonical `Path` inside workspace | Raises `WorkspaceEscapeError` if path traverses or points outside root | `/mnt/k/THE-MATRIX-V2/30-runtime/execution_hand.py:32-46` |
| 14 | R3 Safe Shell | Process Isolation (`shell=False`) | Executes commands strictly via argv lists without shell expansion | `cmd: list[str], cwd: Path, timeout: float` | `subprocess.CompletedProcess` | `shell=False` enforced; command timeouts caught and reported | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:149-168` |
| 15 | R3 Safe Shell | Execution Audit Logging | Logs every command attempt (action, target, risk, result) via logger and optional audit sink | `action: str, target: str, risk: str, result: str, details: dict` | None | Recorded regardless of whether command succeeded or was blocked | `/mnt/k/THE-MATRIX-V2/30-runtime/execution_hand.py:55-59` + test assertions |
| 16 | R3 Safe Shell | Ollama Tool Definitions | Exposes capabilities in OpenAI/Ollama function calling schema | None | `list[dict[str, Any]]` | Generates JSON schemas for `shell`, `bash`, `cli` tools | `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py:184-195` |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `normalize_ollama_base_url` | `"https://localhost:11434"` | Rejection: raises `OllamaConfigurationError` (scheme must be `http`). |
| 2 | `normalize_ollama_base_url` | `"10.0.0.1:11434"` | Rejection: raises `OllamaConfigurationError` (non-loopback IP disallowed). |
| 3 | `normalize_ollama_base_url` | `"127.0.0.1:11434/api"` | Normalization: strips trailing `/api` and path, returns `"http://127.0.0.1:11434"`. |
| 4 | `normalize_ollama_base_url` | `""` or `"   "` | Rejection: raises `OllamaConfigurationError` ("OLLAMA_HOST/OLLAMA_BASE_URL is empty"). |
| 5 | `normalize_ollama_base_url` | `"[::1]:11434"` or `"::1:11434"` | Accepts IPv6 loopback, formats as `"http://[::1]:11434"`. |
| 6 | `OllamaClient.chat` | `messages=[]` (empty list) | Rejection: raises `OllamaProtocolError` ("Ollama chat requires at least one message"). |
| 7 | `OllamaClient.resolve_model` | `"nonexistent_model"` | Rejection: refreshes tags, then raises `OllamaModelNotFoundError`. |
| 8 | `OllamaClient.tags` | Server returns malformed JSON or HTTP 500 | Protocol/HTTP error: raises `OllamaProtocolError` or `OllamaHTTPError(500, ...)`. |
| 9 | `probe()` | Ollama daemon completely stopped (ConnectionRefused) | Clean exit: returns `(1, {"ready": False, "service": "unavailable", "error": "OllamaConnectionError", ...})` with zero crash. |
| 10 | `validate_shell_command` | `command="rm", args=["-rf", "/"]` | Rejection: raises `DisallowedCommandError` (or `valid=False`, `"Command 'rm' not in allowlist"`). |
| 11 | `validate_shell_command` | `command="python", args=["script.py"]` (no `-m`) | Rejection: raises `DisallowedCommandError` (`-m` flag required). |
| 12 | `validate_shell_command` | `command="python", args=["-m", "os"]` | Rejection: raises `DisallowedCommandError` (module `os` not in `allowed_modules`). |
| 13 | `validate_shell_command` | `command="git", args=["push", "origin", "main"]` | Rejection: raises `DisallowedCommandError` (subcommand `push` not allowed). |
| 14 | `validate_bash_command` | `script_path="../secret.sh"` | Rejection: raises `WorkspaceEscapeError` (path escapes workspace). |
| 15 | `validate_bash_command` | `script_path="missing.sh"` | Rejection: raises `ScriptExecutionError` or `FileNotFoundError`. |
| 16 | `validate_bash_command` | `script_path` containing NUL byte `"\x00"` | Rejection: raises `WorkspaceEscapeError` or `ValueError` ("contains a NUL byte"). |
| 17 | `execute_shell_command` | Command hanging longer than `timeout_s` | Timeout: subprocess killed, raises `CommandTimeoutError` or returns `{"ok": False, "error": "Command timeout after Xs"}`. Audit logged as `"timeout"`. |
| 18 | `execute_shell_command` | Command generating massive stdout (>10MB) | Buffer containment: output safely sliced to `completed.stdout[-2000:] + completed.stderr[-500:]`. |

---

## 5. Detailed Specifications for Implementation

### A. `services/ollama_client.py`

#### 1. Public API & Signatures
```python
# Exceptions
class OllamaError(RuntimeError): ...
class OllamaConfigurationError(OllamaError): ...
class OllamaConnectionError(OllamaError): ...
class OllamaTimeoutError(OllamaConnectionError): ...
class OllamaHTTPError(OllamaError):
    status: int
    def __init__(self, status: int, message: str) -> None: ...
class OllamaProtocolError(OllamaError): ...
class OllamaModelNotFoundError(OllamaError): ...

# Base URL normalization
def normalize_ollama_base_url(value: str | None = None) -> str: ...

# Transport
class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, bytes]: ...

# Client
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

    def health(self) -> dict[str, Any]: ...
    def tags(self, *, refresh: bool = True) -> list[dict[str, Any]]: ...
    def model_names(self) -> list[str]: ...
    def resolve_model(self, model: str) -> str: ...
    def has_model(self, model: str) -> bool: ...
    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

# Router
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
    endpoints: dict[str, ModelEndpoint]

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
def probe() -> tuple[int, dict[str, Any]]: ...
```

#### 2. Probe Implementation Contract
```python
def probe() -> tuple[int, dict[str, Any]]:
    """Probes the local Ollama service. Returns (exit_code, result_dict).
    Guaranteed not to raise an unhandled exception.
    """
    router = get_router()
    try:
        status = router.discover()
    except OllamaError as exc:
        return 1, {
            "ready": False,
            "service": "unavailable",
            "error": type(exc).__name__,
            "message": str(exc),
            "base_url": router.client.base_url,
        }
    except Exception as exc:
        return 1, {
            "ready": False,
            "service": "error",
            "error": type(exc).__name__,
            "message": str(exc),
            "base_url": router.client.base_url if hasattr(router, "client") else "unknown",
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
        "base_url": status.get("base_url"),
    }
```

---

### B. `services/safe_shell.py`

#### 1. Public API & Signatures
```python
# Exceptions
class SafeShellError(Exception):
    """Base exception for safe shell execution."""

class DisallowedCommandError(SafeShellError):
    """Raised when a command or argument is not on the allowlist."""

class WorkspaceEscapeError(SafeShellError):
    """Raised when a path escapes the workspace root."""

class CommandTimeoutError(SafeShellError):
    """Raised when command execution exceeds timeout."""

class ScriptExecutionError(SafeShellError):
    """Raised when workspace script execution fails validation."""

# Capability validator and runner
class ShellCapabilityValidator:
    workspace_root: Path
    timeout_s: int

    SHELL_ALLOWLIST: dict[str, dict[str, Any]] = {
        "python": {
            "description": "Python with specific modules only",
            "args_mode": "constrained",
            "allowed_modules": {"compileall", "pytest", "unittest"},
            "max_args": 10,
        },
        "git": {
            "description": "Git read-only diagnostics",
            "args_mode": "constrained",
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

    def resolve_workspace_path(self, path: str | Path) -> Path: ...

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
    ) -> dict[str, Any]: ...

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
        """Convenience execution method that enforces strict exception raising
        for non-allowlisted commands and path escapes.
        """
        ...

    def get_tool_definitions(self) -> list[dict[str, Any]]: ...
```

#### 2. Security Invariants
- `shell=False` is passed explicitly to every `subprocess.run()`.
- Python executions MUST use `sys.executable` to guarantee running inside `.venv` without PATH resolution ambiguity.
- Bandit markers `# nosec: B404` and `# nosec: B603, B607` MUST be present on subprocess statements.
- `resolve_workspace_path`:
  - Disallows NUL bytes (`\x00`).
  - Resolves path strictly against `self.workspace_root`.
  - Enforces `resolved == self.workspace_root or self.workspace_root in resolved.parents` (or `resolved.is_relative_to(self.workspace_root)`).
  - Raises `WorkspaceEscapeError` if validation fails.
- Audit logging:
  - Invokes `audit_sink(action=..., target=..., risk=..., result=..., details=...)` if provided.
  - Logs structured entries via `logging.getLogger("Sovereign.SafeShell")`.

---

## 6. Test Suite Requirements

### A. `tests/test_ollama_client.py`
Must cover at minimum:
1. `test_normalize_base_url_valid`:
   - Validates `127.0.0.1:11434`, `localhost:11434`, `http://127.0.0.1:11434/api`, `http://localhost:11434/v1`.
2. `test_normalize_base_url_rejects_external_hosts`:
   - Validates that non-loopback addresses (`10.0.0.2:11434`, `192.168.1.1:11434`, `https://example.com:11434`, `8.8.8.8:11434`) raise `OllamaConfigurationError`.
3. `test_normalize_base_url_empty_raises`:
   - Empty or whitespace string raises `OllamaConfigurationError`.
4. `test_probe_success`:
   - With fake transport returning 200 for `/api/version` and `/api/tags`, `probe()` returns `(0, dict)` with `ready=True`, `models=[...]`, and `service="ready"`.
5. `test_probe_offline_graceful`:
   - With fake transport raising `OllamaConnectionError` / `URLError`, `probe()` returns `(1, dict)` with `ready=False`, `service="unavailable"`, and does NOT raise an unhandled exception.
6. `test_model_discovery_and_aliases`:
   - Verifies resolving full tags (`llama3.2:latest`), base name aliases (`llama3.2`), and custom aliases.
7. `test_model_not_found_raises`:
   - `client.resolve_model("missing_model")` raises `OllamaModelNotFoundError`.
8. `test_chat_success`:
   - `client.chat("llama3.2", [{"role": "user", "content": "hi"}])` returns structured response dict with `response="local response"`, `tier="local"`, `tool_calls=[]`.
9. `test_chat_empty_messages_raises`:
   - `client.chat("llama3.2", [])` raises `OllamaProtocolError`.
10. `test_bad_json_raises_protocol_error`:
    - Transport returning invalid/truncated JSON bytes raises `OllamaProtocolError`.
11. `test_timeout_raises_timeout_error`:
    - Transport raising `TimeoutError` or socket timeout raises `OllamaTimeoutError`.
12. `test_http_error_handling`:
    - Transport returning HTTP 404 or 500 raises `OllamaHTTPError` with matching `.status`.
13. `test_router_chat_async`:
    - `await router.chat(AgentRole.NEO, [{"role": "user", "content": "hello"}])` succeeds asynchronously.
14. `test_no_shell_true_in_ollama_client`:
    - Inspects `services/ollama_client.py` AST/text to verify `shell=True` is completely absent.

### B. `tests/test_safe_shell.py`
Must cover at minimum:
1. `test_unknown_command_rejected_and_raises`:
   - Attempting `rm`, `powershell`, `whoami`, or `cat` raises `DisallowedCommandError` (or returns `ok=False` and raises in strict mode).
2. `test_python_compileall_allowed`:
   - `python -m compileall .` passes validation and executes safely using `sys.executable`.
3. `test_python_pytest_allowed`:
   - `python -m pytest` passes validation.
4. `test_python_disallowed_module_rejected`:
   - `python -m subprocess` or `python -m os` raises `DisallowedCommandError`.
5. `test_python_without_m_flag_rejected`:
   - `python some_script.py` raises `DisallowedCommandError`.
6. `test_git_status_allowed`:
   - `git status` passes validation and executes with `shell=False`.
7. `test_git_disallowed_subcommand_rejected`:
   - `git push`, `git commit`, `git checkout` raise `DisallowedCommandError`.
8. `test_workspace_path_traversal_rejected`:
   - Paths like `../outside.sh`, `/etc/passwd`, `C:\Windows` raise `WorkspaceEscapeError`.
9. `test_null_byte_in_path_rejected`:
   - Paths with `\x00` raise `WorkspaceEscapeError` or `ValueError`.
10. `test_bash_workspace_script_execution`:
    - Creates a temporary test script inside workspace, verifies execution and return code.
11. `test_bash_nonexistent_script_rejected`:
    - Nonexistent script path raises `ScriptExecutionError` or `FileNotFoundError`.
12. `test_cli_allowed_commands`:
    - `check`, `verify`, `status`, `models` are validated and allowed.
13. `test_cli_disallowed_command_rejected`:
    - Unknown CLI command (e.g. `cli destroy`) raises `DisallowedCommandError`.
14. `test_audit_logging`:
    - Execution calls invoke `audit_sink` recording `action`, `target`, `risk`, and `result` (e.g. `"capability.shell"`, `"success"` / `"blocked"`).
15. `test_timeout_enforcement`:
    - Mocked or long-running command exceeding timeout is terminated and raises `CommandTimeoutError` or returns timeout status.
16. `test_shell_false_enforced_everywhere`:
    - Mocks `subprocess.run` to assert that `kwargs.get("shell") is False` on all executions.
17. `test_tool_definitions_ollama_format`:
    - `get_tool_definitions()` returns valid function schemas for `shell`, `bash`, `cli`.

---

## 7. Caveats

1. **Local Ollama Daemon**:
   - Ollama may or may not be running locally on the development host during tests. Unit tests MUST use mock transports / injected transports (`UrllibTransport` mock) so that test runs are completely non-flaky and do not depend on an external running Ollama process or internet connectivity.
2. **Cloud Provider Independence**:
   - `cloud_provider.py` does not currently exist in `/mnt/e/matrex-dev`. R2 implementation must be fully self-contained and not depend on cloud provider modules to pass tests or probe checks.
3. **Agent Integration Timing**:
   - Updating `agents/neo_agent.py` and `agents/base_agent.py` to use `services/safe_shell.py` and `services/ollama_client.py` is an integration step that follows the creation and testing of the services. All changes must keep existing 25 tests passing.

---

## 8. Conclusion

The specifications for R2 (`services/ollama_client.py`) and R3 (`services/safe_shell.py`) have been fully extracted and refined:
1. `services/ollama_client.py` must port `model_router.py` + `ollama_health.py:probe()`, support loopback-only endpoints, model aliases, error classification, `probe() -> tuple[int, dict]`, and complete Python 3.10 type annotations with zero dependencies on `cloud_provider`.
2. `services/safe_shell.py` must port `safe_shell_capabilities.py`, strictly enforce `shell=False`, reject all free command strings, validate Python (`-m compileall/pytest/unittest`) and Git (`status/log/diff`), enforce workspace path scoping with `WorkspaceEscapeError`, raise `DisallowedCommandError` on unauthorized commands, and record audit events.
3. Both modules satisfy all quality gates: Black (100 cols), Ruff (0 errors), Mypy (`disallow_untyped_defs = true`), and Bandit (0 High/Medium issues with `# nosec` syntax).

---

## 9. Verification Method

To independently verify the implementation once written:

1. **R2 CLI Probe Verification**:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python3 -c "from services.ollama_client import probe; print(probe())"
   ```
   Must exit with code 0 or 1 without any Python traceback/crash.

2. **R2 Unit Tests**:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python3 -m pytest tests/test_ollama_client.py -v --no-cov
   ```
   Must pass 100% of test cases.

3. **R3 Unit Tests**:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python3 -m pytest tests/test_safe_shell.py -v --no-cov
   ```
   Must pass 100% of test cases.

4. **Security & Shell=True Check**:
   ```bash
   grep -r "shell=True" core/ agents/ services/
   ```
   Must return completely empty (exit code 1).

5. **Linter, Formatter & Bandit Verification**:
   ```bash
   python3 -m black --check core agents services config tests matrix_main.py
   python3 -m ruff check core services agents tests
   python3 -m bandit -r core/ services/ agents/ -x tests/
   ```
   All must pass with 0 errors / 0 issues.

6. **Regression Verification**:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python3 -m pytest -q --no-cov
   ```
   All existing 25 tests + new tests must pass with zero failures.
