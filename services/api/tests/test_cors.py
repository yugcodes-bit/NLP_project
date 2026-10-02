"""FR-30: CORS is limited to the configured web origin(s)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bhaav_api.config import Settings
from bhaav_api.main import create_app

ALLOWED = "http://localhost:3000"
OTHER = "https://evil.example"


def preflight(client: TestClient, origin: str) -> dict[str, str]:
    response = client.options(
        "/v1/analyze",
        headers={
            "origin": origin,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )
    return dict(response.headers)


def test_allowed_origin_passes_preflight_and_sees_our_headers(client: TestClient) -> None:
    headers = preflight(client, ALLOWED)
    assert headers["access-control-allow-origin"] == ALLOWED
    assert "POST" in headers["access-control-allow-methods"]

    response = client.post("/v1/analyze", json={"text": "ok hai"}, headers={"origin": ALLOWED})
    assert response.headers["access-control-allow-origin"] == ALLOWED
    exposed = response.headers["access-control-expose-headers"]
    assert "X-Request-Id" in exposed
    assert "X-Model-Version" in exposed


def test_error_responses_also_carry_cors_headers(client: TestClient) -> None:
    """Otherwise the browser hides the error body and the UI cannot show a useful message."""
    response = client.post("/v1/analyze", json={"text": ""}, headers={"origin": ALLOWED})
    assert response.status_code == 422
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_other_origin_gets_no_cors_headers(client: TestClient) -> None:
    assert "access-control-allow-origin" not in preflight(client, OTHER)
    response = client.post("/v1/analyze", json={"text": "ok hai"}, headers={"origin": OTHER})
    assert "access-control-allow-origin" not in response.headers


def test_multiple_origins_from_settings(model_dir: Path) -> None:
    settings = Settings(
        _env_file=None,
        model_dir=model_dir,
        allowed_origins="http://localhost:3000, https://bhaav.vercel.app ,",
    )
    assert settings.origins == ["http://localhost:3000", "https://bhaav.vercel.app"]
    with TestClient(create_app(settings)) as client:
        headers = preflight(client, "https://bhaav.vercel.app")
        assert headers["access-control-allow-origin"] == "https://bhaav.vercel.app"
