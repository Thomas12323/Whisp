// Client-safe provider metadata — no server-only imports.
// Import this in client components instead of registry.ts.
export const PROVIDERS: { id: string; label: string }[] = [
  { id: "cohere-local", label: "Cohere Transcribe" },
  { id: "whisper-local", label: "faster-whisper" },
];
