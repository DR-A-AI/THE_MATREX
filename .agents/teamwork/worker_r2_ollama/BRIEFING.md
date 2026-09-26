# BRIEFING — 2026-09-23T14:28:01Z

## Mission
Implement Milestone R2 (Ollama Integration): services/ollama_client.py, tests/test_ollama_client.py, probe(), ModelRouter, with loopback enforcement, zero shell=True, and quality gate verification.

## 🔒 My Identity
- Archetype: worker_r2_ollama
- Roles: implementer, qa, specialist
- Working directory: /mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama
- Original parent: fe5ac203-4cd6-4438-a176-a09d6bf8f404
- Milestone: R2 (Ollama Integration)

## 🔒 Key Constraints
- Loopback-only enforcement (localhost, 127.0.0.1, ::1, 127.*). Reject non-loopback IPs and HTTPS with OllamaConfigurationError.
- Stdlib UrllibTransport with injectable transport.
- Full error taxonomy (OllamaError, OllamaConfigurationError, OllamaConnectionError, OllamaTimeoutError, OllamaHTTPError, OllamaProtocolError, OllamaModelNotFoundError).
- OllamaClient (health, tags, model_names, resolve_model, has_model, chat).
- ModelRouter (role mapping to local models, decoupled from cloud_provider).
- Export probe() -> tuple[int, dict[str, Any]] (never crashes, catches OllamaError and exceptions, returns (0, dict) or (1, dict)).
- Strict Python 3.10 typing, zero shell=True.
- Exclusively owns: services/ollama_client.py, tests/test_ollama_client.py.
- DO NOT CHEAT: Genuine implementation, no hardcoded results or facades.

## Current Parent
- Conversation ID: fe5ac203-4cd6-4438-a176-a09d6bf8f404
- Updated: 2026-09-23T14:28:01Z

## Task Summary
- **What to build**: services/ollama_client.py and tests/test_ollama_client.py.
- **Success criteria**: 14 tests pass, probe() passes, ruff/black/bandit pass, no shell=True, full regression tests pass.
- **Interface contracts**: PROJECT.md §4.1, MASTER_PLAN.md §3.2, §6 CP-04, CP-05, CP-06, spec_miner_phase0_2/handoff.md.
- **Code layout**: services/ollama_client.py, tests/test_ollama_client.py.

## Change Tracker
- **Files modified**:
  - `services/ollama_client.py`: Loopback-enforced HTTP Ollama client, UrllibTransport, complete error taxonomy, ModelRouter, probe() entrypoint.
  - `tests/test_ollama_client.py`: 16 comprehensive unit tests covering all 14 scenarios.
- **Build status**: All quality gates and full regression tests PASS (exit code 0).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 16/16 unit tests passed in 0.34s; 58/58 full regression suite passed in 44.50s.
- **Lint status**: Ruff: 0 errors; Black: clean; Bandit: 0 issues (0 High, 0 Medium, 0 Low).
- **Tests added/modified**: 16 unit tests in `tests/test_ollama_client.py`.

## Loaded Skills
- None

## Key Decisions Made
- Used stdlib `urllib.request` inside `UrllibTransport` with injectable transport for offline deterministic testing.
- Handled IPv6 bracket normalization (`[::1]`, `::1:11434`, `[::1]:11434`) strictly within loopback rules.
- Fully decoupled `ModelRouter` from external `cloud_provider` via optional import fallbacks and default local-only operation.
- Guarded `probe()` against any unhandled exceptions, returning standard `(0, dict)` or `(1, dict)`.

## Artifact Index
- /mnt/e/matrex-dev/services/ollama_client.py — Primary Ollama client and router
- /mnt/e/matrex-dev/tests/test_ollama_client.py — Unit test suite (14 scenarios)
- /mnt/e/matrex-dev/.agents/teamwork/worker_r2_ollama/handoff.md — Final handoff report
