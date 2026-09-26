# Handoff Report — Phase 0 Specification Mining: Core & Git State

**Agent**: `spec_miner_phase0_1`  
**Working Directory**: `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_1`  
**Timestamp**: 2026-09-23T14:15:00Z  
**Recipient**: `fe5ac203-4cd6-4438-a176-a09d6bf8f404` (parent orchestrator)

---

## 1. Observation

### 1.1 Specification Documents Directly Inspected

1. **`ORIGINAL_REQUEST.md`** (`/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` & `/mnt/e/matrex-dev/ORIGINAL_REQUEST.md`):
   - **Phase 1 Remediation Requirements**:
     - `R1`: Concurrency hazard remediation in `services/ui_bridge.py:112` via `list(active_connections)` snapshot under `send_lock`, plus guard against uninitialized `bus_client`.
     - `R2`: Code formatting & style compliance via `black` and `ruff check .` with 0 errors.
     - `R3`: Workspace portability eliminating hardcoded `J:\THE_MATRIX` via `Path(os.getenv("MATRIX_ROOT", Path.cwd()))`.
     - `R4`: Security audit and comment syntax cleanup (`# nosec` normalization, 0 Bandit High/Medium).
     - `R5`: Test suite verification (25/25 pytest passing with `SOVEREIGN_BUS_SECRET`), preserving architectural invariants.
   - **Phase 2 Development Requirements**:
     - Autonomous unattended operation mode authorized.
     - **Hard Stop**: Do NOT merge to `main`. Stop when `PHASE2_COMPLETE.md` is written.
     - Team B (OpenCode) parallel track: writes to `/mnt/e/matrex-dev/reports/` (`B1_phase1_commit.md`, `B2_opencode_config.md`, `B3_mcp_audit.md`, `B4_skill_inventory.md`).
     - Rule for R1: If `/mnt/e/matrex-dev/reports/B1_phase1_commit.md` exists, R1 is done by Team B. If not, Team A must execute R1.
     - Feature Porting tasks:
       * `R2`: Ollama client (`services/ollama_client.py`) ported from `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py`.
       * `R3`: Safe shell execution (`services/safe_shell.py`) ported from `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py`.
       * `R4`: MCP tool-call verification (smoke test, no external network).
       * `R5`: Crawler audit & skill pipeline (`services/skill_loader.py` from `/mnt/k/THE-MATRIX-V2/40-skills/loader.py`, `SKILL_PROMOTED`, `SKILL_REVIEW_APPROVED` bus events in `core/models.py`).

2. **`AGENTS.md`** (`/mnt/e/matrex-dev/AGENTS.md`):
   - **Boot / Entrypoints**:
     - Core engine: `python matrix_main.py` starts `NeuralBusRouter` + `Failsafe` + `SecureLibrarian` + `Memory/Assistant/Librarian` crawlers + 6 agents (`neo`, `trinity`, `morpheus`, `smith`, `oracle`, `base`).
     - Web stack (3 fixed ports): Vite dashboard `:5173`, FastAPI `services/ui_bridge.py` `:8000` (`/ws`, `/api`), ZMQ bus `tcp://127.0.0.1:5555`. Windows launcher `IGNITE_MATRIX.bat` terminates ports 5173/8000/5555/5557 before boot.
     - `PYTHONPATH` must include repo root.
   - **Env**:
     - `SOVEREIGN_BUS_SECRET` is strictly mandatory. `core/neural_bus.py:19-25` raises `ValueError` at import if unset.
     - Never log full tokens; mask as `***{last4}`.
   - **Python Toolchain**:
     - Python >=3.10 (CI pins 3.10).
     - Tooling: `black` (100 cols, py310), `ruff check .`, `mypy` (`disallow_untyped_defs = true`), `bandit -r core/ services/ agents/ -x tests/`.
     - Pydantic v2 only (`ConfigDict`, `model_dump(mode="json")`, `datetime.now(timezone.utc)`). One legacy `datetime.utcnow` at `core/models.py:82`.
   - **Tests**:
     - Discovery restricted to `tests/` (`test_*.py`). Full: `python -m pytest -q` (enforces coverage). Fast/single: `--no-cov`.
   - **Windows Quirk (Load-Bearing)**:
     - `WindowsSelectorEventLoopPolicy` required on Windows (not Proactor). Preserved in `matrix_main.py:101-103` and `tests/conftest.py`.
   - **Immutable Architecture (`SOVEREIGN_CONSTITUTION.md`)**:
     - `core/models.py:EventType` + `EventPayload` is the sole bus schema.
     - `core/neural_bus.py`: DEALER clients ↔ ROUTER broadcast; HMAC-SHA256 signature, 16-byte nonce, 5s replay window, 60s TTL. `REGISTER` frames are not broadcast.
     - Key topology: Neo/Trinity only emit `TOKEN_EXTRACTED` (never store); only `AssistantCrawler` listens and broadcasts `KEY_INJECT`; agents maintain `emergency_token_stash` (`MAX_STASH_SIZE=2`, 300s TTL) and must not JIT-request keys directly.
     - Crawlers: async middleware with `asyncio.to_thread` for disk walk, path-traversal guard via `is_relative_to`, Aegis QA gate on `def `/`import `.
     - UI replies: `STATE_UPDATE`/`TASK_COMPLETED` with `source_agent_id` and `payload.message`.

3. **`SOVEREIGN_CONSTITUTION.md`** (`/mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md`):
   - **Supreme Rule**: Commander authority (Dr. Anas Hilal). Zero autonomy on architectural authority.
   - **Immutable Topology**:
     1. Blind Extractors: Neo and Trinity emit `TOKEN_EXTRACTED` only, never store.
     2. Assistant Crawler: Sole distributor listening to `TOKEN_EXTRACTED` and broadcasting `KEY_INJECT`.
     3. Emergency Stash: `MatrixAgent` base maintains `emergency_token_stash` (max 2, 300s TTL). No JIT key requests by agents.
     4. Zero-Trust Neural Bus: All ZMQ events signed with HMAC-SHA256.
     5. Aegis Enforcement: Code violating topology is physically rejected by Aegis validator (`core/aegis_validator.py`).

4. **`HANDOFF_PHASE1_TO_PHASE2.md`** (`/home/AH/.../HANDOFF_PHASE1_TO_PHASE2.md`):
   - Phase 1 audit and repair achieved clean gates (Ruff 0 errors, Black 41 files unchanged, Bandit 0 issues, Pytest 25/25 passed).
   - Documented the exact state: branch was `feat/workspace-setup` with 60+ modified uncommitted files.
   - Formulated the exact commit message required for Phase 1 branch `feat/engine-quality-and-bus-remediation`.

5. **`DELIVERY_HANDOFF.md`** (`/mnt/k/THE-MATRIX-V2/DELIVERY_HANDOFF.md`):
   - Source reference for Phase 2 ports: `model_router.py` (Ollama HTTP discovery, loopback enforcement, error taxonomy), `safe_shell_capabilities.py` (allowlist, no `shell=True`, path traversal guards), and `loader.py` (skill loader pipeline).

---

### 1.2 Git State in `/mnt/e/matrex-dev` Directly Observed

- **Branch (`git branch -a`)**:
  ```text
  * feat/workspace-setup
    main
    remotes/origin/22salfd22-a11y-fix-preview-deployments
    remotes/origin/HEAD -> origin/main
    remotes/origin/feat/workspace-setup
    remotes/origin/gh-pages
    remotes/origin/main
  ```
  - Branch `feat/engine-quality-and-bus-remediation`: **DOES NOT EXIST** (neither local nor remote).
- **Recent Git Log (`git log -n 5 --oneline`)**:
  ```text
  cc1de34 (HEAD -> feat/workspace-setup, origin/feat/workspace-setup) chore(workspace): add VS Code/VS workspace setup and agent guide
  44de7aa chore: add .gitattributes to normalize line endings
  3272e7c (origin/main, origin/HEAD, main) chore(vendor): sync github/awesome-copilot@...
  f317c03 chore(vendor): sync github/awesome-copilot@...
  94e354d chore(vendor): sync github/awesome-copilot@...
  ```
  - **No Phase 1 commit exists** in git history. The commit `chore(core): Phase 1 complete — audit remediation, portability, style compliance` has not yet been executed.
- **Working Tree Status (`git status -s`)**:
  - **17 staged deleted pycache files**: `agents/__pycache__/*.pyc`, `config/__pycache__/*.pyc`, `core/__pycache__/*.pyc`, `services/__pycache__/*.pyc`.
  - **62 modified files in working tree** (uncommitted):
    `.env.example`, `.gitignore`, `THE_MATREX.code-workspace`, `agents/__init__.py`, `agents/aegis_qa.py`, `agents/base_agent.py`, `agents/morpheus_agent.py`, `agents/neo_agent.py`, `agents/oracle_agent.py`, `agents/smith_agent.py`, `agents/trinity_agent.py`, `auth_vault.py`, `config/settings.py`, `core/aegis_validator.py`, `core/auth_vault.py`, `core/engine.py`, `core/factory.py`, `core/failsafe.py`, `core/governance.py`, `core/key_router.py`, `core/librarian_crawler.py`, `core/matrix_vision.py`, `core/memory_manager.py`, `core/models.py`, `core/neural_bus.py`, `core/watchdog.py`, `core/zmq_hooks.py`, `create_keys_secure.py`, `dashboard/src/App.jsx`, `dashboard/src/pages/ChatPage.jsx`, `dashboard/src/pages/LoginPage.jsx`, `dashboard/src/pages/MetricsPage.jsx`, `demo_supreme_extraction.py`, `e2e_test.py`, `inject_memory.py`, `load_test.py`, `matrix_main.py`, `memory/inject_genesis_memory.py`, `neural_bus.py`, `pyproject.toml`, `requirements.txt`, `services/assistant_crawler.py`, `services/librarian.py`, `services/librarian_crawler.py`, `services/mcp_gateway.py`, `services/memory_crawler.py`, `services/ui_bridge.py`, `test_agent.py`, `test_joker.py`, `test_keys.py`, `test_loyalty.py`, `test_ui.py`, `test_ws.py`, `tests/conftest.py`, `tests/test_auth_vault.py`, `tests/test_crawlers_integration.py`, `tests/test_librarian.py`, `tests/test_memory_manager.py`, `tests/test_message_serialization.py`, `tests/test_neo_authority.py`, `tests/test_real_world_crawlers.py`, `watchdog.py`.
  - **Untracked files**:
    `.agents/`, `ORIGINAL_REQUEST.md`, `opencode.json`, `reports/`, `vendor/awesome-copilot/.../obj/`.

---

### 1.3 Team B and Reports Directory Status

- Directory `/mnt/e/matrex-dev/reports/` was created during inspection.
- Contents: exactly one file: `/mnt/e/matrex-dev/reports/proof_of_life.txt` containing verbatim `OPENCODE_IS_ALIVE`.
- Report `/mnt/e/matrex-dev/reports/B1_phase1_commit.md`: **DOES NOT EXIST**.
- Consequently, Team B has **NOT** committed R1, and Team A must execute R1.

---

### 1.4 Status of R1 Code Fixes Directly Inspected

1. **`services/ui_bridge.py`**:
   - Lines 111-118:
     ```python
     if send_lock:
         async with send_lock:
             for conn in list(active_connections):  # noqa: PERF101
                 try:
                     await conn.send_text(msg_str)
                 except Exception:
                     logger.exception("WebSocket send failed")
     ```
     Snapshot iteration `list(active_connections)` under `send_lock` is implemented.
   - Lines 181-185:
     ```python
     if bus_client is not None:
         await bus_client.send(event)
     else:
         logger.error("Cannot forward user command: bus_client is not initialized")
     ```
     Guard against uninitialized `bus_client` is implemented.

2. **`agents/neo_agent.py`**:
   - Line 201: `workspace_root = Path(os.getenv("MATRIX_ROOT", Path.cwd())).resolve()`.
   - Tool functions (`read_local_file`, `write_local_file`, `edit_local_file`, `view_file_lines`, `list_directory`, `inspect_code_definition`, `run_local_command`) resolve paths against `workspace_root`.
   - Lines 213-220: `run_local_command` uses `shlex.split(command, posix=(os.name != "nt"))`, passes argv list to `subprocess.run(args, capture_output=True, text=True, cwd=workspace, check=False)`, with `# nosec: B603` and bounds check (`len(command) > 8192`).
   - Zero hardcoded `J:\THE_MATRIX` in `neo_agent.py`.

3. **`shell=True` Verification**:
   - `grep -r "shell=True" core/ agents/ services/` returned **ZERO MATCHES**.

4. **Hardcoded Windows Paths**:
   - Eliminated from `agents/neo_agent.py`, `core/memory_manager.py`, `core/governance.py`, `core/key_router.py`, `services/librarian_crawler.py`.
   - **Residual Path Caveats**:
     * `core/librarian_crawler.py:22`: `target_dir: str = r"J:\antigravity-awesome-skills-main"` (default parameter).
     * `services/clerk_extractor_clone.js:10` and `services/clerk_extractor_visible.js:9,30`: contain `J:\\THE_MATRIX\\chrome_temp` and `J:\\THE_MATRIX\\scratch\\clerk_vision.png`.

5. **Quality Gates Directly Executed**:
   - **Black**: `.venv/bin/python -m black --check core agents services config tests matrix_main.py`
     * Result: `All done! 41 files would be left unchanged.` (Exit code 0).
   - **Ruff**: `.venv/bin/ruff check .`
     * Result: `All checks passed!` (Exit code 0).
   - **Bandit**: `.venv/bin/bandit -r core/ services/ agents/ -x tests/`
     * Result: `Total lines of code: 3165. Total issues: 0 High, 0 Medium, 0 Low` (Exit code 0).
   - **Pytest**: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`
     * Result: `25 passed, 1 warning in 45.42s` (Exit code 0).
   - **Aegis Topology Validator**: `.venv/bin/python core/aegis_validator.py`
     * Result: `AEGIS PASSED: Sovereign Topology is intact.` (Exit code 0).

---

## 2. Logic Chain

1. **Premise**: Per `ORIGINAL_REQUEST.md` (lines 70-73), before starting R2-R5, the system must check whether `/mnt/e/matrex-dev/reports/B1_phase1_commit.md` exists. If it exists, R1 is considered complete by Team B; if not, Team A must execute R1.
2. **Observation**: Inspection of `/mnt/e/matrex-dev/reports/` confirmed that only `proof_of_life.txt` exists (`OPENCODE_IS_ALIVE`). File `B1_phase1_commit.md` does not exist.
3. **Inference**: Team B has not committed Phase 1. Team A must create the branch `feat/engine-quality-and-bus-remediation` and execute the Phase 1 commit.
4. **Premise**: `ORIGINAL_REQUEST.md` (lines 87-102) requires `feat/engine-quality-and-bus-remediation` to contain the Phase 1 audit remediation with all quality gates green before proceeding to Phase 2.
5. **Observation**: All source code changes for R1-R4 (WebSocket concurrency fix, `neo_agent.py` path portability and `shell=False`, Bandit `# nosec` syntax, and formatting) are already present in the uncommitted working directory.
6. **Observation**: Real-time runs of Black, Ruff, Bandit, Pytest (25/25), and Aegis topology validator confirm 100% compliance with zero regressions.
7. **Inference**: The working tree is in a pristine, ready-to-commit state for R1. Creating branch `feat/engine-quality-and-bus-remediation`, staging the modified files, and committing with the exact requested message satisfies R1 immediately.
8. **Premise**: Invariants specified in `SOVEREIGN_CONSTITUTION.md` and `AGENTS.md` (HMAC signing, key routing topology, stash limit=2, `WindowsSelectorEventLoopPolicy`) must be preserved during all subsequent steps.
9. **Inference**: Any new features (Ollama client `services/ollama_client.py`, safe shell `services/safe_shell.py`, skill pipeline `services/skill_loader.py`) must integrate cleanly into this verified architecture without modifying the constitution or violating `core/models.py` schema isolation.

---

## 3. Caveats

1. **Uncommitted Staged Deletions**: There are 17 staged deletions of Python 3.14 `.pyc` files in git stage. These should be committed alongside the Phase 1 changes or cleaned up per `.gitignore`.
2. **Residual `J:\` Drive Defaults**:
   - `core/librarian_crawler.py:22` retains `target_dir: str = r"J:\antigravity-awesome-skills-main"` as a default parameter, whereas `services/librarian_crawler.py` uses `./skills`.
   - `services/clerk_extractor_*.js` contains Windows paths.
3. **Team B Concurrency**: Team B has dropped `proof_of_life.txt` into `reports/`. Subsequent tasks should monitor `reports/` for `B2_opencode_config.md`, `B3_mcp_audit.md`, and `B4_skill_inventory.md` before executing R4/R5.
4. **Pytest Warning**: Python 3.14 emits a `DeprecationWarning` regarding `_UnionGenericAlias` from `google.genai.types.py:42`. This is an external library deprecation and does not affect test pass rates.

---

## 4. Conclusion

- **R1 Code Implementation**: 100% COMPLETE in the working directory. WebSocket race condition is resolved, `neo_agent.py` uses portable dynamic paths and `shell=False` with `shlex.split`, Bandit annotations are valid, Black and Ruff are 100% clean, and all 25 unit/integration tests pass.
- **R1 Git Commit**: NOT YET EXECUTED. Branch `feat/engine-quality-and-bus-remediation` must be created from `feat/workspace-setup`, and the 62 modified files committed with the specified commit message.
- **Team B Status**: Active (`OPENCODE_IS_ALIVE` confirmed via `reports/proof_of_life.txt`), but no milestone reports have landed yet.
- **Readiness for Phase 2**: The repository is fully validated, architecturally sound, and ready for R1 branch commit followed by R2-R5 module porting.

---

## 5. Verification Method

To independently verify these findings, run the following commands from `/mnt/e/matrex-dev`:

1. **Verify Git Branch and Absence of Phase 1 Commit**:
   ```bash
   git branch -a
   git status -s
   git log -n 5 --oneline
   ```
2. **Verify Team B Report Absence**:
   ```bash
   ls -la reports/
   ```
3. **Verify Zero `shell=True`**:
   ```bash
   grep -r "shell=True" core/ agents/ services/
   ```
4. **Verify Quality Gates**:
   ```bash
   .venv/bin/python -m black --check core agents services config tests matrix_main.py
   .venv/bin/ruff check .
   .venv/bin/bandit -r core/ services/ agents/ -x tests/
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
   .venv/bin/python core/aegis_validator.py
   ```

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Bus Core | Zero-Trust NeuralBusClient | HMAC-SHA256 authenticated DEALER client with anti-replay and TTL checks | `EventPayload`, `SOVEREIGN_BUS_SECRET` env var, `endpoint` | Signed multipart ZMQ frames `[signature, json_bytes]` | Drops unverified signatures, duplicate nonces, or expired TTL (>60s) with CRITICAL log | `core/neural_bus.py:28` |
| 2 | Bus Core | NeuralBusRouter | Central ZMQ ROUTER binding to port 5555, non-blocking broadcast with slow client eviction | Inbound DEALER frames `[sender, signature, msg_bytes]` | Multipart broadcast to all other active clients | Evicts client on `zmq.ZMQError` (EAGAIN/unreachable), logs error | `core/neural_bus.py:137` |
| 3 | Bus Core | Event Registration Framing | DEALER identity handshake with ROUTER without leaking to bus | Frame `[b"REGISTER", b""]` | Client added to router `active_clients` set | Filtered by Router (`signature == b"REGISTER"` is never broadcast) | `core/neural_bus.py:61,168` |
| 4 | Schema | Pydantic Event Schema | Canonical EventPayload schema with strict serialization | `event_type`, `source_agent_id`, `correlation_id`, `payload`, `metadata` | Validated Pydantic v2 `EventPayload` model | `pydantic.ValidationError` if types or structure invalid | `core/models.py:49` |
| 5 | UI Bridge | Snapshot WebSocket Broadcast | Broadcasts ZMQ agent events to connected WebSockets under send lock | Inbound ZMQ `STATE_UPDATE`, `TASK_COMPLETED`, `SOVEREIGN_OVERRIDE`, `AGENT_ALIVE` | JSON text frame over WebSocket | Catches `Exception`, logs warning, purges disconnected sockets | `services/ui_bridge.py:111` |
| 6 | UI Bridge | Clerk JWT WebSocket Auth | Authenticates UI client via Clerk token before accepting commands | JSON message `{"clerk_token": "<jwt>"}` | JSON `{"type": "auth", "status": "success"}` | Rejection with `{"type": "auth", "status": "failed"}` and socket closure | `services/ui_bridge.py:50,158` |
| 7 | UI Bridge | Uninitialized Bus Guard | Protects against forwarding user commands before bus connection is active | Inbound UI text payload | Sends `USER_COMMAND` event to bus | Logs error `"Cannot forward user command: bus_client is not initialized"` without crashing | `services/ui_bridge.py:181` |
| 8 | Agents | Emergency Token Stash | In-memory token storage in `MatrixAgent` base with TTL and bounded capacity | `KEY_INJECT` event payload with `scope` and `token` | Stashed token dictionary with expiry timestamp | Drops invalid tokens; purges expired; evicts oldest when stash exceeds `MAX_STASH_SIZE=2` | `agents/base_agent.py:33,62` |
| 9 | Crawlers | AssistantCrawler (The Distributor) | Intercepts `TOKEN_EXTRACTED` events and broadcasts `KEY_INJECT` | `TOKEN_EXTRACTED` event from Neo/Trinity | `KEY_INJECT` event broadcast to bus | Validates token string, masks token in logs as `***{last4}` | `services/assistant_crawler.py:10` |
| 10 | Security | Aegis Topology Validator | Pre-commit static AST validator enforcing constitutional rules | Python files (`agents/base_agent.py`, `services/assistant_crawler.py`) | Exit code 0 if valid, prints violation message and exit 1 | Blocks commit if `emergency_token_stash` or `assistant_crawler.py` is missing | `core/aegis_validator.py:6` |
| 11 | Security | Deterministic Guillotine | Regex and AST filter rejecting dangerous dynamic execution | Arbitrary code/action string | `True` (allowed) or `False` (severed) | Detects `pickle`, `eval`, `exec`, `os.system`, `subprocess.Popen`, dynamic attribute access | `agents/aegis_qa.py:9` |
| 12 | Agent Tooling | Safe Local Shell Execution | Subprocess execution using argv list, dynamic workspace root, and length limits | Command string (max 8192 chars) | Formatted string `STDOUT:\n...\nSTDERR:\n...` | Returns error message on empty command, >8192 chars, or subprocess exception | `agents/neo_agent.py:204` |
| 13 | Agent Tooling | Dynamic Workspace Resolution | Resolves workspace path dynamically across Linux and Windows | `MATRIX_ROOT` env var or `Path.cwd()` | Absolute resolved `Path` | Falls back to current working directory if env var unset | `agents/neo_agent.py:201` |
| 14 | Key Routing | APIKeyRouter Round-Robin | Rotates available Gemini API keys from environment configuration | `.env` variables (`GEMINI_API_KEY`, `GEMINI_BACKUP_KEY_*`) | Active API key string or `None` | Returns `None` if no valid keys found; handles exhaustion gracefully | `core/key_router.py:15` |
| 15 | Crawlers | Async LibrarianCrawler | Asynchronous skill file scanner with path-traversal prevention | `target_dir` Path, Markdown files | JSON schema mapping skills and previews | Drops and logs `SECURITY BREACH ATTEMPT: Path traversal detected` if path outside target | `core/librarian_crawler.py:19` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `NeuralBusClient` HMAC Auth | Tampered payload or wrong `SOVEREIGN_BUS_SECRET` | Rejects message with `ZMQ SPOOFING DETECTED! Invalid signature. Dropping message.` without dispatching. |
| 2 | `NeuralBusClient` Replay Protection | Duplicate nonce submitted within 5 seconds | Rejects message with `REPLAY ATTACK DETECTED! Nonce ... already processed.` and drops message. |
| 3 | `NeuralBusClient` Replay Window Expiry | Nonce submitted after 5 seconds | Nonce is purged from `seen_nonces`; message rejected by TTL check if timestamp is old. |
| 4 | `NeuralBusClient` Message TTL | Message timestamp older than 60.0s | Rejects message with `Message TTL expired. Dropping message.` |
| 5 | `NeuralBusRouter` Client Disconnect | DEALER abruptly terminates during broadcast | Router catches `zmq.ZMQError` (EAGAIN / unreachable), logs info, and purges client from `active_clients`. |
| 6 | `NeuralBusRouter` Registration Frame | Inbound frame with signature `b"REGISTER"` | Router adds sender identity to `active_clients` and skips broadcast loop. |
| 7 | `services/ui_bridge.py` WebSocket Broadcast | Client disconnects while broadcast loop is executing | Loop iterates over `list(active_connections)` snapshot under lock; handles disconnect exception cleanly. |
| 8 | `services/ui_bridge.py` Early User Command | User sends text message via WebSocket before `bus_client` is connected | Checks `if bus_client is not None:`; logs error `"bus_client is not initialized"` without raising unhandled exception. |
| 9 | `agents/base_agent.py` Stash Overflow | More than 2 keys injected via `KEY_INJECT` | Calculates oldest token timestamp, purges oldest entry, and inserts newest token (`MAX_STASH_SIZE=2` maintained). |
| 10 | `agents/base_agent.py` Token Expiry | Token in emergency stash exceeds 300 seconds TTL | `_clean_stash()` purges token on next stash access. |
| 11 | `agents/neo_agent.py` Command Injection | Malicious command string `ls; rm -rf /` or `ls && whoami` | Parsed safely via `shlex.split(posix=...)`; arguments executed via `subprocess.run(shell=False)` as literal args. |
| 12 | `agents/neo_agent.py` Oversized Command | Command string exceeding 8192 characters | Rejected immediately with `"ERROR: command too long"`. |
| 13 | `core/librarian_crawler.py` Path Traversal | File path containing `../../etc/passwd` | Checked via `resolved_path.is_relative_to(self.target_dir)`; returns `None` and logs security warning. |
| 14 | Windows Event Loop Policy | System platform is `win32` | `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` set; prevents Proactor loop ZMQ crash. |
