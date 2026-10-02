# ADR-008: Workspace layout, shared Python code, and pipeline state

- **Status:** Proposed (drafted with the Phase 1 scaffold; human to accept)
- **Date:** 2026-10-01
- **Deciders:** project owner + Claude Code
- **Numbering:** ADR-007 is reserved by `09_phases_and_roadmap.md` for the teacher selection.

## Context
The planning docs fix the folder layout (`CLAUDE.md` §6) and the big choices (ADR-001…006) but
leave four practical questions open that the scaffold has to answer:

1. How the two Python packages (`ml`, `services/api`) are installed and tested together.
2. How normalisation / LID code is shared between them when the API image must stay free of the ML
   dependencies and its Docker build context is `services/api` only (`15` §2–3).
3. Where the random-weight development model is built.
4. How `dedupe` can rewrite `data/processed/` without becoming destructive on a second run.

## Options considered
1. **Shared code**
   - A. Third package (`packages/shared`) — clean, but a new top-level folder and a second wheel
     to install inside the API image.
   - B. API imports `bhaav` — drags scikit-learn/datasketch (later torch) into the serving image.
   - C. **Copy + freshness check** — what `06` §6 already describes.
2. **Dedupe output**
   - A. Harmonise into `data/interim/`, dedupe into `data/processed/` — pure, but contradicts FR-33.
   - B. **Rewrite `data/processed/` in place, guarded by a summary file with content hashes.**
3. **Dummy model location**: in `ml` (needs the ML package inside the API Docker build) or
   **in the API package** as a dev tool.

## Decision
- **uv workspace** at the repo root with members `ml` (package `bhaav`, `src/` layout) and
  `services/api` (package `bhaav_api`). The root is a virtual project holding the `dev`
  dependency group; one `uv sync` installs both packages editable. Heavy training deps (torch,
  transformers) will be an optional extra of `bhaav` added in Phase 4.
- **Shared code is copied, never imported across packages.** The source of truth is
  `ml/src/bhaav/data/{normalize,lid}.py` plus `configs/{normalization,label_schema}.yaml`.
  `python -m bhaav.sync_shared` writes generated copies to
  `services/api/bhaav_api/inference/{normalize,lid}.py`,
  `services/api/bhaav_api/resources/*.yaml` and `apps/web/lib/generated/*.json`.
  `--check` (pre-commit + a pytest) fails when a copy is stale. The two modules therefore depend
  only on stdlib, `regex`, `numpy`, `pydantic`, `pyyaml`, and on each other by relative import.
- **Normalisation fixtures are the cross-language contract**: `ml/tests/fixtures/normalize_cases.json`
  is consumed by the Python tests now and by the TypeScript implementation when it is written.
- **Dummy model lives in the API package** (`bhaav_api.devtools.dummy_model`, extra `dummy`),
  so `docker build --build-arg MODEL_SOURCE=dummy` works with the `services/api` context alone.
  It also writes a tiny dummy LID model. Both are flagged `"dummy": true` in their metadata.
- **`dedupe` rewrites `data/processed/*.jsonl` in place** and records
  `data/processed/dedupe_summary.json` with the SHA-256 of every output file. A second run that
  finds matching hashes is a no-op, so the report is not overwritten with zeros. Removed records
  go to `data/interim/dedupe_removed.jsonl` (git-ignored) for audit. Re-running `harmonize`
  resets the state.

## Consequences
- + Serving image stays small; shared behaviour is byte-identical by construction.
- + All three pipeline commands keep the paths the SRS names (FR-33, FR-34).
- − Generated files are committed; forgetting to re-sync fails CI rather than silently drifting.
- − `normalize.py` / `lid.py` cannot import the rest of `bhaav`.
- Reversal: promote the two modules to a real shared package (option 1A) with a follow-up ADR.

## Validation
`ml/tests/test_sync_shared.py` (freshness), `ml/tests/test_pipeline_e2e.py` (harmonize → dedupe →
stats on a synthetic source, dedupe idempotence), Docker build with `MODEL_SOURCE=dummy` in CI.

Status 2026-10-02: the two test files pass locally. The Docker build has **not** been validated
yet — Docker is not installed on the development machine and CI has not run.
