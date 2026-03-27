"use client";

import { useState } from "react";

interface Props {
  status: "done" | "error";
  text: string | null;
  durationMs?: number;
  audioDurationSec?: number;
  rtf?: number;
  errorMsg: string | null;
  onDismiss: () => void;
}

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function countWords(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function RtfBadge({ rtf }: { rtf: number }) {
  // RTF < 1 = faster than real-time (good), > 1 = slower (expected on CPU)
  const label = `RTF ${rtf.toFixed(2)}×`;
  const title =
    rtf < 1
      ? `${(1 / rtf).toFixed(1)}× schneller als Echtzeit`
      : `${rtf.toFixed(1)}× langsamer als Echtzeit`;
  const cls =
    rtf <= 1
      ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/20"
      : rtf <= 3
      ? "bg-amber-500/15 text-amber-300 border border-amber-500/20"
      : "bg-red-500/15 text-red-300 border border-red-500/20";
  return (
    <span title={title} className={`text-xs px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

export default function ResultPanel({
  status,
  text,
  durationMs,
  audioDurationSec,
  rtf,
  errorMsg,
  onDismiss,
}: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transkript-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (status === "error") {
    return (
      <div className="rounded-xl border border-red-500/25 bg-red-500/5 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1">
              Fehler
            </p>
            <p className="text-sm text-zinc-300">{errorMsg}</p>
          </div>
          <button onClick={onDismiss} className="text-zinc-500 hover:text-zinc-300 transition-colors mt-0.5 shrink-0">
            ✕
          </button>
        </div>
      </div>
    );
  }

  if (!text) return null;

  const words = countWords(text);
  const chars = text.length;
  const wpm =
    audioDurationSec && audioDurationSec > 0
      ? Math.round((words / audioDurationSec) * 60)
      : null;

  return (
    <div className="rounded-xl border border-zinc-700/60 bg-zinc-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-zinc-800 gap-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mr-1">
            Transkript
          </span>

          {/* Inference time */}
          {durationMs !== undefined && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
              ⏱ {formatDuration(durationMs)}
            </span>
          )}

          {/* RTF */}
          {rtf !== undefined && <RtfBadge rtf={rtf} />}

          {/* Counts */}
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
            {words} Wörter
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
            {chars} Zeichen
          </span>

          {/* WPM */}
          {wpm !== null && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">
              {wpm} WPM
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={copy}
            className="text-xs px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {copied ? "✓ Kopiert" : "Kopieren"}
          </button>
          <button
            onClick={download}
            className="text-xs px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Herunterladen
          </button>
          <button onClick={onDismiss} className="text-zinc-500 hover:text-zinc-300 transition-colors px-1">
            ✕
          </button>
        </div>
      </div>

      {/* Text */}
      <div className="px-4 py-4 max-h-80 overflow-y-auto">
        <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}
