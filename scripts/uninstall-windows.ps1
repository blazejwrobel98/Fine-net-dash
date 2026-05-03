<#
.SYNOPSIS
  Removes the scheduled task and optionally the install folder.
#>
param(
    [string]$InstallPath = (Join-Path $env:LOCALAPPDATA "DividendPortfolio"),
    [string]$TaskName = "DividendPortfolio",
    [switch]$RemoveData
)

$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed task: $TaskName"
} else {
    Write-Host "No task named: $TaskName"
}

if ($RemoveData -and (Test-Path $InstallPath)) {
    Remove-Item $InstallPath -Recurse -Force
    Write-Host "Removed folder: $InstallPath"
} elseif (Test-Path $InstallPath) {
    Write-Host "Folder left in place: $InstallPath (use -RemoveData to delete)"
}
