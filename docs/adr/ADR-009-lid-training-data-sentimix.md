# ADR-009: Train the word-level LID on SentiMix, not HingLID

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** project owner (chose "SentiMix only") + Claude Code
- **Amends:** ADR-006 (the data source only; the model family is unchanged)

## Context
ADR-006 chose a character n-gram logistic regression for word-level language tags and named
L3Cube-HingLID (+ SentiMix) as training data, on the belief that HingLID was CC-BY-4.0.

The licence check of 2026-10-02 found that the L3Cube README licenses HingCorpus and HingLID as
**CC BY-NC-SA 4.0**. NonCommercial + ShareAlike would follow the trained tagger into the API and
the in-browser model, and README promises model weights under "the most restrictive training
source" licence. SemEval-2020 Task 9 SentiMix is **CC-BY-4.0** (Zenodo, open) and has word-level
`Hin` / `Eng` / `O` / `EMT` tags for 20,000 Hinglish tweets.

## Options considered
1. **HingLID (+ SentiMix)** — cleaner word tags and an established LID benchmark; but NC-SA terms
   on a component that ships in the public product.
2. **SentiMix only** — permissive licence, same register as much of our emotion data (tweets);
   but its word tags are noisy and it is not a standard LID benchmark.
3. **No learned LID** (script rules + dictionary) — no licence question; poor on Roman-script text,
   which is most of Hinglish.

## Decision
We choose **SentiMix only** for training and evaluating the LID model. HingLID and HingCorpus stay
`likely_allowed` in the registry and are not fetched.

## Consequences
- + The tagger, and everything built on it (Code-Mixing Index, the code-mix lens), carries no
  NonCommercial or ShareAlike obligation.
- − Measured quality is agreement with noisy tags. First run (`lid_charngram_sentimix_v1`): test
  macro-F1 0.8412 (95% CI 0.8376–0.8449). An informal check on GoEmotions (plain English) showed
  the tagger labelling roughly one word in eleven as Hindi, so CMI is inflated on monolingual
  text. That check is not a recorded experiment yet and must not be quoted as a result.
- − The roadmap line "LID evaluated on HingLID test" is replaced by evaluation on the SentiMix
  official test file. Our number is not comparable with published HingLID results.
- HingCorpus was also the planned source of unlabelled text for distillation (`08` §4) and of
  spelling-variant mining. Those need a new plan or a separate decision on the NC-SA terms.
- Reversal: mark `hinglid` allowed, add a reader, retrain; nothing else changes.

## Validation
- Phase 5 (ADR-006): compare against HingBERT-LID on a held-out set; upgrade only if it wins by
  more than 3 F1 and fits the latency budget.
- Hand-check a sample of tagger errors against SentiMix tags to estimate how much of the roughly
  16% disagreement is label noise rather than model error.
