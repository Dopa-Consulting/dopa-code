# Dopa Code - Quickstart
# Ejecutar en PowerShell como usuario normal (NO admin)
# Set-ExecutionPolicy Bypass -Scope Process; .\quickstart.ps1

$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "   Dopa Code - Quickstart v0.3.0" -ForegroundColor Yellow
Write-Host "   Inti + OpenCode + PWA" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# 1. Verify prerequisites
Write-Host "[1/6] Verificando requisitos..." -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python 3.11+ no encontrado. Instala desde https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $(python --version)" -ForegroundColor Green

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "ERROR: Node.js 20+ no encontrado." -ForegroundColor Red
    exit 1
}
Write-Host "  Node:   $(node --version)" -ForegroundColor Green

$bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $bun) {
    Write-Host "  Instalando Bun..." -ForegroundColor Yellow
    powershell -c "irm bun.sh/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.bun\bin;$env:Path"
}
$bunVersion = & "$env:USERPROFILE\.bun\bin\bun.exe" --version 2>$null
Write-Host "  Bun:    $bunVersion" -ForegroundColor Green

# 2. Setup backend
Write-Host "[2/6] Configurando backend Inti..." -ForegroundColor Cyan

Push-Location "$ROOT\backend-inti"
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
Pop-Location

Write-Host "  Backend dependencies OK" -ForegroundColor Green

# 3. Setup .env
Write-Host "[3/6] Configurando .env..." -ForegroundColor Cyan

if (-not (Test-Path "$ROOT\.env")) {
    Copy-Item "$ROOT\.env.example" "$ROOT\.env"
    Write-Host "  .env creado desde .env.example" -ForegroundColor Green
} else {
    Write-Host "  .env ya existe" -ForegroundColor Green
}
Write-Host "  Configura tus API keys en: $ROOT\.env" -ForegroundColor Yellow

# 4. Install OpenCode CLI
Write-Host "[4/6] Verificando OpenCode CLI..." -ForegroundColor Cyan

$opencode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $opencode) {
    Write-Host "  Instalando OpenCode CLI..." -ForegroundColor Yellow
    npm install -g opencode-ai@latest
}
Write-Host "  OpenCode: $(opencode --version)" -ForegroundColor Green

# 5. Start bridge
Write-Host "[5/6] Iniciando bridge OpenCode..." -ForegroundColor Cyan

$bridgeLog = "$ROOT\agent-runtime\bridge.log"
$bunBin = "$env:USERPROFILE\.bun\bin\bun.exe"
Start-Process -FilePath $bunBin -ArgumentList "$ROOT\agent-runtime\bridge.js" -WindowStyle Hidden -RedirectStandardOutput $bridgeLog -RedirectStandardError $bridgeLog
Start-Sleep -Seconds 3

try {
    $bridgeHealth = Invoke-RestMethod -Uri "http://localhost:4097/health" -Headers @{"x-bridge-token"="dopa-bridge-local-dev"} -TimeoutSec 3
    Write-Host "  Bridge: OK (mode: $($bridgeHealth.mode))" -ForegroundColor Green
} catch {
    Write-Host "  Bridge: esperando... (log: $bridgeLog)" -ForegroundColor Yellow
}

# 6. Start daemon + open PWA
Write-Host "[6/6] Iniciando daemon Inti..." -ForegroundColor Cyan

$daemonLog = "$ROOT\daemon.log"
Start-Process -FilePath "$ROOT\backend-inti\venv\Scripts\python.exe" -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "$ROOT\backend-inti" -WindowStyle Hidden -RedirectStandardOutput $daemonLog -RedirectStandardError $daemonLog

Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "  Daemon: OK (v$($health.version), dummy=$($health.dummy_mode))" -ForegroundColor Green
} catch {
    Write-Host "  Daemon: esperando... (log: $daemonLog)" -ForegroundColor Yellow
}

# Open PWA
Start-Process "http://localhost:8000"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "   Dopa Code iniciado!" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  PWA:      http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  Bridge:   http://localhost:4097/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Logs:     $daemonLog" -ForegroundColor Gray
Write-Host "            $bridgeLog" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para detener: Ctrl+C en las ventanas abiertas" -ForegroundColor Gray
Write-Host ""
