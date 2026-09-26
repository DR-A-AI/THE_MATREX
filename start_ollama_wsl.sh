#!/bin/bash
echo "Starting Ollama natively in WSL using Windows Models..."
export OLLAMA_MODELS=/mnt/e/OLLAMA

# Kill existing instance manually (since pkill isn't available)
PID=$(ps -ef | grep "ollama serve" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "Killing existing Ollama process ($PID)..."
    kill -9 $PID 2>/dev/null
fi

sleep 1

# Ensure the local bin path is correct for any user
OLLAMA_BIN="$HOME/.local/bin/ollama"
if [ ! -f "$OLLAMA_BIN" ]; then
    # Fallback if installed system-wide
    OLLAMA_BIN=$(which ollama 2>/dev/null)
fi

if [ -z "$OLLAMA_BIN" ] || [ ! -x "$OLLAMA_BIN" ]; then
    echo "Error: Ollama binary not found. Please ensure Ollama is installed in WSL."
    exit 1
fi

echo "Using Ollama binary at: $OLLAMA_BIN"

nohup "$OLLAMA_BIN" serve > ollama_wsl.log 2>&1 &
echo "Waiting for Ollama to boot..."
sleep 3
curl -s http://127.0.0.1:11434/api/tags | grep -q "llama3.2"
if [ $? -eq 0 ]; then
    echo "SUCCESS! Ollama is now running perfectly inside WSL on 127.0.0.1:11434"
else
    echo "FAILED to start Ollama in WSL. Check ollama_wsl.log for details."
fi
