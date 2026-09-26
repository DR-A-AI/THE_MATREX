# Task Assignment: Bus Architect & Integration Engineer — Milestone R5 (Crawler Audit & Skills Pipeline)

## Objectives
1. Read `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 126–134, 160–164).
2. Read `/mnt/e/matrex-dev/MASTER_PLAN.md` (§3.5, §6 CP-11) and `/mnt/e/matrex-dev/PROJECT.md` (§4.4, §4.5).
3. Read reference specification in `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md` and source in `/mnt/k/THE-MATRIX-V2/40-skills/loader.py`, `/mnt/k/THE-MATRIX-V2/40-skills/SKILL_CONTRACT.md`.
4. Check if `/mnt/e/matrex-dev/reports/B4_skill_inventory.md` exists. If present, incorporate findings; if absent, implement standard reference.

## Bus Schema Extension (`core/models.py`)
- Wire new `EventType` members in `core/models.py` ONLY:
  ```python
  SKILL_PROMOTED = "skill_promoted"
  SKILL_REVIEW_APPROVED = "skill_review_approved"
  ```
- Strict constraint: DO NOT modify existing EventPayload schema or alter the immutable key distribution topology.

## Skills Pipeline Implementation (`services/skill_loader.py`)
- Port `/mnt/k/THE-MATRIX-V2/40-skills/loader.py` as `services/skill_loader.py`:
  - 5-stage lifecycle: `DISCOVERED` -> `VALIDATED` -> `PREPARED` -> `PROMOTED` -> `INJECTED`.
  - Enforce `SKILL_CONTRACT` v1.0:
    * `contract_version == "1.0"`.
    * `allowed_tools` MUST be a subset of strictly 6 declarative tools:
      `{"docs.read", "memory.read", "memory.search", "planning.emit", "skills.discover", "skills.validate"}`.
    * Reject empty or "unknown" licenses.
    * Block offensive patterns (e.g. ransomware, password-crack, active-directory-attack).
  - Packaging: write manifests into `curated/{skill_id}`.
  - Quarantine: `validate_curated()` quarantines incomplete, corrupted, mismatched, or unverified packages into `quarantine/{package_id}`.
  - Review & Approval Gate:
    * Require dual review (`Smith` + `Morpheus`) emitting `EventType.SKILL_REVIEW_APPROVED` on the neural bus.
    * Commander approval required for `EventType.SKILL_PROMOTED`.
    * STRICT RULE: **No skill reaches INJECTED without SKILL_REVIEW_APPROVED bus event.**
  - Injection: declarative bindings only (`curated/{skill_id}/bindings.json`). NEVER executable code injected into Python memory.
  - Aegis QA Gate: `AsymmetricQA.verify()` integration on skill content.
  - Strict Python 3.10 typing, zero `shell=True`.

## Crawler Audit & Fix
- Check `core/librarian_crawler.py`: update residual hardcoded default path `r"J:\antigravity-awesome-skills-main"` to use `Path(os.getenv("MATRIX_ROOT", Path.cwd())) / "skills"`.
- Run and verify all 15 crawler integration tests:
  `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_crawlers_integration.py -v --no-cov` (must pass 15/15).

## Test Suite (`tests/test_skill_pipeline.py`)
- Write `tests/test_skill_pipeline.py` covering:
  1. Discovery of valid metadata (computes sha256 skill_id, stage DISCOVERED)
  2. Offensive skill blocked during discovery/validation
  3. Validation passes with valid contract and reviewer
  4. Validation fails on unknown allowed_tools (outside the 6 allowed tools)
  5. Validation fails on missing/unknown license
  6. Preparation creates manifests in curated directory
  7. Quarantine moves corrupted/tampered package to quarantine directory
  8. Promotion requires Commander approval and emits SKILL_PROMOTED event
  9. Injection fails if SKILL_REVIEW_APPROVED bus event was not emitted
  10. Injection succeeds when SKILL_REVIEW_APPROVED event is verified and writes bindings.json
  11. Bus schema verification: SKILL_PROMOTED and SKILL_REVIEW_APPROVED serialize properly in EventPayload

## Quality & Acceptance Verification
- Run:
  - `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_crawlers_integration.py -v --no-cov` (15/15 pass)
  - `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_skill_pipeline.py -v --no-cov` (all pass)
  - `.venv/bin/ruff check core/models.py services/skill_loader.py tests/test_skill_pipeline.py core/librarian_crawler.py`
  - `.venv/bin/python -m black --check core/models.py services/skill_loader.py tests/test_skill_pipeline.py core/librarian_crawler.py`
  - `.venv/bin/bandit -r services/skill_loader.py core/models.py`
  - `grep -r "shell=True" services/skill_loader.py core/models.py`
  - Full regression: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`
  - Aegis topology: `.venv/bin/python core/aegis_validator.py`

## Write Ownership
- Exclusively owns: `core/models.py`, `services/skill_loader.py`, `core/librarian_crawler.py`, `tests/test_skill_pipeline.py`.

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_r5_skills/handoff.md`.

## 2026-09-23T14:43:44Z
You are worker_r5_skills. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_r5_skills.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/worker_r5_skills/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, /mnt/e/matrex-dev/PROJECT.md, and /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_3/handoff.md.

Implement Milestone R5:
1. Update core/models.py: add SKILL_PROMOTED and SKILL_REVIEW_APPROVED to EventType enum ONLY. Maintain immutable key topology.
2. Port /mnt/k/THE-MATRIX-V2/40-skills/loader.py as services/skill_loader.py (5-stage lifecycle DISCOVERED -> VALIDATED -> PREPARED -> PROMOTED -> INJECTED, SKILL_CONTRACT v1.0, closed 6-tool allowlist, quarantine gate, dual-agent review approval bus event check, declarative bindings injection, Aegis QA integration).
3. Fix residual J:\ path in core/librarian_crawler.py to use MATRIX_ROOT/cwd fallback.
4. Verify crawler integration tests: SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest tests/test_crawlers_integration.py -v --no-cov (15/15 passed).
5. Write tests/test_skill_pipeline.py covering all 11 lifecycle and event scenarios.
6. Verify quality gates:
   - .venv/bin/python -m pytest tests/test_skill_pipeline.py -v --no-cov
   - .venv/bin/ruff check core/models.py services/skill_loader.py tests/test_skill_pipeline.py core/librarian_crawler.py
   - .venv/bin/python -m black --check core/models.py services/skill_loader.py tests/test_skill_pipeline.py core/librarian_crawler.py
   - .venv/bin/bandit -r services/skill_loader.py core/models.py
   - grep -r "shell=True" services/skill_loader.py core/models.py
   - Full regression: SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
   - Aegis topology: .venv/bin/python core/aegis_validator.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your handoff report to /mnt/e/matrex-dev/.agents/teamwork/worker_r5_skills/handoff.md and notify orchestrator when done.
