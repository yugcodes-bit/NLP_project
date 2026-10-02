# syntax=docker/dockerfile:1
# Bhaav inference API. Build context: services/api (docs/15_deployment_runbook.md §2).
#
#   docker build -t bhaav-api .                                  # model pulled from the HF Hub
#   docker build --build-arg MODEL_SOURCE=dummy -t bhaav-api .   # random dev model, no network
#
# No torch and no transformers in this image (ADR-001).

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---- dependencies + package into a virtualenv
FROM base AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY bhaav_api ./bhaav_api
RUN python -m venv /opt/venv && /opt/venv/bin/pip install .

# ---- model files (thrown away except for /model)
FROM builder AS model
ARG MODEL_SOURCE=hub
ARG MODEL_REPO=bhaav/teacher-onnx
ARG MODEL_REVISION=v1.0.0
RUN --mount=type=secret,id=hf_token,required=false \
    set -eu; \
    if [ "$MODEL_SOURCE" = "dummy" ]; then \
        /opt/venv/bin/pip install "onnx>=1.16"; \
        /opt/venv/bin/python -m bhaav_api.devtools.dummy_model --out /model; \
    else \
        if [ -f /run/secrets/hf_token ]; then export HF_TOKEN="$(cat /run/secrets/hf_token)"; fi; \
        /opt/venv/bin/python -m bhaav_api.devtools.fetch_model \
            --repo "$MODEL_REPO" --revision "$MODEL_REVISION" --out /model; \
    fi

# ---- runtime
FROM base AS runtime
RUN useradd --create-home --uid 10001 bhaav
COPY --from=builder /opt/venv /opt/venv
COPY --from=model /model /app/model
ENV PATH="/opt/venv/bin:$PATH" \
    MODEL_DIR=/app/model \
    PORT=8080
USER bhaav
WORKDIR /app
EXPOSE 8080
# Our own middleware writes one text-free line per request, so uvicorn's access log (which would
# print raw URLs) stays off.
CMD ["sh", "-c", "exec uvicorn bhaav_api.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
