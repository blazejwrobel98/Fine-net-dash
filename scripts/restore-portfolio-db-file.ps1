<#
.SYNOPSIS
  Przywraca caly plik portfolio.db z kopii (np. pobranej z eksportu), przy wylaczonym serwerze.
  Bezpieczniejsze niz „Przywroc" w UI przy blokadzie SQLite lub gdy chcesz 1:1 plik z pulpitu.

.PARAMETER InstallPath
  Folder instalacji (domyslnie %LOCALAPPDATA%\DividendPortfolio).

.PARAMETER BackupDb
  Pelna sciezka do pliku .db (backup portfela).

.PARAMETER TaskName
  Nazwa zadania harmonogramu Windows.
#>
param(
    [string]$InstallPath = (Join-Path $env:LOCALAPPDATA "DividendPortfolio"),
    [Parameter(Mandatory = $true)][string]$BackupDb,
    [string]$TaskName = "DividendPortfolio"
)

$ErrorActionPreference = "Stop"
$BackupDb = (Resolve-Path -LiteralPath $BackupDb).Path
$target = Join-Path $InstallPath "backend\data\portfolio.db"
$dataDir = Split-Path $target

if (-not (Test-Path -LiteralPath $BackupDb)) {
    throw "Nie znaleziono pliku kopii: $BackupDb"
}
if (-not (Test-Path (Join-Path $InstallPath "backend\app\main.py"))) {
    throw "InstallPath nie wyglada na instalacje DividendPortfolio: $InstallPath"
}

$venvPy = Join-Path $InstallPath "venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    throw "Brak Pythona w instalacji (oczekiwano): $venvPy"
}

$env:DASHBOARD_RESTORE_SRC = $BackupDb
$code = @'
import os, sqlite3, sys
p = os.environ.get("DASHBOARD_RESTORE_SRC", "")
c = sqlite3.connect(p)
n = c.execute(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='purchase_lots'"
).fetchone()[0]
c.close()
sys.exit(0 if n else 1)
'@
& $venvPy -c $code
$exit = $LASTEXITCODE
Remove-Item Env:DASHBOARD_RESTORE_SRC -ErrorAction SilentlyContinue
if ($exit -ne 0) {
    throw "Plik nie wyglada na baze portfela (brak tabeli purchase_lots): $BackupDb"
}

Write-Host "Stopping task '$TaskName'..."
try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop } catch { }
Start-Sleep -Seconds 4
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*${InstallPath}*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$ts = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$saved = Join-Path $dataDir "portfolio.db.before-restore-file-$ts"
if (Test-Path -LiteralPath $target) {
    Copy-Item -LiteralPath $target -Destination $saved -Force
    Write-Host "Zapisano biezacy plik jako: $(Split-Path $saved -Leaf)"
}
Copy-Item -LiteralPath $BackupDb -Destination $target -Force
Write-Host "Podmieniono portfolio.db kopia: $BackupDb"

try {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Uruchomiono zadanie '$TaskName'. Otworz http://127.0.0.1:8000/"
} catch {
    Write-Warning "Nie udalo sie uruchomic zadania: $_ — odpal recznie Start-Dashboard.bat"
}
exit 0
