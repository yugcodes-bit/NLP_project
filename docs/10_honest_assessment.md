# 10 — Honest Assessment

Read this before getting excited. It exists so that neither the human nor Claude Code overclaims,
and so that we know in advance when to change course.

---

## 1. What is NOT novel (don't claim it)

- **Hinglish emotion detection itself.** Done since at least Vijay et al. (2018); datasets and
  transformer results from 2020–2026 (Sasidhar 2020, Wadhawan & Fahim 2021, Ghosh 2023, SemEval-2024
  Task 10, multiple 2025 papers). One 2021 paper literally had to retract a "first" claim in a 2026 revision.
- **Fine-tuning mBERT / XLM-R / MuRIL / HingBERT on Hinglish.** Standard practice.
- **Hybrid "BERT + BiLSTM + attention" heads.** Many papers; gains usually within seed noise.
- **Multi-label + intensity schema.** Borrowed from SemEval-2025 Task 11 / EmoInHindi.
- **Distillation, ONNX quantisation, Transformers.js.** Standard engineering.
- **Emotion web demos.** Thousands exist (mostly English).

## 2. What plausibly IS a contribution (claim carefully, with evidence)

1. **Harmonisation + cross-dataset evaluation** of Hinglish emotion datasets with a documented mapping,
   showing how models trained on one source generalise (or don't) to others and to fresh data.
2. **An independent, multi-annotated gold test set** with reported agreement.
3. **Systematic, statistically sound comparison** (5 seeds, CIs, significance) of code-mixed vs. multilingual
   encoders vs. classical vs. LLM baselines on the same data.
4. **Robustness suite** for transliteration/spelling/script variation + evidence on whether augmentation fixes it.
5. **Calibration + selective prediction** analysis for this task.
6. **An open, deployed, private-by-default tool** with a distilled in-browser model — a practical artefact
   most papers in this area do not provide.

Individually modest; together a solid **resource + analysis** paper and a genuinely useful product.

## 3. Biggest risks

| # | Risk | Likelihood | Impact | Mitigation | Early signal |
|---|---|---|---|---|---|
| R1 | **Datasets unavailable / unclear license** | High | High | Registry with status; email authors in week 1; fallback plan (`12` §7): SemEval-24 MaSaC (public) + BRIGHTER Hindi + SentiMix re-annotation subset + our gold | Week 2: < 2 usable sources |
| R2 | **Label mapping noise** (different annotators/definitions) hurts more than it helps | Medium | Medium | A8 ablation (single vs harmonised); per-source weighting; drop bad sources | A8 shows harmonised < best single on gold |
| R3 | **Low IAA on gold** (emotion is subjective) | Medium | High | Clear guidelines, pilot round, adjudication, report α honestly, allow multi-label | Pilot α < 0.4 |
| R4 | Annotation volunteers drop out | Medium | High | Smaller gold (≥ 800), pay in pizza/credits, split into 100-item batches | Week 3 throughput < 150/annotator |
| R5 | HingRoBERTa doesn't beat MuRIL/XLM-R significantly | Medium | Low | That's a valid finding — report it; RQ1 is a question, not a promise | Phase 4 val |
| R6 | Robustness augmentation gains are trivial because eval perturbations ≈ train augmentations | Medium | Medium | Held-out variant pairs + different seed (08 §2.5); also natural-variant slice from gold | — |
| R7 | **LLM baseline beats us** on gold | Low–Med | Medium | Still win on cost/latency/privacy/calibration; report honestly; position product accordingly | Phase 3 val |
| R8 | Student too big/slow for phones | Medium | Medium | Vocab pruning; 4-layer student; WebGPU; or ship Privacy Mode as "desktop recommended" | Phase 7 size > 100 MB |
| R9 | Cloud Run free-tier/pricing changes, or cold starts annoy users | Low–Med | Low | Portable Docker; "waking up" UI; Privacy Mode fallback; min-instances=1 if funded | — |
| R10 | Misuse: analysing others' chats, surveillance, mental-health inference | Medium | High | `16_ethics_privacy_and_risk.md`: consent notice, no storage, pseudonymisation, disclaimers, no "risk score" | — |
| R11 | Offensive/toxic content in datasets and examples | High | Medium | Review example gallery; content filters for silver data; content warning in paper | — |
| R12 | Scope creep (sarcasm, speech, more languages) | High | Medium | Feature scoring in `04`; cut list in `09` | Weekly check |
| R13 | Free GPU quota insufficient | Low–Med | Medium | Reduce grid (2 LRs), 3 seeds for ablations, skip large models | — |

## 4. Known limitations we will state up front

- Text-only; no tone of voice or facial cues; sarcasm remains hard.
- Labels capture **perceived** emotion of the writer by annotators, not the writer's true state.
- Data skews toward Twitter/YouTube/TV-dialogue registers, North-Indian Hindi, urban, younger users.
- Ekman-6 is a simplification (no "love", "pride", "embarrassment", "nostalgia" — culturally important).
- Romanised spelling varies by region; our variant tables are incomplete.
- Model may encode stereotypes from social-media data (e.g. associating groups/places with anger).
- Not validated for clinical, HR, legal, or safety-critical decisions — **must not be used for them**.

## 5. Kill / pivot criteria (decide, don't drift)

| Checkpoint | If… | Then… |
|---|---|---|
| End of week 2 | < 2 usable labelled Hinglish sources | Pivot data: MaSaC (SemEval-24) + BRIGHTER-Hindi transfer + bigger gold (2,000) used with cross-validation; reframe paper around gold + transfer |
| End of week 5 | Gold α < 0.4 after revision | Reduce to 4 coarse labels (joy, sadness, anger, neutral+other) for headline; keep 7-label as secondary |
| End of week 6 | Best encoder ≤ B1 (TF-IDF) + 2 F1 | Investigate data noise; the paper becomes a "why is this hard" analysis; product still ships |
| Week 9 | Can't hit NFR-01 latency | Ship smaller teacher (distilled 6-layer) for server too |
| Week 11 | Student < 85% of teacher F1 | Privacy Mode labelled "lite (less accurate)"; or desktop-only |

## 6. Effort reality check

- Biggest time sinks are **not** model training: they are dataset access/cleaning (Phase 1),
  annotation (Phase 2), and frontend polish (Phases 6–7).
- Claude Code can write ~all code, but **cannot**: annotate data, sign up for clouds, accept dataset
  licenses, or judge cultural nuance of examples. Budget human hours: ~25–40 h annotation per
  annotator, ~6–10 h accounts/deploy/admin, ~15 h paper review.

## 7. Integrity checklist (before any public claim)
- [ ] Number comes from `experiments/*/metrics.json` at a recorded git SHA
- [ ] Mean ± std over seeds and a CI are shown
- [ ] Compared on the same split with the same metric
- [ ] Prior work cited for anything not ours
- [ ] Limitation sentence nearby if the claim could be over-read
