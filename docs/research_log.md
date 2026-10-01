# Research Log

Append-only. Newest entry at the **bottom** of "Entries". Never edit or delete past entries — add a
correction entry instead. Format: `### YYYY-MM-DD — <title>` then What / Why / Result / Next.

---

## Human action needed (keep this list current; tick when done)
- [ ] Create GitHub repo and push this planning pack
- [ ] Verify dataset availability + licenses (see `configs/datasets.yaml` → `to_verify`); send access emails Claude drafts
- [ ] Decide gold-set sourcing mix (donated / elicited / API comments) — `12` §5; check institutional ethics process
- [ ] Recruit 2–3 annotators (Hindi + English fluent); schedule pilot (Week 2)
- [ ] Create accounts: Hugging Face (org `bhaav`), Google Cloud (billing + US$1 budget alert), Vercel
- [ ] Verify Tele-MANAS helpline numbers for the wellbeing card
- [ ] Pick target venue + note deadline (`11` §4)

## Open questions
1. Which emotion datasets are actually obtainable with research licenses? (blocks Phase 1 exit)
2. Is `hatred` in older datasets closer to anger or disgust? → inspect 100 examples, decide, log.
3. Cloud Run region: `us-central1` (free-tier pricing) vs `asia-south1` (latency) — measure after launch.
4. Should intensity be predicted for sources without intensity via pseudo-labels? (Default: no, masked.)
5. Teacher choice may trade 1–2 F1 for 3× smaller size (HingBERT-family vs XLM-R-family) — define tie-break rule before seeing results: *choose the smaller model if within 1.0 macro-F1 (overlapping CIs).*

## Entries

### 2026-10-01 — Planning pack created
**What:** Landscape research (datasets, encoders, products, hosting) and full planning documents.
**Why:** Define a practical, deployable, publishable scope before writing code.
**Findings:**
- Hinglish emotion work exists since 2018; datasets are small and use incompatible label sets
  (3/4/6/8/16 classes); most results are single-seed accuracy. → contribution = harmonisation, gold set,
  rigorous comparison, robustness, calibration, deployment.
- L3Cube HingBERT/HingRoBERTa(-Mixed) pretrained on 52.93M real Hinglish sentences (CC-BY-4.0) — prime candidates.
- SemEval-2024 Task 10 (code-mixed ERC, best F1 0.70) and SemEval-2025 Task 11 (multi-label + intensity, includes Hindi) give public data + schema.
- Only 3 "hinglish emotion" models on HF Hub, none documented/benchmarked → product gap is real.
- HF now requires PRO to create Gradio/Docker Spaces → chose Cloud Run (API) + Vercel (web) + HF Hub (artefacts).
- Fine-tuned encoders still beat zero-shot LLMs on emotion classification (Bucher & Martini 2024) → LLM = baseline only.
**Decisions:** ADR-001…006 accepted. Label schema = Ekman-6 + neutral, multi-label, intensity 0–3.
**Next:** Phase 1 — scaffold repo, dataset verification, data pipeline, dummy model, API/web skeletons.
