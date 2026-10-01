# 06 — Architecture & Web Stack

Goal: **the cheapest architecture that is genuinely production-grade** — free to run, fast on
mobile, private by default, portable (no lock-in), and simple enough for one developer + Claude Code.

---

## 1. System overview

```
                                   ┌──────────────────────────────────────────────┐
                                   │  Hugging Face Hub (free)                     │
                                   │  • bhaav/teacher-onnx  (server model, int8)  │
                                   │  • bhaav/student-onnx  (browser model, int8) │
                                   │  • bhaav/hinglish-emotion-bench (dataset)    │
                                   └───────────┬───────────────────┬──────────────┘
                                   pulled at   │ docker build       │ fetched + cached by browser
                                               ▼                    ▼
┌──────────────────────┐  HTTPS  ┌──────────────────────────────┐  ┌─────────────────────────────┐
│  Web app (static)     │───────▶│  Inference API               │  │  Web Worker (Privacy Mode)   │
│  Next.js static export│  JSON  │  FastAPI + ONNX Runtime CPU  │  │  Transformers.js + student   │
│  on Vercel (or CF     │◀───────│  Google Cloud Run            │  │  (WASM; WebGPU if present)   │
│  Pages / HF Static)   │        │  min-instances=0, 1 vCPU,    │  └─────────────────────────────┘
│  • text / batch / chat│        │  2 GiB, concurrency 8        │
│  • chat parser (local)│        │  • /v1/analyze  /batch       │   ┌──────────────────────────┐
│  • charts (Recharts)  │        │  • LID + CMI + occlusion     │──▶│ Supabase (optional, v2): │
└──────────────────────┘        │  • rate limit, no text logs  │   │ opt-in feedback table    │
                                 └──────────────────────────────┘   └──────────────────────────┘
```

## 2. Key decisions (summary — full ADRs in `docs/adr/`)

| # | Decision | Chosen | Main alternatives | Why |
|---|---|---|---|---|
| ADR-001 | Serving runtime | **ONNX Runtime (CPU), int8 dynamic quantisation** | PyTorch, TorchScript, TGI | 2–4× faster on CPU, ~4× smaller, no torch in image (~1.5 GB saved) |
| ADR-002 | API host | **Google Cloud Run** (request-based billing, scale-to-zero) | HF Spaces, Render, Fly.io, Railway, AWS Lambda | Real free tier, any container, HTTPS, autoscaling; portable Docker |
| ADR-003 | Frontend | **Next.js (App Router) static export + TypeScript + Tailwind + shadcn/ui** | Vite+React, SvelteKit, Gradio, Streamlit | Professional UX, static = host anywhere free; Gradio/Streamlit look like demos |
| ADR-004 | Privacy Mode | **Transformers.js v3 in a Web Worker**, distilled int8 student | ONNX Runtime Web directly, TF.js | Same ONNX artefacts, tokenizer handled, cache + WebGPU support |
| ADR-005 | Explanations | **Batched occlusion** (server + browser), IG offline | Captum IG in prod, attention weights, LIME/SHAP | No torch at serve time, same method both modes, attention ≠ explanation |
| ADR-006 | LID | **Char n-gram logistic regression** (exported weights) — upgrade to HingBERT-LID only if it wins by > 3 F1 and fits latency | HingBERT-LID always | Tiny + fast in both server and browser |

## 3. Why not Hugging Face Spaces as the primary host? (researched 2026-10-01)

- HF docs now state: **Gradio and Docker Spaces require a paid plan (PRO) to create**; Static Spaces
  are free; free personal accounts can still host up to **2 Gradio Spaces on ZeroGPU**.
- Free CPU Basic hardware is 2 vCPU / 16 GB but **sleeps after ~48 h of inactivity** (cold start on next visit).
- ZeroGPU has daily GPU-time quotas and is Gradio-centric — a poor fit for a custom React UI + REST API.
- **Therefore:** HF Hub hosts *artefacts* (models, dataset), Cloud Run hosts the *API*, Vercel hosts
  the *UI*. If the owner buys HF PRO (~US$9/mo), a Docker Space becomes a valid alternative API host
  with the **same Dockerfile** (documented in `15_deployment_runbook.md` as Plan B).

## 4. Cloud Run sizing & free-tier math

Free tier (request-based billing, Tier-1 regions such as `us-central1`, per billing account per month):
**180,000 vCPU-seconds, 360,000 GiB-seconds, 2 million requests** **[re-verify on cloud.google.com/run/pricing before deploy]**.

| Item | Assumption | Monthly usage at 50k requests |
|---|---|---|
| CPU | 1 vCPU, ~0.15 s billed per request (incl. overhead, 100 ms rounding) | ≈ 7,500 vCPU-s (4% of free) |
| Memory | 2 GiB × 0.15 s | ≈ 15,000 GiB-s (4% of free) |
| Cold starts | ~10 s × 2 GiB × ~300 starts | ≈ 3,000 vCPU-s + 6,000 GiB-s |
| Requests | 50k | 2.5% of free |

→ Comfortably free up to several hundred thousand requests/month. **Region note:** free tier is
tied to Tier-1 pricing regions (e.g. us-central1); India users will see ~250–300 ms extra RTT.
`asia-south1` (Mumbai) is lower latency but **check whether it is Tier-2 pricing and how the free
tier applies** before choosing it. Default: `us-central1` for cost; revisit after launch.

Settings: `--min-instances=0 --max-instances=3 --cpu=1 --memory=2Gi --concurrency=8
--cpu-boost --timeout=30s`. Set a **GCP budget alert at US$1**.

## 5. Model artefacts & size budget

| Artefact | Target | Notes |
|---|---|---|
| Teacher (server) | best encoder from Phase 4, ONNX int8 ≤ 300 MB | XLM-R-family vocab (250k) makes embeddings huge; HingBERT-family is smaller. Size is a tie-breaker in model selection |
| Student (browser) | ≤ 60 MB int8 (cap 100 MB) | Layer-reduced (e.g. 4–6 layers) student of a BERT-vocab teacher, **optional vocab pruning** to tokens seen in Hinglish corpus |
| LID model | ≤ 2 MB | Char n-gram LR weights as JSON / ONNX |
| Tokenizer | `tokenizer.json` | Fast tokenizer; identical server/browser |

Parity checks (FR-38) gate every export.

## 6. Backend (services/api)

**Stack:** Python 3.11 · FastAPI · Uvicorn (1 worker, async) · onnxruntime · `tokenizers` · numpy ·
pydantic v2 · slowapi (rate limit) · structlog (JSON logs) · pytest + httpx.
**No PyTorch, no transformers** in the serving image (keeps image < 700 MB, faster cold start).

```
services/api/
├── Dockerfile               # python:3.11-slim, non-root user, model baked at build (HF_TOKEN optional)
├── pyproject.toml
├── bhaav_api/
│   ├── main.py              # app factory, CORS, security headers, routers
│   ├── config.py            # pydantic-settings: thresholds, tau, limits, origins, MODEL_DIR
│   ├── routers/{analyze.py, batch.py, meta.py, feedback.py}
│   ├── inference/
│   │   ├── session.py       # ORT session (intra_op_num_threads = vCPU), warmup on startup
│   │   ├── pipeline.py      # normalise → tokenize → run → sigmoid → calibrate → threshold → intensity
│   │   ├── explain.py       # batched occlusion → word scores
│   │   ├── lid.py           # char n-gram LID + CMI
│   │   └── normalize.py     # SHARED rules with ml/src/bhaav/data/normalize.py (single source; copied by build script + parity test)
│   ├── schemas.py           # request/response models (mirror 14_api_contract.md)
│   └── logging.py           # redacting logger: never logs text
└── tests/
```

Request flow: validate → normalise → LRU cache lookup (key = SHA-256 of normalised text + model
version; values only in memory) → inference → optional explain → response.

## 7. Frontend (apps/web)

**Stack:** Next.js 15 (App Router, `output: 'export'`) · TypeScript strict · Tailwind CSS v4 ·
shadcn/ui (Radix) · Recharts · TanStack Query · Zod (validate API responses) ·
`@huggingface/transformers` (v3) in a Web Worker · Comlink (worker RPC) · JSZip (chat zip) ·
Papa Parse (CSV) · html-to-image (share card) · Vitest + Testing Library · Playwright · Lighthouse CI.

```
apps/web/
├── app/
│   ├── page.tsx                 # Analyse (hero input + results)
│   ├── chat/page.tsx            # Chat timeline
│   ├── batch/page.tsx           # CSV
│   ├── playground/page.tsx      # Robustness playground
│   ├── compare/page.tsx         # Model comparison (static JSON from experiments)
│   ├── about/page.tsx           # Model card, data, limitations, citation
│   └── api-docs/page.tsx        # How to use the API (links to /docs on API)
├── components/{EmotionBars, CodeMixLens, IntensityDots, UnsureCard, WellbeingCard, ModeToggle, ...}
├── lib/
│   ├── api.ts                   # typed client + zod schemas
│   ├── worker/emotion.worker.ts # Transformers.js pipeline; postprocessing identical to server
│   ├── postprocess.ts           # thresholds, calibration temp, intensity — loaded from model's config.json
│   ├── chat/parser.ts           # WhatsApp Android/iOS parser
│   └── variants.ts              # playground perturbations (same rules as ml robustness suite)
├── public/model-meta.json       # thresholds, tau, temperature, label order, version (generated)
└── messages/en.json             # all UI copy
```

**Single source of truth for post-processing:** `model-meta.json` (generated by the export step)
carries label order, per-label thresholds, temperature, τ, intensity mapping, and model version.
Server and browser both read it → identical outputs (tested).

## 8. Shared logic across Python ↔ TypeScript

Normalisation rules, spelling-variant tables, and perturbation rules are defined **once** as data
(`configs/normalization.yaml`, `configs/variants.yaml`) and consumed by both languages. A parity
test runs 200 fixture strings through both implementations and asserts identical output.

## 9. CI/CD (GitHub Actions)

| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | PR, push | ruff, mypy, pytest (ml + api, with a tiny dummy ONNX model fixture), eslint, vitest, build web, pip-audit, pnpm audit |
| `deploy-api.yml` | tag `api-v*` | build image (pull model from HF Hub by pinned revision) → push to Artifact Registry → `gcloud run deploy` → smoke test `/v1/health` + golden request |
| `deploy-web.yml` | push to `main` (Vercel Git integration does this automatically) | Lighthouse CI on preview URL |
| `e2e.yml` | nightly + pre-release | Playwright against preview (incl. Privacy Mode no-leak test) |

Auth from GitHub to GCP via **Workload Identity Federation** (no JSON keys).

## 10. Security & privacy architecture
- No database in MVP. Text exists only in request memory; LRU cache stores hashes→results only.
- Logging middleware whitelists fields (`request_id, path, status, latency_ms, input_chars, mode, model_version`).
- CSP: `default-src 'self'; connect-src 'self' <api-origin> https://huggingface.co https://cdn-lfs*.huggingface.co ...; worker-src 'self' blob:`.
- Rate limit by IP (in-memory per instance — acceptable at this scale; note limitation).
- Dependency + container scanning in CI; non-root container; read-only filesystem where possible.

## 11. Scalability path (only if needed)
1. Raise `max-instances`; enable `min-instances=1` (costs money, removes cold start).
2. Move rate limiting to Upstash Redis (free tier) if multiple instances cause abuse.
3. Batch-level dynamic batching in the API.
4. Move teacher to a smaller distilled model if CPU becomes the bottleneck.

## 12. Portability matrix (same container)

| Host | Works? | Notes |
|---|---|---|
| Google Cloud Run | ✅ primary | free tier; scale to zero |
| HF Docker Space | ✅ Plan B | needs HF PRO to create; sleeps on free CPU |
| Render / Railway / Fly.io | ✅ | free tiers change often **[verify]**; most sleep or have small RAM |
| Local `docker run` | ✅ | for demos / viva without internet (pair with `pnpm build && npx serve out`) |
