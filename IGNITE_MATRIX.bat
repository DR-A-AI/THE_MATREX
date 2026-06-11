@echo off
title SOVEREIGN MATRIX - COMMAND NODE
color 0B

:: Enforce current directory in python path for all background tasks
set PYTHONPATH=%cd%

echo ======================================================================
echo          ///  SOVEREIGN MATRIX BOOT SEQUENCE INITIATED  ///
echo ======================================================================
echo.

:: 0. Check for dependencies
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [FATAL ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [FATAL ERROR] NPM is not installed or not in PATH.
    pause
    exit /b 1
)

echo [PRE-BOOT] Checking Python dependencies...
python -m pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install some Python dependencies. The matrix might be unstable.
)

REM Kill any existing processes on ports 5173, 8000, 5555, and 5557 to avoid conflicts
echo [PRE-BOOT] Cleaning up old Matrix stack processes...
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
if not exist node_modules (
    echo [INFO] node_modules not found. Installing NPM dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install NPM dependencies.
    )
)
start "Sovereign Dashboard" cmd /k "npm run dev"
cd ..
timeout /t 5 /nobreak >nul

echo [2/3] Igniting MCP Gateway and UI Bridge...
start "Sovereign MCP Gateway" cmd /k "python services\mcp_gateway.py"
start "Sovereign UI Bridge" cmd /k "python services\ui_bridge.py"
timeout /t 2 /nobreak >nul

echo [3/3] Booting Core Engine (Neural Bus, Watchdog, Librarian, Neo, Trinity, Morpheus)...
echo.
echo ======================================================================
echo THE MATRIX IS ONLINE. AWAITING COMMANDER ORDERS.
echo ======================================================================
echo.
echo DASHBOARD  : http://127.0.0.1:5173
echo UI BRIDGE  : http://127.0.0.1:8000
echo NEURAL BUS : tcp://127.0.0.1:5555
echo.
echo ======================================================================
echo.

:: Run the core engine in the foreground so the Commander sees the logs
python matrix_main.py
if %errorlevel% neq 0 (
    echo [FATAL ERROR] Matrix Engine crashed with exit code %errorlevel%.
)

pause
