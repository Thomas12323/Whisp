"""
Whisp — Settings Manager
Liest/schreibt %APPDATA%\Whisp\settings.json
"""
import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Whisp"
SETTINGS_FILE = APP_DIR / "settings.json"

DEFAULTS: dict = {
    "hotkey":           "ctrl+shift+space",
    "model":            "cohere",
    "language":         "de",
    "microphone":       -1,          # -1 = System-Default
    "overlay_position": "bottom_right",
    "sound_feedback":   True,
    "autostart":        False,
    "max_duration_sec": 0,           # 0 = unbegrenzt
    "mode":             "hold",
    "whisper_size":     "small",
}


def load() -> dict:
    """Lädt Settings. Fehlende Keys werden mit Defaults aufgefüllt."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            # Fehlende Keys aus Defaults ergänzen
            merged = {**DEFAULTS, **stored}
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    """Speichert Settings nach %APPDATA%\Whisp\settings.json"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get(key: str):
    """Einzelnen Wert laden."""
    return load().get(key, DEFAULTS.get(key))


def set_value(key: str, value) -> None:
    """Einzelnen Wert speichern."""
    cfg = load()
    cfg[key] = value
    save(cfg)
