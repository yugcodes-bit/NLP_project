import { labelInfo } from "@/lib/labels";
import { percent } from "@/lib/text";
import messages from "@/messages/en.json";

export interface CandidateItem {
  label: string;
  probability: number;
}

/** The "unsure" state (FR-05): an honest "I don't know" with the two closest guesses. */
export function UnsureCard({ candidates }: { candidates: CandidateItem[] }) {
  return (
    <section
      aria-label={messages.unsure.title}
      className="border-border bg-surface rounded-xl border p-4"
    >
      <h3 className="font-semibold">{messages.unsure.title}</h3>
      <p className="text-muted mt-1 text-sm">{messages.unsure.body}</p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {candidates.map((candidate) => {
          const info = labelInfo(candidate.label);
          return (
            <li key={candidate.label} className="border-border rounded-full border px-3 py-1">
              <span aria-hidden="true">{info.emoji} </span>
              {info.name} <span className="text-muted">{percent(candidate.probability)}%</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
