"""Map every allowed dataset into the unified schema → ``data/processed/<key>.jsonl`` (FR-33).

    uv run python -m bhaav.data.harmonize
    uv run python -m bhaav.data.harmonize --dataset masac24

For each raw row: map source labels through the registry's ``label_map``, normalise the text, tag
script (and language tags + CMI when a trained LID model exists at ``data/interim/lid/``), then
assign splits — official ones where the registry names them, otherwise a stratified 80/10/10.

A source label that is missing from ``label_map`` is an error, not a silent drop: mapping
decisions belong in ``configs/datasets.yaml`` where they are reviewed and versioned.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow.parquet as pq

from bhaav.data.lid import LidModel, script_of, tag_tokens, tokenize
from bhaav.data.lid import code_mixing_index as compute_cmi
from bhaav.data.normalize import Normalizer, load_normalization_config
from bhaav.data.records import Record, sha256_file, write_json, write_jsonl
from bhaav.data.registry import DatasetEntry, FormatSpec, SplitOrAuto, load_registry
from bhaav.data.splits import stratified_split
from bhaav.paths import ProjectPaths
from bhaav.schema import LabelSchema, load_label_schema

SUMMARY_NAME = "harmonize_summary.json"
DEDUPE_SUMMARY_NAME = "dedupe_summary.json"
DEFAULT_SPLIT_SEED = 2026


class HarmonizeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RawRow:
    """One source example before mapping. ``labels`` pairs a source label with its intensity."""

    text: str
    labels: tuple[tuple[str, int | None], ...]
    split: SplitOrAuto
    source_id: str | None = None
    #: The labels as the source wrote them, when a reader has already translated ``labels``
    #: (e.g. GoEmotions' 27 fine emotions → Ekman). Defaults to ``labels`` joined with ``|``.
    source_label: str | None = None


Reader = Callable[[Path, DatasetEntry], Iterator[RawRow]]


def _rows(path: Path, spec: FormatSpec) -> Iterator[dict[str, str]]:
    if not path.is_file():
        raise HarmonizeError(f"raw file missing: {path} (run bhaav.data.fetch first)")
    if spec.file_format == "parquet":
        for record in pq.read_table(path).to_pylist():
            yield {str(k): "" if v is None else str(v) for k, v in record.items()}
        return
    with path.open(encoding=spec.encoding, newline="") as fh:
        if spec.file_format == "jsonl":
            for line in fh:
                if line.strip():
                    yield {str(k): "" if v is None else str(v) for k, v in json.loads(line).items()}
        else:
            delimiter = "\t" if spec.file_format == "tsv" else ","
            for row in csv.DictReader(fh, delimiter=delimiter):
                yield {str(k): v or "" for k, v in row.items()}


def _column(row: dict[str, str], name: str, path: Path) -> str:
    try:
        return row[name]
    except KeyError:
        raise HarmonizeError(f"{path}: column {name!r} not found (have {sorted(row)})") from None


def read_tabular(dataset_dir: Path, entry: DatasetEntry) -> Iterator[RawRow]:
    """Reader for CSV / TSV / JSONL files with one text column and label column(s)."""
    spec = entry.format
    assert spec is not None
    for relative, split in spec.files.items():
        path = dataset_dir / relative
        for row in _rows(path, spec):
            labels: list[tuple[str, int | None]] = []
            if spec.label_column is not None:
                cell = _column(row, spec.label_column, path)
                parts = cell.split(spec.label_delimiter) if spec.label_delimiter else [cell]
                labels = [(part.strip(), None) for part in parts if part.strip()]
            else:
                assert spec.label_columns is not None
                for source_label, column in spec.label_columns.items():
                    cell = _column(row, column, path).strip()
                    value = int(float(cell)) if cell else 0
                    if value > 0:
                        labels.append((source_label, value))
            yield RawRow(
                text=_column(row, spec.text_column, path),
                labels=tuple(labels),
                split=split,
                source_id=_column(row, spec.id_column, path) if spec.id_column else None,
            )


def read_goemotions(dataset_dir: Path, entry: DatasetEntry) -> Iterator[RawRow]:
    """GoEmotions: header-less TSV (text, comma-separated emotion ids, comment id).

    Emotion ids index ``emotions.txt``; the 27 fine emotions are folded into Ekman classes with
    the dataset's own ``ekman_mapping.json``. Both files are fetched and checksum-pinned with
    the data, so the mapping is the official one, not a copy typed into this repo. ``neutral``
    is not in that mapping and passes through under its own name.
    """
    spec = entry.format
    assert spec is not None
    for required in ("emotions.txt", "ekman_mapping.json"):
        if not (dataset_dir / required).is_file():
            raise HarmonizeError(f"raw file missing: {dataset_dir / required}")
    names = (dataset_dir / "emotions.txt").read_text(encoding="utf-8").split()
    ekman: dict[str, list[str]] = json.loads(
        (dataset_dir / "ekman_mapping.json").read_text(encoding="utf-8")
    )
    fine_to_ekman = {fine: coarse for coarse, fines in ekman.items() for fine in fines}

    for relative, split in spec.files.items():
        path = dataset_dir / relative
        if not path.is_file():
            raise HarmonizeError(f"raw file missing: {path} (run bhaav.data.fetch first)")
        with path.open(encoding=spec.encoding, newline="") as fh:
            for number, fields in enumerate(csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)):
                if len(fields) != 3:
                    raise HarmonizeError(
                        f"{path}:{number + 1}: expected 3 columns, got {len(fields)}"
                    )
                text, ids, comment_id = fields
                fine = [names[int(i)] for i in ids.split(",")]
                coarse = dict.fromkeys(fine_to_ekman.get(name, name) for name in fine)
                yield RawRow(
                    text=text,
                    labels=tuple((label, None) for label in coarse),
                    split=split,
                    source_id=comment_id,
                    source_label="|".join(fine),
                )


#: Dataset-specific readers register here as their raw formats are verified.
READERS: dict[str, Reader] = {"tabular": read_tabular, "goemotions": read_goemotions}


@dataclass
class HarmonizeCounts:
    read: int = 0
    written: int = 0
    dropped_empty_text: int = 0
    dropped_no_label: int = 0
    dropped_by_mapping: int = 0
    flags: Counter[str] = field(default_factory=Counter)
    splits: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict[str, object]:
        return {
            "read": self.read,
            "written": self.written,
            "dropped_empty_text": self.dropped_empty_text,
            "dropped_no_label": self.dropped_no_label,
            "dropped_by_mapping": self.dropped_by_mapping,
            "flags": dict(sorted(self.flags.items())),
            "splits": dict(sorted(self.splits.items())),
        }


def harmonize_dataset(
    key: str,
    entry: DatasetEntry,
    *,
    schema: LabelSchema,
    mapping_version: str,
    normalizer: Normalizer,
    raw_root: Path,
    lid_model: LidModel | None = None,
    split_seed: int = DEFAULT_SPLIT_SEED,
) -> tuple[list[Record], HarmonizeCounts]:
    if entry.format is None:
        raise HarmonizeError(f"{key} has no format spec in the registry")
    try:
        reader = READERS[entry.format.reader]
    except KeyError:
        raise HarmonizeError(f"{key}: unknown reader {entry.format.reader!r}") from None

    label_map = entry.resolved_label_map()
    neutral = schema.neutral_label
    counts = HarmonizeCounts()
    unknown: Counter[str] = Counter()
    records: list[Record] = []
    pending_split: list[int] = []

    for index, row in enumerate(reader(raw_root / key, entry)):
        counts.read += 1
        normalized = normalizer(row.text)
        if not normalized.text:
            counts.dropped_empty_text += 1
            continue

        labels = schema.empty_labels()
        flags: list[str] = []
        mapped_any = False
        if not row.labels:
            if entry.format.none_active == "drop":
                counts.dropped_no_label += 1
                continue
            labels[neutral] = 1
            mapped_any = True
        for source_label, intensity in row.labels:
            lookup = source_label.strip().lower()
            if lookup not in label_map:
                unknown[source_label] += 1
                continue
            target = label_map[lookup]
            if target is None:
                continue
            mapped_any = True
            if target.flag:
                flags.append(target.flag)
            if target.to == neutral:
                labels[neutral] = 1
            elif entry.has_intensity and intensity is not None:
                previous = labels[target.to] or 0
                labels[target.to] = max(previous, min(max(intensity, 1), 3))
            else:
                labels[target.to] = None
        if unknown:
            continue  # keep scanning so the error lists every unmapped label at once
        if not mapped_any:
            counts.dropped_by_mapping += 1
            continue
        if labels[neutral] and any(labels[e] != 0 for e in schema.emotions):
            labels[neutral] = 0
            flags.append("neutral_with_emotion")

        raw_tokens = tokenize(normalized.text)
        cmi: float | None = None
        lang_tags: list[str] | None = None
        if lid_model is not None:
            lang_tags = [t.lang for t in tag_tokens(raw_tokens, lid_model)]
            cmi = round(compute_cmi(lang_tags), 2)

        if row.split == "auto":
            pending_split.append(len(records))
        counts.flags.update(flags)
        records.append(
            Record(
                id=f"{key}-{index:06d}",
                text=row.text,
                text_norm=normalized.text,
                script=script_of(raw_tokens),
                labels=labels,
                label_source="mapped",
                source=key,
                source_id=row.source_id,
                source_label=(
                    row.source_label
                    if row.source_label is not None
                    else "|".join(label for label, _ in row.labels)
                ),
                split="train" if row.split == "auto" else row.split,
                cmi=cmi,
                lang_tags=lang_tags,
                license=entry.license or "",
                mapping_version=mapping_version,
                normalization_version=normalizer.config.version,
                has_caps_shouting=normalized.has_caps_shouting,
                flags=sorted(set(flags)),
            )
        )

    if unknown:
        listing = ", ".join(f"{label!r} ×{n}" for label, n in unknown.most_common())
        raise HarmonizeError(
            f"{key}: source labels with no entry in label_map: {listing}. Add each to "
            "configs/datasets.yaml (map it, or set it to null to drop it) and bump mapping_version."
        )

    if pending_split:
        assigned = stratified_split(
            [records[i].active_labels() for i in pending_split], seed=split_seed
        )
        for position, split in zip(pending_split, assigned, strict=True):
            records[position] = records[position].model_copy(update={"split": split})

    counts.written = len(records)
    counts.splits.update(record.split for record in records)
    return records, counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bhaav.data.harmonize", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--dataset", nargs="+", metavar="KEY", help="only these datasets")
    parser.add_argument("--seed", type=int, default=DEFAULT_SPLIT_SEED, help="split seed")
    args = parser.parse_args(argv)

    paths = ProjectPaths.discover()
    schema = load_label_schema(paths.label_schema)
    registry = load_registry(paths.datasets, schema)
    normalizer = Normalizer(load_normalization_config(paths.normalization))
    lid_model = LidModel.load(paths.lid_model) if paths.lid_model.is_file() else None
    if lid_model is None:
        print("no LID model at data/interim/lid/ — cmi and lang_tags will be null")

    candidates = {k: v for k, v in registry.allowed().items() if v.format is not None}
    if args.dataset:
        missing = [k for k in args.dataset if k not in candidates]
        if missing:
            print(f"not allowed or no format spec: {', '.join(missing)}", file=sys.stderr)
            return 2
        candidates = {k: candidates[k] for k in args.dataset}
    else:
        for stale in paths.processed.glob("*.jsonl"):
            stale.unlink()
    # Any harmonise run invalidates a previous dedupe (ADR-008).
    (paths.processed / DEDUPE_SUMMARY_NAME).unlink(missing_ok=True)

    summary: dict[str, object] = {}
    for key, entry in candidates.items():
        try:
            records, counts = harmonize_dataset(
                key,
                entry,
                schema=schema,
                mapping_version=registry.mapping_version,
                normalizer=normalizer,
                raw_root=paths.raw,
                lid_model=lid_model,
                split_seed=args.seed,
            )
        except HarmonizeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        out = paths.processed / f"{key}.jsonl"
        write_jsonl(out, records)
        summary[key] = {**counts.to_dict(), "sha256": sha256_file(out)}
        print(f"[{key}] read {counts.read}, wrote {counts.written} → {out.relative_to(paths.root)}")

    write_json(
        paths.processed / SUMMARY_NAME,
        {
            "mapping_version": registry.mapping_version,
            "normalization_version": normalizer.config.version,
            "schema_version": schema.schema_version,
            "split_seed": args.seed,
            "lid_model": lid_model.version if lid_model else None,
            "datasets": summary,
        },
    )
    if not summary:
        print(
            "0 datasets harmonised: nothing in configs/datasets.yaml is both 'allowed' and has a "
            "format spec yet."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
