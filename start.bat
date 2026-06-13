@echo off
chcp 65001 >nul 2>&1

echo ========================================
echo    Mining Agent System - Launcher
echo ========================================
echo.

REM Check Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python and add to PATH
    pause
    exit /b 1
)

REM Check dependencies
echo [INFO] Checking dependencies...
pip show langgraph >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing missing dependencies...
    pip install -r requirements.txt
)

REM Start News Server
echo [1/4] Starting News Server (Port 8001)...
start "NewsServer" cmd /c "title News Server && python servers\news_server.py > nul 2>&1"

REM Start Mining Data Server
echo [2/4] Starting Mining Data Server (Port 8002)...
start "MiningDataServer" cmd /c "title Mining Data Server && python servers\mining_data_server.py > nul 2>&1"

REM Start Price Server
echo [3/4] Starting Price Server (Port 8003)...
start "PriceServer" cmd /c "title Price Server && python servers\price_server.py > nul 2>&1"

REM Wait for servers to start
echo.
echo [WAIT] Starting servers (5 seconds)...
timeout /t 5 /nobreak >nul

REM Check server status
echo [CHECK] Verifying server status...

netstat -an | findstr ":8001" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] News Server started
) else (
    echo [WARN] News Server may not be running
)

netstat -an | findstr ":8002" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Mining Data Server started
) else (
    echo [WARN] Mining Data Server may not be running
)

netstat -an | findstr ":8003" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Price Server started
) else (
    echo [WARN] Price Server may not be running
)

echo.
echo ========================================
echo    All Services Started
echo ========================================
echo.
echo Servers running in background windows
echo Starting Agent...
echo.

REM Start Agent
cd /d "%~dp0"
python agents\mining_agent.py

echo.
echo ========================================
echo    System Exiting
echo ========================================
pause
