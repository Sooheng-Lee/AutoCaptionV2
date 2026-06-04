@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  call setup.bat
)

".venv\Scripts\python.exe" -m translator_app.cli "https://www.youtube.com/watch?v=PaCmpygFfXo" --language Korean --cpu --output-dir ".appdata\test-outputs" --model-dir ".appdata\test-models"
