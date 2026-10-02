# Progress Summary (simple English)

Last updated: 2026-10-02. This file is a plain-language status page for the human.
The detailed, append-only record is `docs/research_log.md`.

---

## 1. Where we are

We are in **Phase 1** of the roadmap (`docs/09_phases_and_roadmap.md`): build the repo skeleton and
the data pipeline.

**Phase 1 is almost finished. Three of its four exit conditions are met.** The last one ("CI is
green and the Docker image builds") can only be checked after you push the branch to GitHub.
Section 7 tells you exactly how.

All work is on the git branch `phase-1/scaffold`. Nothing has been pushed to GitHub.

## 2. What is done

| Thing | What it does | Status |
|---|---|---|
| Project setup | One Python workspace with two packages (`ml` and `services/api`), linting, type checking, tests | Done |
| Label schema + dataset registry | Read the config files and refuse broken ones. A dataset cannot be used without licence, licence link, check date and an approval note | Done |
| `fetch` | Downloads only approved datasets and checks every file against a saved checksum | Done, **used on real data** |
| `normalize` | Cleans text: links → `<url>`, mentions → `<user>`, "sooooo" → "soo", hashtags split, emoji kept | Done, 65 example cases pass |
| `lid` + language model | Tags each word as Hindi / English / other and computes the Code-Mixing Index | Done, **trained and measured on real data** |
| `harmonize` | Converts each dataset into our common record format | Done, **3 real datasets** |
| `dedupe` | Removes exact and near-duplicate texts; never deletes the test copy | Done, **removed 1,943 real duplicates** |
| `stats` | Writes `reports/data_stats.md` (numbers only, no dataset text) | Done, **real report committed** |
| Shared-code copier | Keeps the text-cleaning code identical in the pipeline, the API and the website | Done |
| API | `/v1/health`, `/v1/labels`, `/v1/analyze`, running a **random dummy model** | Done, run for real on this PC |
| Website | One "Analyse" page: type text, see emotion bars, intensity, language tags | Done, opened in Chrome (phone and desktop size, light and dark) |
| CI workflow | Runs all the checks and a Docker build on GitHub | Written. **Has never run** |

Check results on this machine:

- Python: **334 tests pass**, lint clean, strict type check clean.
- Website: **48 tests pass**, lint clean, builds to static files (134 kB of JavaScript; limit is 200 kB).
- **Rebuild test:** I cloned the repo into an empty folder and rebuilt everything (downloads,
  language model, reports) in about 3 minutes. The results were identical, byte for byte.

## 3. The real numbers we have so far

Only two kinds of real numbers exist. Both are saved in the repo.

**Data** (`reports/data_stats.md`): 60,110 records read, 1,943 duplicates removed, **58,167 kept**.

| Dataset | Language | Records kept | Used for |
|---|---|---|---|
| BRIGHTER Hindi | Hindi (Devanagari) | 3,660 | extra training data |
| GoEmotions | English | 53,446 | extra training data |
| EmoMix-3L | Bangla-Hindi-English mix | 1,061 | testing only |

**Word-language model** (`experiments/lid_charngram_sentimix_v1`): on the SentiMix test file
(3,000 tweets) it scores **macro-F1 0.8412** (95% range 0.8376 to 0.8449), accuracy 0.8442.
Always guessing the more common language would score 0.5783.

Please read that number carefully:
- It measures agreement with SentiMix's own word tags, and **those tags have mistakes** (names and
  some other words are tagged wrongly). So it is not a clean accuracy.
- It is a small helper model for the "which word is Hindi, which is English" display. **It is not
  the emotion model.**

## 4. What does NOT exist yet

- **No emotion model has been trained.** The website shows random answers from a dummy model, and
  says so on screen.
- **No Hinglish emotion training data.** This is the biggest problem. See section 6.
- **No intensity labels anywhere.** None of the datasets we hold says how strong an emotion is.
- **Docker image never built, CI never run.** Both happen after the branch is pushed.
- "Why?" word highlights and the wellbeing card are Phase 6 and are empty placeholders for now.

## 5. Errors and problems so far

### 5.1 The session stopped in the middle (the "API error")
The assistant's connection dropped while it was writing the API files. This was the coding
assistant itself, not the Bhaav project. Nothing was lost; work continued from where it stopped.

About AI APIs in this project:
- The project code has **not called any AI API** (not Claude, not Gemini).
- An AI API is only needed later, for the **LLM baseline experiments** (Phase 3) and **silver
  data** (Phase 5). **We will use the Gemini API for those**, as you asked.
- The live website will **never** send user text to any AI API. That is a project rule.

### 5.2 Problems found while building (all fixed)
1. **Git was ignoring our own code.** `.gitignore` had `data/`, which hides every folder named
   `data`, including the source folder `ml/src/bhaav/data/`. Fixed, and a test now guards it.
2. **Invisible characters in source files.** Fixed with a repair script; a test now catches it.
3. **The lint tool was skipping the data package** (same cause as 1). Fixed.
4. **A tiny practice model was too weak**, so some tests failed. Fixed, and a stronger test added.
5. **Two mistakes in my own tests** (a wrong count; a privacy test fooled by its own tool). Fixed.
6. **Website:** a fragile way of detecting a cancelled request, and "Neutral Neutral" on screen. Fixed.
7. **Newest test tools need Node 22**; this project uses Node 20. Older compatible versions are used.
8. **Port 3000 was busy** with another project of yours (DepLens), so my first browser check opened
   the wrong site. I did not touch that server; Bhaav was tested on port 3100.
9. **Names masked as `[NAME]` were counted as "shouting"** in one dataset. Fixed.

### 5.3 Mistakes found in the planning documents (corrected)
- The paper cited as "Wadhawan & Fahim 2021" is by **Wadhawan & Aggarwal**.
- HingLID's licence is **non-commercial + share-alike**, not the open licence the plan assumed.
  You chose not to use it; we use SentiMix instead (ADR-009).
- **BRIGHTER Hindi has no intensity labels.** The plan was counting on it for intensity.
- The manual gave two different API ports (8000 and 8080). It is now 8080 everywhere.

### 5.4 A problem found in someone else's data
BRIGHTER Hindi's published validation and test files contain **every sentence twice**
(200 rows are really 100; 2,020 rows are really 1,010). Our duplicate remover caught it.

## 6. The big risk: no Hinglish emotion data

| Dataset | Licence found | Status |
|---|---|---|
| BRIGHTER Hindi | CC-BY-4.0 | **In use** |
| SentiMix 2020 | CC-BY-4.0 | **In use** (word language tags only; it has no emotion labels) |
| GoEmotions | Apache-2.0 | **In use** |
| EmoMix-3L | GPL-3.0 | **In use**, testing only |
| HingLID, HingCorpus | Non-commercial, share-alike | Not used (your decision) |
| MaSaC (SemEval-2024) | **No licence in the repo** | Blocked. E-mail needed |
| Wadhawan & Aggarwal 2021 | **No licence in the repo** | Blocked. E-mail needed |
| Vijay 2018 | Only tweet IDs are public | E-mail needed |
| Ghosh 2023, arXiv 2105.09226 | Not public | E-mail needed |

**What this means:** we have Hindi data and English data, but **no Hinglish emotion data to train
on**. The plan warned about this (risk R1). Two ways forward:
1. **The e-mails work** → we get real Hinglish datasets and follow the main plan.
2. **They do not** → the fallback plan (`docs/12` §7): train on Hindi + English and rely on our own
   hand-labelled Hinglish gold set (Phase 2), made larger.

So **sending the e-mails matters a lot**. It is task B below.

## 7. What you need to do: step by step

### Task A: push the branch to GitHub (5 minutes; needed to finish Phase 1)

1. Open a terminal in the project folder `D:\bhaav-planning-pack\bhaav`.
2. Type: `git status` and check that the first line says `On branch phase-1/scaffold`.
3. Type: `git push -u origin phase-1/scaffold`
   If GitHub asks you to sign in, sign in with your `yugcodes-bit` account.
4. Open https://github.com/yugcodes-bit/NLP_project in your browser.
5. Click the **Actions** tab. You will see a run called **ci** with a yellow dot (running).
6. Wait about 5 to 10 minutes. Each of the 4 jobs turns into a green tick or a red cross.
7. Tell me the result. If anything is red, click it, copy the error text, and paste it to me.
   I will fix it. (Red on the first run is normal; this workflow has never run before.)

Do **not** merge the branch yet. We merge after CI is green.

### Task B: send the 5 e-mails (30 minutes; this decides whether we get Hinglish data)

1. Open `docs/research_log.md` and find the heading **"Draft access e-mails"** (first entry dated
   2026-10-02). There are 5 drafts.
2. For each one, find the author's e-mail address: open the paper link in `configs/datasets.yaml`
   (the `url` or `citation` line of that dataset) and look at the first page of the paper.
   For Vijay 2018 the address is written in the README of their GitHub repo.
3. Copy the draft into a new e-mail. Replace `<name>` with your name and `<institute>` with your
   college. Use your college e-mail address if you have one; authors answer those more often.
4. Send it. Then tell me which ones you sent, and I will mark them `requested`.
5. When someone replies, paste the reply to me (remove anything private). I will record the terms
   and add the dataset.

### Task C: read and accept two short decision notes (10 minutes)

1. Read `docs/adr/ADR-008-workspace-layout-and-shared-code.md` (how the code is organised).
2. Read `docs/adr/ADR-009-lid-training-data-sentimix.md` (why SentiMix instead of HingLID).
3. Tell me "accept ADR-008 and ADR-009", or tell me what to change.

### Task D: optional checks

- **Check my dataset choices.** You asked me to choose, and I approved four datasets. If you want
  to double-check, open the `license_url` of each `allowed` dataset in `configs/datasets.yaml`.
  If you disagree with any, tell me and I will remove it.
- **Install Docker Desktop** (https://www.docker.com/products/docker-desktop/) if you want to build
  the API image on your own PC. Not required: GitHub builds it for us.
- **Turn on automatic checks before each commit:** type `uv run pre-commit install` once.

### Later (not now)

- **Gemini API key, Phase 3:** go to Google AI Studio, create an API key, copy `.env.example` to
  `.env`, and paste the key after `GEMINI_API_KEY=`. Never paste the key in chat. A Gemini app
  subscription alone is not an API key.
- **Phase 2:** find 2 or 3 people fluent in Hindi and English to label the gold test set.
- **Phase 6:** create Google Cloud, Vercel and Hugging Face accounts.

## 8. What I will do next

1. After your push: fix whatever CI and the Docker build report, then close Phase 1 and give you
   the phase summary.
2. Phase 2 preparation that does not need you: write 30 worked labelling examples for you to review.
3. Add each Hinglish dataset as soon as an author replies.

## 9. How to see the website yourself

Open two terminals in the project folder:

```
# terminal 1, once: build the placeholder model
uv run python -m bhaav_api.devtools.dummy_model --out dist/dummy

# terminal 1: start the API
$env:MODEL_DIR = "dist/dummy"; $env:ALLOWED_ORIGINS = "http://localhost:3100"
uv run uvicorn bhaav_api.main:app --port 8080

# terminal 2: start the website (port 3100, because your other project uses 3000)
pnpm --dir apps/web exec next dev --port 3100
```

Then open http://localhost:3100. You will see a yellow "Development build" note: the emotion
answers are random until a real model is trained. The word language tags under the text also come
from a placeholder there, not from the measured model.
