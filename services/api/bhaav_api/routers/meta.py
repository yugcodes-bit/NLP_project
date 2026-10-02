"""``GET /v1/health`` and ``GET /v1/labels`` (FR-27)."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from bhaav_api.errors import model_not_ready
from bhaav_api.inference.pipeline import EmotionPipeline
from bhaav_api.schemas import HealthResponse, LabelsResponse

router = APIRouter(prefix="/v1", tags=["meta"])


def get_pipeline(request: Request) -> EmotionPipeline | None:
    pipeline: EmotionPipeline | None = getattr(request.app.state, "pipeline", None)
    return pipeline


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    pipeline = get_pipeline(request)
    return HealthResponse(
        status="ok" if pipeline is not None else "model_not_ready",
        model_version=pipeline.meta.model_version if pipeline is not None else None,
        uptime_s=int(time.monotonic() - request.app.state.started_at),
    )


@router.get("/labels", response_model=LabelsResponse)
def labels(request: Request) -> LabelsResponse:
    pipeline = get_pipeline(request)
    if pipeline is None:
        raise model_not_ready()
    meta = pipeline.meta
    return LabelsResponse(
        labels=list(meta.labels),
        intensity_scale=dict(meta.intensity_scale),
        schema_version=meta.schema_version,
    )
