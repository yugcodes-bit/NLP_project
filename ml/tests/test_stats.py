from __future__ import annotations

from typing import Any

from bhaav.data.records import Record
from bhaav.data.registry import load_registry
from bhaav.data.stats import render_stats
from bhaav.paths import ProjectPaths
from bhaav.schema import LabelSchema


def record(
    schema: LabelSchema,
    id_: str,
    text: str,
    split: str = "train",
    source: str = "mini",
    **fields: Any,
) -> Record:
    labels = {**schema.empty_labels(), **fields.pop("labels", {"joy": None})}
    payload: dict[str, Any] = {
        "id": id_,
        "text": text,
        "text_norm": text,
        "script": "roman",
        "labels": labels,
        "label_source": "mapped",
        "source": source,
        "source_label": "x",
        "split": split,
        "license": "CC0-1.0 (synthetic)",
        "mapping_version": "test-1",
        "normalization_version": "1.0",
        **fields,
    }
    return Record.model_validate(payload)


def section(report: str, heading: str) -> str:
    return report.split(f"## {heading}")[1].split("\n## ")[0]


def test_counts_are_hand_checkable(project: ProjectPaths, schema: LabelSchema) -> None:
    """Five records; every number below can be read straight off this list."""
    records = [
        record(schema, "a", "aa bb cc", cmi=0.0),
        record(schema, "b", "aa bb", split="val", cmi=25.0, labels={"joy": 2, "surprise": 1}),
        record(schema, "c", "aa", labels={"joy": 0, "neutral": 1}, cmi=50.0),
        record(
            schema,
            "d",
            "आज",
            script="devanagari",
            source="mini_intensity",
            labels={"joy": 0, "fear": 3},
            cmi=60.0,
        ),
        record(
            schema,
            "e",
            "aa बब",
            script="mixed",
            labels={"joy": 0, "anger": None},
            flags=["mapped_from_love"],
            has_caps_shouting=True,
        ),
    ]
    registry = load_registry(project.datasets, schema)
    report = render_stats(
        records,
        schema,
        registry,
        {"normalization_version": "1.0", "split_seed": 2026, "lid_model": "toy"},
        None,
    )

    assert "Records: **5** from **2** source(s)" in report
    assert "**not run yet**" in report
    assert "LID model: toy" in report

    by_source = section(report, "Label counts by source")
    assert "| joy | 2 | 0 | 2 | 40.0% |" in by_source
    assert "| fear | 0 | 1 | 1 | 20.0% |" in by_source
    assert "| neutral | 1 | 0 | 1 | 20.0% |" in by_source
    assert "| disgust | 0 | 0 | 0 | 0.0% |" in by_source

    assert "| joy | 1 | 1 |" in section(report, "Label counts by split")

    cardinality = section(report, "Labels per record")
    assert "| 1 | 4 | 80.0% |" in cardinality
    assert "| 2 | 1 | 20.0% |" in cardinality

    # mini: joy (unknown), joy=2 + surprise=1, anger (unknown) → 4 active emotion labels,
    # 2 of them with a known intensity.
    intensity = section(report, "Intensity coverage")
    assert "| mini | 4 | 2 | 50.0% |" in intensity
    assert "| mini_intensity | 1 | 1 | 100.0% |" in intensity

    script = section(report, "Script")
    assert "| roman | 3 | 60.0% |" in script
    assert "| devanagari | 1 | 20.0% |" in script
    assert "| mixed | 1 | 20.0% |" in script

    # CMI known for 4 records: 0 → [0,10); 25 → [10,30); 50 → [30,50]; 60 → >50.
    cmi = section(report, "Code-Mixing Index")
    for bucket in ("[0, 10)", "[10, 30)", "[30, 50]", "> 50"):
        assert f"| {bucket} | 1 | 25.0% |" in cmi
    assert "CMI available for 4 of 5 records; mean 33.8." in cmi

    # Lengths in characters: 8, 5, 2, 2, 5 → mean 4.4, median 5, max 8.
    assert "| characters | 4.4 | 5 |" in section(report, "Text length")
    flags = section(report, "Flags")
    assert "| mapped_from_love | 1 |" in flags
    assert "| has_caps_shouting | 1 |" in flags


def test_missing_cmi_is_stated_not_invented(project: ProjectPaths, schema: LabelSchema) -> None:
    registry = load_registry(project.datasets, schema)
    report = render_stats([record(schema, "a", "aa bb")], schema, registry)
    assert "Not available: no trained LID model" in section(report, "Code-Mixing Index")


def test_dedupe_summary_is_reported(project: ProjectPaths, schema: LabelSchema) -> None:
    registry = load_registry(project.datasets, schema)
    report = render_stats(
        [record(schema, "a", "aa bb")], schema, registry, None, {"removed": 3, "before": 62}
    )
    assert "Deduplication: 3 of 62 records removed" in report
