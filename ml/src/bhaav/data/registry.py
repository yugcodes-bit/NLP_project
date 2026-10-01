"""Typed loader for the dataset registry (``configs/datasets.yaml``).

The registry is where licence decisions live. Two rules are enforced here rather than left to
convention (``CLAUDE.md`` §3, "Respect dataset licenses"):

* only ``status: allowed`` datasets are ever fetched or harmonised, and
* a dataset cannot be ``allowed`` without a URL, a licence, the page that states the licence and
  the date it was checked.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

import regex
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bhaav.schema import LabelSchema

Split = Literal["train", "val", "test_in_domain", "ood_eval"]
SplitOrAuto = Literal["train", "val", "test_in_domain", "ood_eval", "auto"]

_KEY_RE = regex.compile(r"[a-z][a-z0-9_]*")


class DatasetStatus(StrEnum):
    ALLOWED = "allowed"
    LIKELY_ALLOWED = "likely_allowed"
    TO_VERIFY = "to_verify"
    REQUESTED = "requested"
    BLOCKED = "blocked"
    EXCLUDED = "excluded"


class LabelTarget(BaseModel):
    """A mapping with a caveat, e.g. ``contempt: {to: disgust, flag: mapped_from_contempt}``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    to: str
    flag: str | None = None


class FetchFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(pattern=r"^https://")
    #: Destination relative to ``data/raw/<dataset>/``.
    path: str
    #: Pin after the first fetch. ``null`` means "record what we got" (reported as unpinned).
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class FetchSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    #: Immutable upstream version: git commit, HF revision, DOI or release tag.
    version: str
    files: list[FetchFile] = Field(min_length=1)


class FormatSpec(BaseModel):
    """How ``harmonize`` reads the raw files of a labelled dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reader: str = "tabular"
    file_format: Literal["csv", "tsv", "jsonl"] = "csv"
    encoding: str = "utf-8"
    #: Raw file (relative to ``data/raw/<dataset>/``) → official split, or ``auto`` for a
    #: stratified 80/10/10 split.
    files: dict[str, SplitOrAuto] = Field(min_length=1)
    text_column: str
    id_column: str | None = None
    #: Single column holding the label (or several, separated by ``label_delimiter``).
    label_column: str | None = None
    label_delimiter: str | None = None
    #: Source label → column holding 0/1 or an intensity. Alternative to ``label_column``.
    label_columns: dict[str, str] | None = None
    #: What a row with no active label column means.
    none_active: Literal["neutral", "drop"] = "drop"

    @model_validator(mode="after")
    def _one_label_layout(self) -> Self:
        if (self.label_column is None) == (self.label_columns is None):
            raise ValueError("set exactly one of label_column / label_columns")
        return self


class DatasetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: DatasetStatus
    url: str | None = None
    license: str | None = None
    #: The primary-source page that states the licence.
    license_url: str | None = None
    citation: str | None = None
    verified_on: dt.date | None = None
    script: str | None = None
    roles: tuple[str, ...] = ()
    has_intensity: bool = False
    #: Source label → unified label, ``{to, flag}``, or ``null`` to drop that label.
    #: A string (not a mapping) is a note that a dedicated reader handles the mapping.
    label_map: dict[str, str | LabelTarget | None] | str | None = None
    notes: str = ""
    fetch: FetchSpec | None = None
    format: FormatSpec | None = None

    @model_validator(mode="after")
    def _allowed_needs_evidence(self) -> Self:
        if self.status is DatasetStatus.ALLOWED:
            missing = [
                name
                for name in ("url", "license", "license_url", "verified_on")
                if not getattr(self, name)
            ]
            if missing:
                raise ValueError(
                    f"status 'allowed' requires {', '.join(missing)} — verify from the primary "
                    "source first, never guess"
                )
        return self

    def resolved_label_map(self) -> dict[str, LabelTarget | None]:
        """Label map with lower-cased keys and every target as a ``LabelTarget`` (or ``None``)."""
        if not isinstance(self.label_map, dict):
            return {}
        resolved: dict[str, LabelTarget | None] = {}
        for source_label, target in self.label_map.items():
            key = str(source_label).strip().lower()
            resolved[key] = LabelTarget(to=target) if isinstance(target, str) else target
        return resolved


class DatasetRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mapping_version: str
    datasets: dict[str, DatasetEntry]

    @model_validator(mode="after")
    def _check_keys(self) -> Self:
        bad = [key for key in self.datasets if _KEY_RE.fullmatch(key) is None]
        if bad:
            raise ValueError(f"dataset keys must match {_KEY_RE.pattern}: {bad}")
        return self

    def allowed(self) -> dict[str, DatasetEntry]:
        """Datasets cleared for automatic fetching, in registry order."""
        return {k: v for k, v in self.datasets.items() if v.status is DatasetStatus.ALLOWED}

    def check_against(self, schema: LabelSchema) -> None:
        """Every mapping target must be a label of the unified schema."""
        for key, entry in self.datasets.items():
            for source_label, target in entry.resolved_label_map().items():
                if target is not None and target.to not in schema.labels:
                    raise ValueError(
                        f"datasets.{key}.label_map[{source_label!r}] → {target.to!r} is not in "
                        f"the label schema {list(schema.labels)}"
                    )


def load_registry(path: Path, schema: LabelSchema) -> DatasetRegistry:
    with path.open(encoding="utf-8") as fh:
        registry = DatasetRegistry.model_validate(yaml.safe_load(fh))
    registry.check_against(schema)
    return registry
