# Bhaav (भाव) — Hinglish Emotion Detection

**Hindi-English Code-Mixed Emotion Detection Using Transformer-Based NLP Models**

> "yaar aaj ka din bahut bekaar tha 😩" → **sadness** (high), **anger** (low)
> "kya baat hai bhai, maza aa gaya!!" → **joy** (high)
> "result aane wala hai, dil dhak dhak kar raha hai" → **fear** (medium), **joy?** (abstain — unsure)

Bhaav is two things built together:

1. **A research project** — a harmonised Hinglish emotion benchmark (multi-label + intensity),
   a fresh human-annotated gold test set, a systematic comparison of code-mixed transformers vs.
   classical and zero-shot-LLM baselines, and the first focused **robustness + calibration**
   evaluation for Hinglish emotion models. Target: a workshop/conference paper.
2. **A deployed product** — a fast, mobile-first website and public API that detects emotions in
   Hinglish (Roman, Devanagari or mixed script), explains *which words* drove the prediction, shows
   word-level language tags, analyses whole chats (e.g. a WhatsApp export) as an emotion timeline,
   and offers an on-device **Privacy Mode** where text never leaves the browser.

---

## Why this matters (short version)

- Hinglish is the default register of Indian social media, reviews, support chats and DMs.
- Commercial social-listening tools sell *sentiment* (positive/negative/neutral) for Hinglish;
  fine-grained, explainable **emotion** detection for Hinglish is not available as an open tool.
- Academic Hinglish emotion datasets exist but are small and **mutually incompatible**
  (3, 4, 6, 8 and 16-class label sets; mostly single-label; different sources and eras).
- Fine-tuned encoders still beat zero-shot LLMs on emotion classification, and they are cheap
  enough to run on CPU or even in a browser — which makes a free, private, deployable tool realistic.

Full reasoning: `docs/01_project_definition.md`, `docs/02_market_and_competitor_analysis.md`,
`docs/03_literature_review.md`.

---

## What makes Bhaav different (feature summary)

| # | Feature | Why it's useful |
|---|---------|-----------------|
| 1 | **Multi-label emotions + intensity (0–3)** on Ekman-6 + neutral | Real text mixes feelings; intensity separates "thoda sad" from "bahut dukhi" |
| 2 | **Code-mix lens**: per-word language tags (hi / en / ne / univ) + Code-Mixing Index | Makes the "Hinglish" part visible and debuggable |
| 3 | **Why? highlights** — word-level attribution | Trust + teaching; shows which words drove each emotion |
| 4 | **Spelling-variant robustness** (bahut/bohot/bhot, nahi/nhi/nai) + Roman↔Devanagari | The #1 failure mode of Hinglish models, measured and mitigated |
| 5 | **Calibrated confidence + "unsure" abstention** | Honest output instead of a confident wrong label |
| 6 | **Chat timeline**: paste/upload a WhatsApp export → per-person emotion timeline + emotion-shift markers | Practical, shareable, unique |
| 7 | **Privacy Mode**: distilled model runs in-browser (Transformers.js) | Zero text leaves the device |
| 8 | **Batch CSV + public REST API** with OpenAPI docs | For students, researchers, small brands |
| 9 | **Model-vs-model comparison page** (ours vs. generic multilingual vs. LLM zero-shot) | Research showcase + honest benchmarking |
| 10 | **"Correct me" feedback** (opt-in) → active-learning queue | Grows the dataset ethically over time |

Feature scoring and what was cut: `docs/04_feature_evaluation.md`.

---

## Architecture at a glance

```
 Browser (Next.js on Vercel)
   ├── Server Mode ──HTTPS──▶ FastAPI + ONNX Runtime (int8) on Google Cloud Run (scale-to-zero)
   │                              └── model weights pulled from Hugging Face Hub at build time
   └── Privacy Mode ── Web Worker ── Transformers.js (distilled int8 student, cached)
 Optional: Supabase Postgres (opt-in feedback only)
```

Details and alternatives (HF Spaces, Render, Fly, Railway): `docs/06_architecture_and_web_stack.md`,
deployment steps: `docs/15_deployment_runbook.md`.

---

## Documentation map

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Operating manual for Claude Code — rules, commands, repo layout, definition of done |
| `docs/01_project_definition.md` | Problem, goals, users, scope, success criteria |
| `docs/02_market_and_competitor_analysis.md` | Existing products/models/datasets and our gap |
| `docs/03_literature_review.md` | Academic landscape, datasets, models, findings |
| `docs/04_feature_evaluation.md` | Every candidate feature scored; MVP vs v1 vs later |
| `docs/05_srs.md` | Software Requirements Specification (FR/NFR, acceptance criteria) |
| `docs/06_architecture_and_web_stack.md` | System design, stack choices, trade-offs |
| `docs/07_measurement_methodology.md` | Metrics, statistics, robustness, calibration, latency |
| `docs/08_ml_methodology.md` | Data pipeline, models, training, distillation, export |
| `docs/09_phases_and_roadmap.md` | Phase-by-phase plan with exit criteria (Claude Code follows this) |
| `docs/10_honest_assessment.md` | What's not novel, risks, limits, kill criteria |
| `docs/11_paper_plan.md` | Paper structure, claims, figures, target venues |
| `docs/12_data_plan_and_label_schema.md` | Datasets, licenses, label mapping, splits |
| `docs/13_ui_ux_spec.md` | Pages, components, copy, design system |
| `docs/14_api_contract.md` | REST API spec |
| `docs/15_deployment_runbook.md` | Step-by-step deploy (Cloud Run + Vercel + HF Hub) |
| `docs/16_ethics_privacy_and_risk.md` | Privacy, misuse, wellbeing, bias |
| `docs/17_testing_strategy.md` | Unit/integration/e2e/model tests |
| `docs/18_annotation_guidelines.md` | How to label the gold test set |
| `docs/research_log.md` | Running log of decisions, results, open questions |
| `docs/adr/` | Architecture Decision Records |
| `configs/` | Label schema, dataset registry, training configs |
| `prompts/` | Versioned LLM prompts (baseline + silver labelling) |

---

## Getting started with Claude Code

```bash
unzip bhaav-planning-pack.zip && cd bhaav
git init && git add . && git commit -m "docs: planning pack"
claude            # then type:  /status
```

Claude Code will read `CLAUDE.md`, find Phase 0 in the roadmap, and start building.
You'll be asked for human-only actions (dataset access emails, HF/GCP/Vercel accounts,
annotation sessions) — these are tracked in `docs/research_log.md` → "Human action needed".

## Run it locally (development)

```bash
uv sync                                    # Python 3.11 workspace
pnpm install --dir apps/web                # frontend

uv run python -m bhaav_api.devtools.dummy_model --out dist/dummy
MODEL_DIR=dist/dummy uv run uvicorn bhaav_api.main:app --port 8080
pnpm --dir apps/web dev                    # http://localhost:3000
```

The API currently serves a **random placeholder model**, so the emotions shown are not real
predictions (the page says so). Full command list: `CLAUDE.md` §4.

## Status

**Phase 1 nearly complete (2026-10-02).** Built and tested: the data pipeline (fetch, normalise,
language tagging, harmonise, dedupe, stats), an API skeleton and a web skeleton. The pipeline has
run on three real, openly licensed datasets (`reports/data_stats.md`), and it rebuilds from a
fresh clone with byte-identical output.

What does **not** exist yet:

- **No emotion model has been trained.** The API serves a random placeholder model.
- **No Hinglish emotion training data.** The data in hand is Hindi (BRIGHTER), English
  (GoEmotions) and a trilingual test set (EmoMix-3L). Access requests for the Hinglish emotion
  datasets are pending.
- The only measured model so far is the small word-language tagger: macro-F1 0.8412 (95% CI
  0.8376–0.8449) on the SentiMix test file, against that dataset's own noisy word tags
  (`experiments/lid_charngram_sentimix_v1`).
- CI and the Docker image have not run yet (the work branch is not pushed).

Plain-language progress: `docs/progress_summary.md`. Detailed record: `docs/research_log.md`.

## License (proposed)

Code: MIT. Harmonised dataset release: only where every source license permits redistribution;
otherwise we release **mapping scripts + IDs**, not text. Model weights: same license as the most
restrictive training source. See `docs/12_data_plan_and_label_schema.md`.
