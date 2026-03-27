"""
Whisp - Einstellungen (customtkinter)
Standalone-Fenster oder eingebettet im Dashboard.
"""

import os
import sys
import winreg

import customtkinter as ctk
import sounddevice as sd

ctk.set_appearance_mode("dark")

BG = "#09090b"
BG2 = "#18181b"
BG3 = "#27272a"
ACCENT = "#6366f1"
FG = "#f4f4f5"
FG_DIM = "#a1a1aa"

LANGUAGES = [
    ("Auto-Erkennung", "auto"),
    ("Deutsch", "de"),
    ("Englisch", "en"),
    ("Spanisch", "es"),
    ("Franzoesisch", "fr"),
    ("Italienisch", "it"),
    ("Portugiesisch", "pt"),
    ("Polnisch", "pl"),
    ("Niederlaendisch", "nl"),
    ("Japanisch", "ja"),
    ("Chinesisch", "zh"),
    ("Koreanisch", "ko"),
]

POSITIONS = [
    ("Unten rechts", "bottom_right"),
    ("Unten links", "bottom_left"),
    ("Unten Mitte", "bottom_center"),
    ("Oben rechts", "top_right"),
    ("Oben links", "top_left"),
]

WHISPER_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
SOUND_PROFILES = [("Warm", "warm"), ("Classic", "classic"), ("Soft", "soft")]


def _play_preview(profile: str) -> None:
    try:
        import winsound

        patterns = {
            "warm": [(660, 50), (880, 70), (1040, 90)],
            "classic": [(880, 70), (1320, 60)],
            "soft": [(740, 40), (880, 55), (988, 70)],
        }
        for freq, ms in patterns.get(profile, patterns["warm"]):
            winsound.Beep(freq, ms)
    except Exception:
        pass


def _get_mics():
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        result = [("System-Standard", -1, "Windows Default")]
        seen = set()

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) <= 0:
                continue
            hostapi_index = dev.get("hostapi", 0)
            hostapi_name = hostapis[hostapi_index]["name"] if hostapi_index < len(hostapis) else "Unknown"
            label = f"{dev['name']}  [{hostapi_name}]"
            if label in seen:
                continue
            seen.add(label)
            result.append((label[:72], idx, hostapi_name))

        return result
    except Exception:
        return [("System-Standard", -1, "Windows Default")]


def _section_label(parent, text: str):
    ctk.CTkLabel(parent, text=text, font=ctk.CTkFont("Segoe UI", 9, "bold"), text_color=ACCENT).pack(
        anchor="w", padx=4, pady=(14, 4)
    )


def _setting_row(parent, label: str, widget_fn):
    row = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=10)
    row.pack(fill="x", pady=4)
    ctk.CTkLabel(
        row,
        text=label,
        width=170,
        anchor="w",
        font=ctk.CTkFont("Segoe UI", 11),
        text_color=FG_DIM,
    ).pack(side="left", padx=14, pady=12)
    widget_fn(row)
    return row


def _combo(parent, value: str, options: list, on_change, width=220):
    labels = [o[0] for o in options]
    keys = [o[1] for o in options]
    current = next((label for label, key in options if key == value), labels[0])
    var = ctk.StringVar(value=current)
    combo = ctk.CTkComboBox(
        parent,
        values=labels,
        variable=var,
        state="readonly",
        width=width,
        fg_color=BG3,
        border_color=BG3,
        button_color=ACCENT,
        button_hover_color="#4f46e5",
        dropdown_fg_color=BG3,
        text_color=FG,
        font=ctk.CTkFont("Segoe UI", 11),
    )
    combo.pack(side="right", padx=14, pady=8)

    def _on(choice):
        idx = labels.index(choice)
        on_change(keys[idx])

    combo.configure(command=_on)
    return combo, var


def build_embedded(parent, cfg: dict, on_save):
    container = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
    container.pack(fill="both", expand=True, padx=0, pady=0)
    _build_form(container, cfg, on_save, show_header=False, show_buttons=True)


def open(cfg: dict, on_save, parent=None, embedded=False):
    win = ctk.CTkToplevel()
    win.title("Whisp - Einstellungen")
    win.configure(fg_color=BG)
    win.resizable(False, False)
    win.wm_attributes("-topmost", True)

    w, h = 620, 700
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    container = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    container.pack(fill="both", expand=True, padx=20, pady=0)
    _build_form(container, cfg, lambda c: (on_save(c), win.destroy()), show_header=True, show_buttons=True)


def _build_form(parent, cfg: dict, on_save, show_header=True, show_buttons=True):
    local = dict(cfg)

    def update(key, value):
        local[key] = value

    if show_header:
        ctk.CTkLabel(parent, text="Einstellungen", font=ctk.CTkFont("Segoe UI", 16, "bold"), text_color=FG).pack(
            anchor="w", pady=(16, 0)
        )

    _section_label(parent, "MODELL")
    _setting_row(
        parent,
        "Primaermodell",
        lambda p: _combo(
            p,
            local.get("model", "cohere"),
            [("Cohere Transcribe", "cohere"), ("faster-whisper", "whisper")],
            lambda v: update("model", v),
        ),
    )
    _setting_row(
        parent,
        "Whisper-Groesse",
        lambda p: _combo(
            p,
            local.get("whisper_size", "small"),
            [(size, size) for size in WHISPER_SIZES],
            lambda v: update("whisper_size", v),
        ),
    )

    _section_label(parent, "SPRACHE")
    _setting_row(
        parent,
        "Erkennungssprache",
        lambda p: _combo(p, local.get("language", "de"), LANGUAGES, lambda v: update("language", v)),
    )

    _section_label(parent, "MIKROFON")
    mic_state = {"devices": _get_mics()}
    current_label = local.get("microphone_name", "System-Standard")
    if current_label not in [item[0] for item in mic_state["devices"]]:
        current_label = mic_state["devices"][0][0]
    mic_var = ctk.StringVar(value=current_label)
    mic_detail_var = ctk.StringVar(value="")
    combo_holder = {}

    def _choose_mic(selected_label: str):
        selected = next((item for item in mic_state["devices"] if item[0] == selected_label), mic_state["devices"][0])
        update("microphone", selected[1])
        update("microphone_name", selected[0])
        mic_detail_var.set(f"Quelle: {selected[2]}")

    def _refresh_mics():
        mic_state["devices"] = _get_mics()
        labels = [item[0] for item in mic_state["devices"]]
        current = local.get("microphone_name", "System-Standard")
        if current not in labels:
            current = labels[0]
        mic_var.set(current)
        combo_holder["combo"].configure(values=labels)
        _choose_mic(current)

    _choose_mic(current_label)

    def _mic_row(p):
        wrap = ctk.CTkFrame(p, fg_color="transparent")
        wrap.pack(side="right", padx=14, pady=8)
        combo = ctk.CTkComboBox(
            wrap,
            values=[item[0] for item in mic_state["devices"]],
            variable=mic_var,
            state="readonly",
            width=280,
            fg_color=BG3,
            border_color=BG3,
            button_color=ACCENT,
            button_hover_color="#4f46e5",
            dropdown_fg_color=BG3,
            text_color=FG,
            font=ctk.CTkFont("Segoe UI", 11),
            command=_choose_mic,
        )
        combo.pack(side="left")
        combo_holder["combo"] = combo
        ctk.CTkButton(
            wrap,
            text="Neu laden",
            width=92,
            fg_color=BG3,
            hover_color="#3f3f46",
            text_color=FG,
            command=_refresh_mics,
        ).pack(side="left", padx=(8, 0))

    _setting_row(parent, "Mikrofon", _mic_row)
    ctk.CTkLabel(parent, textvariable=mic_detail_var, text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10)).pack(
        anchor="e", padx=12, pady=(0, 6)
    )

    _section_label(parent, "OVERLAY")
    _setting_row(
        parent,
        "Position",
        lambda p: _combo(
            p,
            local.get("overlay_position", "bottom_right"),
            POSITIONS,
            lambda v: update("overlay_position", v),
        ),
    )

    def _sound_toggle_row(p):
        var = ctk.BooleanVar(value=local.get("sound_feedback", True))
        ctk.CTkSwitch(
            p,
            text="",
            variable=var,
            progress_color=ACCENT,
            button_color=FG,
            button_hover_color=FG_DIM,
            onvalue=True,
            offvalue=False,
            command=lambda: update("sound_feedback", var.get()),
        ).pack(side="right", padx=18, pady=8)

    _setting_row(parent, "Sound-Feedback", _sound_toggle_row)

    _setting_row(
        parent,
        "Sound-Profil",
        lambda p: _combo(
            p,
            local.get("sound_profile", "warm"),
            SOUND_PROFILES,
            lambda v: update("sound_profile", v),
        ),
    )

    _setting_row(
        parent,
        "Sound-Test",
        lambda p: ctk.CTkButton(
            p,
            text="Sound testen",
            fg_color=BG3,
            hover_color="#3f3f46",
            text_color=FG,
            command=lambda: _play_preview(local.get("sound_profile", "warm")),
        ).pack(side="right", padx=14, pady=8),
    )

    def _maxdur_row(p):
        value_label = ctk.CTkLabel(
            p,
            text="Unbegrenzt" if not local.get("max_duration_sec", 0) else f"{local['max_duration_sec']}s",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=FG_DIM,
        )
        value_label.pack(side="right", padx=(0, 14), pady=8)

        def _update_slider(v):
            iv = int(float(v))
            update("max_duration_sec", iv)
            value_label.configure(text="Unbegrenzt" if iv == 0 else f"{iv}s")

        slider = ctk.CTkSlider(
            p,
            from_=0,
            to=300,
            number_of_steps=30,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color="#4f46e5",
            command=_update_slider,
            width=180,
        )
        slider.set(local.get("max_duration_sec", 0))
        slider.pack(side="right", padx=8, pady=8)

    _setting_row(parent, "Max. Aufnahmedauer", _maxdur_row)

    _section_label(parent, "SYSTEM")

    def _autostart_row(p):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "WhispOverlay")
            current = True
        except Exception:
            current = False

        var = ctk.BooleanVar(value=current)

        def _toggle():
            if var.get():
                cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "WhispOverlay", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
            else:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "WhispOverlay")
                    winreg.CloseKey(key)
                except Exception:
                    pass

        ctk.CTkSwitch(
            p,
            text="",
            variable=var,
            progress_color=ACCENT,
            button_color=FG,
            button_hover_color=FG_DIM,
            onvalue=True,
            offvalue=False,
            command=_toggle,
        ).pack(side="right", padx=18, pady=8)

    _setting_row(parent, "Mit Windows starten", _autostart_row)

    def _hf_row(p):
        def _open_hf():
            try:
                import hf_login

                hf_login.open_token_window()
            except Exception:
                pass

        ctk.CTkButton(
            p,
            text="Token einrichten ->",
            fg_color=BG3,
            hover_color="#3f3f46",
            text_color=FG,
            command=_open_hf,
        ).pack(side="right", padx=14, pady=8)

    _setting_row(parent, "HuggingFace Token", _hf_row)

    if show_buttons:
        ctk.CTkFrame(parent, fg_color=BG3, height=1, corner_radius=0).pack(fill="x", pady=(16, 8))
        ctk.CTkButton(
            parent,
            text="Speichern",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=ACCENT,
            hover_color="#4f46e5",
            text_color="white",
            corner_radius=10,
            height=42,
            command=lambda: on_save(local),
        ).pack(fill="x", pady=(0, 16))
