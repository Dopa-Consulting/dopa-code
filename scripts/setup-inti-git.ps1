# setup-inti-git.ps1 - PowerShell version para Windows
# Configura git para que Inti aparezca como co-author

$ErrorActionPreference = "Continue"
$gitDir = git rev-parse --git-dir 2>$null

if (-not $gitDir) {
    Write-Host "[Inti] No es un repositorio git. Ejecuta dentro de un workspace." -ForegroundColor Red
    exit 1
}

$hooksDir = Join-Path $gitDir "hooks"
$scriptDir = Join-Path $PSScriptRoot "git-hooks"

Write-Host "[Inti] Configurando git hooks para co-autoria..." -ForegroundColor Yellow

# Instalar hooks
Copy-Item "$scriptDir\prepare-commit-msg" "$hooksDir\prepare-commit-msg" -Force
Copy-Item "$scriptDir\commit-msg" "$hooksDir\commit-msg" -Force
Copy-Item "$scriptDir\post-commit" "$hooksDir\post-commit" -Force

# Configurar alias
git config alias.inti '!git commit -m "[Inti] $1" --trailer "Co-authored-by: Inti <inti@dopa.solutions>"'

Write-Host "[Inti] Hooks instalados!" -ForegroundColor Green
Write-Host ""
Write-Host "Cada commit en branches intl/* o agent/* llevara:" -ForegroundColor Gray
Write-Host "  Co-authored-by: Inti <inti@dopa.solutions>" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para que Inti tenga foto de perfil en GitHub:" -ForegroundColor Yellow
Write-Host "  1. Crea cuenta GitHub: inti@dopa.solutions" -ForegroundColor Gray
Write-Host "  2. Sube public/inti-logo.svg como avatar" -ForegroundColor Gray
Write-Host "  3. Los commits de Inti mostraran el logo del sol andino" -ForegroundColor Gray
Write-Host ""
