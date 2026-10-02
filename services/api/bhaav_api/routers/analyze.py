"""``POST /v1/analyze`` (FR-01 … FR-09).

Phase 1 skeleton: the full decision path runs, against whatever model ``MODEL_DIR`` holds.
Not implemented yet, and returned as documented placeholders:

* ``explanation`` is always ``null`` (occlusion arrives in Phase 6, ADR-005)
* ``wellbeing.show`` is always ``false`` (FR-25 arrives in Phase 6)
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from bhaav_api.errors import model_not_ready, text_empty, text_too_long
from bhaav_api.inference.lid import detect_script
from bhaav_api.routers.meta import get_pipeline
from bhaav_api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Candidate,
    EmotionOut,
    LidOut,
    LidToken,
    Wellbeing,
)

router = APIRouter(prefix="/v1", tags=["analyze"])

_PROBABILITY_DIGITS = 4


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    started = time.perf_counter()
    pipeline = get_pipeline(request)
    if pipeline is None:
        raise model_not_ready()

    # Length is counted in Unicode code points, so one emoji is one character.
    text = payload.text.strip()
    limit = request.app.state.settings.max_text_chars or pipeline.max_chars
    request.state.input_chars = len(text)
    if not text:
        raise text_empty()
    if len(text) > limit:
        raise text_too_long(limit)

    normalized = pipeline.normalizer(text).text
    if not normalized:  # nothing but invisible characters
        raise text_empty()

    decision = pipeline.infer(normalized)
    emotions = [
        EmotionOut(
            label=label,
            probability=round(decision.scores[label], _PROBABILITY_DIGITS),
            active=True,
            intensity=decision.intensity[label],
        )
        for label in decision.active
    ]
    scores = None
    if payload.options.all_scores:
        scores = {k: round(v, _PROBABILITY_DIGITS) for k, v in decision.scores.items()}
    candidates = None
    if decision.candidates is not None:
        candidates = [
            Candidate(label=label, probability=round(p, _PROBABILITY_DIGITS))
            for label, p in decision.candidates
        ]

    lid = None
    if payload.options.lid:
        mix = pipeline.code_mix(normalized)
        if mix is not None:
            lid = LidOut(
                tokens=[LidToken(text=t.text, lang=t.lang) for t in mix.tokens],
                cmi=round(mix.cmi, 1),
                lang_share={k: round(v, 3) for k, v in mix.lang_share.items()},
            )

    return AnalyzeResponse(
        text_normalized=normalized,
        script=detect_script(normalized),
        emotions=emotions,
        scores=scores,
        top=decision.top,
        abstained=decision.abstained,
        candidates=candidates,
        confidence=round(decision.confidence, _PROBABILITY_DIGITS),
        lid=lid,
        explanation=None,
        wellbeing=Wellbeing(show=False),
        model_version=pipeline.meta.model_version,
        mode="server",
        latency_ms=round((time.perf_counter() - started) * 1000),
    )
