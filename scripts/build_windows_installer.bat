@echo off
setlocal

cd /d "%~dp0\.."

echo ================================
echo   Build Windows Installer
echo ================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERRORE: Python launcher (py) non trovato.
    pause
    exit /b 1
)

where iscc >nul 2>nul
if errorlevel 1 (
    echo ERRORE: Inno Setup Compiler (iscc) non trovato nel PATH.
    echo Installa Inno Setup e assicurati che ISCC.exe sia nel PATH.
    pause
    exit /b 1
)

echo [1/4] Installo/aggiorno PyInstaller...
py -m pip install -U pyinstaller
if errorlevel 1 (
    echo ERRORE: installazione PyInstaller fallita.
    pause
    exit /b 1
)

echo.
echo [2/4] Preparo tools...
py scripts\setup_video_tools_windows.py
if errorlevel 1 (
    echo ERRORE: setup_video_tools_windows.py fallito.
    pause
    exit /b 1
)

echo.
echo [3/4] Build PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
py -m PyInstaller packaging\windows\yt_cut_merge_gui.spec
if errorlevel 1 (
    echo ERRORE: build PyInstaller fallita.
    pause
    exit /b 1
)

echo.
echo [4/4] Build installer Inno Setup...
if exist installer rmdir /s /q installer
iscc packaging\windows\yt_cut_merge_installer.iss
if errorlevel 1 (
    echo ERRORE: build installer fallita.
    pause
    exit /b 1
)

echo.
echo =========================================
echo   Completato
echo =========================================
echo Installer pronto in:
echo   installer\yt_cut_merge_setup.exe
echo.
pause
endlocal
