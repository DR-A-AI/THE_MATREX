@echo off
REM 🔧 Sovereign Matrix - Web Stack Diagnostic & Fix (Windows)
REM Diagnoses and fixes IGNITE_MATRIX.bat startup issues

setlocal enabledelayedexpansion
color 0E
cls

echo.
echo =============================================
echo.  SOVEREIGN MATRIX - WEB STACK DIAGNOSTIC
echo.
echo =============================================
echo.

REM Check 1: Ports
echo [1/6] Checking port availability...
echo.

for %%P in (5173 8000 5555) do (
    netstat -ano | findstr ":%%P" >nul 2>&1
    if !errorlevel! equ 0 (
        if %%P equ 5555 (
            echo   Port %%P ^(ZMQ^):      ^[ACTIVE^] - Matrix engine running
        ) else (
            echo   Port %%P:            ^[IN USE^] - Potential conflict
        )
    ) else (
        echo   Port %%P:            ^[FREE^] - Available
    )
)
echo.

REM Check 2: Dashboard setup
echo [2/6] Checking Dashboard setup...
if exist "dashboard\node_modules" (
    echo   ^[✓^] npm dependencies installed
) else (
    echo   ^[✗^] npm dependencies MISSING
    echo   ^ → Fix: cd dashboard ^&^& npm install
)
echo.

REM Check 3: Python dependencies
echo [3/6] Checking Python dependencies...
python -c "import uvicorn, fastapi, aiofiles" >nul 2>&1
if !errorlevel! equ 0 (
    echo   ^[✓^] FastAPI, Uvicorn, aiofiles installed
) else (
    echo   ^[✗^] Missing dependencies
    echo   ^ → Fix: pip install fastapi uvicorn aiofiles
)
echo.

REM Check 4: Dashboard env
echo [4/6] Checking dashboard environment...
if exist "dashboard\.env" (
    echo   ^[✓^] dashboard\.env exists
) else (
    echo   ^[!^] No dashboard\.env (optional)
)
if exist "dashboard\vite.config.js" (
    echo   ^[✓^] vite.config.js exists
) else (
    echo   ^[✗^] vite.config.js MISSING
)
echo.

REM Check 5: Firewall
echo [5/6] Checking Windows Firewall...
netsh advfirewall show allprofiles state 2>nul | findstr "ON OFF" >nul 2>&1
if !errorlevel! equ 0 (
    netsh advfirewall show allprofiles state 2>nul | findstr "ON" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   ^[!^] Firewall is ON - May need port exceptions
        echo   ^ → Ports to whitelist: 5173 ^(Vite^), 8000 ^(FastAPI^)
    ) else (
        echo   ^[✓^] Firewall is OFF or permissive
    )
) else (
    echo   ^[?^] Could not check firewall
)
echo.

REM Check 6: Browser connectivity test
echo [6/6] Testing backend endpoints...
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=2)" >nul 2>&1
if !errorlevel! equ 0 (
    echo   ^[✓^] UI Bridge ^(FastAPI^) is responding
) else (
    echo   ^[!^] UI Bridge not responding - May not be started yet
)
echo.

echo =============================================
echo.
echo FIXES TO TRY ^(in order^):
echo.
echo 1. Kill existing processes on port 5173:
echo    ^ → taskkill /F /IM node.exe
echo.
echo 2. Reinstall npm dependencies:
echo    ^ → cd dashboard ^&^& npm install
echo.
echo 3. Check Windows Firewall:
echo    ^ → Add exceptions for ports 5173 and 8000
echo.
echo 4. Test manually:
echo    ^ → Terminal 1: cd dashboard ^&^& npm run dev
echo    ^ → Terminal 2: python services/ui_bridge.py
echo    ^ → Browser: http://127.0.0.1:5173
echo.
echo 5. If still failing, check:
echo    ^ → Event Viewer for errors
echo    ^ → Dashboard vite.config.js for correct port
echo.
echo =============================================
echo.
pause
