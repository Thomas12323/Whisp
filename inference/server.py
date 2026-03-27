"""
Whisp inference server — runs CohereLabs/cohere-transcribe-03-2026 and faster-whisper locally.

Start with:
    python server.py

Environment variables:
    WHISPER_MODEL_SIZE  faster-whisper model size (default: small)
                        Options: tiny, base, small, medium, large-v3
                        Note: large-v3 requires ~3 GB RAM on top of Cohere's ~4 GB.
"""

import io
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

import librosa
import numpy as np
import psutil
import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

COHERE_MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
device = "cuda" if torch.cuda.is_available() else "cpu"

# Dict keyed by model name; values depend on model type
models: dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Background CPU monitor (non-blocking for health endpoint)
# ---------------------------------------------------------------------------
_cpu_percent: float = 0.0


def _cpu_monitor() -> None:
    global _cpu_percent
    while True:
        _cpu_percent = psutil.cpu_percent(interval=1.0)


threading.Thread(target=_cpu_monitor, daemon=True).start()


# ---------------------------------------------------------------------------
# Lifespan — load both models independently so one failure doesn't kill the server
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Cohere Transcribe
    try:
        log.info("Loading Cohere model %s on %s …", COHERE_MODEL_ID, device)
        cohere_processor = AutoProcessor.from_pretrained(COHERE_MODEL_ID, trust_remote_code=True)
        cohere_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            COHERE_MODEL_ID, trust_remote_code=True
        ).to(device)
        cohere_model.eval()
        models["cohere"] = {"processor": cohere_processor, "model": cohere_model}
        log.info("Cohere model loaded.")
    except Exception as e:
        log.error("Failed to load Cohere model: %s", e)

    # Load faster-whisper
    try:
        log.info("Loading faster-whisper (%s) on %s …", WHISPER_MODEL_SIZE, device)
        from faster_whisper import WhisperModel
        compute_type = "float16" if device == "cuda" else "int8"
        whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
        models["whisper"] = whisper_model
        log.info("faster-whisper (%s) loaded.", WHISPER_MODEL_SIZE)
    except Exception as e:
        log.error("Failed to load faster-whisper: %s", e)

    log.info("Server ready. Loaded models: %s", list(models.keys()))
    yield
    log.info("Shutting down.")


app = FastAPI(title="Whisp inference server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    proc = psutil.Process()
    proc_mem_mb = proc.memory_info().rss / 1024 / 1024
    vm = psutil.virtual_memory()
    return {
        "status": "ok",
        "model_loaded": len(models) > 0,
        "models_loaded": list(models.keys()),
        "device": device,
        "cpu_percent": round(_cpu_percent, 1),
        "process_memory_mb": round(proc_mem_mb),
        "system_memory_used_gb": round(vm.used / 1024 ** 3, 1),
        "system_memory_total_gb": round(vm.total / 1024 ** 3, 1),
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(...),
    model: str = Form("cohere"),
) -> dict:
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    # Decode audio with librosa — handles MP3, WebM, M4A, WAV, FLAC, OGG, …
    try:
        audio_array, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
        audio_array = audio_array.astype(np.float32)
        audio_duration_sec = len(audio_array) / 16000
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Audio decoding failed: {exc}") from exc

    if model == "whisper":
        wm = models.get("whisper")
        if wm is None:
            raise HTTPException(status_code=503, detail="faster-whisper not loaded.")
        try:
            t0 = time.perf_counter()
            # Materialize the lazy generator before stopping the clock —
            # faster-whisper is lazy and yields nothing until iterated.
            segments_gen, _ = wm.transcribe(audio_array, language=language, beam_size=5)
            segments_list = list(segments_gen)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            text = " ".join(seg.text.strip() for seg in segments_list)
        except Exception as exc:
            log.exception("Whisper transcription failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    else:
        # Default: Cohere Transcribe
        cohere = models.get("cohere")
        if cohere is None:
            raise HTTPException(status_code=503, detail="Cohere model not loaded.")
        try:
            t0 = time.perf_counter()
            texts = cohere["model"].transcribe(
                processor=cohere["processor"],
                audio_arrays=[audio_array],
                sample_rates=[16000],
                language=language,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            text = texts[0]
        except Exception as exc:
            log.exception("Cohere transcription failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    rtf = round(duration_ms / (audio_duration_sec * 1000), 3) if audio_duration_sec > 0 else None

    log.info(
        "[%s] Transcribed %.1fs audio in %.1fs (RTF %.2f) — %d words",
        model,
        audio_duration_sec,
        duration_ms / 1000,
        rtf or 0,
        len(text.split()),
    )

    return {
        "text": text,
        "duration_ms": duration_ms,
        "audio_duration_sec": round(audio_duration_sec, 2),
        "rtf": rtf,
    }


if __name__ == "__main__":
    port = 8000
    log.info("Starting Whisp inference server on http://localhost:%d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
