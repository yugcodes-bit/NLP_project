# 12 — Data Plan & Label Schema

Single source of truth in code: `configs/label_schema.yaml` and `configs/datasets.yaml`.
This document explains the reasoning; if they disagree, the YAML wins and this doc must be updated.

---

## 1. Unified label schema

| Label | Definition (writer's expressed feeling) | Hinglish cues (non-exhaustive) |
|---|---|---|
| **anger** | annoyance, frustration, rage, irritation | gussa, dimaag kharab, bakwaas, pagal, chid, 😡🤬 |
| **disgust** | revulsion, contempt, strong moral distaste | chhi, ghatiya, ghinn, yuck, sharam aani chahiye, 🤢 |
| **fear** | worry, anxiety, nervousness, dread | darr, tension, ghabrahat, dil dhak dhak, 😰 |
| **joy** | happiness, excitement, pride, love/affection, relief | khush, maza aa gaya, mast, zabardast, ❤️😂🥳 |
| **sadness** | sorrow, disappointment, loneliness, hurt | dukh, udaas, bura laga, rona aa gaya, 😢💔 |
| **surprise** | astonishment, shock (pos. or neg.) | kya!, sach mein?, omg, yakeen nahi hota, 😲 |
| **neutral** | no clear emotion; informational | — |

- **Multi-label**: any subset of the 6 emotions; `neutral` only when none apply.
- **Intensity** per present emotion: 1 = low ("thoda"), 2 = moderate, 3 = high ("bahut zyada", caps, multiple !!!, strong emoji).
- Schema intentionally matches SemEval-2025 Task 11 (BRIGHTER) labels → enables Hindi transfer and comparison.
- "Love" is mapped to **joy** (documented limitation); "trust/anticipation" (Plutchik) not used.

## 2. Dataset registry (status as of 2026-10-01 — Claude Code must verify each)

| Key | Dataset | Lang/script | Size (reported) | Source labels | Role | Status |
|---|---|---|---|---|---|---|
| `vijay18` | Vijay et al. 2018 Hinglish emotion tweets | Hinglish Roman | ~2.8k **[verify]** | Ekman-6 **[verify]** | train/val/test_in_domain | `to_verify` |
| `wadhawan21` | Wadhawan & Fahim 2021 (WASSA) | Hinglish Roman | **[verify]** | 6 classes (class-balanced) | train/val/test_in_domain | `to_verify` |
| `sasidhar20` | Sasidhar et al. 2020 | Hinglish | 12,000 | happy, sad, anger | train | `to_verify` (likely overlaps vijay18 → dedupe!) |
| `ghosh23` | Ghosh et al. 2023 SentiMix-emotion | Hinglish Roman | 20,000 | Ekman (+neutral?) | train/val/test_in_domain | `to_verify` (may need author request) |
| `cm1589` | arXiv 2105.09226 corpus | Hinglish Roman | 1,589 | 4 emotions | train/val/test_in_domain | `to_verify` |
| `masac24` | SemEval-2024 T10 EDiReF / MaSaC ERC | Hinglish (TV dialogue) | dialogues (see repo) | 8 emotions | train (utterance-level) + conversation demo eval | `likely_allowed` (public GitHub) |
| `brighter_hin` | SemEval-2025 T11 Hindi | Hindi **Devanagari** | 2,556 / 100 / 1,010 | 6 + intensity | auxiliary train (AUG-6), intensity | `likely_allowed` **[check license]** |
| `emoinhindi` | EmoInHindi 2022 | Hindi Devanagari, dialogue | 44,247 utt. | 16 + intensity | optional auxiliary | `to_verify` |
| `emomix3l` | EmoMix-3L 2024 | Bangla-Hindi-English | 1,071 (test) | multi-label | **extra OOD eval only** | `likely_allowed` |
| `goemotions` | GoEmotions (Ekman mapping) | English | 58k | 27→Ekman | auxiliary (AUG-5) | `allowed` (Apache-2.0 **[verify]**) |
| `hinglid` | L3Cube-HingLID | Hinglish | — | word LID | LID training | `likely_allowed` (CC-BY-4.0 **[verify]**) |
| `hingcorpus` | L3Cube-HingCorpus (sample) | Hinglish | 52.9M sentences | unlabelled | distillation unlabeled data, variant mining | `likely_allowed` **[verify]** |
| `sentimix20` | SemEval-2020 T9 SentiMix | Hinglish | ~20k | sentiment + LID | aux sentiment head (A6), LID | `likely_allowed` |
| `springer25` | 2025 CNN-transformer 20,201 tweets | Hinglish | 20,201 | 4 | train if released | `to_verify` |
| `healer26` | LREC 2026 Hinglish counselling ERC | Hinglish | — | hierarchical | **exclude from v1** (sensitive mental-health domain) | `excluded` |

Status values: `allowed` · `likely_allowed` (public, license to confirm) · `to_verify` · `requested`
(email sent) · `blocked` · `excluded`. Only `allowed` is fetched automatically.

## 3. Access plan (week 1)
1. For each `to_verify`: find official repo/paper link → record URL, license, citation in YAML.
2. If not public: Claude drafts a polite request email (template below) → **human sends**.
3. Track in `docs/research_log.md` → "Human action needed".

```
Subject: Request for research access to <dataset> (Hinglish emotion)
Dear Dr. <name>, I am a student at <institute> working on Hindi–English code-mixed emotion detection.
Your <paper, year> dataset would be valuable for a non-commercial research benchmark comparing models
across datasets. Could you share access, and confirm the terms (e.g. whether we may release label
mappings and tweet IDs, but not text)? We will cite <paper> and share results with you. Thank you, <name>
```

## 4. Label mapping (initial proposal — confirm after inspecting data)

| Source label | → Unified | Note |
|---|---|---|
| happy / happiness / joy / love | joy | love→joy is lossy; flag `mapped_from_love` |
| sad / sadness | sadness | |
| anger / angry / hatred / hate | anger | hatred→anger flagged; check examples — may be closer to disgust |
| disgust | disgust | |
| fear | fear | |
| surprise | surprise | |
| neutral / others / no emotion | neutral | "others" often = mixed bag → inspect; may drop |
| MaSaC: joy, sadness, anger, fear, disgust, surprise, contempt, neutral | identity; contempt→disgust (flag) | |
| EmoInHindi 16 classes | map subset to Ekman; drop unmappable | document each |
| GoEmotions | official Ekman mapping | |

Mapping is versioned (`mapping_version` in each record). Any change → re-harmonise → new data hash.

## 5. Gold test set sourcing (needs human decision — see "Human action needed")

Requirement: **not from any training source**, diverse registers, recent, legally usable for research.

| Option | Pros | Cons / ToS | Recommendation |
|---|---|---|---|
| A. **Donated messages**: volunteers paste their *own* past messages (consent form; PII scrubbed) | Realistic, consented, chat-like (matches product) | Volunteer bias; slower | ✅ ~40% |
| B. **Elicited writing**: prompts like "Describe a time you felt X, the way you'd text a friend" | Covers rare labels (disgust, surprise) | Less natural; label leakage from prompt → annotators label blind | ✅ ~20% (rare classes) |
| C. **Public comments via official APIs** (e.g. YouTube Data API on Indian vlogs/cricket/movies) | Natural, diverse | API ToS restrict storage/redistribution → keep internal, release IDs only **[verify ToS]** | ✅ ~40% if ToS OK |
| D. Scraping X/Instagram | Natural | ToS risk | ❌ |

All gold items are annotated **blind** (annotators don't see the source/prompt). Target ≥ 40 positives per label.

## 6. Splits & sizes (targets)
- Per source: official splits if present; else 80/10/10 iterative stratification.
- `val` = union of source val portions (+ 10% of silver? **No** — val is human-labelled only).
- Gold: 1,000–1,500 items. Robust set: gold × 8 perturbation families.

## 7. Fallback plan if < 2 Hinglish sources are usable
1. MaSaC (SemEval-2024) utterances as main Hinglish source.
2. BRIGHTER Hindi + GoEmotions as transfer sources (+ transliteration of BRIGHTER Hindi to Roman as augmentation — flag synthetic).
3. Enlarge gold to ~2,000 and use **5-fold cross-validation on gold** for a "fine-tune on small gold" condition, with a separate frozen 500-item final test.
4. Reframe paper toward "transfer + robustness + gold resource".

## 8. Release policy
- Code: MIT. Mapping scripts + record IDs + our labels: CC-BY-4.0.
- Text redistribution **only** where source license allows; otherwise "rehydration" scripts.
- Gold set: release text for donated/elicited items (consent covers it); for API-sourced items release IDs only.
- Datasheet (Gebru et al.) for harmonised set and gold set.

## 9. Privacy handling for collected data
PII scrubbing (phone numbers, emails, @handles, names via NER + manual pass), no usernames stored,
consent records kept separately from text, right-to-withdraw honoured until publication freeze.
