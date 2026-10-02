# CLAUDE.md — Operating Manual for Claude Code

> You are building **Bhaav (भाव)** — a deployable web app + research project for
> **Hindi-English Code-Mixed (Hinglish) Emotion Detection using Transformer-based NLP models.**
> This file is your contract. Read it fully at the start of every session.

---

## 1. Read order (mandatory before writing any code)

1. `README.md` — one-page overview
2. `docs/01_project_definition.md` — what we are building and why
3. `docs/10_honest_assessment.md` — what is NOT novel, risks, things you must not overclaim
4. `docs/09_phases_and_roadmap.md` — **find the current phase**, then work only on that phase
5. The doc(s) the current phase points to (SRS, architecture, ML methodology, etc.)
6. `docs/research_log.md` — latest decisions and open questions (append to it, never rewrite history)

If a doc contradicts another doc: the **higher-numbered ADR in `docs/adr/` wins**, then `05_srs.md`,
then everything else. If still unclear, write the question into `docs/research_log.md` under
"Open questions" and pick the more conservative option.

---

## 2. Project in one paragraph

Indians write emotions in Hinglish ("yaar aaj ka din bahut bekaar tha 😩", "kya baat hai bhai, maza aa gaya").
Generic emotion models (English GoEmotions models, multilingual sentiment APIs) handle this poorly:
Romanised Hindi has no fixed spelling, scripts mix (Roman + Devanagari), and most existing Hinglish
emotion datasets are small, use incompatible label sets, and are single-label. Bhaav (1) harmonises
existing Hinglish emotion datasets into one **multi-label + intensity** schema, (2) builds a small
**fresh human-annotated gold test set**, (3) fine-tunes and compares code-mixed transformers
(HingRoBERTa, HingBERT, MuRIL, XLM-R, IndicBERT) against classical and zero-shot-LLM baselines,
(4) measures **robustness to transliteration/script variation** and **calibration**, and (5) ships
the best model as a fast, privacy-respecting website + API with code-mix-aware explanations.

---

## 3. Non-negotiable rules

### Engineering
- **Monorepo** layout exactly as in §6. Do not invent new top-level folders without an ADR.
- Python **3.11**, managed with **uv** (`uv sync`, `uv run`). Node **20 LTS**, **pnpm**.
- Type everything: Python with type hints + `mypy --strict` on `services/` and `ml/src/`;
  TypeScript `strict: true`.
- Lint/format: `ruff` + `ruff format` (Python), `eslint` + `prettier` (TS). CI fails on lint errors.
- Every new module gets tests. Target ≥ 80% line coverage on `services/api` and `ml/src/bhaav/data`.
- **Never commit**: datasets, model weights, `.env`, API keys, notebooks with outputs > 1 MB.
  Data lives in `data/` (git-ignored) and is reproducible from `configs/datasets.yaml` + scripts.
- Secrets only via environment variables. Provide `.env.example`.
- Small, reviewable commits. Conventional commit messages (`feat:`, `fix:`, `docs:`, `exp:` for experiments).

### Research integrity (read `docs/10_honest_assessment.md`)
- **Never claim "first"** Hinglish emotion work — it is not (Vijay et al. 2018, Wadhawan & Aggarwal 2021,
  Ghosh et al. 2023, SemEval-2024 Task 10, etc.).
- **Never report a number you did not produce in this repo.** Every metric in the paper/README/website
  must trace to a file in `experiments/<run_id>/metrics.json`.
- Primary metric is **macro-F1** (not accuracy). Always report mean ± std over **5 seeds** and a
  bootstrap 95% CI. See `docs/07_measurement_methodology.md`.
- **The gold test set is sacred.** Never train, tune thresholds, or select checkpoints on it.
  Use the validation split. Touch the gold test set only in the final evaluation phase, and log
  each time you do in `docs/research_log.md`.
- Deduplicate across splits (exact + near-duplicate) **before** any training run.
- Respect dataset licenses. If a license is unclear, the dataset is `status: blocked` in
  `configs/datasets.yaml` until the human confirms.

### Product
- **Privacy by default**: the API does not store input text. Logs contain only lengths, latencies,
  and model version — never raw text. Feedback storage is **opt-in** per submission.
- The site must show a clear **"Not a medical or psychological diagnostic tool"** notice and the
  wellbeing message described in `docs/16_ethics_privacy_and_risk.md`.
- Mobile-first. Must work on a ₹10k Android phone on 4G (see NFRs in `docs/05_srs.md`).
- Bilingual UI copy (English + Hinglish). No Hindi-only UI.

---

## 4. Commands (create these as you build; keep this list accurate)

```bash
# setup
uv sync                                   # python deps (root workspace)
pnpm install --dir apps/web               # frontend deps

# data
uv run python -m bhaav.data.fetch --list         # registry status table
uv run python -m bhaav.data.fetch --all --strict # download allowed datasets → data/raw (checksums pinned)
uv run python -m bhaav.data.lid_experiment       # train + evaluate the word-level LID → data/interim/lid, experiments/
uv run python -m bhaav.data.harmonize            # map to unified schema → data/processed
uv run python -m bhaav.data.dedupe               # removes duplicates in place + reports/dedupe_report.md
uv run python -m bhaav.data.stats                # dataset card stats → reports/data_stats.md

# shared code (run after editing normalize.py, lid.py or configs/*.yaml)
uv run python -m bhaav.sync_shared               # regenerate the copies in services/api and apps/web
uv run python -m bhaav.sync_shared --check       # fail if a copy is stale

# training / eval  (NOT BUILT YET — Phases 3–4)
uv run python -m bhaav.train --config configs/train/hingroberta_mixed.yaml --seed 13
uv run python -m bhaav.evaluate --run experiments/<run_id> --split val
uv run python -m bhaav.robustness --run experiments/<run_id>
uv run python -m bhaav.export_onnx --run experiments/<run_id> --quantize int8

# services (the API works from any directory; port 8080 matches Docker and .env.example)
uv run python -m bhaav_api.devtools.dummy_model --out dist/dummy   # random dev model, once
MODEL_DIR=dist/dummy uv run uvicorn bhaav_api.main:app --reload --port 8080
#   PowerShell:  $env:MODEL_DIR = "dist/dummy"; uv run uvicorn bhaav_api.main:app --reload --port 8080
pnpm --dir apps/web dev                                    # http://localhost:3000
#   port 3000 busy?  pnpm --dir apps/web exec next dev --port 3100  and add it to ALLOWED_ORIGINS

# quality
uv run ruff check . && uv run ruff format --check . && uv run mypy services/api ml/src
uv run pytest -q                                           # add --cov for coverage
pnpm --dir apps/web lint && pnpm --dir apps/web test && pnpm --dir apps/web build
```

---

## 5. Definition of Done (per task)

A task is done only when **all** are true:
1. Code + tests written, `pytest`/`pnpm test` green locally.
2. Lint + type-check clean.
3. Relevant doc updated (API change → `docs/14_api_contract.md`; new metric → `07`; etc.).
4. A one-paragraph entry appended to `docs/research_log.md` (what, why, result, next).
5. If it is an experiment: `experiments/<run_id>/` contains `config.yaml`, `metrics.json`,
   `predictions_val.jsonl`, `env.txt` (pip freeze + git SHA + GPU), and a short `NOTES.md`.

---

## 6. Target repository layout

```
bhaav/
├── CLAUDE.md                  ← you are here
├── README.md
├── pyproject.toml             ← uv workspace root
├── .env.example
├── .github/workflows/         ← ci.yml, deploy-api.yml, deploy-web.yml
├── .claude/commands/          ← custom slash commands for this project
├── configs/
│   ├── label_schema.yaml      ← THE label taxonomy (single source of truth)
│   ├── datasets.yaml          ← dataset registry + license status + label mappings
│   └── train/*.yaml           ← one config per model/experiment family
├── data/                      ← git-ignored: raw/, interim/, processed/, gold/
├── docs/                      ← planning + research docs (this pack)
│   └── adr/                   ← architecture decision records
├── ml/
│   ├── src/bhaav/
│   │   ├── data/              ← fetch, harmonize, normalize, transliterate, dedupe, augment
│   │   ├── models/            ← heads (multi-label, intensity), losses
│   │   ├── train.py  evaluate.py  robustness.py  calibrate.py  distill.py  export_onnx.py
│   │   └── baselines/         ← majority, tfidf_lr, fasttext, llm_zeroshot
│   ├── notebooks/             ← exploration only; never the source of truth
│   └── tests/
├── experiments/               ← git-tracked metrics/configs only (weights → HF Hub)
├── services/
│   └── api/                   ← FastAPI + ONNX Runtime inference service (Dockerfile here)
├── apps/
│   └── web/                   ← Next.js frontend (+ in-browser Transformers.js worker)
├── paper/                     ← LaTeX (ACL template), figures/, tables/ (generated)
├── prompts/                   ← LLM baseline + silver-labelling prompts (versioned)
└── reports/                   ← generated: data_stats.md, eval tables, error analysis
```

---

## 7. How to work (session protocol)

1. Run `/status` (see `.claude/commands/status.md`) — it tells you the phase and next unchecked task.
2. Plan the task in ≤ 10 bullet points; if it touches > 5 files or changes an interface, write a
   short ADR draft first in `docs/adr/`.
3. Implement → test → update docs → log.
4. When a phase's exit criteria (in `docs/09_phases_and_roadmap.md`) are met, tick them and
   **stop and summarise for the human** before starting the next phase.
5. When blocked by something only the human can do (dataset access request, API key, cloud account,
   annotation work, license confirmation), list it under **"Human action needed"** in
   `docs/research_log.md` and continue with any unblocked task.

## 8. Things you must NOT do
- Do not scrape Twitter/X, Instagram, or WhatsApp without explicit human instruction and ToS check.
- Do not upload any user text to third-party LLM APIs from the production site.
- Do not use LLM-generated labels as gold labels. LLM output = **silver** data only, always flagged.
- Do not add auth, payments, user accounts, or a database beyond the opt-in feedback table in v1.
- Do not chase SOTA with giant models — the deployed model must run on CPU under the latency budget.
- Do not delete or rewrite earlier entries in `docs/research_log.md`.
