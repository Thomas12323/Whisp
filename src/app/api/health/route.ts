import { NextResponse } from "next/server";

const INFERENCE_SERVER_URL =
  process.env.INFERENCE_SERVER_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${INFERENCE_SERVER_URL}/health`, {
      signal: AbortSignal.timeout(3000),
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json() as {
        model_loaded?: boolean;
        models_loaded?: string[];
        device?: string;
        cpu_percent?: number;
        process_memory_mb?: number;
        system_memory_used_gb?: number;
        system_memory_total_gb?: number;
      };
      return NextResponse.json({
        status: "online",
        modelLoaded: data.model_loaded ?? false,
        modelsLoaded: data.models_loaded ?? [],
        device: data.device ?? "unknown",
        cpuPercent: data.cpu_percent ?? null,
        processMemoryMb: data.process_memory_mb ?? null,
        systemMemoryUsedGb: data.system_memory_used_gb ?? null,
        systemMemoryTotalGb: data.system_memory_total_gb ?? null,
      });
    }
    return NextResponse.json({ status: "offline" });
  } catch {
    return NextResponse.json({ status: "offline" });
  }
}
