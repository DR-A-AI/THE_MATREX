# AGENTS.md — Sovereign Matrix

## Boot / entrypoints
- Core engine: `python matrix_main.py` — starts `NeuralBusRouter` + `Failsafe` + `SecureLibrarian` + `Memory/Assistant/Librarian` crawlers + 6 agents (neo, trinity, morpheus, smith, oracle, base). This is the real wiring; read it before touching startup order.
- Web stack (3 processes, fixed ports): Vite dashboard `:5173` + FastAPI `services/ui_bridge.py` `:8000` (`/ws`, `/api` proxied in `dashboard/vite.config.js`) + ZMQ bus `tcp://127.0.0.1:5555`. Windows launcher `IGNITE_MATRIX.bat` kills ports 5173/8000/5555/5557 first; for manual runs start in that order. Diagnose with `DIAGNOSTIC.bat` / `DIAGNOSTIC.sh`.
- `PYTHONPATH` must include repo root (`IGNITE_MATRIX.bat` sets `PYTHONPATH=%cd%`). Bare `python services/...` from another cwd breaks `core.*` imports.

## Env (required before anything runs)
- Copy `.env.example` → `.env`. `config/settings.py` (pydantic-settings, `.env` file) and `matrix_main.py` (`ZMQ_ROUTER_URL`, `ZMQ_BUS_URL`) read env at import/boot.
- `SOVEREIGN_BUS_SECRET` is **mandatory**: `core/neural_bus.py:19-23` raises `ValueError` at import if unset. No bus client/agent/test touching `neural_bus` works without it.
- Never commit `secrets/` or `.env` (gitignored). Never log full tokens — mask as `***{last4}` (established pattern in `agents/base_agent.py`, crawlers). See `SECURITY_VAULT.md`.

## Python toolchain
- Requires Python `>=3.10`; CI pins `3.10` (`.github/workflows/production_ci.yml`). `pip install -r requirements.txt`.
- Format/lint/typecheck: `black` (line-length 100, py310), `ruff check .`, `mypy` (`disallow_untyped_defs = true`), `bandit -r core/ services/ agents/ -x tests/`. CI runs exactly `ruff` → `bandit` → `pytest`.
- Pydantic v2 only: use `ConfigDict`, `model_dump(mode="json")`, `datetime.now(timezone.utc)` — one legacy `datetime.utcnow` reference remains at `core/models.py:72`, do not add new ones.

## Tests
- `pytest.ini` + `pyproject.toml` limit discovery to `tests/` (`python_files = tests/test_*.py`, `asyncio_mode = auto`). Root-level `test_*.py` / `e2e_test.py` / `load_test.py` are **not** collected — run them explicitly if needed.
- Full: `python -m pytest -q` (addopts force `--cov=. --cov-report=html --cov-report=term-missing`). Single: `python -m pytest tests/test_<name>.py -v --no-cov` (add `--no-cov` for speed; e.g. `tests/test_crawlers_integration.py` = 15 crawler tests).
- No Redis/Postgres needed for unit tests (SQLite-backed memory). Integration suites assume the ZMQ router from `matrix_main.py` flow is up.

## Windows quirk (load-bearing)
- ZMQ requires `WindowsSelectorEventLoopPolicy`, **not** Proactor. Already set in `matrix_main.py:101-103` and `tests/conftest.py`. Preserve it; do not "fix" the `DeprecationWarning` filter — it exists for Python 3.14+.

## Immutable architecture (`SOVEREIGN_CONSTITUTION.md` — do not redesign)
- `core/models.py:EventType` + `EventPayload` is the only bus schema (`use_enum_values=True`). New event types go there.
- `core/neural_bus.py`: DEALER clients ↔ ROUTER broadcast; every message HMAC-SHA256-signed with 16-byte nonce, 5s replay window, 60s TTL. `REGISTER` frames are not broadcast.
- Key topology is non-negotiable: Neo/Trinity only emit `TOKEN_EXTRACTED` (never store); only `AssistantCrawler` listens and broadcasts `KEY_INJECT`; agents keep `emergency_token_stash` (`MAX_STASH_SIZE=2`, 300s TTL in `agents/base_agent.py`) and must **not** JIT-request keys directly. Deleting stash/crawler or bypassing this breaks Aegis checks.
- Crawlers are async middleware (`CRAWLERS_SAFE_WORKFLOW.md`): file scans via `asyncio.to_thread`, path-traversal guard with `is_relative_to`, parameterized SQLite queries, Aegis QA gate on `def `/`import ` content. Never add sync I/O on the event loop.
- Agent replies to UI must be `STATE_UPDATE`/`TASK_COMPLETED` with `source_agent_id=<agent>` and `payload.message` — that is what `ui_bridge.py` forwards (`HANDOVER.md` gap is fixed in `base_agent.py:start()` via `USER_COMMAND` handler; keep it).

## Frontend / deploy
- Dashboard (`dashboard/`, React 19 + Vite 8 + Tailwind 4): `cd dashboard && npm install && npm run dev` / `npm run build` / `npm run lint`. `vite.config.js` `base: '/THE_MATREX/'` (GitHub Pages path) — don't change without updating `deploy-pages.yml`. Vercel build: `cd dashboard && npm install && npm run build`, output `dashboard/dist` (`vercel.json`).
- `terraform/` applies on push to `main` via OIDC (`azure_terraform.yml`); safe to read, do not hand-edit without a plan.
