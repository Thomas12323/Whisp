export interface TranscriptionRequest {
  file: File | Blob;
  fileName: string;
  mimeType: string;
  language: string;
}

export interface TranscriptionResult {
  text: string;
  durationMs?: number;
  audioDurationSec?: number;
  rtf?: number;
}

export interface TranscriptionProvider {
  readonly id: string;
  readonly label: string;
  transcribe(request: TranscriptionRequest): Promise<TranscriptionResult>;
}
