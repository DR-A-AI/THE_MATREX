#!/usr/bin/env bash
# Antigravity Lifecycle Hook - Quality Gate
# PostToolUse contract: Read JSON from stdin, output "{}" on stdout

# Slurp stdin JSON context
INPUT_JSON=$(cat)

VENV_BIN="/mnt/e/matrex-dev/.venv/bin"
PROJECT_ROOT="/mnt/e/matrex-dev"

# Run Ruff check if ruff is available
if [ -x "$VENV_BIN/ruff" ]; then
    "$VENV_BIN/ruff" check "$PROJECT_ROOT/core" "$PROJECT_ROOT/services" "$PROJECT_ROOT/agents" >&2
elif command -v ruff &>/dev/null; then
    ruff check "$PROJECT_ROOT/core" "$PROJECT_ROOT/services" "$PROJECT_ROOT/agents" >&2
fi

# Strictly return valid JSON on stdout per Antigravity PostToolUse specification
echo "{}"
exit 0
