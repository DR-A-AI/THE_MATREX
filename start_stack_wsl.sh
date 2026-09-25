#!/bin/bash
# Sovereign Matrix — WSL stack launcher (no secrets stored; loaded at runtime only).
# Usage: ./start_stack_wsl.sh  (from repo root)
# Starts: matrix_main (:5555) -> ui_bridge (:8000) -> vite (:5173), each backgrounded.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" MATRIX_ROOT="$ROOT"
# All secrets (SOVEREIGN_BUS_SECRET, GROQ_API_KEY_001/002/003, CLERK_*, ...)
# live in project .env (gitignored) and are loaded by the processes via
# load_dotenv(). This launcher sets PYTHONPATH/MATRIX_ROOT only.
export SOVEREIGN_BUS_SECRET="$(grep ^SOVEREIGN_BUS_SECRET .env | cut -d= -f2 | tr -d '\r"')"
mkdir -p logs
PY="$ROOT/.venv/bin/python"
nohup "$PY" matrix_main.py > logs/matrix_main.wsl.log 2>&1 &
echo "matrix: $!"
for _ in $(seq 1 30); do
  "$PY" -c "import socket;socket.create_connection(('127.0.0.1',5555),timeout=2).close()" 2>/dev/null && break || sleep 2
done
nohup "$PY" services/ui_bridge.py > logs/ui_bridge.wsl.log 2>&1 &
echo "bridge: $!"
for _ in $(seq 1 20); do
  curl -s -m 2 http://127.0.0.1:8000/api/health 2>/dev/null | grep -q online && break || sleep 2
done
curl -s -m 5 http://127.0.0.1:8000/api/health; echo
(cd dashboard && nohup ./node_modules/.bin/vite > ../logs/vite.wsl.log 2>&1 & echo "vite: $!")
sleep 9
curl -s -m 5 http://127.0.0.1:5173/THE_MATREX/ -o /dev/null -w "APP:%{http_code}\n"
