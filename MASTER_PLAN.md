# MASTER PLAN — Sovereign Matrix Phase 2 Development & Remediation

**Project**: Sovereign Matrix (`DR-A-AI/THE_MATREX`)  
**Root Directory**: `/mnt/e/matrex-dev`  
**Execution Authority**: Sovereign Commander (Dr. Anas Hilal)  
**Autonomous Operation Mode**: Full Authorization (Unattended Operation)  
**Hard Stop Condition**: Do **NOT** merge to `main`. Stop when `PHASE2_COMPLETE.md` is verified and authored.  
**Version**: 2.0.0  
**Date**: 2026-09-23  

---

## 1. Executive Summary & Mission

The Sovereign Matrix repository underwent an intensive Phase 1 audit and remediation that resolved critical concurrency hazards, eliminated hardcoded Windows paths, resolved AST security issues, and brought quality gates (Black, Ruff, Bandit, Pytest 25/25) to 100% compliance.

Phase 2 transitions the engine from remediation into robust, air-gapped sovereign capability expansion:
1. **Commit Phase 1 baseline**: Formalize the 62 uncommitted remediation files into branch `feat/engine-quality-and-bus-remediation`.
2. **Local Brain Integration (R2)**: Port the offline, loopback-only Ollama client (`services/ollama_client.py`) with zero cloud dependencies and graceful offline fallbacks.
3. **Safe Shell Execution (R3)**: Implement zero-trust sandboxed command execution (`services/safe_shell.py`) enforcing an absolute `shell=False` invariant, strict command allowlists, and workspace boundary confinement.
4. **MCP Tool-Call Gateway (R4)**: Implement an offline, stdio JSON-RPC MCP gateway (`services/mcp_gateway.py`) with capability registration, argument schema validation, and risk-escalation gates, verified via non-interactive offline smoke tests.
5. **Skill Lifecycle Pipeline & Crawler Audit (R5)**: Implement the declarative skill loader (`services/skill_loader.py`) enforcing `SKILL_CONTRACT` v1.0 across a 5-stage lifecycle (`DISCOVERED` -> `VALIDATED` -> `PREPARED` -> `PROMOTED` -> `INJECTED`), bus review events (`SKILL_REVIEW_APPROVED`, `SKILL_PROMOTED`), and verify the health of all three crawler sub-systems.

---

## 2. Team Structure & Specialist Role Assignments

Per the Autonomous Operation Directive, tasks are divided among named specialists operating with clear boundaries:

| Specialist Role | Primary Responsibility | Target Modules / Ownership | Invariant Enforced |
|---|---|---|---|
| **Integration Engineer** | Porting core capabilities from `/mnt/k/THE-MATRIX-V2` into `/mnt/e/matrex-dev` | `services/ollama_client.py`, `services/safe_shell.py`, `services/mcp_gateway.py`, `services/skill_loader.py` | Standalone modules, Python 3.10 typing, zero cloud dependency, loopback isolation |
| **Security Reviewer** | AST & static analysis, shell safety, Bandit auditing, sandbox bounds | `core/aegis_validator.py`, `agents/aegis_qa.py`, global audits | Absolute `shell=False` everywhere; `# nosec` compliance; 0 Bandit High/Medium |
| **Bus Architect** | Neural bus schema governance, event models, topology protection | `core/models.py`, `core/neural_bus.py` | Only modify `EventType` in `core/models.py`; protect HMAC-SHA256 DEALER/ROUTER & key topology |
| **Crawler Auditor** | Lifecycle verification of crawlers, SQLite isolation, Aegis QA gates | `services/assistant_crawler.py`, `services/memory_crawler.py`, `services/librarian_crawler.py`, `core/librarian_crawler.py` | AssistantCrawler is sole distributor; token masking `***{last4}`; async non-blocking I/O; clean startup/teardown |
| **Test Engineer** | Pre-integration unit tests, integration test suites, smoke testing | `tests/test_ollama_client.py`, `tests/test_safe_shell.py`, `tests/test_mcp_smoke.py`, `tests/test_skill_pipeline.py` | Write comprehensive tests before integration; mock external I/O; verify offline execution |

### Parallel Track: Team B (OpenCode) Interface

Team B operates concurrently as a background process, writing status and discovery reports to `/mnt/e/matrex-dev/reports/`:
- `reports/B1_phase1_commit.md`: Indicates Team B executed the Phase 1 git commit. *(Checked: Does NOT exist; proof of life confirmed `proof_of_life.txt`. Team A will execute R1 commit).*
- `reports/B2_opencode_config.md`: OpenCode configuration and workspace telemetry.
- `reports/B3_mcp_audit.md`: MCP server inventory and gap analysis (prerequisite checkpoint for R4 final validation).
- `reports/B4_skill_inventory.md`: Discovered skill repository inventory (prerequisite checkpoint for R5 skill ingestion).

---

## 3. Milestones & Detailed Task Breakdown

```
Phase 0: Planning & Specification Mining [COMPLETED]
   │
   ▼
Milestone R1: Phase 1 Commit & Quality Baseline Gate
   │
   ├──────────────────────────────┬──────────────────────────────┐
   ▼                              ▼                              ▼
Milestone R2: Ollama Client    Milestone R3: Safe Shell       Parallel Watch: Team B Reports
   │                              │                              │ (B3_mcp_audit, B4_skills)
   ├──────────────────────────────┴──────────────────────────────┘
   │
   ├──────────────────────────────┬──────────────────────────────┐
   ▼                              ▼                              ▼
Milestone R4: MCP Gateway      Milestone R5: Skills & Crawlers
   │                              │
   └──────────────────────────────┴──────────────────────────────┐
                                                                 ▼
                                                  Global Quality Gate & Final Attestation
                                                  (Authoring PHASE2_COMPLETE.md)
```

### Phase 0: Planning & Specification Mining (Current Phase)
- **Status**: Completed by `worker_phase0_plan`.
- **Outputs**:
  - `/mnt/e/matrex-dev/MASTER_PLAN.md`: Comprehensive sequencing, risk mitigation, and verification manual.
  - `/mnt/e/matrex-dev/PROJECT.md`: System architecture, deduplicated feature inventory (56 items), interface contracts, and code layout.

---

### Milestone R1: Commit Phase 1 Remediation
- **Lead Role**: Team A Manager / Integration Engineer.
- **Pre-Conditions**:
  - Verify if `/mnt/e/matrex-dev/reports/B1_phase1_commit.md` exists. If yes, skip to R2.
  - If no, verify working tree contains all Phase 1 fixes.
- **Tasks**:
  1. Create branch `feat/engine-quality-and-bus-remediation` from current HEAD (`feat/workspace-setup`).
  2. Stage all modified working tree files (excluding `.agents/`, `reports/`, and untracked artifacts).
  3. Execute commit with the exact required commit message:
     ```text
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
  4. Verify Git branch status and log.

---

### Milestone R2: Local Brain Integration (Ollama Client)
- **Lead Role**: Integration Engineer & Test Engineer.
- **Source**: `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py` and `30-runtime/ollama_health.py`.
- **Target**: `services/ollama_client.py` and `tests/test_ollama_client.py`.
- **Tasks**:
  1. Implement `services/ollama_client.py`:
     - URL normalization enforcing loopback addresses (`127.0.0.1`, `localhost`, `[::1]`) and `http` scheme. Reject all non-loopback hosts.
     - HTTP transport via stdlib `urllib.request` with timeout and error classification:
       `OllamaError`, `OllamaConfigurationError`, `OllamaConnectionError`, `OllamaTimeoutError`, `OllamaHTTPError`, `OllamaProtocolError`, `OllamaModelNotFoundError`.
     - `OllamaClient` methods: `health()`, `tags()`, `model_names()`, `resolve_model()`, `has_model()`, `chat(stream=False)`.
     - `ModelRouter` mapping agent roles (`NEO`, `MORPHEUS`, `ORACLE`, `SMITH`, `GHOST`, `TRINITY`) to preferred local models (`llama3.2`, `qwen3-coder`, `deepseek-r1:8b`, `gemma3`).
     - Decouple from missing `cloud_provider`: wrap cloud fallback in safe optional imports; default to pure local mode.
     - Export top-level `probe() -> tuple[int, dict[str, Any]]` guaranteed never to raise an unhandled exception.
  2. Implement `tests/test_ollama_client.py`:
     - Test URL normalization (valid loopbacks accepted, external IPs/schemes rejected, empty strings raise).
     - Test `probe()` returning exit code 0 when online and 1 when offline without traceback.
     - Test mock transport handling for valid chat, bad JSON, timeouts, HTTP 404/500, and model resolution.
     - Verify AST contains zero instances of `shell=True`.
  3. Run quality gates: Black, Ruff, Bandit, Pytest.

---

### Milestone R3: Safe Shell Execution for Agents
- **Lead Role**: Security Reviewer & Integration Engineer.
- **Source**: `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py` and `30-runtime/execution_hand.py`.
- **Target**: `services/safe_shell.py` and `tests/test_safe_shell.py`.
- **Tasks**:
  1. Implement `services/safe_shell.py`:
     - `ShellCapabilityValidator` with strict allowlists:
       * `python`: constrained to `-m` with modules `compileall`, `pytest`, `unittest`, executed via `sys.executable`.
       * `git`: constrained to read-only subcommands `status`, `log`, `diff`.
       * `CLI`: constrained to `check`, `verify`, `models`, `status`, `run`.
       * `bash`: constrained to scripts physically residing within `workspace_root`, size <= 1MB.
     - Workspace path resolution enforcing strict containment within `/mnt/e/matrex-dev` (rejects `..`, absolute paths outside workspace, NUL bytes).
     - Custom exception hierarchy: `SafeShellError`, `DisallowedCommandError`, `WorkspaceEscapeError`, `CommandTimeoutError`, `ScriptExecutionError`.
     - Subprocess execution: strictly `shell=False` everywhere, explicit timeouts, output truncation to prevent memory spikes.
     - Comprehensive audit logging via structured logger and optional audit sink.
     - Export Ollama function-calling schemas for shell capabilities.
  2. Implement `tests/test_safe_shell.py`:
     - Test non-allowlisted commands raise `DisallowedCommandError`.
     - Test path traversal attempts (`../secret`, `/etc/passwd`) raise `WorkspaceEscapeError`.
     - Test valid python and git commands succeed.
     - Test `shell=False` enforcement via subprocess mocking.
     - Test timeout termination and audit logging.
  3. Wire into Agent Layer:
     - Update `agents/neo_agent.py` to route local shell calls through `ShellCapabilityValidator`.
  4. Run quality gates: Black, Ruff, Bandit, Pytest.

---

### Milestone R4: MCP Tool-Call Verification
- **Lead Role**: Integration Engineer & Test Engineer.
- **Source**: `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py` and `tests/test_mcp_stdio_gateway.py`.
- **Target**: `services/mcp_gateway.py` and `tests/test_mcp_smoke.py`.
- **Tasks**:
  1. Coordinate with Team B report: check `/mnt/e/matrex-dev/reports/B3_mcp_audit.md`. If not yet available, utilize standard V2 MCP gateway contract.
  2. Implement `services/mcp_gateway.py`:
     - Remove broken legacy stubs (`npx.cmd`, `WindowsProactorEventLoopPolicy`).
     - Implement `MCPServer` protocol and `StdioMCPServer` (JSON-RPC 2.0 handshake over stdio, `tools/list`, `tools/call`).
     - Launcher allowlist restricting executable commands to known safe interpreters.
     - Implement `MCPGateway` with tool registration, JSON schema parameter validation, argument size capping (64KB), and execution timeout handling.
     - Risk & Approval Engine: automatically elevate risk to `HIGH` and flag `requires_approval=True` for state-modifying or destructive operations (`write*`, `delete*`, `create*`, `update*`).
  3. Implement offline, non-interactive smoke test:
     - Provide `tests/fake_mcp_stdio_server.py` exposing tool `fixture_echo`.
     - Implement `tests/test_mcp_smoke.py` that discovers `fixture_echo`, calls it with valid/invalid inputs, prints discovered tool name, and cleanly terminates with exit code 0 without internet or Node.js.
  4. Run quality gates: Black, Ruff, Bandit, Pytest.

---

### Milestone R5: Crawler Audit and Skill Pipeline
- **Lead Role**: Bus Architect, Crawler Auditor & Integration Engineer.
- **Source**: `/mnt/k/THE-MATRIX-V2/40-skills/loader.py`, `SKILL_CONTRACT.md`, and target crawler suite.
- **Target**: `core/models.py`, `services/skill_loader.py`, and `tests/test_skill_pipeline.py`.
- **Tasks**:
  1. Coordinate with Team B report: check `/mnt/e/matrex-dev/reports/B4_skill_inventory.md`.
  2. Bus Architecture Extension:
     - Add `SKILL_PROMOTED = "skill_promoted"` and `SKILL_REVIEW_APPROVED = "skill_review_approved"` to `EventType` in `core/models.py`.
     - Verify zero alterations to key distribution event types or HMAC validation logic.
  3. Implement `services/skill_loader.py`:
     - 5-stage lifecycle: `DISCOVERED` -> `VALIDATED` -> `PREPARED` -> `PROMOTED` -> `INJECTED`.
     - `SKILL_CONTRACT` v1.0 enforcement: strictly validate metadata, require verified license, enforce closed 6-tool allowlist (`docs.read`, `memory.read`, `memory.search`, `planning.emit`, `skills.discover`, `skills.validate`). Reject arbitrary shell tools.
     - Offensive pattern blocking: reject malicious or high-risk skills during discovery.
     - Quarantine mechanism: isolate invalid or corrupted skills into `quarantine/`.
     - Neural bus gate: skills cannot transition from `PROMOTED` to `INJECTED` without verified `SKILL_REVIEW_APPROVED` bus event from Smith/Morpheus and Commander approval.
  4. Verify Crawler Sub-systems:
     - Run `tests/test_crawlers_integration.py` (15/15 passing).
     - Verify clean start/stop for `AssistantCrawler`, `MemoryCrawler`, `LibrarianCrawler`.
     - Verify path traversal guards in `services/librarian_crawler.py` and `core/librarian_crawler.py`.
     - Verify Asymmetric QA gate for code patterns in memory crawler.
  5. Implement `tests/test_skill_pipeline.py`:
     - Test full lifecycle transitions.
     - Test rejection of unapproved tools, missing licenses, or path escapes.
     - Test quarantine moves.
     - Test bus event requirement for skill injection.
  6. Run quality gates: Black, Ruff, Bandit, Pytest.

---

### Milestone Global Gate: Final Verification & Attestation
- **Lead Role**: Security Reviewer & Team A Manager.
- **Pre-Conditions**: All milestones R1 through R5 completed and verified.
- **Tasks**:
  1. Full Quality Gate Sweep:
     - `ruff check .` -> exactly 0 errors.
     - `python -m black --check core agents services config tests matrix_main.py` -> 0 reformats.
     - `python -m bandit -r core/ services/ agents/ -x tests/` -> 0 High/Medium issues.
     - `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python -m pytest -q --no-cov` -> >= 30 tests, 100% passing.
     - `grep -r "shell=True" core/ agents/ services/` -> exactly 0 occurrences.
     - `python core/aegis_validator.py` -> passes sovereign topology validation.
  2. Attestation Documentation:
     - Author `/mnt/e/matrex-dev/PHASE2_COMPLETE.md` with verbatim test execution logs, branch name, commit SHA, test counts, and Team B report references.
  3. Hard Stop Enforcement: Confirm NO merge to `main`. Notify user and orchestrator.

---

## 4. Sequencing, Workflows & Dependency Graph

```text
                               ┌────────────────────────────────┐
                               │  Phase 0: Planning & Mining   │
                               │  (MASTER_PLAN.md, PROJECT.md)  │
                               └───────────────┬────────────────┘
                                               │
                                               ▼
                               ┌────────────────────────────────┐
                               │ Milestone R1: Phase 1 Commit   │
                               │ (feat/engine-quality-and-bus)  │
                               └───────────────┬────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
        ┌─────────────────────────────┐                 ┌─────────────────────────────┐
        │ Milestone R2: Ollama Client │                 │ Milestone R3: Safe Shell    │
        │ - services/ollama_client.py │                 │ - services/safe_shell.py    │
        │ - tests/test_ollama_client  │                 │ - tests/test_safe_shell     │
        └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
        ┌─────────────────────────────┐                 ┌─────────────────────────────┐
        │ Milestone R4: MCP Gateway   │                 │ Milestone R5: Skill Pipeline│
        │ - services/mcp_gateway.py   │                 │ - core/models.py EventTypes │
        │ - tests/test_mcp_smoke.py   │                 │ - services/skill_loader.py  │
        │ - Awaits B3_mcp_audit.md    │                 │ - tests/test_skill_pipeline │
        │                             │                 │ - Awaits B4_skill_inventory │
        └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                                               ▼
                               ┌────────────────────────────────┐
                               │ Global Gate: Quality & Tests   │
                               │ - Ruff 0, Black 0, Bandit 0    │
                               │ - Pytest >= 30/30 passed       │
                               │ - Aegis Topology Validated     │
                               │ - PHASE2_COMPLETE.md Written   │
                               └────────────────────────────────┘
```

### Dependency Rules:
1. **R1 must precede all implementations**: Branch `feat/engine-quality-and-bus-remediation` establishes the verified baseline. No feature code is written before this commit exists.
2. **R2 & R3 run in parallel**: Ollama client and Safe Shell execution are decoupled service capabilities that do not share state.
3. **R4 & R5 depend on baseline + Team B reports**:
   - R4 depends on `services/safe_shell.py` for process execution primitives and awaits `reports/B3_mcp_audit.md`.
   - R5 depends on `core/models.py` schema additions and awaits `reports/B4_skill_inventory.md`.
4. **Global Gate requires all milestones complete**: No partial attestation.

---

## 5. Risk Map & Mitigation Strategies

| Risk ID | Risk Category | Threat / Hazard Description | Impact | Probability | Mitigation Strategy & Verification |
|---|---|---|---|---|---|
| **RSK-01** | Concurrency | WebSocket broadcast iteration race condition (`RuntimeError: Set changed size during iteration`) | Fatal crash of `ui_bridge.py` during client churn | Low (remédiated) | Iterate over `list(active_connections)` snapshot protected by `asyncio.Lock` (`send_lock`). Verified via test suite and static review. |
| **RSK-02** | Platform Quirk | Python asyncio Proactor loop used on Windows instead of Selector loop | Fatal ZMQ socket crash on Windows host | Medium | Enforce `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())` on `win32` platform in `matrix_main.py` and `tests/conftest.py`. Prohibit Proactor in `mcp_gateway.py`. |
| **RSK-03** | Network Isolation | Ollama client connecting to public/external IP addresses or accepting remote redirects | Data exfiltration, SSRF, non-airgapped leakage | High | Strict `normalize_ollama_base_url` validator rejecting any host not in `{"127.0.0.1", "localhost", "::1"}`. Reject `https`. Unit test non-loopback rejection. |
| **RSK-04** | Remote Code Exec | Shell command injection via agent tools using `shell=True` or unescaped strings | Arbitrary code execution on host system | Critical | Absolute ban on `shell=True`. Enforce `shlex.split(posix=...)` and argv lists. Enforce `ShellCapabilityValidator` allowlists. Verified by Bandit and `grep -r "shell=True"`. |
| **RSK-05** | Directory Traversal | Escaping `/mnt/e/matrex-dev` workspace root via `../` in file tools, bash scripts, or skills | Unauthorized disk read/write, host compromise | High | Canonical path resolution via `Path.resolve()`, enforcing `path.is_relative_to(workspace_root)`. Reject NUL bytes. Disallow absolute paths outside root. |
| **RSK-06** | Constitutional Violation | Modifying or bypassing immutable key distribution topology (e.g. agents fetching keys directly) | Breach of Sovereign Constitution, Aegis validator failure | Critical | Code changes to `core/models.py` restricted to enum additions. `emergency_token_stash` (max 2, TTL 300s) and `AssistantCrawler` routing remain immutable. Aegis pre-commit validator run in CI. |
| **RSK-07** | Bus Spoofing / Replay | Forged ZMQ messages, replay of captured frames, or missing secret | Unauthorized bus takeover, state corruption | High | Zero-trust HMAC-SHA256 signature on every DEALER frame, 16-byte nonce tracking with 5s replay window, 60s TTL limit. Mandatory `SOVEREIGN_BUS_SECRET`. |
| **RSK-08** | Flaky CI / External I/O | Tests relying on external Ollama service, live npm packages, or internet network | Flaky builds, false failures in offline CI | High | Mock transports (`UrllibTransport` mock) in `test_ollama_client.py`. Python stdio fixture script in `test_mcp_smoke.py`. 100% offline test execution. |

---

## 6. Verification Checkpoints & Acceptance Test Matrix

Every milestone has unambiguous verification commands that must exit 0:

| Checkpoint | Target Milestone | Verification Command | Expected Output / Exit Criteria |
|---|---|---|---|
| **CP-01** | R1 Commit | `git branch --show-current && git log -n 1 --oneline` | Branch is `feat/engine-quality-and-bus-remediation`, latest commit is Phase 1 chore commit. |
| **CP-02** | R1 Quality | `.venv/bin/ruff check . && .venv/bin/python -m black --check core agents services config tests matrix_main.py` | Ruff: 0 errors; Black: clean (0 files reformatted). |
| **CP-03** | R1 Security | `.venv/bin/bandit -r core/ services/ agents/ -x tests/` | 0 High, 0 Medium issues across 3100+ LOC. |
| **CP-04** | R1 Baseline Tests | `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov` | Exactly `25 passed` (exit code 0). |
| **CP-05** | R2 Ollama Probe | `SOVEREIGN_BUS_SECRET=x python -c "from services.ollama_client import probe; print(probe())"` | Prints `(0, {...})` or `(1, {...})` without traceback or unhandled exception. |
| **CP-06** | R2 Ollama Tests | `python -m pytest tests/test_ollama_client.py -v --no-cov` | 100% tests pass (covering loopback, bad JSON, timeouts, offline probe). |
| **CP-07** | R3 Safe Shell Tests | `python -m pytest tests/test_safe_shell.py -v --no-cov` | 100% tests pass (disallowed command raises, path traversal raises, audit logged). |
| **CP-08** | R3 Shell Safety | `grep -r "shell=True" core/ agents/ services/` | Empty output (exit code 1). Zero occurrences. |
| **CP-09** | R4 MCP Smoke | `python -m pytest tests/test_mcp_smoke.py -v --no-cov` | Discovers and invokes `fixture_echo` tool over stdio JSON-RPC without network. |
| **CP-10** | R5 Crawler Suite | `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python -m pytest tests/test_crawlers_integration.py -v --no-cov` | Exactly `15 passed` (exit code 0). |
| **CP-11** | R5 Skills Tests | `python -m pytest tests/test_skill_pipeline.py -v --no-cov` | 100% tests pass (contract validation, quarantine, bus review events). |
| **CP-12** | Global Gate | `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef python -m pytest -q --no-cov` | `>= 30 passed`, 0 failed. |
| **CP-13** | Aegis Topology | `python core/aegis_validator.py` | Prints `AEGIS PASSED: Sovereign Topology is intact.` (exit code 0). |

---

## 7. Acceptance Criteria Checklist & Definition of Done

### Milestone R1 — Phase 1 Commit
- [ ] Branch `feat/engine-quality-and-bus-remediation` exists and is checked out.
- [ ] Working tree changes committed with required commit message.
- [ ] `ruff check .` -> 0 errors.
- [ ] `black --check` -> clean.
- [ ] `bandit -r core/ services/ agents/ -x tests/` -> 0 High/Medium.
- [ ] `python -m pytest -q --no-cov` -> 25/25 passed.

### Milestone R2 — Ollama Integration
- [ ] `services/ollama_client.py` created and type-annotated (`mypy` compliant).
- [ ] Non-loopback addresses strictly rejected.
- [ ] Decoupled from cloud provider (pure local operation).
- [ ] `probe()` function callable and returns `(int, dict)` without unhandled crash.
- [ ] `tests/test_ollama_client.py` passes 100%.

### Milestone R3 — Safe Shell Execution
- [ ] `services/safe_shell.py` created with strict allowlists (`python -m`, `git status/log/diff`, `CLI`).
- [ ] `shell=False` enforced in every subprocess invocation.
- [ ] Workspace traversal attempts (`../`) raise `WorkspaceEscapeError`.
- [ ] Disallowed commands raise `DisallowedCommandError`.
- [ ] Full audit logging of command attempts.
- [ ] `agents/neo_agent.py` updated to use safe shell validator.
- [ ] `tests/test_safe_shell.py` passes 100%.

### Milestone R4 — MCP Gateway
- [ ] `services/mcp_gateway.py` refactored to implement `MCPServer`, `StdioMCPServer`, and `MCPGateway`.
- [ ] Removed `npx.cmd` and Proactor event loop policy violations.
- [ ] Automatic risk and approval inference for state-modifying operations.
- [ ] Argument size and JSON schema validation enforced.
- [ ] Non-interactive, offline smoke test (`tests/test_mcp_smoke.py`) exits 0 and prints discovered tool name.

### Milestone R5 — Crawler Audit & Skill Pipeline
- [ ] `core/models.py` updated with `SKILL_PROMOTED` and `SKILL_REVIEW_APPROVED` EventTypes.
- [ ] `services/skill_loader.py` implements 5-stage lifecycle and `SKILL_CONTRACT` v1.0.
- [ ] Closed tool allowlist (6 tools) strictly enforced.
- [ ] Invalid/malicious skills quarantined into `quarantine/`.
- [ ] Bus event verification: skill cannot reach `INJECTED` without `SKILL_REVIEW_APPROVED`.
- [ ] All 15 crawler integration tests pass (`test_crawlers_integration.py`).
- [ ] `tests/test_skill_pipeline.py` passes 100%.

### Global Gate & Attestation
- [ ] Full quality gate clean (Ruff 0, Black clean, Bandit 0 High/Medium).
- [ ] Full test suite `>= 30` tests pass with zero regressions.
- [ ] Zero occurrences of `shell=True` across `core/`, `agents/`, `services/`.
- [ ] Aegis topology validator passes.
- [ ] Attestation report written to `/mnt/e/matrex-dev/PHASE2_COMPLETE.md`.
- [ ] **HARD STOP**: Git branch remains unmerged to `main`.

---

## 8. Operational Rules & Guardrails

1. **Integrity Mandate**: No hardcoded test results, facade implementations, or bypasses. All code must maintain real state and execute genuine logic.
2. **Minimal Change Principle**: Modify only what is strictly necessary. Never perform unrelated refactoring.
3. **Pre-Modification Re-Reading**: Always inspect a file before editing it.
4. **Secret Protection**: Never commit `.env` or `secrets/`. Never log full tokens; use `***{last4}`.
5. **Event Loop Discipline**: Never change the event loop policy to Proactor on Windows; preserve `WindowsSelectorEventLoopPolicy`.
6. **No Blocking I/O**: In agents and crawlers, offload disk access and subprocesses to worker threads or async primitives.
