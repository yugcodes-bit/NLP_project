# Progress Summary (simple English)

Last updated: 2026-10-02. This file is a plain-language status page for the human.
The detailed, append-only record is `docs/research_log.md`.

---

## 1. Where we are

We are in **Phase 1** of the roadmap (`docs/09_phases_and_roadmap.md`): build the repo skeleton and
the data pipeline. **All the code for Phase 1 is written and tested.** Phase 1 is still *not
finished*, because its exit conditions need real datasets, and no dataset is approved yet.

All work is on the git branch `phase-1/scaffold` (8 commits). Nothing has been pushed to GitHub.

## 2. What is done

| Thing | What it does | Status |
|---|---|---|
| Project setup | One Python workspace with two packages (`ml` and `services/api`), linting, type checking, test config | Done |
| Label schema loader | Reads `configs/label_schema.yaml` and refuses a broken schema | Done |
| Dataset registry loader | Reads `configs/datasets.yaml`. A dataset cannot be marked `allowed` unless its licence, licence link and check date are filled in | Done |
| `fetch` | Downloads only `allowed` datasets and checks each file's checksum | Done, tested with a fake server |
| `normalize` | Cleans text: fixes spacing, turns links into `<url>`, mentions into `<user>`, "sooooo" into "soo", splits hashtags, keeps emoji | Done, 63 example cases pass |
| `lid` | Splits text into words, detects script (Roman / Devanagari / mixed), holds the word-language model, computes the Code-Mixing Index | Done |
| `lid_train` | Trains the small word-language model | Code done. **Not trained on real data** |
| `harmonize` | Converts a dataset into our common record format and makes train / val / test splits | Done, tested on made-up data |
| `dedupe` | Removes exact and near-duplicate texts, and never deletes the test copy | Done |
| `stats` | Writes `reports/data_stats.md` (numbers only, no dataset text) | Done |
| Shared-code copier | Copies the text-cleaning code into the API and website so they always behave the same | Done |
| API | `/v1/health`, `/v1/labels`, `/v1/analyze`, running a **random dummy model** | Done, run for real on this PC |
| Website | One "Analyse" page: type text, see emotion bars, intensity, language tags | Done, opened in Chrome (phone and desktop size, light and dark) |
| CI workflow | Runs lint, type check, tests, web build and a Docker build on GitHub | Written. **Has never run** (branch not pushed) |
| Dataset licence check | Looked up the licence of 11 datasets on their official pages | Done, results below |

Check results on this machine:

- Python: **314 tests pass**, 98% of the code is covered by tests, lint clean, strict type check clean.
- Website: **48 tests pass**, lint clean, builds to static files (134 kB of JavaScript; our limit is 200 kB).

Important: every test uses **made-up (synthetic) sentences** and the API uses a **random model**.
There are **no research numbers** yet: no accuracy, no F1.

## 3. What is NOT done or NOT checked

- **No real data.** Nothing has been downloaded, so `reports/data_stats.md` does not exist yet.
- **The language-tag model has no accuracy number.** It needs an approved dataset first.
- **Docker image never built.** Docker is not installed on this PC. CI will build it.
- **CI never run.** It runs only after the branch is pushed to GitHub.
- "Why?" word highlights and the wellbeing card are **not built yet** (they are Phase 6). The API
  returns empty placeholders for them.

## 4. Errors and problems so far

### 4.1 The session stopped in the middle (the "API error")
The assistant's connection dropped while it was writing the API files. This was the coding
assistant itself, not the Bhaav project. Nothing was lost: all files were already saved, and four
commits were already made. Work continued from the half-written API.

To be clear about AI APIs in this project:
- The project code has **not called any AI API** (not Claude, not Gemini).
- An AI API is only needed later, for the **LLM baseline experiments** (Phase 3) and **silver
  data** (Phase 5). **We will use the Gemini API for those**, as you asked.
- The live website will **never** send user text to any AI API. That is a project rule.

### 4.2 Problems found while building (all fixed)
1. **Git was ignoring our own code.** `.gitignore` had `data/`, which hides every folder named
   `data`, including the source folder `ml/src/bhaav/data/`. The whole data pipeline would have
   been left out of every commit. Now it is `/data/` (top-level folder only), and a test guards it.
2. **Invisible characters in source files.** Special characters such as the zero-width joiner were
   saved as real invisible characters instead of readable codes. The code still worked, but nobody
   could review it. Fixed with a repair script; a test now fails if it happens again.
3. **The lint tool was skipping the data package**, for the same reason as problem 1. After the
   fix it found 9 small style issues, all fixed.
4. **A tiny practice model was too weak**, so some tests failed. Fixed its setting and added a
   stronger test that compares our exported model with scikit-learn directly.
5. **One wrong number in a test.** The code was right; the test was wrong. Fixed the test.
6. **A test was fooled by its own tool.** A privacy test saw user text in a log, but the log
   belonged to the test's own web client, not our server. The test now checks only server logs.
7. **Website bug:** a cancelled request was detected in a fragile way. Fixed.
8. **Website wording:** the neutral label showed "Neutral Neutral". Fixed.
9. **Newest test tools need Node 22**, but this project uses Node 20. Older versions that support
   Node 20 are used instead.
10. **Port 3000 was busy.** Another project of yours (DepLens) is running there, so the browser
    check first opened the wrong site. I did not touch that server; Bhaav was tested on port 3100.

### 4.3 Mistakes found in the planning documents (corrected)
- The paper cited as "Wadhawan & Fahim 2021" is by **Wadhawan & Aggarwal**.
- HingLID's licence is **CC BY-NC-SA** (non-commercial, share-alike), not CC-BY.
- BRIGHTER's **intensity** data does **not include Hindi**, as far as its page shows.
- The manual gave two different API ports (8000 and 8080). It is now 8080 everywhere.

## 5. The big finding: datasets

| Dataset | Licence found | Can we use it? |
|---|---|---|
| BRIGHTER Hindi | CC-BY-4.0 | Yes, after your OK. It is Hindi only (Devanagari), not Hinglish |
| SentiMix 2020 | CC-BY-4.0 | Yes, after your OK. Sentiment + word language tags, **no emotion labels** |
| GoEmotions | Apache-2.0 | Yes, after your OK. English only |
| EmoMix-3L | GPL-3.0 | Yes, after your OK. Testing only |
| HingLID, HingCorpus | CC BY-NC-SA 4.0 | Your decision (non-commercial + share-alike) |
| MaSaC (SemEval-2024) | **No licence in the repo** | Blocked. Need to e-mail the organisers |
| Wadhawan & Aggarwal 2021 | **No licence in the repo** | Blocked. Need to e-mail the authors |
| Vijay 2018 | GPL-3.0, but only tweet IDs | Need to e-mail the authors for the text |
| Ghosh 2023, arXiv 2105.09226 | Not public | Need to e-mail the authors |

**What this means:** today we have **zero usable Hinglish emotion training datasets**. This is the
biggest risk the plan warned about (risk R1). If the e-mails do not get us at least two Hinglish
sources in about two weeks, the plan's fallback applies (`docs/12` §7): train on MaSaC + Hindi +
English transfer data and build a bigger gold set of our own.

Caution: I read these licence pages with an automated tool. Please open each link yourself before
approving. The links are in `configs/datasets.yaml`.

## 6. What we do next

1. **You:** the items in section 7.
2. **Me, once datasets are approved:** write the readers for those datasets, download them, run
   the real pipeline and commit `reports/data_stats.md`.
3. **Me:** train and measure the word-language model on an approved dataset.
4. **Me:** write the TypeScript copy of the text cleaner (needed later for Privacy Mode).
5. Then Phase 2 (gold test set, mostly human work) and Phase 3 (baselines).

## 7. What we need from you

| Need | How |
|---|---|
| Push the branch so CI runs | `git push -u origin phase-1/scaffold` |
| Approve the 4 clearly-licensed datasets | Open the links in `configs/datasets.yaml`, then tell me "allow brighter_hin, sentimix20, goemotions, emomix3l" (or a subset) |
| Decide on HingLID (non-commercial, share-alike) | Say yes or no. If no, we use SentiMix for word language tags |
| Send 5 access e-mails | Drafts are in `docs/research_log.md`, entry of 2026-10-02. Fill in your name and institute |
| Accept ADR-008 | Read `docs/adr/ADR-008-workspace-layout-and-shared-code.md` |
| Gemini API key (Phase 3, not now) | Copy `.env.example` to `.env`, fill in `GEMINI_API_KEY=...`. The key comes from Google AI Studio. Do not paste it in chat |
| Optional | Install Docker Desktop; decide whether to move from Node 20 to Node 22 |

## 8. How to see it yourself

```
uv run python -m bhaav_api.devtools.dummy_model --out dist/dummy
$env:MODEL_DIR = "dist/dummy"; uv run uvicorn bhaav_api.main:app --port 8080
pnpm --dir apps/web exec next dev --port 3100
```

Port 3000 is used by your other project, so the site runs on 3100 here. For that, start the API
with `$env:ALLOWED_ORIGINS = "http://localhost:3100"` set as well. Then open
http://localhost:3100. You will see a yellow "Development build" note: the answers are random
until a real model is trained.
