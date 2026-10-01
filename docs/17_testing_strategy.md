# 17 — Testing Strategy

Test pyramid tuned for an ML product: lots of fast unit tests, focused model/behavioural tests,
a few end-to-end tests that protect the promises we make to users (privacy, correctness, speed).

---

## 1. Layers

| Layer | Tooling | What | Runs |
|---|---|---|---|
| Unit (Python) | pytest, hypothesis | normalise, LID/CMI, harmonise mappings, dedupe, metrics (hand-computed fixtures), bootstrap, calibration, thresholds, chat-independent utils | every PR |
| Unit (TS) | Vitest | chat parser, CSV handling, postprocess (thresholds/τ/neutral rule), variants, zod schemas | every PR |
| Cross-language parity | pytest + node script | normalisation + variants + postprocess give identical outputs on 200 fixtures | every PR |
| API integration | pytest + httpx (ASGI) with **tiny dummy ONNX** | endpoints, validation errors, batch, rate limit, CORS, headers, **no text in logs** | every PR |
| Model behavioural (CheckList-style) | pytest, real model (marked `slow`) | MFT: clear examples per label; INV: spelling/script variants keep labels; DIR: adding "bahut"/"!!!" doesn't lower intensity; negation ("khush nahi hu" ≠ joy) | nightly + before release |
| Export parity | pytest | ONNX vs PyTorch probs; int8 F1 drop ≤ 1 pt on val | on export |
| Golden responses | pytest | 30 fixed inputs → labels must match `golden.json` (probabilities ± 0.05) | every deploy |
| E2E | Playwright | analyse flow, unsure state, wellbeing card, chat upload (fixture), batch, **Privacy Mode network no-leak** | nightly + preview deploys |
| Performance | `bench_latency.py`, Lighthouse CI, k6 | NFR-01/03/04 | pre-release |
| Security | pip-audit, pnpm audit, trivy (image) | known CVEs | weekly + PR |

## 2. Key test cases to write early
- `test_normalize.py`: elongation, emoji ZWJ sequences, Devanagari matras, mixed script, URLs/mentions, hashtags camel-case.
- `test_cmi.py`: all-Hindi → 0; 50/50 → 50; only emoji → 0; worked example from Gambäck & Das.
- `test_metrics.py`: macro-F1 / Jaccard / ECE on tiny arrays with answers computed by hand in the docstring.
- `test_dedupe.py`: planted near-duplicates ("bahut accha" vs "bahut acha!!") across splits are caught.
- `parser.test.ts`: Android 24h `dd/mm/yy, HH:MM - Name: msg`; iOS `[dd/mm/yy, h:mm:ss AM] Name: msg`; multi-line messages; system messages; `<Media omitted>`; unicode names; RTL marks.
- `privacy-mode.spec.ts`: intercept all requests; type canary text; assert no request URL/body contains it.
- `test_no_text_in_logs.py`: send canary text; assert caplog/stdout has no canary.

## 3. Fixtures
- `ml/tests/fixtures/mini_dataset.jsonl` (50 rows, synthetic, all labels).
- `services/api/tests/assets/dummy.onnx` (random tiny model, same I/O) + `model-meta.json`.
- `apps/web/tests/fixtures/chat_android.txt`, `chat_ios.txt` (synthetic conversations — **never real chats**).

## 4. Coverage & gates
- Coverage ≥ 80% on `services/api` and `ml/src/bhaav/data`, `ml/src/bhaav/metrics`.
- PR cannot merge if: lint/type/test fail, parity fails, golden fails, or bundle size budget exceeded.
