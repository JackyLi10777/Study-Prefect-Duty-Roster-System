@echo off
setlocal
cd /d "%~dp0"

rem Practice mode always uses its own database, backups, logs, preferences,
rem launcher port, and visible/PDF identity.
set "SING_YIN_APP_MODE=practice"
set "SING_YIN_DATABASE_PATH=%~dp0data\practice\runtime\practice.sqlite3"
set "SING_YIN_BACKUP_DIR=%~dp0data\practice\backups"
set "SING_YIN_LOG_DIR=%~dp0data\practice\logs"
set "SING_YIN_PORT=8090"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_sing_yin_roster.ps1"
set "LAUNCH_EXIT=%ERRORLEVEL%"
if "%LAUNCH_EXIT%"=="0" exit /b 0

echo.
if "%LAUNCH_EXIT%"=="2" (
    echo Practice mode has stopped.
) else (
    echo Practice mode could not be started. Review the message above.
)
echo Press any key to close this window.
pause >nul
exit /b %LAUNCH_EXIT%
