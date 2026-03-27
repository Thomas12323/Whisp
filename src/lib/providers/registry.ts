import type { TranscriptionProvider } from "./types";
import { LocalCohereProvider } from "./local-cohere";
import { LocalWhisperProvider } from "./local-whisper";

// To add a new model: implement TranscriptionProvider, import it here,
// and add an instance to this array. Nothing else needs to change.
const providers: TranscriptionProvider[] = [
  new LocalCohereProvider(),
  new LocalWhisperProvider(),
];

const providerMap = new Map<string, TranscriptionProvider>(
  providers.map((p) => [p.id, p])
);

export function getProvider(id: string): TranscriptionProvider {
  const provider = providerMap.get(id);
  if (!provider) throw new Error(`Unknown transcription provider: "${id}"`);
  return provider;
}

export function listProviders(): { id: string; label: string }[] {
  return providers.map((p) => ({ id: p.id, label: p.label }));
}
