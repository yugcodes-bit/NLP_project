# 09 — Phases & Roadmap

**Claude Code: this is your task list.** Work only on the current phase (first phase with unchecked
exit criteria). Tick boxes as you complete them (`- [x]`). At the end of each phase, stop and give
the human a summary + list of "Human action needed" items.

Total: ~15 weeks for one student + Claude Code. Web work runs **in parallel** with ML from Phase 1
using a dummy model, so the product is never blocked on research.

```
Week:        1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
P1 Scaffold ███████
P2 Gold set     ████████████████                     (human annotation, parallel)
P3 Baselines        ████
P4 Encoders             ████████████
P5 Improve                          ████████
P6 MVP web  ░░░░░░░░░░░░░░░░████████████              (░ = with dummy model)
P7 v1 feat                                  ████████████
P8 Final+paper                                          ████████████
P9 Launch                                                           ████
```

---

## Phase 0 — Planning ✅ (this pack)
- [x] Research landscape, datasets, models, deployment options
- [x] Write planning docs, ADRs, configs
- [ ] **Human:** create GitHub repo, push this pack, open Claude Code, run `/status`

---

## Phase 1 — Repo scaffold & data pipeline (Weeks 1–2)
**Goal:** reproducible data foundation + skeleton apps.

Tasks (status notes dated 2026-10-02; a ticked box means the code is written, tested and committed)
- [x] Monorepo per `CLAUDE.md` §6; uv workspace; pnpm app; pre-commit (ruff, prettier); `.env.example`
  — hooks are configured but not installed; run `uv run pre-commit install` once
- [ ] CI `ci.yml` (lint, type, test) green on an empty test suite
  — workflow written; **never run**, because the branch is not pushed. Same commands pass locally
- [x] `configs/label_schema.yaml` loader + validation (pydantic)
- [x] Dataset registry loader; `bhaav.data.fetch` for every `status: allowed` dataset (with checksum + version capture)
  — 4 datasets allowed and fetched; every file pinned to a version and a SHA-256
- [ ] **Human:** confirm/obtain access + licenses for each dataset in `configs/datasets.yaml` (emails to authors where needed — Claude drafts them in `docs/research_log.md`)
  — 4 approved (choice delegated to Claude on 2026-10-02). **Still open:** send the 5 access e-mails
  for the Hinglish emotion datasets (drafts in the research log)
- [x] `normalize.py` + `configs/normalization.yaml` + tests (≥ 40 fixture cases incl. Devanagari, emoji, elongation)
  — 65 cases + property tests
- [x] Script detection + char n-gram LID + CMI (`lid.py`), LID evaluated on ~~HingLID~~ **SentiMix** test; record F1
  — HingLID is CC BY-NC-SA, so the tagger is trained and tested on SentiMix (ADR-009).
  `experiments/lid_charngram_sentimix_v1`: test macro-F1 0.8412 (95% CI 0.8376–0.8449), against noisy tags
- [x] `harmonize.py` → `data/processed/*.jsonl` with provenance — 3 real datasets, 60,110 records
- [x] `dedupe.py` (exact + MinHash) + report — 1,943 removed, 58,167 kept (`reports/dedupe_report.md`)
- [x] `stats.py` → `reports/data_stats.md` (counts per label/source/split, script mix, CMI histogram, length)
- [x] Dummy ONNX model (random weights, correct I/O) for API/web development
- [ ] FastAPI skeleton with `/v1/health`, `/v1/labels`, `/v1/analyze` (dummy), tests; Dockerfile builds
  — everything done and run locally **except** the Docker build (Docker is not installed here; CI will build it)
- [x] Next.js skeleton (static export) with Analyse page calling the dummy API

**Exit criteria** (status 2026-10-02)
- [x] `uv run python -m bhaav.data.harmonize && ... dedupe && ... stats` runs end-to-end from a clean clone
  — verified: fresh `git clone` → `uv sync` → `fetch --all --strict` → `lid_experiment` → `harmonize`
  → `dedupe` → `stats` in about 3 minutes; reports and metrics byte-identical to the committed ones
- [x] ≥ 3 datasets harmonised (or fallback plan triggered — see `12` §7)
  — 3 harmonised (BRIGHTER Hindi, GoEmotions, EmoMix-3L). **Caveat: none is a Hinglish emotion
  training set and none has intensity labels.** Unless the access e-mails succeed, the fallback
  plan of `12` §7 is what Phase 4 will actually run on
- [x] `reports/data_stats.md` committed; label mapping decisions logged
- [ ] CI green; Docker image builds; web app renders dummy results locally
  — web app renders (checked in Chrome). **CI has never run and the Docker image has never been
  built**: both need the branch pushed to GitHub. This is the only open exit criterion

---

## Phase 2 — Gold test set (Weeks 2–5, mostly human, parallel)
**Goal:** 1,000–1,500 independently sourced, triple/double-annotated Hinglish items.

- [ ] Finalise `18_annotation_guidelines.md` with 30 worked examples (Claude drafts; human reviews)
- [ ] Source pool: collect ~3,000 candidate texts from **sources not used in training** (see `12` §5), PII-scrubbed
- [ ] Set up annotation tool (Label Studio local or a simple Streamlit/Google Sheet form) with the exact schema
- [ ] Pilot: 100 items × 3 annotators → compute α → revise guidelines → re-pilot if α < 0.5
- [ ] Main annotation: 1,000–1,500 items, ≥ 2 annotators each, third for disagreements
- [ ] Compute IAA (07 §4); write `data/gold/DATASHEET.md`
- [ ] Freeze gold: hash recorded in `research_log.md`; file read-only; access logged
- [ ] Tag slices: script, CMI bucket, emoji, sarcasm flag, length

**Exit criteria**
- [ ] Gold frozen with ≥ 1,000 items, IAA reported, all 7 labels with ≥ 40 positives (else targeted collection)

---

## Phase 3 — Baselines (Week 3)
- [ ] Evaluation module implementing **all** metrics in `07` (unit-tested on toy predictions with hand-computed answers)
- [ ] Bootstrap + paired significance utilities (tested)
- [ ] B0, B1 (TF-IDF LR), B2 (fastText), B3 (English GoEmotions model)
- [ ] B5 LLM zero-shot harness (prompt v1, JSON parsing, retries, caching responses to disk) — run on `val` only for now
- [ ] `bhaav.report` generates Markdown tables from `experiments/`

**Exit criteria**
- [ ] Baseline val results table in `reports/`; B1 established as the "classical bar"

---

## Phase 4 — Encoder benchmark (Weeks 4–6)
- [ ] Training script (HF `Trainer` or plain PyTorch loop) with multi-label + masked intensity heads, config-driven
- [ ] Kaggle/Colab runner notebook that clones repo, runs a config, uploads `experiments/<run>` back (no logic in notebook)
- [ ] LR sweep (1 seed) for E1–E8
- [ ] 5 seeds at best LR for E1–E8
- [ ] Calibration (T, thresholds, τ) per model on val
- [ ] Efficiency benchmark (size, CPU latency) per model via ONNX export
- [ ] Select **teacher** (best val macro-F1; tie-break by size/latency) — ADR-007 written

**Exit criteria**
- [ ] Val results for 8 encoders × 5 seeds with mean ± std; teacher chosen with written rationale
- [ ] Real ONNX int8 teacher replaces dummy model in the API (behind `MODEL_DIR`)

---

## Phase 5 — Improve & understand (Weeks 7–8)
- [ ] Robustness suite (07 §5) + 100-item meaning-preservation check
- [ ] Ablations A1–A9 per `08` §3.6 (prioritise A8, A7, A2, A5)
- [ ] Silver data generation (AUG-4) with filters + human audit of 200
- [ ] Final teacher config = best ablation combo; re-run 5 seeds
- [ ] Error analysis on **val** (gold stays untouched): 200 errors tagged
- [ ] LID model decision (ADR-006 confirm/upgrade)

**Exit criteria**
- [ ] Final teacher frozen; robustness + ablation tables on val; error taxonomy documented

---

## Phase 6 — MVP website & API, first deploy (Weeks 6–9)
- [ ] API: full `/v1/analyze` per `14_api_contract.md` (normalise → infer → calibrate → threshold → intensity → LID/CMI → occlusion)
- [ ] Redacting logger + `test_no_text_in_logs`; rate limiting; security headers; payload limits
- [ ] Latency benchmark meets NFR-01 (else: smaller teacher / shorter max_len / threads tuning)
- [ ] Web: Analyse page (EmotionBars, IntensityDots, UnsureCard, CodeMixLens, explanation toggle), About/Model card, WellbeingCard, disclaimer, dark mode
- [ ] Copy reviewed for tone (English + Hinglish microcopy)
- [ ] **Human:** create GCP project + billing (free tier) + budget alert; Vercel account; HF org/repo; GitHub secrets / Workload Identity
- [ ] Deploy API (Cloud Run) + web (Vercel) per `15_deployment_runbook.md`
- [ ] Lighthouse CI ≥ targets; Playwright smoke e2e on production URL

**Exit criteria**
- [ ] **Public URL live** with MVP features; README updated with links; smoke tests green

---

## Phase 7 — v1 features (Weeks 9–11)
- [ ] Distil student (S1 → S2 if size > 60 MB), export int8, parity, publish to HF Hub
- [ ] Privacy Mode (Web Worker + Transformers.js, progress UI, cache, no-leak e2e test)
- [ ] Chat timeline: WhatsApp parser (Android/iOS fixtures), consent notice, pseudonymisation, timeline + shift markers, privacy-mode default
- [ ] Batch CSV page (column picker, batching, progress, chart, CSV export)
- [ ] Robustness playground (shared variant rules, side-by-side, stability score)
- [ ] Model comparison page (static JSON from `experiments/` via `bhaav.report --web`)
- [ ] Example gallery (≥ 20 curated examples, reviewed for offensiveness)
- [ ] API: `/v1/analyze/batch`, OpenAPI polish, API docs page with curl/Python/JS snippets
- [ ] Share card (no raw text by default)

**Exit criteria**
- [ ] All v1 features live; e2e suite green; Lighthouse still ≥ targets

---

## Phase 8 — Final evaluation & paper (Weeks 12–14)
- [ ] **Unseal gold** (log it): evaluate all baselines + encoders + final teacher + student + LLM B5/B6
- [ ] Significance tests (paired bootstrap + Holm), CIs, slices, robustness on gold, calibration on gold
- [ ] Generate all paper tables/figures from `experiments/` (`paper/tables`, `paper/figures`)
- [ ] Write paper per `11_paper_plan.md`; limitations + ethics sections
- [ ] Release: HF dataset (mapping scripts + IDs; text only where licensed), model cards, gold datasheet
- [ ] Update website comparison page with **gold** numbers

**Exit criteria**
- [ ] Full paper draft compiled; every number traceable to `experiments/`; human review done

---

## Phase 9 — Launch & hardening (Week 15)
- [ ] Security pass (deps audit, headers, CSP, rate limit abuse test), privacy review vs `16`
- [ ] Load test (k6/locust) at 10 rps for 5 min on Cloud Run; confirm cost stays ₹0
- [ ] Final README with demo GIF, citation, links; CHANGELOG; tag `v1.0.0`
- [ ] Launch posts (drafts in `docs/launch/`), submit paper
- [ ] Post-launch backlog grooming → `docs/research_log.md` "Next"

**Exit criteria**
- [ ] v1.0.0 tagged; site stable for 7 days; paper submitted (or venue chosen with deadline)

---

## Milestones summary

| Milestone | Week | Evidence |
|---|---|---|
| M1 Data pipeline works | 2 | data_stats.md |
| M2 Gold frozen | 5 | DATASHEET.md + hash |
| M3 Teacher chosen | 6 | ADR-007 + val table |
| M4 **MVP live** | 9 | public URL |
| M5 v1 live (privacy mode + chat) | 11 | public URL |
| M6 Paper draft | 14 | paper/main.pdf |
| M7 v1.0.0 launch | 15 | tag + posts |

## If behind schedule — cut in this order
1. Share card (F15) → 2. Batch CSV (F9) → 3. B4 translate-then-classify → 4. Ablations A1/A3/A9 →
5. Student vocab pruning (ship S1 even if 80–100 MB) → 6. Playground (keep robustness *results* in paper).
**Never cut:** gold set, multi-seed evaluation, privacy guarantees, wellbeing card, honest limitations.
