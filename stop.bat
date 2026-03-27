@echo off
title Whisp Stop
echo.
echo   Stopping Whisp...
echo.

taskkill /F /IM python.exe 2>nul && echo   python.exe beendet. || echo   python.exe lief nicht.
taskkill /F /IM node.exe   2>nul && echo   node.exe beendet.   || echo   node.exe lief nicht.

echo.
echo   Fertig.
echo.
pause
