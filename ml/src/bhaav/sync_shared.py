"""Copy the single-source shared code and configs to the API and web packages (ADR-008).

    uv run python -m bhaav.sync_shared            # rewrite the generated copies
    uv run python -m bhaav.sync_shared --check    # exit 1 if any copy is stale (pre-commit, CI)

Sources of truth: ``ml/src/bhaav/data/{normalize,lid}.py`` and ``configs/*.yaml``.
Never edit the generated files; edit the source and re-run this.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import yaml

from bhaav.paths import find_repo_root

_API = Path("services/api/bhaav_api")
_WEB = Path("apps/web/lib/generated")

#: source → generated copy, with a "do not edit" header in the target's comment syntax.
COPIES: tuple[tuple[Path, Path], ...] = (
    (Path("ml/src/bhaav/data/normalize.py"), _API / "inference/normalize.py"),
    (Path("ml/src/bhaav/data/lid.py"), _API / "inference/lid.py"),
    (Path("configs/normalization.yaml"), _API / "resources/normalization.yaml"),
    (Path("configs/label_schema.yaml"), _API / "resources/label_schema.yaml"),
)
#: YAML source → JSON for the web app (JSON has no comments, so no header).
JSON_EXPORTS: tuple[tuple[Path, Path], ...] = (
    (Path("configs/label_schema.yaml"), _WEB / "label-schema.json"),
    (Path("configs/normalization.yaml"), _WEB / "normalization.json"),
)


def _header(source: Path) -> str:
    return (
        f"# GENERATED FILE - do not edit. Source: {source.as_posix()}\n"
        "# Regenerate with: uv run python -m bhaav.sync_shared\n"
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def render(root: Path) -> dict[Path, str]:
    """Expected content of every generated file, keyed by repo-relative path."""
    rendered: dict[Path, str] = {}
    for source, target in COPIES:
        rendered[target] = _header(source) + _read(root / source)
    for source, target in JSON_EXPORTS:
        payload = yaml.safe_load(_read(root / source))
        rendered[target] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return rendered


def stale(root: Path) -> list[Path]:
    """Generated files that are missing or differ from what ``render`` would produce."""
    out: list[Path] = []
    for target, content in render(root).items():
        path = root / target
        if not path.is_file() or _read(path) != content:
            out.append(target)
    return out


def write(root: Path) -> list[Path]:
    written: list[Path] = []
    for target, content in render(root).items():
        path = root / target
        if path.is_file() and _read(path) == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        written.append(target)
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bhaav.sync_shared", description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 when stale")
    args = parser.parse_args(argv)
    root = find_repo_root()

    if args.check:
        out_of_date = stale(root)
        for target in out_of_date:
            print(f"stale: {target.as_posix()}")
        if out_of_date:
            print("run: uv run python -m bhaav.sync_shared")
            return 1
        return 0

    for target in write(root):
        print(f"wrote {target.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
