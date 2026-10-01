"""The unified record of ``data/processed/*.jsonl`` (``docs/05_srs.md`` §5) and JSONL I/O."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from bhaav.data.lid import Script
from bhaav.data.registry import Split

LabelSource = Literal["gold", "mapped", "silver"]


class Record(BaseModel):
    """One harmonised example.

    ``labels`` holds every label of the schema, in schema order:

    * ``0`` — absent
    * ``1``–``3`` — present with that intensity
    * ``null`` — present, intensity unknown (source has no intensity; masked in the intensity loss)

    ``neutral`` carries no intensity and is always ``0`` or ``1``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    text_norm: str
    script: Script
    labels: dict[str, int | None]
    label_source: LabelSource
    source: str
    source_id: str | None = None
    source_label: str
    split: Split
    cmi: float | None = None
    lang_tags: list[str] | None = None
    license: str
    mapping_version: str
    normalization_version: str
    has_caps_shouting: bool = False
    flags: list[str] = []
    notes: str = ""

    def active_labels(self) -> frozenset[str]:
        return frozenset(label for label, value in self.labels.items() if value != 0)


def read_jsonl(path: Path) -> Iterator[Record]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield Record.model_validate_json(line)


def write_jsonl(path: Path, records: Iterable[Record]) -> int:
    """Write atomically (temp file + rename) with LF newlines. Returns the number of records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False))
            fh.write("\n")
            count += 1
    os.replace(tmp, path)
    return count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_bytes(text.encode("utf-8"))
