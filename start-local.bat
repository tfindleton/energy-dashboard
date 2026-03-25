@echo off
setlocal

cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
  echo uv was not found on PATH.
  echo Install uv first: https://docs.astral.sh/uv/getting-started/installation/
  goto :error
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  uv venv .venv
  if errorlevel 1 goto :error
)

echo Installing or updating dependencies...
uv pip install --upgrade --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 goto :error

echo Dependencies are ready.
echo Starting Energy Dashboard at http://127.0.0.1:8000/
".venv\Scripts\python.exe" -m dashboard serve --host 127.0.0.1 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" goto :error

exit /b 0

:error
echo.
echo Startup failed.
pause
exit /b 1
