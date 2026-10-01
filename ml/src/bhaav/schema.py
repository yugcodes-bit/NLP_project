"""Loader and validator for ``configs/label_schema.yaml``, the single source of truth for labels."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

INTENSITY_LEVELS = (0, 1, 2, 3)


class IntensityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scale: dict[int, str]
    head: Literal["coral_ordinal"]
    missing_policy: Literal["mask"]

    @model_validator(mode="after")
    def _check_scale(self) -> Self:
        if tuple(sorted(self.scale)) != INTENSITY_LEVELS:
            raise ValueError(f"intensity.scale must define exactly levels {INTENSITY_LEVELS}")
        return self


class UiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    emoji: dict[str, str]
    hinglish_name: dict[str, str]


class LabelSchema(BaseModel):
    """The label taxonomy. ``labels`` order is the model's output index order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    multi_label: bool
    labels: tuple[str, ...]
    emotions: tuple[str, ...]
    neutral_label: str
    neutral_rule: Literal["exclusive"]
    intensity: IntensityConfig
    descriptions: dict[str, str]
    ui: UiConfig

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("labels must be unique")
        if self.neutral_label in self.emotions:
            raise ValueError("neutral_label must not be listed under emotions")
        if self.labels != (*self.emotions, self.neutral_label):
            raise ValueError(
                "labels must be exactly the emotions (same order) followed by neutral_label"
            )
        expected = set(self.labels)
        for name, mapping in (
            ("descriptions", self.descriptions),
            ("ui.emoji", self.ui.emoji),
            ("ui.hinglish_name", self.ui.hinglish_name),
        ):
            if set(mapping) != expected:
                raise ValueError(f"{name} must have exactly one entry per label")
        return self

    def index(self, label: str) -> int:
        """Position of ``label`` in the model output vector."""
        return self.labels.index(label)

    def empty_labels(self) -> dict[str, int | None]:
        """A fresh all-absent label dict in schema order."""
        return dict.fromkeys(self.labels, 0)


def load_label_schema(path: Path) -> LabelSchema:
    with path.open(encoding="utf-8") as fh:
        return LabelSchema.model_validate(yaml.safe_load(fh))
