## 2026-09-23T06:41:38Z
Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_m1_1/.
You are Worker M1 (Remediation & Hardening Worker).
Your caller / orchestrator conversation ID is: a7ca307a-2740-4738-ad77-fb642eafc773.

MANDATORY FIRST STEP:
Read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md before doing any work.
Also read /mnt/e/matrex-dev/.agents/teamwork/orchestrator_1/PROJECT.md for architecture and contracts.
Read the findings from survey explorers:
- /mnt/e/matrex-dev/.agents/teamwork/explorer_survey_1/handoff.md (R1 & R5)
- /mnt/e/matrex-dev/.agents/teamwork/explorer_survey_2/handoff.md (R2 & R4)
- /mnt/e/matrex-dev/.agents/teamwork/explorer_survey_3/handoff.md (R3 & Diff)

WRITE OWNERSHIP:
You have exclusive write ownership of:
- services/ui_bridge.py
- agents/neo_agent.py
- core/zmq_hooks.py
- core/failsafe.py
- services/librarian.py
- core/models.py
- services/mcp_gateway.py
- core/librarian_crawler.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TASK IMPLEMENTATION REQUIREMENTS:
1. R1 Concurrency Hazard Remediation (`services/ui_bridge.py`):
   - In `broadcast_to_clients`, restore snapshot iteration: `for conn in list(active_connections):` under `async with send_lock:`.
   - In `websocket_endpoint`, guard uninitialized `bus_client`: `if bus_client is not None:` before `await bus_client.send(event)`.
   - In `lifespan`, ensure proper cleanup `if bus_client is not None: await bus_client.stop()`.
2. R3 Workspace Portability & Path Neutrality (`agents/neo_agent.py`):
   - Add `from pathlib import Path` at top imports.
   - Replace all 11 occurrences of hardcoded `J:\THE_MATRIX` (including lines 205-208, 221-222, 234-235, 247-248, 266-267, 283-284, 295, 331, and docstrings) with dynamic workspace resolution using `Path(os.getenv("MATRIX_ROOT", Path.cwd())).resolve()` and clean `Path` joins.
   - Delete the literal directory `'J:\THE_MATRIX\memory'` from disk if present.
3. R4 Security Audit & Comment Syntax Cleanup:
   - Normalize `# nosec` comment syntax in `core/zmq_hooks.py` (use plain `# nosec` on lines 19 and 68 to eliminate B104 tester warnings), `core/failsafe.py`, `services/librarian.py`, `agents/neo_agent.py`, `core/models.py`, `services/mcp_gateway.py`.
   - Ensure no prose text follows `# nosec` unless separated by a second `#` (e.g. `# nosec: B603  # explanation`).
4. R2 Code Formatting & Style Compliance:
   - Execute `.venv/bin/python -m black core agents services config tests matrix_main.py`.
   - Verify `.venv/bin/python -m black --check core agents services config tests matrix_main.py` reports 0 reformatting warnings (exit code 0).
   - Verify `.venv/bin/ruff check .` reports 0 errors (exit code 0).
5. R5 Test Suite Verification & Invariant Preservation:
   - Run `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`.
   - Ensure all 25 unit and integration tests pass 100% with 0 failures.
   - Verify `.venv/bin/bandit -r core/ services/ agents/ -x tests/` reports 0 issues and 0 warnings.
   - Preserve all architectural invariants (HMAC signing, key routing topology, emergency token stash limits, WindowsSelectorEventLoopPolicy).

DELIVERABLES:
1. Update /mnt/e/matrex-dev/.agents/teamwork/worker_m1_1/progress.md with timestamps.
2. Record full changes and diffs in /mnt/e/matrex-dev/.agents/teamwork/worker_m1_1/changes.md.
3. Provide a self-contained handoff report in /mnt/e/matrex-dev/.agents/teamwork/worker_m1_1/handoff.md following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification commands with full outputs).
4. Send a message to your caller (ID: a7ca307a-2740-4738-ad77-fb642eafc773) upon completion.
