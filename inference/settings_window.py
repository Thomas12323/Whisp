"""
Whisp — Einstellungen (customtkinter)
Standalone-Fenster ODER eingebettet in Dashboard-Tab.
"""
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import sounddevice as sd
import settings as settings_mod

ctk.set_appearance_mode("dark")

BG      = "#09090b"
BG2     = "#18181b"
BG3     = "#27272a"
ACCENT  = "#6366f1"
FG      = "#f4f4f5"
FG_DIM  = "#a1a1aa"
RED     = "#ef4444"

LANGUAGES = [
    ("Auto-Erkennung", "auto"), ("Deutsch", "de"), ("Englisch", "en"),
    ("Spanisch", "es"), ("Französisch", "fr"), ("Italienisch", "it"),
    ("Portugiesisch", "pt"), ("Polnisch", "pl"), ("Niederländisch", "nl"),
    ("Japanisch", "ja"), ("Chinesisch", "zh"), ("Koreanisch", "ko"),
]
POSITIONS = [
    ("Unten rechts", "bottom_right"), ("Unten links", "bottom_left"),
    ("Unten Mitte",  "bottom_center"), ("Oben rechts", "top_right"),
    ("Oben links",   "top_left"),
]
WHISPER_SIZES = ["tiny", "base", "small", "medium", "large-v3"]


def _get_mics():
    try:
        devs = sd.query_devices()
        result = [("System-Standard", -1)]
        seen = set()
        for i, d in enumerate(devs):
            if d["max_input_channels"] > 0 and "MME" in d["name"]:
                name = d["name"][:48]
                if name not in seen:
                    seen.add(name)
                    result.append((name, i))
        return result
    except Exception:
        return [("System-Standard", -1)]


def _section_label(parent, text: str):
    ctk.CTkLabel(parent, text=text,
                  font=ctk.CTkFont("Segoe UI", 9, "bold"),
                  text_color=ACCENT).pack(anchor="w", padx=4, pady=(14, 4))


def _setting_row(parent, label: str, widget_fn):
    row = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=8)
    row.pack(fill="x", pady=3)
    ctk.CTkLabel(row, text=label, width=160, anchor="w",
                  font=ctk.CTkFont("Segoe UI", 11),
                  text_color=FG_DIM).pack(side="left", padx=14, pady=10)
    widget_fn(row)
    return row


def _combo(parent, value: str, options: list, on_change, width=200):
    labels = [o[0] for o in options]
    keys   = [o[1] for o in options]
    current = next((l for l, k in options if k == value), labels[0])
    var = ctk.StringVar(value=current)
    cb  = ctk.CTkComboBox(parent, values=labels, variable=var,
                           state="readonly", width=width,
                           fg_color=BG3, border_color=BG3,
                           button_color=ACCENT, button_hover_color="#4f46e5",
                           dropdown_fg_color=BG3, text_color=FG,
                           font=ctk.CTkFont("Segoe UI", 11))
    cb.pack(side="right", padx=14, pady=8)
    def _on(choice):
        idx = labels.index(choice)
        on_change(keys[idx])
    cb.configure(command=_on)
    return cb, var


def build_embedded(parent, cfg: dict, on_save):
    """Rendert Settings direkt in einen Frame (für Dashboard-Tab)."""
    container = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
    container.pack(fill="both", expand=True, padx=0, pady=0)
    _build_form(container, cfg, on_save, show_header=False, show_buttons=True)


def open(cfg: dict, on_save, parent=None, embedded=False):
    """Öffnet eigenes Fenster."""
    win = ctk.CTkToplevel()
    win.title("Whisp — Einstellungen")
    win.configure(fg_color=BG)
    win.resizable(False, False)
    win.wm_attributes("-topmost", True)

    w, h = 560, 580
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    container = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    container.pack(fill="both", expand=True, padx=20, pady=0)

    _build_form(container, cfg, lambda c: (on_save(c), win.destroy()),
                show_header=True, show_buttons=True)


def _build_form(parent, cfg: dict, on_save, show_header=True, show_buttons=True):
    local = dict(cfg)

    def update(key, val):
        local[key] = val

    if show_header:
        ctk.CTkLabel(parent, text="Einstellungen",
                      font=ctk.CTkFont("Segoe UI", 16, "bold"),
                      text_color=FG).pack(anchor="w", pady=(16, 0))

    # ── Modell ────────────────────────────────────────────────────────────────
    _section_label(parent, "MODELL")

    _setting_row(parent, "Primärmodell", lambda p: _combo(
        p, local.get("model", "cohere"),
        [("Cohere Transcribe", "cohere"), ("faster-whisper", "whisper")],
        lambda v: update("model", v)
    ))
    _setting_row(parent, "Whisper-Größe", lambda p: _combo(
        p, local.get("whisper_size", "small"),
        [(s, s) for s in WHISPER_SIZES],
        lambda v: update("whisper_size", v)
    ))

    # ── Sprache ───────────────────────────────────────────────────────────────
    _section_label(parent, "SPRACHE")
    _setting_row(parent, "Erkennungssprache", lambda p: _combo(
        p, local.get("language", "de"), LANGUAGES,
        lambda v: update("language", v), width=220
    ))

    # ── Mikrofon ──────────────────────────────────────────────────────────────
    _section_label(parent, "MIKROFON")
    mics = _get_mics()
    mic_val = local.get("microphone", -1)
    current_mic = next((l for l, k in mics if k == mic_val), mics[0][0])
    mic_var = ctk.StringVar(value=current_mic)
    mic_keys = {l: k for l, k in mics}

    def _mic_row(p):
        cb = ctk.CTkComboBox(p, values=[m[0] for m in mics], variable=mic_var,
                              state="readonly", width=280,
                              fg_color=BG3, border_color=BG3,
                              button_color=ACCENT, button_hover_color="#4f46e5",
                              dropdown_fg_color=BG3, text_color=FG,
                              font=ctk.CTkFont("Segoe UI", 11))
        cb.pack(side="right", padx=14, pady=8)
        cb.configure(command=lambda v: update("microphone", mic_keys.get(v, -1)))

    _setting_row(parent, "Mikrofon", _mic_row)

    # ── Overlay ───────────────────────────────────────────────────────────────
    _section_label(parent, "OVERLAY")
    _setting_row(parent, "Position", lambda p: _combo(
        p, local.get("overlay_position", "bottom_right"), POSITIONS,
        lambda v: update("overlay_position", v), width=200
    ))

    def _sound_row(p):
        var = ctk.BooleanVar(value=local.get("sound_feedback", True))
        sw  = ctk.CTkSwitch(p, text="", variable=var,
                              progress_color=ACCENT,
                              button_color=FG, button_hover_color=FG_DIM,
                              onvalue=True, offvalue=False,
                              command=lambda: update("sound_feedback", var.get()))
        sw.pack(side="right", padx=18, pady=8)

    _setting_row(parent, "Sound-Feedback", _sound_row)

    def _maxdur_row(p):
        val  = local.get("max_duration_sec", 0)
        lbl  = ctk.CTkLabel(p, text="Unbegrenzt" if not val else f"{val}s",
                              font=ctk.CTkFont("Segoe UI", 11), text_color=FG_DIM)
        lbl.pack(side="right", padx=(0, 14), pady=8)

        def _upd(v):
            iv = int(float(v))
            update("max_duration_sec", iv)
            lbl.configure(text="Unbegrenzt" if iv == 0 else f"{iv}s")

        sl = ctk.CTkSlider(p, from_=0, to=300, number_of_steps=30,
                            progress_color=ACCENT, button_color=ACCENT,
                            button_hover_color="#4f46e5",
                            command=_upd, width=160)
        sl.set(val)
        sl.pack(side="right", padx=8, pady=8)

    _setting_row(parent, "Max. Aufnahmedauer", _maxdur_row)

    # ── System ────────────────────────────────────────────────────────────────
    _section_label(parent, "SYSTEM")

    def _autostart_row(p):
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(k, "WhispOverlay")
            current = True
        except Exception:
            current = False

        var = ctk.BooleanVar(value=current)

        def _toggle():
            import sys, os
            if var.get():
                cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                k   = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(k, "WhispOverlay", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(k)
            else:
                try:
                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(k, "WhispOverlay")
                    winreg.CloseKey(k)
                except Exception:
                    pass

        ctk.CTkSwitch(p, text="", variable=var,
                       progress_color=ACCENT, button_color=FG,
                       button_hover_color=FG_DIM,
                       onvalue=True, offvalue=False,
                       command=_toggle).pack(side="right", padx=18, pady=8)

    _setting_row(parent, "Mit Windows starten", _autostart_row)

    # HuggingFace Token
    def _hf_row(p):
        def _open_hf():
            try:
                import hf_login
                hf_login.open_token_window()
            except Exception:
                pass
        ctk.CTkButton(p, text="Token einrichten →",
                       font=ctk.CTkFont("Segoe UI", 11),
                       fg_color=BG3, hover_color="#3f3f46",
                       text_color=FG, corner_radius=8,
                       command=_open_hf).pack(side="right", padx=14, pady=8)

    _setting_row(parent, "HuggingFace Token", _hf_row)

    # ── Speichern ─────────────────────────────────────────────────────────────
    if show_buttons:
        ctk.CTkFrame(parent, fg_color=BG3, height=1, corner_radius=0).pack(
            fill="x", pady=(16, 8))
        ctk.CTkButton(parent, text="Speichern",
                       font=ctk.CTkFont("Segoe UI", 12, "bold"),
                       fg_color=ACCENT, hover_color="#4f46e5",
                       text_color="white", corner_radius=10, height=40,
                       command=lambda: on_save(local)).pack(
            fill="x", pady=(0, 16))
