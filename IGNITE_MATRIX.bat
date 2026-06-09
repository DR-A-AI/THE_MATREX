@echo off
title SOVEREIGN MATRIX - COMMAND NODE
color 0B

:: Enforce current directory in python path for all background tasks
set PYTHONPATH=%cd%

echo ======================================================================
echo          ///  SOVEREIGN MATRIX BOOT SEQUENCE INITIATED  ///
echo ======================================================================
echo.

REM Kill any existing processes on ports 5173, 8000, 5555, and 5557 to avoid conflicts
echo [PRE-BOOT] Cleaning up old Matrix stack processes (ports 5173, 8000, 5555, 5557)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5173" ^| findstr /C:"LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":8000" ^| findstr /C:"LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5555" ^| findstr /C:"LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5557" ^| findstr /C:"LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [1/3] Powering up Holographic Dashboard (Vite Server on port 5173)...
cd dashboard
start "Sovereign Dashboard" cmd /k "npm run dev"
cd ..
timeout /t 5 /nobreak >nul

echo [2/3] Igniting MCP Gateway (GitHub, Puppeteer, UI Nodes)...
start "Sovereign MCP Gateway" cmd /k "python services\mcp_gateway.py"
timeout /t 2 /nobreak >nul

echo [3/3] Booting Core Engine (Neural Bus, Watchdog, Librarian)...
echo.
echo ======================================================================
echo THE MATRIX IS ONLINE. AWAITING COMMANDER'S ORDERS.
echo ======================================================================
echo.
echo 🌐 DASHBOARD: http://127.0.0.1:5173
echo 🔌 UI BRIDGE: http://127.0.0.1:8000
echo 🧠 NEURAL BUS: tcp://127.0.0.1:5555
echo.
echo ======================================================================
echo.

:: Run the core engine in the foreground so the Commander sees the logs
python matrix_main.py

pause
