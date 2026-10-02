"""Readers for the real dataset formats, exercised on small synthetic files in the same layout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from bhaav.data.harmonize import HarmonizeError, harmonize_dataset
from bhaav.data.normalize import Normalizer
from bhaav.data.records import Record
from bhaav.data.registry import DatasetEntry, load_registry
from bhaav.schema import LabelSchema

EVIDENCE: dict[str, Any] = {
    "status": "allowed",
    "url": "https://example.invalid/d",
    "license": "CC0-1.0 (synthetic)",
    "license_url": "https://example.invalid/d/LICENSE",
    "verified_on": "2026-10-02",
    "approved": "test fixture",
}
EKMAN = {
    "anger": ["anger", "annoyance"],
    "joy": ["joy", "amusement", "love"],
    "sadness": ["sadness"],
    "surprise": ["surprise", "curiosity"],
    "fear": ["fear"],
    "disgust": ["disgust"],
}
FINE = [
    "amusement",
    "anger",
    "annoyance",
    "curiosity",
    "joy",
    "love",
    "sadness",
    "surprise",
    "neutral",
]
IDENTITY = {label: label for label in ("anger", "disgust", "fear", "joy", "sadness", "surprise")}


def harmonize(
    key: str, entry: DatasetEntry, raw: Path, schema: LabelSchema, normalizer: Normalizer
) -> dict[str | None, Record]:
    records, _ = harmonize_dataset(
        key, entry, schema=schema, mapping_version="t", normalizer=normalizer, raw_root=raw
    )
    return {r.source_id: r for r in records}


# ------------------------------------------------------------------ GoEmotions


@pytest.fixture
def goemotions(tmp_path: Path) -> tuple[Path, DatasetEntry]:
    folder = tmp_path / "goemotions"
    folder.mkdir()
    (folder / "emotions.txt").write_text("\n".join(FINE) + "\n", encoding="utf-8")
    (folder / "ekman_mapping.json").write_text(json.dumps(EKMAN), encoding="utf-8")
    rows = {
        "train.tsv": [
            ("that was hilarious", "0", "c1"),  # amusement → joy
            ("so annoying and it makes me angry", "1,2", "c2"),  # anger + annoyance → anger once
            ("i love this but why though", "5,3", "c3"),  # love → joy, curiosity → surprise
            ('he said "wow" twice', "7", "c4"),  # a quote character must not break the TSV
        ],
        "dev.tsv": [("the meeting is at five", "8", "c5")],  # neutral
        "test.tsv": [("this is sad", "6", "c6")],
    }
    for name, lines in rows.items():
        (folder / name).write_text(
            "".join("\t".join(line) + "\n" for line in lines), encoding="utf-8"
        )
    entry = DatasetEntry.model_validate(
        {
            **EVIDENCE,
            "name": "synthetic goemotions",
            "label_map": {**IDENTITY, "neutral": "neutral"},
            "format": {
                "reader": "goemotions",
                "file_format": "tsv",
                "files": {"train.tsv": "train", "dev.tsv": "val", "test.tsv": "test_in_domain"},
                "text_column": "0",
                "label_column": "1",
                "id_column": "2",
            },
        }
    )
    return tmp_path, entry


def test_goemotions_folds_fine_emotions_into_ekman_classes(
    goemotions: tuple[Path, DatasetEntry], schema: LabelSchema, normalizer: Normalizer
) -> None:
    raw, entry = goemotions
    rows = harmonize("goemotions", entry, raw, schema, normalizer)

    assert rows["c1"].active_labels() == {"joy"}
    assert rows["c1"].source_label == "amusement"
    assert rows["c1"].labels["joy"] is None  # no intensity in this source

    assert rows["c2"].active_labels() == {"anger"}
    assert rows["c2"].source_label == "anger|annoyance"  # the original labels are kept

    assert rows["c3"].active_labels() == {"joy", "surprise"}
    assert rows["c4"].text == 'he said "wow" twice'
    assert rows["c5"].labels == {**schema.empty_labels(), "neutral": 1}
    assert [rows[c].split for c in ("c1", "c5", "c6")] == ["train", "val", "test_in_domain"]


def test_goemotions_reports_missing_mapping_files_and_bad_rows(
    goemotions: tuple[Path, DatasetEntry], schema: LabelSchema, normalizer: Normalizer
) -> None:
    raw, entry = goemotions
    (raw / "goemotions" / "test.tsv").write_text("only two\tcolumns\n", encoding="utf-8")
    with pytest.raises(HarmonizeError, match="expected 3 columns, got 2"):
        harmonize("goemotions", entry, raw, schema, normalizer)
    (raw / "goemotions" / "ekman_mapping.json").unlink()
    with pytest.raises(HarmonizeError, match=r"ekman_mapping\.json"):
        harmonize("goemotions", entry, raw, schema, normalizer)


def test_goemotions_emotion_missing_from_the_ekman_mapping_is_an_error(
    goemotions: tuple[Path, DatasetEntry], schema: LabelSchema, normalizer: Normalizer
) -> None:
    raw, entry = goemotions
    (raw / "goemotions" / "ekman_mapping.json").write_text(
        json.dumps({k: v for k, v in EKMAN.items() if k != "surprise"}), encoding="utf-8"
    )
    with pytest.raises(HarmonizeError, match="'curiosity'"):
        harmonize("goemotions", entry, raw, schema, normalizer)


# ------------------------------------------------------------------ Parquet (BRIGHTER layout)


def test_parquet_with_binary_emotion_columns(
    tmp_path: Path, schema: LabelSchema, normalizer: Normalizer
) -> None:
    folder = tmp_path / "brighter"
    folder.mkdir()
    table = pa.table(
        {
            "id": ["h1", "h2", "h3"],
            "text": ["आज बहुत खुश हूँ", "डर भी है और दुख भी", "कल बैठक तीन बजे है"],
            "anger": [0, 0, 0],
            "disgust": [0, 0, 0],
            "fear": [0, 1, 0],
            "joy": [1, 0, 0],
            "sadness": [0, 1, 0],
            "surprise": [0, 0, 0],
            "emotions": [["joy"], ["fear", "sadness"], []],
        }
    )
    pq.write_table(table, folder / "train.parquet")
    entry = DatasetEntry.model_validate(
        {
            **EVIDENCE,
            "name": "synthetic brighter",
            "label_map": IDENTITY,
            "format": {
                "file_format": "parquet",
                "files": {"train.parquet": "train"},
                "text_column": "text",
                "id_column": "id",
                "label_columns": IDENTITY,
                "none_active": "neutral",
            },
        }
    )
    rows = harmonize("brighter", entry, tmp_path, schema, normalizer)

    assert rows["h1"].active_labels() == {"joy"}
    assert rows["h1"].labels["joy"] is None  # binary source: present, intensity unknown
    assert rows["h2"].active_labels() == {"fear", "sadness"}
    assert rows["h3"].labels == {**schema.empty_labels(), "neutral": 1}
    assert rows["h1"].script == "devanagari"


# ------------------------------------------------------------------ the real registry


def test_every_allowed_dataset_is_pinned_and_readable(repo_root: Path, schema: LabelSchema) -> None:
    """An allowed dataset must be reproducible: pinned checksums, and a reader that exists."""
    from bhaav.data.harmonize import READERS

    registry = load_registry(repo_root / "configs" / "datasets.yaml", schema)
    assert registry.allowed(), "expected at least one allowed dataset"
    for key, entry in registry.allowed().items():
        assert entry.fetch is not None, key
        assert all(f.sha256 for f in entry.fetch.files), f"{key}: unpinned file"
        if entry.format is not None:
            assert entry.format.reader in READERS, key
            assert isinstance(entry.label_map, dict), key
            assert entry.label_map, key
