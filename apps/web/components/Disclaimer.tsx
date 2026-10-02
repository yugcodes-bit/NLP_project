import messages from "@/messages/en.json";

/** Shown on every page: Bhaav is not a medical or psychological tool (CLAUDE.md §3, docs/16). */
export function Disclaimer() {
  return (
    <footer className="border-border text-muted mt-10 border-t pt-4 text-sm">
      <p>{messages.footer.disclaimer}</p>
      <p className="mt-1">{messages.footer.privacy}</p>
    </footer>
  );
}
