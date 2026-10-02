from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from bhaav.data.registry import (
    DatasetEntry,
    DatasetRegistry,
    DatasetStatus,
    FormatSpec,
    LabelTarget,
    load_registry,
)
from bhaav.schema import LabelSchema

FIXTURES = Path(__file__).parent / "fixtures"

ALLOWED: dict[str, Any] = {
    "name": "x",
    "status": "allowed",
    "url": "https://example.invalid/x",
    "license": "CC-BY-4.0",
    "license_url": "https://example.invalid/x/LICENSE",
    "verified_on": "2026-10-01",
    "approved": "test fixture",
}


def test_real_registry_loads(repo_root: Path, schema: LabelSchema) -> None:
    registry = load_registry(repo_root / "configs" / "datasets.yaml", schema)
    assert "masac24" in registry.datasets
    assert registry.datasets["healer26"].status is DatasetStatus.EXCLUDED
    # Whatever is allowed must carry its licence evidence and a way to fetch it.
    for entry in registry.allowed().values():
        assert entry.license
        assert entry.license_url
        assert entry.verified_on
        assert entry.approved


def test_test_registry_resolves_flagged_and_dropped_labels(schema: LabelSchema) -> None:
    registry = load_registry(FIXTURES / "datasets_test.yaml", schema)
    assert list(registry.allowed()) == ["mini", "mini_intensity"]
    mapping = registry.datasets["mini"].resolved_label_map()
    assert mapping["happy"] == LabelTarget(to="joy")
    assert mapping["love"] == LabelTarget(to="joy", flag="mapped_from_love")
    assert mapping["others"] is None


@pytest.mark.parametrize("missing", ["url", "license", "license_url", "verified_on", "approved"])
def test_allowed_requires_licence_evidence(missing: str) -> None:
    payload = {k: v for k, v in ALLOWED.items() if k != missing}
    with pytest.raises(ValidationError, match="never guess"):
        DatasetEntry.model_validate(payload)


def test_unverified_dataset_needs_no_evidence() -> None:
    entry = DatasetEntry.model_validate({"name": "x", "status": "to_verify"})
    assert entry.status is DatasetStatus.TO_VERIFY


def test_label_map_keys_are_case_insensitive() -> None:
    entry = DatasetEntry.model_validate({**ALLOWED, "label_map": {" Happy ": "joy"}})
    assert entry.resolved_label_map() == {"happy": LabelTarget(to="joy")}


def test_string_label_map_resolves_to_nothing() -> None:
    entry = DatasetEntry.model_validate({**ALLOWED, "label_map": "use official ekman_mapping.json"})
    assert entry.resolved_label_map() == {}


def test_mapping_target_must_be_a_schema_label(schema: LabelSchema) -> None:
    registry = DatasetRegistry.model_validate(
        {
            "mapping_version": "t",
            "datasets": {"x": {**ALLOWED, "label_map": {"happy": "happiness"}}},
        }
    )
    with pytest.raises(ValueError, match="not in the label schema"):
        registry.check_against(schema)


def test_dataset_key_must_be_a_safe_identifier() -> None:
    with pytest.raises(ValidationError, match="dataset keys"):
        DatasetRegistry.model_validate({"mapping_version": "t", "datasets": {"Bad-Key": ALLOWED}})


def test_fetch_url_must_be_https_and_sha_well_formed() -> None:
    with pytest.raises(ValidationError):
        DatasetEntry.model_validate(
            {**ALLOWED, "fetch": {"version": "v", "files": [{"url": "http://x/y", "path": "y"}]}}
        )
    with pytest.raises(ValidationError):
        DatasetEntry.model_validate(
            {
                **ALLOWED,
                "fetch": {
                    "version": "v",
                    "files": [{"url": "https://x/y", "path": "y", "sha256": "abc"}],
                },
            }
        )


def test_format_needs_exactly_one_label_layout() -> None:
    base = {"files": {"a.csv": "train"}, "text_column": "text"}
    with pytest.raises(ValidationError, match="exactly one"):
        FormatSpec.model_validate(base)
    with pytest.raises(ValidationError, match="exactly one"):
        FormatSpec.model_validate({**base, "label_column": "l", "label_columns": {"joy": "joy"}})
    assert FormatSpec.model_validate({**base, "label_column": "l"}).reader == "tabular"
