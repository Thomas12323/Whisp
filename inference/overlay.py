"""
Whisp Overlay — systemweites Diktierwerkzeug für Windows.

Ctrl + Shift + Space halten → Aufnahme startet
Space loslassen            → Transkription + Text in aktives Fenster einfügen

Tray-Icon: Modell/Sprache wechseln, Einstellungen, Autostart, Beenden.
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
import numpy as np
import psutil
import sounddevice as sd
import torch
import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller as KbController, Key
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("whisp-overlay")

# ── Konfiguration ─────────────────────────────────────────────────────────────
COHERE_MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
DEVICE          = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE     = 16_000
AUTOSTART_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME  = "WhispOverlay"

# Gesprochene Satzzeichen → echte Zeichen (DE + EN)
PUNCT_MAP: dict[str, str] = {
    "komma": ",",
    "punkt": ".",
    "ausrufezeichen": "!",
    "fragezeichen": "?",
    "doppelpunkt": ":",
    "semikolon": ";",
    "bindestrich": "-",
    "gedankenstrich": " – ",
    "neue zeile": "\n",
    "neuer absatz": "\n\n",
    "anführungszeichen": '"',
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

# ── Settings ──────────────────────────────────────────────────────────────────
cfg = settings.load()

# ── Zustand ───────────────────────────────────────────────────────────────────
models: dict            = {}
_model_loading: bool    = False
is_recording: bool      = False
audio_chunks: list      = []
_stream                 = None
_pressed_keys: set      = set()
_kb                     = KbController()
_tray_icon: Icon | None = None
_cpu_percent: float     = 0.0
_last_stats: dict       = {}
_audio_level: float     = 0.0


# ── CPU-Monitor ───────────────────────────────────────────────────────────────
def _cpu_monitor() -> None:
    global _cpu_percent
    while True:
        _cpu_percent = psutil.cpu_percent(interval=2.0)
        _update_tray_title()


def _update_tray_title() -> None:
    if _tray_icon is None:
        return
    model_label = "Cohere" if cfg["model"] == "cohere" else f"Whisper-{cfg.get('whisper_size','small')}"
    lang_label  = cfg["language"].upper()
    try:
        _tray_icon.title = f"Whisp  ·  {model_label}  ·  {lang_label}  ·  CPU {_cpu_percent:.0f}%"
    except Exception:
        pass


threading.Thread(target=_cpu_monitor, daemon=True).start()


# ── Overlay-Fenster ───────────────────────────────────────────────────────────
_root: tk.Tk | None     = None
_label: tk.Label | None = None
_hide_job               = None


def _build_overlay() -> None:
    global _root, _label
    _root = tk.Tk()
    _root.withdraw()
    _root.overrideredirect(True)
    _root.wm_attributes("-topmost", True)
    _root.wm_attributes("-alpha", 0.93)
    _root.wm_attributes("-toolwindow", True)
    _root.configure(bg="#18181b")

    _label = tk.Label(
        _root,
        text="",
        bg="#18181b",
        fg="white",
        font=("Segoe UI", 13, "bold"),
        padx=22,
        pady=10,
    )
    _label.pack()
    _root.mainloop()


def _get_overlay_pos(w: int, h: int) -> tuple[int, int]:
    """Berechnet x,y anhand der konfigurierten Position."""
    sw = _root.winfo_screenwidth()
    sh = _root.winfo_screenheight()
    margin = 24
    pos = cfg.get("overlay_position", "bottom_right")
    if pos == "bottom_left":
        return margin, sh - h - 64
    elif pos == "bottom_center":
        return (sw - w) // 2, sh - h - 64
    elif pos == "top_right":
        return sw - w - margin, margin + 40
    elif pos == "top_left":
        return margin, margin + 40
    else:  # bottom_right (default)
        return sw - w - margin, sh - h - 64


def _show(text: str, color: str = "white") -> None:
    if _root is None or _label is None:
        return

    def _update():
        global _hide_job
        if _hide_job:
            _root.after_cancel(_hide_job)
            _hide_job = None
        _label.configure(text=text, fg=color)
        _root.update_idletasks()
        w = max(_root.winfo_reqwidth(), 320)
        h = _root.winfo_reqheight()
        x, y = _get_overlay_pos(w, h)
        _root.geometry(f"{w}x{h}+{x}+{y}")
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


# ── Sound-Feedback ────────────────────────────────────────────────────────────
def _beep_start() -> None:
    if cfg.get("sound_feedback", True):
        try:
            winsound.Beep(880, 80)
        except Exception:
            pass


def _beep_done() -> None:
    if cfg.get("sound_feedback", True):
        try:
            winsound.Beep(1320, 60)
        except Exception:
            pass


# ── Audio ─────────────────────────────────────────────────────────────────────
def _audio_cb(indata, frames, time_info, status) -> None:
    global _audio_level
    if is_recording:
        audio_chunks.append(indata.copy())
        _audio_level = float(np.abs(indata).mean()) * 8.0


def start_recording() -> None:
    global is_recording, audio_chunks, _stream
    if is_recording:
        return

    # Lazy loading: Modell noch nicht geladen?
    if _model_loading:
        _show("⏳  Modell lädt noch…", "#f59e0b")
        return

    requested = cfg.get("model", "cohere")
    if requested not in models:
        if models:
            # Anderes Modell ist geladen — darauf wechseln
            fallback = list(models.keys())[0]
            cfg["model"] = fallback
            settings.save(cfg)
            log.warning("Wechsle zu verfügbarem Modell: %s", fallback)
        elif not _model_loading:
            _show("⏳  Modell lädt…", "#f59e0b")
            threading.Thread(target=_load_models_then_record, daemon=True).start()
            return
        else:
            return

    _do_start_recording()


def _do_start_recording() -> None:
    global is_recording, audio_chunks, _stream
    audio_chunks = []
    is_recording = True
    mic_idx = cfg.get("microphone", -1)
    device  = None if mic_idx == -1 else mic_idx
    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=device,
        callback=_audio_cb,
    )
    _stream.start()
    log.info("Aufnahme gestartet (Gerät: %s)", device)
    _show("● Aufnahme…", "#ef4444")
    threading.Thread(target=_beep_start, daemon=True).start()


def _load_models_then_record() -> None:
    _load_models()
    if not models:
        return
    # Falls das gewünschte Modell nicht geladen werden konnte, auf verfügbares wechseln
    if cfg.get("model") not in models:
        fallback = list(models.keys())[0]
        log.warning("Modell '%s' nicht verfügbar, wechsle zu '%s'", cfg.get("model"), fallback)
        cfg["model"] = fallback
        settings.save(cfg)
        _show(f"⚠  Cohere nicht verfügbar → {fallback}", "#f59e0b")
        time.sleep(1.5)
    _do_start_recording()


def stop_recording() -> None:
    global is_recording, _stream
    if not is_recording:
        return
    is_recording = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None
    log.info("Aufnahme gestoppt — %d Blöcke", len(audio_chunks))
    _show("⟳  Verarbeitung…", "#f59e0b")
    threading.Thread(target=_transcribe_and_paste, daemon=True).start()


# ── Satzzeichen ersetzen ──────────────────────────────────────────────────────
def _apply_punctuation(text: str) -> str:
    import re
    for spoken, symbol in sorted(PUNCT_MAP.items(), key=lambda x: -len(x[0])):
        pattern = rf"(?<![a-zA-ZäöüÄÖÜß]){re.escape(spoken)}(?![a-zA-ZäöüÄÖÜß])"
        text = re.sub(pattern, symbol, text, flags=re.IGNORECASE)
    return text.strip()


# ── Transkription ─────────────────────────────────────────────────────────────
def _transcribe_and_paste() -> None:
    if not audio_chunks:
        _show("⚠  Keine Aufnahme", "#ef4444")
        _hide_after(2000)
        return

    audio    = np.concatenate(audio_chunks, axis=0).flatten().astype(np.float32)
    dur      = len(audio) / SAMPLE_RATE
    lang_arg = None if cfg["language"] == "auto" else cfg["language"]
    model_id = cfg["model"]

    # Max-Dauer prüfen
    max_dur = cfg.get("max_duration_sec", 0)
    if max_dur > 0 and dur > max_dur:
        audio = audio[:int(max_dur * SAMPLE_RATE)]
        dur   = max_dur

    log.info("Transkribiere %.1fs | Modell=%s | Sprache=%s", dur, model_id, lang_arg or "auto")

    try:
        t0 = time.perf_counter()

        if model_id == "whisper":
            wm = models.get("whisper")
            if wm is None:
                raise RuntimeError("Whisper nicht geladen")
            segs, _ = wm.transcribe(audio, language=lang_arg, beam_size=5)
            text = " ".join(s.text.strip() for s in segs)

        else:
            cm = models.get("cohere")
            if cm is None:
                raise RuntimeError("Cohere nicht geladen")
            texts = cm["model"].transcribe(
                processor=cm["processor"],
                audio_arrays=[audio],
                sample_rates=[SAMPLE_RATE],
                language=lang_arg,
            )
            text = texts[0]

        elapsed = time.perf_counter() - t0
        text    = _apply_punctuation(text.strip())
        words   = len(text.split()) if text else 0
        rtf     = elapsed / dur if dur > 0 else 0

        log.info("Fertig %.2fs (RTF %.2f, %d Wörter, CPU %.0f%%): %s",
                 elapsed, rtf, words, _cpu_percent, text[:80])

        if text:
            _paste_text(text)
            _last_stats["rtf"] = rtf
            _last_stats["wpm"] = words
            _append_history({"text": text, "wpm": words, "rtf": rtf,
                             "model": model_id, "lang": cfg.get("language","de")})
            _show(
                f"✓  {words} Wörter  ·  {elapsed:.1f}s  ·  RTF {rtf:.2f}",
                "#22c55e",
            )
            threading.Thread(target=_beep_done, daemon=True).start()
        else:
            _show("⚠  Kein Text erkannt", "#f59e0b")

        _hide_after(2200)

    except Exception as exc:
        log.error("Fehler: %s", exc)
        _show(f"✗  {exc}", "#ef4444")
        _hide_after(3500)


def _load_history() -> list:
    hist_file = settings_mod.APP_DIR / "history.json"
    if hist_file.exists():
        try:
            return json.load(open(hist_file, encoding="utf-8"))
        except Exception:
            pass
    return []


def _append_history(entry: dict) -> None:
    history = _load_history()
    history.insert(0, entry)
    history = history[:50]
    hist_file = settings_mod.APP_DIR / "history.json"
    import json as _json
    _json.dump(history, open(hist_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _paste_text(text: str) -> None:
    pyperclip.copy(text)
    time.sleep(0.18)
    _kb.press(Key.ctrl)
    _kb.press("v")
    _kb.release("v")
    _kb.release(Key.ctrl)


# ── Hotkey ────────────────────────────────────────────────────────────────────
def _ctrl_down()  -> bool: return Key.ctrl_l  in _pressed_keys or Key.ctrl_r  in _pressed_keys
def _shift_down() -> bool: return Key.shift   in _pressed_keys or Key.shift_r in _pressed_keys


def _on_press(key) -> None:
    _pressed_keys.add(key)
    if _ctrl_down() and _shift_down() and key == Key.space and not is_recording:
        start_recording()


def _on_release(key) -> None:
    if key == Key.space and is_recording:
        stop_recording()
    _pressed_keys.discard(key)


# ── Autostart ─────────────────────────────────────────────────────────────────
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


# ── Tray-Icon ─────────────────────────────────────────────────────────────────
_ICON_BASE: Image.Image | None = None
_ICON_PATH = Path(__file__).parent / "assets" / "whisp.ico"


def _load_base_icon() -> None:
    global _ICON_BASE
    if _ICON_PATH.exists():
        try:
            _ICON_BASE = Image.open(_ICON_PATH).convert("RGBA").resize((64, 64))
        except Exception:
            pass


def _icon_image(state: str = "idle") -> Image.Image:
    """Generiert das Tray-Icon. state: idle/recording/processing/done/error"""
    size = 64

    # Basis-Icon laden falls vorhanden
    if _ICON_BASE:
        img = _ICON_BASE.copy()
    else:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)
        colors = {
            "idle":       (99, 102, 241),
            "recording":  (220, 38,  38),
            "processing": (217, 119, 6),
            "done":       (22,  163, 74),
            "error":      (127, 29,  29),
        }
        bg = colors.get(state, colors["idle"])
        d.ellipse([2, 2, 62, 62], fill=bg)
        d.rectangle([27, 12, 37, 34], fill="white", outline="white")
        d.arc([22, 26, 42, 42], 0, 180, fill="white", width=3)
        d.line([32, 42, 32, 52], fill="white", width=3)
        d.line([24, 52, 40, 52], fill="white", width=3)

    # Status-Indikator als farbiger Punkt oben rechts
    indicator_colors = {
        "idle":       None,
        "recording":  (239, 68,  68),    # rot
        "processing": (245, 158, 11),    # amber
        "done":       (34,  197, 94),    # grün
        "error":      (127, 29,  29),    # dunkelrot
    }
    color = indicator_colors.get(state)
    if color:
        overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(overlay)
        d2.ellipse([44, 4, 60, 20], fill=(*color, 255), outline="white", width=1)
        img = Image.alpha_composite(img, overlay)

    return img


def _set_icon_state(state: str) -> None:
    if _tray_icon:
        try:
            _tray_icon.icon = _icon_image(state)
        except Exception:
            pass


_dashboard = None


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
    proc    = psutil.Process()
    ram_mb  = proc.memory_info().rss / 1024 / 1024
    history = _load_history()
    return {
        "last_rtf":    _last_stats.get("rtf", 0),
        "last_wpm":    _last_stats.get("wpm", 0),
        "cpu":         _cpu_percent,
        "ram_mb":      ram_mb,
        "history":     history,
        "is_recording": is_recording,
        "audio_level": _audio_level,
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


def _set_model(m: str):
    def _handler(icon, item):
        cfg["model"] = m
        settings.save(cfg)
        _update_tray_title()
        log.info("Modell → %s", m)
    return _handler


def _set_lang(lang: str):
    def _handler(icon, item):
        cfg["language"] = lang
        settings.save(cfg)
        _update_tray_title()
        log.info("Sprache → %s", lang)
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
            # ── Modell ──
            MenuItem("Modell", Menu(
                MenuItem("Cohere Transcribe (Primär)", _set_model("cohere"),
                         checked=lambda item: cfg["model"] == "cohere", radio=True),
                MenuItem("faster-whisper (Backup)",   _set_model("whisper"),
                         checked=lambda item: cfg["model"] == "whisper", radio=True),
            )),
            # ── Sprache ──
            MenuItem("Sprache", Menu(
                MenuItem("Auto-Erkennung", _set_lang("auto"),
                         checked=lambda item: cfg["language"] == "auto", radio=True),
                MenuItem("Deutsch",        _set_lang("de"),
                         checked=lambda item: cfg["language"] == "de",   radio=True),
                MenuItem("Englisch",       _set_lang("en"),
                         checked=lambda item: cfg["language"] == "en",   radio=True),
                MenuItem("Spanisch",       _set_lang("es"),
                         checked=lambda item: cfg["language"] == "es",   radio=True),
                MenuItem("Französisch",    _set_lang("fr"),
                         checked=lambda item: cfg["language"] == "fr",   radio=True),
                MenuItem("Italienisch",    _set_lang("it"),
                         checked=lambda item: cfg["language"] == "it",   radio=True),
            )),
            Menu.SEPARATOR,
            MenuItem("Autostart", _toggle_autostart, checked=lambda item: _autostart_enabled()),
            MenuItem("Dashboard öffnen", _open_dashboard),
            MenuItem("Einstellungen ⚙",  _open_settings),
            Menu.SEPARATOR,
            MenuItem("Beenden", _quit),
        ),
    )
    _tray_icon.run()


# ── Modelle laden (Lazy) ──────────────────────────────────────────────────────
def _load_models() -> None:
    global _model_loading
    _model_loading = True
    _set_icon_state("processing")

    whisper_size = cfg.get("whisper_size", "small")

    # Cohere zuerst (Primärmodell)
    try:
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        log.info("Lade Cohere-Modell auf %s …", DEVICE)
        processor = AutoProcessor.from_pretrained(COHERE_MODEL_ID, trust_remote_code=True)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            COHERE_MODEL_ID, trust_remote_code=True
        ).to(DEVICE)
        model.eval()
        models["cohere"] = {"processor": processor, "model": model}
        log.info("Cohere geladen.")
    except Exception as exc:
        log.error("Cohere nicht geladen: %s", exc)

    # Whisper als Backup
    try:
        from faster_whisper import WhisperModel
        compute_type = "float16" if DEVICE == "cuda" else "int8"
        models["whisper"] = WhisperModel(whisper_size, device=DEVICE, compute_type=compute_type)
        log.info("faster-whisper (%s) geladen.", whisper_size)
    except Exception as exc:
        log.warning("faster-whisper nicht verfügbar: %s", exc)

    _model_loading = False
    loaded = list(models.keys())

    if loaded:
        _set_icon_state("done")
        _show(f"✓  Whisp bereit  ({', '.join(loaded)})", "#22c55e")
        _hide_after(2500)
        threading.Thread(target=lambda: (time.sleep(2.5), _set_icon_state("idle")), daemon=True).start()
    else:
        _set_icon_state("error")
        _show("✗  Kein Modell geladen!", "#ef4444")


# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Whisp Overlay startet — Hotkey: Ctrl+Shift+Space")
    _load_base_icon()
    log.info("Settings: %s", settings.SETTINGS_FILE)
    log.info("Konfiguration: %s", cfg)

    threading.Thread(target=_run_tray, daemon=True).start()

    # Lazy loading: Modell wird beim ersten Hotkey-Druck geladen
    # Kein automatisches Laden beim Start → schneller Start
    log.info("Bereit. Modell wird beim ersten Hotkey-Druck geladen.")

    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.start()

    _build_overlay()
