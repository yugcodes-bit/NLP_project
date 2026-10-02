"""From raw model outputs to a decision. Pure functions; the browser must mirror them exactly.

Rules (``docs/08`` §3.3 and §3.5, ``configs/label_schema.yaml``):

1. calibrated probability = ``sigmoid(logit / T)`` per label
2. **abstain** when the highest calibrated probability over all labels is below ``tau``
3. an emotion is **active** when its probability reaches its own threshold
4. **neutral is exclusive**: it is the answer when no emotion is active, or when it clears its
   threshold and beats every emotion; otherwise it is suppressed
5. intensity of an active emotion = number of CORAL thresholds (≥1, ≥2, ≥3) passed, at least 1
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from bhaav_api.inference.model_meta import ModelMeta

FloatArray = npt.NDArray[np.floating]


@dataclass(frozen=True)
class Decision:
    #: Calibrated probability of every label, in model order.
    scores: dict[str, float]
    #: Active labels, most probable first. Empty when abstaining.
    active: tuple[str, ...]
    #: Intensity of each active label (``None`` for neutral).
    intensity: dict[str, int | None]
    top: str | None
    abstained: bool
    #: The two most probable labels, given only when abstaining.
    candidates: tuple[tuple[str, float], ...] | None
    #: Highest calibrated probability over all labels.
    confidence: float


def sigmoid(x: FloatArray) -> npt.NDArray[np.float64]:
    clipped = np.clip(np.asarray(x, dtype=np.float64), -60.0, 60.0)
    return np.asarray(1.0 / (1.0 + np.exp(-clipped)), dtype=np.float64)


def calibrated_probabilities(
    logits: FloatArray, temperature: FloatArray
) -> npt.NDArray[np.float64]:
    return sigmoid(np.asarray(logits, dtype=np.float64) / np.asarray(temperature, dtype=np.float64))


def decode_intensity(coral_logits: FloatArray) -> list[int]:
    """CORAL ordinal decoding: one row of (≥1, ≥2, ≥3) logits per emotion → level 0–3."""
    passed = sigmoid(coral_logits) > 0.5
    return [int(row.sum()) for row in passed]


def decide(logits: FloatArray, coral_logits: FloatArray, meta: ModelMeta) -> Decision:
    """Decide for one text. ``logits``: (n_labels,). ``coral_logits``: (n_emotions, 3)."""
    probabilities = calibrated_probabilities(logits, np.asarray(meta.temperature))
    scores = {label: float(p) for label, p in zip(meta.labels, probabilities, strict=True)}
    order = {label: index for index, label in enumerate(meta.labels)}

    def ranked(labels: tuple[str, ...]) -> list[str]:
        return sorted(labels, key=lambda label: (-scores[label], order[label]))

    confidence = max(scores.values())
    if confidence < meta.tau:
        return Decision(
            scores=scores,
            active=(),
            intensity={},
            top=None,
            abstained=True,
            candidates=tuple((label, scores[label]) for label in ranked(meta.labels)[:2]),
            confidence=confidence,
        )

    neutral = meta.neutral_label
    active_emotions = tuple(e for e in meta.emotions if scores[e] >= meta.thresholds[e])
    neutral_wins = scores[neutral] >= meta.thresholds[neutral] and all(
        scores[neutral] > scores[e] for e in meta.emotions
    )
    if not active_emotions or neutral_wins:
        active: tuple[str, ...] = (neutral,)
        intensity: dict[str, int | None] = {neutral: None}
    else:
        active = tuple(ranked(active_emotions))
        levels = dict(zip(meta.emotions, decode_intensity(coral_logits), strict=True))
        intensity = {label: max(1, levels[label]) for label in active}

    return Decision(
        scores=scores,
        active=active,
        intensity=intensity,
        top=active[0],
        abstained=False,
        candidates=None,
        confidence=confidence,
    )
