@echo off
setlocal
cd /d "%~dp0"

echo Creating a local Python environment for this computer...

if exist ".venv" (
    echo Removing existing .venv copied from another machine...
    rmdir /s /q ".venv"
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m venv ".venv"
) else (
    py -3 -m venv ".venv"
)

if not exist ".venv\Scripts\python.exe" (
    echo Failed to create .venv. Install Python or check your PATH.
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Done. Launch with:
echo .\.venv\Scripts\python.exe .\basil_acquisition.py
endlocal
