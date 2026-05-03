<#
.SYNOPSIS
  Run after MSI copied files: create venv, pip install, register scheduled task.
  Install root = parent of the scripts folder (same layout as release\DividendPortfolio).
#>
$ErrorActionPreference = "Stop"
$installRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $PSScriptRoot "install-windows.ps1") `
    -InstallPath $installRoot `
    -SourcePath $installRoot `
    -SkipFileCopy
