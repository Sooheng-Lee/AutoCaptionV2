@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PYTHON_EXE="
set "INSTALL_WHISPER=0"
set "INSTALL_CUDA=0"
set "PULL_GEMMA=0"
set "GEMMA_MODEL=gemma4"

if /I "%~1"=="--full" set "INSTALL_WHISPER=1"
if /I "%~1"=="--full" set "INSTALL_CUDA=1"
if /I "%~1"=="--with-whisper" set "INSTALL_WHISPER=1"
if /I "%~1"=="--with-cuda" set "INSTALL_CUDA=1"
if /I "%~1"=="--pull-gemma" set "PULL_GEMMA=1"
if /I "%~2"=="--with-cuda" set "INSTALL_CUDA=1"
if /I "%~2"=="--pull-gemma" set "PULL_GEMMA=1"

echo.
echo [Setup] YouTube Subtitle Translator
echo.

if exist "%VENV_DIR%\Scripts\python.exe" (
  set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
  echo [Setup] Existing virtual environment found.
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=python"
  ) else (
    where py >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_EXE=py"
    )
  )

  if "%PYTHON_EXE%"=="" (
    echo [Error] Python was not found in PATH.
    echo Install Python 3.11 or newer, then run setup.bat again.
    exit /b 1
  )

  echo [Setup] Creating virtual environment...
  "%PYTHON_EXE%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [Error] Failed to create virtual environment.
    exit /b 1
  )
  set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
)

echo [Setup] Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [Warning] pip upgrade failed. Continuing with current pip.
)

echo [Setup] Installing required packages...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [Error] Failed to install required packages.
  exit /b 1
)

if "%INSTALL_WHISPER%"=="1" (
  echo [Setup] Installing faster-whisper for real speech recognition...
  "%PYTHON_EXE%" -m pip install faster-whisper
  if errorlevel 1 (
    echo [Warning] faster-whisper installation failed.
    echo The app will still run, but transcription will use placeholder text.
  )
) else (
  echo [Setup] Skipping faster-whisper.
  echo         Run setup.bat --with-whisper for real local speech recognition.
)

if "%INSTALL_CUDA%"=="1" (
  echo [Setup] Installing CUDA cuBLAS/cuDNN Python wheels for GPU transcription...
  "%PYTHON_EXE%" -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
  if errorlevel 1 (
    echo [Warning] CUDA Python wheel installation failed.
    echo           The app can still run in CPU mode.
  )
) else (
  echo [Setup] Skipping CUDA Python wheels.
  echo         Run setup.bat --with-cuda to install cuBLAS/cuDNN DLLs for GPU transcription.
)

echo.
echo [Setup] Checking optional external tools...

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [Warning] ffmpeg was not found.
  echo           The app will use imageio-ffmpeg from the virtual environment when available.
) else (
  echo [OK] ffmpeg found.
)

where node >nul 2>nul
if errorlevel 1 (
  echo [Warning] Node.js was not found.
  echo           yt-dlp may warn that no JavaScript runtime is available for YouTube extraction.
) else (
  echo [OK] Node.js found.
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo [Warning] Ollama was not found.
  echo           Gemma translation will use fallback text until Ollama and the model are configured.
) else (
  echo [OK] Ollama found.
  if "%PULL_GEMMA%"=="1" (
    echo [Setup] Pulling Gemma model: %GEMMA_MODEL%
    ollama pull "%GEMMA_MODEL%"
    if errorlevel 1 (
      echo [Warning] Failed to pull %GEMMA_MODEL%.
      echo           Check the Ollama model name or set it in the app settings.
    )
  ) else (
    echo         Run setup.bat --pull-gemma to pull the default Gemma model.
  )
)

if exist "%SystemRoot%\System32\cublas64_12.dll" (
  echo [OK] CUDA cublas64_12.dll found.
) else (
  echo [Info] CUDA cublas64_12.dll was not found.
  echo        The app can also use CUDA DLLs installed by setup.bat --with-cuda.
)

echo.
echo [Setup] Verifying application imports...
"%PYTHON_EXE%" -c "from translator_app.ui.main_window import MainWindow; import yt_dlp, requests, platformdirs; print('Application imports OK')"
if errorlevel 1 (
  echo [Error] Import verification failed.
  exit /b 1
)

echo.
echo [Setup] Done.
echo Run the app with:
echo   run_app.bat
echo.
echo Test the provided video with:
echo   test_video.bat
echo.
