# Task Assignment: Integration Engineer — Milestone R2 (Ollama Integration)

## Objectives
1. Read `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 104–110, 145–149).
2. Read `/mnt/e/matrex-dev/MASTER_PLAN.md` (§3.2, §6 CP-04, CP-05, CP-06) and `/mnt/e/matrex-dev/PROJECT.md` (§4.1).
3. Read reference specification in `/mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2/handoff.md` and source in `/mnt/k/THE-MATRIX-V2/10-brain/model_router.py`.

## Implementation Requirements for `services/ollama_client.py`
- Write `services/ollama_client.py`:
  - Enforce loopback-only URLs (`localhost`, `127.0.0.1`, `::1` or `127.*`) in `normalize_ollama_base_url()`. Reject non-loopback IPs and HTTPS with `OllamaConfigurationError`.
  - Provide complete exception hierarchy (`OllamaError`, `OllamaConfigurationError`, `OllamaConnectionError`, `OllamaTimeoutError`, `OllamaHTTPError`, `OllamaProtocolError`, `OllamaModelNotFoundError`).
  - Implement stdlib `UrllibTransport` with injectable transport for tests.
  - Implement `OllamaClient`: `health()`, `tags()`, `model_names()`, `resolve_model()`, `has_model()`, `chat(model, messages, tools=None)`.
  - Implement `ModelRouter` mapping agent roles (`NEO`, `MORPHEUS`, `ORACLE`, `SMITH`, `GHOST`, `TRINITY`) to local models.
  - Fully decoupled from `cloud_provider.py` (safe import fallback, pure local operation).
  - Directly export `probe() -> tuple[int, dict[str, Any]]`:
    - Catches `OllamaError` and general exceptions; returns `(0, {...})` when ready or `(1, {...})` when unavailable. NEVER crashes.
  - Python 3.10 type annotations (`disallow_untyped_defs = true`).
  - Strictly `shell=False`. Zero `shell=True`.

## Test Requirements for `tests/test_ollama_client.py`
- Write `tests/test_ollama_client.py` with mock transports covering all required scenarios:
  1. Base URL normalization with valid loopback variants (`127.0.0.1:11434`, `localhost`, etc.)
  2. Rejection of external hosts (`10.0.0.1`, `192.168.1.1`, `example.com`, HTTPS)
  3. Rejection of empty/whitespace URL
  4. `probe()` success returning `(0, dict)` with `ready=True`
  5. `probe()` offline graceful returning `(1, dict)` with `ready=False` (no unhandled exception)
  6. Model discovery and alias resolution
  7. Model not found raises `OllamaModelNotFoundError`
  8. Chat success returning formatted response dict
  9. Chat empty messages raises `OllamaProtocolError`
  10. Bad/truncated JSON raises `OllamaProtocolError`
  11. Timeout raises `OllamaTimeoutError`
  12. HTTP 404/500 raises `OllamaHTTPError`
  13. Async chat on `ModelRouter`
  14. Zero `shell=True` check

## Quality & Acceptance Verification
- Run:
  - `.venv/bin/python -m pytest tests/test_ollama_client.py -v --no-cov`
  - `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -c "from services.ollama_client import probe; print(probe())"`
  - `.venv/bin/ruff check services/ollama_client.py tests/test_ollama_client.py`
  - `.venv/bin/python -m black --check services/ollama_client.py tests/test_ollama_client.py`
  - `.venv/bin/bandit -r services/ollama_client.py`
  - `grep -r "shell=True" services/ollama_client.py`
  - Full regression suite: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`

## Write Ownership
- Exclusively owns: `services/ollama_client.py`, `tests/test_ollama_client.py`.

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama/handoff.md`.

## 2026-09-23T14:28:01Z
You are worker_r2_ollama. Your working directory is /mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama.
Read your task assignment at /mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama/DISPATCH.md.
Also read /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md, /mnt/e/matrex-dev/MASTER_PLAN.md, /mnt/e/matrex-dev/PROJECT.md, and /mnt/e/matrex-dev/.agents/teamwork/spec_miner_phase0_2/handoff.md.

Implement Milestone R2:
1. Write services/ollama_client.py:
   - Loopback-only enforcement (normalize_ollama_base_url)
   - stdlib UrllibTransport with injectable transport
   - Full error taxonomy (OllamaError, OllamaConfigurationError, OllamaConnectionError, OllamaTimeoutError, OllamaHTTPError, OllamaProtocolError, OllamaModelNotFoundError)
   - OllamaClient (health, tags, model_names, resolve_model, has_model, chat)
   - ModelRouter (role mapping to local models, decoupled from cloud_provider)
   - Export probe() -> tuple[int, dict[str, Any]] (never crashes, catches OllamaError and exceptions, returns (0, dict) or (1, dict))
   - Strict Python 3.10 typing, zero shell=True.
2. Write tests/test_ollama_client.py covering all 14 scenarios using mock transports (deterministic, offline).
3. Run and verify quality gates:
   - .venv/bin/python -m pytest tests/test_ollama_client.py -v --no-cov
   - SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -c "from services.ollama_client import probe; print(probe())"
   - .venv/bin/ruff check services/ollama_client.py tests/test_ollama_client.py
   - .venv/bin/python -m black --check services/ollama_client.py tests/test_ollama_client.py
   - .venv/bin/bandit -r services/ollama_client.py
   - grep -r "shell=True" services/ollama_client.py
   - Full regression: SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your handoff report to /mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama/handoff.md and notify orchestrator when done.
