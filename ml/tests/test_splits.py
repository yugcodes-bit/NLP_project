from __future__ import annotations

from collections import Counter

import pytest

from bhaav.data.splits import stratified_split


def test_ratios_hold_per_label() -> None:
    label_sets = (
        [frozenset({"joy"})] * 500 + [frozenset({"anger"})] * 300 + [frozenset({"disgust"})] * 40
    )
    split = stratified_split(label_sets, seed=1)
    for label, total in (("joy", 500), ("anger", 300), ("disgust", 40)):
        counts = Counter(s for s, labels in zip(split, label_sets, strict=True) if label in labels)
        assert counts["train"] == pytest.approx(0.8 * total, abs=1)
        assert counts["val"] == pytest.approx(0.1 * total, abs=1)
        assert counts["test_in_domain"] == pytest.approx(0.1 * total, abs=1)


def test_rare_label_reaches_every_split() -> None:
    label_sets = [frozenset({"neutral"})] * 970 + [frozenset({"surprise"})] * 30
    split = stratified_split(label_sets, seed=7)
    rare = Counter(s for s, labels in zip(split, label_sets, strict=True) if "surprise" in labels)
    assert rare == {"train": 24, "val": 3, "test_in_domain": 3}


def test_multi_label_examples_are_balanced_on_each_label() -> None:
    label_sets = (
        [frozenset({"joy", "surprise"})] * 100
        + [frozenset({"joy"})] * 200
        + [frozenset({"sadness", "fear"})] * 100
        + [frozenset({"fear"})] * 100
    )
    split = stratified_split(label_sets, seed=3)
    for label in ("joy", "surprise", "sadness", "fear"):
        total = sum(label in labels for labels in label_sets)
        in_val = sum(
            s == "val" and label in labels for s, labels in zip(split, label_sets, strict=True)
        )
        assert in_val == pytest.approx(0.1 * total, abs=2)


def test_deterministic_for_a_seed_and_different_across_seeds() -> None:
    label_sets = [frozenset({"joy"})] * 50 + [frozenset({"fear"})] * 50
    assert stratified_split(label_sets, seed=5) == stratified_split(label_sets, seed=5)
    assert stratified_split(label_sets, seed=5) != stratified_split(label_sets, seed=6)


def test_unlabelled_examples_and_empty_input() -> None:
    split = stratified_split([frozenset()] * 20, seed=1)
    assert Counter(split) == {"train": 16, "val": 2, "test_in_domain": 2}
    assert stratified_split([], seed=1) == []


def test_ratios_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        stratified_split([frozenset({"joy"})], ratios={"train": 0.5, "val": 0.2})
