# 15 — Deployment Runbook

Primary: **API → Google Cloud Run**, **Web → Vercel**, **Models → Hugging Face Hub**.
Plan B hosts in §6. Steps marked 👤 need the human (accounts, billing, secrets).

Re-verify free-tier terms on the day you deploy: Cloud Run pricing page, Vercel Hobby limits, HF Hub storage.

---

## 0. Prerequisites
- 👤 GitHub repo (public recommended — required by some free CI/CD tiers).
- 👤 Hugging Face account + org `bhaav` (or user namespace); write token.
- 👤 Google Cloud account; new project `bhaav-prod`; billing account linked (free tier still needs billing on file). **Create a budget alert at US$1** (Billing → Budgets & alerts).
- 👤 Vercel account linked to GitHub.
- Local: Docker, `gcloud` CLI, `uv`, `pnpm`, Node 20.

## 1. Publish model artefacts to HF Hub
```bash
uv run python -m bhaav.export_onnx --run experiments/<final_run> --quantize int8 --out dist/teacher
uv run python -m bhaav.publish --dir dist/teacher --repo bhaav/teacher-onnx --revision v1.0.0
uv run python -m bhaav.publish --dir dist/student --repo bhaav/student-onnx --revision v1.0.0
```
Repo contents: `model_quantized.onnx`, `tokenizer.json`, `config.json`, `model-meta.json`, `README.md` (model card).
Student repo layout must match Transformers.js expectations (`onnx/model_quantized.onnx` + tokenizer/config at root).

## 2. Build & test the API image locally
```bash
cd services/api
docker build --build-arg MODEL_REPO=bhaav/teacher-onnx --build-arg MODEL_REVISION=v1.0.0 -t bhaav-api .
docker run -p 8080:8080 -e PORT=8080 -e ALLOWED_ORIGINS=http://localhost:3000 bhaav-api
curl -s localhost:8080/v1/health
curl -s -X POST localhost:8080/v1/analyze -H 'content-type: application/json' \
  -d '{"text":"kya baat hai bhai, maza aa gaya!!","options":{"explain":true,"lid":true}}' | jq
uv run python scripts/bench_latency.py --url http://localhost:8080 --n 500
```

## 3. Deploy API to Cloud Run (first time, manual)
```bash
gcloud config set project bhaav-prod
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
gcloud artifacts repositories create bhaav --repository-format=docker --location=us-central1
gcloud builds submit services/api --tag us-central1-docker.pkg.dev/bhaav-prod/bhaav/api:v1.0.0
gcloud run deploy bhaav-api \
  --image us-central1-docker.pkg.dev/bhaav-prod/bhaav/api:v1.0.0 \
  --region us-central1 --allow-unauthenticated \
  --cpu 1 --memory 2Gi --concurrency 8 --min-instances 0 --max-instances 3 \
  --cpu-boost --timeout 30 \
  --set-env-vars ALLOWED_ORIGINS=https://bhaav.vercel.app,LOG_LEVEL=info
```
Note the service URL. (Artifact Registry storage has its own small free allowance — delete old images.)

## 4. Automate API deploys (GitHub Actions)
- 👤 Set up **Workload Identity Federation** for GitHub → GCP (no service-account keys). Grant the
  deploy SA: `roles/run.admin`, `roles/artifactregistry.writer`, `roles/iam.serviceAccountUser`.
- `deploy-api.yml` on tag `api-v*`: build → push → deploy → smoke test (`/v1/health`, golden `/v1/analyze`
  comparing labels with `services/api/tests/golden.json`). Roll back with
  `gcloud run services update-traffic bhaav-api --to-revisions <prev>=100`.

## 5. Deploy web to Vercel
1. 👤 Import repo in Vercel → Root directory `apps/web` → Framework Next.js.
2. Env vars: `NEXT_PUBLIC_API_URL=https://<cloud-run-url>`, `NEXT_PUBLIC_STUDENT_REPO=bhaav/student-onnx`, `NEXT_PUBLIC_MODEL_REVISION=v1.0.0`.
3. `next.config` uses `output: 'export'`; security headers via `vercel.json` (CSP, HSTS, Referrer-Policy, Permissions-Policy).
4. Every PR gets a preview URL → Lighthouse CI + Playwright smoke run against it.
5. Update Cloud Run `ALLOWED_ORIGINS` to include the production domain (and optionally `*.vercel.app` previews via regex in app config).

## 6. Plan B / alternatives (same Docker image)
| Host | How | Caveats |
|---|---|---|
| **HF Docker Space** | Create Space (SDK: Docker), push `services/api` + `README.md` with `sdk: docker`, `app_port: 8080` | Creating Docker/Gradio Spaces requires **HF PRO** (per HF docs, 2026); free CPU sleeps after ~48 h idle |
| HF **Static** Space (free) | Host the exported web app (`apps/web/out`) | Works for UI + Privacy Mode only; still needs an API host for Server mode |
| Cloudflare Pages / GitHub Pages | Host `apps/web/out` | Equivalent to Vercel for static export |
| Render / Railway / Fly.io | Deploy Dockerfile | Free tiers change frequently; check RAM ≥ 1 GB and sleep policy **[verify]** |
| Offline demo (viva/exam) | `docker run` API + `npx serve apps/web/out` | No internet needed after images are pulled |

## 7. Post-deploy checklist
- [ ] `/v1/health` OK; golden request labels match
- [ ] Web → API CORS works from production domain only
- [ ] Privacy Mode loads student from HF CDN; network tab shows no text in requests
- [ ] Lighthouse mobile ≥ targets
- [ ] Cloud Run logs contain **no input text** (search logs for a canary phrase you submitted)
- [ ] Budget alert active; max-instances = 3
- [ ] README updated with live URLs and model versions

## 8. Operations
- Monitoring: Cloud Run metrics (latency, instance count, 5xx); free uptime check (Cloud Monitoring or UptimeRobot) on `/v1/health` every 5–15 min — note this keeps an instance warm only briefly; it does not remove cold starts.
- Cost watch: monthly check of billing report; expected ₹0.
- Model update: publish new HF revision → bump `MODEL_REVISION` → tag `api-vX.Y.Z` → web env bump for student.
- Incident: if API down → banner "Server mode is down — switch to Private mode" (web reads `/v1/health` failure).
