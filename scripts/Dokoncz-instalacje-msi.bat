@echo off
chcp 65001 >nul
title Fine Net Dash — dokończenie instalacji
cd /d "%~dp0"
echo Tworzenie venv, instalacja pakietów, rejestracja harmonogramu zadań...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AfterMsi.ps1"
if errorlevel 1 (
  echo.
  echo Wystąpił błąd — sprawdź komunikat PowerShell powyżej.
  pause
  exit /b 1
)
echo.
echo Gotowe. Uruchom Start-Dashboard.bat albo zadanie „DividendPortfolio” w harmonogramie.
pause
