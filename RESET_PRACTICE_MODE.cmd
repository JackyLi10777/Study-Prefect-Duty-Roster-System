@echo off
setlocal
cd /d "%~dp0"

python.exe -X utf8 "%~dp0scripts\reset_practice_mode.py"
if errorlevel 1 (
    echo.
    echo Practice data was not reset. Review the message above.
    echo Press any key to close this window.
    pause >nul
    exit /b 1
)

call "%~dp0START_PRACTICE_MODE.cmd"
exit /b %ERRORLEVEL%
