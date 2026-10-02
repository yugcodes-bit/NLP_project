import messages from "@/messages/en.json";

const LEVELS = [1, 2, 3] as const;

/** Intensity 1–3 as filled dots plus the word, so it reads without colour or shape. */
export function IntensityDots({ level }: { level: 1 | 2 | 3 }) {
  const word = messages.intensity[String(level) as "1" | "2" | "3"];
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <span aria-hidden="true" className="tracking-tight">
        {LEVELS.map((step) => (step <= level ? "●" : "○")).join("")}
      </span>
      <span className="text-muted text-sm">{word}</span>
    </span>
  );
}
