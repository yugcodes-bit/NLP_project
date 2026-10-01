# 04 — Feature Evaluation

Every candidate feature scored, so we build what matters and cut what doesn't.
Principle: **practical, not complicated.** A feature earns a place only if it is useful to a real
user *or* produces a research result, and it fits the free-tier, single-developer budget.

## 1. Scoring rubric (1–5 each)

| Criterion | Weight | Meaning |
|---|---|---|
| **U** — User value | 0.30 | Would a real user notice/miss it? |
| **R** — Research value | 0.20 | Does it produce a paper result or figure? |
| **D** — Differentiation | 0.20 | Do competitors lack it? |
| **E** — Ease (inverse effort) | 0.20 | 5 = < 1 day, 1 = > 2 weeks |
| **K** — Low risk | 0.10 | 5 = no infra/ethics/cost risk |

**Score = 0.3U + 0.2R + 0.2D + 0.2E + 0.1K** (max 5.0). ≥ 3.8 → MVP · 3.2–3.79 → v1 · < 3.2 → later/cut.

## 2. Scored features

| # | Feature | U | R | D | E | K | Score | Decision |
|---|---|---|---|---|---|---|---|---|
| F1 | Single-text emotion analysis (multi-label probs) | 5 | 5 | 3 | 5 | 5 | **4.60** | MVP |
| F2 | Intensity 0–3 per emotion | 4 | 4 | 4 | 4 | 5 | **4.10** | MVP |
| F3 | Calibrated confidence + "unsure" abstention | 4 | 5 | 5 | 4 | 5 | **4.50** | MVP |
| F4 | Word attribution highlights ("Why?") | 5 | 4 | 4 | 3 | 4 | **4.10** | MVP (occlusion over ONNX; IG offline) |
| F5 | Word-level language tags + Code-Mixing Index | 4 | 4 | 5 | 4 | 5 | **4.30** | MVP (HingBERT-LID or char-n-gram LID) |
| F6 | Spelling/script normalisation in pipeline | 3 | 5 | 4 | 4 | 5 | **4.00** | MVP (backend, invisible) |
| F7 | Example gallery (curated Hinglish samples, one click) | 4 | 1 | 2 | 5 | 5 | **3.30** | v1 (cheap, great for demos) |
| F8 | Chat timeline (WhatsApp `.txt` export → per-person emotion over time + shift markers) | 5 | 3 | 5 | 3 | 3 | **4.00** | MVP-stretch → shipped in v1 if MVP runs late (client-side parsing; consent notice) |
| F9 | Batch CSV upload → table + summary chart + download | 4 | 2 | 3 | 4 | 4 | **3.40** | v1 |
| F10 | Public REST API + OpenAPI docs + rate limit | 4 | 3 | 3 | 4 | 4 | **3.60** | v1 (comes almost free with FastAPI) |
| F11 | Privacy Mode: in-browser distilled model (Transformers.js) | 4 | 4 | 5 | 2 | 4 | **3.80** | v1 (needs distillation from Phase 5) |
| F12 | Model comparison page (ours vs generic vs LLM; precomputed) | 3 | 4 | 4 | 4 | 5 | **3.80** | v1 (static from experiment results) |
| F13 | Opt-in "Correct me" feedback → Supabase table | 3 | 3 | 3 | 3 | 3 | **3.00** | Later (privacy + moderation overhead) — build only after launch |
| F14 | Robustness playground (toggle spelling variants / script, see prediction change) | 3 | 5 | 5 | 4 | 5 | **4.20** | v1 (showcases RQ3 visually) |
| F15 | Shareable result card (PNG, no raw text by default) | 4 | 1 | 3 | 4 | 4 | **3.20** | v1 |
| F16 | Emotion-aware reply suggestions via LLM | 3 | 1 | 2 | 3 | 2 | 2.30 | **Cut** (third-party LLM, privacy, scope creep) |
| F17 | Live Twitter/X / YouTube comment monitoring | 4 | 2 | 2 | 1 | 1 | 2.30 | **Cut** (ToS, cost, scraping) |
| F18 | Sarcasm detector as separate model | 3 | 4 | 3 | 1 | 4 | 2.90 | Later (we only report sarcasm slice) |
| F19 | Speech input (voice note → ASR → emotion) | 4 | 2 | 4 | 1 | 2 | 2.80 | Later |
| F20 | Other code-mixed languages (Tanglish, Benglish) | 3 | 4 | 4 | 1 | 4 | 3.10 | Later (architecture must allow) |
| F21 | User accounts + saved history | 2 | 1 | 1 | 2 | 2 | 1.60 | **Cut** |
| F22 | Browser extension (analyse selected text) | 3 | 1 | 3 | 3 | 3 | 2.60 | Later |
| F23 | Dark mode + bilingual UI (English / Hinglish copy) | 4 | 1 | 2 | 5 | 5 | 3.30 | v1 (cheap polish) |
| F24 | Wellbeing nudge (gentle helpline note on strong sadness/fear + risk keywords) | 4 | 1 | 3 | 4 | 3 | 3.10 | **MVP (required for responsibility)** — overrides score |
| F25 | Embeddable widget `<script>` for other sites | 2 | 1 | 3 | 3 | 3 | 2.30 | Later |

## 3. Release buckets

### MVP (first public deploy, end of Phase 6)
F1, F2, F3, F4, F5, F6, F24 + basic API (F10 minimal) + About/Model-card page.

### v1 (end of Phase 7)
F7, F8 (if not already in MVP), F9, F10 (full), F11, F12, F14, F15, F23.

### Later / research extensions
F13, F18, F19, F20, F22, F25.

### Cut
F16, F17, F21.

## 4. The three "signature" features (lead the demo with these)

1. **Code-mix lens** (F4 + F5): the input sentence re-rendered with each word tinted by language and
   underlined by emotion contribution. Nobody else shows this.
2. **Chat timeline** (F8): drop a WhatsApp export → line chart of joy/sadness/anger per person over
   time, with ⚡ markers at emotion shifts. Viral, practical, and inspired by EDiReF.
3. **Robustness playground** (F14): one click turns "bahut khush hu" into "bohot khush hun" /
   "बहुत खुश हूँ" / mixed script and shows predictions stay stable — visual proof of RQ3.

## 5. Feature details & acceptance hints

**F3 Abstention**: threshold τ chosen on validation to hit ≥ 90% precision on answered items while
keeping coverage ≥ 80% (tune). UI shows "Bhaav isn't sure 🤔" with the top-2 candidates.

**F4 Attribution**: production uses **batched leave-one-word-out occlusion** over the ONNX model
(n+1 forward passes in one batch; no PyTorch in the serving image; identical method in the browser).
Integrated Gradients (Captum) is used **offline** in the paper to sanity-check that occlusion and IG
agree (rank correlation). Aggregate sub-word scores to words. Show only the top emotion by default.

**F5 LID**: tags {hi, en, univ (emoji/number/punct/name), ne (named entity), other}. CMI computed
per Gambäck & Das. Use HingBERT-LID if latency allows; else a char-n-gram LR LID trained on
L3Cube-HingLID (tiny, fast). Decide by benchmark in Phase 4.

**F8 Chat timeline**: parse WhatsApp Android + iOS export formats client-side (regex, handle
12h/24h, dd/mm vs mm/dd, multi-line messages, "<Media omitted>", system messages). Max 5,000
messages per upload; sample if more. Show consent banner: "Only analyse chats you're part of; others'
messages are personal." Default mode for chats = Privacy Mode if available.

**F24 Wellbeing**: if sadness or fear intensity ≥ 2 **and** a small curated risk-keyword list matches
(Hinglish + Hindi + English), show a non-alarmist card with India's Tele-MANAS helpline
(**14416 / 1-800-891-4416 [verify current numbers before launch]**). Never claim diagnosis.
Never log the text.
