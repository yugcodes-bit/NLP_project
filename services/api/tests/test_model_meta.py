from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from bhaav_api.config import Settings
from bhaav_api.inference.model_meta import ModelMeta
from bhaav_api.inference.pipeline import EmotionPipeline
from bhaav_api.main import create_app


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"labels": ("joy", "neutral", "anger")}, "followed by neutral_label"),
        ({"temperature": (1.0, 1.0)}, "one value per label"),
        ({"temperature": (1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0)}, "must be positive"),
        ({"thresholds": {"joy": 0.5}}, "exactly one entry per label"),
        ({"tau": 1.5}, "less than or equal to 1"),
        ({"max_length": 0}, "greater than 0"),
        ({"surprise_field": 1}, "Extra inputs are not permitted"),
    ],
)
def test_invalid_meta_is_rejected(meta: ModelMeta, change: dict[str, Any], message: str) -> None:
    payload = {**meta.model_dump(), **change}
    with pytest.raises(ValidationError, match=message):
        ModelMeta.model_validate(payload)


def test_threshold_must_be_a_probability(meta: ModelMeta) -> None:
    thresholds = {**meta.thresholds, "joy": 1.0}
    with pytest.raises(ValidationError, match="strictly between 0 and 1"):
        ModelMeta.model_validate({**meta.model_dump(), "thresholds": thresholds})


def test_unexpected_error_returns_a_generic_500_without_details(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(self: EmotionPipeline, text: str) -> None:
        raise RuntimeError(f"model blew up on: {text}")

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        monkeypatch.setattr(EmotionPipeline, "infer", explode)
        response = client.post("/v1/analyze", json={"text": "zxcanaryqv secret text"})

    assert response.status_code == 500
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal error",
        "status": 500,
        "detail": "an unexpected error occurred",
        "code": "INTERNAL",
    }
    assert "zxcanaryqv" not in response.text
