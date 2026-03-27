"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AudioInput, { type AudioSource } from "./AudioInput";
import LanguageSelect from "./LanguageSelect";
import ModelSelect from "./ModelSelect";
import ModelCheckboxGroup from "./ModelCheckboxGroup";
import ResultPanel from "./ResultPanel";
import ComparePanel, { type CompareColumn } from "./ComparePanel";
import HistoryPanel from "./HistoryPanel";
import { PROVIDERS } from "@/lib/providers/metadata";
import { SUPPORTED_LANGUAGES } from "@/lib/config";
import { type HistoryEntry, loadHistory, saveHistory } from "@/lib/history";

type Status = "idle" | "loading" | "done" | "error";
type Mode = "single" | "compare";

function countWords(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function formatElapsed(ms: number) {
  return `${(ms / 1000).toFixed(1)} s`;
}

export default function TranscribeForm() {
  const [audioSource, setAudioSource] = useState<AudioSource | null>(null);
  const [audioDurationSec, setAudioDurationSec] = useState<number | null>(null);
  const [language, setLanguage] = useState<string>(SUPPORTED_LANGUAGES[0].code);

  // Mode: single or compare
  const [mode, setMode] = useState<Mode>("single");

  // Single mode
  const [modelId, setModelId] = useState(PROVIDERS[0].id);
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<{
    text: string;
    durationMs?: number;
    audioDurationSec?: number;
    rtf?: number;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Compare mode
  const [selectedModels, setSelectedModels] = useState<string[]>(
    PROVIDERS.map((p) => p.id)
  );
  const [compareColumns, setCompareColumns] = useState<[CompareColumn, CompareColumn] | null>(null);

  // Shared: elapsed time during loading
  const [elapsedMs, setElapsedMs] = useState(0);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // History
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  // -------------------------------------------------------------------------
  // Derived state
  // -------------------------------------------------------------------------

  const isSingleLoading = mode === "single" && status === "loading";
  const isCompareLoading =
    mode === "compare" &&
    compareColumns !== null &&
    compareColumns.some((c) => c.status === "loading");
  const isLoading = isSingleLoading || isCompareLoading;

  const hasEnoughModels =
    mode === "single" ? true : selectedModels.length === 2;
  const canSubmit = audioSource !== null && !isLoading && hasEnoughModels;

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  const startElapsed = () => {
    setElapsedMs(0);
    const t0 = Date.now();
    elapsedRef.current = setInterval(() => setElapsedMs(Date.now() - t0), 200);
  };

  const stopElapsed = () => {
    if (elapsedRef.current) {
      clearInterval(elapsedRef.current);
      elapsedRef.current = null;
    }
  };

  const buildFormData = (src: AudioSource) => {
    const body = new FormData();
    if (src.type === "file") {
      body.append("file", src.file);
    } else {
      const ext = src.blob.type.includes("wav") ? "wav" : "webm";
      body.append("file", src.blob, `recording.${ext}`);
    }
    return body;
  };

  const classifyError = (err: unknown, res?: Response): string => {
    if (err instanceof DOMException && err.name === "AbortError") {
      return "Zeitüberschreitung nach 3 Minuten.";
    }
    if (res) {
      if (res.status === 415) return "Dateiformat nicht unterstützt.";
      if (res.status === 413) return "Datei zu groß (max. 500 MB).";
    }
    if (err instanceof Error) return err.message;
    return "Unbekannter Fehler.";
  };

  const addHistory = (entries: HistoryEntry[]) => {
    setHistory((prev) => {
      const next = [...entries, ...prev].slice(0, 20);
      saveHistory(next);
      return next;
    });
  };

  const dismiss = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setErrorMsg(null);
    setCompareColumns(null);
  }, []);

  // -------------------------------------------------------------------------
  // Audio source handling
  // -------------------------------------------------------------------------

  const handleAudioChange = (src: AudioSource | null) => {
    setAudioSource(src);
    if (!src) {
      setAudioDurationSec(null);
    } else if (src.type === "recording") {
      setAudioDurationSec(src.durationSec > 0 ? src.durationSec : null);
    }
  };

  // -------------------------------------------------------------------------
  // Single-model submit
  // -------------------------------------------------------------------------

  const handleSingleSubmit = useCallback(async () => {
    if (!audioSource) return;

    setStatus("loading");
    setResult(null);
    setErrorMsg(null);
    startElapsed();

    const body = buildFormData(audioSource);
    body.append("language", language);
    body.append("modelId", modelId);

    let res: Response | undefined;
    try {
      res = await fetch("/api/transcribe", { method: "POST", body });
      const data = await res.json() as {
        text?: string;
        error?: string;
        durationMs?: number;
        audioDurationSec?: number;
        rtf?: number;
      };

      if (!res.ok || data.error) {
        const msg = data.error ?? classifyError(null, res);
        setErrorMsg(msg);
        setStatus("error");
      } else {
        const text = data.text ?? "";
        const resolvedAudioDuration = data.audioDurationSec ?? audioDurationSec ?? null;
        if (resolvedAudioDuration !== null) setAudioDurationSec(resolvedAudioDuration);

        setResult({
          text,
          durationMs: data.durationMs,
          audioDurationSec: resolvedAudioDuration ?? undefined,
          rtf: data.rtf,
        });
        setStatus("done");

        const modelMeta = PROVIDERS.find((p) => p.id === modelId);
        const entry: HistoryEntry = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          sourceName: audioSource.type === "file" ? audioSource.file.name : "Aufnahme",
          language,
          modelId,
          modelLabel: modelMeta?.label ?? modelId,
          wordCount: countWords(text),
          charCount: text.length,
          transcriptionDurationMs: data.durationMs ?? 0,
          audioDurationSec: resolvedAudioDuration,
          text,
        };
        addHistory([entry]);
      }
    } catch (err) {
      setErrorMsg(classifyError(err, res));
      setStatus("error");
    } finally {
      stopElapsed();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioSource, language, modelId, audioDurationSec]);

  // -------------------------------------------------------------------------
  // Compare submit
  // -------------------------------------------------------------------------

  const handleCompareSubmit = useCallback(async () => {
    if (!audioSource || selectedModels.length < 2) return;

    const [idA, idB] = selectedModels;
    const labelA = PROVIDERS.find((p) => p.id === idA)?.label ?? idA;
    const labelB = PROVIDERS.find((p) => p.id === idB)?.label ?? idB;

    setCompareColumns([
      { modelId: idA, modelLabel: labelA, status: "loading" },
      { modelId: idB, modelLabel: labelB, status: "loading" },
    ]);
    startElapsed();

    const makeRequest = async (mId: string) => {
      const body = buildFormData(audioSource);
      body.append("language", language);
      body.append("modelId", mId);
      const res = await fetch("/api/transcribe", { method: "POST", body });
      const data = await res.json() as {
        text?: string;
        error?: string;
        durationMs?: number;
        audioDurationSec?: number;
        rtf?: number;
      };
      if (!res.ok || data.error) {
        throw new Error(data.error ?? classifyError(null, res));
      }
      return data;
    };

    const [settledA, settledB] = await Promise.allSettled([
      makeRequest(idA),
      makeRequest(idB),
    ]);

    stopElapsed();

    const resolvedAudioDuration =
      (settledA.status === "fulfilled" ? settledA.value.audioDurationSec : null) ??
      (settledB.status === "fulfilled" ? settledB.value.audioDurationSec : null) ??
      audioDurationSec ??
      null;
    if (resolvedAudioDuration !== null) setAudioDurationSec(resolvedAudioDuration);

    const toColumn = (
      modelId: string,
      modelLabel: string,
      settled: PromiseSettledResult<{
        text?: string;
        durationMs?: number;
        audioDurationSec?: number;
        rtf?: number;
      }>
    ): CompareColumn => {
      if (settled.status === "fulfilled") {
        return {
          modelId,
          modelLabel,
          status: "done",
          result: {
            text: settled.value.text ?? "",
            durationMs: settled.value.durationMs,
            audioDurationSec: resolvedAudioDuration ?? undefined,
            rtf: settled.value.rtf,
          },
        };
      }
      return {
        modelId,
        modelLabel,
        status: "error",
        errorMsg:
          settled.reason instanceof Error
            ? settled.reason.message
            : "Unbekannter Fehler.",
      };
    };

    const newCols: [CompareColumn, CompareColumn] = [
      toColumn(idA, labelA, settledA),
      toColumn(idB, labelB, settledB),
    ];
    setCompareColumns(newCols);

    // Save successful runs to history
    const sourceName =
      (audioSource.type === "file" ? audioSource.file.name : "Aufnahme") +
      " (Vergleich)";
    const newEntries: HistoryEntry[] = newCols
      .filter((col) => col.status === "done" && col.result)
      .map((col) => ({
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        sourceName,
        language,
        modelId: col.modelId,
        modelLabel: col.modelLabel,
        wordCount: countWords(col.result!.text),
        charCount: col.result!.text.length,
        transcriptionDurationMs: col.result!.durationMs ?? 0,
        audioDurationSec: resolvedAudioDuration,
        text: col.result!.text,
      }));
    if (newEntries.length > 0) addHistory(newEntries);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioSource, language, selectedModels, audioDurationSec]);

  // -------------------------------------------------------------------------
  // Unified submit
  // -------------------------------------------------------------------------

  const handleSubmitRef = useRef(
    mode === "single" ? handleSingleSubmit : handleCompareSubmit
  );
  useEffect(() => {
    handleSubmitRef.current =
      mode === "single" ? handleSingleSubmit : handleCompareSubmit;
  });

  const handleSubmit = () => {
    if (mode === "single") handleSingleSubmit();
    else handleCompareSubmit();
  };

  // -------------------------------------------------------------------------
  // Keyboard shortcuts
  // -------------------------------------------------------------------------

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't fire when typing in an input/textarea
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "Enter" && !e.shiftKey && canSubmit) {
        handleSubmitRef.current();
      }
      if (e.key === "Escape") {
        dismiss();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [canSubmit, dismiss]);

  // -------------------------------------------------------------------------
  // Mode switch
  // -------------------------------------------------------------------------

  const switchMode = (next: Mode) => {
    setMode(next);
    setStatus("idle");
    setResult(null);
    setErrorMsg(null);
    setCompareColumns(null);
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const showSingleResult = mode === "single" && (status === "done" || status === "error");

  return (
    <div className="space-y-5">
      {/* Audio source */}
      <div>
        <label className="block text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">
          Audio
        </label>
        <AudioInput
          value={audioSource}
          onChange={handleAudioChange}
          onDurationKnown={setAudioDurationSec}
          disabled={isLoading}
        />
      </div>

      {/* Settings row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">
            Sprache
          </label>
          <LanguageSelect value={language} onChange={setLanguage} disabled={isLoading} />
        </div>

        <div>
          {/* Mode toggle + model selector */}
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Modell
            </label>
            <div className="flex gap-0.5 p-0.5 bg-zinc-900 rounded-md">
              {(["single", "compare"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => switchMode(m)}
                  disabled={isLoading}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    mode === m
                      ? "bg-zinc-700 text-zinc-100"
                      : "text-zinc-500 hover:text-zinc-300"
                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  {m === "single" ? "Einzeln" : "Vergleich"}
                </button>
              ))}
            </div>
          </div>

          {mode === "single" ? (
            <ModelSelect value={modelId} onChange={setModelId} disabled={isLoading} />
          ) : (
            <ModelCheckboxGroup
              selected={selectedModels}
              onChange={setSelectedModels}
              disabled={isLoading}
            />
          )}
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-4 h-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            Transkribiere… ({formatElapsed(elapsedMs)})
          </span>
        ) : (
          "Transkribieren"
        )}
      </button>

      {/* Single-mode result */}
      {showSingleResult && (
        <ResultPanel
          status={status as "done" | "error"}
          text={result?.text ?? null}
          durationMs={result?.durationMs}
          audioDurationSec={result?.audioDurationSec ?? audioDurationSec ?? undefined}
          rtf={result?.rtf}
          errorMsg={errorMsg}
          onDismiss={dismiss}
        />
      )}

      {/* Compare result (loading or done) */}
      {mode === "compare" && compareColumns && (
        <ComparePanel
          columns={compareColumns}
          elapsedMs={elapsedMs}
          onDismiss={dismiss}
        />
      )}

      {/* History */}
      {history.length > 0 && (
        <HistoryPanel
          entries={history}
          onClear={() => {
            setHistory([]);
            saveHistory([]);
          }}
        />
      )}
    </div>
  );
}
