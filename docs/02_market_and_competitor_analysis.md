# 02 — Market & Competitor Analysis

Research snapshot: **2026-10-01**. Prices/limits change — Claude Code must re-verify anything marked
**[verify]** before relying on it in the product or paper.

---

## 1. The landscape in one picture

```
                    Fine-grained EMOTION
                           ▲
     Academic Hinglish     │     (empty quadrant — open, explainable,
     emotion papers        │      deployable Hinglish EMOTION tool)
     (no usable product)   │            ← Bhaav targets this
                           │
  CLOSED ◀─────────────────┼─────────────────▶ OPEN / FREE
                           │
     Social-listening      │     Hugging Face hobby models,
     suites (Hinglish      │     generic multilingual sentiment,
     SENTIMENT, paid)      │     GoEmotions (English only)
                           ▼
                    Coarse SENTIMENT (pos/neg/neu)
```

## 2. Categories of existing solutions

### 2.1 Commercial social-listening / CX platforms
- Global suites (e.g. Sprinklr, Brandwatch, Brand24, BrandMentions) advertise multilingual sentiment;
  an India-focused vendor (Awshar) markets Hinglish/dialect handling and a "95%+ accuracy" claim
  in a 2026 comparison article. These tools sell **sentiment** and mention analytics to businesses,
  are **closed**, **paid / quote-based**, and do not expose per-word explanations or a research benchmark.
- **Gap for us**: no free, transparent, emotion-level (not just sentiment) Hinglish tool; no
  evidence of calibration or robustness reporting.
- We do **not** compete on social monitoring scale. We compete on *openness, emotion granularity,
  explainability, privacy, and research rigour*.

### 2.2 General cloud NLP APIs
- Major cloud NLP APIs offer sentiment (and some offer emotion) primarily for standard languages.
  Romanised Hindi is generally not a first-class supported "language" for these APIs **[verify for
  the specific APIs you cite in the paper]**.
- **Gap**: transliterated, mixed-script input handling.

### 2.3 LLM chat assistants (Gemini, GPT, Claude, Llama, etc.)
- Can label emotion zero-shot in Hinglish quite well for clear cases.
- Weaknesses for this use case: cost/rate limits at scale, latency, privacy (text goes to a third
  party), non-determinism, weaker calibration, and research consistently showing fine-tuned encoders
  outperform zero-shot LLMs on emotion classification (Bucher & Martini 2024; other 2025 studies).
- Free tiers exist (e.g. Gemini Flash-class models via AI Studio at roughly 10–15 RPM and
  hundreds–~1,500 requests/day as of 2026; Pro models removed from the free tier in April 2026) **[verify]**.
- **Our use**: LLMs are a **baseline** in the paper and an **offline silver-label helper** —
  never in the production inference path.

### 2.4 Open models on Hugging Face
- A Hub search for "hinglish emotion" (2026-10-01) returns only **3** models
  (e.g. `Gek524/hinglish-emotion-xlmr`, `amaan00z/hinglish-emotions-xlmr-10cls`) with minimal
  downloads, no model cards with benchmark results, no robustness/calibration info.
- Strong *building blocks* exist: L3Cube **HingBERT / HingRoBERTa / HingRoBERTa-Mixed / HingBERT-LID**
  (CC-BY-4.0), Google **MuRIL**, AI4Bharat **IndicBERT-v2**, **XLM-R**.
- English emotion models (GoEmotions-trained RoBERTa/DistilRoBERTa) are popular but fail on Romanised Hindi.
- **Gap**: no well-documented, benchmarked, deployable Hinglish emotion model.

### 2.5 Academic systems
- Many papers (2018–2026) report Hinglish emotion results (see `03_literature_review.md`), usually
  on a single dataset, single seed, accuracy-focused, rarely with code/model release, never deployed.
- Shared tasks: **SemEval-2020 Task 9** (Hinglish *sentiment*), **SemEval-2024 Task 10 / EDiReF**
  (emotion recognition in Hindi-English code-mixed *conversations*, best ERC F1 ≈ 0.70),
  **SemEval-2025 Task 11** (multi-label emotion + intensity incl. Hindi in Devanagari).
- **Gap**: unified benchmark across datasets, robustness and calibration analysis, deployment.

## 3. Competitive feature matrix

| Capability | Social-listening suites | Cloud NLP APIs | LLM zero-shot | HF hobby models | Academic papers | **Bhaav** |
|---|---|---|---|---|---|---|
| Hinglish (Roman) support | ✅ (claimed) | ⚠️ | ✅ | ⚠️ | ✅ | ✅ |
| Mixed script (Roman + Devanagari) | ? | ⚠️ | ✅ | ❌ | ⚠️ | ✅ |
| Fine-grained emotions | ⚠️ some | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| Multi-label + intensity | ❌ | ❌ | ⚠️ (prompted) | ❌ | rare | ✅ |
| Explanations (word-level) | ❌ | ❌ | ⚠️ free-text | ❌ | rare | ✅ |
| Word-level language tags / CMI | ❌ | ❌ | ❌ | ❌ | separate task | ✅ |
| Calibrated confidence / abstain | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Chat/conversation timeline | ❌ | ❌ | manual | ❌ | ERC research | ✅ |
| On-device privacy mode | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Free & open | ❌ | ❌ (pay-per-use) | ⚠️ rate-limited | ✅ | ⚠️ | ✅ |
| Published benchmark/robustness | ❌ | ❌ | ❌ | ❌ | partial | ✅ |

## 4. Positioning statement

> **For** students, researchers, developers and small Indian brands **who** need to understand
> emotions in real Hinglish text, **Bhaav is** a free, open, explainable emotion detector
> **that** handles spelling and script variation, tells you when it's unsure, and can run entirely
> on your device. **Unlike** social-listening suites and LLM chatbots, it is transparent,
> benchmarked, calibrated, and private by default.

## 5. Differentiators we can actually defend

1. **Harmonised benchmark + independent gold test set** — measurable, publishable.
2. **Robustness suite** for transliteration/script perturbations — reusable by others.
3. **Calibration + abstention** — rare in this literature.
4. **Code-mix lens UI** (LID + CMI + attribution) — clear, visual, unique for a public tool.
5. **Privacy Mode** (in-browser) — strong story for chat analysis.
6. **Chat timeline with emotion-shift markers** — practical and shareable, inspired by EDiReF.

## 6. Differentiators we should NOT claim
- "Most accurate Hinglish model" — not provable across all datasets.
- "Understands sarcasm" — we only measure that slice.
- "Detects mental health conditions" — explicitly not.
- "First Hinglish emotion detector" — false.

## 7. Go-to-market (lightweight, free)
- Launch post on LinkedIn/X + r/developersIndia + Hugging Face community; demo GIF of chat timeline.
- HF model cards + Space/linking for discoverability; Papers-with-Code style results table in README.
- Offer the API free with rate limits; "cite us" BibTeX on the site.
- College NLP clubs/hackathons: share the benchmark as a challenge.

## Sources
- Social listening 2026 comparison (BrandMentions blog): https://brandmentions.com/blog/best-multilingual-social-listening-tools/
- Hinglish brand-monitoring sentiment paper (arXiv 2601.05091): https://arxiv.org/abs/2601.05091
- HF model search "hinglish emotion": https://huggingface.co/models?search=hinglish%20emotion
- L3Cube code-mixed resources: https://github.com/l3cube-pune/code-mixed-nlp
- Fine-tuned vs zero-shot LLMs (Bucher & Martini 2024): https://arxiv.org/abs/2406.08660
- Gemini free-tier changes 2026 (CloudZero): https://www.cloudzero.com/blog/gemini-pricing/
- SemEval-2024 Task 10: https://aclanthology.org/2024.semeval-1.270/
- SemEval-2025 Task 11 / BRIGHTER: https://brighter-dataset.github.io
