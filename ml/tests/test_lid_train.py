from __future__ import annotations

import numpy as np
import pytest

from bhaav.data.lid import LidModel
from bhaav.data.lid_train import design_matrix, evaluate_lid, fit_classifier, train_lid

Pairs = list[tuple[str, str]]


def test_binary_model_has_one_row_per_class(toy_lid: LidModel) -> None:
    assert toy_lid.classes == ("en", "hi")
    assert toy_lid.weights.shape == (2, 1 << 12)
    assert toy_lid.bias.shape == (2,)


def test_fits_its_training_words(toy_lid: LidModel, lid_pairs: Pairs) -> None:
    """Sanity only: this is training-set accuracy on a toy list, not a reportable number."""
    metrics = evaluate_lid(toy_lid, lid_pairs)
    assert metrics["n_tokens"] == len(lid_pairs)
    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["macro_f1"] == pytest.approx(1.0)


def test_training_is_deterministic(lid_pairs: Pairs) -> None:
    first = train_lid(lid_pairs, version="a", trained_on="t", n_features=1 << 10)
    second = train_lid(list(reversed(lid_pairs)), version="a", trained_on="t", n_features=1 << 10)
    assert (first.weights == second.weights).all()


@pytest.mark.parametrize(
    "extra", [[], [("xin", "zz"), ("qing", "zz"), ("zhong", "zz"), ("xie", "zz")]]
)
def test_exported_model_matches_scikit_learn(lid_pairs: Pairs, extra: Pairs) -> None:
    """The numpy-only export must score words exactly like the classifier it came from.

    Covers both layouts: binary (one coefficient row expanded to two) and multinomial.
    """
    pairs = [*lid_pairs, *extra]
    settings = {"ngram_range": (1, 5), "n_features": 1 << 12, "c": 10.0, "seed": 13}
    classifier, classes = fit_classifier(pairs, **settings)  # type: ignore[arg-type]
    model = train_lid(pairs, version="p", trained_on="t", **settings)  # type: ignore[arg-type]
    assert list(model.classes) == classes

    words = ["bahut", "happy", "Zindagi", "meeting", "xyzzy", "q", "ghabrahat", "xin"]
    expected = classifier.predict_log_proba(design_matrix(words, (1, 5), 1 << 12))
    for row, word in enumerate(words):
        logits = model.logits(word).astype(np.float64)
        log_proba = logits - np.log(np.exp(logits).sum())
        np.testing.assert_allclose(log_proba, expected[row], atol=1e-4)
        assert model.predict(word) == classes[int(np.argmax(expected[row]))]


def test_three_classes_use_multinomial_weights(lid_pairs: Pairs) -> None:
    pairs = [*lid_pairs, ("xin", "zz"), ("qing", "zz"), ("zhong", "zz"), ("xie", "zz")]
    model = train_lid(pairs, version="m", trained_on="t", n_features=1 << 10, c=100.0)
    assert model.classes == ("en", "hi", "zz")
    assert model.weights.shape == (3, 1 << 10)
    assert model.predict("xin") == "zz"


def test_repeated_instances_weigh_more() -> None:
    """A word seen with both tags goes to the tag it carries more often."""
    base = [("yaar", "hi"), ("bahut", "hi"), ("happy", "en"), ("very", "en")]
    mostly_hindi = train_lid(
        [*base, *[("main", "hi")] * 9, ("main", "en")], version="a", trained_on="t"
    )
    mostly_english = train_lid(
        [*base, *[("main", "en")] * 9, ("main", "hi")], version="a", trained_on="t"
    )
    assert mostly_hindi.predict("main") == "hi"
    assert mostly_english.predict("main") == "en"


def test_evaluate_reports_per_language_scores(toy_lid: LidModel) -> None:
    metrics = evaluate_lid(toy_lid, [("bahut", "hi"), ("happy", "en"), ("happy", "hi")])
    per_language = metrics["per_language"]
    assert isinstance(per_language, dict)
    assert per_language["hi"]["support"] == 2
    assert per_language["en"]["support"] == 1
    assert metrics["accuracy"] == pytest.approx(2 / 3)


def test_single_language_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least two"):
        train_lid([("yaar", "hi")], version="a", trained_on="t")
