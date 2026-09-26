# Task Assignment: Phase 0 Planning Engineer

## Objectives
Synthesize the findings of the three Phase 0 Spec Miners (`spec_miner_phase0_1`, `spec_miner_phase0_2`, `spec_miner_phase0_3`) and write:
1. `/mnt/e/matrex-dev/MASTER_PLAN.md`
2. `/mnt/e/matrex-dev/PROJECT.md`

## Specifications to Include
- Detailed Task Breakdown for Phase 0 and Milestones R1 through R5.
- Explicit Team Assignments (Integration Engineer, Security Reviewer, Bus Architect, Crawler Auditor, Test Engineer).
- Sequencing & Dependency Graph (Phase 0 -> R1 -> R2 & R3 in parallel -> R4 & R5 in parallel -> Global Gate).
- Risk Map with mitigation strategies (concurrency, Windows selector loop policy, loopback isolation, shell injection, bus topology invariance).
- Verification Checkpoints and acceptance commands for every requirement.
- Full Feature Inventory merging all features discovered by spec miners.
- Interface Contracts for all new services (`services/ollama_client.py`, `services/safe_shell.py`, `services/mcp_gateway.py`, `services/skill_loader.py`).
- Code Layout and write ownership boundaries.

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Constraints & Scope
- Write `/mnt/e/matrex-dev/MASTER_PLAN.md` and `/mnt/e/matrex-dev/PROJECT.md`.
- Write your completion report to `/mnt/e/matrex-dev/.agents/teamwork/worker_phase0_plan/handoff.md`.
- When complete, send a message to orchestrator with summary and handoff path.

## 2026-09-23T14:16:15Z
You are worker_phase0_plan. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_phase0_plan.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/worker_phase0_plan/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md.
Read the three spec miner reports:
- /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_1/handoff.md
- /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2/handoff.md
- /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md

Write:
1. /mnt/e/matrex-dev/MASTER_PLAN.md: Task breakdown, team assignment, sequencing, risk map, verification checkpoints, Acceptance Criteria.
2. /mnt/e/matrex-dev/PROJECT.md: Project architecture, complete Feature Inventory (deduplicated across miners), Milestones table, Interface Contracts, Code Layout.

