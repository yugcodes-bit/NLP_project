from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from bhaav.schema import LabelSchema, load_label_schema


@pytest.fixture
def raw(repo_root: Path) -> dict[str, Any]:
    with (repo_root / "configs" / "label_schema.yaml").open(encoding="utf-8") as fh:
        loaded: dict[str, Any] = yaml.safe_load(fh)
    return loaded


def test_real_schema_loads(repo_root: Path) -> None:
    schema = load_label_schema(repo_root / "configs" / "label_schema.yaml")
    assert schema.labels == ("anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral")
    assert schema.emotions == schema.labels[:-1]
    assert schema.neutral_label == "neutral"
    assert schema.index("joy") == 3
    assert sorted(schema.intensity.scale) == [0, 1, 2, 3]


def test_empty_labels_is_fresh_and_ordered(schema: LabelSchema) -> None:
    first, second = schema.empty_labels(), schema.empty_labels()
    assert list(first) == list(schema.labels)
    assert set(first.values()) == {0}
    first["joy"] = 3
    assert second["joy"] == 0


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["labels"].append("anger"), "unique"),
        (lambda d: d["emotions"].append("neutral"), "neutral_label must not"),
        (lambda d: d["labels"].reverse(), "followed by neutral_label"),
        (lambda d: d["descriptions"].pop("fear"), "descriptions"),
        (lambda d: d["ui"]["emoji"].pop("joy"), "ui.emoji"),
        (lambda d: d["ui"]["hinglish_name"].update(pride="Garv"), "ui.hinglish_name"),
        (lambda d: d["intensity"]["scale"].pop(3), "levels"),
    ],
)
def test_inconsistent_schema_is_rejected(raw: dict[str, Any], mutate: Any, message: str) -> None:
    broken = copy.deepcopy(raw)
    mutate(broken)
    with pytest.raises(ValidationError, match=message):
        LabelSchema.model_validate(broken)


def test_unknown_field_is_rejected(raw: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LabelSchema.model_validate({**raw, "extra_field": 1})
