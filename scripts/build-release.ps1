<#
.SYNOPSIS
  Builds frontend and copies backend + dist to release\DividendPortfolio (ready to install).

.EXAMPLE
  .\scripts\build-release.ps1
  .\scripts\build-release.ps1 -Zip
#>
param(
    [switch]$Zip
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$OutRoot = Join-Path $RepoRoot "release\DividendPortfolio"

Write-Host "Repo: $RepoRoot"
Write-Host "Frontend build..."
Push-Location (Join-Path $RepoRoot "frontend")
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $RepoRoot "frontend\dist\index.html"))) {
    throw "Missing frontend/dist - npm run build failed."
}

Write-Host "Packaging to: $OutRoot"
if (Test-Path $OutRoot) {
    Remove-Item $OutRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $OutRoot -Force | Out-Null

$BackendSrc = Join-Path $RepoRoot "backend"
$BackendDst = Join-Path $OutRoot "backend"
New-Item -ItemType Directory -Path $BackendDst -Force | Out-Null
robocopy $BackendSrc $BackendDst /E /XD venv __pycache__ .pytest_cache data tests /XF .env /NFL /NDL /NJH /NJS /NC /NS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy backend failed (exit $LASTEXITCODE)" }

$DistSrc = Join-Path $RepoRoot "frontend\dist"
$DistDst = Join-Path $OutRoot "frontend\dist"
New-Item -ItemType Directory -Path $DistDst -Force | Out-Null
robocopy $DistSrc $DistDst /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy frontend/dist failed (exit $LASTEXITCODE)" }

$OutScripts = Join-Path $OutRoot "scripts"
New-Item -ItemType Directory -Path $OutScripts -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "scripts\migrate_portfolio_db.py") $OutScripts -Force
Copy-Item (Join-Path $RepoRoot "scripts\install-windows.ps1") $OutScripts -Force
Copy-Item (Join-Path $RepoRoot "scripts\uninstall-windows.ps1") $OutScripts -Force
Copy-Item (Join-Path $RepoRoot "scripts\Write-StartDashboardBat.ps1") $OutScripts -Force
Copy-Item (Join-Path $RepoRoot "scripts\Run-Dashboard.ps1") $OutScripts -Force
Copy-Item (Join-Path $RepoRoot "scripts\Install-AfterMsi.ps1") $OutScripts -Force

$readme = @"
Install (PowerShell, normal user):

  cd scripts
  .\install-windows.ps1 -InstallPath "$env:LOCALAPPDATA\DividendPortfolio"

Source folder defaults to: release\DividendPortfolio (next to repo).
App runs at Windows logon (Task Scheduler).
Browser: http://127.0.0.1:8000/

Uninstall:
  .\uninstall-windows.ps1

Database: if you run install from the repo (scripts next to backend/), your
existing backend/data/portfolio.db is copied into the install when the target
has no purchase lots yet. Or use -MigrateDbFrom "D:\path\to\portfolio.db".

Start app: double-click Start-Dashboard.bat in the install folder, or
  Start-ScheduledTask -TaskName DividendPortfolio
Recreate the .bat only: .\scripts\Write-StartDashboardBat.ps1

Server log (stdout/stderr): InstallPath\logs\server.log

MSI (GitHub Releases): installs under
  %LOCALAPPDATA%\Programs\FineNetDash\
After install, run once (finishes venv + Task Scheduler):
  powershell -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\Programs\FineNetDash\scripts\Install-AfterMsi.ps1"
Or from that folder:  .\scripts\Install-AfterMsi.ps1
"@
$readme | Set-Content -Path (Join-Path $OutRoot "INSTALL.txt") -Encoding UTF8

if ($Zip) {
    $ZipPath = Join-Path $RepoRoot "release\DividendPortfolio.zip"
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Compress-Archive -Path $OutRoot -DestinationPath $ZipPath -Force
    Write-Host "ZIP: $ZipPath"
}

Write-Host "Done: $OutRoot"
# Robocopy uses 0-7 for success (e.g. 1 = copied files). Without this, the script
# process exit code stays non-zero and CI marks the step as failed.
exit 0
