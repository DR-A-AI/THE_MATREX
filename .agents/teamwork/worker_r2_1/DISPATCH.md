## 2026-09-23T07:28:44Z
Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_r2_1/.
You are Worker R2 (Layout Remediation & Exclusion Worker).
Your caller / orchestrator conversation ID is: a7ca307a-2740-4738-ad77-fb642eafc773.

MANDATORY FIRST STEP:
Read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md before doing any work.
Read /mnt/e/matrex-dev/.agents/teamwork/orchestrator_1/PROJECT.md and /mnt/e/matrex-dev/.agents/teamwork/explorer_r2_1/handoff.md.

WRITE OWNERSHIP:
You have write ownership of:
- pyproject.toml
- .agents/teamwork/challenger_m1_2/test_portability.py (deletion)
- .agents/teamwork/challenger_m1_1/stress_test_ws.py (deletion)
- .agents/teamwork/challenger_m1_1/stress_results.json (deletion)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TASK IMPLEMENTATION REQUIREMENTS:
1. Action 1 (Layout Compliance):
   - Delete all 3 non-metadata files from .agents/teamwork/:
     rm .agents/teamwork/challenger_m1_2/test_portability.py
     rm .agents/teamwork/challenger_m1_1/stress_test_ws.py
     rm .agents/teamwork/challenger_m1_1/stress_results.json
   - Verify that `find .agents -type f ! -name "*.md"` returns empty.
2. Action 2 (Defense-in-Depth):
   - In `pyproject.toml`, update `[tool.ruff] exclude`:
     Change:
     ```toml
     [tool.ruff]
     exclude = ["vendor", ".venv"]
     ```
     To:
     ```toml
     [tool.ruff]
     exclude = ["vendor", ".venv", ".agents"]
     ```
3. Action 3 (Clean up stray memory dir if present):
   - Check if literal `'J:\THE_MATRIX\memory'` or `'J:\THE_MATRIX'` exists on disk; remove if present: `rm -rf "J:\THE_MATRIX"`
4. Action 4 (Toolchain Verification):
   - Run: `.venv/bin/ruff check .` -> MUST pass with 0 errors (`All checks passed!`, exit code 0).
   - Run: `.venv/bin/python -m black --check core agents services config tests matrix_main.py pyproject.toml` -> MUST pass with 0 warnings (exit code 0).
   - Run: `.venv/bin/bandit -r core/ services/ agents/ -x tests/` -> MUST pass with 0 issues and 0 warnings (exit code 0).
   - Run: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov` -> MUST pass 25/25 tests (exit code 0).

DELIVERABLES:
1. Update /mnt/e/matrex-dev/.agents/teamwork/worker_r2_1/progress.md with timestamps.
2. Record changes in /mnt/e/matrex-dev/.agents/teamwork/worker_r2_1/changes.md.
3. Provide self-contained handoff in /mnt/e/matrex-dev/.agents/teamwork/worker_r2_1/handoff.md.
4. Send a message to your caller (ID: a7ca307a-2740-4738-ad77-fb642eafc773) upon completion.
