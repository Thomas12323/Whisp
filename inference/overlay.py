"""
Whisp Overlay - systemweites Diktierwerkzeug fuer Windows.

Ctrl + Shift + Space halten -> Aufnahme startet
Space loslassen            -> Transkription + Text in aktives Fenster einfuegen
"""

import json
import logging
import os
import sys
import threading
import time
import tkinter as tk
import winreg
import winsound
from pathlib import Path

import numpy as np
import psutil
import pyperclip
import sounddevice as sd
import torch
from PIL import Image, ImageDraw
from pynput import keyboard
from pynput.keyboard import Controller as KbController, Key
from pystray import Icon, Menu, MenuItem

import settings
import settings as settings_mod

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("whisp-overlay")

COHERE_MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 16_000
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "WhispOverlay"

PUNCT_MAP: dict[str, str] = {
    "komma": ",",
    "punkt": ".",
    "ausrufezeichen": "!",
    "fragezeichen": "?",
    "doppelpunkt": ":",
    "semikolon": ";",
    "bindestrich": "-",
    "gedankenstrich": " - ",
    "neue zeile": "\n",
    "neuer absatz": "\n\n",
    "anfuehrungszeichen": '"',
    "klammer auf": "(",
    "klammer zu": ")",
    "comma": ",",
    "period": ".",
    "full stop": ".",
    "exclamation mark": "!",
    "question mark": "?",
    "colon": ":",
    "semicolon": ";",
    "new line": "\n",
    "new paragraph": "\n\n",
}

cfg = settings.load()

models: dict = {}
_model_loading = False
is_recording = False
audio_chunks: list = []
_stream = None
_pressed_keys: set = set()
_kb = KbController()
_tray_icon: Icon | None = None
_cpu_percent = 0.0
_last_stats: dict = {}
_audio_level = 0.0

_root: tk.Tk | None = None
_overlay_card: tk.Frame | None = None
_status_pill: tk.Label | None = None
_title_label: tk.Label | None = None
_detail_label: tk.Label | None = None
_meter_canvas: tk.Canvas | None = None
_hide_job = None
_dashboard = None
_overlay_state = "idle"

_ICON_BASE: Image.Image | None = None
_ICON_PATH = Path(__file__).parent / "assets" / "whisp.ico"


def _list_input_devices() -> list[dict]:
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        result = []
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) <= 0:
                continue
            hostapi_index = dev.get("hostapi", 0)
            hostapi_name = hostapis[hostapi_index]["name"] if hostapi_index < len(hostapis) else "Unknown"
            result.append(
                {
                    "index": idx,
                    "name": str(dev.get("name", f"Input {idx}")),
                    "hostapi": hostapi_name,
                    "label": f"{dev.get('name', f'Input {idx}')} [{hostapi_name}]",
                }
            )
        return result
    except Exception:
        return []


def _resolve_input_device() -> tuple[int | None, str, str]:
    devices = _list_input_devices()
    wanted_index = cfg.get("microphone", -1)
    wanted_name = cfg.get("microphone_name", "System-Standard")

    if wanted_index == -1:
        return None, "System-Standard", "Windows Default"

    for dev in devices:
        if dev["index"] == wanted_index:
            cfg["microphone_name"] = dev["label"]
            settings.save(cfg)
            return dev["index"], dev["label"], dev["hostapi"]

    for dev in devices:
        if dev["label"] == wanted_name or dev["name"] == wanted_name:
            cfg["microphone"] = dev["index"]
            cfg["microphone_name"] = dev["label"]
            settings.save(cfg)
            return dev["index"], dev["label"], dev["hostapi"]

    cfg["microphone"] = -1
    cfg["microphone_name"] = "System-Standard"
    settings.save(cfg)
    return None, "System-Standard", "Windows Default"


def _requested_model_loaded() -> bool:
    return cfg.get("model", "cohere") in models


def _current_model_status() -> str:
    if _model_loading:
        return "laedt"
    if _requested_model_loaded():
        return "bereit"
    return "nicht geladen"


def _cpu_monitor() -> None:
    global _cpu_percent
    while True:
        _cpu_percent = psutil.cpu_percent(interval=2.0)
        _update_tray_title()


def _update_tray_title() -> None:
    if _tray_icon is None:
        return
    model_label = "Cohere" if cfg["model"] == "cohere" else f"Whisper-{cfg.get('whisper_size', 'small')}"
    lang_label = cfg["language"].upper()
    status_label = _current_model_status()
    try:
        _tray_icon.title = f"Whisp  ·  {model_label}  ·  {lang_label}  ·  {status_label}  ·  CPU {_cpu_percent:.0f}%"
    except Exception:
        pass


threading.Thread(target=_cpu_monitor, daemon=True).start()


def _build_overlay() -> None:
    global _root, _overlay_card, _status_pill, _title_label, _detail_label, _meter_canvas
    _root = tk.Tk()
    _root.withdraw()
    _root.overrideredirect(True)
    _root.wm_attributes("-topmost", True)
    _root.wm_attributes("-alpha", 0.97)
    _root.wm_attributes("-toolwindow", True)
    _root.configure(bg="#0b0b12")

    _overlay_card = tk.Frame(_root, bg="#11111a", padx=18, pady=16, highlightthickness=1, highlightbackground="#26263a")
    _overlay_card.pack()

    header = tk.Frame(_overlay_card, bg="#11111a")
    header.pack(fill="x")

    _status_pill = tk.Label(header, text="Bereit", bg="#16311f", fg="#bbf7d0", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
    _status_pill.pack(side="left")

    _title_label = tk.Label(_overlay_card, text="Whisp", bg="#11111a", fg="#f5f7fb", font=("Segoe UI", 16, "bold"), anchor="w")
    _title_label.pack(fill="x", pady=(10, 2))

    _detail_label = tk.Label(_overlay_card, text="Warte auf Aufnahme", bg="#11111a", fg="#9ca3af", font=("Segoe UI", 10), anchor="w", justify="left")
    _detail_label.pack(fill="x")

    _meter_canvas = tk.Canvas(_overlay_card, width=260, height=24, bg="#11111a", highlightthickness=0, bd=0)
    _meter_canvas.pack(fill="x", pady=(12, 0))

    _animate_overlay()
    _root.mainloop()


def _get_overlay_pos(width: int, height: int) -> tuple[int, int]:
    sw = _root.winfo_screenwidth()
    sh = _root.winfo_screenheight()
    margin = 24
    pos = cfg.get("overlay_position", "bottom_right")
    if pos == "bottom_left":
        return margin, sh - height - 64
    if pos == "bottom_center":
        return (sw - width) // 2, sh - height - 64
    if pos == "top_right":
        return sw - width - margin, margin + 40
    if pos == "top_left":
        return margin, margin + 40
    return sw - width - margin, sh - height - 64


def _animate_overlay() -> None:
    if _root is None or _meter_canvas is None:
        return

    canvas = _meter_canvas
    canvas.delete("all")
    width = max(canvas.winfo_width(), 260)
    height = 24
    bars = 20
    spacing = width / bars
    level = _audio_level if _overlay_state == "recording" else 0.1 if _overlay_state == "processing" else 0.03
    if _overlay_state == "idle":
        level = 0.02

    for i in range(bars):
        x = i * spacing + spacing / 2
        phase = time.time() * (6 if _overlay_state == "recording" else 2.5)
        dynamic = abs(np.sin(phase + i * 0.45))
        amp = 4 + dynamic * 14 * max(level, 0.12)
        if _overlay_state == "idle":
            amp = 3
        top = (height / 2) - amp / 2
        bottom = (height / 2) + amp / 2
        color = "#ef4444" if _overlay_state == "recording" else "#7c3aed" if _overlay_state == "processing" else "#22c55e" if _overlay_state == "done" else "#ef4444" if _overlay_state == "error" else "#3f3f46"
        canvas.create_rectangle(x - 4, top, x + 4, bottom, fill=color, outline="")

    _root.after(50, _animate_overlay)


def _show(title: str, detail: str = "", state: str = "idle") -> None:
    if _root is None or _title_label is None or _detail_label is None or _status_pill is None:
        return

    def _update():
        global _hide_job, _overlay_state
        if _hide_job:
            _root.after_cancel(_hide_job)
            _hide_job = None

        _overlay_state = state
        state_map = {
            "idle": ("Bereit", "#16311f", "#bbf7d0"),
            "recording": ("Aufnahme", "#3b1017", "#fecdd3"),
            "processing": ("Verarbeitung", "#3b2a10", "#fde68a"),
            "done": ("Fertig", "#10271d", "#bbf7d0"),
            "error": ("Fehler", "#3a1010", "#fecaca"),
        }
        pill_text, pill_bg, pill_fg = state_map.get(state, state_map["idle"])
        _status_pill.configure(text=pill_text, bg=pill_bg, fg=pill_fg)
        _title_label.configure(text=title)
        _detail_label.configure(text=detail)

        _root.update_idletasks()
        width = max(_root.winfo_reqwidth(), 340)
        height = _root.winfo_reqheight()
        x, y = _get_overlay_pos(width, height)
        _root.geometry(f"{width}x{height}+{x}+{y}")
        _root.deiconify()
        _root.lift()

    _root.after(0, _update)


def _hide_after(ms: int = 1600) -> None:
    if _root is None:
        return

    def _schedule():
        global _hide_job
        _hide_job = _root.after(ms, _root.withdraw)

    _root.after(0, _schedule)


def _play_sound(kind: str) -> None:
    if not cfg.get("sound_feedback", True):
        return
    profile = cfg.get("sound_profile", "warm")
    patterns = {
        "warm": {"start": [(660, 45), (880, 65)], "done": [(784, 45), (988, 60), (1175, 85)], "error": [(740, 70), (620, 90)]},
        "classic": {"start": [(880, 80)], "done": [(1320, 60)], "error": [(520, 120)]},
        "soft": {"start": [(740, 35), (880, 50)], "done": [(740, 35), (880, 45), (988, 60)], "error": [(698, 55), (587, 75)]},
    }
    try:
        for freq, duration in patterns.get(profile, patterns["warm"]).get(kind, []):
            winsound.Beep(freq, duration)
    except Exception:
        pass


def _beep_start() -> None:
    _play_sound("start")


def _beep_done() -> None:
    _play_sound("done")


def _beep_error() -> None:
    _play_sound("error")


def _audio_cb(indata, frames, time_info, status) -> None:
    global _audio_level
    if is_recording:
        audio_chunks.append(indata.copy())
        _audio_level = min(1.0, float(np.abs(indata).mean()) * 8.0)


def start_recording() -> None:
    if is_recording:
        return

    if _model_loading:
        _show("Modell laedt noch", "Bitte kurz warten", "processing")
        return

    requested = cfg.get("model", "cohere")
    if requested not in models:
        if models:
            fallback = list(models.keys())[0]
            cfg["model"] = fallback
            settings.save(cfg)
            log.warning("Wechsle zu verfuegbarem Modell: %s", fallback)
        elif not _model_loading:
            _show("Modell wird geladen", "Der erste Start kann etwas dauern", "processing")
            threading.Thread(target=_load_models_then_record, daemon=True).start()
            return
        else:
            return

    _do_start_recording()


def _do_start_recording() -> None:
    global is_recording, audio_chunks, _stream, _audio_level
    audio_chunks = []
    _audio_level = 0.0
    is_recording = True

    device, mic_label, _ = _resolve_input_device()
    try:
        _stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=device, callback=_audio_cb)
        _stream.start()
        log.info("Aufnahme gestartet (Geraet: %s)", mic_label)
        _show("Aufnahme laeuft", mic_label, "recording")
        threading.Thread(target=_beep_start, daemon=True).start()
    except Exception as exc:
        is_recording = False
        _stream = None
        log.error("Mikrofon konnte nicht gestartet werden: %s", exc)
        _show("Mikrofon nicht verfuegbar", str(exc), "error")
        threading.Thread(target=_beep_error, daemon=True).start()
        _hide_after(2600)


def _load_models_then_record() -> None:
    _load_models()
    if not models:
        return
    if cfg.get("model") not in models:
        fallback = list(models.keys())[0]
        log.warning("Modell '%s' nicht verfuegbar, wechsle zu '%s'", cfg.get("model"), fallback)
        cfg["model"] = fallback
        settings.save(cfg)
        _show("Modell gewechselt", f"Cohere nicht verfuegbar -> {fallback}", "processing")
        time.sleep(1.5)
    _do_start_recording()


def stop_recording() -> None:
    global is_recording, _stream, _audio_level
    if not is_recording:
        return
    is_recording = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None
    _audio_level = 0.0
    log.info("Aufnahme gestoppt - %d Bloecke", len(audio_chunks))
    _show("Verarbeitung", "Transkription wird erstellt", "processing")
    threading.Thread(target=_transcribe_and_paste, daemon=True).start()


def _apply_punctuation(text: str) -> str:
    import re

    for spoken, symbol in sorted(PUNCT_MAP.items(), key=lambda item: -len(item[0])):
        pattern = rf"(?<![a-zA-ZaeiouAEIOUß]){re.escape(spoken)}(?![a-zA-ZaeiouAEIOUß])"
        text = re.sub(pattern, symbol, text, flags=re.IGNORECASE)
    return text.strip()


def _transcribe_and_paste() -> None:
    if not audio_chunks:
        _show("Keine Aufnahme", "Bitte erneut sprechen", "error")
        threading.Thread(target=_beep_error, daemon=True).start()
        _hide_after(2000)
        return

    audio = np.concatenate(audio_chunks, axis=0).flatten().astype(np.float32)
    duration = len(audio) / SAMPLE_RATE
    lang_arg = None if cfg["language"] == "auto" else cfg["language"]
    model_id = cfg["model"]

    max_duration = cfg.get("max_duration_sec", 0)
    if max_duration > 0 and duration > max_duration:
        audio = audio[: int(max_duration * SAMPLE_RATE)]
        duration = max_duration

    log.info("Transkribiere %.1fs | Modell=%s | Sprache=%s", duration, model_id, lang_arg or "auto")

    try:
        started = time.perf_counter()

        if model_id == "whisper":
            whisper_model = models.get("whisper")
            if whisper_model is None:
                raise RuntimeError("Whisper nicht geladen")
            segments, _ = whisper_model.transcribe(audio, language=lang_arg, beam_size=5)
            text = " ".join(segment.text.strip() for segment in segments)
        else:
            cohere = models.get("cohere")
            if cohere is None:
                raise RuntimeError("Cohere nicht geladen")
            texts = cohere["model"].transcribe(
                processor=cohere["processor"],
                audio_arrays=[audio],
                sample_rates=[SAMPLE_RATE],
                language=lang_arg,
            )
            text = texts[0]

        elapsed = time.perf_counter() - started
        text = _apply_punctuation(text.strip())
        words = len(text.split()) if text else 0
        rtf = elapsed / duration if duration > 0 else 0

        log.info("Fertig %.2fs (RTF %.2f, %d Woerter, CPU %.0f%%): %s", elapsed, rtf, words, _cpu_percent, text[:80])

        if text:
            _paste_text(text)
            _last_stats["rtf"] = rtf
            _last_stats["wpm"] = words
            _append_history({"text": text, "wpm": words, "rtf": rtf, "model": model_id, "lang": cfg.get("language", "de")})
            _show("Transkription eingefuegt", f"{words} Woerter · {elapsed:.1f}s · RTF {rtf:.2f}", "done")
            threading.Thread(target=_beep_done, daemon=True).start()
        else:
            _show("Kein Text erkannt", "Bitte deutlicher sprechen", "processing")

        _hide_after(2200)
    except Exception as exc:
        log.error("Fehler: %s", exc)
        _show("Transkription fehlgeschlagen", str(exc), "error")
        threading.Thread(target=_beep_error, daemon=True).start()
        _hide_after(3500)


def _load_history() -> list:
    history_file = settings_mod.APP_DIR / "history.json"
    if history_file.exists():
        try:
            with open(history_file, encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            pass
    return []


def _append_history(entry: dict) -> None:
    history = _load_history()
    history.insert(0, entry)
    history = history[:50]
    history_file = settings_mod.APP_DIR / "history.json"
    with open(history_file, "w", encoding="utf-8") as handle:
        json.dump(history, handle, ensure_ascii=False, indent=2)


def _paste_text(text: str) -> None:
    pyperclip.copy(text)
    time.sleep(0.18)
    _kb.press(Key.ctrl)
    _kb.press("v")
    _kb.release("v")
    _kb.release(Key.ctrl)


def _ctrl_down() -> bool:
    return Key.ctrl_l in _pressed_keys or Key.ctrl_r in _pressed_keys


def _shift_down() -> bool:
    return Key.shift in _pressed_keys or Key.shift_r in _pressed_keys


def _on_press(key) -> None:
    _pressed_keys.add(key)
    if _ctrl_down() and _shift_down() and key == Key.space and not is_recording:
        start_recording()


def _on_release(key) -> None:
    if key == Key.space and is_recording:
        stop_recording()
    _pressed_keys.discard(key)


def _autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def _toggle_autostart(icon, item) -> None:
    if _autostart_enabled():
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
            log.info("Autostart deaktiviert")
        except FileNotFoundError:
            pass
    else:
        cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        log.info("Autostart aktiviert: %s", cmd)


def _load_base_icon() -> None:
    global _ICON_BASE
    if _ICON_PATH.exists():
        try:
            _ICON_BASE = Image.open(_ICON_PATH).convert("RGBA").resize((64, 64))
        except Exception:
            pass


def _icon_image(state: str = "idle") -> Image.Image:
    size = 64
    if _ICON_BASE:
        img = _ICON_BASE.copy()
    else:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        colors = {"idle": (99, 102, 241), "recording": (220, 38, 38), "processing": (217, 119, 6), "done": (22, 163, 74), "error": (127, 29, 29)}
        bg = colors.get(state, colors["idle"])
        draw.ellipse([2, 2, 62, 62], fill=bg)
        draw.rectangle([27, 12, 37, 34], fill="white", outline="white")
        draw.arc([22, 26, 42, 42], 0, 180, fill="white", width=3)
        draw.line([32, 42, 32, 52], fill="white", width=3)
        draw.line([24, 52, 40, 52], fill="white", width=3)

    indicator_colors = {"idle": None, "recording": (239, 68, 68), "processing": (245, 158, 11), "done": (34, 197, 94), "error": (127, 29, 29)}
    color = indicator_colors.get(state)
    if color:
        overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.ellipse([44, 4, 60, 20], fill=(*color, 255), outline="white", width=1)
        img = Image.alpha_composite(img, overlay)
    return img


def _set_icon_state(state: str) -> None:
    if _tray_icon:
        try:
            _tray_icon.icon = _icon_image(state)
        except Exception:
            pass


def _open_dashboard(icon=None, item=None) -> None:
    if _root:
        _root.after(0, _launch_dashboard)


def _launch_dashboard() -> None:
    global _dashboard
    try:
        import dashboard

        if _dashboard and _dashboard.winfo_exists():
            _dashboard.deiconify()
            _dashboard.lift()
            return
        _dashboard = dashboard.Dashboard(_root, cfg, models, _get_live_stats)
    except Exception as exc:
        log.error("Dashboard Fehler: %s", exc)


def _get_live_stats() -> dict:
    process = psutil.Process()
    ram_mb = process.memory_info().rss / 1024 / 1024
    history = _load_history()
    _, mic_name, mic_host = _resolve_input_device()
    return {
        "last_rtf": _last_stats.get("rtf", 0),
        "last_wpm": _last_stats.get("wpm", 0),
        "cpu": _cpu_percent,
        "ram_mb": ram_mb,
        "history": history,
        "is_recording": is_recording,
        "audio_level": _audio_level,
        "mic_name": mic_name,
        "mic_hostapi": mic_host,
        "requested_model_loaded": _requested_model_loaded(),
        "model_loading": _model_loading,
        "loaded_models": list(models.keys()),
    }


def _open_settings(icon, item) -> None:
    if _root:
        _root.after(0, _launch_settings_window)


def _launch_settings_window() -> None:
    try:
        import settings_window

        settings_window.open(cfg, _on_settings_saved)
    except Exception as exc:
        log.error("Settings-Fenster Fehler: %s", exc)


def _on_settings_saved(new_cfg: dict) -> None:
    global cfg
    cfg = new_cfg
    settings.save(cfg)
    _update_tray_title()
    log.info("Settings gespeichert.")


def _set_model(model_name: str):
    def _handler(icon, item):
        cfg["model"] = model_name
        settings.save(cfg)
        _update_tray_title()
        if model_name in models:
            _show("Modell aktiv", f"{model_name} ist bereit", "done")
            _hide_after(1400)
        else:
            _show("Modell ausgewaehlt", f"{model_name} wird bei Bedarf geladen", "processing")
            _hide_after(1600)
        log.info("Modell -> %s", model_name)

    return _handler


def _set_lang(lang: str):
    def _handler(icon, item):
        cfg["language"] = lang
        settings.save(cfg)
        _update_tray_title()
        log.info("Sprache -> %s", lang)

    return _handler


def _set_overlay_position(position: str):
    def _handler(icon, item):
        cfg["overlay_position"] = position
        settings.save(cfg)
        label_map = {
            "bottom_right": "Unten rechts",
            "bottom_center": "Unten Mitte",
            "bottom_left": "Unten links",
            "top_right": "Oben rechts",
            "top_left": "Oben links",
        }
        _show("Position aktualisiert", label_map.get(position, position), "done")
        _hide_after(1400)

    return _handler


def _quit(icon, item) -> None:
    icon.stop()
    if _root:
        _root.after(0, _root.destroy)


def _run_tray() -> None:
    global _tray_icon

    _tray_icon = Icon(
        "Whisp",
        _icon_image("idle"),
        "Whisp  ·  Ctrl+Shift+Space",
        menu=Menu(
            MenuItem(
                "Modell",
                Menu(
                    MenuItem("Cohere Transcribe (Primaer)", _set_model("cohere"), checked=lambda item: cfg["model"] == "cohere", radio=True),
                    MenuItem("faster-whisper (Backup)", _set_model("whisper"), checked=lambda item: cfg["model"] == "whisper", radio=True),
                ),
            ),
            MenuItem(
                "Sprache",
                Menu(
                    MenuItem("Auto-Erkennung", _set_lang("auto"), checked=lambda item: cfg["language"] == "auto", radio=True),
                    MenuItem("Deutsch", _set_lang("de"), checked=lambda item: cfg["language"] == "de", radio=True),
                    MenuItem("Englisch", _set_lang("en"), checked=lambda item: cfg["language"] == "en", radio=True),
                    MenuItem("Spanisch", _set_lang("es"), checked=lambda item: cfg["language"] == "es", radio=True),
                    MenuItem("Franzoesisch", _set_lang("fr"), checked=lambda item: cfg["language"] == "fr", radio=True),
                    MenuItem("Italienisch", _set_lang("it"), checked=lambda item: cfg["language"] == "it", radio=True),
                ),
            ),
            MenuItem(
                "Overlay-Position",
                Menu(
                    MenuItem("Unten rechts", _set_overlay_position("bottom_right"), checked=lambda item: cfg.get("overlay_position") == "bottom_right", radio=True),
                    MenuItem("Unten Mitte", _set_overlay_position("bottom_center"), checked=lambda item: cfg.get("overlay_position") == "bottom_center", radio=True),
                    MenuItem("Unten links", _set_overlay_position("bottom_left"), checked=lambda item: cfg.get("overlay_position") == "bottom_left", radio=True),
                    MenuItem("Oben rechts", _set_overlay_position("top_right"), checked=lambda item: cfg.get("overlay_position") == "top_right", radio=True),
                    MenuItem("Oben links", _set_overlay_position("top_left"), checked=lambda item: cfg.get("overlay_position") == "top_left", radio=True),
                ),
            ),
            Menu.SEPARATOR,
            MenuItem("Autostart", _toggle_autostart, checked=lambda item: _autostart_enabled()),
            MenuItem("Dashboard oeffnen", _open_dashboard),
            MenuItem("Einstellungen", _open_settings),
            Menu.SEPARATOR,
            MenuItem("Beenden", _quit),
        ),
    )
    _tray_icon.run()


def _load_models() -> None:
    global _model_loading
    _model_loading = True
    _set_icon_state("processing")
    _update_tray_title()

    whisper_size = cfg.get("whisper_size", "small")

    try:
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

        log.info("Lade Cohere-Modell auf %s ...", DEVICE)
        processor = AutoProcessor.from_pretrained(COHERE_MODEL_ID, trust_remote_code=True)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(COHERE_MODEL_ID, trust_remote_code=True).to(DEVICE)
        model.eval()
        models["cohere"] = {"processor": processor, "model": model}
        log.info("Cohere geladen.")
    except Exception as exc:
        log.error("Cohere nicht geladen: %s", exc)

    try:
        from faster_whisper import WhisperModel

        compute_type = "float16" if DEVICE == "cuda" else "int8"
        models["whisper"] = WhisperModel(whisper_size, device=DEVICE, compute_type=compute_type)
        log.info("faster-whisper (%s) geladen.", whisper_size)
    except Exception as exc:
        log.warning("faster-whisper nicht verfuegbar: %s", exc)

    _model_loading = False
    _update_tray_title()
    loaded = list(models.keys())
    if loaded:
        _set_icon_state("done")
        _show("Whisp bereit", f"Geladen: {', '.join(loaded)}", "done")
        _hide_after(2500)
        threading.Thread(target=lambda: (time.sleep(2.5), _set_icon_state("idle")), daemon=True).start()
    else:
        _set_icon_state("error")
        _show("Kein Modell geladen", "Bitte HuggingFace-Zugang pruefen", "error")
        threading.Thread(target=_beep_error, daemon=True).start()


if __name__ == "__main__":
    log.info("Whisp Overlay startet - Hotkey: Ctrl+Shift+Space")
    _load_base_icon()
    log.info("Settings: %s", settings.SETTINGS_FILE)
    log.info("Konfiguration: %s", cfg)

    threading.Thread(target=_run_tray, daemon=True).start()
    log.info("Bereit. Modell wird beim ersten Hotkey-Druck geladen.")

    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.start()

    _build_overlay()
