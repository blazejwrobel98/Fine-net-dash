<#
.SYNOPSIS
  Creates Start-Dashboard.bat in an existing install (e.g. after you stopped the server and have no shortcut yet).

.EXAMPLE
  .\scripts\Write-StartDashboardBat.ps1
  .\scripts\Write-StartDashboardBat.ps1 -InstallPath "D:\Apps\DividendPortfolio" -Port 8000
#>
param(
    [string]$InstallPath = (Join-Path $env:LOCALAPPDATA "DividendPortfolio"),
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$py = Join-Path $InstallPath "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "No venv at $py. Run install-windows.ps1 first or fix -InstallPath."
}

$runSrc = Join-Path $PSScriptRoot "Run-Dashboard.ps1"
$runDst = Join-Path $InstallPath "Run-Dashboard.ps1"
if (-not (Test-Path $runSrc)) {
    throw "Missing Run-Dashboard.ps1 next to this script: $runSrc"
}
Copy-Item $runSrc $runDst -Force

$startBat = Join-Path $InstallPath "Start-Dashboard.bat"
$batBody = @"
@echo off
title DividendPortfolio
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%Run-Dashboard.ps1" -Port $Port
echo.
echo Server stopped. Press a key to close.
pause >nul
"@
[System.IO.File]::WriteAllText($startBat, $batBody.TrimEnd(), [System.Text.UTF8Encoding]::new($false))
Write-Host "Written: $startBat"
Write-Host 'Double-click that file, or: Start-ScheduledTask -TaskName DividendPortfolio'
