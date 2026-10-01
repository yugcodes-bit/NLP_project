from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from bhaav.data import harmonize
from bhaav.data.harmonize import HarmonizeError, harmonize_dataset
from bhaav.data.lid import LidModel
from bhaav.data.normalize import Normalizer
from bhaav.data.records import Record, read_jsonl
from bhaav.data.registry import DatasetEntry, load_registry
from bhaav.paths import ProjectPaths
from bhaav.schema import LabelSchema


def run(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer, key: str, **kwargs: Any
) -> tuple[list[Record], harmonize.HarmonizeCounts]:
    registry = load_registry(project.datasets, schema)
    return harmonize_dataset(
        key,
        registry.datasets[key],
        schema=schema,
        mapping_version=registry.mapping_version,
        normalizer=normalizer,
        raw_root=project.raw,
        **kwargs,
    )


def by_source_id(records: list[Record]) -> dict[str | None, Record]:
    return {r.source_id: r for r in records}


def test_single_label_source(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    records, counts = run(project, schema, normalizer, "mini")
    rows = by_source_id(records)

    assert counts.read == 55
    assert counts.dropped_by_mapping == 1  # "others" is mapped to null
    assert counts.written == len(records) == 54
    assert "m50" not in rows

    happy = rows["m02"]
    assert happy.id == "mini-000001"
    assert happy.text == "kya baat hai bhai, maza aa gaya!!"
    assert happy.text_norm == "kya baat hai bhai, maza aa gaya!!"
    assert happy.source == "mini"
    assert happy.source_label == "happy"
    assert happy.label_source == "mapped"
    assert happy.license == "CC0-1.0 (synthetic)"
    assert happy.mapping_version == "test-1"
    assert happy.normalization_version == normalizer.config.version
    # Single-label source without intensity: present but intensity unknown → null.
    assert happy.labels == {**schema.empty_labels(), "joy": None}
    assert happy.active_labels() == {"joy"}
    assert list(happy.labels) == list(schema.labels)


def test_neutral_flags_script_and_shouting(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    rows = by_source_id(run(project, schema, normalizer, "mini")[0])

    assert rows["m42"].labels == {**schema.empty_labels(), "neutral": 1}
    assert rows["m48"].labels["joy"] is None
    assert rows["m48"].flags == ["mapped_from_love"]
    assert rows["m06"].script == "devanagari"
    assert rows["m02"].script == "roman"
    assert rows["m24"].has_caps_shouting
    assert rows["m24"].text_norm.startswith("kitni bakwaas service")
    assert not rows["m02"].has_caps_shouting
    assert rows["m37"].text_norm == "kya!! tu canada ja raha hai??"


def test_auto_split_is_stratified_and_official_split_is_kept(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    records, counts = run(project, schema, normalizer, "mini")
    rows = by_source_id(records)

    assert all(rows[f"x0{i}"].split == "test_in_domain" for i in range(1, 6))
    auto = [r for r in records if r.source_id and r.source_id.startswith("m")]
    sizes = Counter(r.split for r in auto)
    assert len(auto) == 49
    assert 38 <= sizes["train"] <= 40  # 80% of 49 = 39.2
    assert sizes["val"] >= 4
    assert sizes["test_in_domain"] >= 4
    assert counts.splits == Counter(r.split for r in records)
    # Every label keeps at least one training example.
    for label in schema.labels:
        assert any(r.split == "train" and r.labels[label] != 0 for r in auto)


def test_split_is_reproducible_and_seed_dependent(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    first = [r.split for r in run(project, schema, normalizer, "mini", split_seed=1)[0]]
    again = [r.split for r in run(project, schema, normalizer, "mini", split_seed=1)[0]]
    other = [r.split for r in run(project, schema, normalizer, "mini", split_seed=2)[0]]
    assert first == again
    assert first != other


def test_multi_label_intensity_source(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    records, counts = run(project, schema, normalizer, "mini_intensity")
    rows = by_source_id(records)

    assert counts.written == 8
    assert rows["i1"].labels == {**schema.empty_labels(), "joy": 3}
    assert rows["i2"].labels == {**schema.empty_labels(), "fear": 2, "sadness": 1}
    assert rows["i2"].source_label == "fear|sadness"
    assert rows["i4"].labels == {**schema.empty_labels(), "neutral": 1}  # none_active: neutral
    assert rows["i8"].active_labels() == {"joy", "surprise"}
    assert {r.split for r in records} == {"train", "val"}
    assert rows["i7"].split == "val"
    assert all(r.script == "devanagari" for r in records)


def test_lid_model_adds_tags_and_cmi(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer, toy_lid: LidModel
) -> None:
    without = by_source_id(run(project, schema, normalizer, "mini")[0])["m42"]
    assert without.cmi is None
    assert without.lang_tags is None

    tagged = by_source_id(run(project, schema, normalizer, "mini", lid_model=toy_lid)[0])
    meeting = tagged["m42"]  # "meeting 5 baje shift ho gayi hai"
    assert meeting.lang_tags is not None
    assert len(meeting.lang_tags) == 7
    assert meeting.lang_tags[0] == "en"
    assert meeting.lang_tags[1] == "univ"
    assert meeting.cmi is not None
    assert 0.0 < meeting.cmi <= 50.0
    assert tagged["m13"].cmi == 0.0  # all Devanagari


def _entry(project: ProjectPaths, schema: LabelSchema, **format_overrides: Any) -> DatasetEntry:
    base = load_registry(project.datasets, schema).datasets["mini"].model_dump(mode="json")
    base["format"].update(format_overrides)
    return DatasetEntry.model_validate(base)


def test_unmapped_source_label_is_an_error(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    raw = project.raw / "mini" / "mini_extra.jsonl"
    with raw.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "x06", "text": "kuch bhi", "label": "pride"}) + "\n")
        fh.write(json.dumps({"id": "x07", "text": "aur kuch", "label": "pride"}) + "\n")
    with pytest.raises(HarmonizeError, match=r"'pride' ×2.*bump mapping_version"):
        run(project, schema, normalizer, "mini")


def test_missing_file_and_missing_column(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    kwargs: dict[str, Any] = {
        "schema": schema,
        "mapping_version": "t",
        "normalizer": normalizer,
        "raw_root": project.raw,
    }
    with pytest.raises(HarmonizeError, match="column 'body' not found"):
        harmonize_dataset("mini", _entry(project, schema, text_column="body"), **kwargs)
    (project.raw / "mini" / "mini_extra.jsonl").unlink()
    with pytest.raises(HarmonizeError, match="raw file missing"):
        harmonize_dataset("mini", _entry(project, schema), **kwargs)


def test_empty_text_and_unlabelled_rows_are_dropped(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    with (project.raw / "mini" / "mini_extra.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "x06", "text": " \u200b ", "label": "happy"}) + "\n")
        fh.write(json.dumps({"id": "x07", "text": "label missing", "label": ""}) + "\n")
    records, counts = run(project, schema, normalizer, "mini")
    assert counts.dropped_empty_text == 1
    assert counts.dropped_no_label == 1
    assert not {"x06", "x07"} & set(by_source_id(records))


def test_multiple_labels_in_one_column(
    project: ProjectPaths, schema: LabelSchema, normalizer: Normalizer
) -> None:
    with (project.raw / "mini" / "mini_extra.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {"id": "x06", "text": "khush bhi hu aur hairaan bhi", "label": "happy, surprise"}
            )
            + "\n"
        )
        fh.write(
            json.dumps(
                {"id": "x07", "text": "pata nahi kya feel ho raha hai", "label": "neutral,sad"}
            )
            + "\n"
        )
    entry = _entry(project, schema, label_delimiter=",")
    records, _ = harmonize_dataset(
        "mini",
        entry,
        schema=schema,
        mapping_version="t",
        normalizer=normalizer,
        raw_root=project.raw,
    )
    rows = by_source_id(records)
    assert rows["x06"].active_labels() == {"joy", "surprise"}
    # Neutral cannot be combined with an emotion: the emotion wins and the record is flagged.
    assert rows["x07"].active_labels() == {"sadness"}
    assert rows["x07"].flags == ["neutral_with_emotion"]


def test_cli_writes_processed_files_and_summary(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    stale = project.processed / "old_source.jsonl"
    stale.parent.mkdir(parents=True)
    stale.write_text("", encoding="utf-8")
    (project.processed / harmonize.DEDUPE_SUMMARY_NAME).write_text("{}", encoding="utf-8")

    assert harmonize.main([]) == 0
    assert not stale.exists()
    assert not (project.processed / harmonize.DEDUPE_SUMMARY_NAME).exists()
    assert len(list(read_jsonl(project.processed / "mini.jsonl"))) == 54
    assert len(list(read_jsonl(project.processed / "mini_intensity.jsonl"))) == 8

    summary = json.loads((project.processed / harmonize.SUMMARY_NAME).read_text(encoding="utf-8"))
    assert summary["mapping_version"] == "test-1"
    assert summary["lid_model"] is None
    assert summary["datasets"]["mini"]["written"] == 54
    assert summary["datasets"]["mini"]["flags"] == {"mapped_from_love": 2}
    assert len(summary["datasets"]["mini"]["sha256"]) == 64
    assert "cmi and lang_tags will be null" in capsys.readouterr().out


def test_cli_output_is_byte_identical_across_runs(project: ProjectPaths) -> None:
    assert harmonize.main([]) == 0
    first = (project.processed / "mini.jsonl").read_bytes()
    assert harmonize.main([]) == 0
    assert (project.processed / "mini.jsonl").read_bytes() == first
    assert b"\r\n" not in first


def test_cli_rejects_datasets_that_are_not_allowed(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert harmonize.main(["--dataset", "pending"]) == 2
    assert "not allowed" in capsys.readouterr().err


def test_cli_reports_mapping_errors(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    with (project.raw / "mini" / "mini_extra.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "x06", "text": "kuch bhi", "label": "pride"}) + "\n")
    assert harmonize.main(["--dataset", "mini"]) == 1
    assert "'pride'" in capsys.readouterr().err


def test_cli_with_nothing_allowed_is_a_clean_no_op(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    Path(project.datasets).write_text(
        'mapping_version: "t"\ndatasets:\n  pending: {name: x, status: to_verify}\n',
        encoding="utf-8",
    )
    assert harmonize.main([]) == 0
    assert "0 datasets harmonised" in capsys.readouterr().out
