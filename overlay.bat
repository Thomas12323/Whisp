@echo off
title Whisp Overlay
echo.
echo   Whisp Overlay -- Diktierwerkzeug
echo   Hotkey: Ctrl + Shift + Space (halten zum Aufnehmen)
echo.
echo   Modell und Sprache: Rechtsklick auf das Tray-Icon
echo   Beenden: Rechtsklick auf Tray-Icon ^> Beenden
echo.
cd /d "%~dp0inference"
call venv\Scripts\activate
python overlay.py
