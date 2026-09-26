# PROJECT ARCHITECTURE BENCHMARK & SOVEREIGN TRUTH AUDIT

**System**: Sovereign Matrix Autonomous Agent Operating System (Matrix OS)  
**Workspace**: `/mnt/e/matrex-dev` (Linux/WSL2)  
**Covenant Sources**: `SOVEREIGN_CONSTITUTION.md`, `PRODUCT_VISION.md` (`/mnt/k/THE-MATRIX-V2/00-covenant/PRODUCT_VISION.md`), `workspace.manifest.json`  
**Auditor**: Supreme Architecture & Truth Auditor (`supreme_auditor_1`, Oracle/Ghost Research Agent)  
**Audit Timestamp**: 2026-09-24T16:02:00Z  
**Operating Environment**: Linux 6.6.x (WSL2), Python 3.14.7, Node.js v24.19.0, Ollama v0.34.2 (`llama3.2:3b` on `127.0.0.1:11434`)  
**Audit Status**: **OFFICIAL BENCHMARK ESTABLISHED — INTEGRITY GATES DEFINED**

---

## 1. Executive Summary & Audit Mandate

As the dedicated Oracle/Ghost Supreme Architecture & Truth Auditor, this benchmark provides an uncompromised, empirical audit of the entire Sovereign Matrix codebase against the Sovereign Covenant (`PRODUCT_VISION.md`, `SOVEREIGN_CONSTITUTION.md`, `workspace.manifest.json`, and authoritative user requirements R1–R4).

### The Sovereign Standard
1. **Zero Mocks**: Every test, execution path, and agent capability must interact with real physical processes, real sockets, and real local neural inference models. Mocks, stubs, fake servers, `MagicMock`, and synthetic responses are strictly prohibited.
2. **Constitutional Invariance**: The master-slave topology (Blind Extractors → Distributor → Stash <= 2), zero-trust HMAC-SHA256 signing, anti-replay nonces, and `WindowsSelectorEventLoopPolicy` are non-negotiable.
3. **Genuine End-to-End Execution**: Requirements R1 (Synchronous CLI), R2 (Zero Cold Start Latency), R3 (Real MCP Gateway Activation), and R4 (Web Stack Synchronization) must be physically proven with live metrics.

---

## 2. Sovereign Covenant Cross-Reference & Baseline Architecture

### 2.1 Identity & Architectural Intent (`PRODUCT_VISION.md`)
Cross-referencing against `/mnt/k/THE-MATRIX-V2/00-covenant/PRODUCT_VISION.md`:
- **Core Identity**: `Matrix OS = Commander Intent + Neo + Ghost + Agent Council + Execution + Sovereignty + Memory + Interface`.
- **Supreme Authority**: The Commander (Dr. Anas Hilal) holds absolute authority. Agents possess zero authority on architectural boundaries.
- **Agent Council**:
  - `Neo`: Personal Commander Assistant, Mission Router, and Primary Execution Lead.
  - `Ghost`: Context Observer, Memory Keeper, and Feedback/Awareness layer (non-executive).
  - `Council`: `Oracle` (Knowledge/Synthesis), `Morpheus` (Architecture/Review), `Smith` (Defensive Security/Enforcement), `Trinity` (Legal/Key Extraction).
- **Two-Tier Memory Covenant**:
  1. *Cognitive Layer (RAG)*: `matrix-knowledge.db` (494 chunks, vectors + FTS5 hybrid search <100ms) accessed via `$OPENCODE_KNOWLEDGE_DB`.
  2. *Operational Layer*: `matrix_memory.db` (6 tables: sessions, projects, preferences, skills, failures, audit) managed via `30-runtime/memory_store.py`.
- **Secret Governance**: Zero explicit credentials in code or repository files. All secrets are accessed strictly via `*_REF` environment references and injected through secure channels.

### 2.2 Constitutional Invariants (`SOVEREIGN_CONSTITUTION.md`)
Cross-referencing against `/mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md`:
1. **The Blind Extractors**: Neo and Trinity extract keys from external boundaries and broadcast `EventType.TOKEN_EXTRACTED`. They are strictly forbidden from storing keys in persistent memory.
2. **The Assistant Crawler (The Distributor)**: `AssistantCrawler` is the sole authorized entity listening to `TOKEN_EXTRACTED`. It validates tokens, masks credentials as `***{last4}`, stores them in `AuthVault`, and broadcasts `EventType.KEY_INJECT`.
3. **Emergency Token Stash**: `MatrixAgent` base class maintains `self.emergency_token_stash` (`MAX_STASH_SIZE = 2`, `TTL = 300s`). Agents are strictly forbidden from JIT-requesting keys directly; they must wait for `KEY_INJECT`.
4. **Zero-Trust Neural Bus**: All ZMQ messages must be HMAC-SHA256 signed using `SOVEREIGN_BUS_SECRET`. Nonces are tracked with a 5-second replay window; messages exceeding 60s TTL are dropped.
5. **Windows Event Loop Invariant**: On Windows (`win32`), `WindowsSelectorEventLoopPolicy` is required. The Proactor event loop is strictly forbidden due to ZMQ socket incompatibilities.
6. **Absolute Subprocess Isolation**: `shell=True` is prohibited repository-wide. All commands must execute via argv lists under strict allowlists.

---

## 3. Comprehensive Codebase Forensic Audit

### 3.1 Forensic Finding: Residual Mocks, Fakes, and Stubs
An exhaustive scan across `/mnt/e/matrex-dev` revealed multiple residual mocks and stubs that violate the Zero-Mock Sovereign Command:

| File Location | Line(s) | Violation Description | Severity | Mandated Remediation |
|---|---|---|---|---|
| `core/matrix_vision.py` | 10–20, 33 | `class MockPyAutoGUI` fallback and hardcoded return `{"text": "[Mocked Vision]"}` | **CRITICAL** | Remove mock class and placeholder string; handle missing dependencies via clean error reporting. |
| `core/zmq_hooks.py` | 64–66 | Returns dummy response `{"status": "success", "data": "Skill {skill} executed successfully under sovereign constraints."}` for non-allowlisted skills | **HIGH** | Replace dummy success message with explicit rejection or error when a skill is unknown. |
| `tests/fake_mcp_stdio_server.py` | 1–75 | Complete mock MCP server script (`fake-mcp-server`) returning dummy tool `fixture_echo` | **CRITICAL** | Eliminate entirely. Replace with live subprocess execution of real project MCP servers (`shell`, `syncfusion`). |
| `tests/test_mcp_gateway.py` | 28, 31–50 | Points fixture to `fake_mcp_stdio_server.py` and implements `InMemoryMCPServer` / `MockSovereigntyGate` | **CRITICAL** | Refactor tests to run against real MCP servers (`/mnt/k/mcp/shell/server.js`, `/mnt/k/mcp/syncfusion/server.js`). |
| `tests/test_ollama_client.py` | 17, 39–95 | `MockTransport` simulating HTTP responses, `unittest.mock.MagicMock`, `patch` | **HIGH** | Separate offline unit tests from integration tests; ensure all integration verification runs against live Ollama daemon. |
| `tests/test_safe_shell.py` | 10, 70, 93, 148, 238, 323, 383 | Uses `unittest.mock.patch("subprocess.run")` instead of executing real safe commands | **HIGH** | Test safe shell against real subprocesses (`python3 -m pytest --version`, `git status`). |
| `tests/test_neo_ollama.py` | 24–53, 59 | Uses `TransportEndpoint` mock returning hardcoded string and mutates `_default_router` global singleton | **HIGH** | Test Neo integration against live Ollama model or reset global router singleton in fixture cleanup. |
| `auth_vault.py` | 42 | Warning: `"No Master Key provided! Operating in highly insecure mock mode."` | **MEDIUM** | Enforce explicit secret key handling or throw configuration error instead of silent insecure mock mode. |

### 3.2 Forensic Finding: Constitutional Deviations
1. **Violation of JIT Key Request Ban (`agents/base_agent.py:99–130`)**:
   - `base_agent.py` contains `async def execute_tool(self, tool_name: str, kwargs: dict[str, Any]) -> str`.
   - Lines 117–118: `payload = f"REQUEST_TOKEN:{tool_name}".encode()`; `await socket.send_multipart([payload])`.
   - **Constitutional Conflict**: The Sovereign Constitution Law 3 states: *"Agents MUST NOT use JIT provisioning to request keys directly; they must wait for KEY_INJECT."* Direct requests to port 5557 violate the Blind Extractor topology.
2. **Hardcoded Windows Path Portability Defects**:
   - `matrix_main.py:43`: `failsafe = FailsafeMonitor(matrix_root=r"J:\THE_MATRIX")`
   - `create_keys_secure.py:73`: `open(r"J:\THE_MATRIX\.env", ...)`
   - `tests/test_auth_vault.py:3`: `sys.path.append(r"J:\THE_MATRIX")`
   - `tests/test_neo_authority.py:5`: `sys.path.append(r"J:\THE_MATRIX")`
   - `tests/test_memory_manager.py:3`: `sys.path.append(r"J:\THE_MATRIX")`
   - `tests/test_message_serialization.py:4`: `sys.path.append(r"J:\THE_MATRIX")`
   - `inject_memory.py:9`: Hardcoded `J:\THE_MATRIX` context string.
   - **Remediation**: All path references must dynamically resolve via `os.getenv("MATRIX_ROOT", Path.cwd())`.

### 3.3 Forensic Finding: Test Suite State Pollution & Live Test Failure
- Running the full test suite (`python -m pytest -q --no-cov`) produced:
  `1 failed, 132 passed in 45.61s`
- Failure: `tests/test_ollama_live.py::test_ollama_live_probe_and_chat - assert 1 == 0`.
- **Root Cause Analysis**:
  1. `services/ollama_client.py:591-599` maintains a global mutable singleton `_default_router`.
  2. `tests/test_neo_ollama.py:59` mutates this singleton via `get_router(client=client, reset=True)` using a mock transport.
  3. When `tests/test_ollama_live.py` executes later in the same pytest process, `probe()` calls `get_router()` without `reset=True`, inheriting the stale mock router and failing.
  4. In isolation, `test_ollama_live.py` skips because `_discover_windows_host_ip()` attempts `/etc/resolv.conf` (`10.255.255.254:11434`, Connection Refused), ignoring the fact that Ollama is actively running on `127.0.0.1:11434`.

---

## 4. Requirement Benchmarks & Empirical Proofs

### 4.1 Requirement R1: Synchronous CLI Interaction & Bus Bidirectional Bridge
- **Requirement**: Upgrade `send_command.py` into a robust synchronous CLI client. It must transmit commands to the Neural Bus and synchronously await, parse, and stream the agent's textual and tool execution responses to the user's terminal with zero silent drops.
- **Empirical Findings**:
  - `send_command.py:38-39` currently executes `await asyncio.sleep(0.5)` and exits immediately (`await client.stop()`). No handler is registered on `NeuralBusClient`.
  - In `core/neural_bus.py:127-129`, unhandled events are discarded.
  - Agents (`base_agent.py:428`, `neo_agent.py:667`) only emit `EventType.STATE_UPDATE` and never emit `EventType.TASK_COMPLETED`.
  - In `agents/base_agent.py:271`, thinking messages emit `source_agent_id=self.agent_id` (UUID), preventing UI and CLI from matching status to agent name.
  - In `services/ui_bridge.py:113-117`, failed WebSocket sends log errors but do not remove closed connections from `active_connections`.
- **Acceptance Criteria & Benchmark Invariants**:
  - [ ] `send_command.py` registers unique correlation ID queue and listens for `STATE_UPDATE`, `TASK_COMPLETED`, and `ERROR`.
  - [ ] `send_command.py` streams intermediate thoughts (`status_action`) and final text response to stdout in real time.
  - [ ] Agents emit explicit `TASK_COMPLETED` with final text message upon finishing.
  - [ ] `services/ui_bridge.py` removes dead connections from `active_connections` immediately upon failure under `send_lock`.

### 4.2 Requirement R2: Engine Latency & Pre-Warming (Zero Cold Start)
- **Requirement**: Eliminate the ~30s initial inference delay by introducing an asynchronous model pre-warming pulse at engine boot. Ensure `matrix_main.py` and `base_agent.py` never block the asyncio loop during Ollama tensor evaluation.
- **Empirical Measurement**:
  - Cold model load time on local Ollama (`llama3.2:3b`): **21.8 seconds**.
  - Warm inference time on local Ollama (`llama3.2:3b`): **0.76 seconds**.
  - Verified pre-warming endpoint: `POST http://127.0.0.1:11434/api/chat` with `{"model": "llama3.2:3b", "messages": [], "stream": false}` returns HTTP 200 with `done_reason: 'load'` in **0.091 seconds**.
- **Empirical Bottlenecks in Current Code**:
  - `matrix_main.py` contains no model pre-warming call.
  - `services/ollama_client.py:566` runs `self.get_endpoint(agent)` synchronously on the event loop, executing uncached HTTP calls to `/api/tags`.
  - `core/intent_parser.py:142-156` attempts an invalid import (`OllamaRouter` instead of `ModelRouter`) and invokes async methods synchronously.
  - `core/decision_log.py:86` executes synchronous SQLite database writes directly on the event loop thread.
- **Acceptance Criteria & Benchmark Invariants**:
  - [ ] `matrix_main.py:boot_matrix()` triggers an async pre-warming pulse (`prewarm()`) as an unawaited task on boot.
  - [ ] `ModelRouter.get_endpoint()` caches tag queries (60s TTL) and executes resolving logic via `asyncio.to_thread`.
  - [ ] Tensor evaluation and HTTP network requests in `OllamaClient` run strictly via `asyncio.to_thread` or non-blocking async HTTP.
  - [ ] Engine boots with zero unhandled exceptions and achieves warm round-trip inference under 5 seconds (empirically proven < 1.0s).

### 4.3 Requirement R3: Project MCP Gateway & Workspace Manifest Activation
- **Requirement**: Activate `workspace.manifest.json` inside `services/mcp_gateway.py` so agents can dynamically discover and invoke the 4 project MCP tools (`matrix_shell`, `chrome_devtools`, `syncfusion`, `github`). OpenCode (Team B) verifies MCP protocol compliance.
- **Physical Verification of MCP Servers**:
  - All 4 servers physically exist and execute cleanly over stdio JSON-RPC 2.0 (protocol version `2024-11-05`):
    1. **`shell`** (`/mnt/k/mcp/shell/server.js`): Discovered tool `run_shell_command`. Real call `python3 --version` returned `Python 3.14.7`.
    2. **`syncfusion`** (`/mnt/k/mcp/syncfusion/server.js`): Discovered tool `generate_react_datagrid`. Real call `{"componentName": "OrdersGrid"}` returned valid React component.
    3. **`chrome_devtools`** (`/mnt/k/mcp/chrome-devtools/.../chrome-devtools-mcp.js`): Discovered 29 browser tools (`navigate_page`, `click`, `take_screenshot`).
    4. **`github`** (`/home/AH/.local/bin/github-mcp-server stdio`): Discovered 45 repository tools (`list_issues`, `create_pull_request`).
- **Defects in Current Gateway**:
  - `workspace.manifest.json` specifies Windows paths (`C:\Program Files\...`, `C:\Windows\System32\...`), causing `from_manifest()` to fail on Linux.
  - `services/mcp_gateway.py:488` strictly requires names `{"github", "chrome_devtools", "syncfusion", "shell"}` and rejects `matrix_shell`.
  - `services/mcp_gateway.py:506-509` strictly rejects non-secret environment variables like `NODE_PATH` and `SHELL_CWD` because they do not end with `_REF`.
  - Agents (`base_agent.py`, `neo_agent.py`) have hardcoded tool definitions and do not integrate `MCPGateway`.
- **Acceptance Criteria & Benchmark Invariants**:
  - [ ] `services/mcp_gateway.py:from_manifest()` normalizes commands across platforms (WSL/Linux node & bash vs Windows node.exe & powershell.exe).
  - [ ] Aliases `matrix_shell` to `shell`.
  - [ ] Permits literal configuration strings in `environment` while resolving `*_REF` keys against `os.environ`.
  - [ ] Exposes `get_mcp_gateway()` and wires discovered tools into `NeoAgent` / `MatrixAgent` LLM chat schema.
  - [ ] Completely replaces `tests/fake_mcp_stdio_server.py` with real tests invoking `/mnt/k/mcp/shell/server.js` or `/mnt/k/mcp/syncfusion/server.js`.

### 4.4 Requirement R4: Complete Web Stack Synchronization
- **Requirement**: Ensure `matrix_main.py` (Engine :5555), `services/ui_bridge.py` (FastAPI/WS :8000), and `dashboard/` (Vite :5173) can boot and synchronize seamlessly.
- **Empirical Findings**:
  - Port Allocation:
    - `:5555`: Zero-Trust Neural Bus (ZMQ ROUTER / DEALER)
    - `:8000`: FastAPI UI Bridge WebSocket (`/ws`) & REST API
    - `:5173`: React 19 / Vite Dashboard (proxies `/ws` and `/api` to `:8000`)
  - Sequence Hazard: `IGNITE_MATRIX.bat` starts Vite (5173) before UI Bridge (8000), before Engine (5555), causing frontend WebSocket `ECONNREFUSED` upon browser launch.
  - Missing REST API: `dashboard/vite.config.js` proxies `/api`, but `services/ui_bridge.py` has no REST endpoints, returning 404 for diagnostic health requests.
- **Acceptance Criteria & Benchmark Invariants**:
  - [ ] Boot sequence enforced: Engine (:5555) → UI Bridge (:8000) → Dashboard (:5173).
  - [ ] `services/ui_bridge.py` provides `@app.get("/api/health")` returning status of UI Bridge and Neural Bus connection.
  - [ ] WebSocket broadcast uses snapshot iteration (`list(active_connections)`) under `send_lock` and purges disconnected sockets on error.

---

## 5. Architectural Truth Matrix & Acceptance Criteria

| # | Subsystem / Requirement | Target Standard | Current Repository Status | Gate Classification | Mandated Remediation |
|---|---|---|---|---|---|
| **1** | Production Code Mocks | Zero mocks in `services/`, `agents/`, `core/` | **VIOLATION**: `core/matrix_vision.py` has `MockPyAutoGUI` & `[Mocked Vision]`; `core/zmq_hooks.py` returns dummy string | **FAIL** | Delete all mock classes and fake return strings from production code. |
| **2** | Test Infrastructure Mocks | Zero fake test servers or stubs | **VIOLATION**: `tests/fake_mcp_stdio_server.py`, `InMemoryMCPServer`, and `MockTransport` present | **FAIL** | Replace mock servers with real MCP subprocesses (`/mnt/k/mcp/shell/server.js`). |
| **3** | Constitutional Key Topology | Blind Extractors → Distributor → Stash <= 2; Zero direct JIT requests | **VIOLATION**: `agents/base_agent.py:execute_tool` sends direct `REQUEST_TOKEN` over ZMQ | **FAIL** | Refactor `execute_tool` to use stashed tokens or execute through authorized channels without direct JIT key bypass. |
| **4** | Cross-Platform Portability | Zero hardcoded `J:\THE_MATRIX` paths | **VIOLATION**: Hardcoded in `matrix_main.py:43`, `create_keys_secure.py`, and 4 test files | **FAIL** | Replace all occurrences with `Path(os.getenv("MATRIX_ROOT", Path.cwd()))`. |
| **5** | Code Formatting & Linting | Ruff 0 errors, Black clean, Bandit 0 High/Medium | **VIOLATION**: Ruff reports 27 errors; Black reports 7 files needing reformat | **FAIL** | Run `ruff check --fix` and `black core agents services config tests matrix_main.py`. |
| **6** | R1: Synchronous CLI Client | Synchronously awaits and streams agent responses | **INCOMPLETE**: `send_command.py` sleeps 0.5s and terminates; no event handlers | **FAIL** | Implement response listener queue, correlation filtering, and real-time streaming in `send_command.py`. |
| **7** | R2: Engine Zero Cold Start | Model pre-warming pulse on boot; < 5s warm inference | **PARTIAL**: Warm inference is 0.76s, but engine does not pre-warm; loop blocked by `urllib` & SQLite | **CONDITIONAL** | Add boot prewarm pulse; wrap `urllib` and SQLite calls in `asyncio.to_thread`. |
| **8** | R3: MCP Manifest Activation | Dynamic discovery and execution of 4 project MCP tools | **INCOMPLETE**: Fails on Linux paths; rejects `matrix_shell`; test suite uses mock server | **FAIL** | Update `from_manifest()` with cross-platform normalization; wire into agent execution; test with live servers. |
| **9** | R4: Web Stack Sync | Ordered boot (:5555 → :8000 → :5173); `/api/health` available | **PARTIAL**: Ports configured, but startup sequence is inverted and `/api` routes missing | **CONDITIONAL** | Add `/api/health` in `ui_bridge.py`; enforce startup ordering in scripts. |

---

## 6. Official Auditor Certification & Verdict

**AUDIT VERDICT: INTEGRITY VIOLATION / CONDITIONAL HOLD**

The codebase contains substantial, high-quality engineering, and real physical infrastructure (Ollama `llama3.2:3b` responding in 0.76s; Node.js v24.19.0 executing real MCP servers for `shell`, `syncfusion`, `chrome_devtools`, and `github`). However, under the strict Sovereign Covenant:
1. **Residual Mocks Must Be Destroyed**: `core/matrix_vision.py` and `tests/fake_mcp_stdio_server.py` cannot be certified.
2. **Constitutional Invariants Must Be Restored**: Direct JIT key requests in `base_agent.py` and hardcoded `J:\THE_MATRIX` paths in `matrix_main.py` violate constitutional law.
3. **Requirements R1–R4 Must Be Fully Implemented**: CLI streaming, boot pre-warming, manifest cross-platform activation, and clean web stack synchronization must be deployed and verified without mocks.

This benchmark stands as the immutable ground-truth specification. No implementing agent may self-certify. Deliverables will be re-audited upon completion against this document.
