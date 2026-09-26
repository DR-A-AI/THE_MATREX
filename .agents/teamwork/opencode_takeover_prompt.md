You are the OpenCode Lead Engineer for the Sovereign Matrix OS project. The AGY teamwork quota has been exhausted temporarily. You must take over as the primary execution engine.

## CONTEXT — What Was Done Before Interruption

The previous AGY agent team (Milestone 0) completed full architectural surveys and produced these deliverables, all saved on disk:
- `reports/PROJECT_ARCHITECTURE_BENCHMARK.md` (20KB) — complete truth gate and zero-mock criteria
- `.agents/teamwork/orchestrator_3/BRIEFING.md` — full orchestrator state and team roster
- `.agents/teamwork/orchestrator_3/plan.md` — the master plan with M1–M4 breakdown

**Survey findings (already completed, saved in each explorer's handoff):**
- R1: `send_command.py` closes after 0.5s with no inbound handler, no correlation tracking, missing `TASK_COMPLETED` lifecycle in `base_agent.py`
- R2/R4: Ollama model router has blocking calls on the asyncio loop; pre-warming pulse needed at boot; Vite(:5173)/FastAPI(:8000)/ZMQ(:5555) stack needs sync verification
- R3: All 4 MCP servers physically confirmed on disk (`/mnt/k/mcp/`), live stdio handshakes tested; `workspace.manifest.json` is present but NOT loaded by `services/mcp_gateway.py`

## YOUR MISSION

**Step 1 — Write a Status Report FIRST:**
Write `/mnt/e/matrex-dev/reports/OPENCODE_STATUS_REPORT.md` that covers:
- Summary of what was done before interruption (from the files above)
- Current state of each modified file (check git diff or wc -l)
- What M1–M4 need to do next
- Your team's plan of action

**Step 2 — Assemble your team:**
You MUST NOT work alone. Use `subagent_depth: 3` and recruit specialist subagents:
- A Python/asyncio expert for M1 (send_command.py bidirectional CLI) and M2 (pre-warming)
- An MCP protocol expert for M3 (mcp_gateway.py + workspace.manifest.json integration)
- A web stack engineer for M4 (ui_bridge.py + dashboard synchronization)
- A QA/Test engineer to run pytest and verify all fixes

**Step 3 — Execute M1–M4 in parallel where possible:**
Implement each requirement for real — NO MOCKS, NO STUBS:

### M1: Synchronous CLI (`send_command.py`)
- Add a ZMQ DEALER socket that waits for `STATE_UPDATE`/`TASK_COMPLETED` events
- Add correlation ID to match responses to sent commands
- Add timeout (60s) with graceful error message
- Print streamed response to terminal in real time

### M2: Engine Pre-Warming (Zero Cold Start)
- Add async pre-warm call to Ollama at `matrix_main.py` boot (before agents start)
- Ensure `services/ollama_client.py` uses `asyncio.to_thread` for blocking HTTP calls
- No direct `.sync()` or `requests.post` on the event loop

### M3: MCP Gateway + Workspace Manifest
- Modify `services/mcp_gateway.py` to auto-load `workspace.manifest.json` at startup
- Convert Windows paths (K:\\mcp\\) to WSL paths (/mnt/k/mcp/) automatically
- Register `matrix_shell`, `chrome_devtools`, `syncfusion`, `github` servers dynamically

### M4: Web Stack Sync Verification
- Verify `matrix_main.py`, `services/ui_bridge.py`, and `dashboard/` can boot together
- Fix any import or port conflict that prevents the 3-process stack from starting

**Step 4 — Run the verification gate:**
After each milestone:
- `SOVEREIGN_BUS_SECRET=x .venv/bin/python -m pytest tests/ -q --no-cov`
- `grep -r "shell=True" core/ agents/ services/` must return empty
- Check that `reports/opencode_lsp_mcp_audit.md` is written with LSP findings

**Step 5 — Write final report:**
Update `reports/OPENCODE_STATUS_REPORT.md` with full evidence of what was implemented and verified.

## Key Paths
- Working dir: `/mnt/e/matrex-dev`
- Python: `/mnt/e/matrex-dev/.venv/bin/python`
- OpenCode binary: `/home/AH/.bun/bin/opencode`
- Ollama: `http://127.0.0.1:11434`
- MCP servers: `/mnt/k/mcp/`
- Architecture benchmark: `/mnt/e/matrex-dev/reports/PROJECT_ARCHITECTURE_BENCHMARK.md`
- Orchestrator state: `/mnt/e/matrex-dev/.agents/teamwork/orchestrator_3/`

## Constraints (from SOVEREIGN_CONSTITUTION.md)
- ZERO `shell=True` anywhere in core/, agents/, or services/
- ZERO mocks — all implementations must be genuine
- New EventTypes go in `core/models.py` ONLY
- Do NOT touch the HMAC-signed Neural Bus topology
- Do NOT merge to `main` branch

BEGIN NOW with Step 1 (Status Report), then immediately assemble your team and start M1–M4.
