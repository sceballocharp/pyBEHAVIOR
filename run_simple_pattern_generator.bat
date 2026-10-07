@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" "braincodec\simple_pattern_generator.py"
if errorlevel 1 pause
