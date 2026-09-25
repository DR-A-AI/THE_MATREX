@echo off
setlocal EnableDelayedExpansion

:: 0. Force working directory to project root and strip any trailing slash
set "MATRIX_DIR=%~dp0"
if "%MATRIX_DIR:~-1%"=="\" set "MATRIX_DIR=%MATRIX_DIR:~0,-1%"
cd /d "%MATRIX_DIR%"

title SOVEREIGN MATRIX - COMMAND NODE
color 0B

:: Enforce project root in python path for all background tasks
set "PYTHONPATH=%MATRIX_DIR%"
set "MATRIX_ROOT=%MATRIX_DIR%"

REM Groq pool keys live in project .env (gitignored, never commit).
REM matrix_main.py / ui_bridge.py load .env via load_dotenv() — no Desktop parsing here.
if not exist "%MATRIX_DIR%\.env" (
    echo [WARNING] .env not found — Groq pool will be empty (local Ollama only).
)

echo ======================================================================
echo          ///  SOVEREIGN MATRIX BOOT SEQUENCE INITIATED  ///
echo ======================================================================
echo Project Directory: %MATRIX_DIR%
echo.

:: 1. Check for dependencies
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
python -m pip install -r "%MATRIX_DIR%\requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Some Python dependencies could not be verified automatically.
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
cd /d "%MATRIX_DIR%\dashboard"
if not exist "node_modules\.bin\vite.cmd" (
    echo [INFO] Windows Vite binaries not found. Installing NPM dependencies on Windows...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install NPM dependencies.
    )
)
start "Sovereign Dashboard" /D "%MATRIX_DIR%\dashboard" cmd /k "npm run dev"
cd /d "%MATRIX_DIR%"
timeout /t 3 /nobreak >nul

echo [2/3] Igniting MCP Gateway and UI Bridge...
start "Sovereign MCP Gateway" /D "%MATRIX_DIR%" cmd /k "python services\mcp_gateway.py"
start "Sovereign UI Bridge" /D "%MATRIX_DIR%" cmd /k "python services\ui_bridge.py"
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
cd /d "%MATRIX_DIR%"
python matrix_main.py
if %errorlevel% neq 0 (
    echo [FATAL ERROR] Matrix Engine crashed with exit code %errorlevel%.
)

pause
