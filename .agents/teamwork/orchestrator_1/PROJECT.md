# Project: OpenCode Defect Remediation, Adversarial Audit & Quality Verification

## Architecture
- **System**: Sovereign Matrix (/mnt/e/matrex-dev)
- **Core Components**:
  - `services/ui_bridge.py`: FastAPI WebSocket gateway bridging browser clients to the ZMQ neural bus.
  - `core/neural_bus.py`: ZeroMQ ROUTER/DEALER bus with HMAC-SHA256 authenticated messaging.
  - `core/zmq_hooks.py`: ZMQ Router and Dealer socket wrappers for async RPC skill execution.
  - `core/failsafe.py`: FailsafeMonitor managing pre-danger git restore points and system stability.
  - `services/librarian.py` & `services/librarian_crawler.py`: Skill indexing and ephemeral token issuance.
  - `agents/neo_agent.py`: Neo agent providing local execution, filesystem tools, and Dark/Light commands.
  - `tests/`: 25 unit and integration tests across Sovereign Matrix invariants.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: UI Bridge Concurrency Hazard | Restore snapshot iteration `list(active_connections)` under `send_lock` in `services/ui_bridge.py:112`; guard uninitialized `bus_client` at line 176 | M1 | ORIGINAL_REQUEST § R1, Survey E1 |
| 2 | R2: Code Formatting & Style Compliance | Reformat code using Black (`line-length = 100`) across `core/zmq_hooks.py`, `core/failsafe.py`, `services/librarian.py`, `agents/neo_agent.py`; ensure `black --check` and `ruff check .` pass cleanly | M1 | ORIGINAL_REQUEST § R2, Survey E2 |
| 3 | R3: Workspace Portability & Path Neutrality | Replace hardcoded `J:\THE_MATRIX` in `agents/neo_agent.py` with `Path(os.getenv("MATRIX_ROOT", Path.cwd())).resolve()`; import `from pathlib import Path`; cleanup `'J:\THE_MATRIX\memory'` artifact | M1 | ORIGINAL_REQUEST § R3, Survey E3 |
| 4 | R4: Security Audit & Comment Syntax Cleanup | Normalize `# nosec` comment syntax across `core/zmq_hooks.py`, `core/failsafe.py`, `agents/neo_agent.py` to eliminate Bandit parser warnings; ensure bandit reports 0 issues and 0 warnings | M1 | ORIGINAL_REQUEST § R4, Survey E2 |
| 5 | R5: Test Suite Verification & Invariant Preservation | Pass 25/25 pytest suite with zero regressions; preserve HMAC signing, key routing topology, emergency token stash limits, and `WindowsSelectorEventLoopPolicy` | M1 | ORIGINAL_REQUEST § R5, Survey E1 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Defect Remediation & Invariant Hardening | Coordinated remediation across `services/ui_bridge.py`, `agents/neo_agent.py`, `core/zmq_hooks.py`, `core/failsafe.py`, `services/librarian.py`, formatting, bandit cleanup, and 25/25 test verification | Survey complete | DONE |

## Interface Contracts
### UI Bridge ↔ WebSocket Clients
- `broadcast_to_clients(message: dict)`:
  - Must take snapshot of `active_connections` via `list(active_connections)` under `async with send_lock:` to prevent concurrent connection modification errors.
- `websocket_endpoint(websocket: WebSocket)`:
  - If `bus_client is None`, must log error and safely handle message without crashing event loop.
  - In `lifespan`: ensure `if bus_client is not None: await bus_client.stop()` during shutdown.

### Neo Agent ↔ Local Workspace
- Workspace resolution:
  - Must import `from pathlib import Path`.
  - Must resolve workspace as `workspace_root = Path(os.getenv("MATRIX_ROOT", Path.cwd())).resolve()`.
  - All local file tool functions (`read_local_file`, `write_local_file`, `edit_local_file`, `list_local_dir`, `search_local_code`, `run_local_command`, `capture_screen`) must use `workspace_root` rather than hardcoded `J:\THE_MATRIX`.

### Bandit Suppressions ↔ Static Analysis
- Comment format:
  - `core/zmq_hooks.py:19, 68`: replace with plain `# nosec` to avoid B104 tester warnings on compound conditionals.
  - `core/failsafe.py`, `agents/neo_agent.py`, `services/librarian.py`: format `# nosec: Bxxx` or `# nosec: Bxxx, Byyy` without prose comments attached directly to test IDs (prose comments placed on preceding line or after secondary `#`).

## Code Layout
- `services/ui_bridge.py` — Owned exclusively by Worker for R1.
- `agents/neo_agent.py` — Owned exclusively by Worker for R2, R3, R4.
- `core/zmq_hooks.py` — Owned exclusively by Worker for R2, R4.
- `core/failsafe.py` — Owned exclusively by Worker for R2, R4.
- `services/librarian.py` — Owned exclusively by Worker for R2, R4.
- `core/librarian_crawler.py` — Owned exclusively by Worker for clean imports if needed.
