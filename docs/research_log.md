# Research Log

Append-only. Newest entry at the **bottom** of "Entries". Never edit or delete past entries — add a
correction entry instead. Format: `### YYYY-MM-DD — <title>` then What / Why / Result / Next.

---

## Human action needed (keep this list current; tick when done)
- [x] Create GitHub repo and push this planning pack (`origin` = github.com/yugcodes-bit/NLP_project, commit `77e3114`)
- [ ] **Push the work branch** so CI can run for the first time: `git push -u origin phase-1/scaffold`
- [ ] **Approve datasets.** Open each `license_url` in `configs/datasets.yaml`, then tell Claude which of
      `brighter_hin`, `sentimix20`, `goemotions`, `emomix3l` to mark `allowed` (licences look clear)
- [ ] **Decide on HingLID / HingCorpus**: they are CC BY-NC-SA 4.0 (non-commercial, share-alike), not
      CC-BY-4.0. OK for this project? If not, LID is trained on SentiMix (CC-BY-4.0) instead
- [ ] **Send the 5 access e-mails** drafted in the 2026-10-02 entry (masac24, wadhawan21, vijay18, ghosh23, cm1589)
- [ ] Accept or change ADR-008 (`docs/adr/`)
- [ ] Decide on Node version: the plan pins Node 20, which is past end-of-life; newest test tools need Node 22+
- [ ] Optional: install Docker Desktop (to build the API image locally) and run `uv run pre-commit install`
- [ ] Phase 3: put a Gemini API key in `.env` as `GEMINI_API_KEY` (from Google AI Studio; not needed before then)
- [ ] Verify dataset availability + licenses (see `configs/datasets.yaml` → `to_verify`); send access emails Claude drafts
- [ ] Decide gold-set sourcing mix (donated / elicited / API comments) — `12` §5; check institutional ethics process
- [ ] Recruit 2–3 annotators (Hindi + English fluent); schedule pilot (Week 2)
- [ ] Create accounts: Hugging Face (org `bhaav`), Google Cloud (billing + US$1 budget alert), Vercel
- [ ] Verify Tele-MANAS helpline numbers for the wellbeing card
- [ ] Pick target venue + note deadline (`11` §4)

## Open questions
1. Which emotion datasets are actually obtainable with research licenses? (blocks Phase 1 exit)
2. Is `hatred` in older datasets closer to anger or disgust? → inspect 100 examples, decide, log.
3. Cloud Run region: `us-central1` (free-tier pricing) vs `asia-south1` (latency) — measure after launch.
4. Should intensity be predicted for sources without intensity via pseudo-labels? (Default: no, masked.)
5. Teacher choice may trade 1–2 F1 for 3× smaller size (HingBERT-family vs XLM-R-family) — define tie-break rule before seeing results: *choose the smaller model if within 1.0 macro-F1 (overlapping CIs).*
6. (2026-10-02) Question 1 is now partly answered — see the 2026-10-02 entry. Still open: will any
   *Hinglish emotion* training source be usable? If not by end of week 2 → fallback plan (`12` §7).
7. (2026-10-02) BRIGHTER Hindi appears to have **no intensity labels** (the intensity dataset card
   does not list Hindi). If confirmed on download, which source trains the intensity head? Candidates:
   EmoInHindi (licence unchecked), other BRIGHTER languages, or intensity only from our gold set.
8. (2026-10-02) Data licences are stricter than planned: GPL-3.0 (vijay18, emomix3l) and CC BY-NC-SA
   (HingLID). README says model weights take "the most restrictive training source" licence. What
   licence can the released model and the public API actually carry? Needs a human decision before training.
9. (2026-10-02) The record schema has three script values (roman / devanagari / mixed). Text in any
   other script (Bengali, Urdu) is currently reported as `roman`. Add a fourth value `other`? It
   changes SRS §5 and the API contract, so it was left as is.
10. (2026-10-02) The API image installs dependencies with lower bounds only (`pip install .`).
    Pin them from `uv.lock` before the first real deploy (Phase 6).

## Entries

### 2026-10-01 — Planning pack created
**What:** Landscape research (datasets, encoders, products, hosting) and full planning documents.
**Why:** Define a practical, deployable, publishable scope before writing code.
**Findings:**
- Hinglish emotion work exists since 2018; datasets are small and use incompatible label sets
  (3/4/6/8/16 classes); most results are single-seed accuracy. → contribution = harmonisation, gold set,
  rigorous comparison, robustness, calibration, deployment.
- L3Cube HingBERT/HingRoBERTa(-Mixed) pretrained on 52.93M real Hinglish sentences (CC-BY-4.0) — prime candidates.
- SemEval-2024 Task 10 (code-mixed ERC, best F1 0.70) and SemEval-2025 Task 11 (multi-label + intensity, includes Hindi) give public data + schema.
- Only 3 "hinglish emotion" models on HF Hub, none documented/benchmarked → product gap is real.
- HF now requires PRO to create Gradio/Docker Spaces → chose Cloud Run (API) + Vercel (web) + HF Hub (artefacts).
- Fine-tuned encoders still beat zero-shot LLMs on emotion classification (Bucher & Martini 2024) → LLM = baseline only.
**Decisions:** ADR-001…006 accepted. Label schema = Ekman-6 + neutral, multi-label, intensity 0–3.
**Next:** Phase 1 — scaffold repo, dataset verification, data pipeline, dummy model, API/web skeletons.

### 2026-10-02 — Phase 1 scaffold: data pipeline, API skeleton, web skeleton, CI; dataset licence check
**What:** Built the Phase 1 code on branch `phase-1/scaffold` (not pushed).
- uv workspace (`ml` → package `bhaav`, `services/api` → package `bhaav_api`), ruff, `mypy --strict`, pytest, pre-commit config, ADR-008.
- Data pipeline: label-schema and dataset-registry loaders, `fetch`, `normalize`, `lid` (+ `lid_train`), `splits`, `harmonize`, `dedupe`, `stats`, and `sync_shared` (copies the shared text code into the API and the web app).
- API: `/v1/health`, `/v1/labels`, `/v1/analyze` on a random dummy ONNX model; decision rules; text-free logging; RFC 7807 errors; Dockerfile.
- Web: Next.js static export with the Analyse page.
- CI workflow (`.github/workflows/ci.yml`).
- Checked dataset licences on their primary pages.

**Why:** Phase 1 goal — a reproducible data foundation and skeleton apps, so product work is never blocked on research.

**Result (engineering checks only — there are no research results yet):**
- Python: 314 tests pass, 98% line+branch coverage, ruff clean, `mypy --strict` clean. Web: 48 tests pass, lint clean, static build 134 kB first-load JS (budget 200 kB).
- Ran for real on this machine: the API under uvicorn (health, analyze, error format) and the built site in Chrome at 390 px and 1280 px, light and dark; the server log contained no request text.
- **Everything above ran on synthetic sentences and a random model.** No real dataset has been fetched; no accuracy, F1 or LID number exists. Nothing in `experiments/`.
- **Not verified:** the Docker image (Docker is not installed here) and the CI workflow (branch not pushed, so it has never run).

**Problems found and fixed:**
1. `.gitignore` had an unanchored `data/`, which ignored the source package `ml/src/bhaav/data/` (git and ruff both skipped it). Now `/data/`; guarded by `test_repo_hygiene.py`.
2. Unicode escapes typed into source files were stored as literal invisible characters (inside regexes too). Restored with a script; a test now rejects invisible characters in source.
3. The web client detected a cancelled request with `instanceof DOMException`, which fails across JavaScript realms; now checks the error name.
4. The newest vitest / jsdom need Node 22+, but the plan pins Node 20; pinned vitest 4, jsdom 29, plugin-react 5.
5. Test-only mistakes: a miscounted n-gram expectation; a toy LID model under-fitted at the default regularisation (fixture now uses `c=100`, and a new test checks the exported model against scikit-learn exactly).

**Decisions made (interpretations of the docs — say if any is wrong):**
- Neutral rule: `neutral` is the answer when no emotion is active, or when it clears its own threshold *and* beats every emotion; otherwise it is suppressed. Never combined with an emotion.
- `confidence` = highest calibrated probability over all 7 labels; abstain when it is below τ.
- Text length is counted in Unicode code points (one emoji = one character), in the API and the UI.
- Normalisation runs to a fixed point so it is idempotent; digits are exempt from the elongation rule; `max_chars` is enforced by callers, not by truncation.
- Dedupe compares a punctuation-free, repeat-collapsed key (so "bahut accha" ≡ "bahut acha!!", the example in `17` §2) before MinHash; emoji stay in the key because they carry the label.
- Local API port is 8080 everywhere (the manual said 8000 in one place and 8080 in another).
- LLM for baselines B5/B6 and silver data: **Gemini API**, at the human's request (2026-10-02). The exact model id must be checked against Google's docs in Phase 3, not guessed. Production still never calls an LLM.

**Dataset licence findings (2026-10-02).** Read through an automated page fetcher; the human should open each link before approving. Full detail in `configs/datasets.yaml` and `docs/12` §2a.
- Clear licence, awaiting go-ahead: `brighter_hin` CC-BY-4.0; `sentimix20` CC-BY-4.0; `goemotions` Apache-2.0 (repository licence); `emomix3l` GPL-3.0 (test-only by the authors' wish).
- Stricter than planned: `hinglid`, `hingcorpus` are CC BY-NC-SA 4.0, not CC-BY-4.0.
- Unclear → `blocked`: `masac24` and `wadhawan21` are public repos with no licence file.
- Text not public: `vijay18` (tweet IDs only), `ghosh23`, `cm1589`.
- Corrections to the planning pack: `wadhawan21` is by Wadhawan & **Aggarwal** (fixed in CLAUDE.md, docs 03/10/12, registry); BRIGHTER's intensity dataset does not list Hindi; BRIGHTER Hindi split sizes on the card differ from the plan.
- **Risk R1 is real:** no Hinglish emotion *training* set is usable today.

Sources:
https://github.com/LCS2-IIITD/EDiReF-SemEval2024 ·
https://github.com/l3cube-pune/code-mixed-nlp ·
https://github.com/GoswamiDhiman/EmoMix-3L ·
https://github.com/google-research/google-research/tree/master/goemotions ·
https://huggingface.co/datasets/brighter-dataset/BRIGHTER-emotion-categories ·
https://huggingface.co/datasets/brighter-dataset/BRIGHTER-emotion-intensities ·
https://github.com/deepanshu1995/Emotion-Prediction ·
https://github.com/anshulwadhawan/emotion_detection ·
https://aclanthology.org/2021.wassa-1.21/ ·
https://arxiv.org/abs/2105.09226 ·
https://zenodo.org/records/3974927

**Draft access e-mails (human sends; fill in name and institute).**

1. *MaSaC / EDiReF organisers (LCS2, IIIT Delhi) — `masac24`*
   Subject: Licence for the EDiReF SemEval-2024 Task 10 data (MaSaC ERC)
   Dear EDiReF organisers, I am a student at <institute> building a non-commercial research benchmark for Hindi–English code-mixed emotion detection. I would like to use the Task A (emotion recognition in conversation) data from github.com/LCS2-IIITD/EDiReF-SemEval2024, at utterance level. The repository has no licence file, so I want to ask before using it: (1) may the data be used for non-commercial research and for training a publicly released model? (2) may we release our label mapping and utterance IDs, without the text? We will cite the task paper and Bedi et al. (2023). Thank you, <name>

2. *Anshul Wadhawan, Akshita Aggarwal — `wadhawan21`*
   Subject: Licence for the dataset of "Towards Emotion Recognition in Hindi-English Code-Mixed Data"
   Dear authors, I am a student at <institute> working on a non-commercial benchmark that compares models across Hinglish emotion datasets. Your WASSA 2021 dataset at github.com/anshulwadhawan/emotion_detection would be valuable, but the repository has no licence. Could you confirm the terms: may we use it for research and model training, and release label mappings and tweet IDs (not text)? We will cite your paper and share our results. Thank you, <name>

3. *Deepanshu Vijay and co-authors — `vijay18`*
   Subject: Request for tweet text — Hindi-English code-mixed emotion corpus (NAACL-SRW 2018)
   Dear Dr. Vijay, I am a student at <institute> working on Hindi–English code-mixed emotion detection. Your repository shares tweet IDs and says the text can be requested by e-mail; most of these tweets can no longer be retrieved. Could you share the annotated text for non-commercial research? We would keep the text private, release only IDs and our label mapping, and cite your paper. Thank you, <name>

4. *Soumitra Ghosh, Asif Ekbal and co-authors — `ghosh23`*
   Subject: Request for the emotion annotations of SentiMix (Knowledge-Based Systems, 2023)
   Dear Dr. Ghosh, I am a student at <institute> working on a non-commercial benchmark for Hinglish emotion detection. Your emotion annotations of the SemEval-2020 SentiMix data would let us compare single-source and multi-source training. Could you share them, and confirm whether we may release label mappings and tweet IDs? We will cite your paper. Thank you, <name>

5. *Divyansh Singh — `cm1589`*
   Subject: Request for the 1,589-sentence Hindi-English emotion corpus (arXiv 2105.09226)
   Dear Mr. Singh, I am a student at <institute> working on Hinglish emotion detection. Your high-agreement corpus (κ = 0.94) with video-comment text would add a register our other sources lack. Could you share it for non-commercial research and tell us the licence terms? We will cite your paper. Thank you, <name>

**Next:**
1. Human: push the branch (first CI run), approve datasets, send the e-mails, decide on HingLID's NC-SA terms.
2. Once approved: pin fetch URLs + checksums; write readers for BRIGHTER (Parquet), SentiMix (word-tagged format), GoEmotions (TSV + Ekman mapping), EmoMix-3L (CSV); run `fetch → harmonize → dedupe → stats` on real data; commit `reports/data_stats.md`.
3. Train and evaluate the word-level LID on an approved LID dataset and record its F1 under `experiments/`.
4. TypeScript port of `normalize` against the 63 shared fixture cases (needed for Privacy Mode and the playground).
5. Small follow-ups: `starlette.testclient` warns that `httpx` support is deprecated in favour of `httpx2` (check before upgrading); check the remaining unverified datasets (`sasidhar20`, `springer25`, `emoinhindi`).
