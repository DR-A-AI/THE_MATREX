# Phase 2 Context & Mission Directives

## Authority and Scope
Full autonomous authorization is granted for Phase 2.
HARD STOP: Do NOT merge to `main`. Stop when `/mnt/e/matrex-dev/PHASE2_COMPLETE.md` is written and verified.

## User Request Reference
Authoritative user request is recorded in `/mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md` (under `## 2026-09-23T14:02:49Z`).

## Architecture & Constraints
- Read `/mnt/e/matrex-dev/AGENTS.md` and `/mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md` carefully.
- Read `/home/AH/.gemini/antigravity-cli/brain/78b62777-e870-4129-9930-7ca51741c1c7/HANDOFF_PHASE1_TO_PHASE2.md`.
- Read `/mnt/k/THE-MATRIX-V2/DELIVERY_HANDOFF.md`.
- Immutable architecture: `core/models.py` EventType/EventPayload is the only bus schema.
- NEVER use `shell=True`. Enforce `shell=False` everywhere.
- Maintain `.agents/teamwork/` metadata isolation: never place source code, test files, or data in `.agents/teamwork/`.
- Parallel Team B track: check `/mnt/e/matrex-dev/reports/` for B1_phase1_commit.md, B2_opencode_config.md, B3_mcp_audit.md, B4_skill_inventory.md.

## Urgent Mandatory Milestone: R2-Live (Real Ollama Integration Test)
Before writing PHASE2_COMPLETE.md, you MUST execute and pass Milestone R2-Live:
1. DISCOVER the real Ollama endpoint from WSL (e.g. nameserver host IP on port 11434).
2. ADD to .env.example: OLLAMA_HOST and OLLAMA_DEFAULT_MODEL=llama3.2.
3. WRITE a REAL integration test (tests/test_ollama_live.py) that skips if unreachable, probes real service, calls /api/chat with llama3.2 ("Say MATRIX_OK"), asserts response text.
4. WIRE llama3.2 into ONE agent (neo_agent.py preferred) with fallback, and write test_neo_ollama.py.
5. Update GATE_STATUS.md with R2-Live results.
THEN author PHASE2_COMPLETE.md.

## 🔴 SOVEREIGN COMMAND: ZERO MOCKS — REAL PHYSICAL INTEGRATION ONLY
This overrides all current work:
1. HALT all current workers. Audit everything already written.
2. FIND AND ELIMINATE every mock, fake, stub, patch, MagicMock, monkeypatch, fixture server, or simulated response in the ENTIRE codebase:
   - tests/fake_mcp_stdio_server.py → MUST be replaced with a REAL MCP server
   - Any unittest.mock, MagicMock, patch, monkeypatch in test files → REPLACE with real calls
   - Any hardcoded fake responses → REPLACE with real service calls
   - Run: grep -r "mock\|Mock\|MagicMock\|patch\|monkeypatch\|fake\|stub\|fixture" tests/ services/ agents/ core/ --include="*.py" -l
   - Document every file found
3. REPLACE every mock with real implementations:
   - Ollama tests → call real Ollama at Windows host (discover via /etc/resolv.conf nameserver):11434 with model llama3.2
   - MCP gateway tests → use a REAL running MCP server process (start it as subprocess in test setup, not a fake)
   - Crawler tests → start real ZMQ bus, real crawlers, real events
   - Shell tests → execute real allowlisted commands (git status, python --version) in real subprocess
   - Skill pipeline tests → use real skill manifests from /mnt/k/THE-MATRIX-V2/40-skills/curated/
4. VERIFY the final product is a USABLE SYSTEM:
   - python matrix_main.py must start without errors
   - All agents must connect to the bus successfully
   - Ollama (llama3.2) must respond to a real prompt through a real agent
   - MCP tools must be callable end-to-end
   - Skill pipeline must load real skills from /mnt/k/THE-MATRIX-V2/40-skills/curated/
5. Run final full test suite — every test must pass against REAL services (mark tests that require Ollama running with @pytest.mark.live and skip gracefully if service offline, but the code path must be real)
6. Write PHASE2_COMPLETE.md ONLY after:
   - grep for mock/Mock/MagicMock/patch/fake returns ZERO results in production code (services/, agents/, core/)
   - All integration tests use real services or real subprocess fixtures
   - matrix_main.py starts and agents connect successfully (verified by log output)
   - Ollama real call to llama3.2 succeeds at least once with real response documented

THIS IS NON-NEGOTIABLE. No mock = no completion. Real physical product only.

### Specific Audit Targets to Eliminate:
1. `services/librarian.py:38`: Replace `secret_data="EXTRACTED_SECRET_MOCK"` with real secret extraction from neural bus `KEY_INJECT` event.
2. `core/zmq_hooks.py:42`: Replace `# Mock skill execution logic` with real skill execution via `safe_shell.py` or `skill_loader.py`.
3. `tests/fake_mcp_stdio_server.py`: Replace with real MCP server subprocess started in `conftest.py`.
4. `tests/test_ollama_client.py`: Add real integration test `tests/test_ollama_live.py` calling real Ollama endpoint at Windows host IP (`$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434`) with model `llama3.2`.
5. `tests/test_mcp_gateway.py`: Replace fake MCP calls with real MCP server subprocess.
6. `tests/test_skill_pipeline.py`: Use real skill manifests from `/mnt/k/THE-MATRIX-V2/40-skills/curated/sk_7b8af088deda/`.
7. `tests/test_crawlers_integration.py`: Start real ZMQ bus, real crawlers.
8. Verify `matrix_main.py` startup test.
9. Verify `grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py"` returns 0 results.



