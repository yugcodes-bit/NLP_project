"""The build-time Hub downloader, with the network replaced by a fake."""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from bhaav_api.devtools import fetch_model


class FakeHub:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float = 0) -> Any:
        self.requests.append(request)
        name = request.full_url.rsplit("/", 1)[1]
        if name not in self.files:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)  # type: ignore[arg-type]
        return io.BytesIO(self.files[name])


@pytest.fixture
def hub(model_dir: Path, monkeypatch: pytest.MonkeyPatch) -> FakeHub:
    fake = FakeHub({p.name: p.read_bytes() for p in model_dir.iterdir()})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake


def test_fetches_pinned_revision(hub: FakeHub, tmp_path: Path, model_dir: Path) -> None:
    written = fetch_model.fetch_model("bhaav/teacher-onnx", "v1.0.0", tmp_path / "m")
    assert written == ["model_quantized.onnx", "tokenizer.json", "model-meta.json", "lid.json"]
    assert hub.requests[0].full_url == (
        "https://huggingface.co/bhaav/teacher-onnx/resolve/v1.0.0/model_quantized.onnx"
    )
    for path in model_dir.iterdir():
        assert (tmp_path / "m" / path.name).read_bytes() == path.read_bytes()
    assert all(r.get_header("Authorization") is None for r in hub.requests)


def test_token_is_sent_when_given(hub: FakeHub, tmp_path: Path) -> None:
    fetch_model.fetch_model("org/private", "abc", tmp_path / "m", token="hf_secret")
    assert all(r.get_header("Authorization") == "Bearer hf_secret" for r in hub.requests)


def test_optional_file_may_be_absent(hub: FakeHub, tmp_path: Path) -> None:
    del hub.files["lid.json"]
    written = fetch_model.fetch_model("o/r", "v1", tmp_path / "m")
    assert "lid.json" not in written
    assert not (tmp_path / "m" / "lid.json").exists()


def test_required_file_missing_fails(hub: FakeHub, tmp_path: Path) -> None:
    del hub.files["tokenizer.json"]
    with pytest.raises(urllib.error.HTTPError):
        fetch_model.fetch_model("o/r", "v1", tmp_path / "m")


def test_malformed_meta_fails_the_build(hub: FakeHub, tmp_path: Path) -> None:
    hub.files["model-meta.json"] = b'{"model_version": "x"}'
    with pytest.raises(ValueError, match="validation error"):
        fetch_model.fetch_model("o/r", "v1", tmp_path / "m")


def test_cli(
    hub: FakeHub,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_env")
    out = tmp_path / "m"
    assert fetch_model.main(["--repo", "o/r", "--revision", "v1", "--out", str(out)]) == 0
    assert "from o/r@v1" in capsys.readouterr().out
    assert hub.requests[0].get_header("Authorization") == "Bearer hf_env"
