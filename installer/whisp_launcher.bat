@echo off
set PYW=%~dp0inference\venv\Scripts\pythonw.exe
set PY=%~dp0inference\venv\Scripts\python.exe
if not exist "%PYW%" (
    msg * "Whisp: Installation unvollständig. Bitte Setup erneut ausführen."
    exit /b 1
)
start "" "%PYW%" "%~dp0inference\overlay.py"
