"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "online" | "offline";

interface Stats {
  device: string;
  modelsLoaded: string[];
  cpuPercent: number | null;
  processMemoryMb: number | null;
  systemMemoryUsedGb: number | null;
  systemMemoryTotalGb: number | null;
}

const MODEL_LABELS: Record<string, string> = {
  cohere: "Cohere",
  whisper: "Whisper",
};

function CpuBar({ pct }: { pct: number }) {
  const color =
    pct > 85 ? "bg-red-400" : pct > 60 ? "bg-amber-400" : "bg-emerald-400";
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-zinc-500">{pct.toFixed(0)}%</span>
      <span className="inline-block w-10 h-1 rounded-full bg-zinc-700 overflow-hidden align-middle">
        <span
          className={`block h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </span>
    </span>
  );
}

export default function ServerStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [stats, setStats] = useState<Stats | null>(null);

  const check = async () => {
    try {
      const res = await fetch("/api/health", { cache: "no-store" });
      const data = await res.json() as {
        status: string;
        modelsLoaded?: string[];
        device?: string;
        cpuPercent?: number | null;
        processMemoryMb?: number | null;
        systemMemoryUsedGb?: number | null;
        systemMemoryTotalGb?: number | null;
      };
      if (data.status === "online") {
        setStatus("online");
        setStats({
          device: data.device ?? "cpu",
          modelsLoaded: data.modelsLoaded ?? [],
          cpuPercent: data.cpuPercent ?? null,
          processMemoryMb: data.processMemoryMb ?? null,
          systemMemoryUsedGb: data.systemMemoryUsedGb ?? null,
          systemMemoryTotalGb: data.systemMemoryTotalGb ?? null,
        });
      } else {
        setStatus("offline");
        setStats(null);
      }
    } catch {
      setStatus("offline");
      setStats(null);
    }
  };

  useEffect(() => {
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center gap-2.5 text-xs">
      {/* Status dot */}
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
          status === "online"
            ? "bg-emerald-400 shadow-[0_0_6px_1px] shadow-emerald-400/50"
            : status === "offline"
            ? "bg-red-400"
            : "bg-zinc-600 animate-pulse"
        }`}
      />

      {status === "checking" && (
        <span className="text-zinc-500">Verbinde…</span>
      )}

      {status === "offline" && (
        <span className="flex items-center gap-2">
          <span className="text-red-400">Inference Server offline</span>
          <button
            onClick={check}
            className="text-zinc-500 hover:text-zinc-300 underline transition-colors"
          >
            Wiederholen
          </button>
        </span>
      )}

      {status === "online" && stats && (
        <div className="flex items-center gap-2.5 text-zinc-500">
          {/* Device badge */}
          <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase tracking-wide">
            {stats.device}
          </span>

          {/* Loaded models */}
          {stats.modelsLoaded.length > 0 && (
            <span className="text-zinc-600">
              {stats.modelsLoaded.map((m) => MODEL_LABELS[m] ?? m).join(" · ")}
            </span>
          )}

          {/* CPU */}
          {stats.cpuPercent !== null && (
            <span className="flex items-center gap-1">
              <span className="text-zinc-600">CPU</span>
              <CpuBar pct={stats.cpuPercent} />
            </span>
          )}

          {/* RAM */}
          {stats.processMemoryMb !== null && (
            <span className="flex items-center gap-1">
              <span className="text-zinc-600">RAM</span>
              <span>
                {stats.processMemoryMb >= 1024
                  ? `${(stats.processMemoryMb / 1024).toFixed(1)} GB`
                  : `${stats.processMemoryMb} MB`}
              </span>
              {stats.systemMemoryTotalGb !== null && (
                <span className="text-zinc-700">
                  / {stats.systemMemoryTotalGb} GB
                </span>
              )}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
