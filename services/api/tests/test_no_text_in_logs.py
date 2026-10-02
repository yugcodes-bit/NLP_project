"""NFR-06: user text must never reach a log line or an error body (docs/17 §2)."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from bhaav_api.logging import REDACTED, JsonFormatter, log_event

CANARY = "zxcanaryqv"
TEXT = f"yaar {CANARY} aaj bahut bura laga"


def records(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        {"event": r.getMessage(), **getattr(r, "fields", {})}
        for r in caplog.records
        if r.name == "bhaav_api"
    ]


def server_logs(caplog: pytest.LogCaptureFixture) -> str:
    """Every in-process log record except those of ``httpx``.

    ``httpx`` is the test's own HTTP client; it logs the URL it calls and does not exist on the
    server. Everything else (our logger, FastAPI, Starlette, ONNX Runtime, …) is server-side.
    """
    return "\n".join(
        f"{r.name} {r.getMessage()} {getattr(r, 'fields', '')}"
        for r in caplog.records
        if r.name != "httpx"
    )


def test_successful_request_logs_metadata_only(
    client: TestClient, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.DEBUG)
    response = client.post("/v1/analyze", json={"text": TEXT})
    assert response.status_code == 200
    assert CANARY in response.json()["text_normalized"]  # the canary really went through

    captured = capfd.readouterr()
    assert CANARY not in server_logs(caplog)
    assert CANARY not in captured.out
    assert CANARY not in captured.err

    request_lines = [r for r in records(caplog) if r["event"] == "request"]
    assert len(request_lines) == 1
    line = request_lines[0]
    assert line["path"] == "/v1/analyze"
    assert line["method"] == "POST"
    assert line["status"] == 200
    assert line["input_chars"] == len(TEXT)
    assert line["mode"] == "server"
    assert line["model_version"] == "bhaav-dummy-0.1.0"
    assert line["request_id"] == response.headers["x-request-id"]
    assert isinstance(line["latency_ms"], int)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"json": {"text": TEXT * 60}},  # too long
        {"json": {"text": {"nested": TEXT}}},  # wrong type
        {"json": {"text": "ok", "options": {"lid": CANARY}}},  # wrong option type
        {
            "content": ('{"text": "' + TEXT).encode(),
            "headers": {"content-type": "application/json"},
        },
    ],
)
def test_rejected_request_leaks_nothing(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
    kwargs: dict[str, object],
) -> None:
    caplog.set_level(logging.DEBUG)
    response = client.post("/v1/analyze", **kwargs)
    assert response.status_code == 422
    assert CANARY not in response.text

    captured = capfd.readouterr()
    assert CANARY not in server_logs(caplog)
    assert CANARY not in captured.out
    assert CANARY not in captured.err
    assert [r["status"] for r in records(caplog) if r["event"] == "request"] == [422]


def test_text_in_the_url_is_not_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.DEBUG)
    assert client.get(f"/v1/{CANARY}").status_code == 404
    assert client.get(f"/v1/health?text={CANARY}").status_code == 200

    captured = capfd.readouterr()
    assert CANARY not in server_logs(caplog)
    assert CANARY not in captured.out
    assert CANARY not in captured.err
    paths = [r["path"] for r in records(caplog) if r["event"] == "request"]
    assert paths == ["unmatched", "/v1/health"]


# ------------------------------------------------------------------ the logger itself


def test_log_event_drops_unknown_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    log_event("request", status=200, text=TEXT, message=TEXT, body=TEXT)
    assert records(caplog) == [{"event": "request", "status": 200}]
    assert CANARY not in caplog.text


def test_log_event_redacts_free_text_in_allowed_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    log_event("request", path=TEXT, error_type="x" * 200, model_version=["list"], status=200)
    assert records(caplog) == [
        {
            "event": "request",
            "path": REDACTED,
            "error_type": REDACTED,
            "model_version": REDACTED,
            "status": 200,
        }
    ]


def test_formatter_emits_one_json_object_and_redacts_the_event_name() -> None:
    def render(message: str, fields: dict[str, object]) -> dict[str, object]:
        record = logging.LogRecord("bhaav_api", logging.INFO, __file__, 1, message, None, None)
        record.fields = fields
        parsed: dict[str, object] = json.loads(JsonFormatter().format(record))
        return parsed

    line = render("request", {"status": 200, "path": "/v1/analyze"})
    assert line["event"] == "request"
    assert line["level"] == "info"
    assert line["status"] == 200
    assert line["path"] == "/v1/analyze"
    assert str(line["ts"]).endswith("Z")
    assert render(TEXT, {})["event"] == REDACTED
