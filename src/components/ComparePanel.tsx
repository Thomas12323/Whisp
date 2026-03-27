"use client";

import { useState } from "react";

export interface CompareColumn {
  modelId: string;
  modelLabel: string;
  status: "loading" | "done" | "error";
  result?: {
    text: string;
    durationMs?: number;
    audioDurationSec?: number;
    rtf?: number;
  };
  errorMsg?: string;
}

interface Props {
  columns: [CompareColumn, CompareColumn];
  elapsedMs: number;
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="text-xs px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
    >
      {copied ? "✓ Kopiert" : "Kopieren"}
    </button>
  );
}

function ColumnCard({
  col,
  elapsedMs,
  isWinner,
}: {
  col: CompareColumn;
  elapsedMs: number;
  isWinner: boolean;
}) {
  if (col.status === "loading") {
    return (
      <div className="rounded-xl border border-zinc-700/60 bg-zinc-900 overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
            {col.modelLabel}
          </span>
        </div>
        <div className="px-4 py-8 flex items-center justify-center gap-2 text-zinc-400 text-sm">
          <span className="w-4 h-4 rounded-full border-2 border-zinc-600 border-t-indigo-400 animate-spin" />
          <span>
            Transkribiere…{" "}
            <span className="text-zinc-500 font-mono">
              ({(elapsedMs / 1000).toFixed(1)} s)
            </span>
          </span>
        </div>
      </div>
    );
  }

  if (col.status === "error") {
    return (
      <div className="rounded-xl border border-red-500/25 bg-red-500/5 overflow-hidden">
        <div className="px-4 py-3 border-b border-red-500/10">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
            {col.modelLabel}
          </span>
        </div>
        <div className="px-4 py-4">
          <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1">
            Fehler
          </p>
          <p className="text-sm text-zinc-300">{col.errorMsg}</p>
        </div>
      </div>
    );
  }

  // done
  const text = col.result?.text ?? "";
  const words = countWords(text);
  const chars = text.length;
  const wpm =
    col.result?.audioDurationSec && col.result.audioDurationSec > 0
      ? Math.round((words / col.result.audioDurationSec) * 60)
      : null;

  return (
    <div
      className={`rounded-xl border bg-zinc-900 overflow-hidden ${
        isWinner
          ? "border-emerald-500/40"
          : "border-zinc-700/60"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-zinc-800 gap-3">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mr-1 flex items-center gap-1.5">
            {col.modelLabel}
            {isWinner && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 normal-case tracking-normal font-medium">
                🏆 Schneller
              </span>
            )}
          </span>

          {col.result?.durationMs !== undefined && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
              ⏱ {formatDuration(col.result.durationMs)}
            </span>
          )}
          {col.result?.rtf !== undefined && <RtfBadge rtf={col.result.rtf} />}
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
            {words} Wörter
          </span>
          {wpm !== null && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">
              {wpm} WPM
            </span>
          )}
        </div>
        <div className="shrink-0">
          <CopyButton text={text} />
        </div>
      </div>

      {/* Text */}
      <div className="px-4 py-4 max-h-72 overflow-y-auto">
        <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
          {text}
        </p>
      </div>
    </div>
  );
}

export default function ComparePanel({ columns, elapsedMs, onDismiss }: Props) {
  const bothDone = columns[0].status === "done" && columns[1].status === "done";
  const rtf0 = columns[0].result?.rtf;
  const rtf1 = columns[1].result?.rtf;
  const winnerIdx: number | null =
    bothDone && rtf0 !== undefined && rtf1 !== undefined
      ? rtf0 <= rtf1
        ? 0
        : 1
      : null;

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Vergleich
        </span>
        <button
          onClick={onDismiss}
          className="text-zinc-500 hover:text-zinc-300 transition-colors px-1 text-sm"
        >
          ✕
        </button>
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {columns.map((col, i) => (
          <ColumnCard
            key={col.modelId}
            col={col}
            elapsedMs={elapsedMs}
            isWinner={winnerIdx === i}
          />
        ))}
      </div>
    </div>
  );
}
