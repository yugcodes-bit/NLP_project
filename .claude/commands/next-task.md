---
description: Pick and complete the next roadmap task end-to-end
---
1. Run the `/status` procedure to find the next unticked task in the current phase.
2. Re-read the doc sections relevant to it (SRS IDs, API contract, ML methodology, etc.).
3. Plan in ≤ 10 bullets. If it changes an interface or architecture, draft an ADR in `docs/adr/` first.
4. Implement with tests. Run lint, type-check and tests.
5. Update docs touched by the change, tick the task in `docs/09_phases_and_roadmap.md`,
   and append an entry to `docs/research_log.md` (What / Why / Result / Next).
6. Commit with a conventional message. Summarise what changed and what's next.
