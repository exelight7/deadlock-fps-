@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failure
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto failure
)
.venv\Scripts\python.exe main.py
if errorlevel 1 goto failure
exit /b 0
:failure
echo Install Python 3.12 and try again, or download the portable build.
pause
exit /b 1
