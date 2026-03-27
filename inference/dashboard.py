"""
Whisp - Dashboard (customtkinter)
Verbessertes Dashboard mit Live-Mic-Status, Modellstatus und Verlauf.
"""

import math
import time
from pathlib import Path

import customtkinter as ctk
import psutil

import settings as settings_mod

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#09090b"
BG2 = "#18181b"
BG3 = "#27272a"
ACCENT = "#6366f1"
ACCENT_H = "#4f46e5"
GREEN = "#22c55e"
AMBER = "#f59e0b"
RED = "#ef4444"
FG = "#f4f4f5"
FG_DIM = "#a1a1aa"

LOGO_PATH = Path(__file__).parent / "assets" / "whisp_logo.png"
ICON_PATH = Path(__file__).parent / "assets" / "whisp.ico"


class Dashboard(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, models: dict, get_stats_fn):
        super().__init__(master)
        self.cfg = cfg
        self.models = models
        self.get_stats_fn = get_stats_fn
        self._running = True
        self._wave_phase = 0.0

        self.title("Whisp")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        width, height = 720, 760
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{width}x{height}+{(sw-width)//2}+{(sh-height)//2}")

        self._build_ui()
        self._animate()
        self._refresh()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=16)

        logo_holder = ctk.CTkFrame(inner, fg_color=BG3, corner_radius=14, width=52, height=52)
        logo_holder.pack(side="left")
        logo_holder.pack_propagate(False)
        if LOGO_PATH.exists():
            try:
                from PIL import Image

                image = Image.open(LOGO_PATH)
                self._logo_img = ctk.CTkImage(light_image=image, dark_image=image, size=(36, 36))
                ctk.CTkLabel(logo_holder, image=self._logo_img, text="").place(relx=0.5, rely=0.5, anchor="center")
            except Exception:
                ctk.CTkLabel(logo_holder, text="W", font=ctk.CTkFont("Segoe UI", 18, "bold")).place(
                    relx=0.5, rely=0.5, anchor="center"
                )

        title_wrap = ctk.CTkFrame(inner, fg_color="transparent")
        title_wrap.pack(side="left", padx=(14, 0))
        ctk.CTkLabel(title_wrap, text="Whisp", font=ctk.CTkFont("Segoe UI", 22, "bold"), text_color=FG).pack(anchor="w")
        ctk.CTkLabel(
            title_wrap,
            text="Lokale Diktier-App mit Live-Mic-Monitoring",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=FG_DIM,
        ).pack(anchor="w")

        self._status_badge = ctk.CTkLabel(
            inner,
            text="Bereit",
            fg_color="#113122",
            text_color="#b7f7cb",
            corner_radius=999,
            padx=14,
            pady=6,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
        )
        self._status_badge.pack(side="right", pady=6)

        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

        hero = ctk.CTkFrame(self, fg_color=BG2, corner_radius=18)
        hero.pack(fill="x", padx=18, pady=(16, 12))

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(left, text="Live Status", font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color=FG).pack(anchor="w")
        self._summary_line = ctk.CTkLabel(left, text="Warte auf Aufnahme", font=ctk.CTkFont("Segoe UI", 18, "bold"), text_color=FG)
        self._summary_line.pack(anchor="w", pady=(8, 4))
        self._sub_line = ctk.CTkLabel(left, text="Hotkey: Ctrl + Shift + Space", font=ctk.CTkFont("Segoe UI", 11), text_color=FG_DIM)
        self._sub_line.pack(anchor="w")

        right = ctk.CTkFrame(hero, fg_color=BG3, corner_radius=16, width=220)
        right.pack(side="right", padx=18, pady=18, fill="y")
        self._mic_name = ctk.CTkLabel(right, text="Mikrofon: -", text_color=FG, font=ctk.CTkFont("Segoe UI", 12, "bold"))
        self._mic_name.pack(anchor="w", padx=16, pady=(14, 6))
        self._mic_host = ctk.CTkLabel(right, text="Quelle: -", text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10))
        self._mic_host.pack(anchor="w", padx=16)
        self._mic_level_text = ctk.CTkLabel(right, text="Level 0%", text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10))
        self._mic_level_text.pack(anchor="w", padx=16, pady=(12, 4))
        self._mic_level_bar = ctk.CTkProgressBar(right, progress_color=ACCENT, fg_color="#111827")
        self._mic_level_bar.pack(fill="x", padx=16, pady=(0, 14))
        self._mic_level_bar.set(0)

        metrics = ctk.CTkFrame(self, fg_color="transparent")
        metrics.pack(fill="x", padx=18)
        self._metric_labels = {}
        for key, label in [("rtf", "RTF"), ("wpm", "WPM"), ("cpu", "CPU"), ("ram", "RAM")]:
            card = ctk.CTkFrame(metrics, fg_color=BG2, corner_radius=16)
            card.pack(side="left", expand=True, fill="both", padx=4)
            ctk.CTkLabel(card, text=label, text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(12, 0))
            value = ctk.CTkLabel(card, text="-", text_color=FG, font=ctk.CTkFont("Segoe UI", 24, "bold"))
            value.pack(anchor="w", padx=14, pady=(6, 14))
            self._metric_labels[key] = value

        wave_holder = ctk.CTkFrame(self, fg_color=BG2, corner_radius=16)
        wave_holder.pack(fill="x", padx=18, pady=(12, 12))
        ctk.CTkLabel(wave_holder, text="Input Wave", text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(12, 0))
        self._wave_canvas = ctk.CTkCanvas(wave_holder, bg=BG2, height=72, highlightthickness=0, bd=0)
        self._wave_canvas.pack(fill="x", padx=12, pady=(6, 12))

        self._tabs = ctk.CTkTabview(
            self,
            fg_color=BG,
            segmented_button_fg_color=BG3,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_H,
            segmented_button_unselected_color=BG3,
            segmented_button_unselected_hover_color="#3f3f46",
            text_color=FG,
            corner_radius=0,
        )
        self._tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._tabs.add("  Transkriptionen  ")
        self._tabs.add("  Setup  ")
        self._tabs.add("  Einstellungen  ")

        self._build_transcriptions_tab(self._tabs.tab("  Transkriptionen  "))
        self._build_setup_tab(self._tabs.tab("  Setup  "))
        self._build_settings_tab(self._tabs.tab("  Einstellungen  "))

    def _build_transcriptions_tab(self, parent):
        parent.configure(fg_color=BG)
        recent = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=16)
        recent.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(recent, text="Letzte Transkription", text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10)).pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        self._last_text = ctk.CTkTextbox(recent, fg_color=BG3, text_color=FG, height=92, corner_radius=10)
        self._last_text.pack(fill="x", padx=14, pady=(8, 14))
        self._last_text.configure(state="disabled")
        self._hist_scroll = ctk.CTkScrollableFrame(parent, fg_color=BG, corner_radius=0)
        self._hist_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def _build_setup_tab(self, parent):
        parent.configure(fg_color=BG)
        self._setup_cards = ctk.CTkFrame(parent, fg_color="transparent")
        self._setup_cards.pack(fill="both", expand=True, padx=12, pady=12)

    def _build_settings_tab(self, parent):
        parent.configure(fg_color=BG)
        try:
            import settings_window

            settings_window.build_embedded(parent, self.cfg, self._on_settings_saved)
        except Exception as exc:
            ctk.CTkLabel(parent, text=f"Einstellungen konnten nicht geladen werden:\n{exc}", text_color=RED).pack(pady=40)

    def _on_settings_saved(self, new_cfg: dict):
        self.cfg.update(new_cfg)
        settings_mod.save(self.cfg)

    def _draw_waveform(self, audio_level: float = 0.0, is_recording: bool = False):
        canvas = self._wave_canvas
        canvas.delete("all")
        width = canvas.winfo_width() or 680
        height = 72
        bars = 56
        bar_w = max(3, width // bars - 3)
        spacing = width / bars
        self._wave_phase += 0.1

        for i in range(bars):
            x = int(i * spacing + spacing / 2)
            base = 4 + 4 * abs(math.sin(self._wave_phase * 0.4 + i * 0.2))
            dynamic = audio_level * 42 * (0.35 + 0.65 * abs(math.sin(self._wave_phase + i * 0.33)))
            amp = max(4, base + dynamic) if is_recording else base
            cy = height // 2
            color = ACCENT if is_recording else "#3f3f46"
            canvas.create_rectangle(x - bar_w // 2, cy - amp, x + bar_w // 2, cy + amp, fill=color, outline="")

    def _update_history(self, history: list):
        self._last_text.configure(state="normal")
        self._last_text.delete("0.0", "end")
        self._last_text.insert("0.0", history[0].get("text", "Noch keine Transkriptionen vorhanden.") if history else "Noch keine Transkriptionen vorhanden.")
        self._last_text.configure(state="disabled")

        for child in self._hist_scroll.winfo_children():
            child.destroy()

        if not history:
            ctk.CTkLabel(
                self._hist_scroll,
                text="Druecke Ctrl + Shift + Space, um die erste Aufnahme zu machen.",
                text_color=FG_DIM,
                font=ctk.CTkFont("Segoe UI", 11),
            ).pack(pady=40)
            return

        for entry in history[:20]:
            card = ctk.CTkFrame(self._hist_scroll, fg_color=BG2, corner_radius=12)
            card.pack(fill="x", pady=4)
            preview = entry.get("text", "")[:140]
            if len(entry.get("text", "")) > 140:
                preview += "..."
            ctk.CTkLabel(card, text=preview, text_color=FG, justify="left", wraplength=620, font=ctk.CTkFont("Segoe UI", 11)).pack(
                anchor="w", padx=14, pady=(12, 6)
            )
            parts = []
            if entry.get("wpm"):
                parts.append(f"{entry['wpm']} WPM")
            if entry.get("rtf"):
                parts.append(f"RTF {entry['rtf']:.2f}")
            if entry.get("model"):
                parts.append(entry["model"])
            if entry.get("lang"):
                parts.append(entry["lang"].upper())
            ctk.CTkLabel(
                card,
                text="  ·  ".join(parts) if parts else "Ohne Metadaten",
                text_color=FG_DIM,
                font=ctk.CTkFont("Segoe UI", 10),
            ).pack(anchor="w", padx=14, pady=(0, 12))

    def _update_setup_tab(self, stats: dict):
        for child in self._setup_cards.winfo_children():
            child.destroy()

        cards = [
            ("Modell", "Geladen" if self.models else "Wird beim ersten Hotkey geladen", GREEN if self.models else AMBER),
            ("Mikrofon", stats.get("mic_name", "System-Standard"), FG),
            ("Quelle", stats.get("mic_hostapi", "Windows Default"), FG_DIM),
            ("Aktives Modell", self.cfg.get("model", "cohere"), FG),
            ("Sound-Profil", self.cfg.get("sound_profile", "warm"), FG),
        ]

        for title, value, color in cards:
            card = ctk.CTkFrame(self._setup_cards, fg_color=BG2, corner_radius=14)
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text=title, text_color=FG_DIM, font=ctk.CTkFont("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=value, text_color=color, font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(0, 12))

    def _animate(self):
        if not self._running:
            return
        try:
            stats = self.get_stats_fn()
            audio_level = stats.get("audio_level", 0.0)
            is_recording = stats.get("is_recording", False)
            self._draw_waveform(audio_level, is_recording)
            self._mic_level_bar.set(min(1.0, max(0.0, audio_level)))
            self._mic_level_text.configure(text=f"Level {int(min(100, audio_level * 100))}%")
        except Exception:
            pass
        self.after(40, self._animate)

    def _refresh(self):
        if not self._running:
            return
        try:
            stats = self.get_stats_fn()
            is_recording = stats.get("is_recording", False)

            if is_recording:
                self._status_badge.configure(text="Aufnahme laeuft", fg_color="#3a1010", text_color="#ffc0c0")
                self._summary_line.configure(text="Ich hoere gerade zu")
                self._sub_line.configure(text="Loslassen zum Transkribieren")
            elif self.models:
                self._status_badge.configure(text="Bereit", fg_color="#113122", text_color="#b7f7cb")
                self._summary_line.configure(text="Bereit fuer Diktat")
                self._sub_line.configure(text="Hotkey: Ctrl + Shift + Space")
            else:
                self._status_badge.configure(text="Modelle warten", fg_color="#3b2508", text_color="#ffd699")
                self._summary_line.configure(text="Modelle werden bei Bedarf geladen")
                self._sub_line.configure(text="Erster Hotkey startet das Laden")

            self._mic_name.configure(text=f"Mikrofon: {stats.get('mic_name', 'System-Standard')}")
            self._mic_host.configure(text=f"Quelle: {stats.get('mic_hostapi', 'Windows Default')}")

            rtf = stats.get("last_rtf", 0)
            rtf_color = GREEN if 0 < rtf < 1 else AMBER if rtf and rtf < 3 else RED if rtf else FG
            self._metric_labels["rtf"].configure(text=f"{rtf:.2f}" if rtf else "-", text_color=rtf_color)
            self._metric_labels["wpm"].configure(text=str(stats.get("last_wpm", "-")))
            self._metric_labels["cpu"].configure(text=f"{stats.get('cpu', 0):.0f}%")
            self._metric_labels["ram"].configure(text=f"{stats.get('ram_mb', 0):.0f} MB")

            self._update_history(stats.get("history", []))
            self._update_setup_tab(stats)
        except Exception:
            pass
        self.after(1200, self._refresh)

    def _on_close(self):
        self._running = False
        self.withdraw()


if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()
    cfg = settings_mod.load()
    start = time.time()

    def fake_stats():
        elapsed = time.time() - start
        return {
            "last_rtf": 0.42,
            "last_wpm": 138,
            "cpu": 18.0,
            "ram_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "history": [
                {"text": "Das ist ein Test der Spracherkennung mit Whisp.", "wpm": 138, "rtf": 0.42, "model": "cohere", "lang": "de"},
                {"text": "Hello world, this is a second transcription example.", "wpm": 110, "rtf": 0.51, "model": "cohere", "lang": "en"},
            ],
            "is_recording": int(elapsed) % 6 < 3,
            "audio_level": abs(math.sin(elapsed * 3)) * 0.8,
            "mic_name": "USB Podcast Microphone",
            "mic_hostapi": "WASAPI",
        }

    dash = Dashboard(root, cfg, {}, fake_stats)
    dash.mainloop()
