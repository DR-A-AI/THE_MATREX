# Changes Log — Worker R2

## Summary of Changes

### 1. Layout Compliance Remediations (.agents/teamwork Cleanup)
Deleted 3 non-metadata files from `.agents/teamwork/` to enforce strict layout adherence ("`.agents/teamwork/` must contain only metadata — source, tests, or data there is a violation"):
- Deleted `.agents/teamwork/challenger_m1_2/test_portability.py` (executable test script)
- Deleted `.agents/teamwork/challenger_m1_1/stress_test_ws.py` (executable test script)
- Deleted `.agents/teamwork/challenger_m1_1/stress_results.json` (raw benchmark results data)

Verification:
- `find .agents -type f ! -name "*.md"` returns empty (0 files).

### 2. Linter Exclusion Defense-in-Depth (`pyproject.toml`)
Updated `pyproject.toml`:
- Added `".agents"` to `[tool.ruff] exclude` list (`exclude = ["vendor", ".venv", ".agents"]`).
- Added `force-exclude = '''pyproject\.toml'''` to `[tool.black]` so Black does not attempt to parse TOML configuration as Python code when arguments include `pyproject.toml`.

### 3. Stray Disk Artifact Cleanup
- Removed stray `./J:\THE_MATRIX\memory` directory from disk (`rm -rf "J:\THE_MATRIX\memory"`).
- Verified with `find . -maxdepth 2 -name "*MATRIX*"` that no stray J: directory exists on disk.

### 4. Toolchain Verification
All toolchain commands executed and verified with exit code 0:
1. `.venv/bin/ruff check .` -> `All checks passed!` (exit code 0).
2. `.venv/bin/python -m black --check core agents services config tests matrix_main.py pyproject.toml` -> `41 files would be left unchanged.` (exit code 0).
3. `.venv/bin/bandit -r core/ services/ agents/ -x tests/` -> `No issues identified.` (exit code 0).
4. `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov` -> `25 passed, 1 warning in 44.43s` (exit code 0).
