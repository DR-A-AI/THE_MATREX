# SOVEREIGN MATRIX — Full-Session Delivery & Lessons Report
**Date:** 2026-09-25 (UTC) | **Branch:** `feat/engine-quality-and-bus-remediation`
**Committed:** `91fac60` (pushed to `origin/feat/...` — main-origin NEVER touched)
**Uncommitted follow-ups:** exist (listed §5) — review before second commit
**Mode path:** plan (read-only verify) → build (team execution) → live ops
**Team used:** Engineering Manager + Delivery Manager + Architect + Explore/Verifier + Backend Engineer + Debugger + Reviewer. Strict rule enforced: no agent works outside its specialty.

> No secrets below. Key names + fingerprints only. Values never printed.

---

## 1. Server verification (opening)
- Found all three down on Windows host (`netstat` empty, WSL `curl` 000). Relaunched from WSL in order matrix→bridge→vite with `PYTHONPATH=root`, `MATRIX_ROOT`, `SOVEREIGN_BUS_SECRET`.
- Proven: `:5555` TCP + `NeuralBusClient` connect, `:8000/api/health → {"status":"online","bus_connected":true}`, `:5173/THE_MATREX/ → 200`.
- Lesson: `ss -tlnp` inside WSL does NOT show Windows listeners — verify with `curl -v` + python sockets, never `ss` alone.

## 2. Previous-agent handover audit (plan mode, read-only)
- Files: `Handover/MASTER_HANDOVER_REPORT.md` (282 lines), `SESSION_RESUME_CHECKPOINT.md`, `STRIKE_FORCE_DELIVERY_REPORT.md`, root `HANDOVER.md` (FAILURE ADMITTED, still open textually), root `MASTER_HANDOVER_REPORT.md` (duplicate).
- Verdicts: 150/150, Ruff clean, Bandit 0 all re-verified live but had NO saved artifacts; `20/20` = `test_skill_pipeline.py` (not Groq); `5/5` = `test_groq_client.py`; `9.10s` build proven via brain task log `task-2980`; `USER_COMMAND` gap fixed in code but undocumented.
- Action taken: `Handover/evidence/2026-09-25/` created (`ruff.log`, `pytest-full.log` 155, `pytest-groq-10.log`, `pytest-skill-pipeline-20.log`, `bandit.log`, `vite-build-9.10s-archived.log`, `MANIFEST.md`). Root master duplicate deleted after byte-compare (Handover/ is source of truth per AGENTS.md).

## 3. agy conversation inspection (`51a5f80d-...`)
- Store: `~/.gemini/antigravity-cli/conversations/<id>.db` (sqlite, 3116 steps) + `brain/<id>/` (tasks logs, transcripts).
- Last tasks: vite build 9.10s, 20-suite, ruff+150 gate, handover heredocs. Older: failed live E2E (neo 180s timeout — background of HANDOVER.md), one intent test failure.
- Keys: NO `.env` files inside brain dirs (good), BUT transcripts contain live `gsk_` values (28+32 hits) → recommended Groq rotation (done §7). Brain master handover was byte-identical to project.

## 4. Groq pool unification (env-only) + account saga
- `services/groq_client.py` no longer scans Desktop; loads `GROQ_API_KEY_001/002/003` + legacy `GROQ_API_KEY` + email overrides, dedupes, masks (`gsk_***{last4}`). Tests rewritten to `monkeypatch.setenv` (10 tests).
- Saga: 003/hotmail cancelled from Groq (kept in non-Groq registrations, e.g. Clerk identity line); positional renumber ordered by Commander: **001=dranashilal, 002=r11salfd, 003=tarek** (verified by value fingerprints, NOT labels).
- Keys live in project `.env` (gitignored) — processes load via `load_dotenv()` (`matrix_main.py:5`, `ui_bridge.py:27`, `base_agent.py:18`). Launchers (`IGNITE_MATRIX.bat`, `start_stack_wsl.sh`) do ZERO Desktop key parsing.
- Flex behavior proven live: `flex → 400 → auto-downgrade → real completion in ~0.5s`.

## 5. Agent-intelligence repairs (the "stupid replies" complaint)
1. **Hypothetical disclaimers:** status path had no telemetry → added `core/status_telemetry.py` (TCP/HTTP probes; offline reported honestly as `غير متصل ❌`, proven by negative test on dead ports).
2. **Field mismatch (ROOT CAUSE of live failure):** UI sends `payload.command`, handler read only `payload.message` → empty string → `general_chat 0.00` → LLM garbage. Fixed unified `command or message` extraction (neo + base). Proven: `is_status_query('جاهز؟')=True` in-process while live routed `general_chat` — the mismatch explained it.
3. **Greedy hijack (second complaint — every question got same telemetry):** split detection: `is_readiness_ping()` (full-message, ≤8 words) = instant reply; broad `is_status_query()` = grounding only. Substantive audits/checks flow to tools.
4. **Generic AWS boilerplate:** added real `get_system_status` tool (telemetry+Groq pool masked+Ollama models), force-included for status queries + snapshot injected into prompt. First live call hit **GOVERNANCE LOCK** → added read-only allowlist (`get_system_status`, file reads) in `core/governance.py`; dangerous tools still HITL-gated. Live proof: "Verify active cloud accounts" answered with real acc_001/002/003 state.
5. **Model invents tool args:** `get_system_status(show_agent_status=...)` crashed (`TypeError`) → all zero-arg tools must accept `**_ignored`.
6. **Duplicates (user screenshot):** agent sends STATE_UPDATE+TASK_COMPLETED with identical text AND bridge forwarded both. Fixed at bridge (dedup 30s window + empty-frame drop) and UI (ChatPage last-message guard). Proven: exactly 1 reply per command. (An observed ar+en pair was TWO concurrent commands — user's own browser session + probe — not a bug.)
7. **Mixed-language garbage ("كيف" → Viet/EN mix):** system-prompt LANGUAGE RULE (reply strictly in commander's language).

## 6. Security hardening (C6, all scenarios, proven live)
- Router gates in `core/neural_bus.py`: HMAC (was broadcasting unsigned frames → SPOOFING storms), 1MiB cap, 60s TTL, 300/5s flood mute. Live: unsigned frame → single WARNING drop, 0 agent alerts.
- Commander auth: token tier ADDED then **cancelled per operator order** (passwordless localhost) — `.env` emptied, whitelist-only + 60s alert rate-limit. Live verified both phases.
- `tests/test_bus_security.py` (9 tests). Full suite: **174 passed**.
- C2 `config/settings.py`: rebuilt to model real `.env` keys (was 9 `extra_forbidden` errors on import).
- C5 CLERK PEM: 10-line fragile block → single-line escaped, byte-identical value, naive parsers work.
- C3 dist: rebuilt licensed (Syncfusion key hash-matched into bundle), fresh vs src.
- C1 Groq-in-.env: resolved. C4: scoped commit `91fac60` pushed to branch only.

## 7. Rotation executed
- Groq 001/002/003 rotated (prefixes nZG/uC5/bQv verified positionally), `.env` rewritten, engine restarted, live call `READY` in 0.51s.
- `COMMANDER_AUTH_TOKEN` cancelled (passwordless per order).

## 8. Current live state (end of session)
- PIDs: matrix 25844+, bridge 25930+, vite 25964+ (use `ps`; PIDs rotate on restart). Health: bridge `online`, dashboard 200, Ollama v0.34.4, Groq pool 3/3.
- Suite: 174 collected. Evidence: `Handover/evidence/2026-09-25/` (+ `live-neo-readiness-proof.log`, `vite-syncfusion-rebuild.log`).

## 9. OPEN / next agent must know
1. **Uncommitted follow-ups** (`git status` ~81 entries incl. pre-existing): token-cancellation, dedup, ping-narrowing, tool, governance allowlist, telemetry, settings, PEM line, `.env` values (ignored, fine). Review + second commit on the SAME branch. NEVER main.
2. `HANDOVER.md` (root) still textually admits failure — close it with E2E references now that the loop is proven.
3. `IGNITE_MATRIX.bat` edited blind from WSL — needs one Windows boot test.
4. Pre-existing LSP/pyright notes (`mcp_gateway.call_tool` typing) + 1.7MB chunk warning — cosmetic.
5. `governance/` PENDING files may accumulate from the lock era — sweep stale ones.
6. Old Desktop key files redundant (nothing reads them) — Commander's call to delete.

## 10. LESSONS (read before touching anything)
1. **Payload shape first:** UI sends `command`, agents read `message` — always reproduce with the EXACT live payload before theorizing.
2. **Tie-breaks kill:** `general_chat` first + strict `>` = new routes dead on 0.00 ties. Order routes deliberately; test ties explicitly.
3. **HITL vs autonomy:** read-only introspection must bypass approval or every status answer hangs on a lock file.
4. **Models invent args:** zero-arg tools MUST accept `**kwargs`; validate with a live tool-call test, not just unit.
5. **Duplicates have layers:** contract (two events) × forwarder (bridge) × renderer (StrictMode). Fix at forwarder + renderer; prove by counting WS frames.
6. **Tests inherit env:** `load_dotenv()` at import pulls REAL tokens into tests — isolate with `delenv` fixtures or tests flip behavior mysteriously.
7. **Tool-shells kill children:** agent-spawned background processes die on tool timeout — relaunch with `setsid` + verify in separate calls; `start_stack_wsl.sh` is for real terminals.
8. **Log TZ ≠ system TZ** (~5h offset observed) — correlate by content/correlation_id, not wall time.
9. **Evidence over claims:** every "fixed" needs a saved log + live probe output hyperlinked here; numbers without artifacts are rumors (this session's opening finding).
10. **Numbering by fingerprint, never by label:** account/key mapping verified by value hashes positionally — labels lie, positions drift, hashes don't.
11. **Ask once, sharply:** when directives conflict (003 ban vs positional order), present the two concrete readings with proof — don't guess twice.
12. **Zero-mock law is load-bearing:** probes, negative tests (dead ports → honest offline), masked logging (`gsk_***{last4}`), `.gitignore` for key files — the Aegis hook rejects the rest.
