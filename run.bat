@echo off
title MP4 to Text Converter
setlocal

cd /d "%~dp0"

set "VENV_PY=%~dp0venv\Scripts\python.exe"

echo ================================
echo   Starting Server...
echo ================================
echo.

REM Check venv python
if not exist "%VENV_PY%" (
    echo [ERROR] venv Python not found.
    echo Create venv first:
    echo   python -m venv venv
    pause
    exit /b 1
)

REM Check packages
echo Checking packages...
"%VENV_PY%" -c "import fastapi, uvicorn, whisper, pydub, dotenv; from google import genai" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    echo This may take a few minutes on first run...
    echo.
    "%VENV_PY%" -m pip install -r requirements.txt
    echo.
    echo Installation complete!
) else (
    echo All packages are already installed.
)

echo.
echo ================================
echo   Server URL: http://localhost:8000
echo   Browser will open automatically
echo   Press Ctrl+C to stop
echo ================================
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM Run server with venv python
"%VENV_PY%" start_server.py

pause
