# Handoff Report: Requirement R3 — Project MCP Gateway & Workspace Manifest Activation

**Author**: survey_r3_explorer (R3 MCP Gateway & Workspace Manifest Explorer)  
**Date**: 2026-09-24  
**Type**: Hard Handoff (Investigation & Synthesis Complete)  
**Target Recipient**: Orchestrator / Implementer Agent  

---

## 1. Observation

1. **Manifest Server Configuration (`workspace.manifest.json:34-72`)**:
   `workspace.manifest.json` defines four servers under `mcp_gateway.servers`:
   - `"github"`: command `["C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "K:\\mcp\\github\\run-github-mcp.ps1"]`, env `{"GITHUB_PERSONAL_ACCESS_TOKEN": "GH_TOKEN_REF"}`.
   - `"chrome_devtools"`: command `["C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe", "K:\\mcp\\chrome-devtools\\node_modules\\chrome-devtools-mcp\\build\\src\\bin\\chrome-devtools-mcp.js", "--headless", "--isolated", "--no-usage-statistics", "--workspace", "K:\\THE-MATRIX-V2"]`.
   - `"syncfusion"`: command `["C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe", "K:\\mcp\\syncfusion\\server.js"]`.
   - `"shell"`: command `["C:\\Program Files\\Microsoft Visual Studio\\18\\Enterprise\\MSBuild\\Microsoft\\VisualStudio\\NodeJs\\node.exe", "K:\\mcp\\shell\\server.js"]`.

2. **OpenCode Configuration (`opencode.json:6-45`)**:
   `opencode.json` defines three local MCP servers:
   - `"matrix_shell"`: command `["/usr/bin/node", "/mnt/k/mcp/shell/server.js"]`, environment with `NODE_PATH`, `SHELL_CWD`, `SHELL_ALLOWLIST`.
   - `"chrome_devtools"`: command `["/usr/bin/node", "/mnt/k/mcp/chrome-devtools/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js", "--headless", "--isolated", "--no-usage-statistics", "--workspace", "/mnt/e/matrex-dev"]`.
   - `"syncfusion"`: command `["/usr/bin/node", "/mnt/k/mcp/syncfusion/server.js"]`.

3. **Physical MCP Servers Verified Live over JSON-RPC 2.0 (Zero Mocks)**:
   - **`shell`** (`/mnt/k/mcp/shell/server.js`):
     - Initialized over stdio: `{"result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "Shell_Mcp", "version": "3.0.0"}}}`
     - Discovered tools: `run_shell_command`
     - Executed call `{"executable": "python3", "args": ["--version"]}`: returned `{"content": [{"type": "text", "text": "Python 3.14.7\n"}], "isError": false}`.
   - **`syncfusion`** (`/mnt/k/mcp/syncfusion/server.js`):
     - Initialized over stdio: `{"result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "Syncfusion_Mcp", "version": "2.0.0"}}}`
     - Discovered tools: `generate_react_datagrid`
     - Executed call `{"componentName": "OrdersGrid"}`: returned valid React DataGrid component with `registerLicense(...)` and directives.
   - **`chrome_devtools`** (`/mnt/k/mcp/chrome-devtools/.../chrome-devtools-mcp.js`):
     - Initialized over stdio: `{"result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "chrome_devtools", "version": "1.9.0"}}}`
     - Discovered 29 tools: `click`, `navigate_page`, `evaluate_script`, `take_screenshot`, `fill`, `fill_form`, etc.
   - **`github`** (`/home/AH/.local/bin/github-mcp-server stdio`):
     - Native Linux binary initialized over stdio: `{"result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "github-mcp-server", "version": "1.12.2"}}}`
     - Discovered 45 tools: `create_pull_request`, `list_issues`, `create_branch`, `get_file_contents`, etc.

4. **Gateway Code Observations (`services/mcp_gateway.py`)**:
   - Line 488: `if server_name not in {"github", "chrome_devtools", "syncfusion", "shell"}: raise ValueError(f"unknown MCP server: {server_name}")` rejects `"matrix_shell"`.
   - Line 499–504: Launcher check fails on Linux when `command[0]` is a Windows path like `C:\Program Files\...\node.exe`, because `shutil.which` returns `None` and `Path(command[0]).exists()` returns `False`.
   - Line 506–509: `MCP environment must contain *_REF values only` rejects direct string environment variables needed by servers (e.g. `NODE_PATH`, `SHELL_CWD`).
   - Line 719–745: Standalone runner `run_sovereign_mcp_gateway()` executes `await asyncio.Event().wait()` without binding an IPC/ZMQ port or exposing an agent API.

5. **Agent Implementation Observations (`agents/base_agent.py`, `agents/neo_agent.py`)**:
   - `agents/base_agent.py:355-380`: Defines hardcoded `base_tool_map = {"open_browser": open_browser}` and static tool schema.
   - `agents/neo_agent.py:364-539`: Defines hardcoded `tool_map` with 11 OS functions.
   - Neither agent imports or calls `MCPGateway`.

6. **Test Infrastructure Observations (`tests/fake_mcp_stdio_server.py`, `tests/test_mcp_gateway.py`)**:
   - `tests/fake_mcp_stdio_server.py` is a mock returning `fake-mcp-server` and `fixture_echo`.
   - 16 tests in `tests/test_mcp_gateway.py` pass (`16 passed in 1.15s`), but rely on this mock script, directly violating the Sovereign Zero-Mock Directive.

---

## 2. Logic Chain

1. **Step 1 (Zero-Mock Viability)**: From Observation 3, real MCP servers for all four tools (`shell`, `syncfusion`, `chrome_devtools`, `github`) physically exist on disk and execute properly under Node.js v24.19.0 and native Linux binaries over stdio JSON-RPC 2.0. Therefore, mock servers (`fake_mcp_stdio_server.py`) can be completely eliminated.
2. **Step 2 (Portability Defect)**: From Observation 1 and 4, `workspace.manifest.json` specifies Windows paths (`C:\...`, `K:\...`), while `services/mcp_gateway.py:501` checks `shutil.which(command[0])` and `Path(command[0]).exists()`. On Linux/WSL, this causes `from_manifest()` to fail with `ValueError`. Therefore, platform-aware path and launcher normalization must be implemented in `from_manifest()`.
3. **Step 3 (Manifest Server Aliasing)**: From Observation 2 and 4, `opencode.json` and user requirements refer to `matrix_shell`, but `mcp_gateway.py:488` only allows `"shell"`. Therefore, `matrix_shell` must be accepted and aliased to `"shell"`.
4. **Step 4 (Environment Isolation Flexibility)**: From Observation 4, `mcp_gateway.py` raises `ValueError` if an environment variable doesn't end with `_REF`. However, non-secret configurations like `SHELL_CWD` and `NODE_PATH` are required by the subprocess. Therefore, `from_manifest()` must allow string literals for general configs while resolving `*_REF` against `os.environ` for secret tokens.
5. **Step 5 (Agent Integration)**: From Observation 5, agents currently cannot access MCP capabilities because `mcp_gateway` is not integrated into `_handle_user_command()`. Since `MCPGateway.discover()` outputs OpenAI/Ollama function calling schemas, integrating `get_mcp_gateway()` into the agent chat loop will allow agents to dynamically discover and invoke MCP tools seamlessly.

---

## 3. Caveats

- `github-mcp-server` requires a valid GitHub token (`GITHUB_PERSONAL_ACCESS_TOKEN` or `GITHUB_TOKEN`) to execute authenticated operations against GitHub APIs; without credentials, read-only tools or unauthenticated tools work, but write actions will fail with GitHub 401 Unauthorized.
- `chrome_devtools` requires a display or headless Chrome executable to launch browser sessions; `--headless` flag is passed in the manifest, but if Chrome is not installed, browser launch operations will fail.
- No other caveats.

---

## 4. Conclusion

Requirement R3 is fully achievable with 100% genuine execution and zero mocks. The 4 MCP tools exist, conform to protocol `2024-11-05`, and are verifiable over stdio JSON-RPC 2.0. To activate `workspace.manifest.json`, the implementer must:
1. Update `services/mcp_gateway.py` with cross-platform command normalization (`_normalize_command_for_platform`) and server alias tolerance (`matrix_shell`).
2. Permit literal environment strings alongside `*_REF` resolution.
3. Expose an async singleton `get_mcp_gateway()` in `services/mcp_gateway.py`.
4. Wire `get_mcp_gateway()` into `agents/base_agent.py` and `agents/neo_agent.py` so discovered tools are merged into the LLM chat tool schema and routed during execution.
5. Replace `tests/fake_mcp_stdio_server.py` in test suites with live execution of `shell/server.js` or `syncfusion/server.js`.

---

## 5. Verification Method

1. **Test Manifest Parsing and Real Discovery**:
   ```bash
   SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "
   import asyncio
   from services.mcp_gateway import MCPGateway
   async def test():
       gw = MCPGateway.from_manifest()
       tools = await gw.discover()
       print('Discovered tools:', [t['function']['name'] for t in tools])
       assert len(tools) > 0
       await gw.close()
   asyncio.run(test())
   "
   ```
2. **Execute Real Shell MCP Tool Call**:
   ```bash
   SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "
   import asyncio
   from services.mcp_gateway import MCPGateway
   async def test():
       gw = MCPGateway.from_manifest()
       await gw.discover()
       res = await gw.call('run_shell_command', {'executable': 'python3', 'args': ['--version']})
       print('Tool Call Result:', res)
       assert res['ok'] is True
       await gw.close()
   asyncio.run(test())
   "
   ```
3. **Execute Real Syncfusion MCP Tool Call**:
   ```bash
   SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "
   import asyncio
   from services.mcp_gateway import MCPGateway
   async def test():
       gw = MCPGateway.from_manifest()
       await gw.discover()
       res = await gw.call('generate_react_datagrid', {'componentName': 'VerifiedGrid'})
       print('Tool Call Result:', res)
       assert res['ok'] is True
       assert 'VerifiedGrid' in res['content'][0]['text']
       await gw.close()
   asyncio.run(test())
   "
   ```
4. **Run Pytest Suite**:
   ```bash
   SOVEREIGN_BUS_SECRET=test .venv/bin/python -m pytest tests/test_mcp_gateway.py -v --no-cov
   ```
5. **Invalidation Conditions**:
   - If `from_manifest()` raises `ValueError` on Linux.
   - If any test relies on `fake_mcp_stdio_server.py`.
   - If `run_shell_command` or `generate_react_datagrid` fails to execute.
