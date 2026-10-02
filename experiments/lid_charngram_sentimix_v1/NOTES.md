# lid_charngram_sentimix_v1

Word-level language identification (Hindi vs English) for Roman-script words: logistic regression
on hashed character 1–5-grams (ADR-006). Trained and evaluated on SemEval-2020 Task 9 SentiMix
(Hinglish), CC-BY-4.0, DOI 10.5281/zenodo.3974927.

## Result

| split | tweets | scored tokens | accuracy | macro-F1 | majority-class accuracy |
|---|---|---|---|---|---|
| val (official validation) | 3000 | 62579 | 0.8464 | 0.8420 | 0.5911 |
| **test (official test)** | 3000 | 62430 | 0.8442 | **0.8412** | 0.5783 |

Test macro-F1 95% bootstrap interval over tweets (1000 resamples): [0.8376, 0.8449].
`C` = 10.0 was chosen on val from [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]; test was scored once.

## How to read this number

- It measures **agreement with SentiMix's own word tags**, and those tags are noisy: names and
  some non-Hindi, non-English words carry `Eng` or `Hin` tags in the source. The score is
  therefore not a clean accuracy against expert labels, and its ceiling is below 1.
- Only Roman-script words tagged `Hin`/`Eng` are scored. Emoji, numbers, punctuation and
  Devanagari are tagged by rule in `bhaav.data.lid` and are not part of this number.
- One deterministic fit (convex objective), so there is no seed variance to report; the interval
  above reflects sampling of tweets only.
- Train, val and test come from the same Twitter collection. Nothing here says how the tagger
  behaves on chat-style text.
- ADR-006 also calls for a comparison with HingBERT-LID. That is not done yet.

## Files

`config.yaml`, `metrics.json`, `predictions_val.jsonl` (per tweet: gold and predicted language of
each scored token as `h`/`e`; no text), `env.txt`.
