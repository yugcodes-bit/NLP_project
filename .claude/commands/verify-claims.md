---
description: Audit every number/claim in README, website copy and paper against experiments/
---
1. Grep `README.md`, `apps/web` copy/JSON, and `paper/` for numbers and comparative claims ("better", "first", "state-of-the-art", "%").
2. For each number, find the source `experiments/*/metrics.json` (and git SHA). Flag anything untraceable.
3. Check each claim against `docs/10_honest_assessment.md` §1, §7 (no "first", CIs present, same split).
4. Output a table: claim · location · source file · status (OK / untraceable / overclaim) · fix.
