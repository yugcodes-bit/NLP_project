# ADR-001 … ADR-006: Initial architecture decisions

- **Status:** Accepted · **Date:** 2026-10-01 · **Deciders:** project owner + planning assistant
- Split into separate files if any decision is revisited.

---

## ADR-001 — Serve with ONNX Runtime (CPU) + int8 dynamic quantisation
**Context:** Free CPU hosting, latency target p95 ≤ 300 ms, small image for fast cold starts.
**Options:** PyTorch eager · TorchScript · ONNX Runtime · Hugging Face TGI/TEI.
**Decision:** ONNX Runtime CPU with dynamic int8 quantisation; tokenisation with `tokenizers`.
**Consequences:** + 2–4× CPU speed-up typical, ~4× smaller weights, no torch in image. − Export/parity
step needed; some quantisation accuracy loss (gate: ≤ 1 macro-F1 point).
**Validation:** FR-38 parity test; NFR-01 latency benchmark.

## ADR-002 — Host the API on Google Cloud Run (request-based, scale-to-zero)
**Context:** Need HTTPS container hosting at ₹0 for low traffic. HF now requires PRO to create
Docker/Gradio Spaces; free CPU Spaces sleep after ~48 h idle.
**Options:** Cloud Run · HF Docker Space (PRO) · Render/Railway/Fly free tiers · AWS Lambda container.
**Decision:** Cloud Run, `us-central1`, min-instances 0, max 3, 1 vCPU / 2 GiB, budget alert US$1.
**Consequences:** + Generous free tier (180k vCPU-s, 360k GiB-s, 2M req/month at time of writing), autoscale,
portable Docker. − Cold starts (~5–15 s); requires billing account; extra RTT from India.
**Validation:** cost report after 1 month; p95 latency from India; cold-start UX feedback.

## ADR-003 — Frontend: Next.js static export + TypeScript + Tailwind + shadcn/ui
**Context:** Need polished, mobile-first UX; client-side features (chat parsing, worker inference); free hosting.
**Options:** Gradio/Streamlit · Vite + React · SvelteKit · Next.js.
**Decision:** Next.js App Router with `output: 'export'`, deployed to Vercel (portable to any static host).
**Consequences:** + Professional UI, huge ecosystem, Claude Code fluent in it, host anywhere.
− No server-side features (OG image generation, API routes) — acceptable.
**Validation:** Lighthouse ≥ targets; bundle budget.

## ADR-004 — Privacy Mode via Transformers.js (v3) in a Web Worker
**Context:** Users may analyse private chats; on-device inference removes trust issues.
**Options:** Transformers.js · ONNX Runtime Web directly · TensorFlow.js · WebLLM.
**Decision:** Transformers.js `text-classification`-style pipeline with custom post-processing from
`model-meta.json`; WASM default, WebGPU opportunistic; distilled int8 student.
**Consequences:** + Reuses ONNX artefacts and tokenizer; caching built in. − Download size; slower on old phones.
**Validation:** NFR-03; e2e no-leak test; student F1 ≥ 95% of teacher (target).

## ADR-005 — Explanations by batched occlusion (production), IG offline
**Context:** Need word-level "why" in both server and browser, without torch at serve time.
**Options:** Attention weights · Integrated Gradients (Captum) · LIME/SHAP · occlusion.
**Decision:** Leave-one-word-out occlusion, batched in one forward pass (n+1 rows); IG used offline
to validate agreement in the paper.
**Consequences:** + Simple, model-agnostic, identical across modes. − Cost grows with word count
(cap at 40 words; beyond → explain top-40 by heuristic). Attention-based "explanations" avoided (known unfaithfulness).
**Validation:** deletion test (07 §2.8); latency with explain p95 ≤ 1.2 s.

## ADR-006 — Word-level LID: char n-gram logistic regression first
**Context:** Need fast per-word language tags + CMI in server and browser.
**Options:** HingBERT-LID (transformer) · char n-gram LR · dictionary lookup.
**Decision:** Char 1–5-gram LR trained on L3Cube-HingLID (+ SentiMix LID), exported as compact weights.
Upgrade to HingBERT-LID only if it beats LR by > 3 F1 and fits latency budget.
**Consequences:** + < 2 MB, < 5 ms. − Lower accuracy on ambiguous words ("main", "to").
**Validation:** LID F1 on held-out HingLID test reported in Phase 1.
