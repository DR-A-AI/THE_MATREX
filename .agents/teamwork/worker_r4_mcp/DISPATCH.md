# Task Assignment: Integration Engineer — Milestone R4 (MCP Gateway & Smoke Test)

## Objectives
1. Read `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 121–125, 156–159).
2. Read `/mnt/e/matrex-dev/MASTER_PLAN.md` (§3.4, §6 CP-10) and `/mnt/e/matrex-dev/PROJECT.md` (§4.3).
3. Read reference specification in `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md` and source in `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py`.
4. Check if `/mnt/e/matrex-dev/reports/B3_mcp_audit.md` exists. If present, incorporate findings; if absent, implement the complete V2 reference specification.

## Implementation Requirements for `services/mcp_gateway.py`
- Replace broken stub in `services/mcp_gateway.py`:
  - Enforce `MCPServer` protocol with `list_tools()` and `call_tool(name, arguments)`.
  - Implement `StdioMCPServer` for JSON-RPC 2.0 communication over stdio:
    * Handshake: `initialize` -> `notifications/initialized`.
    * Discovery: `tools/list`.
    * Calling: `tools/call`.
    * Launcher allowlist strictly: `{"github-mcp-server", "chrome-devtools-mcp", "syncfusion-mcp", "shell-mcp", "npx", "node", "node.exe", "uvx", "python", "python3", "powershell", "pwsh", "powershell.exe", Path(sys.executable).name.lower()}`.
    * Enforce `shell=False` unconditionally.
    * Environment variable isolation: manifest environment values must end with `_REF`.
    * Payload size limits: max 64KB buffer.
  - Implement `CapabilityRegistry` and `Capability` dataclass.
  - Automatic risk and approval inference: destructive verbs or `readOnlyHint == False` escalate risk to `HIGH` and `requires_approval = True`.
  - Support sovereignty pre-flight gate.
  - Clean shutdown of child processes.
  - Strict Python 3.10 typing (`disallow_untyped_defs = true`), Bandit `# nosec` where applicable.

## Non-Interactive Offline Smoke Test Requirements
- Port `/mnt/k/THE-MATRIX-V2/tests/fake_mcp_stdio_server.py` as `tests/fake_mcp_stdio_server.py`:
  - Python stdio JSON-RPC server implementing `initialize`, `notifications/initialized`, `tools/list` (exposing tool `fixture_echo`), and `tools/call`.
  - Runs using `sys.executable` (0 network dependencies, no external node/npm required).
- Create `tests/test_mcp_gateway.py`:
  - Tests stdio gateway handshake, discovery, calling, argument validation, and clean shutdown.
- Create standalone smoke test script `smoke_test_mcp.py` at project root:
  - Invokes the stdio MCP gateway with `fake_mcp_stdio_server.py`.
  - Discovers tools.
  - Prints the discovered tool name (e.g. `Discovered MCP tool: fixture_echo`).
  - Calls the tool.
  - Closes gateway cleanly.
  - Exits with code 0.
  - Completely non-interactive and zero external network.

## Quality & Acceptance Verification
- Run:
  - `.venv/bin/python smoke_test_mcp.py` -> exits 0, prints >= 1 tool name.
  - `.venv/bin/python -m pytest tests/test_mcp_gateway.py -v --no-cov` -> all pass.
  - `.venv/bin/ruff check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py`
  - `.venv/bin/python -m black --check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py`
  - `.venv/bin/bandit -r services/mcp_gateway.py`
  - `grep -r "shell=True" services/mcp_gateway.py smoke_test_mcp.py`
  - Full regression: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`

## Write Ownership
- Exclusively owns: `services/mcp_gateway.py`, `tests/fake_mcp_stdio_server.py`, `tests/test_mcp_gateway.py`, `smoke_test_mcp.py`.

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_r4_mcp/handoff.md`.
