import TranscribeForm from "@/components/TranscribeForm";
import ServerStatus from "@/components/ServerStatus";

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800/60 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <span className="text-base font-semibold tracking-tight">Whisp</span>
          <ServerStatus />
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-7">
          <h1 className="text-xl font-semibold text-zinc-100">Transkription</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Lade eine Audiodatei hoch oder nimm direkt auf
          </p>
        </div>
        <TranscribeForm />
      </main>
    </div>
  );
}
