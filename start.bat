@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Created .env. Edit OPENAI_API_KEY and REMOTIFY_TOKEN, then run start.bat again.
  pause
  exit /b 0
)

python -m app.main
pause
