"""Runtime settings, read from environment variables (see ``.env.example``)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    #: Directory holding ``model_quantized.onnx``, ``tokenizer.json``, ``model-meta.json``
    #: and optionally ``lid.json``.
    model_dir: Path = Path("/app/model")
    #: Comma-separated list of origins allowed by CORS.
    allowed_origins: str = "http://localhost:3000"
    #: Input length limit in Unicode code points. Unset → ``max_chars`` of the normalisation config.
    max_text_chars: int | None = None
    log_level: str = "info"
    #: ONNX Runtime intra-op threads; 0 lets the runtime decide.
    ort_threads: int = 0

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
