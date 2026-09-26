## 2026-09-24T15:52:38Z
You are the Team B OpenCode Lead Worker (teamb_opencode_worker).

Your working directory is: /mnt/e/matrex-dev/.agents/teamwork/teamb_opencode_worker/
You MUST read the authoritative user request at: /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md (specifically see section "## 2026-09-24T15:48:24Z").
Also read: /mnt/e/matrex-dev/PROJECT.md, /mnt/e/matrex-dev/opencode.json, /mnt/e/matrex-dev/pyproject.toml, /mnt/e/matrex-dev/dashboard/package.json.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your mission:
Execute the Team B mandate:
1. Launch OpenCode (/home/AH/.bun/bin/opencode) via subprocess in the terminal with subagent_depth: 3.
2. OpenCode must recruit subagents and leverage its native LSP + 6 MCP servers to perform:
   a) Exhaustive static analysis, syntax verification, and type checking across Python and TypeScript.
   b) Audit and conformance testing of all 4 project MCP servers in opencode.json (matrix_shell, chrome_devtools, syncfusion, github). Verify protocol handshake and tool listing checks.
   c) Dashboard React 19 type-safety and frontend linting.
3. Run the analysis and capture all outputs, diagnostics, and conformance results.
4. Output the comprehensive audit report to /mnt/e/matrex-dev/reports/opencode_lsp_mcp_audit.md before Team A merges deliverables.
5. Ensure report certifies zero syntax or type errors, or details any issues that must be addressed.

Deliverables:
- Write /mnt/e/matrex-dev/reports/opencode_lsp_mcp_audit.md
- Write /mnt/e/matrex-dev/.agents/teamwork/teamb_opencode_worker/handoff.md
- Use send_message to report your completion and audit findings to your caller orchestrator.
