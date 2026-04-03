@echo off
setlocal enabledelayedexpansion
echo === 独轮车 DL Cart Builder ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Install from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install pyinstaller yt-dlp
if errorlevel 1 ( echo ERROR: pip failed. && pause && exit /b 1 )

echo.
echo [2/3] Downloading FFmpeg to bundle into exe...
if exist ffmpeg.exe (
    echo FFmpeg already present, skipping download.
) else (
    set "FURL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    set "FZIP=%TEMP%\ffmpeg_dl.zip"
    powershell -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '!FURL!' -OutFile '!FZIP!' -UseBasicParsing"
    if !errorlevel! neq 0 (
        echo ERROR: FFmpeg download failed. Check network and retry.
        pause
        exit /b 1
    )
    powershell -Command "Expand-Archive -Path '!FZIP!' -DestinationPath '%TEMP%\ffmpeg_ext' -Force"
    for /d %%d in ("%TEMP%\ffmpeg_ext\ffmpeg-*") do (
        copy /Y "%%d\bin\ffmpeg.exe"  "ffmpeg.exe"  >nul
        copy /Y "%%d\bin\ffprobe.exe" "ffprobe.exe" >nul
    )
    del /q "!FZIP!" 2>nul
    rmdir /s /q "%TEMP%\ffmpeg_ext" 2>nul
    echo FFmpeg ready.
)

echo.
echo [3/3] Building exe (bundling ffmpeg inside)...
python -m PyInstaller --onefile --windowed --collect-all yt_dlp ^
    --add-binary "ffmpeg.exe;." ^
    --add-binary "ffprobe.exe;." ^
    --name DLCart ytdlp_gui.py
if errorlevel 1 ( echo ERROR: build failed. && pause && exit /b 1 )

echo.
echo Done! dist\DLCart.exe is ready.
echo FFmpeg is bundled inside - users need nothing extra.
echo.
pause
