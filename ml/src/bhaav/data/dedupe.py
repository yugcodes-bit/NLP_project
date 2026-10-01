"""Remove exact and near-duplicate texts across sources and splits (FR-34, ``docs/08`` §2.4).

    uv run python -m bhaav.data.dedupe

Three tiers, each catching what the previous one misses:

1. **exact** — identical normalised text
2. **punct_insensitive** — identical after dropping punctuation and collapsing every repeated
   character ("bahut accha" ≡ "bahut acha!!")
3. **near** — MinHash LSH over character 5-grams of that key, confirmed by exact Jaccard ≥ 0.8

Within a duplicate cluster one record survives, chosen so that evaluation data is never the copy
that gets deleted: protected (gold) > test_in_domain / ood_eval > val > train, then source name.

``data/processed/*.jsonl`` is rewritten in place. ``dedupe_summary.json`` stores the output
hashes, so a second run is a no-op instead of overwriting the report with zeros (ADR-008).
Removed records are kept in ``data/interim/dedupe_removed.jsonl`` for audit.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import regex
from datasketch import MinHash, MinHashLSH

from bhaav.data.harmonize import DEDUPE_SUMMARY_NAME
from bhaav.data.records import Record, read_jsonl, sha256_file, write_json, write_jsonl
from bhaav.paths import ProjectPaths

Tier = Literal["exact", "punct_insensitive", "near"]

DEFAULT_THRESHOLD = 0.8
NUM_PERM = 128
SHINGLE_SIZE = 5
REPORT_NAME = "dedupe_report.md"
REMOVED_NAME = "dedupe_removed.jsonl"

_SPLIT_RANK = {"gold": 0, "test_in_domain": 1, "ood_eval": 1, "val": 2, "train": 3}
_PLACEHOLDER_RE = regex.compile(r"<[a-z]+>")
_NOT_CONTENT_RE = regex.compile(r"[^\p{L}\p{M}\p{N}\p{Extended_Pictographic} ]+")
_REPEAT_RE = regex.compile(r"(.)\1+")
_SPACES_RE = regex.compile(r" +")


def dedupe_key(text_norm: str) -> str:
    """Aggressive comparison key: no placeholders or punctuation, no repeated characters.

    Emoji stay because they carry the label ("maza aa gaya 😂" vs "maza aa gaya 😢").
    """
    key = _PLACEHOLDER_RE.sub(" ", text_norm)
    key = _NOT_CONTENT_RE.sub(" ", key)
    key = _REPEAT_RE.sub(r"\1", key)
    key = _SPACES_RE.sub(" ", key).strip()
    return key or text_norm


def shingles(key: str, size: int = SHINGLE_SIZE) -> frozenset[str]:
    if len(key) <= size:
        return frozenset({key})
    return frozenset(key[i : i + size] for i in range(len(key) - size + 1))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 1.0


@dataclass(frozen=True)
class Item:
    """The slice of a record that dedupe needs."""

    id: str
    source: str
    split: str
    text_norm: str
    labels: frozenset[str]
    source_rank: int = 0
    protected: bool = False

    @property
    def priority(self) -> tuple[int, int, str]:
        return (_SPLIT_RANK.get(self.split, 9), self.source_rank, self.id)


@dataclass(frozen=True)
class Removal:
    id: str
    source: str
    split: str
    kept_id: str
    kept_source: str
    kept_split: str
    tier: Tier
    jaccard: float
    label_conflict: bool


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[max(root_a, root_b)] = min(root_a, root_b)


def find_duplicates(
    items: Sequence[Item],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    num_perm: int = NUM_PERM,
) -> list[Removal]:
    """Return one ``Removal`` per record that should be dropped. Deterministic."""
    keys = [dedupe_key(item.text_norm) for item in items]
    unique_keys = sorted(set(keys))
    key_index = {key: i for i, key in enumerate(unique_keys)}
    key_shingles = [shingles(key) for key in unique_keys]

    clusters = _UnionFind(len(unique_keys))
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    signatures: list[MinHash] = []
    for i, grams in enumerate(key_shingles):
        signature = MinHash(num_perm=num_perm)
        signature.update_batch([gram.encode("utf-8") for gram in sorted(grams)])
        signatures.append(signature)
        lsh.insert(str(i), signature)
    for i, signature in enumerate(signatures):
        for candidate in lsh.query(signature):
            j = int(candidate)
            # LSH only proposes; the real Jaccard decides.
            if j > i and jaccard(key_shingles[i], key_shingles[j]) >= threshold:
                clusters.union(i, j)

    members: dict[int, list[int]] = defaultdict(list)
    for position, key in enumerate(keys):
        members[clusters.find(key_index[key])].append(position)

    removals: list[Removal] = []
    for positions in members.values():
        if len(positions) < 2:
            continue
        ordered = sorted(positions, key=lambda p: items[p].priority)
        kept = items[ordered[0]]
        kept_key = keys[ordered[0]]
        for position in ordered[1:]:
            item = items[position]
            if item.protected:
                continue
            tier: Tier
            if item.text_norm == kept.text_norm:
                tier, score = "exact", 1.0
            elif keys[position] == kept_key:
                tier, score = "punct_insensitive", 1.0
            else:
                tier = "near"
                score = jaccard(shingles(keys[position]), shingles(kept_key))
            removals.append(
                Removal(
                    id=item.id,
                    source=item.source,
                    split=item.split,
                    kept_id=kept.id,
                    kept_source=kept.source,
                    kept_split=kept.split,
                    tier=tier,
                    jaccard=round(score, 4),
                    label_conflict=item.labels != kept.labels,
                )
            )
    return sorted(removals, key=lambda r: r.id)


def _table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return lines


def render_report(
    removals: Sequence[Removal], totals: dict[str, int], threshold: float, protected: int
) -> str:
    before = sum(totals.values())
    lines = [
        "# Deduplication report",
        "",
        "Generated by `python -m bhaav.data.dedupe`. Counts only — no dataset text.",
        "",
        f"- Records before: **{before}**",
        f"- Removed: **{len(removals)}** ({len(removals) / before:.2%})"
        if before
        else "- Removed: 0",
        f"- Records after: **{before - len(removals)}**",
        f"- Protected records compared against (never removed): {protected}",
        f"- Near-duplicate rule: MinHash LSH, {NUM_PERM} permutations, char {SHINGLE_SIZE}-grams, "
        f"Jaccard ≥ {threshold}",
        f"- Removed pairs with **different labels**: {sum(r.label_conflict for r in removals)} "
        "(the kept copy's label wins)",
        "",
        "## Removed by tier",
        "",
    ]
    tiers = Counter(r.tier for r in removals)
    lines += _table(
        ["tier", "removed"], [[t, tiers.get(t, 0)] for t in ("exact", "punct_insensitive", "near")]
    )
    lines += ["", "## Removed by source", ""]
    by_source = Counter(r.source for r in removals)
    lines += _table(
        ["source", "before", "removed", "after"],
        [[s, n, by_source.get(s, 0), n - by_source.get(s, 0)] for s, n in sorted(totals.items())],
    )
    lines += ["", "## Removed copy → kept copy (source)", ""]
    pairs = Counter((r.source, r.kept_source) for r in removals)
    lines += _table(
        ["removed from", "kept in", "count"], [[a, b, n] for (a, b), n in sorted(pairs.items())]
    )
    lines += ["", "## Removed copy → kept copy (split)", ""]
    splits = Counter((r.split, r.kept_split) for r in removals)
    lines += _table(
        ["removed from", "kept in", "count"], [[a, b, n] for (a, b), n in sorted(splits.items())]
    )
    return "\n".join(lines) + "\n"


def _load_protected(paths: Sequence[Path]) -> list[Item]:
    """Texts that must survive (the gold set). Accepts JSONL with ``id`` and ``text_norm``."""
    protected: list[Item] = []
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    protected.append(
                        Item(
                            id=str(row["id"]),
                            source="gold",
                            split="gold",
                            text_norm=str(row["text_norm"]),
                            labels=frozenset(),
                            source_rank=-1,
                            protected=True,
                        )
                    )
    return protected


def run(
    paths: ProjectPaths,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    force: bool = False,
    protect: Sequence[Path] = (),
) -> dict[str, object] | None:
    """Deduplicate ``data/processed`` in place. Returns the summary, or ``None`` if already done."""
    files = sorted(paths.processed.glob("*.jsonl"))
    summary_path = paths.processed / DEDUPE_SUMMARY_NAME
    if summary_path.is_file() and not force:
        previous = json.loads(summary_path.read_text(encoding="utf-8"))
        if previous.get("files") == {f.name: sha256_file(f) for f in files}:
            return None

    by_file: dict[Path, list[Record]] = {f: list(read_jsonl(f)) for f in files}
    items: list[Item] = []
    for rank, (_, records) in enumerate(by_file.items()):
        items.extend(
            Item(r.id, r.source, r.split, r.text_norm, r.active_labels(), source_rank=rank)
            for r in records
        )
    protected = _load_protected(protect)
    removals = find_duplicates([*protected, *items], threshold=threshold)
    removed = {r.id: r for r in removals}

    totals = {f.stem: len(records) for f, records in by_file.items()}
    audit: list[dict[str, object]] = []
    for path, records in by_file.items():
        kept = [r for r in records if r.id not in removed]
        audit.extend(
            {**asdict(removed[r.id]), "text_norm": r.text_norm} for r in records if r.id in removed
        )
        write_jsonl(path, kept)

    removed_path = paths.interim / REMOVED_NAME
    removed_path.parent.mkdir(parents=True, exist_ok=True)
    with removed_path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in audit:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    paths.reports.mkdir(parents=True, exist_ok=True)
    report = render_report(removals, totals, threshold, len(protected))
    (paths.reports / REPORT_NAME).write_bytes(report.encode("utf-8"))

    summary: dict[str, object] = {
        "threshold": threshold,
        "num_perm": NUM_PERM,
        "shingle_size": SHINGLE_SIZE,
        "before": sum(totals.values()),
        "removed": len(removals),
        "removed_by_tier": dict(sorted(Counter(r.tier for r in removals).items())),
        "removed_by_source": dict(sorted(Counter(r.source for r in removals).items())),
        "label_conflicts": sum(r.label_conflict for r in removals),
        "protected": len(protected),
        "files": {f.name: sha256_file(f) for f in files},
    }
    write_json(summary_path, summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bhaav.data.dedupe", description=__doc__.split("\n")[0])
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--force", action="store_true", help="run even if already deduplicated")
    parser.add_argument(
        "--protect",
        nargs="+",
        type=Path,
        default=[],
        metavar="JSONL",
        help="files whose texts must survive (the gold set); log each use in docs/research_log.md",
    )
    args = parser.parse_args(argv)

    paths = ProjectPaths.discover()
    if not list(paths.processed.glob("*.jsonl")):
        print("nothing to deduplicate: data/processed has no *.jsonl (run bhaav.data.harmonize)")
        return 0
    summary = run(paths, threshold=args.threshold, force=args.force, protect=args.protect)
    if summary is None:
        print("already deduplicated (hashes match dedupe_summary.json); re-run harmonize to reset")
        return 0
    print(
        f"removed {summary['removed']} of {summary['before']} records "
        f"({summary['removed_by_tier']}); report → reports/{REPORT_NAME}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
