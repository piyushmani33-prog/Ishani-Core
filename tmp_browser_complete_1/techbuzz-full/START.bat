@echo off
setlocal
title TechBuzz Empire - Ishani Core v9
echo.
echo ======================================================
echo   TechBuzz Empire - Leazy Jinn Mother Brain v9
echo   52 Living Brains | Carbon Protocol | Accounts AI
echo ======================================================
echo.
cd /d "%~dp0"
set PYTHONPATH=%~dp0

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment...
    ".venv\Scripts\python.exe" app.py
) else if exist "venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
endlocal
