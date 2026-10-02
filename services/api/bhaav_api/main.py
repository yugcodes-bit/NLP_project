"""Application factory.

    uv run uvicorn bhaav_api.main:app --reload --port 8000

The app starts even when the model cannot be loaded: ``/v1/health`` then reports
``model_not_ready`` and inference endpoints answer 503, which is easier to diagnose on a host
than a crash loop.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from bhaav_api import __version__
from bhaav_api.config import Settings, get_settings
from bhaav_api.errors import (
    ApiError,
    handle_api_error,
    handle_http_error,
    handle_unexpected_error,
    handle_validation_error,
)
from bhaav_api.inference.pipeline import EmotionPipeline, ModelLoadError
from bhaav_api.logging import configure_logging, log_event
from bhaav_api.routers import analyze, meta

_EXPOSED_HEADERS = ["X-Request-Id", "X-Model-Version"]


def _route_template(request: Request) -> str:
    """The matched route pattern, never the raw URL (a raw path could contain user text)."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            app.state.pipeline = EmotionPipeline.load(
                settings.model_dir, threads=settings.ort_threads
            )
            log_event("model_loaded", model_version=app.state.pipeline.meta.model_version)
        except ModelLoadError as exc:
            app.state.pipeline = None
            log_event("model_load_failed", error_type=type(exc).__name__)
        yield

    app = FastAPI(
        title="Bhaav API",
        version=__version__,
        description="Hinglish emotion detection. Not a medical or psychological diagnostic tool.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.pipeline = None
    app.state.started_at = time.monotonic()

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        pipeline: EmotionPipeline | None = app.state.pipeline
        model_version = pipeline.meta.model_version if pipeline is not None else None
        response.headers["X-Request-Id"] = request_id
        if model_version is not None:
            response.headers["X-Model-Version"] = model_version
        log_event(
            "request",
            request_id=request_id,
            method=request.method,
            path=_route_template(request),
            status=response.status_code,
            latency_ms=round((time.perf_counter() - started) * 1000),
            input_chars=getattr(request.state, "input_chars", None),
            error_code=getattr(request.state, "error_code", None),
            mode="server",
            model_version=model_version,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
        expose_headers=_EXPOSED_HEADERS,
    )

    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

    app.include_router(meta.router)
    app.include_router(analyze.router)
    return app


app = create_app()
