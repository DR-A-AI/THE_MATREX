# TECHNICAL ANALYSIS REPORT: Requirement R3 — Project MCP Gateway & Workspace Manifest Activation

**Author**: survey_r3_explorer (R3 MCP Gateway & Workspace Manifest Explorer)  
**Date**: 2026-09-24  
**Target Subsystems**: `workspace.manifest.json`, `services/mcp_gateway.py`, `opencode.json`, `agents/base_agent.py`, `agents/neo_agent.py`, `tests/test_mcp_gateway.py`, `smoke_test_mcp.py`  
**Governing Documents**: `PROJECT.md`, `SOVEREIGN_CONSTITUTION.md`, `AGENTS.md`, `ORIGINAL_REQUEST.md`  

---

## 1. Executive Summary

Requirement R3 mandates the activation of `workspace.manifest.json` within `services/mcp_gateway.py` so that autonomous agents (Neo, Morpheus, Trinity, Smith, Oracle, Base) can dynamically discover and invoke the 4 project MCP tools:
1. **`matrix_shell`** (registered as `"shell"` in manifest, `"matrix_shell"` in `opencode.json`)
2. **`chrome_devtools`** (headless browser automation via Google Puppeteer)
3. **`syncfusion`** (enterprise React DataGrid code generation)
4. **`github`** (repository, PR, issue, branch, and workflow automation)

### Core Investigation Findings:
1. **Zero Mocks Feasibility (100% Real)**: All four MCP servers exist physically on disk, run natively under Node.js v24.19.0 and native Linux binaries without external cloud mocks. Verified directly via live JSON-RPC 2.0 stdio handshakes:
   - `shell` (`/mnt/k/mcp/shell/server.js`): Discovers `run_shell_command`, executes live commands (`python3 --version` returned `Python 3.14.7\n`).
   - `syncfusion` (`/mnt/k/mcp/syncfusion/server.js`): Discovers `generate_react_datagrid`, generates full React DataGrid code with injected license.
   - `chrome_devtools` (`/mnt/k/mcp/chrome-devtools/.../chrome-devtools-mcp.js`): Discovers 29 browser automation tools (`click`, `navigate_page`, `evaluate_script`, `take_screenshot`).
   - `github` (`/home/AH/.local/bin/github-mcp-server stdio`): Discovers 45 live GitHub management tools.
2. **Current Gateway Blocking Defects**:
   - `from_manifest()` in `services/mcp_gateway.py:488` strictly rejects server names other than `{"github", "chrome_devtools", "syncfusion", "shell"}`, throwing `ValueError` if `"matrix_shell"` is passed.
   - `workspace.manifest.json` contains Windows-specific paths (`C:\Program Files\...`, `K:\mcp\...`), causing `shutil.which` and `Path.exists` in `mcp_gateway.py:501` to fail-closed on Linux/WSL.
   - Environment reference enforcement (`*_REF` only) prevents setting non-secret operational parameters (e.g. `NODE_PATH`, `SHELL_ALLOWLIST`).
   - Standalone runner `run_sovereign_mcp_gateway()` is an empty idle wait (`asyncio.Event().wait()`) with no bus listener or IPC endpoint.
3. **Agent Integration Void**:
   - Neither `agents/base_agent.py` nor `agents/neo_agent.py` currently connects to `mcp_gateway.py`. Agents rely on hardcoded local tool dictionaries (`open_browser` in base agent; 11 hardcoded OS tools in Neo).
   - `tests/test_mcp_gateway.py` and `smoke_test_mcp.py` rely on `tests/fake_mcp_stdio_server.py`, violating the Sovereign Zero-Mock Command.

---

## 2. Analysis of `workspace.manifest.json` & Comparative Audit

### 2.1 Schema & Structure Breakdown
File: `/mnt/e/matrex-dev/workspace.manifest.json` (Lines 1–77)

```json
{
  "schema_version": 1,
  "workspace_id": "matrix-v2",
  "root": "K:\\THE-MATRIX-V2",
  "canonical": true,
  "components": { ... },
  "model": { ... },
  "skills_import": { ... },
  "frontend": { ... },
  "external_runtime_paths": [],
  "mcp_gateway": {
    "timeout_seconds": 15,
    "max_output_bytes": 65536,
    "servers": {
      "github": {
        "enabled": true,
        "command": [
          "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
          "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
          "K:\\mcp\\github\\run-github-mcp.ps1"
        ],
        "max_output_bytes": 1048576,
        "environment": {"GITHUB_PERSONAL_ACCESS_TOKEN": "GH_TOKEN_REF"}
      },
      "chrome_devtools": {
        "enabled": true,
        "command": [
          "C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe",
          "K:\\mcp\\chrome-devtools\\node_modules\\chrome-devtools-mcp\\build\\src\\bin\\chrome-devtools-mcp.js",
          "--headless", "--isolated", "--no-usage-statistics",
          "--workspace", "K:\\THE-MATRIX-V2"
        ]
      },
      "syncfusion": {
        "enabled": true,
        "command": [
          "C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe",
          "K:\\mcp\\syncfusion\\server.js"
        ]
      },
      "shell": {
        "enabled": true,
        "command": [
          "C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe",
          "K:\\mcp\\shell\\server.js"
        ]
      }
    }
  },
  "secret_paths": [ "F:\\Users\\AA5II\\Matrix-Secrets" ]
}
```

### 2.2 The 4 Project MCP Tools: Real Specifications

| Server Key | Alternate / Prompt Alias | Underlying Implementation | Protocol Version | Discovered Tool(s) | Verified Functionality |
|---|---|---|---|---|---|
| `"shell"` | `"matrix_shell"` | Node.js `@modelcontextprotocol/sdk` (`/mnt/k/mcp/shell/server.js`) | `2024-11-05` (Server: `Shell_Mcp` v3.0.0) | `run_shell_command` | Sandboxed subprocess (`execFile`), shell=False, executable allowlist, timeout, maxBuffer. Output verified on `python3 --version`. |
| `"chrome_devtools"` | `chrome_devtools` | Google DevTools MCP (`/mnt/k/mcp/chrome-devtools/node_modules/chrome-devtools-mcp/.../chrome-devtools-mcp.js`) | `2024-11-05` (Server: `chrome_devtools` v1.9.0) | 29 tools (`click`, `close_page`, `drag`, `emulate`, `evaluate_script`, `fill`, `fill_form`, `navigate_page`, `take_screenshot`, etc.) | Headless Chrome automation over DevTools protocol with isolated sessions and workspace bounds. |
| `"syncfusion"` | `syncfusion` | Node.js `@modelcontextprotocol/sdk` (`/mnt/k/mcp/syncfusion/server.js`) | `2024-11-05` (Server: `Syncfusion_Mcp` v2.0.0) | `generate_react_datagrid` | Compiles validated, type-safe React DataGrid components with injected license key (`registerLicense(...)`), customizable columns, and row data. |
| `"github"` | `github` | Native Go binary (`/home/AH/.local/bin/github-mcp-server stdio`) | `2024-11-05` (Server: `github-mcp-server` v1.12.2) | 45 tools (`create_pull_request`, `list_issues`, `create_branch`, `get_file_contents`, `push_files`, etc.) | Full GitHub REST/GraphQL API integration with OAuth scope policy enforcement and pagination. |

### 2.3 Detailed Tool Schemas

#### 1. `run_shell_command` (from `shell` / `matrix_shell`)
- **Description**: Executes a single executable without a shell (no pipes, chaining, or redirection). Audited.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "executable": {
        "type": "string",
        "description": "Executable name or absolute path. No shell metacharacters."
      },
      "args": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Arguments (no shell expansion)."
      }
    },
    "required": ["executable"]
  }
  ```
- **Inferred Risk**: `HIGH` (due to `"run_shell_command"` starting with `"run"`, or command execution nature).
- **Requires Approval**: `True`.

#### 2. `generate_react_datagrid` (from `syncfusion`)
- **Description**: Generates a React DataGrid (Syncfusion ej2-react-grids) with caller-supplied columns and data.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "componentName": {
        "type": "string",
        "description": "PascalCase component name, e.g. UsersGrid"
      },
      "columns": {
        "type": "array",
        "description": "Optional column defs [{field, headerText?, width?, align?}]"
      },
      "data": {
        "type": "array",
        "description": "Optional row objects (max 500)"
      }
    },
    "required": ["componentName"]
  }
  ```
- **Inferred Risk**: `LOW` (pure code generation returning string content).
- **Requires Approval**: `False`.

#### 3. `chrome_devtools` Tools (Sample: `navigate_page`, `take_screenshot`, `evaluate_script`)
- **`navigate_page`**:
  - `properties`: `{"url": {"type": "string"}}`, `required`: `["url"]`
  - Inferred Risk: `LOW`
- **`take_screenshot`**:
  - `properties`: `{"format": {"type": "string", "enum": ["png", "jpeg", "webp"]}, "quality": {"type": "number"}}`
  - Inferred Risk: `LOW`
- **`evaluate_script`**:
  - `properties`: `{"script": {"type": "string"}}`, `required`: `["script"]`
  - Inferred Risk: `HIGH` (inferred from `"evaluate"` verb).
  - Requires Approval: `True`.

#### 4. `github` Tools (Sample: `create_pull_request`, `list_issues`, `get_file_contents`)
- **`get_file_contents`**:
  - Inferred Risk: `LOW`, Requires Approval: `False`
- **`create_pull_request`**:
  - Inferred Risk: `HIGH` (inferred from `"create"` prefix).
  - Requires Approval: `True`.

---

## 3. Discrepancy & Portability Analysis

### 3.1 `workspace.manifest.json` vs. `opencode.json` Discrepancies

| Aspect | `workspace.manifest.json` | `opencode.json` | Resolution / Standard |
|---|---|---|---|
| **Shell Server Key** | `"shell"` | `"matrix_shell"` | Support both in `from_manifest()`: treat `"matrix_shell"` and `"shell"` as aliases. |
| **Node Launcher** | `C:\Program Files\...\node.exe` | `/usr/bin/node` | Dynamically resolve launcher: if `node.exe` or `node`, search `shutil.which("node")` or fallback to `sys.executable` if Python script. |
| **Script Paths** | `K:\mcp\shell\server.js`, `K:\mcp\syncfusion\server.js` | `/mnt/k/mcp/shell/server.js`, `/mnt/k/mcp/syncfusion/server.js` | Normalize Windows drive letters (`K:\...` → `/mnt/k/...`) when running under POSIX (`os.name != "nt"`). |
| **GitHub Launcher** | PowerShell `.ps1` wrapper calling `K:\mcp\github\github-mcp-server.exe` | (Not registered in `opencode.json`) | Under Linux, execute `/home/AH/.local/bin/github-mcp-server stdio` directly without PowerShell overhead. |
| **Environment Values** | `"GITHUB_PERSONAL_ACCESS_TOKEN": "GH_TOKEN_REF"` | Direct literals: `SHELL_CWD`, `SHELL_ALLOWLIST`, etc. | Support both: if value ends with `_REF`, resolve from `os.environ[ref[:-4]]`; otherwise, allow string literals for non-secret configs. |

---

## 4. Deep Audit of `services/mcp_gateway.py`

### 4.1 Component Roles
File: `/mnt/e/matrex-dev/services/mcp_gateway.py` (745 lines)

- **`MCPServer` (Protocol, lines 242–248)**:
  Defines async contract: `list_tools()`, `call_tool(name, arguments)`, `close()`.
- **`StdioMCPServer` (lines 250–449)**:
  Manages subprocess over stdio using JSON-RPC 2.0.
  - Line 265: Validates launcher against `ALLOWED_LAUNCHERS` and `shutil.which()`.
  - Line 360: Resolves environment references (`*_REF`).
  - Lines 367–376: Spawns subprocess with `shell=False`.
  - Line 378: Executes `initialize` JSON-RPC handshake.
  - Line 387: Sends `notifications/initialized` notification frame.
  - Line 394: Implements `list_tools()` sending `tools/list`.
  - Line 403: Implements `call_tool()` sending `tools/call`.
- **`Capability` & `CapabilityRegistry` (lines 125–240)**:
  Stores discovered tools, validates input values, enforces payload limits (`MAX_PAYLOAD_BYTES = 65536`), and converts tools to OpenAI/Ollama function calling schemas via `tool_definition()`.
- **`MCPGateway` (lines 450–717)**:
  Aggregates servers, routes calls to owning server, enforces JSON schema validation, applies NUL byte check, verifies sovereign pre-flight gate, and logs execution audit trails.
- **`from_manifest()` (lines 480–525)**:
  Factory method that parses `workspace.manifest.json` and instantiates `StdioMCPServer` instances for enabled servers.

### 4.2 Identified Vulnerabilities & Deficiencies

1. **Defect 1: Server Name Rigid Whitelist** (`services/mcp_gateway.py:488`)
   ```python
   # Current:
   if server_name not in {"github", "chrome_devtools", "syncfusion", "shell"}:
       raise ValueError(f"unknown MCP server: {server_name}")
   ```
   *Impact*: If `workspace.manifest.json` or `opencode.json` contains `"matrix_shell"`, initialization crashes immediately.
   *Fix*: Allow `{"github", "chrome_devtools", "syncfusion", "shell", "matrix_shell"}` and normalize `"matrix_shell"` to `"shell"`.

2. **Defect 2: Platform-Rigid Launcher & Path Resolution** (`services/mcp_gateway.py:499–504`)
   ```python
   launcher = Path(command[0]).name.lower()
   if launcher not in ALLOWED_LAUNCHERS or (
       shutil.which(command[0]) is None and not Path(command[0]).exists()
   ):
       raise ValueError(f"unavailable or disallowed MCP launcher: {command[0]}")
   ```
   *Impact*: On Linux/WSL, `command[0]` is `"C:\Program Files\...\node.exe"`. `shutil.which` returns `None` and `Path.exists` returns `False`. The entire manifest loader aborts.
   *Fix*: Implement a platform normalization function `_normalize_manifest_command(command: list[str]) -> list[str]`:
   - If launcher is `node.exe` or `node`: resolve via `shutil.which("node")` or `/usr/bin/node`.
   - If launcher is `powershell.exe` on Linux: if `server_name == "github"` and `shutil.which("github-mcp-server")` exists, replace command with `["github-mcp-server", "stdio"]`.
   - Translate all argument paths (`K:\mcp\...` → `/mnt/k/mcp/...`).

3. **Defect 3: Strict `*_REF` Requirement Breaks Non-Secret Env Variables** (`services/mcp_gateway.py:274–278, 506–509`)
   ```python
   if not isinstance(env, dict) or any(
       not isinstance(k, str) or not isinstance(v, str) or not v.endswith("_REF")
       for k, v in env.items()
   ):
       raise ValueError("MCP environment must contain *_REF values only")
   ```
   *Impact*: Environment variables like `"NODE_PATH": "/mnt/k/mcp/shell/node_modules"` or `"SHELL_CWD": "/mnt/e/matrex-dev"` cause `from_manifest` to raise `ValueError`.
   *Fix*: Allow non-secret string environment values directly, while strictly resolving `*_REF` keys against `os.environ`.

4. **Defect 4: Standalone Launcher is a Dead-End No-Op** (`services/mcp_gateway.py:719–745`)
   ```python
   async def run_sovereign_mcp_gateway() -> None:
       ...
       await asyncio.Event().wait()
   ```
   *Impact*: `IGNITE_MATRIX.bat` starts `python services\mcp_gateway.py`, but it opens no port, connects to no bus, and provides no IPC. Agents running in `matrix_main.py` cannot communicate with it.
   *Fix*: `MCPGateway` should be instantiated in-process via a shared singleton provider `get_mcp_gateway()`, loaded at agent cluster startup.

5. **Defect 5: Unhandled Crash on Missing `*_REF` in Host Environment** (`services/mcp_gateway.py:364`)
   ```python
   if ref_target not in os.environ:
       raise RuntimeError(f"missing environment reference: {ref}")
   ```
   *Impact*: If `GH_TOKEN` is not set in `.env`, starting the gateway crashes the entire server.
   *Fix*: Gracefully warn and mark the specific server as unauthenticated/disabled or pass an empty/masked token, preventing cascade failures.

---

## 5. Agent Tool Discovery & Dispatch Architecture

### 5.1 Current Agent State
In `agents/base_agent.py:355–420`:
- Hardcodes a single function `open_browser` and passes `tools = [...]` to `router.chat()`.
- Lacks any reference to `MCPGateway`.

In `agents/neo_agent.py:364–658`:
- Defines 11 hardcoded tools (`run_local_command`, `read_local_file`, `write_local_file`, `edit_local_file`, `list_local_dir`, `search_local_code`, `open_browser`, `capture_screen`, `safe_click`, `safe_type_text`, `safe_press_key`).
- Lacks discovery or dispatch to `services/mcp_gateway.py`.

### 5.2 Target Dispatch Pipeline

```
  ┌────────────────────────────────────────────────────────┐
  │              Commander Directive (Event)               │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                 Agent (Neo / Morpheus)                 │
  │  1. Dynamic Discovery: gateway.discover()              │
  │  2. Combine local tools + MCP capability tools         │
  │  3. Submit to Ollama /api/chat with full tool schema   │
  └───────────────────────────┬────────────────────────────┘
                              │ LLM returns tool_calls
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                Tool Routing Evaluator                  │
  ├───────────────────────────┬────────────────────────────┤
  │ If name in local_tool_map │ If gateway.has_tool(name)  │
  │ -> Execute local fn       │ -> Check Sovereign Pre-    │
  │                           │    Flight Gate             │
  │                           │ -> gateway.call(name, args)│
  └───────────────────────────┴─────────────┬──────────────┘
                                            │
                                            ▼
                              ┌────────────────────────────┐
                              │    StdioMCPServer          │
                              │  JSON-RPC 2.0 stdio frame  │
                              │  {"method": "tools/call"}  │
                              └─────────────┬──────────────┘
                                            │
                                            ▼
                              ┌────────────────────────────┐
                              │  Real Subprocess Running:  │
                              │  - shell/server.js         │
                              │  - syncfusion/server.js    │
                              │  - chrome-devtools-mcp.js  │
                              │  - github-mcp-server       │
                              └────────────────────────────┘
```

### 5.3 Error Handling & Fallback Protocol
1. **Tool Not Found**: If an agent requests an unknown function, return structured error:
   `{"role": "tool", "content": "ERROR: Function <name> not found.", "name": name}`
2. **Schema Mismatch**: Handled fail-closed by `MCPGateway._validate_json_schema()` returning `{"ok": False, "error": "..."}`, forwarded back to the model for self-correction.
3. **Subprocess Timeout**: Enforced by `asyncio.wait_for(..., self.timeout_s)`, returning `{"ok": False, "error": "timeout after 15s"}`.
4. **Sovereignty Rejection**: If Commander denies high-risk execution, returns `{"ok": False, "error": "Safety override: blocked"}`.
5. **Zero Silent Drops**: Every execution attempt records an audit log through `MCPGateway._audit()` with action, target, risk, and result.

---

## 6. Zero Mocks Mandate & Test Suite Migration

### 6.1 Replacement of `tests/fake_mcp_stdio_server.py`
The file `tests/fake_mcp_stdio_server.py` is an explicit mock violating the Sovereign Zero-Mock Directive.
It must be eliminated and replaced with real physical execution:

- **Primary Real Subprocess Test Fixture**: Use `/mnt/k/mcp/shell/server.js` or `/mnt/k/mcp/syncfusion/server.js`.
- **Verified Execution Evidence**:
  - `run_shell_command` executed via node directly tested and verified:
    ```json
    {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "Python 3.14.7\n"}], "isError": false}}
    ```
  - `generate_react_datagrid` executed via node directly tested and verified:
    ```json
    {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "import * as React from 'react';\n..."}], "isError": false}}
    ```
- **Test Implementation**:
  Update `tests/test_mcp_gateway.py` to launch a real Node process running `shell/server.js` or `syncfusion/server.js` in a pytest fixture.

---

## 7. Implementation Recommendations for Implementer Agent

### Recommendation 1: Cross-Platform Path Normalization in `services/mcp_gateway.py`
Add a normalization helper to translate Windows paths to WSL/Linux paths:
```python
def _normalize_command_for_platform(server_name: str, command: list[str]) -> list[str]:
    if not command:
        return command
    cmd = list(command)
    launcher = Path(cmd[0]).name.lower()
    
    # 1. Resolve launcher on Linux/WSL
    if os.name != "nt":
        if launcher in {"node", "node.exe"}:
            node_bin = shutil.which("node") or "/usr/bin/node"
            cmd[0] = node_bin
        elif launcher in {"powershell.exe", "pwsh", "powershell"} and server_name == "github":
            gh_bin = shutil.which("github-mcp-server") or "/home/AH/.local/bin/github-mcp-server"
            if Path(gh_bin).exists():
                return [gh_bin, "stdio"]
                
    # 2. Normalize Windows drive paths in arguments (e.g. K:\ -> /mnt/k/)
    if os.name != "nt":
        for i in range(1, len(cmd)):
            arg = cmd[i]
            if len(arg) >= 3 and arg[1] == ":" and arg[2] in ("\\", "/"):
                drive = arg[0].lower()
                rel = arg[3:].replace("\\", "/")
                cmd[i] = f"/mnt/{drive}/{rel}"
    return cmd
```

### Recommendation 2: Update Server Allowlist & Environment Policy in `from_manifest`
```python
# In MCPGateway.from_manifest:
server_key = "shell" if server_name == "matrix_shell" else server_name
if server_key not in {"github", "chrome_devtools", "syncfusion", "shell"}:
    raise ValueError(f"unknown MCP server: {server_name}")

# Normalize environment:
clean_env = {}
for k, v in env.items():
    if v.endswith("_REF"):
        ref_target = v[:-4]
        if ref_target in os.environ:
            clean_env[k] = os.environ[ref_target]
    else:
        clean_env[k] = v
```

### Recommendation 3: Provide Shared Gateway Accessor `get_mcp_gateway()`
Provide an in-process singleton accessor in `services/mcp_gateway.py`:
```python
_default_gateway: MCPGateway | None = None

async def get_mcp_gateway(*, reset: bool = False) -> MCPGateway:
    global _default_gateway
    if _default_gateway is None or reset:
        manifest_path = Path(__file__).resolve().parent.parent / "workspace.manifest.json"
        _default_gateway = MCPGateway.from_manifest(manifest_path)
        await _default_gateway.discover()
    return _default_gateway
```

### Recommendation 4: Wire Agent Dispatch in `agents/base_agent.py` and `agents/neo_agent.py`
In `_handle_user_command`:
1. Obtain tools: `gateway = await get_mcp_gateway()`, retrieve `mcp_tools = gateway.registry.tool_definitions()`.
2. Append `mcp_tools` to agent's local tool schemas.
3. In tool call loop:
   ```python
   if gateway.has_tool(name):
       mcp_res = await gateway.call(name, args)
       if mcp_res.get("ok"):
           content = mcp_res.get("content", [])
           result = content[0].get("text", "") if content else str(mcp_res)
       else:
           result = f"ERROR: MCP tool call failed: {mcp_res.get('error')}"
   ```

### Recommendation 5: End-to-End Real Test (`tests/test_mcp_live_e2e.py`)
Create a real integration test verifying:
1. Manifest parses cleanly.
2. Servers start via real stdio subprocesses.
3. Tools list from `shell` and `syncfusion`.
4. `run_shell_command` executes `python3 --version` and asserts real output.
5. `generate_react_datagrid` executes and asserts valid React code.

---

## 8. Conclusion
The MCP Gateway architecture is fundamentally sound, fully compliant with JSON-RPC 2.0 stdio specifications, and backed by genuine, non-mocked tools on disk. Activating `workspace.manifest.json` requires four surgical changes: cross-platform path normalization, server name alias tolerance (`matrix_shell`), environment reference flexibility, and agent dispatch wiring. Zero mocks are required to achieve full production readiness.
