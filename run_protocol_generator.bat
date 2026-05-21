@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" protocol_generator.py
) else (
    python protocol_generator.py
)
