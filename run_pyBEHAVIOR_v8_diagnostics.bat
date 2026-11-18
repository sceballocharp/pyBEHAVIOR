@echo off
set "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%.venv\Scripts\python.exe" -u "%SCRIPT_DIR%diagnose_pyBEHAVIOR_v8.py"
echo.
echo Diagnostic logs are saved in the diagnostics folder beside pyBEHAVIOR.
pause
