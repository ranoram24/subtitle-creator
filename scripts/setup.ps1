# setup.ps1 — Bootstrap the Python backend for subtitle-creator
# Run from the repo root: .\scripts\setup.ps1

param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$BackendDir = Join-Path $PSScriptRoot ".." "backend"
$VenvDir = Join-Path $BackendDir ".venv"

Write-Host ""
Write-Host "=== Subtitle Creator — Backend Setup ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pyVersion = & $PythonExe --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Install Python 3.10+ and re-run."
}
Write-Host "      Found: $pyVersion"

# 2. Check FFmpeg
Write-Host "[2/5] Checking FFmpeg..." -ForegroundColor Yellow
$ffVersion = ffmpeg -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0) {
    Write-Warning "FFmpeg not found on PATH. Install from https://ffmpeg.org/download.html"
} else {
    Write-Host "      Found: $ffVersion"
}

# 3. Create virtual environment
Write-Host "[3/5] Creating virtual environment at $VenvDir ..." -ForegroundColor Yellow
if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
} else {
    Write-Host "      Already exists, skipping."
}

$PipExe = Join-Path $VenvDir "Scripts" "pip.exe"
$PythonVenv = Join-Path $VenvDir "Scripts" "python.exe"

# 4. Detect CUDA and install torch
Write-Host "[4/5] Installing PyTorch..." -ForegroundColor Yellow
$nvidiaPresent = $false
try {
    $nvidiaSmi = nvidia-smi --query-gpu=name --format=csv,noheader 2>&1
    if ($LASTEXITCODE -eq 0) { $nvidiaPresent = $true }
} catch {}

if ($nvidiaPresent) {
    Write-Host "      NVIDIA GPU detected — installing CUDA 12.1 torch wheel..."
    & $PipExe install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
} else {
    Write-Host "      No NVIDIA GPU — installing CPU torch..."
    & $PipExe install torch --index-url https://download.pytorch.org/whl/cpu --quiet
}

# 5. Install remaining requirements
Write-Host "[5/5] Installing Python dependencies..." -ForegroundColor Yellow
& $PipExe install -r (Join-Path $BackendDir "requirements.txt") --quiet

Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Green
Write-Host "Next step: run .\scripts\download_models.ps1 (or python backend/scripts/download_models.py)"
Write-Host "Then build the C# frontend: dotnet build frontend/SubtitleCreator"
Write-Host ""
