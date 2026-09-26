#!/bin/bash
echo "Starting matrix_main.py in background..."
.venv/bin/python matrix_main.py > engine_test.log 2>&1 &
ENGINE_PID=$!
sleep 5 # Wait for engine to boot

echo "Sending command to Neo..."
.venv/bin/python send_command.py --agent neo "We need to read file"

echo "Waiting for response..."
sleep 15 # Wait for Neo to think and respond via Ollama

echo "Killing engine..."
kill $ENGINE_PID 2>/dev/null
sleep 2

echo "========== ENGINE LOGS =========="
cat engine_test.log
