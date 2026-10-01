# 03 — Literature Review

Snapshot: 2026-10-01. Entries marked **[verify]** contain details (exact counts, licenses, availability)
that Claude Code must confirm from the primary source before they appear in the paper.
Keep `paper/refs.bib` in sync with this file.

---

## 1. Emotion models (theory → label sets)

- **Ekman (1992)** — six basic emotions: anger, disgust, fear, joy (happiness), sadness, surprise.
  Most computational label sets (incl. SemEval-2025 Task 11) derive from it.
- **Plutchik (1980)** — 8 primary emotions incl. trust and anticipation; intensity dimension.
- **GoEmotions (Demszky et al., ACL 2020)** — 58k English Reddit comments, 27 emotions + neutral,
  multi-label, with an official Ekman mapping. Standard English transfer source.

**Decision:** Ekman-6 + neutral, multi-label, intensity 0–3 → maximises compatibility with existing
Hinglish datasets (most use subsets of Ekman) and with BRIGHTER/SemEval-2025 schema.

## 2. Code-mixing foundations

- **Code-Mixing Index (Gambäck & Das, 2014/2016)** — quantifies mixing per utterance; later work
  (Kodali et al. 2025, cited in an EACL 2026 Findings paper) finds structural metrics like CMI
  correlate poorly with human *acceptability* — fine for bucketing analysis, not as a quality score.
- **Word-level LID** — FIRE shared tasks; **L3Cube-HingLID + HingBERT-LID** (production-quality LID model).
- **Benchmarks**: **LinCE** (Aguilar et al., LREC 2020), **GLUECoS** (Khanuja et al., ACL 2020) —
  code-switching evaluation suites (LID, POS, NER, sentiment; no emotion task).
- **COMI-LINGUA (2025)** — expert-annotated large-scale multitask Hinglish dataset **[verify tasks; check
  whether sentiment/emotion is included]**.
- **Transliteration**: AI4Bharat **Aksharantar / IndicXlit** — open transliteration models/datasets
  for Indic ↔ Roman; used for script-switch augmentation and normalisation.
- **Synthetic code-mixed generation**: GCM toolkit; LLM-based code-mixed augmentation
  (e.g. arXiv 2411.00691 shows LLM-generated code-mixed data helps sentiment for Spanish-English and
  Malayalam-English).

## 3. Pretrained encoders relevant to Hinglish

| Model | Pretraining | Script | Notes |
|---|---|---|---|
| mBERT | 104-language Wikipedia | mostly native scripts | Weak on Romanised Hindi |
| XLM-R (base/large) | CC-100, 100 languages | native scripts | Strong multilingual baseline; 250k vocab → large embedding matrix |
| MuRIL (Google) | 17 Indian languages + **transliterated** pairs | native + Roman | Designed for Indian langs incl. transliterated text |
| IndicBERT v2 (AI4Bharat) | IndicCorp v2, 23 langs | native (+ some Roman) **[verify]** | Strong on Indic NLU |
| **HingBERT / HingMBERT / HingRoBERTa** (L3Cube, Nayak & Joshi, WILDRE-6 @ LREC 2022) | **L3Cube-HingCorpus: 52.93M real Hinglish sentences, 1.04B tokens from Twitter** | Roman | BERT / mBERT / XLM-R further pretrained on HingCorpus |
| **HingBERT-Mixed, HingRoBERTa-Mixed** | HingCorpus Roman + Devanagari | mixed | Best fit for mixed-script input |
| HingGPT | GPT-2 on HingCorpus | Roman / Devanagari | Generative; not our focus |

Evidence: L3Cube models outperform mBERT/XLM-R on Hinglish downstream tasks in their paper; a later
comparative NER study reports HingRoBERTa/HingBERT beating other models including a closed LLM.
License: **CC-BY-4.0** (per HF model cards).

## 4. Hinglish emotion datasets & systems (chronological)

| Year | Work | Data | Labels | Reported result | Availability |
|---|---|---|---|---|---|
| 2018 | **Vijay et al.**, NAACL-SRW — "Corpus creation and emotion prediction for Hindi-English code-mixed social media text" | Hinglish tweets with word-level language + causal-language annotations | Ekman-6 **[verify]** | SVM baseline | Public on GitHub **[verify]** |
| 2020 | **Sasidhar, Premjith, Soman** — Procedia CS | **12,000** Hinglish texts from various sources (incl. Vijay et al.) | happy, sad, anger | CNN-BiLSTM **83.21% accuracy** | **[verify]** |
| 2021 | **Wadhawan & Fahim**, WASSA @ EACL (arXiv 2102.09943) | Class-balanced Hinglish tweets, self-annotated | 6 emotions | BERT best, **71.43% accuracy** | Claimed "openly available" **[verify]** |
| 2021→2026 | arXiv 2105.09226 (v6, revised) | **1,589** sentences, Twitter + video comments, κ = 0.94 | 4 emotions | 5 baseline classifiers; revision explicitly retracts a "first" claim | Released **[verify]** |
| 2023 | **Ghosh et al.**, Knowledge-Based Systems — multitask sentiment + emotion | **20,000** SentiMix (SemEval-2020 T9) instances manually labelled with Ekman emotions | Ekman-6 (+neutral?) **[verify]** | Transformer multitask framework | On request? **[verify]** |
| 2024 | **SemEval-2024 Task 10 (EDiReF)**, Kumar et al. — data: **MaSaC** (Bedi et al. 2023), Indian TV sitcom dialogues | Hindi-English code-mixed **conversations** | 8 emotions (ERC) + emotion-flip triggers | Best ERC F1 **0.70**; 84 participants, 24 system papers | **Public** (GitHub: LCS2-IIITD/EDiReF-SemEval2024) |
| 2024 | **EmoMix-3L** (WILDRE-7 @ LREC-COLING) | **1,071** Bangla-Hindi-English test instances | multi-label emotions | MuRIL best | Public (GitHub) |
| 2025 | **CNN-transformer**, Discover AI (Springer) | **20,201** code-mixed tweets (imbalanced) | happy, sad, anger, neutral | — | **[verify]** |
| 2025 | **mBERT hybrid + attention**, Int. J. Inf. Tech. (Springer, Nov 2025) | Hinglish | emotions | — | **[verify]** |
| 2026 | **Healer** — Knowledge-infused hierarchy-aware ERC, LREC 2026 | New Hinglish **mental-health counselling** conversation dataset | hierarchical emotions | — | **[verify]**; sensitive domain |

Related (not Hinglish, but useful):
- **EmoInHindi** (Singh et al., LREC 2022) — 1,814 Hindi dialogues, **44,247** utterances, **16** emotions,
  multi-label + intensity; Wizard-of-Oz counselling setting; Devanagari Hindi.
- **BRIGHTER / SemEval-2025 Task 11** (Muhammad et al. 2025) — 28 languages, multi-label + intensity
  (0–3) over anger, disgust, fear, joy, sadness, surprise (+neutral); **Hindi split ≈ 2,556 train /
  100 dev / 1,010 test** (Devanagari). 700+ participants; data public.
- **SemEval-2020 Task 9 SentiMix** (Patwa et al.) — ~20k Hinglish tweets with sentiment + word LID;
  base of Ghosh et al. emotion labels.

## 5. Methods observed in the literature

| Family | Examples | Takeaway for us |
|---|---|---|
| Classical | SVM/LR on n-grams; char n-grams | **Char n-gram TF-IDF + LR is a strong, cheap baseline** for noisy spelling — must include |
| Static embeddings + RNN/CNN | fastText/Word2Vec + BiLSTM/CNN-BiLSTM | Historical; include one (fastText) for completeness |
| Fine-tuned transformers | BERT, RoBERTa, mBERT, XLM-R, MuRIL | Current standard; most papers single-seed |
| Hybrid heads | mBERT + BiLSTM/CNN + attention | Marginal gains, often within seed variance — we test one hybrid at most |
| Translation pipeline | Hinglish→English then English model (AIMA @ SemEval-24) | Adds latency + translation errors; include as ablation if cheap |
| Context/conversation | History-based ERC, speaker modelling (SemEval-24) | Inspires our chat-timeline; we use light context only |
| LLM prompting / ensembling | Mistral-7B, GPT, ensembles + prompting (MasonTigers) | LLMs as baseline + silver data |
| LLM-generated explanations as features | Lotus @ SemEval-25 (Llama-3 explanations + RoBERTa) | Interesting; out of scope for v1 (latency) |
| Weighted loss for imbalance | SemEval-25 weighted BCE | Use class-weighted BCE / ASL |
| Multitask sentiment + emotion | Ghosh et al. 2023 | Optional auxiliary sentiment head (ablation) |

## 6. Fine-tuned encoders vs LLMs

- Bucher & Martini (2024): fine-tuned smaller models **consistently and significantly outperform**
  zero-shot GPT-3.5/4 and Claude Opus across sentiment, stance and **emotion** tasks; gap widens for
  less standard tasks and with more training data.
- Code-mixed: GPT-4 zero-shot underperforms dataset benchmarks for Spanish-English and
  Malayalam-English sentiment (arXiv 2411.00691). A Hinglish NER study (COMI-LINGUA) shows mixed
  LLM results (some LLMs strong on small samples, GPT-4o weak) — LLM results are **prompt- and
  sample-sensitive**, so we evaluate on the full gold test set, not a tiny subset.
- **Implication**: product uses a fine-tuned encoder; LLM is a comparison point and offline helper.

## 7. Gaps → our contributions

| Gap in literature | Our response |
|---|---|
| Incompatible label sets; single-dataset evaluation | Harmonised multi-source corpus + documented mapping + cross-dataset eval |
| No independent test set; possible leakage / near-dupes | Fresh gold test set + MinHash near-dup removal |
| Accuracy on imbalanced data; single seed | Macro-F1, 5 seeds, bootstrap CIs, significance tests |
| Robustness to spelling/script variation not measured | Perturbation suite + augmentation ablation |
| Calibration ignored | ECE, reliability diagrams, temperature scaling, abstention curves |
| Effect of mixing degree unclear | CMI-bucketed analysis |
| No deployable/open tool | Live site, API, ONNX student, in-browser privacy mode |

## 8. Reading list for Claude Code (priority order)
1. L3Cube HingCorpus/HingBERT paper — arXiv 2204.08398
2. SemEval-2025 Task 11 overview — arXiv 2503.07269 (schema, metrics, intensity)
3. SemEval-2024 Task 10 overview — arXiv 2402.18944 (+ AIMA 2501.11166, MasonTigers 2407.00581)
4. Wadhawan & Fahim 2021 — arXiv 2102.09943
5. Ghosh et al. 2023 — KBS (multitask)
6. arXiv 2105.09226 (latest version) — small high-agreement dataset
7. Bucher & Martini 2024 — arXiv 2406.08660
8. Guo et al. 2017 "On Calibration of Modern Neural Networks" (temperature scaling)
9. Ribeiro et al. 2020 CheckList (behavioural testing → our robustness suite)
10. Sanh et al. DistilBERT; Hinton et al. 2015 distillation

## Sources
- https://arxiv.org/abs/2102.09943
- https://arxiv.org/html/2105.09226v6
- https://www.sciencedirect.com/science/article/pii/S1877050920311236
- https://www.sciencedirect.com/science/article/abs/pii/S0950705122012783
- https://aclanthology.org/2024.semeval-1.270/ · https://arxiv.org/pdf/2402.18944
- https://arxiv.org/pdf/2501.11166 · https://arxiv.org/pdf/2407.00581
- https://github.com/GoswamiDhiman/EmoMix-3L · https://arxiv.org/pdf/2405.06922
- https://link.springer.com/article/10.1007/s44163-025-00400-y
- https://link.springer.com/article/10.1007/s41870-025-02813-5
- https://aclanthology.org/2026.lrec-1.226/
- https://aclanthology.org/2022.lrec-1.627/ (EmoInHindi)
- https://brighter-dataset.github.io · https://arxiv.org/pdf/2502.19856 · https://arxiv.org/pdf/2507.08499
- https://github.com/l3cube-pune/code-mixed-nlp · https://huggingface.co/l3cube-pune/hing-roberta-mixed
- https://arxiv.org/pdf/2503.21670 (COMI-LINGUA)
- https://arxiv.org/abs/2406.08660 · https://arxiv.org/pdf/2411.00691
- https://aclanthology.org/2026.findings-eacl.291.pdf
