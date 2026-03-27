@echo off
title Whisp Setup
echo.
echo  ============================================
echo   Whisp Setup — Erstinstallation
echo  ============================================
echo.

:: Python pruefen
python --version >nul 2>&1
if errorlevel 1 (
    echo  FEHLER: Python nicht gefunden.
    echo  Bitte Python 3.11 von https://python.org installieren.
    echo  Wichtig: "Add Python to PATH" ankreuzen!
    pause
    exit /b 1
)

echo  [1/4] Erstelle virtuelle Umgebung...
cd /d "%~dp0inference"
python -m venv venv
if errorlevel 1 (
    echo  FEHLER: venv konnte nicht erstellt werden.
    pause
    exit /b 1
)

echo  [2/4] Installiere Pakete (dauert einige Minuten)...
call venv\Scripts\activate
pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo  FEHLER: Installation fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo  [3/4] HuggingFace Login
echo.
echo  Das Cohere-Modell ist ein geschuetztes Modell.
echo  Du brauchst einen kostenlosen HuggingFace-Account und musst
echo  einmalig die Nutzungsbedingungen akzeptieren:
echo.
echo    1. Gehe zu: https://huggingface.co/CohereLabs/cohere-transcribe-03-2026
echo    2. Klicke auf "Access repository" und akzeptiere die Bedingungen
echo    3. Gehe zu: https://huggingface.co/settings/tokens
echo    4. Erstelle einen Token (Read-Zugriff reicht)
echo    5. Kopiere den Token (beginnt mit "hf_...")
echo.
pause

echo.
echo  Bitte HuggingFace-Token eingeben (beginnt mit hf_):
python -c "from huggingface_hub import login; login()"

echo.
echo  [4/4] Setup abgeschlossen!
echo.
echo  Whisp starten: overlay.bat (im Hauptordner) doppelklicken
echo  Beim ersten Start wird das Modell heruntergeladen (~4 GB, einmalig).
echo.
pause
