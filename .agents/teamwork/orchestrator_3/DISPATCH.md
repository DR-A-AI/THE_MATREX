## 2026-09-24T15:50:17Z

You are the Project Orchestrator (orchestrator_3) for the Sovereign Matrix project.

Working directory: /mnt/e/matrex-dev/.agents/teamwork/orchestrator_3/
Authoritative request: /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md (specifically see section "## 2026-09-24T15:48:24Z")
Project root: /mnt/e/matrex-dev

Your mission is to lead and coordinate the dual-track massive agent workforce to execute the comprehensive diagnostic audit and systemic architectural upgrade of the Sovereign Matrix agent environment (Matrix OS):

1. Dual-Team Protocol:
   - Team A (Teamwork Preview Multi-Agent Core): Core Python engine, Neural Bus, bridges (ui_bridge.py, mcp_gateway.py, factory.py), and Ollama local model integration. Specialist roles in agent-creator, agent-tool-builder, diagnosing-bugs, frontend-design, generative_ui, agent-orchestration-improve-agent, agent-orchestration-multi-agent-optimize.
   - Team B (OpenCode CLI via Subprocess): Launch OpenCode (/home/AH/.bun/bin/opencode) via subprocess in the terminal with subagent_depth: 3. Team B must recruit subagents and use native LSP + 6 MCP servers to perform static analysis, type checking, syntax/grammar verification, and MCP protocol auditing. Output reports to reports/opencode_lsp_mcp_audit.md before Team A merges deliverables.
   - Supreme Auditor (Oracle / Ghost research agent): Continuously benchmark all deliverables against PRODUCT_VISION.md, SOVEREIGN_CONSTITUTION.md, workspace.manifest.json, etc., ensuring 100% genuine execution with zero mocks. Generate reports/PROJECT_ARCHITECTURE_BENCHMARK.md.

2. Requirements to Fulfill:
   - R1: Synchronous CLI Interaction & Bus Bidirectional Bridge (send_command.py)
   - R2: Engine Latency & Pre-Warming (Zero Cold Start, non-blocking asyncio loop during Ollama tensor evaluation)
   - R3: Project MCP Gateway & Workspace Manifest Activation (workspace.manifest.json inside services/mcp_gateway.py, 4 project MCP tools)
   - R4: Complete Web Stack Synchronization (matrix_main.py :5555, services/ui_bridge.py :8000, dashboard/ :5173)

3. Acceptance Criteria:
   - Synchronous Interaction & Verification (CLI prints actual agent response, UI Bridge forwards STATE_UPDATE without dropping frames or blocking loop)
   - OpenCode (Team B) Verification (reports/opencode_lsp_mcp_audit.md certifying 0 syntax/type errors, MCP servers in opencode.json pass handshake and tool listing)
   - Engine & MCP Verification (automated test for mcp_gateway.py tools, engine boots clean and round-trip inference under 5s on warm model)
   - Research & Truth Gate (reports/PROJECT_ARCHITECTURE_BENCHMARK.md certifying 100% genuine execution with zero mocks)

Maintain your plan.md, progress.md, and BRIEFING.md in your working directory. Report progress regularly. When complete and verified, report completion to the Sentinel.
