# Milestone R4 Handoff Report: MCP Gateway & Smoke Test

## 1. Observation

### 1.1 Context & Gaps Identified
- Checked `/mnt/e/matrex-dev/reports/B3_mcp_audit.md`: Not present (status: absent). In accordance with `DISPATCH.md` §Objectives item 4, implemented the complete V2 reference specification from `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py`.
- Replaced legacy stub in `/mnt/e/matrex-dev/services/mcp_gateway.py` (which invoked `npx.cmd` and set `WindowsProactorEventLoopPolicy()`, violating ZMQ selector loop requirements and platform portability).

### 1.2 Delivered Artifacts
1. **`services/mcp_gateway.py`** (630 lines):
   - Protocol `MCPServer`: defines `list_tools`, `call_tool`, and `close`.
   - Class `StdioMCPServer`:
     * JSON-RPC 2.0 handshake: `initialize` -> `notifications/initialized`.
     * Discovery: `tools/list`.
     * Calling: `tools/call`.
     * Strict launcher allowlist:
       `{"github-mcp-server", "chrome-devtools-mcp", "syncfusion-mcp", "shell-mcp", "npx", "node", "node.exe", "uvx", "python", "python3", "powershell", "pwsh", "powershell.exe", Path(sys.executable).name.lower()}`.
     * `shell=False` unconditionally enforced (line 372) with `# nosec: B603`.
     * Environment isolation: enforces `*_REF` suffix on environment mappings.
     * Max payload limit: 64KB buffer (`MAX_PAYLOAD_BYTES = 65536`).
     * Clean process termination (`terminate` -> `wait(2.0)` -> `kill` -> transport close).
   - Data structures: `CapabilityInput`, `Capability`, and `CapabilityRegistry`.
   - Automatic risk & approval escalation:
     * Destructive verbs (`delete*`, `write*`, `create*`, `update*`, `send*`, `execute*`) or annotations (`readOnlyHint == False`, `destructiveHint == True`) infer `risk = "HIGH"` and `requires_approval = True`.
   - Sovereignty pre-flight gate integration: evaluates `sovereignty.pre_flight(...)` when approval is required; fails closed if gate is omitted.
   - Exception hierarchy: `MCPError`, `MCPProtocolError`, `MCPValidationError`, `MCPTimeoutError`, `MCPApprovalRequiredError`.
   - Strict Python 3.10 typing (`from __future__ import annotations`, full argument and return type hints).
2. **`tests/fake_mcp_stdio_server.py`** (72 lines):
   - Deterministic stdio JSON-RPC 2.0 test fixture server in pure Python.
   - Exposes `fixture_echo` tool taking integer `count` and returning `{content: [{type: "text", text: str(count)}]}`.
   - Zero external network dependencies, executed via `sys.executable`.
3. **`tests/test_mcp_gateway.py`** (388 lines):
   - 16 comprehensive unit tests covering handshake, discovery, calling, JSON schema validation, NUL byte rejection, 64KB payload bounds, launcher allowlist rejection, environment isolation, risk escalation, sovereignty gate pre-flight approval, process shutdown, manifest loading, and sync adapter.
4. **`smoke_test_mcp.py`** (68 lines):
   - Standalone, offline, non-interactive smoke test script at repository root.
   - Discovers `fixture_echo`, prints `Discovered MCP tool: fixture_echo`, calls the tool with `count: 42`, asserts result, closes cleanly, and exits with code 0.

### 1.3 Verbatim Execution Results

#### 1. Standalone Smoke Test Execution
Command:
```bash
.venv/bin/python smoke_test_mcp.py
```
Output:
```
Discovered MCP tool: fixture_echo
MCP Tool call successful: result={'ok': True, 'content': [{'type': 'text', 'text': '42'}]}
```
Exit code: 0

#### 2. Unit Tests Execution
Command:
```bash
.venv/bin/python -m pytest tests/test_mcp_gateway.py -v --no-cov
```
Output:
```
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- /mnt/e/matrex-dev/.venv/bin/python
cachedir: .pytest_cache
rootdir: /mnt/e/matrex-dev
configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
plugins: anyio-4.15.1, langsmith-0.14.0, asyncio-1.4.0, cov-7.1.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 16 items

tests/test_mcp_gateway.py::test_stdio_handshake_and_discovery PASSED     [  6%]
tests/test_mcp_gateway.py::test_stdio_tool_call_success PASSED           [ 12%]
tests/test_mcp_gateway.py::test_argument_schema_validation_type_mismatch PASSED [ 18%]
tests/test_mcp_gateway.py::test_argument_schema_validation_missing_required PASSED [ 25%]
tests/test_mcp_gateway.py::test_argument_schema_validation_unknown_property PASSED [ 31%]
tests/test_mcp_gateway.py::test_nul_byte_rejection_in_arguments PASSED   [ 37%]
tests/test_mcp_gateway.py::test_argument_payload_limit_enforced PASSED   [ 43%]
tests/test_mcp_gateway.py::test_unregistered_tool_returns_error PASSED   [ 50%]
tests/test_mcp_gateway.py::test_launcher_allowlist_enforcement PASSED    [ 56%]
tests/test_mcp_gateway.py::test_environment_variable_isolation PASSED    [ 62%]
tests/test_mcp_gateway.py::test_risk_and_approval_inference PASSED       [ 68%]
tests/test_mcp_gateway.py::test_sovereignty_pre_flight_gate PASSED       [ 75%]
tests/test_mcp_gateway.py::test_clean_process_shutdown PASSED            [ 81%]
tests/test_mcp_gateway.py::test_from_manifest_loader PASSED              [ 87%]
tests/test_mcp_gateway.py::test_run_allowed_synchronous_adapter PASSED   [ 93%]
tests/test_mcp_gateway.py::test_mcp_smoke PASSED                         [100%]

============================== 16 passed in 0.95s ==============================
```
Exit code: 0

#### 3. Ruff Linter Verification
Command:
```bash
.venv/bin/ruff check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py tests/fake_mcp_stdio_server.py
```
Output:
```
All checks passed!
```
Exit code: 0

#### 4. Black Code Style Verification
Command:
```bash
.venv/bin/python -m black --check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py tests/fake_mcp_stdio_server.py
```
Output:
```
All done! ✨ 🍰 ✨
4 files would be left unchanged.
```
Exit code: 0

#### 5. Bandit Security Audit
Command:
```bash
.venv/bin/bandit -r services/mcp_gateway.py
```
Output:
```
[tester]	WARNING	nosec encountered (B603), but no failed test on file ./services/mcp_gateway.py:367
Run started:2026-09-23 14:53:55.093723+00:00

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 630
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
Files skipped (0):
```
Exit code: 0

#### 6. Shell Security Check
Command:
```bash
grep -rn "shell=True" services/mcp_gateway.py smoke_test_mcp.py tests/fake_mcp_stdio_server.py tests/test_mcp_gateway.py
```
Output: (Empty / Exit code 1 — 0 occurrences found)

Command:
```bash
grep -rn "shell=False" services/mcp_gateway.py
```
Output:
```
372:            shell=False,
```

#### 7. Full Regression Test Suite
Command:
```bash
SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
```
Output:
```
........................................................................ [ 76%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/google/genai/types.py:42
  /mnt/e/matrex-dev/.venv/lib/python3.14/site-packages/google/genai/types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
94 passed, 1 warning in 45.62s
```
Exit code: 0 (94 passed, 0 failures, 0 regressions).

---

## 2. Logic Chain

1. **Protocol Implementation**:
   - `services/mcp_gateway.py` implements the `MCPServer` protocol and `StdioMCPServer` transport conforming to JSON-RPC 2.0 specifications.
   - Handshake sequence performs bidirectional protocol negotiation (`initialize` request -> response validation -> `notifications/initialized`).
   - Supports both `Content-Length:` header frames and standard newline-delimited JSON-RPC messages.

2. **Security Controls Enforcement**:
   - `ALLOWED_LAUNCHERS` contains exclusively approved interpreters and server binaries. Executable checks verify both presence in allowlist and existence on system PATH.
   - `shell=False` is passed unconditionally into `asyncio.create_subprocess_exec` (`services/mcp_gateway.py:372`), eliminating shell injection vulnerabilities.
   - Environment variables must follow the `*_REF` convention, resolving secret tokens from the host environment without hardcoded secrets.
   - Argument sizes and payload frames are capped at 64KB (`MAX_PAYLOAD_BYTES`), preventing memory exhaustion.
   - NUL byte checks prevent C-string truncation attacks in inputs.

3. **Risk & Approval Escalation**:
   - Destructive verbs (`delete*`, `write*`, `create*`, `update*`, `send*`, `execute*`) and tool annotations (`readOnlyHint == False` or `destructiveHint == True`) automatically elevate capability risk to `HIGH` and enforce `requires_approval = True`.
   - Tool execution checks the `sovereignty.pre_flight` gate; unauthorized requests or missing sovereignty configurations fail closed.

4. **Zero-Network Offline Smoke Testing**:
   - `tests/fake_mcp_stdio_server.py` implements a minimal, deterministic in-process stdio JSON-RPC server with zero external dependencies (no Node.js, npm, or network required).
   - `smoke_test_mcp.py` exercises the end-to-end gateway stack using `fake_mcp_stdio_server.py`, discovers `fixture_echo`, calls the tool, verifies output, cleanly terminates child processes, and exits 0.

5. **Regression Verification**:
   - Running the entire project test suite confirmed all 94 tests pass cleanly with zero regressions.

---

## 3. Caveats

- No caveats. All requirements specified in `DISPATCH.md`, `PROJECT.md` §4.3, and `MASTER_PLAN.md` §3.4 have been fully implemented and verified against strict quality gates.

---

## 4. Conclusion

Milestone R4 (MCP Gateway & Smoke Test) is fully implemented, verified, and complete:
- `services/mcp_gateway.py` provides a production-grade, secure, asynchronous MCP gateway.
- `tests/fake_mcp_stdio_server.py` provides a reliable local fixture.
- `tests/test_mcp_gateway.py` provides 16 automated unit tests.
- `smoke_test_mcp.py` provides an offline, non-interactive smoke test exiting 0 and printing the discovered tool name.
- Quality gates (Ruff, Black, Bandit, shell=False check, and 94/94 full test suite) are 100% clean.

---

## 5. Verification Method

To independently verify the implementation, run the following commands from the repository root (`/mnt/e/matrex-dev`):

```bash
# 1. Run standalone non-interactive smoke test (prints tool name and exits 0)
.venv/bin/python smoke_test_mcp.py

# 2. Run unit test suite
.venv/bin/python -m pytest tests/test_mcp_gateway.py -v --no-cov

# 3. Verify linting
.venv/bin/ruff check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py tests/fake_mcp_stdio_server.py

# 4. Verify formatting
.venv/bin/python -m black --check services/mcp_gateway.py tests/test_mcp_gateway.py smoke_test_mcp.py tests/fake_mcp_stdio_server.py

# 5. Verify security scanning
.venv/bin/bandit -r services/mcp_gateway.py

# 6. Verify absence of shell=True
grep -rn "shell=True" services/mcp_gateway.py smoke_test_mcp.py

# 7. Run full project test regression suite
SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
```

Invalidation conditions:
- Any non-zero exit code from `smoke_test_mcp.py`.
- Any failure in `tests/test_mcp_gateway.py`.
- Any occurrence of `shell=True` in `services/mcp_gateway.py` or `smoke_test_mcp.py`.
- Any failure in the full regression suite.
