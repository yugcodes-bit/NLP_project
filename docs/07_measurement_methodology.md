# 07 — Measurement Methodology

How every number in this project is produced. If a metric is not defined here, it does not go in
the paper or on the website.

---

## 1. Evaluation sets

| Set | Source | Purpose | Allowed uses |
|---|---|---|---|
| `train` | Harmonised sources (train portions) | Fit models | Training only |
| `val` | Stratified held-out 10% of each source (or official dev) | Model selection, early stopping, threshold tuning, temperature scaling, τ | Unlimited |
| `test_in_domain` | Official/held-out test portions of each source | Per-source comparability with prior work | Final eval only |
| **`gold`** | **Fresh human-annotated set** (`18_annotation_guidelines.md`) | Headline results; cross-dataset generalisation | **Final eval only — logged each use** |
| `robust` | Deterministic perturbations of `gold` (and `val` for dev) | Robustness (RQ3) | `val` version during dev; `gold` version at final |
| `slices` | Tagged subsets of gold: script (roman/devanagari/mixed), CMI bucket, has-emoji, sarcasm-flagged, length bucket | Error analysis (RQ4) | Final eval only |

Leakage controls: exact + MinHash near-duplicate removal (char 5-gram Jaccard ≥ 0.8) **between all
splits and vs. gold**; gold collected from sources/time-period disjoint from training data where possible;
report the number of removed items.

## 2. Primary & secondary metrics

### 2.1 Emotion detection (multi-label, 7 labels)
- **Primary: macro-F1 over the 6 emotions + neutral** (per-label binary F1, unweighted mean).
- Secondary: micro-F1, per-label P/R/F1, **sample-wise Jaccard** (SemEval-2018/2025 style), exact-match ratio, ROC-AUC per label (threshold-free).
- **Single-label sources** (when evaluating per-source comparability): also report macro-F1 and
  accuracy on argmax prediction **only** to compare with prior papers; never headline accuracy.

### 2.2 Intensity (0–3)
- Per-emotion **Pearson r** between predicted and gold intensity on items where the emotion is present
  in gold *or* predicted (SemEval-2025 Track B convention: report r over all items with 0 for absent) —
  document which convention; compute **both** and headline the SemEval one.
- Quadratic-weighted Cohen's κ (ordinal agreement) as secondary.

### 2.3 Calibration
- **ECE** (15 equal-mass bins) per label on predicted probability vs. binary truth; report mean over labels.
- **Brier score**.
- Reliability diagram (figure).
- Before and after temperature scaling (per-label or shared T — pick on val; report both).

### 2.4 Selective prediction (abstention)
- **Risk–coverage curve** and **AURC** (area under risk–coverage; lower is better), risk = 1 − sample Jaccard.
- Operating point: coverage and macro-F1-on-answered at the deployed τ.

### 2.5 Robustness
For each perturbation family p (see §5): **Δ_p = macroF1(clean) − macroF1(perturbed)** and
**prediction flip rate** (fraction of items whose active-label set changes).
Aggregate **Robustness Score = mean_p(macroF1_perturbed / macroF1_clean)**.

### 2.6 Code-mixing slices
Macro-F1 per CMI bucket: `[0,10)`, `[10,30)`, `[30,50]` (+ "monolingual Hindi", "monolingual English").
Macro-F1 per script: roman, devanagari, mixed.

### 2.7 Efficiency
- Parameters, ONNX file size (fp32/int8), peak RAM.
- **Latency**: p50/p95/p99 over 1,000 gold texts, batch=1, after 50 warm-up calls, on (a) Cloud Run
  1 vCPU, (b) local reference CPU (record model), (c) browser WASM on a mid-range laptop and a
  mid-range Android phone (Chrome). Report cold-start separately.
- Throughput (texts/sec) at batch 16.

### 2.8 Explanations (paper, light-touch)
- **Deletion test / comprehensiveness**: drop top-k attributed words → drop in predicted prob
  (higher = more faithful) vs. dropping random k words. k ∈ {1, 3}.
- Spearman ρ between occlusion and Integrated Gradients word rankings (agreement check).

### 2.9 LLM baseline cost
Tokens, USD (or free-tier requests) per 1,000 texts, latency per text, and parse-failure rate.

## 3. Statistical protocol

1. **Seeds**: every trainable configuration × **5 seeds** {13, 42, 87, 1234, 2026}. Report mean ± std.
2. **Confidence intervals**: 1,000× bootstrap over gold items (resample items, recompute macro-F1)
   using the seed-ensemble-averaged predictions *or* per seed then averaged — state which. Report 95% CI.
3. **Pairwise comparison** (our best vs. each baseline): **paired bootstrap** on macro-F1 difference
   (10,000 resamples, two-sided); also **approximate randomisation** test as a check. Significance at
   α = 0.05 with **Holm–Bonferroni** correction across comparisons.
4. **No test-set tuning**: thresholds, T, τ, early stopping — all on `val`.
5. **Hyperparameter search budget** equal across encoders (same grid, §08) — avoid giving our favourite model more tuning.
6. **Report everything**, including models that lose. Negative results go in the paper.

## 4. Inter-annotator agreement (gold set)
- **Krippendorff's α** (nominal, per label as binary; and overall via MASI distance for sets).
- Intensity: Krippendorff's α (interval) on items where both annotators mark the emotion present.
- Target α ≥ 0.6 per label for "acceptable"; report honestly if lower and discuss (emotion is subjective; SemEval-2025 used reliability measures like split-half class match for this reason).
- Final gold label = majority (≥ 2 of 3) or adjudicated by a third annotator when 2 disagree.

## 5. Robustness perturbation suite (deterministic, seed 2026)

| Family | Operation | Example |
|---|---|---|
| P1 Spelling variants | Swap tokens using `configs/variants.yaml` (bahut→bohot/bhot, nahi→nhi/nai, hai→h/he, kya→kia, mujhe→mjhe) with p=0.5 per eligible token | "bahut accha hai" → "bohot acha h" |
| P2 Vowel/char drop (SMS-style) | Drop internal vowels for Hindi-tagged tokens, p=0.3 | "pyaar" → "pyr" |
| P3 Script switch → Devanagari | Transliterate Hindi-tagged tokens to Devanagari (IndicXlit) | "bahut khush" → "बहुत खुश" |
| P4 Mixed script | Transliterate 50% of Hindi tokens | "बहुत khush" |
| P5 Emoji removal | Remove all emoji | "maza aa gaya 😂" → "maza aa gaya" |
| P6 Elongation / case | "sooo", "BAHUT", "!!!!" normalisation stress | |
| P7 Typos (keyboard) | 1 adjacent-key substitution per 10 chars | |
| P8 Code-mix direction | Translate content words en↔hi using a small bilingual dictionary (no LLM) | "very happy" → "bahut happy" |

P5 is diagnostic (emoji carry genuine signal — a drop is expected, not a bug). All perturbation
code lives in `ml/src/bhaav/robustness.py` and mirrors `apps/web/lib/variants.ts` (playground).
Each perturbed item keeps its gold label; a 100-item manual check confirms perturbations do not
change the meaning (report % meaning-preserving).

## 6. Reporting templates

### Main results table (paper Table 2)
| Model | Params | macro-F1 (gold) | 95% CI | micro-F1 | Jaccard | ECE (after T) | Robust. score | p50 ms (CPU) |
|---|---|---|---|---|---|---|---|---|

### Per-source table (paper Table 3) — macro-F1 when training on single source vs. harmonised, evaluated on each `test_in_domain` and on `gold` (cross-dataset matrix heatmap).

### Figures
1. Cross-dataset generalisation heatmap (train source × eval set).
2. Robustness bars per perturbation family for top 4 models (+ with/without augmentation).
3. Macro-F1 by CMI bucket and script.
4. Reliability diagrams before/after temperature scaling.
5. Risk–coverage curves.
6. Teacher vs. student: size–latency–F1 trade-off scatter.

## 7. Artefacts each evaluation run must write
`metrics.json` (all numbers above, nested by set/slice), `per_label.csv`, `predictions_<set>.jsonl`
(id, probs, active labels, intensity — no text), `bootstrap.json`, `reliability.png`, `NOTES.md`.
Aggregation script `bhaav.report` builds paper tables (LaTeX + Markdown) **only** from these files.
