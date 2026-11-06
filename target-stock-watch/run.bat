@echo off
cd /d "%~dp0"

rem Pick a Python: prefer the py launcher, fall back to python.exe
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (
  python -c "import sys" >nul 2>nul && set PY=python
)
if not defined PY (
  echo.
  echo Python 3 was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup, then run this again.
  echo.
  pause
  exit /b 1
)

if not exist .venv (
  echo First run: setting things up, this takes a few minutes...
  %PY% -m venv .venv || goto :fail
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt || goto :fail
  python -m playwright install chromium || goto :fail
) else (
  call .venv\Scripts\activate.bat
)

python target_stock_watch.py %*
pause
exit /b 0

:fail
echo.
echo Setup failed - see the error above. Delete the .venv folder and try again.
pause
exit /b 1
