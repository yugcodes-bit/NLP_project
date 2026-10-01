from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from bhaav import sync_shared


def test_generated_copies_in_the_repo_are_fresh(repo_root: Path) -> None:
    """Fails when normalize.py / lid.py / configs changed without re-running the sync."""
    assert sync_shared.stale(repo_root) == [], "run: uv run python -m bhaav.sync_shared"


@pytest.fixture
def sandbox(tmp_path: Path, repo_root: Path) -> Path:
    for source in {s for s, _ in (*sync_shared.COPIES, *sync_shared.JSON_EXPORTS)}:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root / source, target)
    return tmp_path


def test_write_then_check_round_trip(sandbox: Path) -> None:
    expected = {target for _, target in (*sync_shared.COPIES, *sync_shared.JSON_EXPORTS)}
    assert set(sync_shared.stale(sandbox)) == expected
    assert set(sync_shared.write(sandbox)) == expected
    assert sync_shared.stale(sandbox) == []
    assert sync_shared.write(sandbox) == []  # nothing to do the second time


def test_python_copy_is_the_source_plus_a_header(sandbox: Path) -> None:
    sync_shared.write(sandbox)
    source = (sandbox / "ml/src/bhaav/data/normalize.py").read_text(encoding="utf-8")
    copy = (sandbox / "services/api/bhaav_api/inference/normalize.py").read_text(encoding="utf-8")
    header, _, body = copy.partition("uv run python -m bhaav.sync_shared\n")
    assert header.startswith(
        "# GENERATED FILE - do not edit. Source: ml/src/bhaav/data/normalize.py"
    )
    assert body == source


def test_json_export_matches_the_yaml(sandbox: Path) -> None:
    sync_shared.write(sandbox)
    exported = json.loads(
        (sandbox / "apps/web/lib/generated/label-schema.json").read_text(encoding="utf-8")
    )
    assert exported["labels"] == [
        "anger",
        "disgust",
        "fear",
        "joy",
        "sadness",
        "surprise",
        "neutral",
    ]
    assert exported["ui"]["hinglish_name"]["joy"] == "Khushi"
    assert exported["intensity"]["scale"] == {
        "0": "absent",
        "1": "low",
        "2": "moderate",
        "3": "high",
    }


def test_edit_to_a_source_or_a_copy_is_detected(sandbox: Path) -> None:
    sync_shared.write(sandbox)
    copy = sandbox / "services/api/bhaav_api/inference/lid.py"
    copy.write_text(copy.read_text(encoding="utf-8") + "# hand edit\n", encoding="utf-8")
    assert sync_shared.stale(sandbox) == [Path("services/api/bhaav_api/inference/lid.py")]

    sync_shared.write(sandbox)
    config = sandbox / "configs/normalization.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("max_char_repeat: 2", "max_char_repeat: 3"),
        encoding="utf-8",
    )
    assert set(sync_shared.stale(sandbox)) == {
        Path("services/api/bhaav_api/resources/normalization.yaml"),
        Path("apps/web/lib/generated/normalization.json"),
    }


def test_cli_check_and_write(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BHAAV_ROOT", str(sandbox))
    assert sync_shared.main(["--check"]) == 1
    assert "stale: services/api/bhaav_api/inference/normalize.py" in capsys.readouterr().out
    assert sync_shared.main([]) == 0
    assert "wrote apps/web/lib/generated/label-schema.json" in capsys.readouterr().out
    assert sync_shared.main(["--check"]) == 0
