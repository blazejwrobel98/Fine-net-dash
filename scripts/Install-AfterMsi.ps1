<#
.SYNOPSIS
  Po instalacji MSI: tworzy venv, instaluje pakiety, rejestruje zadanie harmonogramu.
  Katalog instalacji = folder nadrzędny względem tego skryptu (jak w release\DividendPortfolio).
  Alternatywa: dwuklik na Dokoncz-instalacje-msi.bat w folderze scripts.
#>
$ErrorActionPreference = "Stop"
$installRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $PSScriptRoot "install-windows.ps1") `
    -InstallPath $installRoot `
    -SourcePath $installRoot `
    -SkipFileCopy
