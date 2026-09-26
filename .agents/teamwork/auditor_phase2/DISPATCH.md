# Task Assignment: Forensic Auditor — Phase 2 Global Integrity Audit

## Objectives
Perform an adversarial forensic integrity audit over all Phase 2 changes introduced across `/mnt/e/matrex-dev`.
Verify that all implementations are authentic, complete, robust, and free of shortcuts or integrity violations.

## Scope of Inspection
1. **Source Implementations**:
   - `services/ollama_client.py`: Verify authentic HTTP communication via stdlib urllib transport, loopback address validation, model router mapping, error taxonomy, non-crashing `probe()`.
   - `services/safe_shell.py`: Verify authentic subprocess execution with `shell=False`, strict allowlists (Python, Git, CLI, Bash), workspace scoping with `WorkspaceEscapeError`, custom exceptions, structured audit logging.
   - `services/mcp_gateway.py`: Verify authentic stdio JSON-RPC 2.0 gateway, process lifecycle, launcher allowlist, schema validation, risk/approval escalation, payload size limits.
   - `services/skill_loader.py`: Verify authentic 5-stage lifecycle, closed 6-tool allowlist, quarantine mechanism, dual-agent bus event `SKILL_REVIEW_APPROVED` check, declarative bindings, AsymmetricQA integration.
   - `core/models.py`: Verify exact additions to `EventType` (`SKILL_PROMOTED`, `SKILL_REVIEW_APPROVED`) and zero alterations to existing key routing topology or schemas.
   - `core/librarian_crawler.py`: Verify portable path resolution.

2. **Integrity Forensics & Prohibitions (Zero Tolerance)**:
   - Check for hardcoded test strings or dummy mocks in production source files (`services/`, `core/`, `agents/`).
   - Check for `shell=True`: `grep -rn "shell=True" core/ agents/ services/` MUST be completely empty.
   - Check that no skill reaches `INJECTED` without `SKILL_REVIEW_APPROVED` bus event.
   - Check that `SOVEREIGN_CONSTITUTION.md` and `AGENTS.md` invariants are strictly preserved (HMAC signing, key distribution topology, emergency token stash limit=2/300s TTL).

3. **Auditor Verdict**:
   - Must issue explicit verdict: `CLEAN` or `INTEGRITY VIOLATION`.
   - If `CLEAN`, provide detailed evidence chain.
   - Report findings in `/mnt/e/matrex-dev/.agents/teamwork/auditor_phase2/handoff.md`.

## 2026-09-23T14:56:53Z
You are auditor_phase2. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/auditor_phase2.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/auditor_phase2/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, and /mnt/e/matrex-dev/PROJECT.md.

Perform forensic integrity audit:
1. Examine services/ollama_client.py, services/safe_shell.py, services/mcp_gateway.py, services/skill_loader.py, core/models.py, core/librarian_crawler.py.
2. Verify zero cheating, zero hardcoding of test outputs, zero facade/dummy implementations.
3. Verify grep -rn "shell=True" core/ agents/ services/ is completely empty.
4. Verify SKILL_REVIEW_APPROVED bus event enforcement before INJECTED stage.
5. Verify preservation of immutable key distribution topology and Aegis rules.
6. Issue explicit verdict: CLEAN or INTEGRITY VIOLATION.

Write your report to /mnt/e/matrex-dev/.agents/teamwork/auditor_phase2/handoff.md and notify orchestrator when done.
