@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PYTHON_EXE="
set "INSTALL_WHISPER=0"
set "INSTALL_CUDA=0"
set "PULL_GEMMA=0"
set "GEMMA_MODEL=gemma4"

REM Python detection (always run to find python)
set "DETECTED_PYTHON="
set "PYTHON_STATUS=미설치 (설치 필요)"
where python >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_STATUS=설치됨 (PATH)"
  set "DETECTED_PYTHON=python"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_STATUS=설치됨 (py)"
    set "DETECTED_PYTHON=py"
  ) else (
    if exist "%USERPROFILE%\miniconda3\python.exe" (
      set "PYTHON_STATUS=설치됨 (Miniconda)"
      set "DETECTED_PYTHON=%USERPROFILE%\miniconda3\python.exe"
    ) else if exist "%USERPROFILE%\anaconda3\python.exe" (
      set "PYTHON_STATUS=설치됨 (Anaconda)"
      set "DETECTED_PYTHON=%USERPROFILE%\anaconda3\python.exe"
    ) else (
      for /d %%d in ("%USERPROFILE%\AppData\Local\Programs\Python\Python*") do (
        if exist "%%d\python.exe" (
          set "PYTHON_STATUS=설치됨 (AppData)"
          set "DETECTED_PYTHON=%%d\python.exe"
        )
      )
    )
  )
)

if not "%~1"=="" goto PARSE_ARGS

:INTERACTIVE_MODE
echo ==================================================
echo   YouTube Subtitle Translator - PC 맞춤 설정 마법사
echo ==================================================
echo.
echo 현재 PC 사양 및 설치 상태를 확인하는 중입니다...
echo.

REM 2. GPU Check
set "HAS_NVIDIA=0"
set "GPU_NAME=CPU (내장 그래픽 또는 감지 실패)"
for /f "delims=" %%a in ('powershell -command "if (Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like '*NVIDIA*' }) { '1' } else { '0' }" 2^>nul') do set "HAS_NVIDIA=%%a"
for /f "delims=" %%a in ('powershell -command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | Select-String -Pattern 'NVIDIA', 'AMD', 'Intel' | Select-Object -First 1" 2^>nul') do set "GPU_NAME=%%a"

REM 3. RAM Check
set "SYSTEM_RAM_GB=8"
for /f %%a in ('powershell -command "[math]::round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB)" 2^>nul') do set "SYSTEM_RAM_GB=%%a"
if "!SYSTEM_RAM_GB!"=="" set "SYSTEM_RAM_GB=8"
set "SYSTEM_RAM_GB=!SYSTEM_RAM_GB: =!"

REM 4. Ollama Check
set "OLLAMA_STATUS=미설치 (로컬 번역 사용 시 설치 권장)"
set "HAS_OLLAMA=0"
where ollama >nul 2>nul
if not errorlevel 1 (
  set "OLLAMA_STATUS=설치됨"
  set "HAS_OLLAMA=1"
)

REM 5. FFmpeg Check
set "FFMPEG_STATUS=미설치 (가상환경 내 imageio-ffmpeg 사용 예정)"
where ffmpeg >nul 2>nul
if not errorlevel 1 (
  set "FFMPEG_STATUS=설치됨"
)

REM 6. Node.js Check
set "NODE_STATUS=미설치 (yt-dlp 경고가 발생할 수 있음)"
where node >nul 2>nul
if not errorlevel 1 (
  set "NODE_STATUS=설치됨"
)

echo [PC 사양 정보]
echo - GPU: !GPU_NAME!
echo - RAM: !SYSTEM_RAM_GB! GB
echo.
echo [외부 도구 설치 상태]
echo - Python: !PYTHON_STATUS!
echo - Ollama (로컬 LLM): !OLLAMA_STATUS!
echo - FFmpeg (미디어 변환): !FFMPEG_STATUS!
echo - Node.js (추출 도움): !NODE_STATUS!
echo ==================================================
echo.
echo 설치 방식을 선택해주세요:
echo   1. 권장 설치 (현재 PC 사양에 최적화된 설정을 자동으로 감지하여 설치)
echo   2. 사용자 지정 설치 (설치할 패키지를 단계별로 직접 선택)
echo   3. 최소 설치 (가장 기본적인 CPU 패키지만 설치, 약 50MB)
echo.

set "MODE_CHOICE="
set /p "MODE_CHOICE=선택 (기본값: 1): "
if "!MODE_CHOICE!"=="" set "MODE_CHOICE=1"
set "MODE_CHOICE=!MODE_CHOICE: =!"

if "!MODE_CHOICE!"=="1" goto RECOMMEND_SETUP
if "!MODE_CHOICE!"=="2" goto CUSTOM_SETUP
if "!MODE_CHOICE!"=="3" goto MINIMAL_SETUP
echo 잘못된 입력입니다. 권장 설치(1)로 진행합니다.
timeout /t 2 >nul
goto RECOMMEND_SETUP

:RECOMMEND_SETUP
echo.
echo [권장 설치 설정 구성 중...]
set "INSTALL_WHISPER=1"

if "!HAS_NVIDIA!"=="1" (
  set "INSTALL_CUDA=1"
  echo - NVIDIA GPU 감지: CUDA 가속 패키지 설치 예정 - 빠른 음성 인식 가능
) else (
  set "INSTALL_CUDA=0"
  echo - NVIDIA GPU 미감지: CPU 모드로 설치 예정
)

if "!HAS_OLLAMA!"=="1" (
  set "PULL_GEMMA=1"
  if !SYSTEM_RAM_GB! GEQ 16 (
    set "GEMMA_MODEL=gemma2:2b"
    echo - 16GB 이상 RAM 감지: Gemma 2 2B 모델 다운로드 예정
  ) else (
    set "GEMMA_MODEL=gemma:2b"
    echo - 8GB 이하 RAM 감지: 경량 Gemma 2B 모델 다운로드 예정
  )
) else (
  set "PULL_GEMMA=0"
  echo - Ollama 미감지: 로컬 Gemma 번역 모델 다운로드 건너뜀
)
goto CONFIRM_INSTALL

:CUSTOM_SETUP
echo.
echo ==================================================
echo   사용자 지정 설치 설정
echo ==================================================
echo.

if "!HAS_NVIDIA!"=="1" (
  echo NVIDIA GPU !GPU_NAME! 이 감지되었습니다.
  set "USER_CUDA="
  set /p "USER_CUDA=CUDA 가속(GPU 번역/음성인식)을 설치하시겠습니까? [Y/n]: "
  if "!USER_CUDA!"=="" set "USER_CUDA=Y"
) else (
  echo NVIDIA GPU가 감지되지 않았습니다.
  set "USER_CUDA="
  set /p "USER_CUDA=CUDA 가속 패키지를 설치하시겠습니까? (NVIDIA GPU와 드라이버가 없으면 실패할 수 있습니다) [y/N]: "
  if "!USER_CUDA!"=="" set "USER_CUDA=N"
)
set "USER_CUDA=!USER_CUDA: =!"
if /I "!USER_CUDA!"=="Y" (
  set "INSTALL_CUDA=1"
) else (
  set "INSTALL_CUDA=0"
)

set "USER_WHISPER="
set /p "USER_WHISPER=로컬 고성능 음성 인식(faster-whisper)을 설치하시겠습니까? [Y/n]: "
if "!USER_WHISPER!"=="" set "USER_WHISPER=Y"
set "USER_WHISPER=!USER_WHISPER: =!"
if /I "!USER_WHISPER!"=="Y" (
  set "INSTALL_WHISPER=1"
) else (
  set "INSTALL_WHISPER=0"
)

if "!HAS_OLLAMA!"=="1" (
  set "USER_GEMMA="
  set /p "USER_GEMMA=Ollama 번역 모델(Gemma)을 자동으로 다운로드하시겠습니까? [Y/n]: "
  if "!USER_GEMMA!"=="" set "USER_GEMMA=Y"
  set "USER_GEMMA=!USER_GEMMA: =!"
  if /I "!USER_GEMMA!"=="Y" (
    set "PULL_GEMMA=1"
    echo.
    echo 다운로드할 모델을 선택하세요:
    echo   1. gemma2:2b [약 1.6GB, 추천 - 최신 경량 모델]
    echo   2. gemma:2b [약 1.7GB, 구형 경량 모델]
    echo   3. gemma2 [9B, 약 5.5GB, 고사양 GPU 및 RAM 16GB 이상 필요]
    echo   4. gemma4 [프로젝트 기본값]
    echo   5. 직접 입력
    echo.
    set "MODEL_CHOICE="
    set /p "MODEL_CHOICE=선택 (기본값: 1): "
    if "!MODEL_CHOICE!"=="" set "MODEL_CHOICE=1"
    set "MODEL_CHOICE=!MODEL_CHOICE: =!"
    
    if "!MODEL_CHOICE!"=="1" set "GEMMA_MODEL=gemma2:2b"
    if "!MODEL_CHOICE!"=="2" set "GEMMA_MODEL=gemma:2b"
    if "!MODEL_CHOICE!"=="3" set "GEMMA_MODEL=gemma2"
    if "!MODEL_CHOICE!"=="4" set "GEMMA_MODEL=gemma4"
    if "!MODEL_CHOICE!"=="5" (
      set /p "GEMMA_MODEL=Ollama 모델 이름 입력: "
      set "GEMMA_MODEL=!GEMMA_MODEL: =!"
    )
  ) else (
    set "PULL_GEMMA=0"
  )
) else (
  echo [Info] Ollama가 설치되어 있지 않아 로컬 Gemma 번역 모델 다운로드를 건너뜁니다.
  set "PULL_GEMMA=0"
)
goto CONFIRM_INSTALL

:MINIMAL_SETUP
echo.
echo [최소 설치 설정 적용 중...]
set "INSTALL_WHISPER=0"
set "INSTALL_CUDA=0"
set "PULL_GEMMA=0"
goto CONFIRM_INSTALL

:CONFIRM_INSTALL
echo.
echo ==================================================
echo   설치 정보 요약
echo ==================================================
echo - 가상환경 폴더: !VENV_DIR!
echo - 음성인식 엔진(faster-whisper) 설치: !INSTALL_WHISPER! (1:설치, 0:미설치)
echo - GPU CUDA 라이브러리 설치: !INSTALL_CUDA! (1:설치, 0:미설치)
echo - Ollama Gemma 모델 다운로드: !PULL_GEMMA! (1:다운로드, 0:건너뜀)
if "!PULL_GEMMA!"=="1" echo   - 다운로드 모델명: !GEMMA_MODEL!
echo ==================================================
echo.

set "CONFIRM="
set /p "CONFIRM=이 설정으로 설치를 시작하시겠습니까? [Y/n]: "
if "!CONFIRM!"=="" set "CONFIRM=Y"
set "CONFIRM=!CONFIRM: =!"
if /I "!CONFIRM!"=="Y" (
  goto RUN_SETUP
) else (
  echo 설치를 취소하고 설정 마법사를 다시 시작합니다.
  timeout /t 2 >nul
  cls
  goto INTERACTIVE_MODE
)

:PARSE_ARGS
if /I "%~1"=="--full" set "INSTALL_WHISPER=1"
if /I "%~1"=="--full" set "INSTALL_CUDA=1"
if /I "%~1"=="--with-whisper" set "INSTALL_WHISPER=1"
if /I "%~1"=="--with-cuda" set "INSTALL_CUDA=1"
if /I "%~1"=="--pull-gemma" set "PULL_GEMMA=1"
if /I "%~2"=="--with-cuda" set "INSTALL_CUDA=1"
if /I "%~2"=="--pull-gemma" set "PULL_GEMMA=1"

:RUN_SETUP
echo.
echo [Setup] 가상 환경 및 패키지 설치를 진행합니다...
echo.


if exist "%VENV_DIR%\Scripts\python.exe" (
  set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
  echo [Setup] Existing virtual environment found.
) else (
  if not "!DETECTED_PYTHON!"=="" (
    set "PYTHON_EXE=!DETECTED_PYTHON!"
  )

  if "!PYTHON_EXE!"=="" (
    echo [Error] Python was not found on this system.
    echo Install Python 3.11 or newer, then run setup.bat again.
    exit /b 1
  )

  echo [Setup] Creating virtual environment...
  "!PYTHON_EXE!" -m venv "%VENV_DIR%"
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
if "!PULL_GEMMA!"=="1" (
  echo.
  echo [!] Ollama에서 '!GEMMA_MODEL!' 모델을 다운로드했습니다.
  echo     앱 실행 후 설정 화면에서 Gemma 모델명을 '!GEMMA_MODEL!'으로 지정하여 사용해주세요.
)
echo.
echo Run the app with:
echo   run_app.bat
echo.
echo Test the provided video with:
echo   test_video.bat
echo.
