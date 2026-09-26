# Task Assignment: Global Quality Gate Reviewer — Phase 2 Verification

## Objectives
Execute and independently verify all Phase 2 Acceptance Criteria and Global Quality Gate checks across `/mnt/e/matrex-dev`.

## Quality Gate Commands to Execute and Verify
1. **Ruff Linter**:
   `.venv/bin/ruff check .` -> MUST be 0 errors.
2. **Black Formatter**:
   `.venv/bin/python -m black --check core agents services config tests matrix_main.py smoke_test_mcp.py` -> MUST be clean.
3. **Bandit Security**:
   `.venv/bin/bandit -r core/ services/ agents/ -x tests/` -> MUST be 0 High/Medium issues.
4. **Pytest Full Suite**:
   `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov` -> MUST pass 100% (>= 30 tests; expected ~94 tests).
5. **Shell Isolation Audit**:
   `grep -rn "shell=True" core/ agents/ services/` -> MUST return 0 matches.
6. **R2 Verification Command**:
   `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -c "from services.ollama_client import probe; print(probe())"` -> MUST exit code 0 without crash.
7. **R4 Smoke Test Command**:
   `.venv/bin/python smoke_test_mcp.py` -> MUST exit code 0 and print >=1 tool name.
8. **Aegis Topology Validator**:
   `.venv/bin/python core/aegis_validator.py` -> MUST exit code 0 (Sovereign Topology intact).
9. **Git State Verification**:
   Check current branch (`feat/engine-quality-and-bus-remediation`), commit log, and git status.

## Reviewer Verdict
- Must issue explicit verdict: `APPROVE` or `REQUEST_CHANGES`.
- Report all exact command outputs and evaluation in `/mnt/e/matrex-dev/.agents/teamwork/reviewer_phase2/handoff.md`.

## 2026-09-23T14:56:54Z
You are reviewer_phase2. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/reviewer_phase2.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/reviewer_phase2/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, and /mnt/e/matrex-dev/PROJECT.md.

Execute Global Quality Gate verification:
1. .venv/bin/ruff check .
2. .venv/bin/python -m black --check core agents services config tests matrix_main.py smoke_test_mcp.py
3. .venv/bin/bandit -r core/ services/ agents/ -x tests/
4. SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov
5. grep -rn "shell=True" core/ agents/ services/
6. SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -c "from services.ollama_client import probe; print(probe())"
7. .venv/bin/python smoke_test_mcp.py
8. .venv/bin/python core/aegis_validator.py
9. Check git branch and status.
Issue explicit verdict: APPROVE or REQUEST_CHANGES.

Write your report to /mnt/e/matrex-dev/.agents/teamwork/reviewer_phase2/handoff.md and notify orchestrator when done.

