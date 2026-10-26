@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" update_animal_log.py %*
) else (
    python update_animal_log.py %*
)
pause
