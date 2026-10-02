"""Request and response models. They mirror ``docs/14_api_contract.md`` — keep the two in step."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnalyzeOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    explain: bool = False
    lid: bool = True
    all_scores: bool = True


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    options: AnalyzeOptions = AnalyzeOptions()


class EmotionOut(BaseModel):
    label: str
    probability: float
    active: bool
    #: 1–3 for emotions; ``null`` for ``neutral``, which carries no intensity.
    intensity: int | None


class Candidate(BaseModel):
    label: str
    probability: float


class LidToken(BaseModel):
    text: str
    lang: Literal["hi", "en", "univ", "ne", "other"]


class LidOut(BaseModel):
    tokens: list[LidToken]
    cmi: float
    lang_share: dict[str, float]


class ExplanationWord(BaseModel):
    text: str
    score: float


class Explanation(BaseModel):
    target: str
    method: Literal["occlusion"]
    words: list[ExplanationWord]


class Wellbeing(BaseModel):
    show: bool


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    text_normalized: str
    script: Literal["roman", "devanagari", "mixed"]
    emotions: list[EmotionOut]
    scores: dict[str, float] | None
    top: str | None
    abstained: bool
    candidates: list[Candidate] | None
    confidence: float
    lid: LidOut | None
    explanation: Explanation | None
    wellbeing: Wellbeing
    model_version: str
    mode: Literal["server", "browser"]
    latency_ms: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok", "model_not_ready"]
    model_version: str | None
    uptime_s: int


class LabelsResponse(BaseModel):
    labels: list[str]
    intensity_scale: dict[str, str]
    schema_version: str
