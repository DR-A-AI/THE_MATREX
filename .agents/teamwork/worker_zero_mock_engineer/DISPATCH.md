# Task Assignment: Lead Integration Engineer — Sovereign Zero-Mock Implementation

## Directive
Execute the Sovereign Command: "ZERO MOCKS — REAL PHYSICAL INTEGRATION ONLY".
Authoritative request: `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (under `## 2026-09-23T15:05:23Z` and `## 2026-09-23T15:06:18Z`).

## Mandate & Scope

### 1. Production Code De-Mocking (Zero Toleration)
- `services/librarian.py:38`:
  Eliminate `secret_data="EXTRACTED_SECRET_MOCK"`. Implement real extraction logic reading from `AuthVault` or neural bus token store.
- `core/zmq_hooks.py:42`:
  Eliminate `# Mock skill execution logic`. Implement real skill execution utilizing `services.safe_shell` or `services.skill_loader`.
- Verify production code contains ZERO mock strings:
  `grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py" | grep -v "# nosec" | grep -v "dispatch"`
  MUST return ZERO lines.

### 2. Ollama Real Host Discovery & Live Integration
- In `services/ollama_client.py`:
  Update `normalize_ollama_base_url()` so that it accepts the WSL2 Windows host gateway IP (`172.*.*.*` or nameserver from `/etc/resolv.conf`) and `OLLAMA_HOST` env var, while still rejecting external public internet domains.
- Update `.env.example`:
  ```
  OLLAMA_HOST=http://<windows-host-ip>:11434
  OLLAMA_DEFAULT_MODEL=llama3.2
  ```
- Wire `llama3.2` into `agents/neo_agent.py`:
  When `OLLAMA_HOST` is configured, `NeoAgent` uses `services.ollama_client` for completions with graceful fallback when offline. Ensure `shell=False`.
- Create `tests/test_ollama_live.py`:
  Integration test calling the real Windows host Ollama daemon at `http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434` with model `llama3.2`. Mark with `@pytest.mark.live`. Skip gracefully if unreachable.
- Create `tests/test_neo_ollama.py`:
  Test NeoAgent's Ollama integration path.
- Keep unit tests in `tests/test_ollama_client.py` for real error conditions (real connection failures, bad JSON, timeouts).

### 3. Real MCP Server Integration
- Replace `tests/fake_mcp_stdio_server.py`:
  Use a REAL MCP server subprocess (from `/mnt/e/matrex-dev/opencode.json`, `services/`, `/mnt/k/mcp/`, or real Python stdio server).
- In `tests/test_mcp_gateway.py` and `smoke_test_mcp.py`:
  Execute real stdio handshake and tool call against the real MCP server process.

### 4. Real Skills Pipeline Integration
- In `tests/test_skill_pipeline.py`:
  Use REAL skill manifests from `/mnt/k/THE-MATRIX-V2/40-skills/curated/sk_7b8af088deda/` (copying or reading the curated manifests) instead of synthetic manifests.

### 5. Real Matrix Engine & Crawlers Verification
- In `tests/test_crawlers_integration.py`:
  Ensure all tests run real ZMQ bus, real crawlers, and real events (`SOVEREIGN_BUS_SECRET=test`).
- Test `matrix_main.py` startup:
  `SOVEREIGN_BUS_SECRET=test timeout 5 .venv/bin/python matrix_main.py 2>&1 | tail -20`
  Verify router, crawlers, and agents start and connect without errors.

### 6. Mandatory Verification Commands
Run all of the following commands and record outputs:
1. `grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py" | grep -v "# nosec" | grep -v "dispatch"` -> MUST be ZERO results.
2. `OLLAMA_HOST=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434 SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "from services.ollama_client import probe; import json; print(json.dumps(probe(), indent=2))"`
3. `SOVEREIGN_BUS_SECRET=test timeout 5 .venv/bin/python matrix_main.py 2>&1 | tail -20`
4. `.venv/bin/python smoke_test_mcp.py`
5. `.venv/bin/ruff check .`
6. `.venv/bin/python -m black --check core agents services config tests matrix_main.py smoke_test_mcp.py`
7. `.venv/bin/bandit -r core/ services/ agents/ -x tests/`
8. `grep -rn "shell=True" core/ agents/ services/`
9. `SOVEREIGN_BUS_SECRET=test .venv/bin/python -m pytest -q --no-cov`

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_zero_mock_engineer/handoff.md`.
