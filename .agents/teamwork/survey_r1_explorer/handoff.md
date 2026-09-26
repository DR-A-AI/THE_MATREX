# Handoff Report: Requirement R1 (Synchronous CLI Interaction & Bus Bidirectional Bridge)

**Agent**: `survey_r1_explorer`  
**Working Directory**: `/mnt/e/matrex-dev/.agents/teamwork/survey_r1_explorer/`  
**Target Milestone**: Survey & Architectural Investigation (Requirement R1)  
**Parent Orchestrator ID**: `099ee37a-35a6-4355-b6cd-a3dc0c99b104`  

---

## 1. Observation

Direct code observations from inspected files across `/mnt/e/matrex-dev`:

1. **Fire-and-Forget Termination in `send_command.py`**:
   - `send_command.py:38-39`:
     ```python
     await asyncio.sleep(0.5)
     await client.stop()
     ```
   - No event handler is registered on `client` (`send_command.py:20-21`). Handlers dictionary remains `{}`.
   - Client identity is statically hardcoded: `client = NeuralBusClient(identity="CommanderCLI", endpoint=bus_url)` (`send_command.py:20`).
2. **Absence of Inbound Processing in `NeuralBusClient` without Handlers**:
   - `core/neural_bus.py:127-129`:
     ```python
     handler = self.handlers.get(event_type_str)
     if handler:
         asyncio.create_task(handler(event))
     ```
   - In `send_command.py`, because no handler is registered, any event from the bus is silently ignored.
3. **Agent Completion Signaling & Missing `TASK_COMPLETED`**:
   - `core/models.py:18` defines `TASK_COMPLETED = "task_completed"`.
   - `services/ui_bridge.py:120` registers `bus_client.register_handler(EventType.TASK_COMPLETED.value, handle_agent_message)`.
   - Neither `agents/base_agent.py` nor `agents/neo_agent.py` ever emits `EventType.TASK_COMPLETED`. Both emit `EventType.STATE_UPDATE` for the final reply (`base_agent.py:428-434`, `neo_agent.py:667-673`):
     ```python
     reply = EventPayload(
         event_type=EventType.STATE_UPDATE,
         source_agent_id=self.name,
         correlation_id=event.correlation_id,
         payload={"message": response_msg},
     )
     await self.client.send(reply)
     ```
4. **Agent ID / Name Mismatch Bug**:
   - `agents/base_agent.py:270-274`:
     ```python
     thinking_msg = EventPayload(
         event_type=EventType.STATE_UPDATE,
         source_agent_id=self.agent_id, # UUID instead of self.name
         correlation_id=event.correlation_id,
         payload={"status_action": f"{self.name} IS WORKING... \n> Thinking..."},
     )
     ```
   - In `neo_agent.py:177`, `source_agent_id=self.name`.
   - In `dashboard/src/pages/ChatPage.jsx:62`, `setAgentStatuses(prev => ({...prev, [data.sender.toLowerCase()]: data.text}))`. When `sender` is a UUID, the UI fails to map status to active agents.
5. **WebSocket Loop Contention and Dead Socket Leak in `services/ui_bridge.py`**:
   - `services/ui_bridge.py:111-118`:
     ```python
     if send_lock:
         async with send_lock:
             for conn in list(active_connections):
                 try:
                     await conn.send_text(msg_str)
                 except Exception:
                     logger.exception("WebSocket send failed")
     ```
   - Broken/disconnected WebSockets log exceptions but are not purged from `active_connections`. Subsequent events continue attempting to send to dead sockets.
   - `send_lock` blocks concurrently running event deliveries.
   - Inbound correlation ID uses coarse second timestamp: `correlation_id=str(int(time.time()))` (`services/ui_bridge.py:178`).
6. **Router Purging on `EAGAIN` in `core/neural_bus.py`**:
   - `core/neural_bus.py:177-185`:
     ```python
     await self.socket.send_multipart([client, signature, msg_bytes], flags=zmq.NOBLOCK)
     ...
     except zmq.ZMQError as e:
         disconnected.append(client)
     ...
     for d in disconnected:
         self.active_clients.discard(d)
     ```
   - On transient buffer pressure (`EAGAIN`), the router drops the client identity from `self.active_clients`, causing permanent message starvation for that client.

---

## 2. Logic Chain

1. **Why `send_command.py` cannot synchronously receive responses**:
   - Direct Observation 1 shows `send_command.py` sleeps for 0.5s and calls `client.stop()`.
   - Direct Observation 2 shows `NeuralBusClient` requires explicit registration in `self.handlers` to process frames.
   - Ollama inference and agent tool execution take from 2 to 30+ seconds.
   - Therefore, the CLI process disconnects before any response is generated, and even if frames arrive within 500ms, they are silently dropped because no handler is registered.
2. **Why callers cannot distinguish task completion from intermediate thoughts**:
   - Direct Observation 3 shows that agents emit `EventType.STATE_UPDATE` for both intermediate thoughts/tool steps and final answers.
   - Neither agent emits `EventType.TASK_COMPLETED`.
   - Therefore, a synchronous listener cannot reliably distinguish an intermediate progress update from the final deliverable without ad-hoc payload key heuristic matching.
3. **Why UI status and WebSocket broadcast degrade under load**:
   - Direct Observation 4 shows `base_agent.py:271` emits UUID `self.agent_id` as `source_agent_id`, breaking frontend status mapping.
   - Direct Observation 5 shows `services/ui_bridge.py` retains failed WebSocket sockets in `active_connections` indefinitely and locks all sends with a single `asyncio.Lock()`.
   - Direct Observation 6 shows the central router drops clients permanently on transient `EAGAIN` exceptions.
   - Therefore, connection drops, frame loss, and loop stalls inevitably occur under bursty traffic or flaky client conditions.

---

## 3. Caveats

1. **Read-Only Scope**: In strict adherence to our read-only explorer mandate, no source code files (`send_command.py`, `base_agent.py`, `ui_bridge.py`, `neural_bus.py`) were modified during this investigation.
2. **Ollama Live Service Availability**: Live LLM inference latency depends on the host environment (WSL2 loopback to Windows Ollama service `:11434`). The CLI timeout must default to at least 60 seconds to accommodate cold model loading.
3. **External Dashboard Contracts**: Changes to the WebSocket message payload in `ui_bridge.py` must maintain backwards compatibility with `dashboard/src/pages/ChatPage.jsx`, which expects `{sender: str, text: str, type: 'status' | 'chat'}`.

---

## 4. Conclusion

Requirement R1 is fully analyzed, scoped, and ready for implementation.
The required technical roadmap consists of:
1. **Refactoring `send_command.py`**:
   - Implement dynamic identity (`CommanderCLI_<uuid8>`).
   - Register correlation queue for `STATE_UPDATE`, `TASK_COMPLETED`, `TASK_FAILED`, `ERROR`, `INTENT_PARSED`, and `DECISION_LOGGED`.
   - Add streaming terminal renderer for real-time status actions and final output.
   - Support both single-command execution and interactive mode with configurable timeout.
2. **Remediating `agents/base_agent.py` and `agents/neo_agent.py`**:
   - Fix `source_agent_id=self.name` bug at `base_agent.py:271`.
   - Emit explicit `EventType.TASK_COMPLETED` with `payload={"message": response_msg, "status": "success"}` and `EventType.TASK_FAILED` on failure.
3. **Hardening `services/ui_bridge.py`**:
   - Prune dead WebSockets on send failure.
   - Replace coarse `str(int(time.time()))` with `str(uuid.uuid4())`.
   - Register handlers for `ERROR` and `TASK_FAILED`.

Exhaustive code blueprints, sequence diagrams, and before/after specifications have been committed to:
`/mnt/e/matrex-dev/.agents/teamwork/survey_r1_explorer/analysis.md`

---

## 5. Verification Method

1. **Codebase Inspection**:
   - Verify `analysis.md` at `/mnt/e/matrex-dev/.agents/teamwork/survey_r1_explorer/analysis.md`.
   - Confirm line citations against `send_command.py:38`, `base_agent.py:270`, `ui_bridge.py:111`, and `neural_bus.py:177`.
2. **Unit Test Execution**:
   - Execute existing test suite:
     ```bash
     SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
     ```
   - Target result: 25/25 passing tests.
3. **Implementation Verification (Downstream Implementer)**:
   - When the implementation agent deploys the refactored `send_command.py`:
     ```bash
     SOVEREIGN_BUS_SECRET=test .venv/bin/python send_command.py --agent neo "Test status"
     ```
   - Must synchronously stream thinking status, display final response, and exit 0 without hanging or terminating prematurely.
