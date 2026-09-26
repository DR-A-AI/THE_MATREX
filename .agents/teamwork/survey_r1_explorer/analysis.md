# Technical Investigation Report: Requirement R1 — Synchronous CLI Interaction & Bus Bidirectional Bridge

**Author**: R1 CLI & Bus Bridge Explorer (`survey_r1_explorer`)  
**Target Subsystem**: Sovereign Matrix CLI (`send_command.py`), Agent Runtime (`agents/base_agent.py`, `agents/neo_agent.py`), Zero-Trust Neural Bus (`core/neural_bus.py`), and UI Bridge (`services/ui_bridge.py`)  
**Date**: 2026-09-24  
**Status**: Completed Investigation (Read-Only Analysis)

---

## 1. Executive Summary

Requirement R1 mandates upgrading `send_command.py` from an asynchronous, fire-and-forget probe into a robust, synchronous CLI client capable of transmitting directives to the Zero-Trust Neural Bus, synchronously awaiting execution, parsing intermediate status updates, and streaming live tool execution commentary and final agent responses directly to the user's terminal with zero silent drops. Furthermore, R1 mandates verifying that `services/ui_bridge.py` forwards agent events over WebSocket without dropping frames or blocking the asyncio event loop.

Our investigation identified **six foundational bottlenecks and architectural flaws** preventing synchronous execution:
1. **Premature Socket Termination in `send_command.py`**: The CLI client unconditionally terminates after a 0.5-second sleep (`send_command.py:38-39`), long before Ollama inference (typically 2–15s warm, up to 30s cold) or multi-step tool loops can execute.
2. **Deaf CLI Listener**: `send_command.py` never registers handlers via `client.register_handler()` for `STATE_UPDATE`, `TASK_COMPLETED`, or errors; thus, all incoming replies received by `NeuralBusClient._listen_loop()` are silently discarded.
3. **No Correlation Tracking**: Neither `send_command.py` nor `services/ui_bridge.py` implements a wait mechanism (`asyncio.Future` or `asyncio.Queue`) mapped to the request's `correlation_id`.
4. **Missing `TASK_COMPLETED` Invariant**: Neither `agents/base_agent.py` nor `agents/neo_agent.py` emits `EventType.TASK_COMPLETED` at the conclusion of a directive; both emit generic `EventType.STATE_UPDATE` for intermediate thoughts, tool calls, and final answers alike, leaving the caller unable to detect task completion deterministically.
5. **UUID vs. Name Mismatch Bug in `base_agent.py:270-272`**: The initial thinking status update in `base_agent.py` emits `source_agent_id=self.agent_id` (a UUID) instead of `self.name` ("neo", "trinity"), breaking UI client status rendering.
6. **Socket Drops & Head-of-Line Blocking**:
   - `core/neural_bus.py:177-185`: Router broadcast uses `flags=zmq.NOBLOCK` and on `EAGAIN` permanently purges the client from `active_clients`, causing silent, irrecoverable disconnection during traffic bursts.
   - `services/ui_bridge.py:111-118`: Iterates over connections under a global `send_lock` and fails to prune disconnected sockets on send exceptions, causing cascading latency and dead-socket accumulation.

---

## 2. In-Depth Component Analysis

### 2.1. `send_command.py` Analysis

#### Current Codebase Inspection
```python
# send_command.py (lines 12–40)
async def send_command(agent: str, message: str):
    bus_url = os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
    secret = os.getenv("SOVEREIGN_BUS_SECRET")
    if not secret:
        print("ERROR: SOVEREIGN_BUS_SECRET must be set in .env")
        return

    client = NeuralBusClient(identity="CommanderCLI", endpoint=bus_url)
    await client.start()
    
    payload = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="dr-anas-hilal",
        correlation_id=str(uuid.uuid4()),
        payload={
            "target_agent": agent,
            "message": message,
            "auth_token": os.getenv("COMMANDER_AUTH_TOKEN", "sovereign_commander_token_123")
        }
    )
    
    print(f"📡 Sending authenticated command to '{agent}'...")
    await client.send(payload)
    print("✅ Command sent to Neural Bus.")
    
    await asyncio.sleep(0.5)
    await client.stop()
```

#### Defect Decomposition
1. **Fire-and-Forget Pattern**:
   - At line 35, `client.send(payload)` signs the message with HMAC-SHA256 and pushes it onto the DEALER socket.
   - At line 38, `await asyncio.sleep(0.5)` pauses for 500ms and immediately invokes `await client.stop()`.
   - The DEALER socket is closed with `linger=0`, cancelling the underlying `_listen_task` before the agent can even begin its first inference pass.
2. **Missing Inbound Event Handlers**:
   - `NeuralBusClient` (`core/neural_bus.py:51`) requires `register_handler(event_type, handler)`.
   - In `_listen_loop()` (`core/neural_bus.py:127-129`):
     ```python
     handler = self.handlers.get(event_type_str)
     if handler:
         asyncio.create_task(handler(event))
     ```
   - In `send_command.py`, `self.handlers` is empty (`{}`). When the router broadcasts `STATE_UPDATE`, `_listen_loop` drops it silently because `handler` is `None`.
3. **Static Client Identity Hazard**:
   - `client = NeuralBusClient(identity="CommanderCLI", endpoint=bus_url)`
   - If two CLI calls run simultaneously or in quick succession, the ROUTER socket on `:5555` treats the second client as an identity collision or routes frames to an already-closed socket.
4. **Lack of Terminal Streaming UX**:
   - No interactive spinner or streaming parser.
   - Intermediate status notifications (`Thinking...`, `Executing tool: ...`) and cognitive deliberation outcomes (`INTENT_PARSED`) are completely invisible.

---

### 2.2. `agents/base_agent.py` & `agents/neo_agent.py` Analysis

#### Event Ingestion & Authority Check
- In `base_agent.py:58`:
  ```python
  self.client.register_handler(EventType.USER_COMMAND.value, self._handle_user_command)
  ```
- In `base_agent.py:132-150` & `neo_agent.py:146`:
  ```python
  async def _validate_commander(self, event: EventPayload) -> bool:
      AUTHORIZED_COMMANDERS = ["Commander_UI", "dr-anas-hilal", "admin", "Commander_Tester"]
      source = event.source_agent_id
      if source not in AUTHORIZED_COMMANDERS:
          ...
          await self.client.send(alert)
          return False
      return True
  ```
  `send_command.py` uses `source_agent_id="dr-anas-hilal"`, which successfully passes authorization.

#### Target Routing & Filtering
- In `base_agent.py:160` and `neo_agent.py:142`:
  ```python
  if target.lower() not in self.name.lower() and target.lower() not in self.agent_id.lower():
      return
  ```
  Matches target agent name (e.g., `--agent neo`).

#### Cognitive Gate Deliberation (`base_agent.py:169–205`)
- When a command arrives, `base_agent.py` deliberate via:
  ```python
  intent = self.intent_parser.parse(message)
  trace = self.cognitive_gate.deliberate(message)
  self.decision_logger.log(trace)
  ```
- Events emitted during gate execution:
  - `EventType.INTENT_PARSED` (with `correlation_id=event.correlation_id`, payload `{"intent": intent.inferred, "complexity": intent.complexity}`)
  - If rejected: `EventType.STATE_UPDATE` (payload `{"message": "Execution halted..."}`)
  - If accepted: `EventType.DECISION_LOGGED` (payload `{"task_hash": trace.task_hash, "decision": "proceed"}`)
- **Divergence**: `neo_agent.py:134-172` overrides `_handle_user_command` and completely bypasses the Cognitive Gate! It jumps directly into local tool evaluation and Ollama inference.

#### Intermediate and Final Status Updates
- **Source Agent ID Bug (`base_agent.py:270-274`)**:
  ```python
  thinking_msg = EventPayload(
      event_type=EventType.STATE_UPDATE,
      source_agent_id=self.agent_id,   # <--- BUG: Emits UUID instead of self.name ("neo", "base")!
      correlation_id=event.correlation_id,
      payload={"status_action": f"{self.name} IS WORKING... \n> Thinking..."},
  )
  await self.client.send(thinking_msg)
  ```
  Because `source_agent_id` is a UUID, `ui_bridge.py` forwards `sender="c3d2e1..."`. The React dashboard (`ChatPage.jsx:62`) attempts to index `agentStatuses[data.sender.toLowerCase()]`, which fails to match `activeAgent` ("neo").
- **Intermediate Status in `neo_agent.py`**:
  - Initial thinking (`neo_agent.py:174`): `payload={"status_action": "Thinking..."}`
  - Pre-tool commentary (`neo_agent.py:592`): `payload={"status_action": content}`
  - Tool invocation (`neo_agent.py:601`): `payload={"status_action": f"أقوم الآن بتنفيذ الأداة: {calls_str}..."}`
  - Visual capture (`neo_agent.py:643`): `payload={"message": f"إليك ما أراه على الشاشة الآن أيها القائد:\n\n{img_md}"}`
- **Final Reply (`base_agent.py:428`, `neo_agent.py:667`)**:
  ```python
  reply = EventPayload(
      event_type=EventType.STATE_UPDATE,
      source_agent_id=self.name,
      correlation_id=event.correlation_id,
      payload={"message": response_msg},
  )
  await self.client.send(reply)
  ```
- **Crucial Architectural Gap**:
  Neither agent emits `EventType.TASK_COMPLETED`. Both emit `STATE_UPDATE`. A listener cannot easily tell if a `STATE_UPDATE` is an intermediate notification or the final deliverable without inspecting whether the payload contains `"status_action"` vs `"message"`. Furthermore, intermediate messages (like screen capture markdown in `neo_agent.py:643`) ALSO use `"message"`!

---

### 2.3. `services/ui_bridge.py` Analysis

#### Inbound Pathway (WebSocket -> Neural Bus)
```python
# services/ui_bridge.py (lines 175-184)
event = EventPayload(
    event_type=EventType.USER_COMMAND,
    source_agent_id="Commander_UI",
    correlation_id=str(int(time.time())),  # <--- DEFECT: Truncated timestamp!
    payload={"target_agent": target_agent, "message": user_text},
)
if bus_client is not None:
    await bus_client.send(event)
```
- **Correlation ID Collision Defect**: `str(int(time.time()))` has 1-second resolution. Any rapid subsequent messages share the exact same `correlation_id`.
- **Unhandled Parsing Exception**: If a malformed text frame is received over `/ws`, `payload = json.loads(data)` raises `json.JSONDecodeError`, aborting the connection handler abruptly.

#### Outbound Pathway (Neural Bus -> WebSocket)
```python
# services/ui_bridge.py (lines 111–118)
if send_lock:
    async with send_lock:
        for conn in list(active_connections):
            try:
                await conn.send_text(msg_str)
            except Exception:
                logger.exception("WebSocket send failed")
```
- **Dead Connection Accumulation**: When `await conn.send_text(msg_str)` fails (client closed, network drop), it logs an exception but does NOT remove `conn` from `active_connections`. The broken connection remains in `active_connections` until `websocket_endpoint` terminates. Every subsequent bus event attempts to send to the dead socket.
- **Lock Contention / Head-of-Line Blocking**:
  A single global lock `send_lock` serializes all broadcasts across all connections. A slow network client delays all other clients and delays the processing of incoming ZMQ events.
- **Selective Event Registration**:
  `ui_bridge.py:119-122` registers only:
  - `STATE_UPDATE`
  - `TASK_COMPLETED`
  - `SOVEREIGN_OVERRIDE`
  - `AGENT_ALIVE`
  It completely drops `EventType.ERROR`, `EventType.TASK_FAILED`, `EventType.INTENT_PARSED`, and `EventType.DECISION_LOGGED`. System crashes or task failures result in complete silence in the UI.

---

### 2.4. `core/neural_bus.py` Router Purging Hazard

In `core/neural_bus.py:173-190`:
```python
# Broadcast to all other active clients
disconnected = []
for client in list(self.active_clients):
    if client != sender:
        try:
            # Architectural Fix: Use NOBLOCK to prevent one slow client from blocking the entire bus
            await self.socket.send_multipart(
                [client, signature, msg_bytes], flags=zmq.NOBLOCK
            )
        except zmq.ZMQError as e:
            # Host unreachable or Queue full (EAGAIN)
            logger.info(
                f"Client {client.decode(errors='replace')} unreachable or queue full (errno={e.errno}), purging."
            )
            disconnected.append(client)
        except Exception:
            logger.exception("Broadcast to client failed")
            disconnected.append(client)
for d in disconnected:
    self.active_clients.discard(d)
```
- **Root Cause of Silent Frame Drops**:
  `zmq.NOBLOCK` raises `zmq.ZMQError` with `errno == zmq.EAGAIN` whenever the outgoing socket queue is momentarily full or when a client DEALER is context-switching.
  The router treats `EAGAIN` as a dead client and immediately discards it (`self.active_clients.discard(d)`).
  Once discarded, that client NEVER receives another broadcast from the router unless it explicitly sends a new frame or reconnects. This explains intermittent drops between `matrix_main.py` agents and `ui_bridge.py`.

---

## 3. End-to-End Interaction Flow

### Synchronous CLI Interaction Sequence (R1 Target Architecture)

```text
User Terminal                 send_command.py               NeuralBusRouter                Agent (Neo)
     │                              │                              │                            │
     │ 1. Run CLI command           │                              │                            │
     ├─────────────────────────────>│                              │                            │
     │                              │ 2. Connect DEALER            │                            │
     │                              │    Identity: CommanderCLI_xx │                            │
     │                              ├─────────────────────────────>│                            │
     │                              │ 3. Send USER_COMMAND         │                            │
     │                              │    correlation_id: <uuid>    │                            │
     │                              ├─────────────────────────────>│                            │
     │                              │                              │ 4. Route USER_COMMAND      │
     │                              │                              ├───────────────────────────>│
     │                              │                              │                            │ 5. Parse Intent &
     │                              │                              │ 6. STATE_UPDATE            │    Cognitive Gate
     │                              │                              │    (Thinking...)           │
     │                              │ 7. Broadcast                 │<───────────────────────────┤
     │                              │<─────────────────────────────┤                            │
     │ 8. Stream: "⏳ Thinking..."  │                              │                            │
     │<─────────────────────────────┤                              │                            │
     │                              │                              │ 9. STATE_UPDATE            │ 10. Execute Tool
     │                              │                              │    (Executing tool: ...)   │     (e.g., read_file)
     │                              │ 11. Broadcast                │<───────────────────────────┤
     │                              │<─────────────────────────────┤                            │
     │ 12. Stream: "🔧 Tool: ..."   │                              │                            │
     │<─────────────────────────────┤                              │                            │
     │                              │                              │ 13. TASK_COMPLETED         │ 14. Synthesize final
     │                              │                              │     (payload.message)      │     response
     │                              │ 15. Broadcast                │<───────────────────────────┤
     │                              │<─────────────────────────────┤                            │
     │ 16. Print Final Answer       │                              │                            │
     │<─────────────────────────────┤                              │                            │
     │ 17. Exit 0                   │                              │                            │
```

---

## 4. Architectural Recommendations & Exact Changes

### 4.1. Recommendations for `send_command.py`

1. **Synchronous Coroutine with Event Correlation Queue**:
   - Generate a unique client identity: `identity = f"CommanderCLI_{uuid.uuid4().hex[:8]}"`.
   - Generate a unique correlation ID: `cid = str(uuid.uuid4())`.
   - Use an `asyncio.Queue[EventPayload]` to collect events matching `event.correlation_id == cid`.
   - Register event handlers on `NeuralBusClient` for:
     - `EventType.STATE_UPDATE.value`
     - `EventType.TASK_COMPLETED.value`
     - `EventType.TASK_FAILED.value`
     - `EventType.ERROR.value`
     - `EventType.INTENT_PARSED.value`
     - `EventType.DECISION_LOGGED.value`
2. **Synchronous Await Loop with Timeout**:
   - Loop awaiting items from the queue with a default timeout (e.g., `--timeout 60`).
   - If an event has `status_action`, render intermediate status to stderr or stdout with terminal styling (e.g. `⏳ Thinking...`, `🔧 Executing tool: ...`).
   - If an event is `EventType.TASK_COMPLETED`, extract `message = event.payload.get("message")`, print the final result, and terminate cleanly.
   - If an event is `EventType.TASK_FAILED` or `EventType.ERROR`, display the failure and exit with non-zero status code.
   - For backwards compatibility (if agent emits final `STATE_UPDATE` without `TASK_COMPLETED`):
     Detect when `message` is present without `status_action`. To avoid terminating on intermediate screenshot messages, check if `is_final` flag is set or terminate when final chat message arrives.
3. **Interactive REPL Mode**:
   - Support both single-shot execution: `python send_command.py --agent neo "command"`
   - And continuous interactive shell: `python send_command.py --agent neo --interactive`
4. **Clean Bus Handshake & Graceful Shutdown**:
   - After `client.start()`, yield control briefly (`await asyncio.sleep(0.05)`) so the `REGISTER` frame reaches the router before the command frame is pushed.
   - Wrap in `try ... finally` to ensure `await client.stop()` is always invoked, removing hanging sockets.

### 4.2. Recommendations for `agents/base_agent.py` & `agents/neo_agent.py`

1. **Fix `source_agent_id` Bug in `base_agent.py:270`**:
   - Change `source_agent_id=self.agent_id` to `source_agent_id=self.name`.
2. **Deterministic `EventType.TASK_COMPLETED` Emission**:
   - In both `base_agent.py` and `neo_agent.py`, upon completing the command execution and tool loop, emit `EventType.TASK_COMPLETED` with:
     ```python
     completion_event = EventPayload(
         event_type=EventType.TASK_COMPLETED,
         source_agent_id=self.name,
         correlation_id=event.correlation_id,
         payload={
             "message": response_msg,
             "status": "success",
             "target_agent": self.name,
         },
         metadata={"agent": self.name, "task": "user_command_execution"}
     )
     await self.client.send(completion_event)
     ```
   - On unhandled exception or Ollama failure: emit `EventType.TASK_FAILED` with `correlation_id=event.correlation_id` and error payload.
3. **Unify Cognitive Gate Execution**:
   - In `neo_agent.py`, ensure Cognitive Gate deliberation is run or delegated to `super()._handle_user_command(event)` before tool loop begins.

### 4.3. Recommendations for `services/ui_bridge.py`

1. **Prune Dead Sockets on Broadcast Failure**:
   - Update `handle_agent_message`:
     ```python
     dead_connections = []
     async with send_lock:
         for conn in list(active_connections):
             try:
                 await conn.send_text(msg_str)
             except Exception:
                 logger.warning("WebSocket send failed; marking connection for removal")
                 dead_connections.append(conn)
         for dead in dead_connections:
             if dead in active_connections:
                 active_connections.remove(dead)
     ```
2. **Prevent Head-of-Line Blocking**:
   - Instead of sequential `await conn.send_text()`, broadcast concurrently:
     ```python
     await asyncio.gather(
         *(send_to_connection(conn, msg_str) for conn in list(active_connections)),
         return_exceptions=True
     )
     ```
3. **Expand Registered Handlers**:
   - Register handlers for `EventType.ERROR.value`, `EventType.TASK_FAILED.value`, and `EventType.INTENT_PARSED.value`.
   - Forward error events with `type: "error"` or `type: "status"` so the dashboard does not stay stuck in "Thinking...".
4. **Generate RFC4122 UUID for `correlation_id`**:
   - Replace `correlation_id=str(int(time.time()))` with `correlation_id=str(uuid.uuid4())`.

### 4.4. Recommendations for `core/neural_bus.py`

1. **Avoid Purging Active Clients on Transient `EAGAIN`**:
   - When `send_multipart` raises `zmq.ZMQError` with `errno == zmq.EAGAIN`, do not immediately discard the client from `self.active_clients`.
   - Maintain a failure counter or retry queue, purging only after persistent unreachable errors (e.g. 5 consecutive drops or timeout), or increase `ZMQ_SNDHWM` / `ZMQ_RCVHWM`.

---

## 5. Proposed Code Architecture Specifications

### 5.1. Upgraded `send_command.py` Blueprint

```python
"""Synchronous CLI Interaction Client for Sovereign Matrix Neural Bus.

Transmits user directives, subscribes to the Zero-Trust Neural Bus,
synchronously awaits the target agent's response, and streams
intermediate commentary and tool execution status in real time.
"""

import argparse
import asyncio
import os
import sys
import uuid
from typing import Any
from dotenv import load_dotenv

from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient

load_dotenv()


async def execute_cli_command(
    agent: str,
    message: str,
    timeout: float = 60.0,
    verbose: bool = False,
) -> int:
    bus_url = os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
    secret = os.getenv("SOVEREIGN_BUS_SECRET")
    if not secret:
        sys.stderr.write("ERROR: SOVEREIGN_BUS_SECRET must be set in environment.\n")
        return 1

    client_id = f"CommanderCLI_{uuid.uuid4().hex[:8]}"
    correlation_id = str(uuid.uuid4())
    event_queue: asyncio.Queue[EventPayload] = asyncio.Queue()

    client = NeuralBusClient(identity=client_id, endpoint=bus_url)

    async def _on_event(event: EventPayload) -> None:
        if event.correlation_id == correlation_id:
            await event_queue.put(event)

    for etype in [
        EventType.STATE_UPDATE.value,
        EventType.TASK_COMPLETED.value,
        EventType.TASK_FAILED.value,
        EventType.ERROR.value,
        EventType.INTENT_PARSED.value,
        EventType.DECISION_LOGGED.value,
    ]:
        client.register_handler(etype, _on_event)

    await client.start()
    # Allow registration frame to reach router
    await asyncio.sleep(0.05)

    payload = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="dr-anas-hilal",
        correlation_id=correlation_id,
        payload={
            "target_agent": agent,
            "message": message,
            "auth_token": os.getenv("COMMANDER_AUTH_TOKEN", "sovereign_commander_token_123"),
        },
    )

    sys.stdout.write(f"📡 Directive dispatched to '{agent}' [ID: {correlation_id[:8]}]...\n")
    sys.stdout.flush()
    await client.send(payload)

    completed = False
    exit_code = 0
    start_time = asyncio.get_event_loop().time()

    try:
        while not completed:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = timeout - elapsed
            if remaining <= 0:
                sys.stderr.write(f"\n❌ TIMEOUT: Agent '{agent}' did not complete within {timeout}s.\n")
                return 1

            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                sys.stderr.write(f"\n❌ TIMEOUT: Agent '{agent}' response timed out.\n")
                return 1

            etype = event.event_type
            pdata = event.payload

            if etype == EventType.INTENT_PARSED and verbose:
                sys.stdout.write(f"🧠 [Cognitive Gate] Inferred: {pdata.get('intent')} (Complexity: {pdata.get('complexity')})\n")
                sys.stdout.flush()

            elif etype == EventType.DECISION_LOGGED and verbose:
                sys.stdout.write(f"⚖️ [Decision Log] Task Hash: {pdata.get('task_hash')} -> {pdata.get('decision')}\n")
                sys.stdout.flush()

            elif etype == EventType.STATE_UPDATE:
                if "status_action" in pdata:
                    action_text = str(pdata.get("status_action")).strip()
                    sys.stdout.write(f"⏳ [{event.source_agent_id}] {action_text}\n")
                    sys.stdout.flush()
                elif "message" in pdata:
                    msg = str(pdata.get("message"))
                    # If this is a standalone final message without TASK_COMPLETED
                    if not pdata.get("is_intermediate", False):
                        sys.stdout.write(f"\n💬 [{event.source_agent_id}]:\n{msg}\n")
                        sys.stdout.flush()

            elif etype == EventType.TASK_COMPLETED:
                final_msg = pdata.get("message", "")
                if final_msg:
                    sys.stdout.write(f"\n💬 [{event.source_agent_id}]:\n{final_msg}\n")
                sys.stdout.write(f"✅ Directive completed successfully by '{event.source_agent_id}'.\n")
                sys.stdout.flush()
                completed = True
                exit_code = 0

            elif etype in (EventType.TASK_FAILED, EventType.ERROR):
                err_msg = pdata.get("error") or pdata.get("message") or "Unknown error"
                sys.stderr.write(f"\n❌ [{event.source_agent_id}] Task Failed: {err_msg}\n")
                completed = True
                exit_code = 1

    finally:
        await client.stop()

    return exit_code
```

---

## 6. Verification and Test Blueprint

To verify the synchronous interaction and bus bridge remediation without regressions:
1. **Unit Test for Synchronous CLI Dispatch (`tests/test_cli_sync.py`)**:
   - Mock/Local DEALER loop simulating agent response events:
     - Verify that intermediate `STATE_UPDATE` events trigger live output callbacks.
     - Verify that `TASK_COMPLETED` terminates the wait loop cleanly with exit code 0.
     - Verify that timeout raises expected error and terminates DEALER socket.
2. **UI Bridge Concurrency Test (`tests/test_ui_bridge_concurrency.py`)**:
   - Establish 10 concurrent WebSocket connections to `services/ui_bridge.py`.
   - Abruptly disconnect 3 connections.
   - Emit 50 rapid `STATE_UPDATE` frames on ZMQ bus.
   - Verify that all 7 surviving connections receive all 50 frames with zero frame drops.
   - Verify that the 3 dead connections are safely pruned without raising unhandled exceptions or blocking the loop.
3. **End-to-End Live Verification**:
   - Boot Matrix engine: `python matrix_main.py`.
   - Execute synchronous CLI: `python send_command.py --agent neo "Ping verification"`.
   - Confirm terminal outputs:
     1. `📡 Directive dispatched to 'neo' ...`
     2. `⏳ [neo] Thinking...`
     3. `💬 [neo]: <Text response>`
     4. `✅ Directive completed successfully by 'neo'.`
     5. Exit code 0.
