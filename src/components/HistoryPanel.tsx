"use client";

import { useState } from "react";
import type { HistoryEntry } from "@/lib/history";

interface Props {
  entries: HistoryEntry[];
  onClear: () => void;
}

function formatTime(ms: number) {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function formatAgo(timestamp: number) {
  const diff = Math.floor((Date.now() - timestamp) / 1000);
  if (diff < 60) return "gerade eben";
  if (diff < 3600) return `vor ${Math.floor(diff / 60)} Min.`;
  if (diff < 86400) return `vor ${Math.floor(diff / 3600)} Std.`;
  return new Date(timestamp).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const LANGUAGE_LABELS: Record<string, string> = {
  de: "DE", en: "EN", fr: "FR", it: "IT", es: "ES", pt: "PT",
  nl: "NL", pl: "PL", el: "EL", ar: "AR", zh: "ZH", ja: "JA",
  ko: "KO", vi: "VI",
};

export default function HistoryPanel({ entries, onClear }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [open, setOpen] = useState(true);

  return (
    <div className="rounded-xl border border-zinc-800 overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 text-sm font-semibold text-zinc-300 hover:text-zinc-100 transition-colors"
        >
          <span
            className={`text-xs text-zinc-500 transition-transform ${open ? "rotate-90" : ""}`}
          >
            ▶
          </span>
          Verlauf
          <span className="text-xs font-normal text-zinc-500">{entries.length}</span>
        </button>
        {open && (
          <button
            onClick={onClear}
            className="text-xs text-zinc-500 hover:text-red-400 transition-colors"
          >
            Alles löschen
          </button>
        )}
      </div>

      {/* Entries */}
      {open && (
        <div className="divide-y divide-zinc-800/60 max-h-96 overflow-y-auto">
          {entries.map((entry) => {
            const isExpanded = expanded === entry.id;
            return (
              <div key={entry.id} className="bg-zinc-950">
                {/* Row */}
                <button
                  onClick={() => setExpanded(isExpanded ? null : entry.id)}
                  className="w-full px-4 py-3 text-left hover:bg-zinc-800/40 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm text-zinc-300 truncate max-w-[160px]">
                        {entry.sourceName}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 shrink-0">
                        {LANGUAGE_LABELS[entry.language] ?? entry.language}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-500">
                      <span>{entry.wordCount} Wörter</span>
                      {entry.transcriptionDurationMs > 0 && (
                        <span>⏱ {formatTime(entry.transcriptionDurationMs)}</span>
                      )}
                      <span>{formatAgo(entry.timestamp)}</span>
                      <span className={`text-zinc-600 transition-transform ${isExpanded ? "rotate-180" : ""}`}>
                        ▾
                      </span>
                    </div>
                  </div>
                  {!isExpanded && (
                    <p className="mt-1 text-xs text-zinc-500 truncate">
                      {entry.text.slice(0, 120)}
                    </p>
                  )}
                </button>

                {/* Expanded text */}
                {isExpanded && (
                  <div className="px-4 pb-4">
                    <div className="rounded-lg bg-zinc-900 border border-zinc-800 px-3 py-3 max-h-48 overflow-y-auto">
                      <p className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
                        {entry.text}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-zinc-600">
                        {entry.charCount} Zeichen
                      </span>
                      {entry.audioDurationSec && entry.audioDurationSec > 0 && (
                        <span className="text-xs text-zinc-600">
                          · {Math.round((entry.wordCount / entry.audioDurationSec) * 60)} WPM
                        </span>
                      )}
                      <span className="text-xs text-zinc-600">· {entry.modelLabel}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
