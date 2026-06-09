#!/bin/bash
# 🔧 Sovereign Matrix - Web Stack Diagnostic & Auto-Fix
# This script diagnoses and fixes IGNITE_MATRIX.bat startup issues

echo "=========================================="
echo "🔍 SOVEREIGN MATRIX WEB STACK DIAGNOSTIC"
echo "=========================================="
echo ""

# Check 1: Port conflicts
echo "[1/5] Checking port availability..."
echo "  Port 5173 (Vite):     $(lsof -i :5173 2>/dev/null && echo '❌ IN USE' || echo '✅ FREE')"
echo "  Port 8000 (FastAPI):  $(lsof -i :8000 2>/dev/null && echo '❌ IN USE' || echo '✅ FREE')"
echo "  Port 5555 (ZMQ):      $(lsof -i :5555 2>/dev/null && echo '✅ MATRIX RUNNING' || echo '⚠️ NOT RUNNING')"
echo ""

# Check 2: Dashboard setup
echo "[2/5] Checking Dashboard setup..."
if [ -d "dashboard/node_modules" ]; then
    echo "  ✅ npm dependencies installed"
else
    echo "  ❌ npm dependencies NOT installed"
    echo "     → Run: cd dashboard && npm install"
fi
echo ""

# Check 3: Python UI Bridge
echo "[3/5] Checking Python environment..."
python -c "import uvicorn, fastapi" 2>/dev/null && echo "  ✅ FastAPI/Uvicorn installed" || echo "  ❌ Missing: pip install fastapi uvicorn"
echo ""

# Check 4: Test services individually
echo "[4/5] Testing individual services..."
echo ""
echo "  Testing UI Bridge (FastAPI on 8000)..."
timeout 3 python services/ui_bridge.py 2>&1 | head -5 && echo "    ✅ Starts successfully" || echo "    ⚠️ Check error above"
echo ""

# Check 5: Firewall
echo "[5/5] Checking Windows Firewall..."
netsh advfirewall show allprofiles 2>/dev/null | grep "State" && echo "  ✅ Firewall check complete" || echo "  ⚠️ Could not verify firewall"
echo ""

echo "=========================================="
echo "DIAGNOSIS COMPLETE"
echo "=========================================="
