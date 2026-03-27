"""
Whisp — Post-Install Script
Findet das System-Python (via py.exe Launcher), erstellt ein venv und installiert Dependencies.
"""
import subprocess
import sys
import shutil
from pathlib import Path


def find_python() -> str:
    """Findet Python 3.10+ über py.exe Launcher oder direkt."""
    # py.exe Launcher (Standard bei Python-Installation auf Windows)
    for candidate in ["py", "python", "python3"]:
        try:
            r = subprocess.run([candidate, "--version"], capture_output=True, text=True)
            if r.returncode == 0 and "3." in r.stdout:
                version = r.stdout.strip().split()[1]
                major, minor = int(version.split(".")[0]), int(version.split(".")[1])
                if major == 3 and minor >= 10:
                    return candidate
        except FileNotFoundError:
            continue

    # Registry-Suche
    try:
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for subkey in [r"SOFTWARE\Python\PythonCore", r"SOFTWARE\WOW6432Node\Python\PythonCore"]:
                try:
                    key = winreg.OpenKey(hive, subkey)
                    i = 0
                    while True:
                        try:
                            ver = winreg.EnumKey(key, i)
                            major, minor = int(ver.split(".")[0]), int(ver.split(".")[1])
                            if major == 3 and minor >= 10:
                                install_key = winreg.OpenKey(key, f"{ver}\\InstallPath")
                                path = winreg.QueryValueEx(install_key, "ExecutablePath")[0]
                                if Path(path).exists():
                                    return path
                        except (ValueError, OSError):
                            pass
                        i += 1
                except OSError:
                    pass
    except Exception:
        pass

    return None


def main():
    app_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    venv    = app_dir / "inference" / "venv"
    req     = app_dir / "inference" / "requirements.txt"
    log     = open(app_dir / "install.log", "w", encoding="utf-8")

    def run(cmd):
        log.write(f"\n>>> {' '.join(str(c) for c in cmd)}\n")
        log.flush()
        r = subprocess.run(cmd, stdout=log, stderr=log)
        log.write(f">>> Exit: {r.returncode}\n")
        log.flush()
        return r.returncode

    log.write("=== Whisp Installation ===\n")
    log.write(f"App: {app_dir}\n")

    py = find_python()
    if not py:
        log.write("FEHLER: Python 3.10+ nicht gefunden!\n")
        log.close()
        # Fehlermeldung per msgbox
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "Python 3.10 oder höher ist nicht installiert.\n\n"
            "Bitte Python von python.org herunterladen und Whisp Setup erneut ausführen.",
            "Whisp — Python fehlt",
            0x10
        )
        return

    log.write(f"Python: {py}\n")

    # venv erstellen
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)

    if run([py, "-m", "venv", str(venv)]) != 0:
        log.write("FEHLER: venv konnte nicht erstellt werden!\n")
        log.close()
        return

    pip = venv / "Scripts" / "pip.exe"
    run([pip, "install", "--upgrade", "pip", "--quiet"])
    code = run([pip, "install", "-r", str(req), "--quiet"])

    if code != 0:
        log.write("FEHLER: pip install fehlgeschlagen!\n")
    else:
        log.write("\n=== Fertig ===\n")

    log.close()


if __name__ == "__main__":
    main()
