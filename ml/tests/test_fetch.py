from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from bhaav.data import fetch
from bhaav.data.fetch import ChecksumMismatchError, FetchError, fetch_dataset
from bhaav.data.registry import DatasetEntry
from bhaav.paths import ProjectPaths

PAYLOAD = b"id,text,label\n1,synthetic row,happy\n"
SHA = hashlib.sha256(PAYLOAD).hexdigest()


def entry(
    *, status: str = "allowed", sha256: str | None = SHA, path: str = "train.csv"
) -> DatasetEntry:
    payload: dict[str, Any] = {
        "name": "Synthetic",
        "status": status,
        "url": "https://example.invalid/ds",
        "license": "CC0-1.0",
        "license_url": "https://example.invalid/ds/LICENSE",
        "verified_on": "2026-10-01",
        "approved": "test fixture",
        "fetch": {
            "version": "abc123",
            "files": [
                {"url": "https://example.invalid/ds/train.csv", "path": path, "sha256": sha256}
            ],
        },
    }
    return DatasetEntry.model_validate(payload)


class Server:
    """Counts requests so tests can assert on caching."""

    def __init__(self, body: bytes = PAYLOAD, status: int = 200) -> None:
        self.body, self.status, self.calls = body, status, 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(self.status, content=self.body, headers={"etag": '"v1"'})

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


def test_downloads_verifies_and_writes_manifest(tmp_path: Path) -> None:
    server = Server()
    result = fetch_dataset("ds", entry(), tmp_path, server.client())

    assert (tmp_path / "ds" / "train.csv").read_bytes() == PAYLOAD
    assert [f.sha256 for f in result.files] == [SHA]
    assert result.unpinned == ()
    manifest = json.loads((tmp_path / "ds" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "abc123"
    assert manifest["license"] == "CC0-1.0"
    assert manifest["files"][0]["sha256"] == SHA
    assert manifest["files"][0]["etag"] == '"v1"'


def test_pinned_file_is_served_from_cache(tmp_path: Path) -> None:
    server = Server()
    fetch_dataset("ds", entry(), tmp_path, server.client())
    again = fetch_dataset("ds", entry(), tmp_path, server.client())
    assert server.calls == 1
    assert again.files[0].cached

    fetch_dataset("ds", entry(), tmp_path, server.client(), force=True)
    assert server.calls == 2


def test_checksum_mismatch_discards_the_download(tmp_path: Path) -> None:
    server = Server(body=b"tampered")
    with pytest.raises(ChecksumMismatchError, match="upstream file changed"):
        fetch_dataset("ds", entry(), tmp_path, server.client())
    assert not (tmp_path / "ds" / "train.csv").exists()
    assert not (tmp_path / "ds" / "train.csv.part").exists()


def test_unpinned_file_is_recorded_and_reported(tmp_path: Path) -> None:
    result = fetch_dataset("ds", entry(sha256=None), tmp_path, Server().client())
    assert [f.sha256 for f in result.unpinned] == [SHA]


@pytest.mark.parametrize(
    "status", ["likely_allowed", "to_verify", "requested", "blocked", "excluded"]
)
def test_only_allowed_datasets_are_fetched(tmp_path: Path, status: str) -> None:
    server = Server()
    with pytest.raises(FetchError, match="only 'allowed'"):
        fetch_dataset("ds", entry(status=status), tmp_path, server.client())
    assert server.calls == 0


def test_path_cannot_escape_the_dataset_directory(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="escapes"):
        fetch_dataset("ds", entry(path="../../evil.csv"), tmp_path, Server().client())


def test_http_error_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="download failed"):
        fetch_dataset("ds", entry(), tmp_path, Server(status=404).client())


def test_cli_list_and_all(
    project: ProjectPaths, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert fetch.main(["--list"]) == 0
    listing = capsys.readouterr().out
    assert "mini" in listing
    assert "to_verify" in listing

    # The synthetic registry points at a host that does not exist; route it to a fake server.
    server = Server(body=(project.raw / "mini" / "mini_dataset.jsonl").read_bytes())
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **_: real_client(transport=httpx.MockTransport(server))
    )
    assert fetch.main(["--all"]) == 0
    out = capsys.readouterr().out
    assert "1 allowed dataset(s) to fetch" in out
    assert "unpinned mini_dataset.jsonl" in out
    assert fetch.main(["--all", "--strict"]) == 1
    assert fetch.main(["--dataset", "nope"]) == 2
    assert fetch.main(["--dataset", "pending"]) == 1
