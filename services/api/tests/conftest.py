"""API test fixtures. The model is the random dummy model, built once per session (docs/17 §3)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bhaav_api.config import Settings
from bhaav_api.devtools.dummy_model import build_dummy_model
from bhaav_api.inference.model_meta import ModelMeta
from bhaav_api.main import create_app


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dummy-model")
    build_dummy_model(out)
    return out


@pytest.fixture
def settings(model_dir: Path) -> Settings:
    return Settings(_env_file=None, model_dir=model_dir, allowed_origins="http://localhost:3000")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def client_without_model(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, model_dir=tmp_path / "missing")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def meta() -> ModelMeta:
    """Hand-written metadata for decision-rule tests: anger and fear have lower thresholds."""
    labels = ("anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral")
    return ModelMeta(
        model_version="test-1.0.0",
        schema_version="1.0",
        labels=labels,
        emotions=labels[:-1],
        neutral_label="neutral",
        neutral_rule="exclusive",
        intensity_scale={"0": "absent", "1": "low", "2": "moderate", "3": "high"},
        temperature=(1.0,) * 7,
        thresholds={**dict.fromkeys(labels, 0.5), "anger": 0.3, "fear": 0.3},
        tau=0.4,
        max_length=128,
        normalization_version="1.0",
        created_at="2026-10-02T00:00:00+00:00",
    )
