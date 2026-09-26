# Progress — worker_zero_mock_engineer

Last visited: 2026-09-23T15:10:00Z

## Current Status
- Initializing task and assessing codebase.

## Plan
1. [ ] Audit production code for mock/stub/fake strings and remove them.
2. [ ] Fix `services/librarian.py:38` (AuthVault / real secret extraction).
3. [ ] Fix `core/zmq_hooks.py:42` (safe_shell / skill_loader real execution).
4. [ ] Verify `grep -rn "mock\|Mock\|MagicMock\|MOCK\|fake\|stub" services/ agents/ core/ --include="*.py"` returns 0 results (excluding nosec/dispatch).
5. [ ] Update `services/ollama_client.py` for WSL2 Windows host gateway IP & env var support.
6. [ ] Update `.env.example` with `OLLAMA_HOST` and `OLLAMA_DEFAULT_MODEL=llama3.2`.
7. [ ] Wire `llama3.2` into `agents/neo_agent.py` with graceful fallback and `shell=False`.
8. [ ] Write `tests/test_ollama_live.py` and `tests/test_neo_ollama.py`.
9. [ ] Implement real MCP server subprocess to replace `tests/fake_mcp_stdio_server.py`.
10. [ ] Update `tests/test_mcp_gateway.py` and `smoke_test_mcp.py` to use real MCP server.
11. [ ] Integrate real skill manifests from `/mnt/k/THE-MATRIX-V2/40-skills/curated/sk_7b8af088deda/` into `tests/test_skill_pipeline.py`.
12. [ ] Test `matrix_main.py` startup.
13. [ ] Run all verification gates (ruff, black, bandit, shell=True check, pytest).
14. [ ] Write `handoff.md` and notify parent.
