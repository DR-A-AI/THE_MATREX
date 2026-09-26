# Task Assignment: Integration Engineer — Zero Mock Audit & Physical Endpoint Discovery

## Objectives
Execute Step 1 & 2 of the Sovereign Directive: "ZERO MOCKS — REAL PHYSICAL INTEGRATION ONLY".

1. **Grep and Catalog Every Mock Across the Entire Codebase**:
   Run:
   `grep -rnE "(unittest\.mock|MagicMock|patch\(|monkeypatch|from unittest import mock|import mock)" tests/ services/ agents/ core/`
   `grep -rnE "(fake|stub|fixture_server)" tests/ services/ agents/ core/`
   Document every file found, the lines, and what is mocked.

2. **Discover the Real Windows Host Ollama Endpoint from WSL**:
   - Get the host IP:
     `cat /etc/resolv.conf | grep nameserver | awk '{print $2}'`
   - Test connectivity to Ollama on Windows:
     `curl -s -m 3 http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434/api/version`
     `curl -s -m 3 http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434/api/tags`
     `curl -s -m 3 http://127.0.0.1:11434/api/version`
     `curl -s -m 3 http://localhost:11434/api/version`
   - Verify if `llama3.2` is present in the tags.
   - Test a real chat call:
     `curl -s -X POST http://<ip>:11434/api/chat -d '{"model": "llama3.2", "messages": [{"role": "user", "content": "Say MATRIX_OK"}], "stream": false}'`
   - Document the exact Windows host IP, URL, and curl output.

3. **Discover Real MCP Servers Available in Environment**:
   - Check MCP servers in `/home/AH/.gemini/antigravity-cli/mcp/` or node/npx or python modules:
     Check `which npx`, `which node`, `which uvx`, `which python3`.
     Check schemas in `/home/AH/.gemini/antigravity-cli/mcp/`.
     Check if a standard MCP server can be launched (e.g. via python script or standard tool).
   - Document how a real running MCP server can be used without `fake_mcp_stdio_server.py`.

4. **Inspect Real Skills in `/mnt/k/THE-MATRIX-V2/40-skills/curated/`**:
   - List files in `/mnt/k/THE-MATRIX-V2/40-skills/curated/`.
   - Document package manifests, source manifests, and bindings.

5. **Deliver Report**:
   Write `/mnt/e/matrex-dev/.agents/teamwork/worker_demock_audit/handoff.md`.
