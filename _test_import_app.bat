@echo off
cd /d "D:\code\Study-Prefect-Duty-Roster-System"
set PYEXE=C:\Users\lichu\AppData\Local\Microsoft\WindowsApps\python.exe
if not exist "%PYEXE%" (
  echo Python stub not found.
  exit /b 1
)
echo Running import test with %PYEXE%
"%PYEXE%" -c "import sys; print('Python:', sys.executable); import app; print('? Import ??')" 2>&1
echo Exit code: %ERRORLEVEL%
exit /b %ERRORLEVEL%
