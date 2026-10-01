"""Shared fixtures. All dataset text used by the tests is synthetic (docs/17 §3)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bhaav.data.lid import LidModel
from bhaav.data.lid_train import train_lid
from bhaav.data.normalize import Normalizer, load_normalization_config
from bhaav.paths import ProjectPaths, find_repo_root
from bhaav.schema import LabelSchema, load_label_schema

FIXTURES = Path(__file__).parent / "fixtures"

HINDI_WORDS = (
    "yaar aaj ka din bahut bekaar tha kya baat hai bhai maza aa gaya nahi mujhe kuch accha "
    "lagta khush dukh gussa darr tension ghar kal abhi raha rahi hoon main tum hum kyun kaise "
    "kab kahan zindagi dost pyaar dil mann samajh bolo suno dekho chalo theek bilkul thoda zyada"
).split()
ENGLISH_WORDS = (
    "the is are was happy sad angry result exam interview office meeting train phone service "
    "order cancel finally trip confirm party promotion school team match report mail class room "
    "number flight boss cabin surprise follow giveaway good bad very really today tomorrow"
).split()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root()


@pytest.fixture(scope="session")
def schema(repo_root: Path) -> LabelSchema:
    return load_label_schema(repo_root / "configs" / "label_schema.yaml")


@pytest.fixture(scope="session")
def normalizer(repo_root: Path) -> Normalizer:
    return Normalizer(load_normalization_config(repo_root / "configs" / "normalization.yaml"))


@pytest.fixture(scope="session")
def lid_pairs() -> list[tuple[str, str]]:
    return [(w, "hi") for w in HINDI_WORDS] + [(w, "en") for w in ENGLISH_WORDS]


@pytest.fixture(scope="session")
def toy_lid(lid_pairs: list[tuple[str, str]]) -> LidModel:
    """A tiny LID model trained on ~100 obvious words. Good enough to tag the fixtures.

    ``c=100``: with so few examples the default regularisation under-fits the training words.
    """
    return train_lid(
        lid_pairs, version="toy", trained_on="test word lists", n_features=1 << 12, c=100.0
    )


@pytest.fixture
def project(tmp_path: Path, repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectPaths:
    """A throwaway repo root: real label/normalisation configs, test registry, synthetic data."""
    configs = tmp_path / "configs"
    configs.mkdir()
    for name in ("label_schema.yaml", "normalization.yaml"):
        shutil.copy(repo_root / "configs" / name, configs / name)
    shutil.copy(FIXTURES / "datasets_test.yaml", configs / "datasets.yaml")

    mini = tmp_path / "data" / "raw" / "mini"
    mini.mkdir(parents=True)
    shutil.copy(FIXTURES / "mini_dataset.jsonl", mini / "mini_dataset.jsonl")
    shutil.copy(FIXTURES / "mini_extra.jsonl", mini / "mini_extra.jsonl")
    intensity = tmp_path / "data" / "raw" / "mini_intensity"
    intensity.mkdir(parents=True)
    shutil.copy(FIXTURES / "mini_intensity_train.csv", intensity / "train.csv")
    shutil.copy(FIXTURES / "mini_intensity_dev.csv", intensity / "dev.csv")

    monkeypatch.setenv("BHAAV_ROOT", str(tmp_path))
    return ProjectPaths(tmp_path)
