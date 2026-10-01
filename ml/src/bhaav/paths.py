"""Repository paths, resolved from the repo root so commands work from any directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_MARKER = Path("configs") / "label_schema.yaml"


def find_repo_root(start: Path | None = None) -> Path:
    """Return ``$BHAAV_ROOT`` if set, else the nearest ancestor that holds the configs."""
    env = os.environ.get("BHAAV_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / _MARKER).is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find {_MARKER.as_posix()} above {here}. "
        "Run from inside the repo or set BHAAV_ROOT."
    )


@dataclass(frozen=True)
class ProjectPaths:
    """Every path the pipeline reads or writes, relative to one root (overridable in tests)."""

    root: Path

    @classmethod
    def discover(cls) -> ProjectPaths:
        return cls(find_repo_root())

    @property
    def configs(self) -> Path:
        return self.root / "configs"

    @property
    def label_schema(self) -> Path:
        return self.configs / "label_schema.yaml"

    @property
    def datasets(self) -> Path:
        return self.configs / "datasets.yaml"

    @property
    def normalization(self) -> Path:
        return self.configs / "normalization.yaml"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def interim(self) -> Path:
        return self.data / "interim"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def lid_model(self) -> Path:
        return self.interim / "lid" / "lid_model.json"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"
