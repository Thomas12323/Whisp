export interface HistoryEntry {
  id: string;
  timestamp: number;
  sourceName: string;
  language: string;
  modelId: string;
  modelLabel: string;
  wordCount: number;
  charCount: number;
  transcriptionDurationMs: number;
  audioDurationSec: number | null;
  text: string;
}

const STORAGE_KEY = "whisp_history";
const MAX_ENTRIES = 20;

export function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as HistoryEntry[];
  } catch {
    return [];
  }
}

export function saveHistory(entries: HistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
}

export function prependEntry(
  entries: HistoryEntry[],
  entry: HistoryEntry
): HistoryEntry[] {
  return [entry, ...entries].slice(0, MAX_ENTRIES);
}
