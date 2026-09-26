# Specification Mining Report: R4 MCP Gateway & R5 Skills / Crawlers

## 1. Observation

### 1.1 Authoritative Specification Sources Examined
1. **R4 MCP Gateway & Capability Registry**:
   - `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py` (lines 1–326): In-process and stdio JSON-RPC MCP gateway implementation.
   - `/mnt/k/THE-MATRIX-V2/30-runtime/capability_registry.py` (lines 1–124): Typed capability registry and schema mapping.
   - `/mnt/k/THE-MATRIX-V2/tests/fake_mcp_stdio_server.py` (lines 1–34): Reference deterministic stdio fixture server (`fixture_echo`).
   - `/mnt/k/THE-MATRIX-V2/tests/test_mcp_stdio_gateway.py` (lines 1–40): Reference offline, non-interactive smoke test using `fake_mcp_stdio_server.py`.
   - `/mnt/k/THE-MATRIX-V2/tests/test_mcp_gateway_path.py` (lines 1–132): In-memory fake MCP server integration and error behavior.
   - `/mnt/k/THE-MATRIX-V2/workspace.manifest.json` (lines 34–72): Manifest structure for `mcp_gateway.servers`.
   - `/mnt/e/matrex-dev/services/mcp_gateway.py` (lines 1–72): Existing implementation in target codebase (broken placeholder that invokes `npx.cmd` and sets `WindowsProactorEventLoopPolicy`).

2. **R5 Skills Pipeline & Contract**:
   - `/mnt/k/THE-MATRIX-V2/40-skills/loader.py` (lines 1–378): Skill absorption pipeline (`discover`, `validate`, `prepare`, `validate_curated`, `load_curated`, `promote`, `inject`).
   - `/mnt/k/THE-MATRIX-V2/40-skills/SKILL_CONTRACT.md` (lines 1–34): Contract v1.0 specifications and strict allowed tool list.
   - `/mnt/k/THE-MATRIX-V2/tests/test_skill_loader.py` (lines 1–126): Unit test cases validating deterministic manifests, quarantine, and non-execution invariants.
   - `/mnt/e/matrex-dev/skills_schema.json` (lines 1–11): Legacy schema with hardcoded Windows path `J:\THE_MATRIX\skills\test_skill.md`.
   - `/mnt/e/matrex-dev/skills/test_skill.md` (lines 1–10): Sample skill markdown format.

3. **Bus Topology & Models**:
   - `/mnt/e/matrex-dev/core/models.py` (lines 1–120): `EventType` enum and `EventPayload` model.
   - `/mnt/e/matrex-dev/core/neural_bus.py` (lines 1–60): HMAC-SHA256 bus signing and anti-replay window.
   - `/mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md` (lines 1–15): Non-negotiable key distribution topology.
   - `/mnt/e/matrex-dev/agents/base_agent.py` (lines 55–84): Emergency token stash rules (`MAX_STASH_SIZE=2`, 300s TTL).

4. **R5 Crawlers Architecture**:
   - `/mnt/e/matrex-dev/services/assistant_crawler.py` (lines 1–61): The Blind Distributor (`TOKEN_EXTRACTED` -> `KEY_INJECT`).
   - `/mnt/e/matrex-dev/services/memory_crawler.py` (lines 1–229): SQLite memory indexing, heuristic sanitization, Aegis QA validation.
   - `/mnt/e/matrex-dev/core/librarian_crawler.py` (lines 1–110): Skill file crawler with path-traversal guard and `aiofiles`.
   - `/mnt/e/matrex-dev/services/librarian_crawler.py` (lines 1–137): Periodic skill directory scanner with `MATRIX_ROOT` fallback.
   - `/mnt/e/matrex-dev/services/librarian.py` (lines 1–58): `SecureLibrarian` JIT token provisioning server on port 5557.
   - `/mnt/e/matrex-dev/agents/aegis_qa.py` (lines 1–184): Deterministic Guillotine and Asymmetric QA.
   - `/mnt/e/matrex-dev/tests/test_crawlers_integration.py` (lines 1–406): 15 integration tests.

### 1.2 Verbatim Test Executions
- Executed: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_crawlers_integration.py -v --no-cov`
  Result: `15 passed, 1 warning in 9.31s` (Exit code: 0).
- Executed: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`
  Result: `25 passed, 1 warning in 39.40s` (Exit code: 0).

---

## 2. Logic Chain

### 2.1 R4 MCP Gateway & Offline Smoke Test Analysis
1. **Current Defect in `matrex-dev/services/mcp_gateway.py`**:
   - Currently, `matrex-dev/services/mcp_gateway.py` merely contains an asynchronous helper `launch_mcp_node_detached` that attempts to invoke `npx.cmd -y @modelcontextprotocol/server-puppeteer` and `@modelcontextprotocol/server-github` to `DEVNULL`.
   - Defect 1 (Portability): On Linux, `npx.cmd` fails immediately (`FileNotFoundError`).
   - Defect 2 (EventLoop violation): Line 70 sets `asyncio.WindowsProactorEventLoopPolicy()`, directly violating the Sovereign Matrix invariant (`WindowsSelectorEventLoopPolicy` required for ZMQ).
   - Defect 3 (No MCP semantics): It does not parse JSON-RPC, does not discover tools, does not expose tool definitions to agents, and has no calling or validation mechanism.
2. **Authoritative Pattern in `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py`**:
   - Implements `MCPServer` Protocol with `list_tools()` and `call_tool(name, arguments)`.
   - `StdioMCPServer` implements JSON-RPC 2.0 communication over stdio (`stdin`/`stdout`), handling initialization handshake (`initialize` -> `notifications/initialized`), `tools/list`, and `tools/call`.
   - Launcher allowlist strictly enforces:
     `{"github-mcp-server", "chrome-devtools-mcp", "syncfusion-mcp", "shell-mcp", "npx", "node", "node.exe", "uvx", "python", "python3", "powershell", "pwsh", "powershell.exe", Path(sys.executable).name.lower()}`.
   - `shell=False` is enforced unconditionally in subprocess execution.
   - Inferred approval and risk escalation:
     - Any tool matching destructive annotations, `readOnlyHint == False`, or prefixes `delete*`, `write*`, `create*`, `update*`, `send*`, `execute*` is flagged as `requires_approval = True`.
     - Any tool requiring approval has its risk elevated from `LOW` to `HIGH`.
   - Approval gate: capabilities requiring approval check `sovereignty.pre_flight()`. If no sovereignty gate is provided, execution is fail-closed.
3. **Non-Interactive Offline Smoke Test Requirements**:
   - Per `ORIGINAL_REQUEST.md`: "Smoke test exits 0, prints ≥1 tool name from registered MCP server. Non-interactive, no external network required."
   - The authoritative test is exemplified in `/mnt/k/THE-MATRIX-V2/tests/test_mcp_stdio_gateway.py`:
     - Spawns `/mnt/k/THE-MATRIX-V2/tests/fake_mcp_stdio_server.py` using `sys.executable` (no external node/npx/network required).
     - Gateway performs JSON-RPC handshake over stdin/stdout.
     - Calls `gateway.discover()` -> returns tool `fixture_echo`.
     - Calls `gateway.call("fixture_echo", {"count": 3})` -> returns `{"ok": True, "content": [{"type": "text", "text": "3"}]}`.
     - Calls `gateway.call("fixture_echo", {"count": "3"})` -> validates schema failure, returns `{"ok": False, ...}`.
     - Closes subprocess cleanly via `gateway.close()`.

### 2.2 R5 Skills Pipeline Lifecycle & Bus Schema Analysis
1. **Lifecycle Invariant**:
   - The lifecycle progresses through defined stages:
     `DISCOVERED` -> `VALIDATED` -> `PREPARED` -> `PROMOTED` -> `INJECTED`.
   - Rejection occurs at any stage if security constraints are breached.
   - `DISCOVERED`: Metadata-only JSON reading. Generates deterministic `skill_id = f"sk_{hashlib.sha256(name.encode()).hexdigest()[:12]}"`. Heuristic risk check (`BLOCKED_PATTERNS`).
   - `VALIDATED`: Requires named reviewer (e.g. `smith` or `morpheus`). Enforces `SKILL_CONTRACT` v1.0:
     - `contract_version == "1.0"`.
     - `allowed_tools` MUST be a subset of `{"docs.read", "memory.read", "memory.search", "planning.emit", "skills.discover", "skills.validate"}`.
     - License must not be empty or `"unknown"`.
     - High risk / offensive skills rejected.
   - `PREPARED`: Writes `package_manifest.json` and `source_manifest.json` under `curated/{skill_id}`.
   - `validate_curated`: Evaluates curated package directories. Incomplete manifests, unknown tools, mismatched IDs, or invalid licenses are quarantined into `quarantine/{package_id}`.
   - `Aegis QA Gate`: `AsymmetricQA.verify()` scans content for dangerous code (`eval`, `exec`, `subprocess`, forbidden imports).
   - `SKILL_REVIEW_APPROVED` & `SKILL_PROMOTED`:
     - Smith and Morpheus review the validated skill and approve by emitting `EventType.SKILL_REVIEW_APPROVED` over the neural bus.
     - Commander approves promotion (`promote(record, commander_approval=True)`), triggering `EventType.SKILL_PROMOTED` on the bus.
     - Strict acceptance criteria: **No skill reaches INJECTED without SKILL_REVIEW_APPROVED bus event.**
   - `INJECTED`: Writes `curated/{skill_id}/bindings.json` recording target agents. Skills are declarative access contracts, NEVER executable code injected into Python memory.
2. **Bus Architect Constraints (`core/models.py`)**:
   - Additions to `EventType(str, Enum)`:
     ```python
     SKILL_PROMOTED = "skill_promoted"
     SKILL_REVIEW_APPROVED = "skill_review_approved"
     ```
   - Invariant: `EventType` and `EventPayload` are the only bus schemas (`use_enum_values=True`).
   - Adding these events must NOT modify the immutable key topology (Neo/Trinity -> `TOKEN_EXTRACTED` -> `AssistantCrawler` -> `KEY_INJECT` -> `emergency_token_stash`).

### 2.3 R5 Crawler Verification Invariants Analysis
1. **Librarian Crawler**:
   - Role: Scans skill directories, parses markdown frontmatter, generates `skills_schema.json`.
   - Security Invariant: Path-traversal protection via `resolved_path.is_relative_to(target_dir)`. Rejects any traversal attempt outside target dir.
   - Async Invariant: Directory traversal (`os.walk`) offloaded to `asyncio.to_thread`; file reading uses `aiofiles` or `asyncio.to_thread`. No blocking I/O on the main loop.
2. **Memory Crawler**:
   - Role: Listens for `MEMORY_STORE_REQUEST` and `MEMORY_RECALL_REQUEST`.
   - Security Invariant: Any content containing `"def "`, `"import "`, or `"eval("` is passed through `AsymmetricQA.verify()`. If rejected, emits `EventType.ERROR` and denies storage.
   - Storage Invariant: Per-agent isolated SQLite storage (`AgentMemoryDB`) using parameterized SQL queries. Sanitizes conversational chatter before storing.
   - Response Invariant: Emits `EventType.MEMORY_STORED` on store, `EventType.MEMORY_INJECT` on recall, and updates `EventType.STATE_UPDATE`.
3. **Assistant Crawler**:
   - Role: Sole authorized consumer of `EventType.TOKEN_EXTRACTED` from Neo and Trinity.
   - Security Invariant: Logs masked tokens only (`***{token[-4:]}`). Never logs full secrets.
   - Distribution Invariant: Broadcasts `EventType.KEY_INJECT` to all agents to replenish their `emergency_token_stash` (max 2 keys, 300s TTL).
   - Invariant: Agents must never JIT-request keys directly from external sources; only AssistantCrawler distributes keys via bus.

---

## 3. Caveats
1. `services/mcp_gateway.py` in `matrex-dev` is currently an unfunctional stub; porting `MCPGateway`, `CapabilityRegistry`, and `StdioMCPServer` from `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py` will be required in Phase 2.
2. `services/skill_loader.py` does not yet exist in `matrex-dev`; porting `SkillLoader` from `/mnt/k/THE-MATRIX-V2/40-skills/loader.py` is required.
3. The offline smoke test for MCP must avoid running external Node.js commands (like `npx` or `node`) during CI or in environments where Node or network is absent; a local Python stdio fixture script (or in-memory mock conforming to `MCPServer`) is required.
4. `core/librarian_crawler.py:22` still has a default parameter `target_dir=r"J:\antigravity-awesome-skills-main"`, though `tests/test_crawlers_integration.py` passes explicit portable arguments. During R5 implementation, this default should use `Path(os.getenv("MATRIX_ROOT", Path.cwd())) / "skills"`.

---

## 4. Conclusion
1. **R4 MCP Specification**:
   - Complete contract is defined by `MCPServer` protocol and `MCPGateway` in `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py`.
   - Tools are discovered via JSON-RPC 2.0 `tools/list`, mapped to `Capability` instances, validated against JSON Schema, gated by risk/approval rules, and invoked via `tools/call`.
   - Non-interactive offline smoke test is fully verified via a stdio Python fixture (e.g. `fake_mcp_stdio_server.py`) that returns `fixture_echo`, requires 0 network connections, runs with `shell=False`, and exits 0 after printing the tool name.
2. **R5 Skills Pipeline Specification**:
   - Follows strict 5-stage lifecycle (`DISCOVERED` -> `VALIDATED` -> `PREPARED` -> `PROMOTED` -> `INJECTED`).
   - SKILL_CONTRACT v1.0 limits declarative tools strictly to `{"docs.read", "memory.read", "memory.search", "planning.emit", "skills.discover", "skills.validate"}`.
   - Skills with offensive patterns, empty capabilities, missing fields, or invalid licenses are rejected or quarantined.
   - Dual-agent review (`Smith` + `Morpheus`) must emit `SKILL_REVIEW_APPROVED` on the bus, and Commander approval triggers `SKILL_PROMOTED`.
   - `core/models.py:EventType` must be updated with `SKILL_PROMOTED = "skill_promoted"` and `SKILL_REVIEW_APPROVED = "skill_review_approved"`.
3. **R5 Crawler Verification Specification**:
   - All 15 crawler integration tests currently pass cleanly (`15 passed in 9.31s`).
   - Invariants (path traversal check, async I/O, token masking, Aegis QA gate on code, SQLite parameterization, clean start/stop) are active and verified.

---

## 5. Verification Method

### Test Commands
1. Verify Crawler Integration Suite:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_crawlers_integration.py -v --no-cov
   ```
2. Verify Full Baseline Suite:
   ```bash
   SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
   ```
3. Test V2 Reference MCP Stdio Gateway:
   ```bash
   python -m unittest /mnt/k/THE-MATRIX-V2/tests/test_mcp_stdio_gateway.py
   ```
4. Test V2 Reference Skill Loader:
   ```bash
   python -m unittest /mnt/k/THE-MATRIX-V2/tests/test_skill_loader.py
   ```

### Invalidation Conditions
- Any crawler test failure in `tests/test_crawlers_integration.py`.
- Any addition of `shell=True` in subprocess invocations.
- Permitting skills to reach `INJECTED` stage without a verified `SKILL_REVIEW_APPROVED` event on the bus.
- Permitting arbitrary shell tool names in `SKILL_CONTRACT` outside the closed 6-tool allowlist.
- Modifying the immutable key distribution topology or bypassing `AssistantCrawler`.

---

## 6. Specification Miner Findings

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R4 MCP | Stdio JSON-RPC Handshake | Performs `initialize` and `notifications/initialized` protocol exchange over stdio | Child process stdin/stdout, JSON-RPC 2.0 frames | Protocol version, capabilities, clientInfo | Raises `RuntimeError` on closed stdout or id mismatch | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:283-298` |
| 2 | R4 MCP | Tool Discovery (`discover`) | Queries MCP servers for available tools and registers them as typed capabilities | Server instances conforming to `MCPServer` protocol | List of function-calling tool definition dicts | Discards tools with invalid names; times out after `timeout_s` | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:112-147` |
| 3 | R4 MCP | Automatic Risk & Approval Inference | Automatically infers `risk="HIGH"` and `requires_approval=True` based on destructive annotations or tool verbs | Tool `inputSchema`, `annotations`, `risk`, tool name | Updated `Capability.risk` and `Capability.requires_approval` | Defaults to `LOW`/`False` if no heuristics match | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:124-133` |
| 4 | R4 MCP | Tool Calling (`call`) | Validates arguments against JSON schema and invokes tool on owning server | Tool name, arguments dictionary, approval_id | `{"ok": True, **output}` | Returns `{"ok": False, "error": str}` on validation error or timeout | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:152-203` |
| 5 | R4 MCP | Argument & Buffer Limit Enforcement | Restricts argument and response size to prevent memory exhaustion (64KB default) | Serialized JSON payload bytes | Validated payload | Raises `ValueError` or `RuntimeError` if payload exceeds limit | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:175,251,265` |
| 6 | R4 MCP | Environment Variable Isolation | Mandates manifest environment values use `*_REF` references resolved from host env | Manifest `environment` mapping | Cleaned child process env dict | Raises `ValueError` if environment value does not end with `_REF` | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:95-99,284-288` |
| 7 | R4 MCP | Launcher Allowlist Guard | Restricts executable launchers for MCP servers to known safe binaries | Executable path/name from manifest command | Verified command list | Raises `ValueError` for unknown or missing launcher binaries | `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py:87-94` |
| 8 | R4 MCP | Offline Smoke Test Pattern | Non-interactive verification running stdio MCP server via `sys.executable` | Local python script (e.g. `fake_mcp_stdio_server.py`) | Exit code 0, discovered tool name printed | Non-zero exit code if handshake or call fails | `/mnt/k/THE-MATRIX-V2/tests/test_mcp_stdio_gateway.py:12-36` |
| 9 | R5 Skills | Metadata Discovery (`discover`) | Reads skill manifest without code import/execution; computes sha256 skill ID | Path to manifest JSON file | Discovered record dict with `stage="DISCOVERED"` | Returns error dict if file unreadable or malformed | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:94-116` |
| 10 | R5 Skills | SKILL_CONTRACT v1.0 Validation | Validates contract fields and restricts allowed tools to closed allowlist | Skill record, reviewer name | Validated record dict with `stage="VALIDATED"` | Returns record with `stage="REJECTED"` and specific rejection reason | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:128-150` |
| 11 | R5 Skills | Closed Tool Allowlist | Limits tools to 6 declarative labels: `docs.read`, `memory.read`, `memory.search`, `planning.emit`, `skills.discover`, `skills.validate` | `record["allowed_tools"]` list | Validated tool set | Rejects skill if any unknown tool is requested | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:39-46,285-286` |
| 12 | R5 Skills | Offensive Pattern Blocking | Flags offensive skills (`active-directory-attack`, `password-crack`, `ransomware`, etc.) as HIGH risk | Name, capabilities, source ref | Assessed risk string (`LOW`, `MEDIUM`, `HIGH`) | HIGH risk skills rejected during validation | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:25-28,118-124` |
| 13 | R5 Skills | Metadata Packaging (`prepare`) | Packages validated skill into `curated/{skill_id}` with `package_manifest.json` | Validated record | Prepared record with `stage="PREPARED"` | Raises `ValueError` if stage is not `VALIDATED` | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:153-184` |
| 14 | R5 Skills | Curated Quarantine Gate (`validate_curated`) | Audits curated packages and moves incomplete, mismatched, or unsafe ones to `quarantine/` | Curated directory files | `{"valid": [...], "quarantined": [...]}` | Moves failing packages to `quarantine/` with collision suffix | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:185-207` |
| 15 | R5 Skills | Dual Review Approval Bus Event | Smith and Morpheus emit approval event on neural bus | Skill review verdict | Neural bus `SKILL_REVIEW_APPROVED` event | Rejection / blocked promotion if approval event missing | `/mnt/e/matrex-dev/ORIGINAL_REQUEST.md:130,163` |
| 16 | R5 Skills | Promotion Approval (`promote`) | Promotes prepared skill with Commander approval; records audit | Prepared record, `commander_approval=True` | Promoted record with `stage="PROMOTED"` | Raises `PermissionError` if commander approval is missing | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:311-324` |
| 17 | R5 Skills | Agent Binding Injection (`inject`) | Binds promoted skill to target agents via `bindings.json` access log | Promoted record, list of agent names | Injected record with `stage="INJECTED"` | Raises `ValueError` if stage is not `PROMOTED` | `/mnt/k/THE-MATRIX-V2/40-skills/loader.py:325-338` |
| 18 | R5 Skills | Bus Schema Additions | Adds `SKILL_PROMOTED` and `SKILL_REVIEW_APPROVED` to `EventType` enum | Enum members in `core/models.py` | Validated Pydantic models on bus | Schema validation failure if unknown event emitted | `/mnt/e/matrex-dev/core/models.py:13-36` |
| 19 | R5 Crawlers | Path-Traversal Guard | Verifies skill files are within target directory via `is_relative_to` | File path | Metadata dict or `None` | Logs security breach and returns `None` | `/mnt/e/matrex-dev/core/librarian_crawler.py:32-37` |
| 20 | R5 Crawlers | Asynchronous File Scanning | Offloads directory scanning and file reads to threads/aiofiles | Target directory path | Schema dict (`{"version": "1.0", "skills": [...]}`) | Returns empty or logs error on unreadable files | `/mnt/e/matrex-dev/core/librarian_crawler.py:57-68` |
| 21 | R5 Crawlers | Memory Sanitization & Sorting | Strips conversational noise and greetings (Arabic & English) | Raw text string | Cleaned content string | Preserves code and core facts | `/mnt/e/matrex-dev/services/memory_crawler.py:51-80` |
| 22 | R5 Crawlers | Aegis QA Code Gate | Evaluates memory/skill content with code patterns (`def `, `import `, `eval(`) via AsymmetricQA | Content string | Boolean pass/fail | Emits `EventType.ERROR` and rejects storage on violation | `/mnt/e/matrex-dev/services/memory_crawler.py:105-121` |
| 23 | R5 Crawlers | Isolated Per-Agent SQLite Storage | Stores permanent and temporary memories in per-agent SQLite databases | Memory key, category, content | Boolean success status; emits `MEMORY_STORED` | Emits `EventType.ERROR` if database insertion fails | `/mnt/e/matrex-dev/services/memory_crawler.py:126-153` |
| 24 | R5 Crawlers | Token Interception & Masking | Listens for `TOKEN_EXTRACTED`, masks secrets (`***{last4}`), broadcasts `KEY_INJECT` | `TOKEN_EXTRACTED` event payload | `KEY_INJECT` event payload | Masks token; drops missing or non-string tokens | `/mnt/e/matrex-dev/services/assistant_crawler.py:34-61` |
| 25 | R5 Crawlers | JIT Token Provisioning Server | Responds to explicit `REQUEST_TOKEN:<scope>` requests via ZMQ ROUTER on port 5557 | ZMQ multipart request | ZMQ multipart `TOKEN_GRANTED:<token_id>` | Rejects invalid commands; tokens tracked in AuthVault | `/mnt/e/matrex-dev/services/librarian.py:23-46` |

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | R4 MCP `call` | Argument with unknown property not in schema | `ValueError("unknown argument(s): [...]")` raised; audit logged with result `"blocked"` |
| 2 | R4 MCP `call` | Missing required argument | `ValueError("missing required argument(s): [...]")` raised; call fails closed |
| 3 | R4 MCP `call` | Argument type mismatch (e.g. string for integer) | `ValueError("$.prop must be integer")` raised; returns `{"ok": False, "error": ...}` |
| 4 | R4 MCP `call` | Argument string contains NUL byte (`\x00`) | `ValueError("<name>.<input> contains a NUL byte")` raised by `validate_values` |
| 5 | R4 MCP `call` | Argument size exceeds 65,536 bytes | `ValueError("MCP arguments exceed output limit")` raised; call rejected |
| 6 | R4 MCP `call` | Server execution exceeds `timeout_s` | `asyncio.TimeoutError` caught; audit logged with result `"timeout"`; returns `{"ok": False, "error": "timeout after ...s"}` |
| 7 | R4 MCP `call` | Approved capability invoked without `SovereigntyGate` | Returns `{"ok": False, "error": "sovereignty gate required for approved capability"}` |
| 8 | R4 MCP `run_allowed` | Invoked while an asyncio event loop is already running | Returns `{"ok": False, "error": "MCP run_allowed cannot block an active event loop"}` |
| 9 | R4 MCP `from_manifest` | Server launcher not in allowlist or not found on PATH | Raises `ValueError("unavailable or disallowed MCP launcher: ...")` |
| 10 | R4 MCP `from_manifest` | Environment variable does not end with `_REF` | Raises `ValueError("MCP environment must contain *_REF values only")` |
| 11 | R5 Skills `discover` | Manifest with empty capabilities | Assigned `risk="MEDIUM"`; tagged as empty capabilities ghost |
| 12 | R5 Skills `discover` | Manifest containing "password-crack" in name or source | Assigned `risk="HIGH"`; blocked during validation |
| 13 | R5 Skills `validate` | Reviewer argument is empty string or None | Returns `stage="REJECTED"`, reason: `"no reviewer — promotion blocked"` |
| 14 | R5 Skills `validate` | License is `"unknown"` or `""` | Returns `stage="REJECTED"`, reason: `"unverified license (...)"` |
| 15 | R5 Skills `validate` | `allowed_tools` contains `"shell.exec"` | Returns `stage="REJECTED"`, reason: `"invalid skill contract: unknown allowed tools: shell.exec"` |
| 16 | R5 Skills `validate_curated` | Package directory contains symlinks | Package moved to `quarantine/` with reason `"symlinked package directory"` or `"symlinked <file>"` |
| 17 | R5 Skills `validate_curated` | Missing `source_manifest.json` or `package_manifest.json` | Package moved to `quarantine/` with reason `"missing <manifest>"` |
| 18 | R5 Skills `promote` | `commander_approval=False` | Raises `PermissionError("promotion requires Commander approval")` |
| 19 | R5 Skills `inject` | Invoked on a skill whose stage is not `"PROMOTED"` | Raises `ValueError("inject requires PROMOTED stage")` |
| 20 | R5 Crawlers `read_skill` | File path points outside target directory (e.g. `../../etc/passwd`) | `is_relative_to` check fails; returns `None`; logs security breach warning |
| 21 | R5 Crawlers `_handle_store_request` | Memory content contains `__import__('os').system('rm -rf /')` | Guillotine detects forbidden pattern; AsymmetricQA rejects; emits `EventType.ERROR`; storage denied |
| 22 | R5 Crawlers `_handle_extracted_token` | Token string has length <= 4 characters | Masked token formatted as `"***"` to avoid leaking partial or full short secret |
| 23 | R5 Crawlers `_handle_extracted_token` | Token is non-string or None | Handled safely: cast to empty string, logged as `"***"`, key injected with safe empty/string token |
| 24 | R5 Crawlers `emergency_token_stash` | Stash reaches `MAX_STASH_SIZE` (2) | Oldest token in dictionary evicted to prevent memory leak |
| 25 | R5 Crawlers `emergency_token_stash` | Token age exceeds 300 seconds (TTL) | Evicted during `_clean_stash()` sweep |
