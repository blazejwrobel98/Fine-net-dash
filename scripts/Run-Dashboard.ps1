<#
.SYNOPSIS
  Starts uvicorn from the install folder and appends all output to logs\server.log.

.NOTES
  Intended to live next to venv/ and backend/ (InstallPath). $PSScriptRoot is the install root.
#>
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"
$InstallPath = $PSScriptRoot
$logDir = Join-Path $InstallPath "logs"
$null = New-Item -ItemType Directory -Force -Path $logDir
$log = Join-Path $logDir "server.log"
$venvPy = Join-Path $InstallPath "venv\Scripts\python.exe"
$backend = Join-Path $InstallPath "backend"

function Write-Banner([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    $line | Tee-Object -FilePath $log -Append
}

if (-not (Test-Path $venvPy)) {
    Write-Banner "ERROR: missing venv python: $venvPy"
    exit 1
}
if (-not (Test-Path (Join-Path $backend "app\main.py"))) {
    Write-Banner "ERROR: missing backend app: $backend"
    exit 1
}

$exitCode = 0
Push-Location $backend
try {
    Write-Banner "===== uvicorn start port=$Port pid=$PID ====="
    & $venvPy -m uvicorn app.main:app --host 127.0.0.1 --port $Port *>&1 | Tee-Object -FilePath $log -Append
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { $exitCode = $LASTEXITCODE }
} finally {
    Pop-Location
    Write-Banner "===== uvicorn stopped exitCode=$exitCode (LASTEXITCODE=$LASTEXITCODE) ====="
}
exit $exitCode
