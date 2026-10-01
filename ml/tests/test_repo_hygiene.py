"""Guards for things that are easy to break without noticing."""

from __future__ import annotations

import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

#: Source trees whose files must not hide invisible characters. Data fixtures (JSONL/CSV) are
#: exempt: emoji there legitimately carry variation selectors and joiners.
SCANNED = ("ml/src", "ml/tests", "services/api/bhaav_api", "services/api/tests")
EXTRA_FILES = ("ml/tests/fixtures/normalize_cases.json",)


def _hidden(ch: str) -> bool:
    code = ord(ch)
    if code < 0x80:
        return False
    return (
        unicodedata.category(ch) in {"Cf", "Cc", "Zs", "Zl", "Zp", "Cs", "Co"}
        or 0xFE00 <= code <= 0xFE0F  # variation selectors
        or 0x0300 <= code <= 0x036F  # combining diacritics
        or code == 0xFFFD
    )


def _files(root: Path) -> list[Path]:
    found = [p for tree in SCANNED for p in sorted((root / tree).rglob("*.py"))]
    return [*found, *(root / extra for extra in EXTRA_FILES)]


def test_no_invisible_characters_in_source(repo_root: Path) -> None:
    """Zero-width, bidi, no-break-space and similar characters must be written as escapes.

    A literal one in a regex or a test string cannot be reviewed, and editors strip them.
    Write ``chr(0x200D)`` or an escape sequence instead.
    """
    offenders = []
    for path in _files(repo_root):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.split("\n"), 1):
            hidden = sorted({f"U+{ord(ch):04X}" for ch in line if _hidden(ch)})
            if hidden:
                offenders.append(f"{path.relative_to(repo_root).as_posix()}:{number} {hidden}")
    assert offenders == []


def test_gitignore_keeps_data_out_and_source_in(repo_root: Path) -> None:
    """Datasets, weights and secrets are ignored; the ``bhaav.data`` source package is not.

    A bare ``data/`` pattern ignores every directory of that name, which once hid
    ``ml/src/bhaav/data/`` from git (and from ruff, which honours .gitignore).
    """
    ignored = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in ("/data/", "*.onnx", "*.safetensors", ".env", ".env.*"):
        assert pattern in ignored
    assert "data/" not in ignored
    assert "data" not in ignored


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_git_tracks_the_data_package(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "ml/src/bhaav/data/normalize.py"],
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 1, "ml/src/bhaav/data is git-ignored"
