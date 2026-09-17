# PowerShell dev startup script for SovereignForge
# Run from project root: .\scripts\start_dev.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SovereignForge — Dev Startup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Verify we're in the right directory
if (-not (Test-Path ".\backend\main.py")) {
    Write-Host "ERROR: Run this script from the sovereignforge/ root directory." -ForegroundColor Red
    exit 1
}

# ── Create temp directories ──
$tmp = [System.IO.Path]::GetTempPath()
$sfTemp = Join-Path $tmp "sovereignforge"
@("uploads", "outputs") | ForEach-Object {
    New-Item -ItemType Directory -Path (Join-Path $sfTemp $_) -Force | Out-Null
}
Write-Host "[OK] Temp directories created: $sfTemp" -ForegroundColor Green

# ── Check Ollama ──
Write-Host ""
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "[OK] Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Ollama not responding. Starting ollama serve in background..." -ForegroundColor Yellow
    Start-Process -NoNewWindow -FilePath "ollama" -ArgumentList "serve"
    Start-Sleep -Seconds 3
}

# ── Build sandbox Docker image (if not built) ──
Write-Host ""
Write-Host "Checking sandbox Docker image..." -ForegroundColor Yellow
$imageExists = docker images -q sovereignforge-sandbox:latest 2>$null
if (-not $imageExists) {
    Write-Host "Building sandbox image..." -ForegroundColor Yellow
    docker build -t sovereignforge-sandbox:latest .\sandbox\
    Write-Host "[OK] Sandbox image built" -ForegroundColor Green
} else {
    Write-Host "[OK] Sandbox image already exists" -ForegroundColor Green
}

# ── Check/activate venv ──
Write-Host ""
Write-Host "Checking Python venv..." -ForegroundColor Yellow
if (-not (Test-Path ".\venv")) {
    Write-Host "Creating venv..." -ForegroundColor Yellow
    python -m venv venv
}
$venvPython = ".\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: venv Python not found at $venvPython" -ForegroundColor Red
    exit 1
}

# Install deps if needed
Write-Host "Installing/verifying backend dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install -q -r .\backend\requirements-dev.txt
Write-Host "[OK] Backend deps ready" -ForegroundColor Green

# ── Start mitmproxy in background ──
Write-Host ""
Write-Host "Starting mitmproxy sovereignty monitor..." -ForegroundColor Yellow
$mitm = Start-Process -NoNewWindow -PassThru `
    -FilePath ".\venv\Scripts\mitmdump.exe" `
    -ArgumentList "--listen-port 8080 --scripts .\sovereignty\mitmproxy_addon.py" `
    -RedirectStandardOutput ".\logs\mitmproxy.log" 2>$null
if ($mitm) {
    Write-Host "[OK] mitmproxy started (PID $($mitm.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARN] mitmproxy failed to start — sovereignty monitor inactive" -ForegroundColor Yellow
}

# ── Start FastAPI backend ──
Write-Host ""
Write-Host "Starting FastAPI backend..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path ".\logs" -Force | Out-Null
$backend = Start-Process -NoNewWindow -PassThru `
    -FilePath $venvPython `
    -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory ".\backend" `
    -RedirectStandardOutput "..\logs\backend.log"
Write-Host "[OK] Backend started (PID $($backend.Id))" -ForegroundColor Green
Start-Sleep -Seconds 2

# ── Start Next.js frontend ──
Write-Host ""
Write-Host "Starting Next.js frontend..." -ForegroundColor Yellow
$frontend = Start-Process -NoNewWindow -PassThru `
    -FilePath "npm" `
    -ArgumentList "run dev" `
    -WorkingDirectory ".\frontend" `
    -RedirectStandardOutput "..\logs\frontend.log"
Write-Host "[OK] Frontend started (PID $($frontend.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SovereignForge is running!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:   http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:    http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Monitor:    http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "Logs: .\logs\" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Yellow

# Keep script running
try {
    while ($true) { Start-Sleep -Seconds 60 }
} finally {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    @($backend, $frontend, $mitm) | Where-Object { $_ } | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}
