---
description: Run or register an ML experiment following the measurement protocol
argument-hint: <config path> [seeds]
---
Experiment request: $ARGUMENTS

1. Validate the config against `configs/label_schema.yaml` and `docs/08_ml_methodology.md` (same budget as other encoders).
2. Confirm the gold set is NOT used (only train/val). Abort if any code path reads `data/gold/` outside Phase 8.
3. Produce the command(s) to run locally or the Kaggle/Colab runner cell (no logic in notebooks).
4. After results arrive, ensure `experiments/<run_id>/` has config.yaml, metrics.json, predictions_val.jsonl, env.txt, NOTES.md.
5. Regenerate tables with `bhaav.report`, then log the result in `docs/research_log.md` with mean ± std over seeds.
