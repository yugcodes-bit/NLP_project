import { AnalysePanel } from "@/components/AnalysePanel";
import { Disclaimer } from "@/components/Disclaimer";
import messages from "@/messages/en.json";

export default function AnalysePage() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-4 py-6 sm:py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">
          {messages.brand.name}{" "}
          <span lang="hi" className="text-accent">
            {messages.brand.devanagari}
          </span>
        </h1>
        <p className="text-muted mt-1">{messages.brand.tagline}</p>
      </header>
      <main className="flex-1">
        <AnalysePanel />
      </main>
      <Disclaimer />
    </div>
  );
}
