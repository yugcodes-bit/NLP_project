# 05 — Software Requirements Specification (SRS)

Format loosely follows IEEE 830 / ISO 29148. IDs are stable — reference them in commits, tests and PRs.
Priority: **M** = Must (MVP), **S** = Should (v1), **C** = Could (later).

---

## 1. Introduction

### 1.1 Purpose
Specify the behaviour of Bhaav's web app, inference API, and ML pipeline so that Claude Code can
implement and test each requirement independently.

### 1.2 Scope
Web app (Next.js), inference API (FastAPI + ONNX Runtime), in-browser inference worker
(Transformers.js), ML pipeline (data → training → evaluation → export). See `01_project_definition.md`.

### 1.3 Definitions
See glossary in `01_project_definition.md`. "Text" = a UTF-8 string ≤ 1,000 characters unless stated.

## 2. Overall description

### 2.1 Product perspective
```
[User browser] ──► [Web app: Next.js on Vercel]
                      ├─► [Inference API: FastAPI on Cloud Run] ──► [ONNX model files (baked in image)]
                      └─► [Web Worker: Transformers.js student model from HF Hub CDN]
[Optional] [Supabase Postgres: opt-in feedback]          [HF Hub: model + dataset repos]
```

### 2.2 User classes
Casual user · Researcher/student · Developer (API) · Small business analyst (batch) · Maintainer (admin via env/CLI only).

### 2.3 Operating environment
- Browsers: last 2 versions of Chrome, Edge, Firefox, Safari; Chrome Android; Safari iOS.
- Privacy Mode requires WebAssembly (all above); WebGPU used opportunistically.
- Server: Linux container, 1–2 vCPU, ≤ 2 GiB RAM.

### 2.4 Constraints
Free tiers; CPU inference; no storage of user text; open-source licenses compatible with MIT code.

## 3. Functional requirements

### 3.1 Text analysis
| ID | Requirement | Pri |
|---|---|---|
| FR-01 | The system shall accept text in Roman, Devanagari, or mixed script, 1–1,000 chars. Longer input → validation error with message. | M |
| FR-02 | The system shall return a probability in [0,1] for each of the 7 labels (anger, disgust, fear, joy, sadness, surprise, neutral). | M |
| FR-03 | The system shall return the set of **active** emotions using per-label thresholds tuned on validation. If none active → `neutral`. | M |
| FR-04 | The system shall return an intensity (0–3) for each active emotion. | M |
| FR-05 | The system shall return `abstained: true` when max calibrated confidence < τ (configurable), plus top-2 candidates. | M |
| FR-06 | The system shall return word-level language tags (`hi`, `en`, `univ`, `ne`, `other`) and the utterance CMI (0–100). | M |
| FR-07 | On request (`explain=true`), the system shall return word-level attribution scores for the top emotion (and optionally all active emotions). | M |
| FR-08 | The system shall normalise input (Unicode NFC, whitespace, repeated characters "sooooo"→"soo", emoji preserved) before inference, and return the normalised text. | M |
| FR-09 | The response shall include `model_version`, `latency_ms`, and `mode` (`server` / `browser`). | M |
| FR-10 | The UI shall display results as emotion bars with intensity, an "unsure" state, a code-mix lens, and an explanation toggle. | M |

### 3.2 Batch & chat
| ID | Requirement | Pri |
|---|---|---|
| FR-11 | The API shall accept a batch of ≤ 64 texts per request and return results in order. | S |
| FR-12 | The UI shall accept a CSV (≤ 5 MB, ≤ 1,000 rows), let the user choose the text column, process in batches, show a table + distribution chart, and export results as CSV. | S |
| FR-13 | The UI shall parse WhatsApp chat exports (Android + iOS formats, `.txt`, or `.zip` containing it) **client-side**. | S |
| FR-14 | The chat view shall show per-participant emotion timelines (rolling window), overall distribution per participant, and markers where the dominant emotion of a participant changes between consecutive windows ("emotion shift"). | S |
| FR-15 | Chat analysis shall default to Privacy Mode when available, and show a consent notice before processing. | S |
| FR-16 | Participant names shall be pseudonymised in any shareable output ("Person A/B"). | S |

### 3.3 Privacy Mode
| ID | Requirement | Pri |
|---|---|---|
| FR-17 | The UI shall offer a toggle to run inference fully in-browser using the distilled student model in a Web Worker. | S |
| FR-18 | On first use, the UI shall show the download size and progress; the model shall be cached (Cache API) for subsequent visits. | S |
| FR-19 | In Privacy Mode, the app shall make **no** network request containing user text (verifiable in e2e test via request interception). | S |
| FR-20 | Privacy Mode shall provide FR-02..FR-05 and FR-08; LID and attribution may use lighter methods (occlusion). | S |

### 3.4 Showcase & information
| ID | Requirement | Pri |
|---|---|---|
| FR-21 | Example gallery: ≥ 20 curated, non-offensive Hinglish examples covering all emotions and scripts. | S |
| FR-22 | Robustness playground: given input, generate variants (spelling variants, Devanagari, mixed script, emoji removed) and show predictions side-by-side with a stability score. | S |
| FR-23 | Model comparison page: static table/charts from `experiments/` results (macro-F1 with CIs, ECE, latency, size) for all compared models. | S |
| FR-24 | About / Model card page: data sources, label schema, metrics, limitations, intended use, citation (BibTeX). | M |
| FR-25 | Wellbeing card per `16_ethics_privacy_and_risk.md` when trigger conditions are met. | M |
| FR-26 | Shareable result card (PNG) that excludes the raw input text unless the user opts in. | C |

### 3.5 API platform
| ID | Requirement | Pri |
|---|---|---|
| FR-27 | `GET /v1/health` returns status + model_version; `GET /v1/labels` returns label schema. | M |
| FR-28 | OpenAPI docs at `/docs`; contract in `14_api_contract.md`. | S |
| FR-29 | Rate limiting per IP: 60 req/min single, 10 req/min batch (configurable). 429 with `Retry-After`. | M |
| FR-30 | CORS restricted to the web app origin(s) + `localhost`; public API usage allowed without key in v1 under rate limits. | M |
| FR-31 | Opt-in feedback endpoint storing (text, predicted, corrected labels, consent flag, timestamp) — only if the user ticks consent. | C |

### 3.6 ML pipeline
| ID | Requirement | Pri |
|---|---|---|
| FR-32 | Pipeline shall fetch each dataset listed as `status: allowed` in `configs/datasets.yaml`, verify checksums, and record versions. | M |
| FR-33 | Pipeline shall map source labels to the unified schema via `configs/datasets.yaml` mappings and emit `data/processed/*.jsonl` with provenance fields. | M |
| FR-34 | Pipeline shall perform exact + near-duplicate (MinHash, Jaccard ≥ 0.8 on char 5-grams) removal across splits and against the gold test set. | M |
| FR-35 | Training shall be fully config-driven and seed-controlled; each run writes the experiment folder described in `CLAUDE.md` §5. | M |
| FR-36 | Evaluation shall compute all metrics in `07_measurement_methodology.md` and write `metrics.json` + markdown table. | M |
| FR-37 | Robustness script shall generate the perturbation suite deterministically (fixed seed) and report per-perturbation deltas. | M |
| FR-38 | Export script shall produce ONNX (fp32 + int8) and validate parity (max abs prob diff ≤ 0.02 fp32; macro-F1 drop ≤ 1.0 pt int8 on val). | M |
| FR-39 | Distillation script shall train a student from teacher soft labels and report teacher/student gap. | S |

## 4. Non-functional requirements

| ID | Category | Requirement | Pri |
|---|---|---|---|
| NFR-01 | Latency (server) | Single text, warm: p50 ≤ 120 ms, p95 ≤ 300 ms on 1 vCPU (excluding network). With `explain=true`: p95 ≤ 1,200 ms. | M |
| NFR-02 | Cold start | Cloud Run cold start ≤ 15 s; UI shows "waking up the model…" state after 1.5 s. | M |
| NFR-03 | Browser model | Student download ≤ 60 MB (int8) target, hard cap 100 MB; inference ≤ 250 ms/text on a mid-range laptop (WASM). | S |
| NFR-04 | Web performance | Lighthouse mobile ≥ 90 Performance, ≥ 95 Accessibility, ≥ 90 Best Practices; initial JS ≤ 200 KB gz (model excluded). | M |
| NFR-05 | Accessibility | WCAG 2.1 AA; colour is never the only signal (bars have labels + numbers); keyboard navigable. | M |
| NFR-06 | Privacy | No user text in logs, analytics, error trackers or storage (except FR-31 with consent). Verified by test (log capture). | M |
| NFR-07 | Security | Input validation (pydantic), payload size limit 64 KB, rate limiting, dependency scanning (pip-audit, pnpm audit) in CI, security headers (CSP, HSTS, X-Content-Type-Options). | M |
| NFR-08 | Availability | Best-effort ≥ 99% monthly on free tier; graceful error UI; Privacy Mode as fallback when API is down. | S |
| NFR-09 | Cost | ₹0/month at ≤ 50k requests/month. Alert (GCP budget) at US$1. | M |
| NFR-10 | Reproducibility | Any reported metric reproducible from git SHA + config + seed within ±0.5 macro-F1 points on same hardware class. | M |
| NFR-11 | Maintainability | Type-checked, linted, ≥ 80% coverage on API + data modules; ADRs for major decisions. | M |
| NFR-12 | Portability | API runs anywhere Docker runs; no Cloud-Run-specific code paths. | M |
| NFR-13 | i18n | UI copy in English with Hinglish microcopy; all strings in a single messages file. | S |
| NFR-14 | Observability | Structured JSON logs (request id, latency, input length, mode, status); `/metrics` optional. | S |

## 5. Data requirements
- Unified record (`data/processed/*.jsonl`):
```json
{"id":"wadhawan21-000123","text":"...","text_norm":"...","script":"roman|devanagari|mixed",
 "labels":{"anger":0,"disgust":0,"fear":0,"joy":2,"sadness":0,"surprise":0,"neutral":0},
 "label_source":"gold|mapped|silver","source":"wadhawan21","source_label":"happy",
 "split":"train|val|test_in_domain","cmi":34.5,"lang_tags":null,"license":"...","notes":""}
```
- Intensity: 0 = absent; for sources without intensity, active label → intensity **null** (unknown)
  and the intensity head is trained only on records with intensity (masked loss).
- As implemented (`ml/src/bhaav/data/records.py`, 2026-10-02): `neutral` is always 0 or 1 (it has no
  intensity); `split` may also be `ood_eval`; and each record additionally carries `source_id`
  (the source's own id, for ID-only releases), `mapping_version`, `normalization_version`,
  `has_caps_shouting` (analysis only) and `flags` (e.g. `mapped_from_love`, `neutral_with_emotion`).
  `lang_tags` is one tag per token of `text_norm`, or `null` when no trained LID model was available.

## 6. External interfaces
- REST API (see `14_api_contract.md`), Hugging Face Hub (model download at build), Supabase (optional).

## 7. Acceptance test summary (traceability)

| Requirement(s) | Test |
|---|---|
| FR-01..FR-09 | `services/api/tests/test_analyze.py` (unit + golden-response snapshot) |
| FR-11 | `test_batch.py` |
| FR-13/14 | `apps/web/src/lib/chat/__tests__/parser.test.ts` with fixtures for Android/iOS, 12h/24h |
| FR-19 | Playwright e2e `privacy-mode.spec.ts` asserting no request body contains input text |
| FR-29 | `test_rate_limit.py` |
| FR-34 | `ml/tests/test_dedupe.py` with planted near-duplicates |
| FR-38 | `ml/tests/test_export_parity.py` |
| NFR-01 | `scripts/bench_latency.py` in CI (warn) + pre-release (block) |
| NFR-04/05 | Lighthouse CI on preview deploys |
| NFR-06 | `test_no_text_in_logs.py` (caplog asserts) |
