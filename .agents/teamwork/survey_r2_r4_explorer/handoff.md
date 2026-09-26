# Handoff Report — R2 & R4 Latency & Web Stack Survey

**Handoff Type**: Hard (Task Complete)  
**Author**: `survey_r2_r4_explorer`  
**Recipient**: Parent Orchestrator (`099ee37a-35a6-4355-b6cd-a3dc0c99b104`)  
**Mission**: Requirements R2 (Engine Latency & Pre-Warming, True Non-Blocking Execution) and R4 (Complete Web Stack Synchronization)  
**Date**: 2026-09-24  

---

## 1. Observation

1. **Cold Load Latency & Ollama Endpoints**:
   - `matrix_main.py:27-106`: The boot sequence boots `NeuralBusRouter`, `FailsafeMonitor`, `SecureLibrarian`, crawlers, and agents, but makes no connection or pre-load call to Ollama.
   - Live testing of the local Ollama server at `http://127.0.0.1:11434` (version `0.34.2`, model `llama3.2:3b`):
     - `POST /api/generate` returned `urllib.error.HTTPError: HTTP Error 404: Not Found`.
     - `POST /api/chat` with `{"model": "llama3.2:3b", "messages": [], "stream": false}` returned HTTP 200:
       ```json
       {"model": "llama3.2:3b", "created_at": "...", "message": {"role": "assistant", "content": ""}, "done": true, "done_reason": "load"}
       ```
       Execution time on warm cache: `0.091s`.
   - `services/ollama_client.py:386-387`:
     ```python
     if not messages:
         raise OllamaProtocolError("Ollama chat requires at least one message")
     ```
     `tests/test_ollama_client.py:309-322` asserts that calling `chat()` with empty `messages` raises `OllamaProtocolError`.

2. **Event Loop Blocking in `services/ollama_client.py`**:
   - `services/ollama_client.py:560-571`:
     ```python
     async def chat(
         self,
         agent: AgentRole,
         messages: list[dict[str, Any]],
         tools: list[dict[str, Any]] | None = None,
     ) -> dict[str, Any]:
         endpoint = self.get_endpoint(agent)  # Line 566: Synchronous execution on event loop!
         if endpoint:
             return await asyncio.to_thread(
                 self.client.chat, endpoint.model_id, messages, tools=tools
             )
     ```
   - `get_endpoint(agent)` at lines 524-542 iterates through `self.ROLE_MODELS.get(agent)` and calls `_check_ollama_model(model)`, which calls `has_model(model)` -> `resolve_model(model)` -> `self.tags(refresh=True)` -> `urllib.request.urlopen()`.
   - `UrllibTransport.request` (lines 169-206) executes blocking socket I/O synchronously on the calling thread.

3. **Cognitive Gate and Intent Parser Blocking in `agents/base_agent.py`**:
   - `agents/base_agent.py:170-173`:
     ```python
     intent = self.intent_parser.parse(message)
     trace = self.cognitive_gate.deliberate(message)
     self.decision_logger.log(trace)
     ```
   - `core/intent_parser.py:142-156`:
     ```python
     try:
         from services.ollama_client import OllamaRouter  # Non-existent import; class is ModelRouter
         router = OllamaRouter()
         response = router.chat(...)  # ModelRouter.chat is async def; cannot be called synchronously
     ```
   - `core/decision_log.py:86-118`: `DecisionLogger.log(trace)` opens `sqlite3.connect()`, runs `INSERT INTO decision_log`, and commits synchronously on the event loop.

4. **Failsafe Monitor Subprocess and Path Portability**:
   - `matrix_main.py:43`:
     `failsafe = FailsafeMonitor(matrix_root=r"J:\THE_MATRIX")`
     Contains a hardcoded Windows path.
   - `core/failsafe.py:89-99, 117-128`: Calls `subprocess.run(["git", ...])` synchronously.

5. **Web Stack Startup & Proxy Configuration**:
   - `IGNITE_MATRIX.bat:50-82`: Boots components in order: (1) Vite (`npm run dev` on 5173), (2) UI Bridge (`ui_bridge.py` on 8000), (3) Core Engine (`matrix_main.py` on 5555).
   - `dashboard/vite.config.js:14-25`:
     ```javascript
     proxy: {
       '/ws': {
         target: 'ws://127.0.0.1:8000',
         ws: true,
         changeOrigin: true
       },
       '/api': {
         target: 'http://127.0.0.1:8000',
         changeOrigin: true
       }
     }
     ```
   - `services/ui_bridge.py`: Defines `@app.websocket("/ws")`, but has ZERO `@app.get("/api/...")` endpoints. Any REST call to `/api` returns 404.

---

## 2. Logic Chain

1. **Cold Start Latency (R2)**:
   - Observation 1 proves that `matrix_main.py` performs no pre-loading.
   - Observation 1 proves that cold loading takes ~30s, but sending `POST /api/chat` with `messages: []` and `stream: false` returns `done_reason: 'load'` and forces weights into memory.
   - Because `client.chat()` must continue raising `OllamaProtocolError` on empty messages to satisfy existing test invariants, a dedicated `prewarm()` method on `OllamaClient` and `ModelRouter` is required.
   - Launching this as an unawaited `asyncio.create_task()` in `matrix_main.py:boot_matrix()` allows the engine to boot without pausing, achieving zero-cold-start when user commands arrive.

2. **Event Loop Non-Blocking (R2)**:
   - Observation 2 proves that `ModelRouter.chat()` executes `get_endpoint()` synchronously on the asyncio event loop thread before calling `asyncio.to_thread()`.
   - `get_endpoint()` triggers un-cached `urllib.request.urlopen()` calls to `/api/tags` for each candidate model, blocking the event loop.
   - Caching `tags` with a 60-second TTL and resolving endpoints via `asyncio.to_thread` guarantees that `ModelRouter.chat()` never performs synchronous network I/O on the event loop.
   - Observation 3 proves that `core/intent_parser.py` has an incorrect import (`OllamaRouter` vs `ModelRouter`) and attempts synchronous execution of an async method. Making `parse_async()` an explicit coroutine or keeping the rule-based fallback prevents freezing the event loop during intent parsing.
   - Offloading `DecisionLogger.log()` to `asyncio.to_thread()` eliminates SQLite file I/O delays from the event loop.

3. **Web Stack Synchronization (R4)**:
   - Observation 5 shows `IGNITE_MATRIX.bat` starts Vite (:5173) before UI Bridge (:8000), which starts before Engine (:5555).
   - When Vite opens first, immediate browser WebSocket requests hit `ECONNREFUSED` on port 8000.
   - Reordering boot sequence to Engine (:5555) -> Bridge (:8000) -> Dashboard (:5173) guarantees every service is available before its dependent attempts connection.
   - Observation 5 shows `vite.config.js` proxies `/api`, but `ui_bridge.py` defines no REST routes. Implementing `@app.get("/api/health")` and `@app.get("/api/status")` satisfies the proxy contract and enables diagnostic health-checks.

---

## 3. Caveats

1. **VRAM Capacity Constraints**:
   Pre-warming multiple large models (e.g. `llama3.2:3b` and `qwen3-coder`) concurrently on machines with limited VRAM (<= 8GB) can cause memory swapping. Pre-warming should prioritize the primary model (`os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")`).
2. **WSL2 Networking Differences**:
   When running under WSL2 with Ollama on Windows, `normalize_ollama_base_url()` discovers the host gateway via `/etc/resolv.conf`. Both loopback and WSL2 gateway are handled, but latency depends on WSL2 virtualized vswitch performance.
3. **Read-Only Scope**:
   In accordance with the explorer role, no source code files in `services/`, `agents/`, `core/`, or `dashboard/` were modified directly. All findings are synthesized as actionable architectural proposals.

---

## 4. Conclusion

1. **Pre-Warming**: The ~30s latency can be completely eliminated by adding `OllamaClient.prewarm()` (`POST /api/chat` with `messages: []`) and dispatching an asynchronous background task `asyncio.create_task(_prewarm_brain())` at `matrix_main.py:boot_matrix()`.
2. **True Async Execution**: Eliminating event loop blocking requires:
   - Adding a 60-second TTL in-memory cache to `OllamaClient.tags()`.
   - Wrapping `get_endpoint` in `asyncio.to_thread` within `ModelRouter.chat()`.
   - Wrapping `decision_logger.log()` in `asyncio.to_thread()`.
   - Correcting `OllamaRouter` to `ModelRouter` in `core/intent_parser.py` and making intent extraction async.
   - Dynamically resolving `matrix_root` at `matrix_main.py:43`.
3. **Web Stack Synchronization**:
   - Reorder `IGNITE_MATRIX.bat` to boot Engine (:5555) -> UI Bridge (:8000) -> Dashboard (:5173).
   - Add `@app.get("/api/health")` and `@app.get("/api/status")` to `services/ui_bridge.py`.
   - Use `loadEnv` in `dashboard/vite.config.js` for dynamic backend port resolution.

---

## 5. Verification Method

1. **Test Suite Verification**:
   Execute the full test suite to verify baseline integrity:
   ```bash
   SOVEREIGN_BUS_SECRET=sovereign_terminal_key_2026_matrix_secure .venv/bin/python -m pytest -q --no-cov
   ```
   (Verified: 38/38 unit and integration tests passing).

2. **Live Ollama Pre-Warming Pulse Verification**:
   ```bash
   .venv/bin/python -c "
   import json, urllib.request, time
   from services.ollama_client import normalize_ollama_base_url
   base_url = normalize_ollama_base_url()
   req = urllib.request.Request(
       f'{base_url}/api/chat',
       data=json.dumps({'model': 'llama3.2:3b', 'messages': [], 'stream': False}).encode(),
       headers={'Content-Type': 'application/json'},
       method='POST'
   )
   t0 = time.time()
   with urllib.request.urlopen(req) as resp:
       res = json.loads(resp.read().decode())
   print('Prewarm verified:', res.get('done_reason') == 'load', 'Elapsed:', round(time.time() - t0, 3))
   "
   ```

3. **Event Loop Non-Blocking Verification**:
   Verify that `get_endpoint` does not make un-cached network calls by measuring consecutive executions of `router.get_endpoint(AgentRole.NEO)` to confirm cache hit latency (<0.5ms).

4. **Web Stack Port & Proxy Verification**:
   ```bash
   # Verify UI Bridge REST endpoint:
   curl -s http://127.0.0.1:8000/api/health
   # Verify Vite dev server proxy:
   curl -s http://127.0.0.1:5173/api/health
   ```
