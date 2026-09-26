# Task Assignment: Phase 0 Spec Miner — Crawlers & Skills

## Objectives
Investigate:
1. `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (read this first)
2. `/mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py` (for R4 MCP)
3. `/mnt/k/THE-MATRIX-V2/40-skills/loader.py` and `/mnt/k/THE-MATRIX-V2/40-skills/SKILL_CONTRACT.md` (for R5 Skills)
4. `/mnt/e/matrex-dev/core/models.py` (EventType and EventPayload definitions, topology rules)
5. `/mnt/e/matrex-dev/tests/test_crawlers_integration.py`, `services/librarian.py`, `agents/assistant_crawler.py`, `agents/memory_crawler.py` (for R5 Crawlers)

Enumerate:
- R4 MCP requirements: How MCP tools are discovered, registered, and called; what non-interactive smoke test requires without external network.
- R5 Skill Pipeline requirements: Complete lifecycle (discover metadata-only -> validate SKILL_CONTRACT v1.0 -> quarantine bad -> curate good -> Aegis QA -> Smith+Morpheus SKILL_REVIEW_APPROVED event on bus -> INJECTED).
- R5 Bus Architect constraints: exact schema additions for `core/models.py:EventType` (SKILL_PROMOTED, SKILL_REVIEW_APPROVED) without altering immutable topology.
- R5 Crawler audit requirements: verification that assistant_crawler, memory_crawler, librarian_crawler start/process/stop cleanly and pass 15/15 crawler integration tests.

## Constraints & Scope
- Read-only exploration. DO NOT edit or create target files.
- Report all findings in `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md`.
- When finished, send a message to orchestrator with summary and handoff path.

## 2026-09-23T14:08:29Z
You are spec_miner_phase0_3. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md.
Investigate:
1. /mnt/k/THE-MATRIX-V2/30-runtime/mcp_gateway.py (for R4 MCP)
2. /mnt/k/THE-MATRIX-V2/40-skills/loader.py and /mnt/k/THE-MATRIX-V2/40-skills/SKILL_CONTRACT.md (for R5 Skills)
3. /mnt/e/matrex-dev/core/models.py (EventType/EventPayload schema and topology)
4. /mnt/e/matrex-dev/tests/test_crawlers_integration.py, services/librarian.py, agents/assistant_crawler.py, agents/memory_crawler.py (for R5 Crawlers)
Extract exact requirements for R4 MCP tool discovery and non-interactive offline smoke test; R5 skill pipeline lifecycle and bus events (SKILL_PROMOTED, SKILL_REVIEW_APPROVED in core/models.py); R5 crawler verification invariants.
Write your full findings to /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md.
When done, send a message to orchestrator with summary and report path.
