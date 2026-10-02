"""Shared bookkeeping for experiment folders (``CLAUDE.md`` §5).

Every run writes ``experiments/<run_id>/`` with ``config.yaml``, ``metrics.json``,
``predictions_val.jsonl``, ``env.txt`` and ``NOTES.md``. This module provides the parts that are
the same for every kind of run: the environment record and the atomic writers.
"""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path

import yaml

from bhaav.data.records import write_json


def git_state(root: Path) -> tuple[str, bool]:
    """``(commit sha, dirty)`` of the repo at ``root``; ``("unknown", True)`` outside git."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return sha, bool(status)


def environment_report(root: Path, gpu: str = "none (CPU only)") -> str:
    """The content of ``env.txt``: git SHA, interpreter, platform, GPU and installed packages."""
    sha, dirty = git_state(root)
    packages = sorted(
        f"{dist.metadata['Name']}=={dist.version}"
        for dist in importlib.metadata.distributions()
        if dist.metadata["Name"]
    )
    header = [
        f"git_sha: {sha}",
        f"git_dirty: {str(dirty).lower()}",
        f"python: {sys.version.split()[0]}",
        f"platform: {platform.platform()}",
        f"gpu: {gpu}",
        "",
        "# installed packages",
    ]
    return "\n".join([*header, *packages]) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))


def write_run_files(
    run_dir: Path,
    *,
    root: Path,
    config: dict[str, object],
    metrics: dict[str, object],
    notes: str,
) -> None:
    """Write ``config.yaml``, ``metrics.json``, ``env.txt`` and ``NOTES.md`` for one run."""
    write_text(run_dir / "config.yaml", yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    write_json(run_dir / "metrics.json", metrics)
    write_text(run_dir / "env.txt", environment_report(root))
    write_text(run_dir / "NOTES.md", notes)
