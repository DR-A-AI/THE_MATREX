# Technical Analysis & Implementation Strategy: Concurrency & Invariant Verification

**Author**: Explorer 1 (Concurrency & Invariant Explorer)  
**Date**: 2026-09-23T06:34:00Z  
**Target Scope**: R1 (Concurrency Hazard in `services/ui_bridge.py`) & R5 (Test Suite Verification & Invariant Preservation)

---

## 1. R1: Concurrency Hazard Remediation in `services/ui_bridge.py`

### 1.1 Root Cause & Mechanism of the WebSocket Broadcast Race Condition
In `services/ui_bridge.py`, incoming ZMQ events (`STATE_UPDATE`, `TASK_COMPLETED`, `SOVEREIGN_OVERRIDE`, `AGENT_ALIVE`) trigger `handle_agent_message(event)`:

```python
# services/ui_bridge.py:110-117
if send_lock:
    async with send_lock:
        for conn in active_connections:
            try:
                await conn.send_text(msg_str)
            except Exception:
                logger.exception("WebSocket send failed")
```

#### Race Hazard Mechanism:
1. `active_connections: list[WebSocket] = []` is a shared module-level list.
2. In `websocket_endpoint`:
   - Connection open: `active_connections.append(websocket)` (line 143)
   - Connection disconnect/close: `active_connections.remove(websocket)` (line 182 in `finally` block)
3. Both `active_connections.append()` and `active_connections.remove()` execute **outside** of `send_lock`.
4. In `handle_agent_message`: The loop iterates directly over `active_connections` (`for conn in active_connections:`). When `await conn.send_text(msg_str)` is executed, the coroutine yields control back to the asyncio event loop.
5. If another WebSocket client connects or disconnects while the broadcast is yielding:
   - For a `list`: modifying the list in-place (`.remove()`) during forward iteration causes index shift, resulting in skipped connections or processing elements out of sequence.
   - For a `set` (or if converted to set): mutating the collection during iteration immediately raises `RuntimeError: Set changed size during iteration`.
   - If a client connection abruptly terminates, `send_text` raises an exception; without snapshotting, concurrent modifications can corrupt loop state.

#### Historical Precedent:
Git log audit reveals that commit `OMNI-AUDIT` previously implemented snapshot iteration:
```python
async with send_lock:
    for conn in list(active_connections):
        try:
            await conn.send_text(msg_str)
        ...
```
A recent modification regressed this by removing `list(...)`, exposing the broadcast loop to mutation hazards during async yields.

### 1.2 Uninitialized `bus_client` Hazard
In `services/ui_bridge.py`:
- Line 71: `bus_client = None`
- Lines 78-79: `bus_client` is initialized inside FastAPI's `lifespan` manager:
  ```python
  @contextlib.asynccontextmanager
  async def lifespan(app: FastAPI):
      global send_lock
      send_lock = asyncio.Lock()
      global bus_client
      bus_client = NeuralBusClient(identity="UI_Bridge")
      ...
  ```
- Line 176 in `websocket_endpoint`:
  ```python
  event = EventPayload(
      event_type=EventType.USER_COMMAND,
      source_agent_id="Commander_UI",
      correlation_id=str(int(time.time())),
      payload={"target_agent": target_agent, "message": user_text},
  )
  await bus_client.send(event)  # <-- UNGUARDED DEREFERENCE
  ```

#### Failure Scenarios:
1. If a client connects and transmits a message before `lifespan` finishes initializing `bus_client`, or if `ui_bridge` is loaded or tested without triggering the lifespan context manager, `bus_client` is `None`.
2. Calling `await bus_client.send(event)` triggers an unhandled `AttributeError: 'NoneType' object has no attribute 'send'`, aborting the connection handler and potentially dropping the WebSocket.
3. On application shutdown, `bus_client` is never stopped, leaving background listening tasks and open ZMQ sockets unclosed.

### 1.3 Remediation Strategy for `services/ui_bridge.py`

#### A. Snapshot Iteration under `send_lock`
Restore `list(active_connections)` snapshotting at line 112:
```python
        if send_lock:
            async with send_lock:
                for conn in list(active_connections):
                    try:
                        await conn.send_text(msg_str)
                    except Exception:
                        logger.exception("WebSocket send failed")
```
Creating a shallow copy `list(active_connections)` creates an isolated snapshot of the connection list at that moment. Subsequent appends or removes during `await conn.send_text(...)` mutate `active_connections` without modifying the snapshot list being iterated.

#### B. Guard Against Uninitialized `bus_client`
1. In `websocket_endpoint`: Guard `bus_client.send(event)` with a check for `bus_client is not None`:
```python
            if bus_client is not None:
                await bus_client.send(event)
            else:
                logger.error("NeuralBusClient is not initialized; cannot route message to %s", target_agent)
```
2. In `lifespan`: Ensure graceful cleanup on shutdown:
```python
    asyncio.create_task(bus_client.start())
    try:
        yield
    finally:
        if bus_client is not None:
            await bus_client.stop()
```

### 1.4 Test Coverage Assessment
- **Existing Tests in `tests/`**: None. There are currently 0 tests in `tests/` targeting `services/ui_bridge.py`.
- **Existing Scripts**:
  - `test_ws.py`: A manual script connecting to `ws://127.0.0.1:8000/ws` and sending Arabic text commands to Neo.
  - `test_ui.py`: A Playwright browser test verifying the React dashboard frontend.
- **Recommended Test Implementation**:
  A unit test should be added (or verified) that instantiates `websocket_endpoint` / `lifespan` or mocks `active_connections` during `handle_agent_message` to verify:
  1. Concurrent removal of a connection from `active_connections` during broadcast does not crash the loop.
  2. Sending a command when `bus_client is None` logs an error without raising `AttributeError`.

---

## 2. R5: Test Suite Verification & Invariant Preservation

### 2.1 Baseline Test Suite Execution
Execution command:
```bash
SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
```

#### Results:
- **Total Tests Collected**: 25
- **Total Tests Passed**: 25 (100%)
- **Failures / Errors**: 0
- **Duration**: ~57.5 seconds
- **Warnings**: 1 harmless warning (`google.genai.types` `_UnionGenericAlias` deprecation in Python 3.14).

#### Catalog of All 25 Collected Tests:
| Suite File | Test Name | Status |
| :--- | :--- | :--- |
| `tests/test_auth_vault.py` | `test_auth_vault_token_lifecycle` | PASSED |
| `tests/test_auth_vault.py` | `test_auth_vault_invalid_token` | PASSED |
| `tests/test_auth_vault.py` | `test_auth_vault_garbage_collection` | PASSED |
| `tests/test_crawlers_integration.py` | `test_librarian_crawler_init` | PASSED |
| `tests/test_crawlers_integration.py` | `test_librarian_crawler_path_traversal_protection` | PASSED |
| `tests/test_crawlers_integration.py` | `test_librarian_crawler_scan_and_read` | PASSED |
| `tests/test_crawlers_integration.py` | `test_memory_crawler_init` | PASSED |
| `tests/test_crawlers_integration.py` | `test_memory_crawler_extract_and_sort` | PASSED |
| `tests/test_crawlers_integration.py` | `test_memory_crawler_store_and_recall` | PASSED |
| `tests/test_crawlers_integration.py` | `test_memory_crawler_aegis_qa_rejection` | PASSED |
| `tests/test_crawlers_integration.py` | `test_assistant_crawler_init` | PASSED |
| `tests/test_crawlers_integration.py` | `test_assistant_crawler_token_masking` | PASSED |
| `tests/test_crawlers_integration.py` | `test_crawler_agent_workflow_safe_memory_storage` | PASSED |
| `tests/test_crawlers_integration.py` | `test_crawler_agent_workflow_safe_token_injection` | PASSED |
| `tests/test_crawlers_integration.py` | `test_full_lifecycle_memory_operations` | PASSED |
| `tests/test_crawlers_integration.py` | `test_crawler_security_event_validation` | PASSED |
| `tests/test_crawlers_integration.py` | `test_memory_crawler_concurrent_operations` | PASSED |
| `tests/test_crawlers_integration.py` | `test_crawler_logging_and_audit_trail` | PASSED |
| `tests/test_librarian.py` | `test_librarian_jit_provisioning` | PASSED |
| `tests/test_memory_manager.py` | `test_agent_memory_db_lifecycle` | PASSED |
| `tests/test_message_serialization.py` | `test_event_payload_serialization` | PASSED |
| `tests/test_neo_authority.py` | `test_authority` | PASSED |
| `tests/test_real_world_crawlers.py` | `test_real_world_librarian_crawler` | PASSED |
| `tests/test_real_world_crawlers.py` | `test_real_world_memory_crawler` | PASSED |
| `tests/test_real_world_crawlers.py` | `test_real_world_assistant_crawler` | PASSED |

### 2.2 Architectural Invariants Audit

#### 1. HMAC-SHA256 Signing & Anti-Replay (`core/neural_bus.py`)
- **Key Ingestion**: Mandatory `SOVEREIGN_BUS_SECRET` environment variable checked at module import (`lines 21-25`). Fails fast if missing.
- **Signing**: Messages are HMAC-SHA256 signed using `BUS_SECRET` over canonical JSON bytes (`_sign_payload` lines 42-43).
- **Anti-Replay Window**: Each message carries a 16-byte random hex nonce (`nonce`) and timestamp (`time.time()`). Nonces are tracked in `seen_nonces` with a 5.0-second purge window (`lines 99-111`).
- **TTL Enforcement**: 60.0-second message TTL (`lines 114-116`).
- **Integrity Status**: Verified intact.

#### 2. Key Routing Topology (`SOVEREIGN_CONSTITUTION.md` & `services/assistant_crawler.py`)
- **Blind Extraction**: Neo (`agents/neo_agent.py:42`) and Trinity (`agents/trinity_agent.py:36`) emit `TOKEN_EXTRACTED` upon detecting tokens. They never store tokens.
- **Exclusive Distributor**: `AssistantCrawler` (`services/assistant_crawler.py:25`) is the only entity registered to handle `TOKEN_EXTRACTED`. It stores to the Auth Vault and broadcasts `KEY_INJECT` (`lines 50-57`).
- **No Direct JIT Requesting**: Agents are forbidden from JIT-requesting credentials directly.
- **Integrity Status**: Verified intact.

#### 3. Emergency Token Stash Limits (`agents/base_agent.py`)
- **Stash Attributes**: `self.emergency_token_stash: dict[str, float] = {}` (line 33).
- **Size Limit**: `self.MAX_STASH_SIZE = 2` (line 34).
- **Eviction & TTL**: When stash capacity reaches 2, the oldest key is evicted (`lines 65-68`). Keys expire after 300.0s TTL (`lines 58, 79`).
- **Masking**: Token logging uses `***{token[-4:]}` pattern (line 75).
- **Integrity Status**: Verified intact.

#### 4. Windows Event Loop Policy (`matrix_main.py:108`, `tests/conftest.py:9`, `services/ui_bridge.py:11`)
- **Policy**: `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` on `sys.platform == "win32"`.
- **Purpose**: pyzmq requires SelectorEventLoop on Windows; ProactorEventLoop triggers fatal socket errors.
- **Integrity Status**: Present in `matrix_main.py`, `tests/conftest.py`, and `services/ui_bridge.py`.

---

## 3. Recommended Implementation Changes

### Concrete Patch for `services/ui_bridge.py`:

```diff
--- a/services/ui_bridge.py
+++ b/services/ui_bridge.py
@@ -109,7 +109,7 @@ async def lifespan(app: FastAPI):
 
         if send_lock:
             async with send_lock:
-                for conn in active_connections:
+                for conn in list(active_connections):
                     try:
                         await conn.send_text(msg_str)
                     except Exception:
@@ -122,7 +122,11 @@ async def lifespan(app: FastAPI):
     bus_client.register_handler(EventType.AGENT_ALIVE.value, handle_agent_message)
 
     asyncio.create_task(bus_client.start())
-    yield
+    try:
+        yield
+    finally:
+        if bus_client is not None:
+            await bus_client.stop()
 
 
 app = FastAPI(title="Sovereign UI Bridge", lifespan=lifespan)
@@ -173,7 +177,10 @@ async def websocket_endpoint(websocket: WebSocket):
                 correlation_id=str(int(time.time())),
                 payload={"target_agent": target_agent, "message": user_text},
             )
-            await bus_client.send(event)
+            if bus_client is not None:
+                await bus_client.send(event)
+            else:
+                logger.error("NeuralBusClient is not initialized; cannot route message to %s", target_agent)
 
     except WebSocketDisconnect:
         logger.info("UI WebSocket Connection Closed.")
```

---

## 4. Verification Plan for Implementer
1. Apply the patch to `services/ui_bridge.py`.
2. Run format check: `.venv/bin/black --check services/ui_bridge.py`.
3. Run linter check: `.venv/bin/ruff check services/ui_bridge.py`.
4. Run full test suite: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`.
5. Verify zero test regressions (25/25 passed).
