"""``model-meta.json``: everything post-processing needs, shipped next to the weights.

Server and browser both read this file, so they decide identically (``docs/06`` §7). It is written
by the export step (``docs/08`` §5) — or by ``bhaav_api.devtools.dummy_model`` for development.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

META_FILE = "model-meta.json"


class ModelMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    model_version: str
    #: True for the random-weight development model. Its outputs mean nothing.
    dummy: bool = False
    schema_version: str
    #: Model output order.
    labels: tuple[str, ...]
    #: Labels that carry intensity, in the order of the intensity head.
    emotions: tuple[str, ...]
    neutral_label: str
    neutral_rule: Literal["exclusive"]
    intensity_scale: dict[str, str]
    #: Per-label temperature; calibrated probability = sigmoid(logit / T).
    temperature: tuple[float, ...]
    #: Per-label decision threshold on the calibrated probability.
    thresholds: dict[str, float]
    #: Abstain when the highest calibrated probability is below this.
    tau: float = Field(ge=0.0, le=1.0)
    max_length: int = Field(gt=0)
    normalization_version: str
    created_at: str
    git_sha: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.labels != (*self.emotions, self.neutral_label):
            raise ValueError("labels must be the emotions followed by neutral_label")
        if len(self.temperature) != len(self.labels):
            raise ValueError("temperature needs one value per label")
        if any(t <= 0 for t in self.temperature):
            raise ValueError("temperatures must be positive")
        if set(self.thresholds) != set(self.labels):
            raise ValueError("thresholds needs exactly one entry per label")
        if any(not 0.0 < t < 1.0 for t in self.thresholds.values()):
            raise ValueError("thresholds must be strictly between 0 and 1")
        return self


def load_model_meta(path: Path) -> ModelMeta:
    return ModelMeta.model_validate(json.loads(path.read_text(encoding="utf-8")))
