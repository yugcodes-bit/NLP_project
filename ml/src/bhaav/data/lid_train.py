"""Train and evaluate the char n-gram word-level LID model (ADR-006).

The featuriser is the one in ``bhaav.data.lid`` — training and serving cannot drift because they
share the function. scikit-learn is used only here; the exported model needs numpy alone.

This module is the dataset-independent part (fit, export, score). The run on real data — reading
SentiMix, choosing the regularisation on validation, reporting on test, writing the experiment
folder — is ``bhaav.data.lid_experiment``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from bhaav.data.lid import LidModel, ngram_features

DEFAULT_NGRAM_RANGE = (1, 5)
DEFAULT_N_FEATURES = 1 << 16


def design_matrix(
    words: Sequence[str], ngram_range: tuple[int, int], n_features: int
) -> csr_matrix[np.float32]:
    """One row per word: ``1 / sqrt(k)`` at each of its ``k`` hashed n-gram indices."""
    data: list[float] = []
    columns: list[int] = []
    row_pointer = [0]
    for word in words:
        indices = ngram_features(word, ngram_range, n_features)
        columns.extend(indices)
        data.extend([1.0 / np.sqrt(len(indices))] * len(indices))
        row_pointer.append(len(columns))
    return csr_matrix(
        (np.asarray(data, dtype=np.float32), columns, row_pointer),
        shape=(len(words), n_features),
        dtype=np.float32,
    )


def fit_classifier(
    pairs: Sequence[tuple[str, str]],
    *,
    ngram_range: tuple[int, int] = DEFAULT_NGRAM_RANGE,
    n_features: int = DEFAULT_N_FEATURES,
    c: float = 1.0,
    seed: int = 13,
) -> tuple[LogisticRegression, list[str]]:
    """Fit on ``(word, language)`` token instances. Repeated instances act as sample weights.

    ``c`` is the inverse L2 strength; tune it on the LID validation split (the default
    under-fits when there are only a few hundred distinct words).
    """
    counts = Counter((word.lower(), lang) for word, lang in pairs)
    examples = sorted(counts)
    classes = sorted({lang for _, lang in examples})
    if len(classes) < 2:
        raise ValueError("LID training needs at least two languages")

    features = design_matrix([word for word, _ in examples], ngram_range, n_features)
    targets = np.asarray([classes.index(lang) for _, lang in examples])
    weights = np.asarray([counts[example] for example in examples], dtype=np.float64)
    classifier = LogisticRegression(C=c, max_iter=2000, random_state=seed)
    classifier.fit(features, targets, sample_weight=weights)
    return classifier, classes


def train_lid(
    pairs: Sequence[tuple[str, str]],
    *,
    version: str,
    trained_on: str,
    ngram_range: tuple[int, int] = DEFAULT_NGRAM_RANGE,
    n_features: int = DEFAULT_N_FEATURES,
    c: float = 1.0,
    seed: int = 13,
) -> LidModel:
    """Fit and export the numpy-only model that the API and (later) the browser load."""
    classifier, classes = fit_classifier(
        pairs, ngram_range=ngram_range, n_features=n_features, c=c, seed=seed
    )
    coef = np.asarray(classifier.coef_, dtype=np.float32)
    intercept = np.asarray(classifier.intercept_, dtype=np.float32)
    if coef.shape[0] == 1:
        # Binary LR stores one row for the positive class; expand to the softmax-equivalent pair.
        coef = np.vstack([np.zeros_like(coef[0]), coef[0]])
        intercept = np.asarray([0.0, intercept[0]], dtype=np.float32)
    return LidModel(
        version=version,
        classes=tuple(classes),
        ngram_range=ngram_range,
        n_features=n_features,
        weights=coef,
        bias=intercept,
        trained_on=trained_on,
    )


def evaluate_lid(model: LidModel, pairs: Sequence[tuple[str, str]]) -> dict[str, object]:
    """Token-level accuracy, macro-F1 and per-language precision / recall / F1."""
    gold = [lang for _, lang in pairs]
    cache: dict[str, str] = {}
    predicted = []
    for word, _ in pairs:
        if word not in cache:
            cache[word] = model.predict(word)
        predicted.append(cache[word])
    labels = sorted(set(gold) | set(model.classes))
    precision, recall, f1, support = precision_recall_fscore_support(
        gold, predicted, labels=labels, zero_division=0
    )
    return {
        "n_tokens": len(pairs),
        "accuracy": float(accuracy_score(gold, predicted)),
        "macro_f1": float(np.mean(f1)),
        "per_language": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(labels)
        },
    }
