# Task Assignment: Integration Engineer — Milestone R2-Live (Real Ollama Integration Test & Neo Wiring)

## Objectives
Execute and pass Milestone R2-Live per the urgent directive from Sentinel / Commander:
Authoritative request: `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (under `## 2026-09-23T15:01:08Z`).

### Task 1: Discover Real Ollama Endpoint from WSL
- Discover the Windows host IP from WSL:
  - Query nameserver from `/etc/resolv.conf`: `cat /etc/resolv.conf | grep nameserver | awk '{print $2}'`
  - Probe: `curl -s http://<nameserver-ip>:11434/api/version` or `http://localhost:11434/api/version`
  - Check `OLLAMA_HOST` environment variable if set.
  - Document the correct WSL -> Windows host URL for reaching Ollama.
  - In `services/ollama_client.py`: Ensure `normalize_ollama_base_url()` supports the WSL2 Windows host gateway IP (and `OLLAMA_HOST` env var) in addition to `localhost`/`127.0.0.1`/`::1`, without permitting arbitrary external public domains.
  - Update `.env.example` with:
    ```
    OLLAMA_HOST=http://<windows-host-ip>:11434
    OLLAMA_DEFAULT_MODEL=llama3.2
    ```

### Task 2: Real Integration Test (`tests/test_ollama_live.py`)
- Author `tests/test_ollama_live.py`:
  - Uses `pytest.mark.skipif` to gracefully skip if Ollama is unreachable.
  - Calls `probe()` against the real service.
  - If service is reachable and `llama3.2` is present, calls `/api/chat` with `model="llama3.2"` and prompt "Say MATRIX_OK".
  - Asserts response contains non-empty text.

### Task 3: Wire llama3.2 into `agents/neo_agent.py`
- In `agents/neo_agent.py`:
  - When `OLLAMA_HOST` is configured and available, `NeoAgent` uses `services.ollama_client` (`OllamaClient` or `ModelRouter`) for completions/responses.
  - Falls back gracefully to existing behavior when Ollama is unavailable or unconfigured.
  - Enforce `shell=False` everywhere.
- In `tests/test_neo_ollama.py`:
  - Create a test suite mocking `OllamaClient` to verify the wiring into `NeoAgent` (completion invocation when available, graceful fallback when unavailable).

### Task 4: Quality Gate Verification
- Run:
  - `.venv/bin/python -m pytest tests/test_ollama_client.py tests/test_ollama_live.py tests/test_neo_ollama.py -v --no-cov`
  - `.venv/bin/ruff check services/ollama_client.py agents/neo_agent.py tests/test_ollama_live.py tests/test_neo_ollama.py`
  - `.venv/bin/python -m black --check services/ollama_client.py agents/neo_agent.py tests/test_ollama_live.py tests/test_neo_ollama.py`
  - `.venv/bin/bandit -r services/ollama_client.py agents/neo_agent.py`
  - `grep -r "shell=True" services/ agents/`
  - Full regression: `SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef .venv/bin/python -m pytest -q --no-cov`

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Report findings and test outputs in `/mnt/e/matrex-dev/.agents/teamwork/worker_r2_live/handoff.md`.

## 2026-09-23T15:03:06Z
Execute Milestone R2-Live:
1. Discover the real Ollama endpoint from WSL (e.g., check nameserver in /etc/resolv.conf, localhost, or OLLAMA_HOST). Document the discovered host URL.
2. In services/ollama_client.py: Ensure normalize_ollama_base_url() accepts the WSL2 Windows host gateway IP (and OLLAMA_HOST env var) in addition to 127.0.0.1/localhost.
3. Update .env.example with OLLAMA_HOST and OLLAMA_DEFAULT_MODEL=llama3.2.
4. Write tests/test_ollama_live.py: Real integration test calling probe() and /api/chat with model=llama3.2, skipping gracefully with pytest.mark.skipif if unreachable.
5. Wire llama3.2 into agents/neo_agent.py as an inference backend with graceful fallback. Write tests/test_neo_ollama.py verifying the wiring via mocks.
6. Verify all quality gates:
   - pytest tests/test_ollama_client.py tests/test_ollama_live.py tests/test_neo_ollama.py -v --no-cov
   - ruff check services/ollama_client.py agents/neo_agent.py tests/test_ollama_live.py tests/test_neo_ollama.py
   - black --check services/ollama_client.py agents/neo_agent.py tests/test_ollama_live.py tests/test_neo_ollama.py
   - bandit -r services/ollama_client.py agents/neo_agent.py
   - grep -r "shell=True" services/ agents/
   - Full regression: SOVEREIGN_BUS_SECRET=ci-fix-throwaway-0123456789abcdef pytest -q --no-cov

