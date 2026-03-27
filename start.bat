@echo off
title Whisp Launcher
echo.
echo   Whisp ^— starte beide Server...
echo.

start "Whisp ^| Inference Server" cmd /k "cd /d "%~dp0inference" && venv\Scripts\activate && python server.py"

timeout /t 1 /nobreak >nul

start "Whisp ^| Next.js" cmd /k "cd /d "%~dp0" && npm run dev"

echo   Inference Server  --^>  http://localhost:8000
echo   Next.js           --^>  http://localhost:3000
echo.
echo   Beide Fenster offen lassen.
echo.
pause
