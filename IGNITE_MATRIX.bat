@echo off
title SOVEREIGN MATRIX - COMMAND NODE
color 0B

:: Enforce current directory in python path for all background tasks
set PYTHONPATH=%cd%

echo ======================================================================
echo          ///  SOVEREIGN MATRIX BOOT SEQUENCE INITIATED  ///
echo ======================================================================
echo.

echo [1/3] Powering up Holographic Dashboard (Vite Server)...
cd dashboard
start /B cmd /c "npm run dev"
cd ..
timeout /t 3 /nobreak >nul

echo [2/3] Igniting MCP Gateway (GitHub, Puppeteer, UI Nodes)...
start /B cmd /c "python services\mcp_gateway.py"
timeout /t 2 /nobreak >nul

echo [3/3] Booting Core Engine (Neural Bus, Watchdog, Librarian)...
echo.
echo ======================================================================
echo THE MATRIX IS ONLINE. AWAITING COMMANDER'S ORDERS.
echo ======================================================================
echo.

:: Run the core engine in the foreground so the Commander sees the logs
python matrix_main.py

pause
