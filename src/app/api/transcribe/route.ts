import { NextRequest, NextResponse } from "next/server";
import { getProvider } from "@/lib/providers/registry";
import { ACCEPTED_MIME_TYPES, MAX_FILE_SIZE_BYTES } from "@/lib/config";

export async function POST(req: NextRequest) {
  let formData: FormData;
  try {
    formData = await req.formData();
  } catch {
    return NextResponse.json({ error: "Invalid form data." }, { status: 400 });
  }

  const file = formData.get("file") as File | null;
  const language = formData.get("language") as string | null;
  const modelId = formData.get("modelId") as string | null;

  if (!file || !language || !modelId) {
    return NextResponse.json(
      { error: "Missing required fields: file, language, modelId." },
      { status: 400 }
    );
  }

  // Strip codec suffix (e.g. "audio/webm;codecs=opus" → "audio/webm")
  const mimeBase = file.type.split(";")[0].trim();
  if (!(ACCEPTED_MIME_TYPES as readonly string[]).includes(mimeBase)) {
    return NextResponse.json(
      { error: `Unsupported file type: "${mimeBase}". Please upload an audio file.` },
      { status: 415 }
    );
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return NextResponse.json(
      { error: `File too large. Maximum size is 500 MB.` },
      { status: 413 }
    );
  }

  let provider;
  try {
    provider = getProvider(modelId);
  } catch {
    return NextResponse.json({ error: `Unknown model: "${modelId}".` }, { status: 400 });
  }

  try {
    const result = await provider.transcribe({
      file,
      fileName: file.name || "audio.webm",
      mimeType: mimeBase,
      language,
    });
    return NextResponse.json({
      text: result.text,
      durationMs: result.durationMs,
      audioDurationSec: (result as { audioDurationSec?: number }).audioDurationSec,
      rtf: (result as { rtf?: number }).rtf,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Transcription failed.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
