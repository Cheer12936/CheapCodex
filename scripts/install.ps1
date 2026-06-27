param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python was not found on PATH"
}

python -m venv $VenvPath
& "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip
& "$VenvPath\Scripts\python.exe" -m pip install -e .

Write-Host ""
Write-Host "Installed codex-cheap-worker."
Write-Host "Activate with:"
Write-Host "  .\$VenvPath\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Configure a worker model:"
Write-Host '  $env:WORKER_API_KEY="your-key"'
Write-Host '  $env:WORKER_BASE_URL="https://api.moonshot.ai/v1"'
Write-Host '  $env:WORKER_MODEL="kimi-k2.5"'
Write-Host ""
Write-Host "Try:"
Write-Host '  ask-worker --paths "src/**/*.py" --question "Summarize the modules" --dry-run'

