"""Decision rules on hand-built model outputs. Every expected value is derivable by hand."""

from __future__ import annotations

import math

import numpy as np
import pytest

from bhaav_api.inference.model_meta import ModelMeta
from bhaav_api.inference.postprocess import (
    calibrated_probabilities,
    decide,
    decode_intensity,
    sigmoid,
)

LABELS = ("anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral")
EMOTIONS = LABELS[:-1]


def logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def logits(default: float = 0.02, **probabilities: float) -> np.ndarray:
    """Logits that give exactly the requested probabilities at temperature 1."""
    return np.asarray([logit(probabilities.get(label, default)) for label in LABELS])


def coral(**levels: int) -> np.ndarray:
    """CORAL logits (≥1, ≥2, ≥3) encoding the requested level per emotion; others level 0."""
    rows = [[5.0 if step < levels.get(e, 0) else -5.0 for step in range(3)] for e in EMOTIONS]
    return np.asarray(rows)


def test_contract_example(meta: ModelMeta) -> None:
    """docs/14: sadness 0.82 (high) and anger 0.31 (low) are both active, sadness first."""
    decision = decide(logits(sadness=0.82, anger=0.31), coral(sadness=3, anger=1), meta)
    assert decision.active == ("sadness", "anger")
    assert decision.intensity == {"sadness": 3, "anger": 1}
    assert decision.top == "sadness"
    assert not decision.abstained
    assert decision.candidates is None
    assert decision.confidence == pytest.approx(0.82)
    assert decision.scores["anger"] == pytest.approx(0.31)
    assert list(decision.scores) == list(LABELS)


def test_per_label_thresholds(meta: ModelMeta) -> None:
    """0.45 clears anger's threshold (0.3) but not joy's (0.5)."""
    assert decide(logits(anger=0.45), coral(anger=2), meta).active == ("anger",)
    assert decide(logits(joy=0.45), coral(joy=2), meta).active == ("neutral",)


def test_threshold_is_inclusive(meta: ModelMeta) -> None:
    exact = np.asarray([0.0 if label == "joy" else logit(0.02) for label in LABELS])
    assert decide(exact, coral(joy=1), meta).active == ("joy",)  # sigmoid(0) == 0.5 exactly


def test_no_emotion_active_falls_back_to_neutral(meta: ModelMeta) -> None:
    """FR-03. Confident enough to answer (0.45 ≥ tau 0.4) but nothing reaches its threshold."""
    decision = decide(logits(joy=0.45, neutral=0.10), coral(joy=3), meta)
    assert decision.active == ("neutral",)
    assert decision.intensity == {"neutral": None}
    assert decision.top == "neutral"
    assert not decision.abstained
    assert decision.confidence == pytest.approx(0.45)


def test_abstains_below_tau(meta: ModelMeta) -> None:
    """FR-05. The best probability (0.35) is under tau (0.4): unsure, with the top two offered."""
    decision = decide(logits(fear=0.35, surprise=0.32, joy=0.10), coral(fear=2), meta)
    assert decision.abstained
    assert decision.active == ()
    assert decision.intensity == {}
    assert decision.top is None
    assert decision.candidates is not None
    assert [label for label, _ in decision.candidates] == ["fear", "surprise"]
    assert [p for _, p in decision.candidates] == pytest.approx([0.35, 0.32])
    assert decision.confidence == pytest.approx(0.35)


def test_tau_boundary_answers(meta: ModelMeta) -> None:
    assert not decide(logits(joy=0.4000001), coral(), meta).abstained
    assert decide(logits(joy=0.3999999), coral(), meta).abstained


def test_neutral_wins_only_when_it_beats_every_emotion(meta: ModelMeta) -> None:
    wins = decide(logits(neutral=0.70, joy=0.60), coral(joy=2), meta)
    assert wins.active == ("neutral",)
    assert wins.intensity == {"neutral": None}

    suppressed = decide(logits(neutral=0.60, joy=0.80), coral(joy=2), meta)
    assert suppressed.active == ("joy",)
    assert "neutral" not in suppressed.intensity


def test_neutral_below_its_threshold_does_not_override_an_active_emotion(meta: ModelMeta) -> None:
    """anger 0.35 is active (threshold 0.3); neutral 0.45 is higher but under its own 0.5."""
    decision = decide(logits(anger=0.35, neutral=0.45), coral(anger=1), meta)
    assert decision.active == ("anger",)
    assert decision.confidence == pytest.approx(0.45)


def test_active_emotions_are_sorted_by_probability_then_label_order(meta: ModelMeta) -> None:
    decision = decide(logits(joy=0.6, sadness=0.9, anger=0.6), coral(), meta)
    assert decision.active == ("sadness", "anger", "joy")  # anger precedes joy in label order


def test_active_emotion_has_intensity_at_least_one(meta: ModelMeta) -> None:
    """The intensity head may say 0 for an emotion the detection head switched on."""
    decision = decide(logits(joy=0.9), coral(joy=0), meta)
    assert decision.intensity == {"joy": 1}


def test_temperature_scales_logits_per_label(meta: ModelMeta) -> None:
    hot = meta.model_copy(update={"temperature": (1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 1.0)})
    raw = np.asarray([-4.0, -4.0, -4.0, 2.0, 2.0, -4.0, -4.0])
    decision = decide(raw, coral(), hot)
    assert decision.scores["joy"] == pytest.approx(1 / (1 + math.exp(-1.0)))  # 2.0 / T=2
    assert decision.scores["sadness"] == pytest.approx(1 / (1 + math.exp(-2.0)))
    assert decision.active == ("sadness", "joy")


def test_decode_intensity_counts_thresholds_passed() -> None:
    rows = np.asarray([[-1.0, -2.0, -3.0], [1.0, -2.0, -3.0], [3.0, 1.0, -1.0], [3.0, 2.0, 1.0]])
    assert decode_intensity(rows) == [0, 1, 2, 3]


def test_sigmoid_is_stable_at_extremes() -> None:
    values = sigmoid(np.asarray([-1e6, 0.0, 1e6]))
    assert values[0] == pytest.approx(0.0, abs=1e-20)
    assert values[1] == 0.5
    assert values[2] == pytest.approx(1.0)
    assert np.isfinite(values).all()


def test_calibrated_probabilities_vectorised() -> None:
    out = calibrated_probabilities(np.asarray([0.0, 2.0]), np.asarray([1.0, 2.0]))
    assert out == pytest.approx([0.5, 1 / (1 + math.exp(-1.0))])
