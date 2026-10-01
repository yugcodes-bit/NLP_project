# 14 — API Contract (v1)

Base URL: `https://<cloud-run-service>.run.app` (custom domain optional). JSON over HTTPS. UTF-8.
Versioned path prefix `/v1`. OpenAPI auto-generated at `/docs` and `/openapi.json` — must match this doc.

---

## Common
- Request limit: body ≤ 64 KB. Text: 1–1,000 chars after trimming.
- Rate limits (per IP, per instance): `/v1/analyze` 60/min · `/v1/analyze/batch` 10/min. 429 + `Retry-After`.
- Headers returned: `X-Request-Id`, `X-Model-Version`.
- Errors (RFC 7807 style):
```json
{"type":"about:blank","title":"Text too long","status":422,"detail":"text must be ≤ 1000 characters","code":"TEXT_TOO_LONG"}
```
Codes: `TEXT_EMPTY`, `TEXT_TOO_LONG`, `BATCH_TOO_LARGE`, `RATE_LIMITED`, `MODEL_NOT_READY` (503), `INTERNAL` (500).

## GET /v1/health
```json
{"status":"ok","model_version":"bhaav-teacher-1.0.0","uptime_s":1234}
```

## GET /v1/labels
```json
{"labels":["anger","disgust","fear","joy","sadness","surprise","neutral"],
 "intensity_scale":{"0":"absent","1":"low","2":"moderate","3":"high"},
 "schema_version":"1.0"}
```

## POST /v1/analyze
Request
```json
{
  "text": "yaar aaj ka din bahut bekaar tha 😩",
  "options": { "explain": true, "lid": true, "all_scores": true }
}
```
Response 200
```json
{
  "text_normalized": "yaar aaj ka din bahut bekaar tha 😩",
  "script": "roman",
  "emotions": [
    {"label":"sadness","probability":0.82,"active":true,"intensity":3},
    {"label":"anger","probability":0.31,"active":true,"intensity":1}
  ],
  "scores": {"anger":0.31,"disgust":0.04,"fear":0.06,"joy":0.02,"sadness":0.82,"surprise":0.03,"neutral":0.05},
  "top": "sadness",
  "abstained": false,
  "candidates": null,
  "confidence": 0.82,
  "lid": {
    "tokens": [
      {"text":"yaar","lang":"hi"},{"text":"aaj","lang":"hi"},{"text":"ka","lang":"hi"},{"text":"din","lang":"hi"},
      {"text":"bahut","lang":"hi"},{"text":"bekaar","lang":"hi"},{"text":"tha","lang":"hi"},{"text":"😩","lang":"univ"}
    ],
    "cmi": 0.0,
    "lang_share": {"hi":1.0,"en":0.0}
  },
  "explanation": {
    "target": "sadness",
    "method": "occlusion",
    "words": [{"text":"bekaar","score":0.41},{"text":"😩","score":0.22},{"text":"bahut","score":0.08}]
  },
  "wellbeing": {"show": false},
  "model_version": "bhaav-teacher-1.0.0",
  "mode": "server",
  "latency_ms": 94
}
```
Notes
- `emotions` lists only active emotions, sorted by probability; `scores` (if `all_scores`) lists all 7 calibrated probabilities.
- If `abstained: true` → `emotions` = [], `top` = null, `candidates` = top-2 labels with probabilities.
- `intensity` ∈ {1,2,3} for active emotions.
- `explanation` only when `options.explain`; scores are normalised to sum of absolute values = 1; positive = pushes toward target.
- `wellbeing.show` true triggers the client card (`16` §4); the API never returns the matched keywords.

## POST /v1/analyze/batch
Request
```json
{"items":[{"id":"r1","text":"..."},{"id":"r2","text":"..."}],"options":{"explain":false,"lid":false}}
```
- 1–64 items; `id` optional (defaults to index). `explain` is ignored for batch in v1.
Response 200
```json
{"results":[{"id":"r1", "...same fields as /analyze minus explanation..."}],"model_version":"...","latency_ms":540}
```
Per-item validation errors are returned inline: `{"id":"r2","error":{"code":"TEXT_TOO_LONG"}}` (batch still 200).

## POST /v1/feedback  *(later; disabled unless `FEEDBACK_ENABLED=true`)*
```json
{"text":"...","predicted":["sadness"],"corrected":["anger","sadness"],"intensity":{"anger":2},
 "consent":true,"model_version":"..."}
```
→ 201 `{ "stored": true }`. Rejected with 400 if `consent` is not `true`.

## GET /v1/model-card
Returns `model-meta.json` subset: label order, thresholds, temperature, τ, training data summary, metrics on gold (once available), limitations URL.

## Client-side Privacy Mode parity
The browser worker returns the **same JSON shape** with `mode: "browser"`; fields that are not
computed in-browser are `null` (e.g. `explanation` if disabled). The web app consumes one type
(`AnalyzeResult`, Zod schema in `apps/web/lib/api.ts`) for both modes.

## Versioning
Breaking changes → `/v2`. Additive fields allowed in `/v1`. `model_version` follows semver:
major = label schema change, minor = retrained model, patch = threshold/calibration update.
