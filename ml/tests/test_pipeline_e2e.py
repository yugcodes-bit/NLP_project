"""harmonize → dedupe → stats on synthetic sources, through the real CLIs (Phase 1 exit)."""

from __future__ import annotations

import json

import pytest

from bhaav.data import dedupe, harmonize, stats
from bhaav.data.records import read_jsonl
from bhaav.paths import ProjectPaths


def ids(project: ProjectPaths, name: str) -> set[str | None]:
    return {r.source_id for r in read_jsonl(project.processed / f"{name}.jsonl")}


def test_pipeline_end_to_end(project: ProjectPaths, capsys: pytest.CaptureFixture[str]) -> None:
    assert harmonize.main([]) == 0
    assert dedupe.main([]) == 0
    assert stats.main([]) == 0
    out = capsys.readouterr().out
    assert "removed 3 of 62 records" in out
    assert "wrote reports" in out

    # Each planted pair lost exactly one member; the unrelated rows are untouched.
    kept = ids(project, "mini")
    assert len(kept) == 51
    assert len(kept & {"m09", "x01"}) == 1  # exact duplicate after normalisation
    assert len(kept & {"m02", "x02"}) == 1  # differs only in punctuation / elongation
    assert len(kept & {"m17", "x03"}) == 1  # near-duplicate (one extra word)
    assert {"x04", "x05"} <= kept
    assert len(ids(project, "mini_intensity")) == 8

    summary = json.loads((project.processed / "dedupe_summary.json").read_text(encoding="utf-8"))
    assert summary["before"] == 62
    assert summary["removed"] == 3
    assert summary["removed_by_tier"] == {"exact": 1, "near": 1, "punct_insensitive": 1}
    assert summary["removed_by_source"] == {"mini": 3}
    assert summary["label_conflicts"] == 1  # m17 is "angry", its near-duplicate x03 is "sad"

    removed = [
        json.loads(line)
        for line in (project.interim / "dedupe_removed.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(removed) == 3
    # A copy in the official test split is never the one removed in favour of a train copy.
    assert all(not (r["split"] == "test_in_domain" and r["kept_split"] == "train") for r in removed)


def test_reports_contain_numbers_but_no_dataset_text(project: ProjectPaths) -> None:
    assert harmonize.main([]) == 0
    assert dedupe.main([]) == 0
    assert stats.main([]) == 0

    dedupe_report = (project.reports / "dedupe_report.md").read_text(encoding="utf-8")
    stats_report = (project.reports / "data_stats.md").read_text(encoding="utf-8")
    assert "Removed: **3** (4.84%)" in dedupe_report
    assert "| punct_insensitive | 1 |" in dedupe_report
    assert "Records: **59** from **2** source(s)" in stats_report
    assert "Deduplication: 3 of 62 records removed" in stats_report

    texts = [
        r.text_norm
        for name in ("mini", "mini_intensity")
        for r in read_jsonl(project.processed / f"{name}.jsonl")
    ]
    for report in (dedupe_report, stats_report):
        assert not any(text in report for text in texts)


def test_dedupe_is_idempotent(project: ProjectPaths, capsys: pytest.CaptureFixture[str]) -> None:
    assert harmonize.main([]) == 0
    assert dedupe.main([]) == 0
    report = (project.reports / "dedupe_report.md").read_bytes()
    data = (project.processed / "mini.jsonl").read_bytes()
    capsys.readouterr()

    assert dedupe.main([]) == 0
    assert "already deduplicated" in capsys.readouterr().out
    assert (project.reports / "dedupe_report.md").read_bytes() == report
    assert (project.processed / "mini.jsonl").read_bytes() == data

    # --force re-runs on the already-clean data and finds nothing more to remove.
    assert dedupe.main(["--force"]) == 0
    assert "removed 0 of 59 records" in capsys.readouterr().out
    assert (project.processed / "mini.jsonl").read_bytes() == data


def test_harmonize_resets_dedupe_state(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert harmonize.main([]) == 0
    assert dedupe.main([]) == 0
    assert harmonize.main([]) == 0
    capsys.readouterr()
    assert dedupe.main([]) == 0
    assert "removed 3 of 62 records" in capsys.readouterr().out


def test_protected_file_removes_matching_training_rows(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert harmonize.main([]) == 0
    gold = project.root / "gold_fixture.jsonl"
    gold.write_text(
        json.dumps({"id": "gold-1", "text_norm": "meeting 5 baje shift ho gayi hai!"}) + "\n",
        encoding="utf-8",
    )
    assert dedupe.main(["--protect", str(gold)]) == 0
    assert "removed 4 of 62 records" in capsys.readouterr().out
    assert "m42" not in ids(project, "mini")
    summary = json.loads((project.processed / "dedupe_summary.json").read_text(encoding="utf-8"))
    assert summary["protected"] == 1


def test_dedupe_and_stats_without_data(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert dedupe.main([]) == 0
    assert "nothing to deduplicate" in capsys.readouterr().out
    assert stats.main([]) == 0
    report = (project.reports / "data_stats.md").read_text(encoding="utf-8")
    assert "Records: **0**" in report
    assert "No harmonised data yet" in report
