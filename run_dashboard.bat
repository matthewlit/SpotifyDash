@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Virtual environment Python not found at .venv\Scripts\python.exe
  echo Falling back to system Python...
  set "PYTHON=python"
)

echo Starting Spotify All-Time Dashboard...
"%PYTHON%" -m streamlit --version >nul 2>&1
if errorlevel 1 (
  echo Installing dependencies...
  "%PYTHON%" -m pip install -r requirements.txt
)

echo Starting Spotify Account Dashboard...
"%PYTHON%" -m streamlit run app.py

endlocal
