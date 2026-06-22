# PowerShell script to automate the execution of the a2a_mcp example on Windows
# It starts all necessary servers and agents in the background,
# runs the client, and then cleans up all background processes.

# Exit on error
$ErrorActionPreference = "Stop"

# Configuration
# 使用脚本所在目录为工作目录，便于任意位置执行
$WORK_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_DIR = "logs"

# Array to store background job objects
$jobs = @()

# Cleanup function
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down background processes..."
    
    foreach ($job in $jobs) {
        if ($job -ne $null) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Remove-Job -Job $job -ErrorAction SilentlyContinue
        }
    }
    
    # Also try to kill any remaining processes
    Get-Process | Where-Object { $_.CommandLine -like "*a2a-mcp*" -or $_.CommandLine -like "*uv run*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "Cleanup complete."
}

# Register cleanup on exit
Register-EngineEvent PowerShell.Exiting -Action { Cleanup } | Out-Null

# Check if working directory exists
if (-not (Test-Path $WORK_DIR)) {
    Write-Host "Error: Directory '$WORK_DIR' not found."
    Write-Host "Please update the WORK_DIR variable in this script."
    exit 1
}

# Navigate to working directory
Set-Location $WORK_DIR
Write-Host "Changed directory to $(Get-Location)"

# Create log directory
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR | Out-Null
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found!"
    Write-Host "Creating a template .env file. Please add your OPENAI_API_KEY."
    @"
OPENAI_API_KEY=your_openai_compatible_api_key_here
# Optional environment variables
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
# LITELLM_MODEL=Qwen/Qwen2.5-7B-Instruct
# A2A_LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Please edit .env file and add your OPENAI_API_KEY, then run this script again."
    exit 1
}

Write-Host "Setting up Python virtual environment with 'uv'..."
uv venv

# Activate virtual environment
$venvActivate = Join-Path $WORK_DIR ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Host "Virtual environment activated."
} else {
    Write-Host "Error: Virtual environment activation script not found."
    exit 1
}

Write-Host ""
Write-Host "Starting servers and agents in the background..."

# Function to start a background job
function Start-BackgroundJob {
    param(
        [string]$Name,
        [string]$Command,
        [string]$LogFile
    )
    
    $logPath = Join-Path $LOG_DIR $LogFile
    Write-Host "-> Starting $Name... Log: $logPath"
    
    $job = Start-Job -ScriptBlock {
        param($cmd, $log)
        Set-Location $using:WORK_DIR
        & $using:venvActivate
        Invoke-Expression $cmd | Tee-Object -FilePath $log
    } -ArgumentList $Command, $logPath
    
    $jobs += $job
    return $job
}

# 1. Start MCP Server
Start-BackgroundJob -Name "MCP Server (Port: 10100)" `
    -Command "uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100" `
    -LogFile "mcp_server.log"

# 2. Start Orchestrator Agent
Start-BackgroundJob -Name "Orchestrator Agent (Port: 10101)" `
    -Command "uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/orchestrator_agent.json --port 10101" `
    -LogFile "orchestrator_agent.log"

# 3. Start Planner Agent
Start-BackgroundJob -Name "Planner Agent (Port: 10102)" `
    -Command "uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/planner_agent.json --port 10102" `
    -LogFile "planner_agent.log"

# 4. Start Airline Ticketing Agent
Start-BackgroundJob -Name "Airline Agent (Port: 10103)" `
    -Command "uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/air_ticketing_agent.json --port 10103" `
    -LogFile "airline_agent.log"

# 5. Start Hotel Reservations Agent
Start-BackgroundJob -Name "Hotel Agent (Port: 10104)" `
    -Command "uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/hotel_booking_agent.json --port 10104" `
    -LogFile "hotel_agent.log"

# 6. Start Car Rental Reservations Agent
Start-BackgroundJob -Name "Car Rental Agent (Port: 10105)" `
    -Command "uv run --env-file .env python -m a2a_mcp.agents --agent-card agent_cards/car_rental_agent.json --port 10105" `
    -LogFile "car_rental_agent.log"

Write-Host ""
Write-Host "All services are starting. Waiting 15 seconds for them to initialize..."
Start-Sleep -Seconds 15

# Check if services are running
Write-Host ""
Write-Host "Checking service status..."
foreach ($job in $jobs) {
    $state = (Get-Job -Id $job.Id).State
    Write-Host "  Job $($job.Id): $state"
}

# Run the foreground client
Write-Host ""
Write-Host "---------------------------------------------------------"
Write-Host "Starting CLI Client..."
Write-Host "The script will exit after the client finishes."
Write-Host "---------------------------------------------------------"
Write-Host ""

try {
    uv run --env-file .env python -m a2a_mcp.agents.orchestrator.mcp_client --resource "resource://agent_cards/list" --find_agent "I would like to plan a trip to France."
} catch {
    Write-Host "Error running client: $_"
}

Write-Host ""
Write-Host "---------------------------------------------------------"
Write-Host "CLI client finished."
Write-Host "---------------------------------------------------------"

# Cleanup will be called automatically on exit
