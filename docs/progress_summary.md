# Progress Summary (simple English)

Last updated: 2026-10-02. This file is a plain-language status page for the human.
The detailed, append-only record is `docs/research_log.md`.

---

## 1. Where we are

We are in **Phase 1** of the roadmap (`docs/09_phases_and_roadmap.md`): build the repo skeleton and
the data pipeline. Phase 1 has 13 tasks. The Python data side is written and tested. The API is
half written. The website and CI are not started.

All work is on the git branch `phase-1/scaffold`. Nothing has been pushed to GitHub yet.

## 2. What is done

| Thing | What it does | Status |
|---|---|---|
| Project setup | One Python workspace with two packages (`ml` and `services/api`), linting, type checking, test config | Done, committed |
| Label schema loader | Reads `configs/label_schema.yaml` and refuses a broken schema | Done, tested |
| Dataset registry loader | Reads `configs/datasets.yaml`. A dataset cannot be marked `allowed` unless its licence, licence link and check date are filled in | Done, tested |
| `fetch` | Downloads only `allowed` datasets and checks each file's checksum | Done, tested with a fake server |
| `normalize` | Cleans text: fixes spacing, turns links into `<url>`, mentions into `<user>`, "sooooo" into "soo", splits hashtags, keeps emoji | Done, 63 example cases pass |
| `lid` | Splits text into words, detects script (Roman / Devanagari / mixed), holds the word-language model, computes the Code-Mixing Index | Done, tested |
| `lid_train` | Trains the small word-language model | Code done. **Not trained on real data yet** |
| `harmonize` | Converts a dataset into our common record format and makes train / val / test splits | Done, tested on made-up data |
| `dedupe` | Removes exact and near-duplicate texts, and never deletes the test copy | Done, tested |
| `stats` | Writes `reports/data_stats.md` (numbers only, no dataset text) | Done, tested |
| Shared-code copier | Copies the text-cleaning code into the API so both always behave the same | Done, tested |
| ADR-008 | Written record of the layout decisions | Draft, needs your OK |

Test results on this machine: **207 tests pass**, lint is clean, strict type check is clean.

Important: every test uses **made-up (synthetic) sentences**. No real dataset has been downloaded
yet, so there are **no research numbers** so far.

## 3. What is half done

The API (`services/api`). Written but not tested or committed yet: settings, error format,
text-free logging, request/response shapes, model metadata, and the decision rules (thresholds,
"neutral" rule, "unsure" rule, intensity).

Still to write for the API: the fake ("dummy") model builder, the model pipeline, the three
endpoints (`/v1/health`, `/v1/labels`, `/v1/analyze`), the Dockerfile, and the tests.

## 4. Errors and problems so far

### 4.1 The session stopped in the middle (the "API error")
The assistant's connection dropped while it was writing the API files. This was the coding
assistant itself, not the Bhaav project. Nothing was lost: all files were already saved on disk,
and four commits were already made. We simply continue from the half-written API.

To be clear about AI APIs in this project:
- The project code has **not called any AI API yet** (not Claude, not Gemini).
- An AI API is only needed later, for the **LLM baseline experiments** (Phase 3) and for
  **silver data** (Phase 5). **We will use the Gemini API for those**, as you asked.
- The live website will **never** send user text to any AI API. That is a project rule.

### 4.2 Problems found while building (all fixed)
1. **Git was ignoring our own code.** `.gitignore` had `data/`, which hides every folder named
   `data`, including the source folder `ml/src/bhaav/data/`. The whole data pipeline would have
   been left out of every commit. Fixed by changing it to `/data/` (only the top-level folder).
   A test now guards this.
2. **Invisible characters in source files.** Special characters such as the zero-width joiner were
   saved as real invisible characters instead of readable codes. The code still worked, but nobody
   could review it. Fixed with a repair script. A test now fails if this happens again.
3. **The lint tool was skipping the data package**, for the same reason as problem 1. After the
   fix it checked the code properly and found 9 small style issues, all fixed.
4. **A tiny test model was too weak.** The practice language model (about 100 words) got some of
   its own training words wrong because of a too-strict setting. Fixed the setting for the test
   model, and added a stronger test that compares our exported model with scikit-learn directly.
5. **One wrong number in a test.** The assistant miscounted letters in a test. The code was right,
   the test was wrong. Fixed the test.

### 4.3 Things missing on this computer
- **Docker is not installed**, so the Docker image cannot be built here. CI will build it.
- `uv` was missing and was installed. Python 3.11 was installed next to your Python 3.12.

## 5. What we do next (in this order)

1. Finish the API: dummy model, pipeline, endpoints, Dockerfile, tests.
2. Build the website skeleton: one "Analyse" page that calls the API and shows the result.
3. Add CI (`.github/workflows/ci.yml`): lint, type check, tests, web build, Docker build.
4. Update the docs, tick the finished roadmap boxes, and write the research-log entry.
5. Check each dataset's licence from its official page and write down what we find.
   **This is the main blocker**: no dataset is `allowed` yet, so the real data cannot be processed.

## 6. What we need from you

| Need | When | How |
|---|---|---|
| Approve datasets | Soon | After step 5 above, read the licence findings and tell me which datasets to mark `allowed` |
| Send access emails | Soon | For datasets that are not public; the drafts will be in `docs/research_log.md` |
| Gemini API key | Phase 3, not now | Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY=...`. Do not paste the key in chat. Note: a Gemini Pro app subscription is not an API key; the key comes from Google AI Studio |
| Push the branch | When you are ready | `git push -u origin phase-1/scaffold` (the assistant will not push without your say) |
| Install Docker Desktop | Optional | Only needed to build and run the API image on your own machine |
| Annotators, accounts, helpline check | Later phases | See "Human action needed" in `docs/research_log.md` |

## 7. Honest notes

- Nothing here is a research result yet. It is plumbing, tested on fake data.
- The language model for word tags has **no accuracy number** until the HingLID dataset is cleared.
- The API will first run a **random dummy model**. Its answers mean nothing; it only lets us build
  and test the website. The website will say so on screen.
