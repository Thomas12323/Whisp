@echo off
setlocal
title Whisp — Release ZIP erstellen

:: Version aus Argument oder Standard
set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

set OUT=dist\whisp-v%VERSION%.zip
set TMP=dist\_release_tmp

echo.
echo  Whisp Release Builder — v%VERSION%
echo  =====================================
echo.

:: dist-Ordner erstellen
if not exist dist mkdir dist

:: Temp-Ordner leeren
if exist "%TMP%" rmdir /s /q "%TMP%"
mkdir "%TMP%"

echo  Kopiere Dateien...

:: Overlay + Python
mkdir "%TMP%\inference"
mkdir "%TMP%\inference\assets"
copy inference\overlay.py       "%TMP%\inference\" >nul
copy inference\settings.py      "%TMP%\inference\" >nul
copy inference\settings_window.py "%TMP%\inference\" >nul
copy inference\dashboard.py     "%TMP%\inference\" >nul
copy inference\hf_login.py      "%TMP%\inference\" >nul
copy inference\requirements.txt "%TMP%\inference\" >nul
copy inference\assets\whisp.ico "%TMP%\inference\assets\" >nul 2>&1

:: Logo falls vorhanden
if exist inference\assets\whisp_logo.png (
    copy inference\assets\whisp_logo.png "%TMP%\inference\assets\" >nul
)

:: Batch-Dateien
copy setup.bat   "%TMP%\" >nul
copy overlay.bat "%TMP%\" >nul
copy stop.bat    "%TMP%\" >nul

:: README
copy README.md "%TMP%\" >nul

:: ZIP erstellen (PowerShell)
echo  Erstelle ZIP...
powershell -Command "Compress-Archive -Path '%TMP%\*' -DestinationPath '%OUT%' -Force"

:: Temp aufräumen
rmdir /s /q "%TMP%"

echo.
echo  Fertig: %OUT%
echo.
echo  Jetzt auf GitHub hochladen:
echo    1. git tag v%VERSION%
echo    2. git push origin v%VERSION%
echo    3. GitHub Release erstellen und %OUT% anhängen
echo.
pause
