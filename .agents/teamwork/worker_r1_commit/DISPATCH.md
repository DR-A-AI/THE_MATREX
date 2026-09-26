# Task Assignment: Integration Engineer — Milestone R1 (Phase 1 Commit & Verification)

## Objectives
1. Read `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (specifically lines 87–102 and 138–144).
2. Read `/mnt/e/matrex-dev/MASTER_PLAN.md` and `/mnt/e/matrex-dev/PROJECT.md`.
3. In `/mnt/e/matrex-dev`:
   - Create and checkout branch `feat/engine-quality-and-bus-remediation`:
     `git checkout -b feat/engine-quality-and-bus-remediation`
   - Stage all modified files, staged deletions, and root documents (`MASTER_PLAN.md`, `PROJECT.md`). Do NOT stage `.agents/`.
   - Commit with the exact verbatim commit message:
```
chore(core): Phase 1 complete — audit remediation, portability, style compliance

- Fix WebSocket broadcast race condition (list snapshot under send_lock)
- Fix shell injection in neo_agent.py (shell=True → shlex.split)
- Eliminate all J:\THE_MATRIX hardcoded paths across 5 modules
- Add os import + MATRIX_ROOT/MATRIX_MEMORY_ROOT env resolution
- Black/Ruff/Bandit: all green (0 issues, 3159 LOC)
- Pytest: 25/25 passed
- Add msgpack, Pillow, mss, aiofiles, google-genai to requirements.txt
- Expand .gitignore: .vs/, .coverage, htmlcov/, *.db
- Consolidate [tool.ruff] exclude in pyproject.toml
```
   - Attempt push to origin: `git push -u origin feat/engine-quality-and-bus-remediation` (if push fails due to network/credentials, document it clearly).
4. Run all quality gate commands and capture exact outputs:
   - `.venv/bin/ruff check .`
   - `.venv/bin/python -m black --check core agents services config tests matrix_main.py`
   - `.venv/bin/bandit -r core/ services/ agents/ -x tests/`
   - `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`
   - `grep -r "shell=True" core/ agents/ services/`
   - `.venv/bin/python core/aegis_validator.py`

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Constraints & Scope
- Exclusive ownership: git branch and commit operations for Milestone R1.
- Report all command outputs and git log in `/mnt/e/matrex-dev/.agents/teamwork/worker_r1_commit/handoff.md`.
- Send message to orchestrator when complete.

## 2026-09-23T14:19:39Z
You are worker_r1_commit. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_r1_commit.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/worker_r1_commit/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, and /mnt/e/matrex-dev/PROJECT.md.

Execute Milestone R1:
1. Create and checkout git branch feat/engine-quality-and-bus-remediation.
2. Stage all modified files, pycache deletions, MASTER_PLAN.md, PROJECT.md (exclude .agents/).
3. Commit with the required verbatim message:
chore(core): Phase 1 complete — audit remediation, portability, style compliance

- Fix WebSocket broadcast race condition (list snapshot under send_lock)
- Fix shell injection in neo_agent.py (shell=True → shlex.split)
- Eliminate all J:\THE_MATRIX hardcoded paths across 5 modules
- Add os import + MATRIX_ROOT/MATRIX_MEMORY_ROOT env resolution
- Black/Ruff/Bandit: all green (0 issues, 3159 LOC)
- Pytest: 25/25 passed
- Add msgpack, Pillow, mss, aiofiles, google-genai to requirements.txt
- Expand .gitignore: .vs/, .coverage, htmlcov/, *.db
- Consolidate [tool.ruff] exclude in pyproject.toml
4. Attempt git push -u origin feat/engine-quality-and-bus-remediation.
5. Run all quality gate commands (Ruff, Black check, Bandit, Pytest 25/25 with SOVEREIGN_BUS_SECRET, grep shell=True, aegis_validator.py).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your full handoff report to /mnt/e/matrex-dev/.agents/teamwork/worker_r1_commit/handoff.md and notify orchestrator when done.
