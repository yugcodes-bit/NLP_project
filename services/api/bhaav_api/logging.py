"""Structured JSON logging that cannot carry user text (NFR-06, ``docs/06`` §10).

Two guards, both enforced here rather than by convention:

* **Field whitelist** — ``log_event`` drops every field that is not in ``ALLOWED_FIELDS``.
* **Value whitelist** — values must be numbers, booleans, ``None`` or short strings made of a
  conservative character set. Anything else is replaced by ``"<redacted>"``.

There is deliberately no way to log a free-form message with interpolated data.
"""

from __future__ import annotations

import json
import logging
import re
import time

LOGGER_NAME = "bhaav_api"

ALLOWED_FIELDS = frozenset(
    {
        "request_id",
        "method",
        "path",
        "status",
        "latency_ms",
        "input_chars",
        "mode",
        "model_version",
        "error_type",
        "error_code",
    }
)
_SAFE_VALUE_RE = re.compile(r"[A-Za-z0-9_./{}:+-]{0,80}")
REDACTED = "<redacted>"

Scalar = str | int | float | bool | None


def _safe(value: object) -> Scalar:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str) and _SAFE_VALUE_RE.fullmatch(value):
        return value
    return REDACTED


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Scalar] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "event": _safe(record.getMessage()),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, separators=(",", ":"))


def log_event(event: str, *, level: int = logging.INFO, **fields: object) -> None:
    """Emit one structured line. Unknown fields are dropped; unsafe values are redacted."""
    safe = {key: _safe(value) for key, value in fields.items() if key in ALLOWED_FIELDS}
    logging.getLogger(LOGGER_NAME).log(level, event, extra={"fields": safe})


def configure_logging(level: str) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
