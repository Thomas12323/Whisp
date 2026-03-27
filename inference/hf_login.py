"""
Whisp — HuggingFace Token Setup
Zeigt ein Fenster zur Token-Eingabe für den Zugang zu gated Models (Cohere).
"""
import subprocess
import sys
import webbrowser

import customtkinter as ctk

ctk.set_appearance_mode("dark")

BG     = "#09090b"
BG2    = "#18181b"
BG3    = "#27272a"
ACCENT = "#6366f1"
GREEN  = "#22c55e"
RED    = "#ef4444"
FG     = "#f4f4f5"
FG_DIM = "#a1a1aa"

HF_TOKEN_URL  = "https://huggingface.co/settings/tokens"
HF_MODEL_URL  = "https://huggingface.co/CohereLabs/cohere-transcribe-03-2026"


def open_token_window(on_done=None):
    win = ctk.CTkToplevel()
    win.title("Whisp — HuggingFace Zugang")
    win.configure(fg_color=BG)
    win.resizable(False, False)
    win.wm_attributes("-topmost", True)

    w, h = 500, 480
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Header ────────────────────────────────────────────────────────────────
    header = ctk.CTkFrame(win, fg_color=BG2, corner_radius=0, height=80)
    header.pack(fill="x")
    header.pack_propagate(False)

    ctk.CTkLabel(header, text="HuggingFace Token",
                  font=ctk.CTkFont("Segoe UI", 18, "bold"),
                  text_color=FG).pack(pady=(18, 0))
    ctk.CTkLabel(header, text="Für das Cohere-Modell benötigt",
                  font=ctk.CTkFont("Segoe UI", 11),
                  text_color=FG_DIM).pack()

    ctk.CTkFrame(win, fg_color=BG3, height=1, corner_radius=0).pack(fill="x")

    body = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True, padx=28, pady=20)

    # ── Schritt 1 ─────────────────────────────────────────────────────────────
    step1 = ctk.CTkFrame(body, fg_color=BG2, corner_radius=12)
    step1.pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(step1, text="Schritt 1  —  Modell freischalten",
                  font=ctk.CTkFont("Segoe UI", 12, "bold"),
                  text_color=FG).pack(anchor="w", padx=16, pady=(12, 4))
    ctk.CTkLabel(step1,
                  text="Besuche die Modell-Seite und akzeptiere die Nutzungsbedingungen.",
                  font=ctk.CTkFont("Segoe UI", 11),
                  text_color=FG_DIM, wraplength=420, justify="left").pack(
        anchor="w", padx=16, pady=(0, 8))
    ctk.CTkButton(step1, text="Modell-Seite öffnen →",
                   fg_color=BG3, hover_color="#3f3f46", text_color=FG,
                   font=ctk.CTkFont("Segoe UI", 11), corner_radius=8,
                   command=lambda: webbrowser.open(HF_MODEL_URL)).pack(
        anchor="w", padx=16, pady=(0, 12))

    # ── Schritt 2 ─────────────────────────────────────────────────────────────
    step2 = ctk.CTkFrame(body, fg_color=BG2, corner_radius=12)
    step2.pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(step2, text="Schritt 2  —  Token generieren",
                  font=ctk.CTkFont("Segoe UI", 12, "bold"),
                  text_color=FG).pack(anchor="w", padx=16, pady=(12, 4))
    ctk.CTkLabel(step2,
                  text='Erstelle ein Token mit "Read"-Berechtigung auf HuggingFace.',
                  font=ctk.CTkFont("Segoe UI", 11),
                  text_color=FG_DIM).pack(anchor="w", padx=16, pady=(0, 8))
    ctk.CTkButton(step2, text="Token-Seite öffnen →",
                   fg_color=BG3, hover_color="#3f3f46", text_color=FG,
                   font=ctk.CTkFont("Segoe UI", 11), corner_radius=8,
                   command=lambda: webbrowser.open(HF_TOKEN_URL)).pack(
        anchor="w", padx=16, pady=(0, 12))

    # ── Schritt 3 ─────────────────────────────────────────────────────────────
    step3 = ctk.CTkFrame(body, fg_color=BG2, corner_radius=12)
    step3.pack(fill="x")

    ctk.CTkLabel(step3, text="Schritt 3  —  Token eingeben",
                  font=ctk.CTkFont("Segoe UI", 12, "bold"),
                  text_color=FG).pack(anchor="w", padx=16, pady=(12, 4))

    token_entry = ctk.CTkEntry(step3, placeholder_text="hf_xxxxxxxxxxxxxxxxxxxx",
                                fg_color=BG3, border_color=BG3,
                                text_color=FG, show="*",
                                font=ctk.CTkFont("Segoe UI", 11),
                                height=38, corner_radius=8)
    token_entry.pack(fill="x", padx=16, pady=(0, 8))

    status_lbl = ctk.CTkLabel(step3, text="",
                                font=ctk.CTkFont("Segoe UI", 10),
                                text_color=FG_DIM)
    status_lbl.pack(anchor="w", padx=16)

    def _save_token():
        token = token_entry.get().strip()
        if not token.startswith("hf_") or len(token) < 10:
            status_lbl.configure(text="⚠  Ungültiges Token-Format (muss mit hf_ beginnen)",
                                   text_color=RED)
            return

        status_lbl.configure(text="Token wird gespeichert…", text_color=FG_DIM)
        win.update()

        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 f"from huggingface_hub import login; login(token='{token}', add_to_git_credential=False)"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                status_lbl.configure(text="✓  Token gespeichert — Cohere wird beim nächsten Start geladen",
                                      text_color=GREEN)
                if on_done:
                    win.after(1500, on_done)
                win.after(2000, win.destroy)
            else:
                status_lbl.configure(text=f"✗  Fehler: {result.stderr[:80]}",
                                      text_color=RED)
        except Exception as e:
            status_lbl.configure(text=f"✗  {e}", text_color=RED)

    ctk.CTkButton(step3, text="Token speichern",
                   fg_color=ACCENT, hover_color="#4f46e5",
                   text_color="white", font=ctk.CTkFont("Segoe UI", 12, "bold"),
                   corner_radius=8, height=38,
                   command=_save_token).pack(fill="x", padx=16, pady=(4, 14))

    return win


# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()
    w = open_token_window(on_done=root.destroy)
    root.mainloop()
