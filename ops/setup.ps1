# Setup Breakeven Auto
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path (Split-Path -Parent $root) "monitor-invictus\.venv"
$req = Join-Path $root "vendor\autobreakeven\breakeven-projetos\scripts\requirements.txt"

Write-Host "=== Breakeven Auto setup ==="

if (Test-Path $venv) {
    & "$venv\Scripts\python.exe" -m pip install -r $req -q
    Write-Host "deps skill: OK (monitor-invictus venv)"
} else {
    Write-Host "WARN: venv monitor-invictus nao encontrado — rode setup la primeiro"
    python -m pip install -r $req
}

New-Item -ItemType Directory -Force -Path (Join-Path $root "assets\growthpacks") | Out-Null
Write-Host "assets/growthpacks: OK"
Write-Host "Proximo: python src/integrations/build_strategy_review_manifest.py"
