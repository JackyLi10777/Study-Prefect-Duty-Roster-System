@echo off
setlocal
cd /d "%~dp0"

rem Keep the double-click entry point small. The PowerShell launcher owns all
rem port checks, duplicate-launch protection, readiness polling, and messages.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_sing_yin_roster.ps1"
set "LAUNCH_EXIT=%ERRORLEVEL%"

rem Exit code 0 means an already-running service was opened successfully.
rem Exit code 2 means the child application stopped; keep the window visible.
if "%LAUNCH_EXIT%"=="0" exit /b 0

echo.
if "%LAUNCH_EXIT%"=="2" (
    echo The Sing Yin system has stopped.
) else (
    echo The Sing Yin system could not be started. Review the message above.
)
echo Press any key to close this window.
pause >nul
exit /b %LAUNCH_EXIT%
