# Task Assignment: Integration Engineer — Milestone R3 (Safe Shell Execution)

## Objectives
1. Read `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 111–120, 150–155).
2. Read `/mnt/e/matrex-dev/MASTER_PLAN.md` (§3.3, §6 CP-07, CP-08, CP-09) and `/mnt/e/matrex-dev/PROJECT.md` (§4.2).
3. Read reference specification in `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2/handoff.md` and source in `/mnt/k/THE-MATRIX-V2/30-runtime/safe_shell_capabilities.py`.

## Implementation Requirements for `services/safe_shell.py`
- Write `services/safe_shell.py`:
  - Define custom exception classes: `SafeShellError`, `DisallowedCommandError`, `WorkspaceEscapeError`, `CommandTimeoutError`, `ScriptExecutionError`.
  - Constrain command allowlists:
    * Python: requires `-m <module>` where module is in `{"compileall", "pytest", "unittest"}`. Uses `sys.executable`.
    * Git: read-only subcommands `{"status", "log", "diff"}` and flags `{"--short", "--oneline", "-10", "--stat", "-n", "-s", "--name-only", "--name-status"}`.
    * CLI commands: `{"check", "verify", "models", "status", "run"}`.
  - Workspace scoping:
    * Resolves paths strictly against `workspace_root` (via `MATRIX_ROOT` or `cwd`).
    * Disallows NUL bytes (`\x00`) and path escapes (`..`, absolute paths outside workspace). Raises `WorkspaceEscapeError`.
  - Non-allowlisted command execution raises `DisallowedCommandError`.
  - Strict `shell=False` in every subprocess invocation. Zero `shell=True` anywhere.
  - Process isolation, timeout enforcement, output buffering/truncation.
  - Structured audit logging via `logging.getLogger("Sovereign.SafeShell")` and pluggable `audit_sink`.
  - Python 3.10 type annotations (`disallow_untyped_defs = true`).
  - Bandit `# nosec: B404, B603, B607` comments on subprocess imports and calls.

## Test Requirements for `tests/test_safe_shell.py`
- Write `tests/test_safe_shell.py` covering:
  1. Unknown command rejected and raises `DisallowedCommandError` (explicitly tested)
  2. Python compileall allowed with `sys.executable`
  3. Python pytest allowed
  4. Python disallowed module rejected (`DisallowedCommandError`)
  5. Python without `-m` flag rejected (`DisallowedCommandError`)
  6. Git status allowed
  7. Git write subcommands (`push`, `commit`, etc.) rejected (`DisallowedCommandError`)
  8. Workspace path traversal rejected and raises `WorkspaceEscapeError` (explicitly tested)
  9. NUL byte in path rejected (`WorkspaceEscapeError` or `ValueError`)
  10. Bash workspace script execution (valid script inside workspace)
  11. Nonexistent script raises `ScriptExecutionError` or `FileNotFoundError`
  12. CLI allowed commands validated
  13. CLI disallowed command rejected
  14. Audit logging calls `audit_sink` recording action, target, risk, result
  15. Timeout enforcement terminating hung process
  16. `shell=False` enforced in all executions (mock assertions)
  17. Tool definitions formatted for agent function calling

## Quality & Acceptance Verification
- Run:
  - `.venv/bin/python -m pytest tests/test_safe_shell.py -v --no-cov`
  - `.venv/bin/ruff check services/safe_shell.py tests/test_safe_shell.py`
  - `.venv/bin/python -m black --check services/safe_shell.py tests/test_safe_shell.py`
  - `.venv/bin/bandit -r services/safe_shell.py`
  - `grep -r "shell=True" services/safe_shell.py`
  - Full regression suite: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`

## Write Ownership
- Exclusively owns: `services/safe_shell.py`, `tests/test_safe_shell.py`.

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_r3_shell/handoff.md`.

## 2026-09-23T14:28:01Z
You are worker_r3_shell. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_r3_shell.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/worker_r3_shell/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, /mnt/e/matrex-dev/PROJECT.md, and /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2/handoff.md.

Implement Milestone R3:
1. Write services/safe_shell.py:
   - Exceptions: SafeShellError, DisallowedCommandError, WorkspaceEscapeError, CommandTimeoutError, ScriptExecutionError
   - Strict allowlists: python (-m compileall/pytest/unittest via sys.executable), git (status/log/diff), cli (check/verify/models/status/run)
   - Workspace scoping to workspace_root (MATRIX_ROOT or cwd), rejecting traversal and NUL bytes with WorkspaceEscapeError
   - Disallowed command raises DisallowedCommandError
   - Strict shell=False in every execution
   - Process isolation, timeout, output buffering
   - Structured audit logging via Sovereign.SafeShell logger and audit_sink
   - Strict Python 3.10 typing, Bandit # nosec: B404, B603, B607
2. Write tests/test_safe_shell.py covering all 17 scenarios.
3. Run and verify quality gates:
   - .venv/bin/python -m pytest tests/test_safe_shell.py -v --no-cov
   - .venv/bin/ruff check services/safe_shell.py tests/test_safe_shell.py
   - .venv/bin/python -m black --check services/safe_shell.py tests/test_safe_shell.py
   - .venv/bin/bandit -r services/safe_shell.py
   - grep -r "shell=True" services/safe_shell.py
   - Full regression: SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your handoff report to /mnt/e/matrex-dev/.agents/teamwork/worker_r3_shell/handoff.md and notify orchestrator when done.
