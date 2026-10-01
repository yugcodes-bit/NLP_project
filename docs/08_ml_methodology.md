# 08 — ML Methodology

From raw datasets to a calibrated, quantised, deployable model. Read with
`07_measurement_methodology.md` (how we measure) and `12_data_plan_and_label_schema.md` (what data).

---

## 1. Pipeline overview

```
fetch ─► validate ─► harmonise labels ─► normalise text ─► script/CMI tagging ─► dedupe
   ─► split ─► (augment train only) ─► train (5 seeds × N models) ─► select on val
   ─► calibrate (T, thresholds, τ) ─► evaluate (val → final: test_in_domain, gold, robust, slices)
   ─► distil student ─► export ONNX fp32/int8 ─► parity check ─► publish to HF Hub + model-meta.json
```

## 2. Data processing

### 2.1 Normalisation (`bhaav.data.normalize`, rules in `configs/normalization.yaml`)
1. Unicode NFC; strip zero-width chars except ZWJ inside emoji sequences.
2. Replace URLs → `<url>`, @mentions → `<user>`, numbers kept (they matter: "100%", "2 ghante").
3. Collapse character elongation to max 2 repeats ("sooooo" → "soo", "!!!!!" → "!!").
4. Lower-case **Roman** text only (Devanagari has no case); keep an `has_caps_shouting` feature flag for analysis only.
5. **Keep emoji** (strong signal). Optionally append emoji names? → *ablation only* (`emoji_demojize: false` default).
6. Hashtags: "#BahutKhush" → "bahut khush" (camel-case split) + keep `#` stripped.
7. **No aggressive spelling normalisation by default** — the model should learn variants. A
   *canonicalisation* step (map variants to a canonical form via `variants.yaml`) is an **ablation**
   (A4) because it may help small models and hurt large ones.

### 2.2 Script & code-mixing tagging
- Script per token by Unicode block → utterance script ∈ {roman, devanagari, mixed}.
- Word-level LID: train a **char n-gram (1–5) logistic regression** on L3Cube-HingLID (+ SentiMix LID tags
  if available). Compare against HingBERT-LID on a held-out LID set; keep the faster one unless the
  F1 gap > 3 points (ADR-006).
- CMI (Gambäck & Das): `CMI = 100 × (1 − max_lang_tokens / (N − univ_tokens))`, 0 if N = univ.

### 2.3 Label harmonisation
Source labels → unified 7-label multi-hot via mappings in `configs/datasets.yaml`
(see `12_data_plan_and_label_schema.md` §4). Principles:
- Map only when semantics clearly align (happy → joy). Ambiguous labels (e.g. "hatred", "love",
  "contempt") → mapped **with a flag** or dropped; decisions recorded in the dataset registry.
- Single-label sources produce multi-hot vectors with one positive; **missing-label uncertainty**:
  for single-label sources, other labels are "probably absent" → optionally use **label smoothing
  on negatives** (ε = 0.05) — ablation A5.
- Intensity: only sources with intensity contribute to the intensity loss (masked).

### 2.4 Deduplication & splits
- Exact (normalised text hash) then MinHash LSH (char 5-grams, 128 perms, Jaccard ≥ 0.8).
- Keep official splits where they exist; otherwise stratified (iterative stratification for multi-label) 80/10/10 per source.
- Gold set is checked against everything; any near-dup in train is **removed from train**, not from gold.

### 2.5 Augmentation (train only; each is an ablation)
| ID | Augmentation | Rate |
|---|---|---|
| AUG-1 | Spelling-variant swap (variants.yaml) | 30% of examples, p=0.3 per token |
| AUG-2 | Roman → Devanagari transliteration of Hindi tokens (full or partial) | 15% |
| AUG-3 | Emoji dropout | 10% |
| AUG-4 | **LLM-generated silver data** for rare classes (disgust, surprise, fear), filtered by teacher agreement + 200-item human spot-check | ≤ 20% of train; flagged `label_source: silver` |
| AUG-5 | English GoEmotions (Ekman-mapped) as auxiliary data, down-weighted (λ=0.3) | ablation |
| AUG-6 | BRIGHTER Hindi (Devanagari) as auxiliary multi-label + intensity data | ablation; likely helpful for intensity |

**Important:** robustness perturbation rules (07 §5) and augmentation rules share code but the
**evaluation perturbations use a different random seed and a held-out subset of the variant table**
(20% of variant pairs reserved for eval only) — otherwise robustness gains are trivially inflated.

## 3. Models

### 3.1 Baselines
| ID | Model | Notes |
|---|---|---|
| B0 | Majority / label-prior | sanity |
| B1 | **Char + word n-gram TF-IDF + one-vs-rest Logistic Regression** | strong for noisy spelling; tune C on val |
| B2 | fastText supervised (char n-grams) | classic |
| B3 | English GoEmotions model applied directly (e.g. a public DistilRoBERTa/RoBERTa GoEmotions checkpoint, Ekman-mapped) | shows "generic English model" failure |
| B4 | Translate-then-classify: Hinglish→English (IndicTrans2 or an open MT model) + B3 | ablation if time |
| B5 | **LLM zero-shot** (one open model e.g. Llama-3.x-8B-Instruct / Qwen-class via local or free API, and one hosted Flash-class model) | prompt in `prompts/llm_zeroshot_v1.md`; JSON output; temperature 0 |
| B6 | LLM few-shot (8 examples from train, fixed) | same |

### 3.2 Encoders (fine-tuned)
| ID | Checkpoint | Why |
|---|---|---|
| E1 | `bert-base-multilingual-cased` | standard baseline |
| E2 | `xlm-roberta-base` | strong multilingual |
| E3 | `google/muril-base-cased` | Indian langs + transliterated |
| E4 | `ai4bharat/IndicBERTv2-MLM-only` **[verify exact id]** | Indic-specialised |
| E5 | `l3cube-pune/hing-bert` | BERT on HingCorpus (Roman) |
| E6 | `l3cube-pune/hing-roberta` | XLM-R on HingCorpus (Roman) |
| E7 | `l3cube-pune/hing-roberta-mixed` | XLM-R on HingCorpus (Roman + Devanagari) — **expected best for mixed script** |
| E8 | `l3cube-pune/hing-mbert-mixed` | mBERT-family mixed |
| (opt) E9 | `xlm-roberta-large` / MuRIL-large | only if GPU budget allows; ceiling reference, not deployable |

### 3.3 Architecture (head)
```
encoder → [CLS] (or mean-pool; ablation A1) → dropout 0.1 →
   ├── emotion head: Linear(h, 7)  → sigmoid           (multi-label)
   └── intensity head: Linear(h, 6×3) → per-emotion CORAL ordinal logits for levels {≥1, ≥2, ≥3}
```
- Emotion loss: **BCE with per-label pos_weight** (inverse frequency, clipped to [1, 10]);
  ablation A2: **Asymmetric Loss (ASL)**.
- Intensity loss: CORAL ordinal loss, **masked** to records with intensity labels and to emotions present.
- Total: `L = L_emo + λ_int · L_int`, λ_int ∈ {0.3, 0.5} (tune on val).
- Optional auxiliary sentiment head (pos/neg/neutral) using SentiMix sentiment labels — ablation A6
  (Ghosh et al. 2023 found multitask helps).
- **Neutral handling**: neutral is a label but is forced exclusive at inference: if any emotion is
  active, neutral is suppressed unless its prob > all others (rule documented in model-meta).

### 3.4 Training recipe (identical budget for all encoders)
| Hyper-parameter | Grid / value |
|---|---|
| Max length | 128 tokens (check 99th percentile; Hinglish tweets are short) |
| Batch size | 32 (grad accumulation if OOM) |
| LR | {2e-5, 3e-5, 5e-5}, linear decay, warm-up 6% |
| Epochs | up to 8, early stopping on val macro-F1, patience 2 |
| Weight decay | 0.01 |
| Precision | fp16 (T4) / bf16 if available |
| Seeds | 5 (13, 42, 87, 1234, 2026) at the chosen LR |
| LR selection | 1 seed per LR → choose LR → run remaining seeds |
| Layer-wise LR decay | off by default (ablation A3 if time) |

Hardware plan: Kaggle Notebooks (free GPU weekly quota **[verify current hours]**) and/or Colab.
Rough cost: 8 encoders × (3 LR + 4 seeds) = 56 runs × ~10–20 min ≈ 10–19 GPU-hours — fits in 1–2 weeks of free quota. Keep all runs resumable and log to `experiments/`. Optional: Weights & Biases free tier or `trackio` for dashboards; the JSON files remain the source of truth.

### 3.5 Threshold, calibration, abstention (all on val)
1. Fit **temperature T** (per-label vector or scalar) by minimising NLL on val logits.
2. Tune **per-label thresholds** t_k maximising val F1 per label (grid 0.05–0.95).
3. Choose **τ** (abstain if max calibrated prob of emotions < τ and neutral prob < τ) to achieve
   ≥ 90% precision on answered items with coverage ≥ 80%; record coverage.
4. Store T, t_k, τ in `model-meta.json`.

### 3.6 Ablations (run on the best encoder only, 3 seeds each)
| ID | Ablation | Hypothesis |
|---|---|---|
| A1 | CLS vs mean-pool | small effect |
| A2 | BCE+pos_weight vs ASL | ASL helps rare labels |
| A3 | LLRD | small |
| A4 | Spelling canonicalisation pre-step | helps B1/small models, neutral/negative for HingRoBERTa |
| A5 | Negative label smoothing for single-label sources | helps multi-label calibration |
| A6 | + sentiment auxiliary head | small gain |
| A7 | **Each augmentation AUG-1..6 on/off** | AUG-1/2 improve robustness score; AUG-4 helps rare-class recall |
| A8 | **Train on single source vs harmonised** | harmonised improves gold (cross-dataset) F1 — **core claim (RQ2)** |
| A9 | Emoji demojize | small |

## 4. Distillation (student for Privacy Mode, RQ5)
- Teacher: best deployable encoder (ensemble of 3 seeds' logits as soft targets — cheap and better).
- Student options (pick by size budget ≤ 60 MB int8):
  - S1: teacher architecture truncated to 4 or 6 layers (init from teacher's layers {0,3,7,11} or similar), same vocab.
  - S2: S1 + **vocab pruning** to tokens appearing ≥ 2× in HingCorpus sample + all train data (re-map embedding rows; tokenizer edited accordingly; verify tokenisation identical on 10k samples).
- Loss: `α·KL(student_T || teacher_T)·T² + (1−α)·BCE(gold)`, α=0.7, T=2; plus hidden-state MSE on mapped layers (optional).
- Data for distillation: train + **unlabelled Hinglish text** (L3Cube-HingCorpus sample, 200k sentences, teacher-labelled) — big boost for students.
- Report: size, latency (browser WASM), macro-F1 retained (target ≥ 95% of teacher).

## 5. Export & quantisation
1. `torch.onnx.export` / `optimum` exporter with dynamic axes (batch, seq), opset ≥ 17.
2. ORT graph optimisation (transformer optimiser).
3. **Dynamic int8 quantisation** (MatMul + embedding Gather where supported); compare fp16 for browser WebGPU.
4. Parity tests (FR-38). Benchmark latency (07 §2.7).
5. Generate `model-meta.json` (labels, T, thresholds, τ, intensity cutpoints, normalisation version, training data hash, git SHA).
6. Push to HF Hub with model card (intended use, limitations, metrics with CIs, data sources & licenses, CO₂ estimate).

## 6. LLM usage policy (research only)
- B5/B6 baselines: run on `val` (for prompt development, ≤ 2 prompt iterations) then once on `gold`.
- Silver data (AUG-4): generation prompt in `prompts/silver_generation_v1.md`; every generated item
  passes (a) teacher-agreement filter, (b) dedupe vs. gold, (c) toxicity/PII filter; 200-item human audit with precision reported.
- **Never** send production user text to an LLM.

## 7. Error analysis protocol (Phase 5)
Sample 200 gold errors of the final model; tag each with: spelling variant, script, sarcasm/irony,
emoji-dependent, negation ("khush nahi hu"), context-needed, label ambiguity, annotation error,
cultural idiom ("dil garden garden ho gaya"). Report counts + 10 illustrative examples (anonymised).
Feed recurring patterns back into variants.yaml / augmentation — but **not** into the gold set.
