# Mining Agent - PowerShell Startup Script
# Save as UTF-8 with BOM encoding

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Mining Agent System - Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found! Please install Python and add to PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check dependencies
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Yellow
$langgraphInstalled = pip show langgraph 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing missing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""

# Function to start servers
function Start-Server {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Port
    )
    
    Write-Host "[START] $Name (Port $Port)..." -ForegroundColor Cyan
    
    $logPath = "$env:TEMP\server_$Port.log"
    $errPath = "$env:TEMP\server_$Port.err"
    
    Start-Process -FilePath "python" `
                  -ArgumentList $Script `
                  -WindowStyle Minimized `
                  -PassThru `
                  -RedirectStandardOutput $logPath `
                  -RedirectStandardError $errPath
}

# Start News Server
$newsProcess = Start-Server -Name "News Server" -Script "servers\news_server.py" -Port "8001"

# Start Mining Data Server
$miningProcess = Start-Server -Name "Mining Data Server" -Script "servers\mining_data_server.py" -Port "8002"

# Start Price Server
$priceProcess = Start-Server -Name "Price Server" -Script "servers\price_server.py" -Port "8003"

# Wait for servers to start
Write-Host ""
Write-Host "[WAIT] Starting servers (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check server status
Write-Host ""
Write-Host "[CHECK] Verifying server status..." -ForegroundColor Yellow

function Test-Port {
    param([string]$Port)
    try {
        $connection = Test-NetConnection -ComputerName "localhost" -Port $Port -WarningAction SilentlyContinue
        return $connection.TcpTestSucceeded
    } catch {
        return $false
    }
}

if (Test-Port -Port "8001") {
    Write-Host "[OK] News Server started" -ForegroundColor Green
} else {
    Write-Host "[WARN] News Server may not be running" -ForegroundColor Yellow
}

if (Test-Port -Port "8002") {
    Write-Host "[OK] Mining Data Server started" -ForegroundColor Green
} else {
    Write-Host "[WARN] Mining Data Server may not be running" -ForegroundColor Yellow
}

if (Test-Port -Port "8003") {
    Write-Host "[OK] Price Server started" -ForegroundColor Green
} else {
    Write-Host "[WARN] Price Server may not be running" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   All Services Started" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Servers running in background" -ForegroundColor Gray
Write-Host "Starting Agent..." -ForegroundColor Gray
Write-Host ""

# Start Agent
Write-Host "[START] Agent..." -ForegroundColor Cyan
python agents\mining_agent.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   System Exiting" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Read-Host "Press Enter to exit"
