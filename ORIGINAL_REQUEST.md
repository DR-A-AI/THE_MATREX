# Original User Request

## 2026-09-23T06:26:17Z

Perform an adversarial audit, defect remediation, and quality verification over all changes introduced by the OpenCode CLI team across the Sovereign Matrix repository (/mnt/e/matrex-dev). Verify functional correctness, eliminate introduced concurrency hazards, resolve formatting and path portability defects, and ensure all test suites pass with zero regressions.

Working directory: /mnt/e/matrex-dev
Integrity mode: development

## Requirements

### R1. Concurrency Hazard Remediation
Fix the WebSocket broadcast race condition in `services/ui_bridge.py:112` by restoring snapshot iteration (`list(active_connections)`) under `send_lock` so concurrent client connects/disconnects do not crash broadcasts with `RuntimeError`. Guard against uninitialized `bus_client`.

### R2. Code Formatting & Style Compliance
Run Black formatter to resolve formatting failures across `core/zmq_hooks.py`, `core/failsafe.py`, `services/librarian.py`, and `agents/neo_agent.py`. Ensure both `.venv/bin/python -m black --check core agents services config tests matrix_main.py` and `.venv/bin/ruff check .` pass cleanly with 0 errors.

### R3. Workspace Portability & Path Neutrality
Replace hardcoded Windows paths `J:\THE_MATRIX` in `agents/neo_agent.py` (lines 221, 234, 247) with dynamic workspace resolution using `Path(os.getenv("MATRIX_ROOT", Path.cwd()))`.

### R4. Security Audit & Comment Syntax Cleanup
Normalize `# nosec` comment syntax in `core/failsafe.py`, `core/zmq_hooks.py`, and `agents/neo_agent.py` so Bandit does not report invalid test name parser warnings. Ensure `.venv/bin/bandit -r core/ services/ agents/ -x tests/` reports 0 high/medium issues.

### R5. Test Suite Verification & Invariant Preservation
Ensure all 25 unit and integration tests in `tests/` pass with zero failures via `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`. Preserve all architectural invariants (HMAC signing, key routing topology, emergency token stash limits, and `WindowsSelectorEventLoopPolicy`).

## Acceptance Criteria

### Concurrency & Portability
- [ ] `services/ui_bridge.py` uses `list(active_connections)` snapshot iteration during message broadcast.
- [ ] No hardcoded `J:\THE_MATRIX` paths remain in `agents/neo_agent.py`.

### Linting, Formatting & Security
- [ ] `.venv/bin/python -m black --check core agents services config tests matrix_main.py` passes with 0 reformatting warnings.
- [ ] `.venv/bin/ruff check .` passes with 0 errors.
- [ ] `.venv/bin/bandit -r core/ services/ agents/ -x tests/` reports 0 issues.

### Test Verification
- [ ] `.venv/bin/python -m pytest -q --no-cov` passes 100% (25/25 tests).
- [ ] Zero regressions in ZMQ bus communication or agent lifecycle.

## 2026-09-23T14:02:49Z

## Autonomous Operation Mode — Full Authorization

The user has granted full authorization for autonomous unattended operation.
Proceed without asking for any approvals or confirmations at any intermediate step.
All decisions, file writes, branch creation, test runs, and config changes are pre-approved.

**HARD STOP: Do NOT merge to `main`. Stop when PHASE2_COMPLETE.md is written.**

Use a large specialized team of engineers and experts. You are Team A Manager.
Assign every task to a named specialist. Engineers and experts run in parallel where possible.

---

## Team A — Specialist Roles
| Role | Owner |
|------|-------|
| Integration Engineer | Port Ollama + safe shell from /mnt/k/THE-MATRIX-V2 |
| Security Reviewer | Enforce shell=False, run Bandit, block shell=True in every PR |
| Bus Architect | Wire new EventTypes in core/models.py ONLY, protect immutable topology |
| Crawler Auditor | Verify all crawlers start/stop cleanly, Aegis QA gate |
| Test Engineer | Write pytest suites for every new module before integration |

## Parallel Track — Team B (OpenCode) is running simultaneously
Team B is already running as a background process and will write reports to:
`/mnt/e/matrex-dev/reports/` (B1_phase1_commit.md, B2_opencode_config.md, B3_mcp_audit.md, B4_skill_inventory.md)

Before starting R2-R5, check if /mnt/e/matrex-dev/reports/B1_phase1_commit.md exists.
If it does, R1 is already done by Team B — skip it and read their report.
If not, execute R1 yourself.

---

## Phase 0 — Planning First (mandatory)
1. Read: /mnt/e/matrex-dev/AGENTS.md, /mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md (if exists),
   /home/AH/.gemini/antigravity-cli/brain/78b62777-e870-4129-9930-7ca51741c1c7/HANDOFF_PHASE1_TO_PHASE2.md,
   /mnt/k/THE-MATRIX-V2/DELIVERY_HANDOFF.md
2. Write MASTER_PLAN.md to /mnt/e/matrex-dev/ with: task breakdown, team assignment, sequencing, risk map, verification checkpoints.
3. No agent starts implementation until MASTER_PLAN.md is complete.

---

## Requirements

### R1. Commit Phase 1 Remediation
Create branch `feat/engine-quality-and-bus-remediation`. Stage all modified files. Commit with:
```
chore(core): Phase 1 complete — audit remediation, portability, style compliance

- Fix WebSocket broadcast race condition (list snapshot under send_lock)
- Fix shell injection in neo_agent.py (shell=True → shlex.split)
- Eliminate all J:\THE_MATRIX hardcoded paths across 5 modules
- Add os import + MATRIX_ROOT/MATRIX_MEMORY_ROOT env resolution
- Black/Ruff/Bandit: all green (0 issues, 3159 LOC)
- Pytest: 25/25 passed
- Add msgpack, Pillow, mss, aiofiles, google-genai to requirements.txt
- Expand .gitignore: .vs/, .coverage, htmlcov/, *.db
- Consolidate [tool.ruff] exclude in pyproject.toml
```
Run all quality gates. All must pass before proceeding.

### R2. Ollama Integration
Port `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py` into the target codebase as `services/ollama_client.py`.
Must: discover Ollama via HTTP (OLLAMA_HOST / OLLAMA_BASE_URL), support model aliases,
call /api/chat stream=false, block non-loopback addresses, classify errors.
No automatic model downloads. Agents fall back gracefully when Ollama unavailable.
New tests: tests/test_ollama_client.py covering: available, unavailable, bad JSON, timeout, non-loopback rejection.

### R3. Safe Shell Execution for Agents
Port `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py` as `services/safe_shell.py`.
Wire into agent layer. Must have:
- Explicit allowlist (no free command strings)
- Workspace scoping to /mnt/e/matrex-dev
- Audit logging of every execution attempt
- Timeouts + process isolation
- shell=False everywhere. shell=True is forbidden.
New tests: tests/test_safe_shell.py

### R4. MCP Tool-Call Verification
Wait for Team B report at /mnt/e/matrex-dev/reports/B3_mcp_audit.md.
Implement the gaps identified. Run end-to-end smoke test: at least one MCP tool discovered and called.
Smoke test must be non-interactive and not require external network.

### R5. Crawler Audit and Skill Pipeline
Wait for Team B report at /mnt/e/matrex-dev/reports/B4_skill_inventory.md.
Verify crawlers: assistant_crawler.py, memory_crawler.py, librarian_crawler.py start/process/stop cleanly.
Port /mnt/k/THE-MATRIX-V2/40-skills/loader.py as `services/skill_loader.py`.
Skill pipeline: discover (metadata-only) → validate (SKILL_CONTRACT v1.0) → quarantine (bad) → curate (good) → Aegis QA → Smith+Morpheus SKILL_REVIEW_APPROVED event on bus → INJECTED.
New EventTypes (SKILL_PROMOTED, SKILL_REVIEW_APPROVED) go in core/models.py ONLY.
Tests: tests/test_skill_pipeline.py

---

## Acceptance Criteria

### R1 — Phase 1 Commit
- [ ] Branch feat/engine-quality-and-bus-remediation exists and pushed
- [ ] ruff check . → 0 errors
- [ ] black --check → clean
- [ ] bandit -r core/ services/ agents/ -x tests/ → 0 High/Medium
- [ ] python -m pytest -q --no-cov → 25/25 passed

### R2 — Ollama
- [ ] python -m pytest tests/test_ollama_client.py --no-cov → all pass
- [ ] SOVEREIGN_BUS_SECRET=x python -c "from services.ollama_client import probe; print(probe())" exits without crash
- [ ] grep -r "shell=True" core/ agents/ services/ → empty

### R3 — Safe Shell
- [ ] python -m pytest tests/test_safe_shell.py --no-cov → all pass
- [ ] Non-allowlisted command raises exception (tested)
- [ ] Path traversal attempt rejected (tested)
- [ ] grep -r "shell=True" core/ agents/ services/ → empty

### R4 — MCP
- [ ] Smoke test exits 0, prints ≥1 tool name from registered MCP server
- [ ] Non-interactive, no external network required

### R5 — Crawlers + Skills
- [ ] python -m pytest tests/test_crawlers_integration.py --no-cov → 15/15
- [ ] python -m pytest tests/test_skill_pipeline.py --no-cov → all pass
- [ ] No skill reaches INJECTED without SKILL_REVIEW_APPROVED bus event

### Global Gate (after all R)
- [ ] ruff check . → 0 errors
- [ ] black --check core agents services config tests matrix_main.py → clean
- [ ] bandit -r core/ services/ agents/ -x tests/ → 0 High/Medium
- [ ] python -m pytest -q --no-cov → ≥30 tests, all pass

---

## Verification Resources
- Source: /mnt/k/THE-MATRIX-V2 (WSL-accessible)
- Ollama router: /mnt/k/THE-MATRIX-V2/10-brain/model_router.py
- Safe shell: /mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py
- MCP gateway source: /mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py
- Skill loader: /mnt/k/THE-MATRIX-V2/40-skills/loader.py
- Skill contract: /mnt/k/THE-MATRIX-V2/40-skills/SKILL_CONTRACT.md
- Handoff doc: /home/AH/.gemini/antigravity-cli/brain/78b62777-e870-4129-9930-7ca51741c1c7/HANDOFF_PHASE1_TO_PHASE2.md
- AGENTS.md: /mnt/e/matrex-dev/AGENTS.md
- Team B reports: /mnt/e/matrex-dev/reports/

Working directory: /mnt/e/matrex-dev
Integrity mode: development

## Final Deliverable
Write /mnt/e/matrex-dev/PHASE2_COMPLETE.md with:
- All acceptance criteria checked with actual command output
- Branch name and commit hash
- Test counts and pass/fail
- Evidence from Team B reports
Do NOT merge to main. Notify when done.

## 2026-09-23T15:01:08Z

URGENT — Before writing PHASE2_COMPLETE.md, add Milestone R2-Live (Real Ollama Integration Test):

The user reports that llama3.2 is installed at E:\OLLAMA\manifests\registry.ollama.ai\library\llama3.2 — this means Ollama runs as a Windows process, not inside WSL. The current R2 tests used mocks only. The real Ollama service is NOT running on localhost:11434 from WSL.

Required actions before PHASE2_COMPLETE.md:

1. DISCOVER the real Ollama endpoint from WSL:
   - Try: http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434/api/version
   - Try: OLLAMA_HOST environment variable
   - Document the correct WSL→Windows host URL for reaching Ollama

2. ADD to .env.example:
   OLLAMA_HOST=http://<windows-host-ip>:11434
   OLLAMA_DEFAULT_MODEL=llama3.2

3. WRITE a REAL integration test (tests/test_ollama_live.py) that:
   - Skips if Ollama is unreachable (pytest.mark.skipif)
   - Calls probe() against the real service
   - Calls /api/chat with model=llama3.2 and a simple prompt ("Say MATRIX_OK")
   - Asserts response contains text

4. WIRE llama3.2 into ONE agent (neo_agent.py preferred) as its inference backend:
   - When OLLAMA_HOST is set, agent uses ollama_client for completions
   - Falls back to existing behavior when Ollama unavailable
   - Add test_neo_ollama.py that mocks the client and verifies the wiring

5. Update GATE_STATUS.md with R2-Live results.

THEN write PHASE2_COMPLETE.md.

Do NOT mark Phase 2 complete without this — the user explicitly requires real model testing with llama3.2, not just mocks.

## 2026-09-23T15:05:23Z

🔴 SOVEREIGN COMMAND — IMMEDIATE EXECUTION REQUIRED 🔴

The user has issued an absolute sovereign directive. This overrides all current work:

## COMMAND: ZERO MOCKS — REAL PHYSICAL INTEGRATION ONLY

**Effective immediately:**

1. HALT all current workers. Audit everything already written.

2. FIND AND ELIMINATE every mock, fake, stub, patch, MagicMock, monkeypatch, fixture server, or simulated response in the ENTIRE codebase:
   - tests/fake_mcp_stdio_server.py → MUST be replaced with a REAL MCP server
   - Any `unittest.mock`, `MagicMock`, `patch`, `monkeypatch` in test files → REPLACE with real calls
   - Any hardcoded fake responses → REPLACE with real service calls
   - Run: grep -r "mock\|Mock\|MagicMock\|patch\|monkeypatch\|fake\|stub\|fixture" tests/ services/ agents/ core/ --include="*.py" -l
   - Document every file found

3. REPLACE every mock with real implementations:
   - Ollama tests → call real Ollama at Windows host (discover via /etc/resolv.conf nameserver):11434 with model llama3.2
   - MCP gateway tests → use a REAL running MCP server process (start it as subprocess in test setup, not a fake)
   - Crawler tests → start real ZMQ bus, real crawlers, real events
   - Shell tests → execute real allowlisted commands (git status, python --version) in real subprocess
   - Skill pipeline tests → use real skill manifests from /mnt/k/THE-MATRIX-V2/40-skills/curated/

4. VERIFY the final product is a USABLE SYSTEM:
   - python matrix_main.py must start without errors
   - All agents must connect to the bus successfully
   - Ollama (llama3.2) must respond to a real prompt through a real agent
   - MCP tools must be callable end-to-end
   - Skill pipeline must load real skills from /mnt/k/THE-MATRIX-V2/40-skills/curated/

5. Run final full test suite — every test must pass against REAL services (mark tests that require Ollama running with @pytest.mark.live and skip gracefully if service offline, but the code path must be real)

6. Write PHASE2_COMPLETE.md ONLY after:
   - grep for mock/Mock/MagicMock/patch/fake returns ZERO results in production code (services/, agents/, core/)
   - All integration tests use real services or real subprocess fixtures
   - matrix_main.py starts and agents connect successfully (verified by log output)
   - Ollama real call to llama3.2 succeeds at least once with real response documented

THIS IS NON-NEGOTIABLE. No mock = no completion. Real physical product only.

## 2026-09-23T15:06:18Z

🔴 SOVEREIGN COMMAND UPDATE — SPECIFIC TARGETS FOUND:

Audit scan results. Address ALL of these:

## CRITICAL — Production code with mocks:

### 1. services/librarian.py:38
Contains: secret_data="EXTRACTED_SECRET_MOCK"
→ Replace with real secret extraction logic. If the secret comes from the neural bus KEY_INJECT event, wire it properly. No placeholder strings.

### 2. core/zmq_hooks.py:42
Contains comment: "# Mock skill execution logic"
→ Implement real skill execution via safe_shell.py or skill_loader.py. No mock comments in production.

## CRITICAL — Test infrastructure with fakes:

### 3. tests/fake_mcp_stdio_server.py
→ Replace with a REAL MCP server subprocess. Start a real MCP server (use the matrix_shell or github MCP from /mnt/e/matrex-dev/opencode.json or /mnt/k/mcp/) as a subprocess in conftest.py. Tests must call real MCP tool endpoints.

### 4. tests/test_ollama_client.py
→ All mock-based Ollama tests: keep unit tests for error cases (unreachable = real connection failure, not mocked). Add real integration tests in tests/test_ollama_live.py that call llama3.2 at the Windows host IP ($(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')):11434. Mark with @pytest.mark.live. Skip if unreachable but the call path must be real.

### 5. tests/test_mcp_gateway.py
→ Replace any fake/mock MCP calls with calls to a real MCP server subprocess started in conftest.py.

### 6. tests/test_skill_pipeline.py
→ Use REAL skill manifests from /mnt/k/THE-MATRIX-V2/40-skills/curated/sk_7b8af088deda/ instead of fake/synthetic manifests.

### 7. tests/test_crawlers_integration.py
→ Start REAL ZMQ bus (SOVEREIGN_BUS_SECRET=test), real crawlers as subprocesses or coroutines. No mocked ZMQ sockets.

## VERIFICATION COMMANDS (must all pass before PHASE2_COMPLETE.md):

```bash
# Zero mocks in production code:
grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py" | grep -v "# nosec" | grep -v "dispatch" → ZERO results

# Real Ollama probe (Windows host):
OLLAMA_HOST=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434 SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "from services.ollama_client import probe; import json; print(json.dumps(probe(), indent=2))"

# Real matrix_main.py startup test (5 second run):
SOVEREIGN_BUS_SECRET=test timeout 5 .venv/bin/python matrix_main.py 2>&1 | tail -20

# Full test suite:
SOVEREIGN_BUS_SECRET=test .venv/bin/python -m pytest -q --no-cov
```

Document ALL results in GATE_STATUS.md before writing PHASE2_COMPLETE.md.

## 2026-09-24T15:48:24Z

# Teamwork Project Prompt — Draft

> Status: LAUNCHED
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: A dual-track massive agent workforce:
> 1. **Team A (Teamwork Preview Multi-Agent Core):** Led by the Team Manager, deploying dedicated specialist agents in `agent-creator`, `agent-tool-builder`, `diagnosing-bugs`, `frontend-design`, `generative_ui`, `agent-orchestration-improve-agent`, and `agent-orchestration-multi-agent-optimize`.
> 2. **Team B (OpenCode CLI Parallel Specialist Track):** Headed by the OpenCode CLI (`/home/AH/.bun/bin/opencode`) configured with `subagent_depth: 3`, native LSP, and 6 MCP servers. OpenCode does NOT act alone; it must spawn specialized subagents to handle rigorous static analysis, type checking, syntax/grammar verification, and MCP protocol auditing.
> 3. **Supreme Auditor (وكيل البحث والفهم والمقارنة):** Dedicated Oracle/Ghost research agent benchmarking all deliverables against `PRODUCT_VISION.md` and `SOVEREIGN_CONSTITUTION.md`.

Conduct a comprehensive diagnostic audit and systemic architectural upgrade of the Sovereign Matrix agent environment (Matrix OS). The goal is to eliminate 100% of bottlenecks, silent failures, and architectural weaknesses, transforming it into a highly robust, low-latency, and production-grade local AI ecosystem that fulfills the Sovereign Covenant (`PRODUCT_VISION.md` and `SOVEREIGN_CONSTITUTION.md`).

Use a very large team of agents to accomplish this task.

Working directory: /mnt/e/matrex-dev
Integrity mode: development

## Supreme Manager Mandate

### 1. Dual-Team Architecture (فريقان متوازيان بالكامل)
The lead manager must enforce the Dual-Team protocol:
- **Team A (Teamwork Agents):** Core Python engine, Neural Bus, bridges (`ui_bridge.py`, `mcp_gateway.py`, `factory.py`), and Ollama local model integration.
- **Team B (OpenCode CLI Agents via Subprocess):** 
  The manager must launch OpenCode (`/home/AH/.bun/bin/opencode`) via subprocess in the terminal with `subagent_depth: 3`. 
  - OpenCode is strictly forbidden from working as a single agent; it must recruit subagents and specialist roles.
  - Team B is assigned to exploit its native **LSP (Language Server Protocol) + 6 MCP servers** to perform:
    a) Exhaustive static analysis, syntax verification, and type checking across Python/TypeScript.
    b) Audit and conformance testing of all 4 project MCP servers (`matrix_shell`, `chrome_devtools`, `syncfusion`, `github`).
    c) Dashboard React 19 type-safety and frontend linting.
  - Team B must write its audit reports to `reports/opencode_lsp_mcp_audit.md` before Team A merges deliverables.

### 2. Dedicated Research & Discrepancy Auditor (وكيل البحث والفهم والمقارنة)
The manager MUST instantiate a dedicated **Project Research & Understanding Agent** (Oracle/Ghost).
- **Mission:** Continuously explore, read, and cross-reference `/mnt/e/matrex-dev` and `/mnt/k/THE-MATRIX-V2` (`PRODUCT_VISION.md`, `SOVEREIGN_CONSTITUTION.md`, `workspace.manifest.json`, `70-memory-engine/`, `services/`, and `dashboard/`).
- **Audit & Comparison:** Compare what the true architecture requires against what Team A and Team B produce. Any discrepancy, superficial mock, or deviation must be flagged and rejected immediately. No implementing agent is permitted to self-certify.
- **Deliverable:** Generate `reports/PROJECT_ARCHITECTURE_BENCHMARK.md`.

## Requirements

### R1. Synchronous CLI Interaction & Bus Bidirectional Bridge
Upgrade `send_command.py` into a robust, synchronous CLI client. It must transmit commands to the Neural Bus and synchronously await, parse, and stream the agent's textual and tool execution responses directly to the user's terminal with zero silent drops.

### R2. Engine Latency & Pre-Warming (Zero Cold Start)
Eliminate the ~30s initial inference delay by introducing an asynchronous model pre-warming pulse at engine boot. Ensure `matrix_main.py` and `base_agent.py` never block the asyncio loop during Ollama tensor evaluation.

### R3. Project MCP Gateway & Workspace Manifest Activation
Activate `workspace.manifest.json` inside `services/mcp_gateway.py` so agents can dynamically discover and invoke the 4 project MCP tools (`matrix_shell`, `chrome_devtools`, `syncfusion`, `github`). Team B (OpenCode) must verify MCP protocol compliance.

### R4. Complete Web Stack Synchronization
Ensure `matrix_main.py` (Engine :5555), `services/ui_bridge.py` (FastAPI/WS :8000), and `dashboard/` (Vite :5173) can boot and synchronize seamlessly.

## Acceptance Criteria

### Synchronous Interaction & Verification
- [ ] Running the CLI command waits and successfully prints the agent's actual textual response to the terminal in real time.
- [ ] UI Bridge (`services/ui_bridge.py`) forwards agent `STATE_UPDATE` events without dropping frames or blocking the loop.

### OpenCode (Team B) Verification
- [ ] OpenCode CLI runs with subagents, analyzes the codebase via LSP, and produces `reports/opencode_lsp_mcp_audit.md` certifying zero syntax or type errors.
- [ ] MCP servers in `opencode.json` pass protocol handshake and tool-listing checks.

### Engine & MCP Verification
- [ ] An automated test proves that agents can trigger MCP tools across `mcp_gateway.py` and handle results gracefully.
- [ ] Engine boots with zero unhandled exceptions and executes round-trip inference under 5s on warm model.

### Research & Truth Gate
- [ ] `reports/PROJECT_ARCHITECTURE_BENCHMARK.md` is generated by the Research Agent, comparing all deliverables against `PRODUCT_VISION.md` and certifying 100% genuine execution with zero mocks.

---
*Next: when approved → delegate via invoke_subagent (see Delegation Protocol)*




