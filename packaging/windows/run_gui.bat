@echo off
setlocal

cd /d "%~dp0\..\.."

set "APPDIR=dist\yt_cut_merge_gui"
set "APP=%APPDIR%\yt_cut_merge_gui.exe"
set "TOOLS=tools"
set "YTDLP=%TOOLS%\yt-dlp.exe"

if not exist "%APP%" (
    echo ERRORE: %APP% non trovato.
    pause
    exit /b 1
)

if exist "%YTDLP%" (
    echo Aggiorno yt-dlp...
    "%YTDLP%" -U
)

if not "%~1"=="" (
    start "" "%APP%" --url "%~1"
) else (
    start "" "%APP%"
)

endlocal
exit /b 0
