"""
Whisp — Modell-Download Script
Lädt das Cohere-Modell via HuggingFace Hub herunter.
Zeigt ein einfaches Fortschritts-Fenster.
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path


def _download(app_dir: Path, status_var: tk.StringVar, progress_var: tk.DoubleVar, done_event: threading.Event):
    try:
        venv_python = app_dir / "inference" / "venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = app_dir / "python" / "python.exe"

        # HuggingFace Hub Import via subprocess im venv
        import subprocess
        result = subprocess.run(
            [str(venv_python), "-c",
             "from huggingface_hub import snapshot_download; "
             "snapshot_download('CohereLabs/cohere-transcribe-03-2026', "
             "ignore_patterns=['*.msgpack', '*.h5', 'flax_model*', 'tf_model*'])"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            status_var.set("Modell erfolgreich heruntergeladen!")
            progress_var.set(100)
        else:
            status_var.set(f"Fehler: {result.stderr[:200]}")
    except Exception as e:
        status_var.set(f"Fehler: {e}")
    finally:
        done_event.set()


def main():
    app_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

    root = tk.Tk()
    root.title("Whisp — Modell herunterladen")
    root.configure(bg="#18181b")
    root.resizable(False, False)

    w, h = 480, 200
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(root, text="Whisp", bg="#18181b", fg="#6366f1",
             font=("Segoe UI", 18, "bold")).pack(pady=(20, 4))
    tk.Label(root, text="Cohere Transcribe Modell wird heruntergeladen…",
             bg="#18181b", fg="#a1a1aa", font=("Segoe UI", 10)).pack()

    progress_var = tk.DoubleVar(value=0)
    status_var   = tk.StringVar(value="Verbinde mit HuggingFace Hub…")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Whisp.Horizontal.TProgressbar",
                    troughcolor="#27272a", background="#6366f1", bordercolor="#18181b")

    bar = ttk.Progressbar(root, variable=progress_var, mode="indeterminate",
                          style="Whisp.Horizontal.TProgressbar", length=400)
    bar.pack(pady=16)
    bar.start(12)

    lbl = tk.Label(root, textvariable=status_var, bg="#18181b", fg="#f4f4f5",
                   font=("Segoe UI", 9))
    lbl.pack()

    done_event = threading.Event()

    def _check_done():
        if done_event.is_set():
            bar.stop()
            progress_var.set(100)
            root.after(1500, root.destroy)
        else:
            root.after(200, _check_done)

    threading.Thread(
        target=_download,
        args=(app_dir, status_var, progress_var, done_event),
        daemon=True
    ).start()

    root.after(200, _check_done)
    root.mainloop()


if __name__ == "__main__":
    main()
