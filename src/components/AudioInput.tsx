"use client";

import { useEffect, useRef, useState } from "react";
import { ACCEPTED_EXTENSIONS } from "@/lib/config";

export type AudioSource =
  | { type: "file"; file: File }
  | { type: "recording"; blob: Blob; durationSec: number };

// ---------------------------------------------------------------------------
// Browser-side WebM → WAV conversion (avoids server-side ffmpeg dependency)
// ---------------------------------------------------------------------------

function encodeWav(buffer: AudioBuffer): Blob {
  const samples = buffer.getChannelData(0);
  const numSamples = samples.length;
  const sampleRate = buffer.sampleRate;
  const dataLen = numSamples * 2;
  const ab = new ArrayBuffer(44 + dataLen);
  const v = new DataView(ab);
  const str = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i));
  };
  str(0, "RIFF"); v.setUint32(4, 36 + dataLen, true);
  str(8, "WAVE"); str(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);  v.setUint32(24, sampleRate, true);
  v.setUint32(28, sampleRate * 2, true); v.setUint16(32, 2, true);
  v.setUint16(34, 16, true); str(36, "data"); v.setUint32(40, dataLen, true);
  let off = 44;
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return new Blob([ab], { type: "audio/wav" });
}

async function webmToWav(blob: Blob): Promise<{ wav: Blob; durationSec: number }> {
  const arrayBuffer = await blob.arrayBuffer();
  const decodeCtx = new AudioContext();
  const audioBuffer = await decodeCtx.decodeAudioData(arrayBuffer);
  await decodeCtx.close();
  // Resample to 16 kHz mono
  const sr = 16000;
  const numSamples = Math.ceil(audioBuffer.duration * sr);
  const offCtx = new OfflineAudioContext(1, numSamples, sr);
  const src = offCtx.createBufferSource();
  src.buffer = audioBuffer;
  src.connect(offCtx.destination);
  src.start();
  const rendered = await offCtx.startRendering();
  return { wav: encodeWav(rendered), durationSec: audioBuffer.duration };
}

interface Props {
  value: AudioSource | null;
  onChange: (source: AudioSource | null) => void;
  /** Called once the audio player knows the real decoded duration */
  onDurationKnown?: (sec: number) => void;
  disabled?: boolean;
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(sec: number) {
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = (sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function AudioInput({ value, onChange, onDurationKnown, disabled }: Props) {
  const [tab, setTab] = useState<"upload" | "mic">("upload");
  const [dragging, setDragging] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [micLevel, setMicLevel] = useState(0);
  const [micError, setMicError] = useState<string | null>(null);
  const [converting, setConverting] = useState(false);

  // Audio preview URL
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Create / revoke object URL for audio preview
  useEffect(() => {
    if (!value) {
      setAudioUrl(null);
      return;
    }
    const blob = value.type === "file" ? value.file : value.blob;
    const url = URL.createObjectURL(blob);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      audioCtxRef.current?.close();
      if (recorderRef.current?.state !== "inactive") recorderRef.current?.stop();
    };
  }, []);

  const handleFile = (file: File) => {
    onChange({ type: "file", file });
    setTab("upload");
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  // --- Mic level meter ---
  const startLevelMeter = (stream: MediaStream) => {
    const ctx = new AudioContext();
    audioCtxRef.current = ctx;
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;
      setMicLevel(avg / 255);
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
  };

  const stopLevelMeter = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    setMicLevel(0);
  };

  // --- Recording ---
  const startRecording = async () => {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      startLevelMeter(stream);

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stopLevelMeter();
        stream.getTracks().forEach((t) => t.stop());
        const rawBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        const timerSec = seconds;
        setSeconds(0);
        setRecording(false);
        setConverting(true);
        try {
          // Convert WebM → WAV in the browser so soundfile can read it server-side
          const { wav, durationSec } = await webmToWav(rawBlob);
          onChange({ type: "recording", blob: wav, durationSec });
          onDurationKnown?.(durationSec);
        } catch {
          // Fallback: send raw WebM (may fail on server if ffmpeg not installed)
          onChange({ type: "recording", blob: rawBlob, durationSec: timerSec });
          if (timerSec > 0) onDurationKnown?.(timerSec);
        } finally {
          setConverting(false);
        }
      };

      recorder.start(100);
      recorderRef.current = recorder;
      setSeconds(0);
      setRecording(true);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      setMicError("Kein Mikrofonzugriff — bitte im Browser erlauben.");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.stop();
  };

  const clear = () => {
    onChange(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div>
      {/* Tab switcher */}
      <div className="flex gap-1 p-1 bg-zinc-900 rounded-lg mb-3 w-fit">
        {(["upload", "mic"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            disabled={disabled || recording}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-zinc-700 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {t === "upload" ? "Datei" : "Mikrofon"}
          </button>
        ))}
      </div>

      {/* --- Upload zone --- */}
      {tab === "upload" && (
        <div
          onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => !disabled && !value && fileRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl px-6 py-8 text-center transition-colors ${
            dragging
              ? "border-indigo-500 bg-indigo-500/5"
              : value
              ? "border-zinc-700 cursor-default"
              : "border-zinc-700 hover:border-zinc-500 hover:bg-zinc-800/20 cursor-pointer"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {value?.type === "file" ? (
            <div className="flex items-center justify-center gap-3">
              <span className="text-2xl">🎵</span>
              <div className="text-left min-w-0">
                <p className="text-sm font-medium text-zinc-200 truncate max-w-xs">
                  {value.file.name}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">{formatBytes(value.file.size)}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); clear(); }}
                className="ml-2 p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                ✕
              </button>
            </div>
          ) : (
            <>
              <div className="text-3xl mb-2">📂</div>
              <p className="text-sm text-zinc-300">
                Datei ablegen oder{" "}
                <span className="text-indigo-400 font-medium">klicken</span>
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                MP3 · WAV · FLAC · OGG · M4A · WebM · bis 500 MB
              </p>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            disabled={disabled}
          />
        </div>
      )}

      {/* --- Mic zone --- */}
      {tab === "mic" && (
        <div className="border border-zinc-700 rounded-xl px-6 py-8 text-center">
          {micError && <p className="text-red-400 text-sm mb-4">{micError}</p>}

          {converting ? (
            <div className="flex items-center justify-center gap-2 text-zinc-400 text-sm">
              <span className="w-4 h-4 rounded-full border-2 border-zinc-600 border-t-indigo-400 animate-spin" />
              Audio wird aufbereitet…
            </div>
          ) : value?.type === "recording" && !recording ? (
            <div className="flex items-center justify-center gap-3">
              <span className="text-2xl">🎙</span>
              <div className="text-left">
                <p className="text-sm font-medium text-zinc-200">Aufnahme</p>
                <p className="text-xs text-zinc-500">{formatTime(value.durationSec)}</p>
              </div>
              <button
                onClick={clear}
                className="ml-2 p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                ✕
              </button>
            </div>
          ) : recording ? (
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <span className="font-mono text-xl text-zinc-100">{formatTime(seconds)}</span>
              </div>
              {/* Mic level meter */}
              <div className="w-48 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full"
                  style={{ width: `${micLevel * 100}%`, transition: "none" }}
                />
              </div>
              <button
                onClick={stopRecording}
                className="mt-1 px-5 py-2 rounded-lg text-sm font-medium border border-red-500/40 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Aufnahme beenden
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={startRecording}
                disabled={disabled}
                className="w-14 h-14 rounded-full border-2 border-zinc-600 bg-zinc-800 flex items-center justify-center text-xl hover:border-zinc-400 hover:bg-zinc-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                🎙
              </button>
              <p className="text-sm text-zinc-400">Klicken zum Aufnehmen</p>
            </div>
          )}
        </div>
      )}

      {/* --- Audio player --- */}
      {audioUrl && !recording && (
        <div className="mt-3">
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio
            key={audioUrl}
            src={audioUrl}
            controls
            className="w-full h-9"
            style={{ accentColor: "#6366f1" }}
            onLoadedMetadata={(e) => {
              const dur = e.currentTarget.duration;
              if (isFinite(dur) && dur > 0) onDurationKnown?.(dur);
            }}
          />
        </div>
      )}
    </div>
  );
}
