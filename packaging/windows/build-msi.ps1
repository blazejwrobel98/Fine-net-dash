<#
.SYNOPSIS
  Builds release\DividendPortfolio (if needed) and produces release\FineNetDash.msi using WiX.

.PARAMETER Version
  MSI product version (four numeric parts), e.g. 0.2.0.0

.EXAMPLE
  dotnet tool install --global wix
  .\packaging\windows\build-msi.ps1 -Version 0.2.0.0
#>
param(
    [string]$Version = "0.1.0.0",
    [switch]$SkipReleaseBuild
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $here "..\..")).Path
$payload = Join-Path $repoRoot "release\DividendPortfolio"
$wxsIn = Join-Path $here "Package.wxs"
$wxsWork = Join-Path $here "obj\Package.gen.wxs"
$msiOut = Join-Path $repoRoot "release\FineNetDash.msi"

if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
    throw "WiX CLI not found. Install: dotnet tool install --global wix`nThen add %USERPROFILE%\.dotnet\tools to PATH."
}

if (-not $SkipReleaseBuild) {
    & (Join-Path $repoRoot "scripts\build-release.ps1")
}

if (-not (Test-Path (Join-Path $payload "backend\app\main.py"))) {
    throw "Missing payload at $payload — run scripts\build-release.ps1 first."
}

if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') {
    throw "Version must be four numeric parts (e.g. 1.0.0.0), got: $Version"
}

New-Item -ItemType Directory -Path (Split-Path $wxsWork) -Force | Out-Null
(Get-Content $wxsIn -Raw -Encoding UTF8).Replace("__MSI_VERSION__", $Version) | Set-Content $wxsWork -Encoding UTF8

New-Item -ItemType Directory -Path (Split-Path $msiOut) -Force | Out-Null
Push-Location $here
try {
    wix build "obj\Package.gen.wxs" `
        -bindpath "Payload=$payload" `
        -out $msiOut
} finally {
    Pop-Location
}

Write-Host "MSI: $msiOut"
