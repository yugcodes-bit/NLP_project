"""Download datasets marked ``status: allowed`` into ``data/raw/<key>/`` (FR-32).

    uv run python -m bhaav.data.fetch --list
    uv run python -m bhaav.data.fetch --all
    uv run python -m bhaav.data.fetch --dataset masac24 --strict

Every file is hashed. A SHA-256 pinned in ``configs/datasets.yaml`` must match or the download
is discarded. An unpinned file is accepted once, its hash is written to the dataset's
``MANIFEST.json`` and printed so it can be pinned; ``--strict`` turns unpinned files into errors.
Nothing is fetched for any other status, whatever the flags.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from bhaav.data.records import sha256_file, write_json
from bhaav.data.registry import (
    DatasetEntry,
    DatasetRegistry,
    DatasetStatus,
    FetchFile,
    load_registry,
)
from bhaav.paths import ProjectPaths
from bhaav.schema import load_label_schema

MANIFEST_NAME = "MANIFEST.json"
_TIMEOUT = httpx.Timeout(30.0, read=120.0)


class FetchError(RuntimeError):
    pass


class ChecksumMismatchError(FetchError):
    pass


@dataclass(frozen=True)
class FetchedFile:
    path: str
    url: str
    sha256: str
    bytes: int
    pinned: bool
    cached: bool
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class FetchResult:
    dataset: str
    version: str
    files: tuple[FetchedFile, ...]

    @property
    def unpinned(self) -> tuple[FetchedFile, ...]:
        return tuple(f for f in self.files if not f.pinned)


def _destination(dataset_dir: Path, relative: str) -> Path:
    dest = (dataset_dir / relative).resolve()
    if not dest.is_relative_to(dataset_dir.resolve()):
        raise FetchError(f"fetch path {relative!r} escapes {dataset_dir}")
    return dest


def _download(client: httpx.Client, spec: FetchFile, dest: Path) -> FetchedFile:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with client.stream("GET", spec.url, follow_redirects=True) as response:
            response.raise_for_status()
            with tmp.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            etag = response.headers.get("etag")
            last_modified = response.headers.get("last-modified")
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise FetchError(f"download failed for {spec.url}: {exc}") from exc

    sha = digest.hexdigest()
    if spec.sha256 is not None and sha != spec.sha256:
        tmp.unlink(missing_ok=True)
        raise ChecksumMismatchError(
            f"{spec.url}: expected sha256 {spec.sha256}, got {sha}. The upstream file changed — "
            "re-verify the dataset before updating the pin."
        )
    os.replace(tmp, dest)
    return FetchedFile(
        path=spec.path,
        url=spec.url,
        sha256=sha,
        bytes=size,
        pinned=spec.sha256 is not None,
        cached=False,
        etag=etag,
        last_modified=last_modified,
    )


def fetch_dataset(
    key: str,
    entry: DatasetEntry,
    raw_root: Path,
    client: httpx.Client,
    *,
    force: bool = False,
) -> FetchResult:
    """Fetch one dataset. Refuses anything that is not ``allowed``."""
    if entry.status is not DatasetStatus.ALLOWED:
        raise FetchError(f"{key} has status {entry.status.value!r}; only 'allowed' is fetched")
    if entry.fetch is None:
        raise FetchError(f"{key} is allowed but has no fetch spec in the registry")

    dataset_dir = raw_root / key
    fetched: list[FetchedFile] = []
    for spec in entry.fetch.files:
        dest = _destination(dataset_dir, spec.path)
        # A pinned file already on disk with the right hash does not need the network.
        cached = (
            not force
            and spec.sha256 is not None
            and dest.is_file()
            and sha256_file(dest) == spec.sha256
        )
        if cached and spec.sha256 is not None:
            fetched.append(
                FetchedFile(
                    path=spec.path,
                    url=spec.url,
                    sha256=spec.sha256,
                    bytes=dest.stat().st_size,
                    pinned=True,
                    cached=True,
                )
            )
        else:
            fetched.append(_download(client, spec, dest))

    result = FetchResult(dataset=key, version=entry.fetch.version, files=tuple(fetched))
    write_json(
        dataset_dir / MANIFEST_NAME,
        {
            "dataset": key,
            "name": entry.name,
            "version": entry.fetch.version,
            "license": entry.license,
            "license_url": entry.license_url,
            "source_url": entry.url,
            "fetched_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "files": [asdict(f) for f in fetched],
        },
    )
    return result


def status_table(registry: DatasetRegistry) -> str:
    width = max(len(key) for key in registry.datasets)
    lines = [f"{'dataset'.ljust(width)}  status          fetch  license"]
    for key, entry in registry.datasets.items():
        has_fetch = "yes" if entry.fetch is not None else "-"
        lines.append(
            f"{key.ljust(width)}  {entry.status.value.ljust(14)}  {has_fetch.ljust(5)}  "
            f"{entry.license or '-'}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bhaav.data.fetch", description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="fetch every allowed dataset")
    group.add_argument("--dataset", nargs="+", metavar="KEY", help="fetch these datasets")
    group.add_argument("--list", action="store_true", help="show registry status and exit")
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    parser.add_argument(
        "--strict", action="store_true", help="fail on files without a pinned sha256"
    )
    args = parser.parse_args(argv)

    paths = ProjectPaths.discover()
    registry = load_registry(paths.datasets, load_label_schema(paths.label_schema))

    if args.list:
        print(status_table(registry))
        return 0

    if args.all:
        targets = {k: v for k, v in registry.allowed().items() if v.fetch is not None}
        skipped = [k for k, v in registry.datasets.items() if v.status is not DatasetStatus.ALLOWED]
        print(f"{len(targets)} allowed dataset(s) to fetch; {len(skipped)} not allowed (skipped).")
    else:
        unknown = [k for k in args.dataset if k not in registry.datasets]
        if unknown:
            print(f"unknown dataset(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        targets = {k: registry.datasets[k] for k in args.dataset}

    failures = 0
    with httpx.Client(timeout=_TIMEOUT, headers={"user-agent": "bhaav-data-fetch/0.1"}) as client:
        for key, entry in targets.items():
            try:
                result = fetch_dataset(key, entry, paths.raw, client, force=args.force)
            except FetchError as exc:
                print(f"[{key}] ERROR: {exc}", file=sys.stderr)
                failures += 1
                continue
            cached = sum(f.cached for f in result.files)
            print(f"[{key}] {len(result.files)} file(s), {cached} cached, version {result.version}")
            for item in result.unpinned:
                print(f"[{key}]   unpinned {item.path}: sha256: {json.dumps(item.sha256)}")
            if args.strict and result.unpinned:
                print(
                    f"[{key}] ERROR: --strict and {len(result.unpinned)} unpinned file(s)",
                    file=sys.stderr,
                )
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
