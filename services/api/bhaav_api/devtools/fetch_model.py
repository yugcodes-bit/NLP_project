r"""Download a published model from the Hugging Face Hub into a directory (used at image build).

    python -m bhaav_api.devtools.fetch_model \
        --repo bhaav/teacher-onnx --revision v1.0.0 --out /model

Standard library only. ``HF_TOKEN`` is sent as a bearer token when set (private repos).
"""

from __future__ import annotations

import argparse
import os
import shutil
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from bhaav_api.inference.model_meta import META_FILE, load_model_meta
from bhaav_api.inference.pipeline import LID_FILE, MODEL_FILE, TOKENIZER_FILE

REQUIRED = (MODEL_FILE, TOKENIZER_FILE, META_FILE)
OPTIONAL = (LID_FILE,)
HUB = "https://huggingface.co"


def file_url(repo: str, revision: str, name: str) -> str:
    return f"{HUB}/{repo}/resolve/{revision}/{name}"


def _download(url: str, dest: Path, token: str | None) -> None:
    headers = {"authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as fh:
        shutil.copyfileobj(response, fh)


def fetch_model(repo: str, revision: str, out_dir: Path, token: str | None = None) -> list[str]:
    """Fetch required files (and optional ones that exist). Returns the names written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name in REQUIRED:
        _download(file_url(repo, revision, name), out_dir / name, token)
        written.append(name)
    for name in OPTIONAL:
        try:
            _download(file_url(repo, revision, name), out_dir / name, token)
            written.append(name)
        except urllib.error.HTTPError as exc:
            (out_dir / name).unlink(missing_ok=True)
            if exc.code != 404:
                raise
    load_model_meta(out_dir / META_FILE)  # fail the build on a malformed model-meta.json
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bhaav_api.devtools.fetch_model")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    written = fetch_model(args.repo, args.revision, args.out, os.environ.get("HF_TOKEN") or None)
    print(f"fetched {', '.join(written)} from {args.repo}@{args.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
