## 2026-09-23T14:06:09Z

You are the Project Orchestrator (Team A Manager) for Phase 2 of Sovereign Matrix development.

Working directory: /mnt/e/matrex-dev/.agents/teamwork/orchestrator_2/
Project root: /mnt/e/matrex-dev
Authoritative request: /mnt/e/matrex-dev/.agents/teamwork/ORIGINAL_REQUEST.md (under ## 2026-09-23T14:02:49Z)
Initial context: /mnt/e/matrex-dev/.agents/teamwork/orchestrator_2/context.md

Mandate:
1. Initialize your BRIEFING.md, plan.md, and progress.md in your working directory. Keep progress.md continuously updated.
2. Full autonomous authorization is granted for all operations. Proceed without user intervention.
3. Act as Team A Manager. Decompose and dispatch to named specialist subagents running in parallel where possible:
   - Integration Engineer: Port Ollama + safe shell from /mnt/k/THE-MATRIX-V2
   - Security Reviewer: Enforce shell=False, run Bandit, block shell=True in every PR
   - Bus Architect: Wire new EventTypes in core/models.py ONLY, protect immutable topology
   - Crawler Auditor: Verify all crawlers start/stop cleanly, Aegis QA gate
   - Test Engineer: Write pytest suites for every new module before integration
4. Respect Team B parallel track: check /mnt/e/matrex-dev/reports/ for B1_phase1_commit.md, B2_opencode_config.md, B3_mcp_audit.md, B4_skill_inventory.md.
5. Phase 0 — Planning First (mandatory):
   Read /mnt/e/matrex-dev/AGENTS.md, /mnt/e/matrex-dev/SOVEREIGN_CONSTITUTION.md,
   /home/AH/.gemini/antigravity-cli/brain/78b62777-e870-4129-9930-7ca51741c1c7/HANDOFF_PHASE1_TO_PHASE2.md,
   and /mnt/k/THE-MATRIX-V2/DELIVERY_HANDOFF.md.
   Write /mnt/e/matrex-dev/MASTER_PLAN.md with task breakdown, team assignment, sequencing, risk map, and verification checkpoints.
   No agent starts implementation until MASTER_PLAN.md is complete.
6. Implement and verify requirements R1 through R5 as specified in the original request.
7. Ensure all Acceptance Criteria and Global Quality Gate pass:
   - ruff check . -> 0 errors
   - black --check core agents services config tests matrix_main.py -> clean
   - bandit -r core/ services/ agents/ -x tests/ -> 0 High/Medium
   - python -m pytest -q --no-cov -> >=30 tests, all pass
   - zero shell=True anywhere
8. HARD STOP: Do NOT merge to main. Stop when /mnt/e/matrex-dev/PHASE2_COMPLETE.md is written and verified.
9. Deliver full handoff and notify parent sentinel when complete so Victory Audit can be initiated.

## 2026-09-23T15:02:05Z

URGENT DIRECTIVE FROM SENTINEL / COMMANDER:

Before writing PHASE2_COMPLETE.md, you MUST execute and pass Milestone R2-Live (Real Ollama Integration Test):

The user reports that llama3.2 is installed at E:\OLLAMA\manifests\registry.ollama.ai\library\llama3.2 — this means Ollama runs as a Windows process, not inside WSL. The current R2 tests used mocks only. The real Ollama service is NOT running on localhost:11434 from WSL.

Required actions before PHASE2_COMPLETE.md:

1. DISCOVER the real Ollama endpoint from WSL:
   - Try: http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434/api/version
   - Try: OLLAMA_HOST environment variable
   - Document the correct WSL→Windows host URL for reaching Ollama

2. ADD to .env.example:
   OLLAMA_HOST=http://<windows-host-ip>:11434
   OLLAMA_DEFAULT_MODEL=llama3.2

3. WRITE a REAL integration test (tests/test_ollama_live.py) that:
   - Skips if Ollama is unreachable (pytest.mark.skipif)
   - Calls probe() against the real service
   - Calls /api/chat with model=llama3.2 and a simple prompt ("Say MATRIX_OK")
   - Asserts response contains text

4. WIRE llama3.2 into ONE agent (neo_agent.py preferred) as its inference backend:
   - When OLLAMA_HOST is set, agent uses ollama_client for completions
   - Falls back to existing behavior when Ollama unavailable
   - Add test_neo_ollama.py that mocks the client and verifies the wiring

5. Update GATE_STATUS.md with R2-Live results.

THEN write PHASE2_COMPLETE.md.

Do NOT mark Phase 2 complete or trigger Victory Audit without this — the user explicitly requires real model testing with llama3.2, not just mocks.
Recorded verbatim in ORIGINAL_REQUEST.md under ## 2026-09-23T15:01:08Z.

## 2026-09-23T15:06:05Z

🔴 SOVEREIGN COMMAND — IMMEDIATE EXECUTION REQUIRED 🔴

The user has issued an absolute sovereign directive. This overrides all current work:

COMMAND: ZERO MOCKS — REAL PHYSICAL INTEGRATION ONLY

Effective immediately:
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
Recorded in ORIGINAL_REQUEST.md under ## 2026-09-23T15:05:23Z.

## 2026-09-23T15:06:52Z

🔴 SOVEREIGN COMMAND UPDATE — SPECIFIC TARGETS IDENTIFIED:

Address ALL of these specific targets before PHASE2_COMPLETE.md:

CRITICAL — Production code with mocks:
1. services/librarian.py:38
   Contains: secret_data="EXTRACTED_SECRET_MOCK"
   → Replace with real secret extraction logic. If the secret comes from the neural bus KEY_INJECT event, wire it properly. No placeholder strings.

2. core/zmq_hooks.py:42
   Contains comment: "# Mock skill execution logic"
   → Implement real skill execution via safe_shell.py or skill_loader.py. No mock comments in production.

CRITICAL — Test infrastructure with fakes:
3. tests/fake_mcp_stdio_server.py
   → Replace with a REAL MCP server subprocess. Start a real MCP server (use the matrix_shell or github MCP from /mnt/e/matrex-dev/opencode.json or /mnt/k/mcp/) as a subprocess in conftest.py. Tests must call real MCP tool endpoints.

4. tests/test_ollama_client.py
   → All mock-based Ollama tests: keep unit tests for error cases (unreachable = real connection failure, not mocked). Add real integration tests in tests/test_ollama_live.py that call llama3.2 at the Windows host IP ($(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')):11434. Mark with @pytest.mark.live. Skip if unreachable but the call path must be real.

5. tests/test_mcp_gateway.py
   → Replace any fake/mock MCP calls with calls to a real MCP server subprocess started in conftest.py.

6. tests/test_skill_pipeline.py
   → Use REAL skill manifests from /mnt/k/THE-MATRIX-V2/40-skills/curated/sk_7b8af088deda/ instead of fake/synthetic manifests.

7. tests/test_crawlers_integration.py
   → Start REAL ZMQ bus (SOVEREIGN_BUS_SECRET=test), real crawlers as subprocesses or coroutines. No mocked ZMQ sockets.

MANDATORY VERIFICATION COMMANDS (must all pass and be documented in GATE_STATUS.md):
- Zero mocks in production code:
  grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py" | grep -v "# nosec" | grep -v "dispatch" → ZERO results
- Real Ollama probe (Windows host):
  OLLAMA_HOST=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434 SOVEREIGN_BUS_SECRET=test .venv/bin/python -c "from services.ollama_client import probe; import json; print(json.dumps(probe(), indent=2))"
- Real matrix_main.py startup test (5 second run):
  SOVEREIGN_BUS_SECRET=test timeout 5 .venv/bin/python matrix_main.py 2>&1 | tail -20
- Full test suite:
  SOVEREIGN_BUS_SECRET=test .venv/bin/python -m pytest -q --no-cov

Document ALL results in GATE_STATUS.md before writing PHASE2_COMPLETE.md.
Recorded in ORIGINAL_REQUEST.md under ## 2026-09-23T15:06:18Z.


