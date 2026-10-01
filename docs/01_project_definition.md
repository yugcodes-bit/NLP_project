# 01 — Project Definition

**Title:** Hindi-English Code-Mixed Emotion Detection Using Transformer-Based NLP Models
**Working name:** Bhaav (भाव — "feeling, emotion")
**Type:** Applied NLP research + deployable web product
**Status:** Planning complete (2026-10-01)

---

## 1. Problem statement

Hundreds of millions of Indian users express emotion online in **Hinglish**: Hindi and English
mixed within a sentence, usually typed in Roman script, sometimes in Devanagari, sometimes both.

```
"bhai exam ka result dekh ke dimaag kharab ho gaya"     → anger / sadness
"mummy ne finally haan bol diya 😭❤️"                     → joy (tears ≠ sadness)
"kal interview hai, bohot tension ho rahi hai"           → fear
"wah, kya service hai, 3 ghante se wait kar raha hu 🙂"   → anger (sarcasm)
```

Why this is hard:

1. **No standard spelling** in Romanised Hindi: *bahut / bohot / bhot / bahot*, *nahi / nhi / nai / nahin*.
2. **Script mixing**: Roman + Devanagari in one message; English words written in Devanagari.
3. **Cross-lingual ambiguity**: "main" (Hindi "I" vs English "main"), "to", "hi", "is".
4. **Emotion is cultural and contextual**: 😭 often means overwhelming joy; "mast" = great;
   sarcasm is frequent; emojis carry a lot of signal.
5. **Data scarcity and fragmentation**: existing Hinglish emotion datasets are small (≈1.5k–20k),
   use incompatible label sets, and are mostly single-label.
6. **Generic tools don't fit**: English emotion models misread Romanised Hindi; commercial Indian
   tools mostly sell 3-way sentiment, not emotion, and are closed.

## 2. Goal

Build, evaluate, and **deploy** a transformer-based system that detects **multiple emotions and
their intensity** in Hinglish text, is **robust to spelling/script variation**, gives **calibrated
confidence and explanations**, and is **free and private to use**.

## 3. Objectives (measurable)

| ID | Objective | Measure / target |
|----|-----------|------------------|
| O1 | Unified multi-label + intensity Hinglish emotion corpus from existing public datasets | ≥ 3 sources harmonised, mapping documented, dedup report |
| O2 | Fresh gold test set, independent of all training sources | 1,000–1,500 items, ≥ 2 annotators each, Krippendorff's α reported |
| O3 | Systematic model comparison | ≥ 6 encoders + 3 classical + 1 LLM zero-shot baseline, 5 seeds each |
| O4 | Beat strongest generic baseline | Statistically significant macro-F1 gain (paired bootstrap p < 0.05) on gold test |
| O5 | Robustness | Robustness drop under transliteration/script perturbation ≤ 50% of the best baseline's drop |
| O6 | Calibration | ECE ≤ 0.05 after temperature scaling |
| O7 | Deployable | Server p95 latency ≤ 300 ms (single text, warm, CPU); in-browser student ≤ 60 MB download |
| O8 | Product | Live public URL, API docs, chat timeline, privacy mode; Lighthouse ≥ 90 perf/a11y on mobile |
| O9 | Publication | Paper draft ready for an ACL-family workshop or Indian NLP venue |

Targets O4–O6 are **hypotheses**, not promises. If they fail, we report that honestly
(see `10_honest_assessment.md`).

## 4. Research questions

- **RQ1** Do code-mixed-pretrained encoders (HingBERT / HingRoBERTa / HingRoBERTa-Mixed) outperform
  general multilingual encoders (mBERT, XLM-R, MuRIL, IndicBERT-v2) on Hinglish emotion detection,
  and by how much, once evaluated with multiple seeds and confidence intervals?
- **RQ2** How much does **harmonising multiple datasets** help compared with training on any single
  dataset, especially for **cross-dataset generalisation** to an unseen gold test set?
- **RQ3** How **fragile** are these models to realistic transliteration/spelling and script
  perturbations, and do targeted augmentations close the gap?
- **RQ4** How does performance vary with the **degree of code-mixing** (Code-Mixing Index buckets)?
- **RQ5** Can a **distilled, quantised student** small enough for in-browser inference retain
  ≥ 95% of the teacher's macro-F1?
- **RQ6** How do fine-tuned encoders compare to **zero-/few-shot LLMs** on accuracy, calibration,
  latency and cost for this task?

## 5. Target users

| Persona | Need | What Bhaav gives |
|---------|------|------------------|
| **Student / researcher** (primary for paper) | Baselines, data, reproducible code | API, model card, scripts, benchmark |
| **Curious everyday user** | "What does this message *feel* like?"; fun chat analysis | Text box, chat timeline, privacy mode |
| **Small creator / D2C brand / support lead** | Understand emotions in Hinglish comments/reviews/tickets | Batch CSV, dashboard summary, API |
| **Developer** | Drop-in Hinglish emotion endpoint | REST API, OpenAPI, embeddable snippet |

Explicitly **not** a target: clinicians or anyone making decisions about a specific person's
mental health, employment, credit, policing, etc. (see `16_ethics_privacy_and_risk.md`).

## 6. Scope

### In scope (v1)
- Text only: Hinglish in Roman, Devanagari, or mixed script; also plain Hindi and plain English.
- Label set: **anger, disgust, fear, joy, sadness, surprise, neutral** (Ekman-6 + neutral),
  **multi-label**, each with **intensity 0–3** (aligned with SemEval-2025 Task 11 / BRIGHTER schema).
- Single text analysis, batch CSV (≤ 1,000 rows client-side batched), chat-export timeline.
- Word-level language ID, Code-Mixing Index, attribution highlights, calibrated confidence, abstention.
- Server inference (CPU, ONNX int8) + in-browser privacy mode (distilled student).
- Public REST API with rate limits.

### Out of scope (v1) — candidates for later
- Speech/audio, images, video.
- Other code-mixed pairs (Tanglish, Benglish, Manglish) — architecture should not block them.
- Real-time social-media monitoring / scraping.
- User accounts, saved history, payments.
- Sarcasm/irony detection as a separate model (we only measure the sarcasm failure slice).
- Emotion-cause extraction and emotion-flip *reasoning* (we only *detect* shifts in chats).

## 7. Deliverables

1. GitHub repo (monorepo) with reproducible pipeline and CI.
2. Harmonised dataset release (scripts + IDs; text where licenses allow) + gold test set (if
   annotation source permits release) + datasheet.
3. Trained models on Hugging Face Hub with model cards (teacher + student, ONNX int8).
4. Live website + API (URLs in README) + deployment runbook.
5. Paper (LaTeX, ACL format) + poster/slide deck.
6. Final report: results, error analysis, limitations.

## 8. Success criteria (project-level)

- **Must**: live site + API; documented, reproducible results with seeds and CIs; honest limitations.
- **Should**: significant gain over best generic baseline on the gold test set; robustness gain from
  augmentation; working privacy mode.
- **Could**: paper accepted; community uptake (HF downloads, GitHub stars); extension to another language pair.

## 9. Constraints & assumptions

- **Budget**: ~₹0. Free tiers only (Kaggle/Colab GPUs, Cloud Run free tier, Vercel hobby, HF Hub).
  An optional ≈ US$9/month HF PRO plan is the only paid item ever suggested, and it is not required.
- **Compute**: single T4/P100-class GPU sessions; base-size models (≈ 110M–280M params) only.
- **Team**: 1 student + Claude Code. Annotation needs 2–3 human volunteers fluent in Hindi + English.
- **Timeline**: ~14–16 weeks (see `09_phases_and_roadmap.md`).
- **Assumption**: at least 3 Hinglish emotion datasets are obtainable with research-use licenses
  (verify in Phase 1; fallback plan in `12_data_plan_and_label_schema.md`).

## 10. Glossary

| Term | Meaning |
|------|---------|
| Code-mixing / code-switching | Using two languages within one utterance (intra-sentential) or across sentences |
| Hinglish | Hindi–English code-mixed language, usually Romanised |
| CMI | Code-Mixing Index (Gambäck & Das) — % of tokens not in the dominant language |
| LID | Language identification at the word level |
| Macro-F1 | Unweighted mean of per-class F1; robust to class imbalance |
| ECE | Expected Calibration Error |
| Abstention | Model returns "unsure" when confidence < threshold |
| Silver labels | Automatically produced (e.g. by LLM) labels, never treated as gold |
| Teacher / student | Large accurate model / small distilled model for deployment |
