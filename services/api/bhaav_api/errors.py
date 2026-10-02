"""RFC 7807-style error responses (``docs/14_api_contract.md``).

Error bodies never echo request content: validation messages name the field, not its value.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bhaav_api.logging import log_event


class ApiError(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def text_empty() -> ApiError:
    return ApiError(422, "TEXT_EMPTY", "Text is empty", "text must contain at least 1 character")


def text_too_long(limit: int) -> ApiError:
    return ApiError(422, "TEXT_TOO_LONG", "Text too long", f"text must be ≤ {limit} characters")


def model_not_ready() -> ApiError:
    return ApiError(503, "MODEL_NOT_READY", "Model not ready", "the model is not loaded")


def problem(status: int, code: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
        },
        media_type="application/problem+json",
    )


async def handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    request.state.error_code = exc.code
    return problem(exc.status, exc.code, exc.title, exc.detail)


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    request.state.error_code = "INVALID_REQUEST"
    # Location + message only. The default FastAPI body includes the offending input value.
    issues = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}" for error in exc.errors()
    )
    return problem(422, "INVALID_REQUEST", "Invalid request", issues)


async def handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    request.state.error_code = code
    title = {404: "Not found", 405: "Method not allowed"}.get(exc.status_code, "HTTP error")
    return problem(exc.status_code, code, title, title)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Only the exception type: its message could contain user text.
    log_event("unhandled_error", error_type=type(exc).__name__)
    request.state.error_code = "INTERNAL"
    return problem(500, "INTERNAL", "Internal error", "an unexpected error occurred")
