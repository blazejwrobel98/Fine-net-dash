<#
.SYNOPSIS
  Copies app to InstallPath, creates venv, pip install, registers a scheduled task (run at user logon).

.PARAMETER InstallPath
  Target directory, e.g. $env:LOCALAPPDATA\DividendPortfolio

.PARAMETER SourcePath
  Output of build-release.ps1 (release\DividendPortfolio). Default: next to scripts folder.

.PARAMETER Port
  HTTP port (default 8000).

.PARAMETER TaskName
  Windows Task Scheduler task name.

.PARAMETER NoStartNow
  Do not start the server immediately after install.

.PARAMETER MigrateDbFrom
  Explicit path to an existing portfolio.db to copy into the install.

.PARAMETER ForceMigrateDb
  Overwrite install DB even if it already has purchase lots (backup .bak created).

.PARAMETER SkipFileCopy
  Do not robocopy from SourcePath (files already present, e.g. after MSI). Implies -SourcePath defaults to -InstallPath when omitted.

.NOTES
  For a desktop app with SQLite in your profile, "at logon" is reliable. True "at boot before login"
  needs SYSTEM-visible paths (e.g. ProgramData) and extra setup.
#>
param(
    [string]$InstallPath = (Join-Path $env:LOCALAPPDATA "DividendPortfolio"),
    [string]$SourcePath = "",
    [int]$Port = 8000,
    [string]$TaskName = "DividendPortfolio",
    [switch]$NoStartNow,
    [string]$MigrateDbFrom = "",
    [switch]$ForceMigrateDb,
    [switch]$SkipFileCopy
)

$ErrorActionPreference = "Stop"
$ScriptsDir = $PSScriptRoot
if ($SkipFileCopy -and [string]::IsNullOrWhiteSpace($SourcePath)) {
    $SourcePath = $InstallPath
}
if (-not $SourcePath) {
    $parent = Split-Path $ScriptsDir
    $fromRelease = Join-Path $parent "release\DividendPortfolio"
    if (Test-Path (Join-Path $fromRelease "backend\app\main.py")) {
        $SourcePath = $fromRelease
    } elseif (
        (Test-Path (Join-Path $parent "backend\app\main.py")) -and
        (Test-Path (Join-Path $parent "frontend\dist\index.html"))
    ) {
        $SourcePath = $parent
    } else {
        throw "Package not found. From repo run build-release first, or pass -SourcePath to the folder with backend/ and frontend/dist/."
    }
}
if (-not (Test-Path (Join-Path $SourcePath "backend\app\main.py"))) {
    throw "Package not found at '$SourcePath'. Run: .\scripts\build-release.ps1"
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    $usePyLauncher = $true
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $usePyLauncher = $false
    $pythonExe = (Get-Command python).Source
} else {
    throw "Neither 'py' nor 'python' found in PATH. Install Python 3.11+ from python.org (Add to PATH)."
}

Write-Host "Installing to: $InstallPath"

# Zwolnij blokadę SQLite (uvicorn trzyma plik — robocopy potrafi „nadpisać” DB w niepełnym stanie).
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "Stopped scheduled task '$TaskName' before file update (releases portfolio.db lock)."
        Start-Sleep -Seconds 3
    } catch {
        Write-Warning "Could not stop '$TaskName' before update; close the dashboard window if SQLite gets corrupted. $_"
    }
}

$preSnap = $null
if (-not $SkipFileCopy) {
    if (Test-Path $InstallPath) {
        Write-Warning "Folder exists - files will merge; existing venv is kept if present."
    }
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    $preDb = Join-Path $InstallPath "backend\data\portfolio.db"
    if (Test-Path -LiteralPath $preDb) {
        $preStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
        $preSnap = Join-Path $InstallPath "backend\data\portfolio.db.preinstall-$preStamp"
        try {
            Copy-Item -LiteralPath $preDb -Destination $preSnap -Force
            Write-Host "Safety copy of existing portfolio.db -> $(Split-Path $preSnap -Leaf)"
        } catch {
            Write-Warning "Could not create pre-install DB safety copy: $_"
        }
    }
    # Never overwrite runtime DB in install/backend/data during app updates.
    # Uwaga: /XD bywa zawodny w niektórych wersjach robocopy — po sync sprawdzamy hash i cofamy zmianę.
    robocopy $SourcePath $InstallPath /E /XD venv backend\data /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy install failed (exit $LASTEXITCODE)" }

    if ($preSnap -and (Test-Path -LiteralPath $preSnap)) {
        $preDbAfter = Join-Path $InstallPath "backend\data\portfolio.db"
        try {
            if (-not (Test-Path -LiteralPath $preDbAfter)) {
                Copy-Item -LiteralPath $preSnap -Destination $preDbAfter -Force
                Write-Warning "portfolio.db missing after robocopy - restored from preinstall snapshot."
            } else {
                $hSnap = (Get-FileHash -LiteralPath $preSnap -Algorithm SHA256).Hash
                $hDb = (Get-FileHash -LiteralPath $preDbAfter -Algorithm SHA256).Hash
                if ($hDb -ne $hSnap) {
                    $clobberName = "portfolio.db.robocopy-clobber-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
                    $clobber = Join-Path (Split-Path $preDbAfter) $clobberName
                    Copy-Item -LiteralPath $preDbAfter -Destination $clobber -Force
                    Copy-Item -LiteralPath $preSnap -Destination $preDbAfter -Force
                    Write-Warning ("portfolio.db changed during robocopy (saved clobbered file as " + $clobberName + "); restored from preinstall snapshot.")
                }
            }
        } catch {
            Write-Warning ("Could not verify/restore portfolio.db after robocopy: " + $_)
        }
    }
} else {
    if (-not (Test-Path (Join-Path $InstallPath "backend\app\main.py"))) {
        throw "SkipFileCopy: missing backend at $(Join-Path $InstallPath 'backend'). Run MSI repair or full install."
    }
}

New-Item -ItemType Directory -Path (Join-Path $InstallPath "backend\data") -Force | Out-Null

$VenvPath = Join-Path $InstallPath "venv"
$BackendPath = Join-Path $InstallPath "backend"
$ReqFile = Join-Path $BackendPath "requirements-prod.txt"
if (-not (Test-Path $ReqFile)) {
    $ReqFile = Join-Path $BackendPath "requirements.txt"
}

if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    Write-Host "Creating venv..."
    if ($usePyLauncher) {
        & py -3 -m venv $VenvPath
    } else {
        & $pythonExe -m venv $VenvPath
    }
}

$pip = Join-Path $VenvPath "Scripts\pip.exe"
$venvPy = Join-Path $VenvPath "Scripts\python.exe"
Write-Host "pip install..."
& $pip install --upgrade pip | Out-Null
& $pip install -r $ReqFile

$migratorRepo = Join-Path $ScriptsDir "migrate_portfolio_db.py"
$migratorPkg = Join-Path $SourcePath "scripts\migrate_portfolio_db.py"
$migrator = $null
if (Test-Path $migratorRepo) { $migrator = $migratorRepo }
elseif (Test-Path $migratorPkg) { $migrator = $migratorPkg }

$preferSrc = $null
if ($MigrateDbFrom -and (Test-Path $MigrateDbFrom)) {
    $preferSrc = (Resolve-Path $MigrateDbFrom).Path
} else {
    $repoRootForDb = Split-Path $ScriptsDir
    $autoDb = Join-Path $repoRootForDb "backend\data\portfolio.db"
    if (Test-Path $autoDb) {
        $preferSrc = (Resolve-Path $autoDb).Path
    }
}

if ($migrator -and $preferSrc) {
    Write-Host "Migrating portfolio database (if target empty or -ForceMigrateDb)..."
    if ($ForceMigrateDb) {
        & $venvPy $migrator --install-root $InstallPath --prefer-src $preferSrc --force
    } else {
        & $venvPy $migrator --install-root $InstallPath --prefer-src $preferSrc
    }
} elseif ($preferSrc -and -not $migrator) {
    Write-Warning "migrate_portfolio_db.py not found; skipped DB copy."
} elseif ($MigrateDbFrom -and -not (Test-Path $MigrateDbFrom)) {
    Write-Warning "MigrateDbFrom path not found: $MigrateDbFrom"
}

$urlContent = @"
[InternetShortcut]
URL=http://127.0.0.1:$Port/
"@
$urlContent | Set-Content -Path (Join-Path $InstallPath "Dashboard.url") -Encoding ASCII

$runDashboardSrc = Join-Path $ScriptsDir "Run-Dashboard.ps1"
$runDashboardDst = Join-Path $InstallPath "Run-Dashboard.ps1"
if (Test-Path $runDashboardSrc) {
    Copy-Item $runDashboardSrc $runDashboardDst -Force
} else {
    Write-Warning "Run-Dashboard.ps1 not found next to install script; scheduled task may fail until you copy it."
}

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

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$runScript = Join-Path $InstallPath "Run-Dashboard.ps1"
$psArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runScript`" -Port $Port"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs -WorkingDirectory $InstallPath
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Dividend portfolio dashboard (FastAPI)" | Out-Null

Write-Host ""
Write-Host "Installed. Scheduled task: '$TaskName' (runs at logon)."
Write-Host "Logs: $InstallPath\logs\server.log"
Write-Host "Manual test:"
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$runScript`" -Port $Port"
Write-Host "  (or from backend: & `"$venvPy`" -m uvicorn app.main:app --host 127.0.0.1 --port $Port)"
Write-Host ""
Write-Host "Open: http://127.0.0.1:$Port/  shortcut: $InstallPath\Dashboard.url"
Write-Host "Start anytime: double-click $InstallPath\Start-Dashboard.bat"
Write-Host "Or PowerShell: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "After next logon the scheduled task starts the app automatically."

if (-not $NoStartNow) {
    try {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Started task now - server should listen in a few seconds."
    } catch {
        Write-Warning "Could not start task immediately: $_"
    }
}

# Robocopy success often leaves $LASTEXITCODE 1-7; avoid misleading non-zero script exit in CI.
exit 0
