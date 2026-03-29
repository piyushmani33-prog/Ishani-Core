@echo off
setlocal
cd /d "%~dp0\backend_python"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
) else if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" app.py
) else if exist ".venv\Scripts\py.exe" (
  ".venv\Scripts\py.exe" -3 app.py
) else if exist "venv\Scripts\py.exe" (
  "venv\Scripts\py.exe" -3 app.py
) else if exist "%LocalAppData%\Microsoft\WindowsApps\python.exe" (
  "%LocalAppData%\Microsoft\WindowsApps\python.exe" app.py
) else if exist "%SystemRoot%\py.exe" (
  "%SystemRoot%\py.exe" -3 app.py
) else (
  py -3 app.py
)
endlocal
