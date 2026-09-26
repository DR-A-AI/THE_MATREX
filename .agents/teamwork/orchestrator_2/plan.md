# Sovereign Matrix Phase 2 Execution Plan

## Objectives
Execute Phase 2 development autonomously, adhering strictly to architectural invariants, zero shell=True, comprehensive test coverage, and clear role segregation.

## Phases & Milestones

### Phase 0: Survey & Planning First
1. Inspect Team B reports in `/mnt/e/matrex-dev/reports/` (`B1_phase1_commit.md`, `B2_opencode_config.md`, `B3_mcp_audit.md`, `B4_skill_inventory.md`).
2. Dispatch Explorer / Spec Miner to analyze:
   - `/mnt/e/matrex-dev/AGENTS.md`
   - `/mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md`
   - `/home/AH/.gemini/antigravity-cli/brain/78b62777-e870-4129-9930-7ca51741c1c7/HANDOFF_PHASE1_TO_PHASE2.md`
   - `/mnt/k/THE-MATRIX-V2/DELIVERY_HANDOFF.md`
   - Source code templates in `/mnt/k/THE-MATRIX-V2/`
3. Dispatch Worker to produce `/mnt/e/matrex-dev/MASTER_PLAN.md` and `/mnt/e/matrex-dev/PROJECT.md`.
4. Reviewer & Auditor gate on `MASTER_PLAN.md`.

### Milestone 1: R1 — Phase 1 Commit & Quality Verification
- Check status of Team B's `B1_phase1_commit.md`.
- If completed by Team B: Verify git branch `feat/engine-quality-and-bus-remediation` and commit log.
- If pending: Integration Engineer creates branch, stages, commits with specified message, and runs quality gates (Ruff, Black, Bandit, Pytest 25/25).

### Milestone 2: R2 — Ollama Integration
- Spec Miner / Explorer: analyze `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py`.
- Test Engineer: write `tests/test_ollama_client.py` covering available, unavailable, bad JSON, timeout, non-loopback rejection.
- Integration Engineer (Worker): port to `services/ollama_client.py` with loopback protection, error classification, zero downloads.
- Security Reviewer & Challenger: verify zero shell=True, Bandit clean, test suite passes.
- Auditor: integrity verification.

### Milestone 3: R3 — Safe Shell Execution
- Spec Miner / Explorer: analyze `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py`.
- Test Engineer: write `tests/test_safe_shell.py` covering allowlist enforcement, path traversal rejection, workspace scoping, timeout.
- Integration Engineer (Worker): port to `services/safe_shell.py` and wire into agent layer.
- Security Reviewer: strict check on `shell=False`, Bandit 0 issues, audit logging.
- Auditor: integrity check.

### Milestone 4: R4 — MCP Tool-Call Verification
- Check `/mnt/e/matrex-dev/reports/B3_mcp_audit.md`.
- Implement missing bridges/gaps identified.
- Non-interactive smoke test asserting >= 1 registered MCP tool is discovered and called without external network.

### Milestone 5: R5 — Crawler Audit and Skill Pipeline
- Check `/mnt/e/matrex-dev/reports/B4_skill_inventory.md`.
- Crawler Auditor: verify `assistant_crawler.py`, `memory_crawler.py`, `librarian_crawler.py` start/stop cleanly; verify `tests/test_crawlers_integration.py` (15/15).
- Bus Architect: add `SKILL_PROMOTED`, `SKILL_REVIEW_APPROVED` to `core/models.py:EventType` ONLY.
- Integration Engineer: port `/mnt/k/THE-MATRIX-V2/40-skills/loader.py` as `services/skill_loader.py` with quarantine, curation, Aegis QA, Smith+Morpheus approval.
- Test Engineer: write `tests/test_skill_pipeline.py`.
- Reviewer, Challenger, Auditor gate.

### Phase 6: Global Quality Gate & Final Deliverable
- Ruff: 0 errors
- Black check: clean across all core, agents, services, config, tests, matrix_main.py
- Bandit: 0 High/Medium issues
- Pytest: >= 30 tests, all pass
- Zero shell=True anywhere
- Worker writes `/mnt/e/matrex-dev/PHASE2_COMPLETE.md`
- Final Verification & Handover to parent sentinel for Victory Audit.
