"""Deterministic multi-label stratified splits (iterative stratification, Sechidis et al. 2011)."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping, Sequence

DEFAULT_RATIOS: Mapping[str, float] = {"train": 0.8, "val": 0.1, "test_in_domain": 0.1}


def stratified_split(
    label_sets: Sequence[frozenset[str]],
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = 2026,
) -> list[str]:
    """Assign each example to a split so that every label keeps roughly the requested ratios.

    Rare labels are placed first, which is what keeps them from vanishing from the small splits.
    The result depends only on the inputs and ``seed``.
    """
    if abs(sum(ratios.values()) - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1")
    names = list(ratios)
    n = len(label_sets)
    rng = random.Random(seed)

    want_total = {name: n * ratios[name] for name in names}
    label_counts = Counter(label for labels in label_sets for label in labels)
    want_label = {
        name: {label: count * ratios[name] for label, count in label_counts.items()}
        for name in names
    }
    assignment: list[str | None] = [None] * n

    def place(index: int, label: str | None) -> None:
        def need(name: str) -> tuple[float, float]:
            by_label = want_label[name][label] if label is not None else 0.0
            return (by_label, want_total[name])

        best = max(need(name) for name in names)
        tied = [name for name in names if need(name) == best]
        chosen = tied[0] if len(tied) == 1 else rng.choice(tied)
        assignment[index] = chosen
        want_total[chosen] -= 1
        for own in label_sets[index]:
            want_label[chosen][own] -= 1

    while True:
        remaining = Counter(
            label
            for index, labels in enumerate(label_sets)
            if assignment[index] is None
            for label in labels
        )
        if not remaining:
            break
        rarest = min(remaining, key=lambda label: (remaining[label], label))
        members = [
            index
            for index, labels in enumerate(label_sets)
            if assignment[index] is None and rarest in labels
        ]
        rng.shuffle(members)
        for index in members:
            place(index, rarest)

    for index in range(n):
        if assignment[index] is None:  # examples with no label at all
            place(index, None)

    return [name for name in assignment if name is not None]
