# Dopa Code Installer
# Ejecutar como Administrador en PowerShell
# Set-ExecutionPolicy Bypass -Scope Process; .\install.ps1

$ErrorActionPreference = "Stop"
$DOPA_ROOT = "C:\Program Files\DopaCode"
$DOPA_WORKSPACES = "$env:USERPROFILE\dopa-workspaces"

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "   Dopa Code - Instalador v0.2.0" -ForegroundColor Yellow
Write-Host "   Agente andino Inti + Bridge OpenCode" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# 1. Verify prerequisites
Write-Host "`n[1/6] Verificando requisitos..." -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python 3.11+ no encontrado. Instala desde https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $($python.Version)" -ForegroundColor Green

$bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $bun) {
    Write-Host "  Instalando Bun..." -ForegroundColor Yellow
    powershell -c "irm bun.sh/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.bun\bin;$env:Path"
}
Write-Host "  Bun: $(bun --version)" -ForegroundColor Green

# 2. Install OpenCode CLI
Write-Host "`n[2/6] Instalando OpenCode CLI..." -ForegroundColor Cyan
$opencode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $opencode) {
    npm install -g opencode-ai@latest
}
Write-Host "  OpenCode: $(opencode --version)" -ForegroundColor Green

# 3. Create directories
Write-Host "`n[3/6] Creando directorios..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $DOPA_ROOT | Out-Null
New-Item -ItemType Directory -Force -Path $DOPA_WORKSPACES | Out-Null
New-Item -ItemType Directory -Force -Path "$DOPA_ROOT\logs" | Out-Null
Write-Host "  $DOPA_ROOT" -ForegroundColor Green
Write-Host "  $DOPA_WORKSPACES" -ForegroundColor Green

# 4. Copy binaries
Write-Host "`n[4/6] Copiando binarios..." -ForegroundColor Cyan
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$scriptDir\dopa-code-daemon.exe") {
    Copy-Item "$scriptDir\dopa-code-daemon.exe" "$DOPA_ROOT\dopa-code-daemon.exe" -Force
    Write-Host "  dopa-code-daemon.exe copiado" -ForegroundColor Green
}
if (Test-Path "$scriptDir\dopa-bridge.exe") {
    Copy-Item "$scriptDir\dopa-bridge.exe" "$DOPA_ROOT\dopa-bridge.exe" -Force
    Write-Host "  dopa-bridge.exe copiado" -ForegroundColor Green
}

# 5. Create .env config
Write-Host "`n[5/6] Configurando variables de entorno..." -ForegroundColor Cyan
$envContent = @"
DOPA_DATABASE_URL=sqlite+aiosqlite:///$DOPA_ROOT\dopa_code.db
DOPA_CODE_DUMMY=0
DOPA_OPENROUTER_API_KEY=
DOPA_ANTIGRAVITY_API_KEY=
DOPA_EASYPANEL_DEPLOY_TOKEN=
DOPA_EASYPANEL_ENDPOINT=https://easypanel.io
"@
$envContent | Out-File -FilePath "$DOPA_ROOT\.env" -Encoding UTF8
Write-Host "  .env creado en $DOPA_ROOT" -ForegroundColor Green
Write-Host "  Configura tus API keys en: $DOPA_ROOT\.env" -ForegroundColor Yellow

# 6. Register Windows Service
Write-Host "`n[6/6] Registrando servicio Windows..." -ForegroundColor Cyan
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "  nssm no encontrado. Instala desde https://nssm.cc" -ForegroundColor Yellow
    Write-Host "  O ejecuta manualmente: dopa-code-daemon.exe" -ForegroundColor Yellow
} else {
    nssm stop DopaCode 2>$null
    nssm remove DopaCode confirm 2>$null
    nssm install DopaCode "$DOPA_ROOT\dopa-code-daemon.exe"
    nssm set DopaCode AppDirectory "$DOPA_ROOT"
    nssm set DopaCode DisplayName "Dopa Code - Inti Daemon"
    nssm set DopaCode Description "Agente andino de orquestacion para Dopa Code"
    nssm set DopaCode Start SERVICE_AUTO_START
    nssm set DopaCode AppStdout "$DOPA_ROOT\logs\daemon.log"
    nssm set DopaCode AppStderr "$DOPA_ROOT\logs\daemon-err.log"
    nssm start DopaCode
    Write-Host "  Servicio DopaCode instalado e iniciado" -ForegroundColor Green
}

Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "   Dopa Code instalado correctamente!" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "`nConfiguracion:" -ForegroundColor White
Write-Host "  .env:       $DOPA_ROOT\.env" -ForegroundColor Gray
Write-Host "  Workspaces: $DOPA_WORKSPACES" -ForegroundColor Gray
Write-Host "  Logs:       $DOPA_ROOT\logs\" -ForegroundColor Gray
Write-Host "`nEndpoints:" -ForegroundColor White
Write-Host "  API:      http://localhost:8000" -ForegroundColor Gray
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Gray
Write-Host "  PWA:      http://localhost:8000" -ForegroundColor Gray
Write-Host "`nProximo paso: abre http://localhost:8000 en tu navegador" -ForegroundColor Cyan
