import type {
  TranscriptionProvider,
  TranscriptionRequest,
  TranscriptionResult,
} from "./types";

const INFERENCE_SERVER_URL =
  process.env.INFERENCE_SERVER_URL ?? "http://localhost:8000";

export class LocalWhisperProvider implements TranscriptionProvider {
  readonly id = "whisper-local";
  readonly label = "faster-whisper";

  async transcribe(request: TranscriptionRequest): Promise<TranscriptionResult> {
    const form = new FormData();
    form.append("model", "whisper");
    form.append("language", request.language);
    form.append(
      "file",
      new Blob([request.file as BlobPart], { type: request.mimeType }),
      request.fileName
    );

    let response: Response;
    try {
      response = await fetch(`${INFERENCE_SERVER_URL}/transcribe`, {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(180_000),
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "TimeoutError") {
        throw new Error("Transkription abgebrochen — Zeitüberschreitung nach 3 Minuten.");
      }
      throw new Error(
        "Inference server not reachable. Is `python inference/server.py` running?"
      );
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as { detail?: string };
      throw new Error(body.detail ?? `HTTP ${response.status}`);
    }

    const data = await response.json() as {
      text: string;
      duration_ms?: number;
      audio_duration_sec?: number;
      rtf?: number;
    };
    return {
      text: data.text,
      durationMs: data.duration_ms,
      audioDurationSec: data.audio_duration_sec,
      rtf: data.rtf,
    };
  }
}
