"""
Whisp — Dashboard (customtkinter)
Modernes UI mit Animationen, Waveform, Live-Metriken.
"""
import math
import random
import threading
import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import psutil

import settings as settings_mod

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG        = "#09090b"
BG2       = "#18181b"
BG3       = "#27272a"
ACCENT    = "#6366f1"
ACCENT_H  = "#4f46e5"
GREEN     = "#22c55e"
AMBER     = "#f59e0b"
RED       = "#ef4444"
FG        = "#f4f4f5"
FG_DIM    = "#a1a1aa"
FG_DIMMER = "#52525b"

LOGO_PATH = Path(__file__).parent / "assets" / "whisp_logo.png"
ICON_PATH = Path(__file__).parent / "assets" / "whisp.ico"


class Dashboard(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, models: dict, get_stats_fn):
        super().__init__(master)
        self.cfg          = cfg
        self.models       = models
        self.get_stats_fn = get_stats_fn
        self._running     = True
        self._wave_phase  = 0.0
        self._pulse_alpha = 1.0
        self._pulse_dir   = -1

        self.title("Whisp")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        w, h = 620, 700
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._build_ui()
        self._animate()
        self._refresh()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        hinner = ctk.CTkFrame(header, fg_color="transparent")
        hinner.pack(fill="x", padx=24, pady=0, expand=True)
        hinner.pack_configure(anchor="center")

        # Logo placeholder (ersetzt durch whisp_logo.png wenn vorhanden)
        logo_frame = ctk.CTkFrame(hinner, fg_color=ACCENT, corner_radius=10,
                                   width=40, height=40)
        logo_frame.pack(side="left", pady=16)
        logo_frame.pack_propagate(False)

        if LOGO_PATH.exists():
            try:
                img = ctk.CTkImage(
                    light_image=__import__("PIL.Image", fromlist=["Image"]).Image.open(LOGO_PATH),
                    size=(32, 32)
                )
                ctk.CTkLabel(logo_frame, image=img, text="").place(relx=.5, rely=.5, anchor="center")
            except Exception:
                ctk.CTkLabel(logo_frame, text="W", font=ctk.CTkFont("Segoe UI", 18, "bold"),
                              text_color="white").place(relx=.5, rely=.5, anchor="center")
        else:
            ctk.CTkLabel(logo_frame, text="W", font=ctk.CTkFont("Segoe UI", 18, "bold"),
                          text_color="white").place(relx=.5, rely=.5, anchor="center")

        title_frame = ctk.CTkFrame(hinner, fg_color="transparent")
        title_frame.pack(side="left", padx=(12, 0), pady=16)
        ctk.CTkLabel(title_frame, text="Whisp",
                      font=ctk.CTkFont("Segoe UI", 20, "bold"),
                      text_color=FG).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Lokale Spracherkennung",
                      font=ctk.CTkFont("Segoe UI", 11),
                      text_color=FG_DIM).pack(anchor="w")

        self._status_frame = ctk.CTkFrame(hinner, fg_color="transparent")
        self._status_frame.pack(side="right", pady=16)
        self._status_dot = ctk.CTkLabel(self._status_frame, text="●",
                                         font=ctk.CTkFont("Segoe UI", 12),
                                         text_color=AMBER)
        self._status_dot.pack(side="right")
        self._status_lbl = ctk.CTkLabel(self._status_frame, text="Bereit",
                                         font=ctk.CTkFont("Segoe UI", 11),
                                         text_color=FG_DIM)
        self._status_lbl.pack(side="right", padx=(0, 6))

        # Trennlinie
        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

        # Metriken
        metrics_frame = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=90)
        metrics_frame.pack(fill="x")
        metrics_frame.pack_propagate(False)

        self._metric_labels = {}
        for key, label, unit in [
            ("rtf", "RTF",  ""),
            ("wpm", "WPM",  ""),
            ("cpu", "CPU",  "%"),
            ("ram", "RAM",  "MB"),
        ]:
            col = ctk.CTkFrame(metrics_frame, fg_color="transparent")
            col.pack(side="left", expand=True, fill="both")

            val = ctk.CTkLabel(col, text="—",
                                font=ctk.CTkFont("Segoe UI", 26, "bold"),
                                text_color=FG)
            val.pack(pady=(18, 0))
            ctk.CTkLabel(col, text=f"{label}{unit}",
                          font=ctk.CTkFont("Segoe UI", 10),
                          text_color=FG_DIMMER).pack()
            self._metric_labels[key] = val

            if key != "ram":
                ctk.CTkFrame(metrics_frame, fg_color=BG3, width=1,
                              corner_radius=0).pack(side="left", fill="y", pady=16)

        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

        # Waveform Canvas
        self._wave_canvas = tk.Canvas(self, bg=BG2, height=64,
                                       highlightthickness=0, bd=0)
        self._wave_canvas.pack(fill="x")
        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

        # Tabs
        self._tabs = ctk.CTkTabview(self, fg_color=BG, segmented_button_fg_color=BG3,
                                     segmented_button_selected_color=ACCENT,
                                     segmented_button_selected_hover_color=ACCENT_H,
                                     segmented_button_unselected_color=BG3,
                                     segmented_button_unselected_hover_color="#3f3f46",
                                     text_color=FG, corner_radius=0)
        self._tabs.pack(fill="both", expand=True)
        self._tabs.add("  Transkriptionen  ")
        self._tabs.add("  Modell  ")
        self._tabs.add("  Einstellungen  ")

        self._build_transcriptions_tab(self._tabs.tab("  Transkriptionen  "))
        self._build_model_tab(self._tabs.tab("  Modell  "))
        self._build_settings_tab(self._tabs.tab("  Einstellungen  "))

        # Footer
        ctk.CTkFrame(self, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")
        footer = ctk.CTkFrame(self, fg_color=BG, corner_radius=0, height=36)
        footer.pack(fill="x")
        footer.pack_propagate(False)
        ctk.CTkLabel(footer, text="Ctrl + Shift + Space  —  Aufnahme halten",
                      font=ctk.CTkFont("Segoe UI", 9),
                      text_color=FG_DIMMER).pack(side="left", padx=20, pady=8)
        ctk.CTkLabel(footer, text="v1.0",
                      font=ctk.CTkFont("Segoe UI", 9),
                      text_color=FG_DIMMER).pack(side="right", padx=20)

    # ── Tab: Transkriptionen ──────────────────────────────────────────────────
    def _build_transcriptions_tab(self, parent):
        parent.configure(fg_color=BG)

        # Letzte Transkription
        top = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=12)
        top.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(top, text="LETZTE TRANSKRIPTION",
                      font=ctk.CTkFont("Segoe UI", 9, "bold"),
                      text_color=FG_DIMMER).pack(anchor="w", padx=16, pady=(12, 4))

        self._last_text = ctk.CTkTextbox(top, fg_color=BG3, text_color=FG,
                                          font=ctk.CTkFont("Segoe UI", 12),
                                          height=80, corner_radius=8,
                                          activate_scrollbars=False)
        self._last_text.pack(fill="x", padx=12, pady=(0, 12))
        self._last_text.configure(state="disabled")

        # Verlauf-Header
        hist_header = ctk.CTkFrame(parent, fg_color="transparent")
        hist_header.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(hist_header, text="VERLAUF",
                      font=ctk.CTkFont("Segoe UI", 9, "bold"),
                      text_color=FG_DIMMER).pack(side="left")

        # Scroll-Container
        self._hist_scroll = ctk.CTkScrollableFrame(parent, fg_color=BG,
                                                     corner_radius=0, height=300)
        self._hist_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

    def _update_history(self, history: list):
        # Letzte Transkription
        if history:
            self._last_text.configure(state="normal")
            self._last_text.delete("0.0", "end")
            self._last_text.insert("0.0", history[0].get("text", ""))
            self._last_text.configure(state="disabled")

        # Verlauf leeren
        for w in self._hist_scroll.winfo_children():
            w.destroy()

        if not history:
            ctk.CTkLabel(self._hist_scroll,
                          text="Noch keine Transkriptionen.\nCtrl+Shift+Space drücken um zu beginnen.",
                          font=ctk.CTkFont("Segoe UI", 11),
                          text_color=FG_DIMMER, justify="center").pack(pady=40)
            return

        for entry in history[:20]:
            card = ctk.CTkFrame(self._hist_scroll, fg_color=BG2, corner_radius=10)
            card.pack(fill="x", pady=3)

            text = entry.get("text", "")
            preview = text[:100] + ("…" if len(text) > 100 else "")
            ctk.CTkLabel(card, text=preview,
                          font=ctk.CTkFont("Segoe UI", 11),
                          text_color=FG, anchor="w", justify="left",
                          wraplength=500).pack(fill="x", padx=14, pady=(10, 4))

            parts = []
            if entry.get("wpm"):   parts.append(f"{entry['wpm']} WPM")
            if entry.get("rtf"):   parts.append(f"RTF {entry['rtf']:.2f}")
            if entry.get("model"): parts.append(entry["model"].capitalize())
            if entry.get("lang"):  parts.append(entry["lang"].upper())

            if parts:
                ctk.CTkLabel(card, text="  ·  ".join(parts),
                              font=ctk.CTkFont("Segoe UI", 9),
                              text_color=FG_DIMMER).pack(anchor="w", padx=14, pady=(0, 8))

    # ── Tab: Modell ───────────────────────────────────────────────────────────
    def _build_model_tab(self, parent):
        parent.configure(fg_color=BG)

        ctk.CTkLabel(parent, text="GELADENE MODELLE",
                      font=ctk.CTkFont("Segoe UI", 9, "bold"),
                      text_color=FG_DIMMER).pack(anchor="w", padx=16, pady=(12, 6))

        self._model_cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._model_cards_frame.pack(fill="x", padx=16)

        ctk.CTkFrame(parent, fg_color=BG3, height=1, corner_radius=0).pack(
            fill="x", padx=16, pady=16)

        ctk.CTkLabel(parent, text="SYSTEM",
                      font=ctk.CTkFont("Segoe UI", 9, "bold"),
                      text_color=FG_DIMMER).pack(anchor="w", padx=16, pady=(0, 8))

        self._sys_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._sys_frame.pack(fill="x", padx=16)

    def _update_model_tab(self, models: dict, stats: dict):
        # Model cards
        try:
            for w in self._model_cards_frame.winfo_children():
                w.destroy()

            for key, name, desc in [
                ("cohere",  "Cohere Transcribe", "2B Parameter · Apache 2.0 · 2026"),
                ("whisper", "faster-whisper",    f"{self.cfg.get('whisper_size','small')} · OpenAI · CTranslate2"),
            ]:
                loaded    = key in models
                active    = self.cfg.get("model") == key
                dot_color = GREEN if loaded else FG_DIMMER
                status    = "Geladen ✓" if loaded else "Wird beim ersten Hotkey-Druck geladen"

                card = ctk.CTkFrame(self._model_cards_frame, fg_color=BG2, corner_radius=12)
                card.pack(fill="x", pady=4)

                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=12)

                ctk.CTkLabel(row, text="●", font=ctk.CTkFont("Segoe UI", 12),
                              text_color=dot_color).pack(side="left")
                ctk.CTkLabel(row, text=f"  {name}",
                              font=ctk.CTkFont("Segoe UI", 13, "bold"),
                              text_color=FG).pack(side="left")

                if active:
                    badge = ctk.CTkLabel(row, text=" AKTIV ",
                                          font=ctk.CTkFont("Segoe UI", 9, "bold"),
                                          fg_color=ACCENT, text_color="white",
                                          corner_radius=4)
                    badge.pack(side="left", padx=(10, 0))

                ctk.CTkLabel(card, text=desc,
                              font=ctk.CTkFont("Segoe UI", 10),
                              text_color=FG_DIMMER).pack(anchor="w", padx=16, pady=(0, 4))
                ctk.CTkLabel(card, text=status,
                              font=ctk.CTkFont("Segoe UI", 10),
                              text_color=dot_color).pack(anchor="w", padx=16, pady=(0, 10))
        except Exception:
            pass

        # System info
        try:
            for w in self._sys_frame.winfo_children():
                w.destroy()

            try:
                import torch
                device = "CUDA (GPU)" if torch.cuda.is_available() else "CPU"
            except Exception:
                device = "CPU"

            mem   = psutil.virtual_memory()
            proc  = psutil.Process()
            ram   = f"{mem.used/1073741824:.1f} / {mem.total/1073741824:.1f} GB"
            rammb = f"{proc.memory_info().rss/1048576:.0f} MB"

            for label, value in [
                ("Gerät",       device),
                ("System-RAM",  ram),
                ("Prozess-RAM", rammb),
                ("CPU",         f"{stats.get('cpu', 0):.0f}%"),
            ]:
                row = ctk.CTkFrame(self._sys_frame, fg_color="transparent")
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=label, width=140, anchor="w",
                              font=ctk.CTkFont("Segoe UI", 11),
                              text_color=FG_DIM).pack(side="left")
                ctk.CTkLabel(row, text=value,
                              font=ctk.CTkFont("Segoe UI", 11),
                              text_color=FG).pack(side="left")
        except Exception:
            pass

    # ── Tab: Einstellungen ────────────────────────────────────────────────────
    def _build_settings_tab(self, parent):
        parent.configure(fg_color=BG)
        try:
            import settings_window
            settings_window.build_embedded(parent, self.cfg, self._on_settings_saved)
        except Exception as e:
            ctk.CTkLabel(parent, text=f"Einstellungen konnten nicht geladen werden:\n{e}",
                          text_color=RED).pack(pady=40)

    def _on_settings_saved(self, new_cfg: dict):
        self.cfg.update(new_cfg)
        settings_mod.save(self.cfg)

    # ── Waveform Animation ────────────────────────────────────────────────────
    def _draw_waveform(self, audio_level: float = 0.0, is_recording: bool = False):
        c = self._wave_canvas
        c.delete("all")
        w = c.winfo_width() or 620
        h = 64
        bars = 48
        bar_w = max(2, w // bars - 2)
        spacing = w / bars

        self._wave_phase += 0.08

        for i in range(bars):
            x = int(i * spacing + spacing / 2)

            if is_recording and audio_level > 0.01:
                amp = audio_level * 28 * (
                    0.4 + 0.6 * abs(math.sin(self._wave_phase + i * 0.4))
                )
                amp = max(3, amp)
            else:
                amp = 4 + 3 * abs(math.sin(self._wave_phase * 0.3 + i * 0.25))

            cy = h // 2
            color = ACCENT if is_recording else FG_DIMMER
            alpha_factor = 0.5 + 0.5 * abs(math.sin(self._wave_phase * 0.5 + i * 0.2))
            bar_color = self._blend_color(color, BG2, alpha_factor)

            c.create_rectangle(
                x - bar_w // 2, cy - amp,
                x + bar_w // 2, cy + amp,
                fill=bar_color, outline="", tags="wave"
            )

    def _blend_color(self, hex1: str, hex2: str, t: float) -> str:
        r1, g1, b1 = int(hex1[1:3],16), int(hex1[3:5],16), int(hex1[5:7],16)
        r2, g2, b2 = int(hex2[1:3],16), int(hex2[3:5],16), int(hex2[5:7],16)
        r = int(r1 * t + r2 * (1 - t))
        g = int(g1 * t + g2 * (1 - t))
        b = int(b1 * t + b2 * (1 - t))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Animations Loop ───────────────────────────────────────────────────────
    def _animate(self):
        if not self._running:
            return
        try:
            stats         = self.get_stats_fn()
            is_recording  = stats.get("is_recording", False)
            audio_level   = stats.get("audio_level", 0.0)
            self._draw_waveform(audio_level, is_recording)

            # Status-Dot pulsieren wenn Aufnahme läuft
            if is_recording:
                self._pulse_alpha += self._pulse_dir * 0.06
                if self._pulse_alpha <= 0.3 or self._pulse_alpha >= 1.0:
                    self._pulse_dir *= -1
                self._pulse_alpha = max(0.3, min(1.0, self._pulse_alpha))
                r = int(239 * self._pulse_alpha)
                self._status_dot.configure(text_color=f"#{r:02x}2424")
            else:
                self._status_dot.configure(
                    text_color=GREEN if self.models else AMBER)
        except Exception:
            pass
        self.after(40, self._animate)   # 25 fps

    # ── Data Refresh Loop ─────────────────────────────────────────────────────
    def _refresh(self):
        if not self._running:
            return
        try:
            stats = self.get_stats_fn()

            # Status
            if self.models:
                loaded = ", ".join(self.models.keys())
                self._status_lbl.configure(text=f"Bereit  ·  {loaded}")
                self._status_dot.configure(text_color=GREEN)
            else:
                self._status_lbl.configure(text="Hotkey drücken zum Laden")
                self._status_dot.configure(text_color=AMBER)

            # Metriken
            rtf = stats.get("last_rtf", 0)
            rtf_color = (GREEN if rtf < 1 else AMBER if rtf < 3 else RED) if rtf else FG
            self._metric_labels["rtf"].configure(
                text=f"{rtf:.2f}" if rtf else "—", text_color=rtf_color)
            self._metric_labels["wpm"].configure(
                text=str(stats.get("last_wpm", "—")))
            self._metric_labels["cpu"].configure(
                text=f"{stats.get('cpu', 0):.0f}")
            self._metric_labels["ram"].configure(
                text=f"{stats.get('ram_mb', 0):.0f}")

            # History
            self._update_history(stats.get("history", []))

            # Modell-Tab
            self._update_model_tab(self.models, stats)

        except Exception:
            pass
        self.after(1500, self._refresh)

    def _on_close(self):
        self._running = False
        self.withdraw()


# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()

    cfg = settings_mod.load()
    t0  = time.time()

    def fake_stats():
        elapsed = time.time() - t0
        return {
            "last_rtf":    0.42,
            "last_wpm":    138,
            "cpu":         12.5,
            "ram_mb":      3840,
            "is_recording": (int(elapsed) % 6) < 3,
            "audio_level":  abs(math.sin(elapsed * 3)) * 0.8,
            "history": [
                {"text": "Das ist ein Test der Spracherkennung mit Whisp.",
                 "wpm": 138, "rtf": 0.42, "model": "cohere", "lang": "de"},
                {"text": "Hello world, this is a second transcription example.",
                 "wpm": 110, "rtf": 0.51, "model": "cohere", "lang": "en"},
            ],
        }

    dash = Dashboard(root, cfg, {}, fake_stats)
    dash.mainloop()
