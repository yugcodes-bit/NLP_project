"""The SentiMix LID experiment, on a tiny synthetic archive in the real file layout."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import yaml

from bhaav.data import lid_experiment
from bhaav.data.lid import LidModel
from bhaav.data.lid_experiment import (
    MEMBERS,
    TaggedTweet,
    _macro_f1,
    bootstrap_intervals,
    coverage,
    model_tokens,
    pairs_of,
    parse_conll,
    predict_tweets,
)
from bhaav.paths import ProjectPaths

HINDI = "yaar aaj bahut nahi kya hai mujhe accha lagta dil ghar kal abhi raha".split()
ENGLISH = "the result meeting office happy today very phone service order train".split()


def conll(tweets: list[tuple[str, list[tuple[str, str]]]], *, sentiment: bool = True) -> str:
    """Build text in the SentiMix layout, CRLF line endings included."""
    blocks = []
    for tweet_id, tokens in tweets:
        meta = f"meta\t{tweet_id}\tneutral" if sentiment else f"meta\t{tweet_id}"
        blocks.append("\r\n".join([meta, *(f"{tok}\t{tag}" for tok, tag in tokens)]))
    return "\r\n\r\n".join(blocks) + "\r\n\r\n"


def synthetic_tweets(prefix: str, count: int) -> list[tuple[str, list[tuple[str, str]]]]:
    tweets = []
    for i in range(count):
        tokens = [
            (HINDI[i % len(HINDI)], "Hin"),
            (ENGLISH[i % len(ENGLISH)], "Eng"),
            (HINDI[(i + 3) % len(HINDI)], "Hin"),
            ("!!", "O"),
            (ENGLISH[(i + 5) % len(ENGLISH)], "Eng"),
        ]
        tweets.append((f"{prefix}{i}", tokens))
    return tweets


# ------------------------------------------------------------------ parsing


def test_parse_conll_reads_ids_tokens_and_tags() -> None:
    text = conll([("11", [("yaar", "Hin"), ("happy", "Eng")]), ("12", [("@", "O"), ("ok", "Eng")])])
    assert parse_conll(text) == [
        TaggedTweet("11", (("yaar", "Hin"), ("happy", "Eng"))),
        TaggedTweet("12", (("@", "O"), ("ok", "Eng"))),
    ]


def test_parse_conll_handles_the_test_file_layout_without_sentiment() -> None:
    tweets = parse_conll(conll([("7", [("kya", "Hin")])], sentiment=False))
    assert tweets == [TaggedTweet("7", (("kya", "Hin"),))]


def test_the_word_meta_inside_a_tweet_is_a_token_not_a_new_tweet() -> None:
    """The real train file has tokens spelled "meta"; only a block's first line is a header."""
    tweets = parse_conll(conll([("5", [("meta", "Eng"), ("data", "Eng")]), ("6", [("ok", "Eng")])]))
    assert [t.id for t in tweets] == ["5", "6"]
    assert tweets[0].tokens == (("meta", "Eng"), ("data", "Eng"))


def test_parse_conll_without_trailing_blank_line_and_bad_header() -> None:
    assert parse_conll("meta\t1\tneutral\nyaar\tHin") == [TaggedTweet("1", (("yaar", "Hin"),))]
    with pytest.raises(ValueError, match="expected a meta line"):
        parse_conll("yaar\tHin\n")


# ------------------------------------------------------------------ which tokens are scored


def test_only_roman_words_tagged_hin_or_eng_are_scored() -> None:
    tweet = TaggedTweet(
        "1",
        (
            ("yaar", "Hin"),  # scored
            ("Happy", "Eng"),  # scored
            ("!!", "O"),  # not a language tag
            ("😂", "EMT"),  # not a language tag
            ("2", "Eng"),  # a number: decided by rule
            ("खुश", "Hin"),  # Devanagari: decided by rule
            ("don't", "Eng"),  # one word with an apostrophe: scored
            ("a-b", "Eng"),  # splits into three tokens: skipped
        ),
    )
    assert model_tokens(tweet) == [(0, "yaar", "hi"), (1, "Happy", "en"), (6, "don't", "en")]
    assert pairs_of([tweet]) == [("yaar", "hi"), ("Happy", "en"), ("don't", "en")]
    assert coverage([tweet]) == {
        "tweets": 1,
        "tokens": 8,
        "gold_hin_or_eng": 6,
        "scored_roman_words": 3,
        "hin_or_eng_not_scored": 3,
    }


# ------------------------------------------------------------------ metrics


def test_macro_f1_from_confusion_counts_by_hand() -> None:
    """gold hi: 8 right, 2 called en. gold en: 1 called hi, 9 right.

    F1(hi) = 2·8 / (2·8 + 2 + 1) = 16/19;  F1(en) = 2·9 / (2·9 + 2 + 1) = 18/21.
    """
    counts = np.asarray([8.0, 2.0, 1.0, 9.0])
    assert _macro_f1(counts) == pytest.approx((16 / 19 + 18 / 21) / 2)
    assert _macro_f1(np.asarray([5.0, 0.0, 0.0, 5.0])) == pytest.approx(1.0)
    assert _macro_f1(np.asarray([0.0, 0.0, 0.0, 0.0])) == pytest.approx(0.0)


def test_bootstrap_is_deterministic_and_brackets_the_point_estimate() -> None:
    rng = np.random.default_rng(0)
    per_tweet = rng.integers(0, 6, size=(200, 4)).astype(np.float64)
    per_tweet[:, 0] += 5  # mostly-correct hi
    per_tweet[:, 3] += 5  # mostly-correct en
    first = bootstrap_intervals(per_tweet, resamples=300, seed=1)
    assert first == bootstrap_intervals(per_tweet, resamples=300, seed=1)
    assert first != bootstrap_intervals(per_tweet, resamples=300, seed=2)

    point = float(_macro_f1(per_tweet.sum(axis=0)))
    low, high = first["macro_f1_ci95"]
    assert low < point < high
    assert 0.0 < high - low < 0.1


def test_bootstrap_of_a_perfect_tagger_is_exactly_one() -> None:
    per_tweet = np.tile(np.asarray([3.0, 0.0, 0.0, 2.0]), (50, 1))
    assert bootstrap_intervals(per_tweet, resamples=100) == {
        "macro_f1_ci95": [1.0, 1.0],
        "accuracy_ci95": [1.0, 1.0],
    }


def test_predict_tweets_rows_carry_no_text(toy_lid: LidModel) -> None:
    tweets = [TaggedTweet("9", (("bahut", "Hin"), ("happy", "Eng"), ("!!", "O"), ("happy", "Hin")))]
    rows, counts = predict_tweets(toy_lid, tweets)
    assert rows == [{"id": "9", "gold": "heh", "pred": "hee"}]
    # hi→hi once, hi→en once (the mis-tagged "happy"), en→en once.
    assert counts.tolist() == [[1.0, 1.0, 0.0, 1.0]]


# ------------------------------------------------------------------ the whole run


REGISTRY = """
mapping_version: "t"
datasets:
  sentimix20:
    name: "Synthetic stand-in for SentiMix (tests only)"
    status: {status}
    url: "https://example.invalid/sentimix"
    license: "CC0-1.0 (synthetic)"
    license_url: "https://example.invalid/sentimix/LICENSE"
    verified_on: 2026-10-02
    approved: "test fixture"
    fetch:
      version: "test-version"
      files:
        - {{url: "https://example.invalid/s.zip", path: Semeval_2020_task9_data.zip}}
"""


@pytest.fixture
def sentimix_project(project: ProjectPaths) -> ProjectPaths:
    Path(project.datasets).write_text(REGISTRY.format(status="allowed"), encoding="utf-8")
    archive = project.raw / "sentimix20" / "Semeval_2020_task9_data.zip"
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(MEMBERS["train"], conll(synthetic_tweets("tr", 120)))
        zf.writestr(MEMBERS["val"], conll(synthetic_tweets("va", 30)))
        zf.writestr(MEMBERS["test"], conll(synthetic_tweets("te", 30), sentiment=False))
    # The experiment records the git state of the project root; a temp dir has none.
    return project


def test_run_writes_the_model_and_a_complete_experiment_folder(
    sentimix_project: ProjectPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert lid_experiment.main(["--run-id", "lid_test_run"]) == 0
    out = capsys.readouterr().out
    assert "test macro-F1" in out

    model = LidModel.load(sentimix_project.lid_model)
    assert model.classes == ("en", "hi")
    assert model.version == "lid_test_run"
    assert "test-version" in model.trained_on
    assert not model.dummy

    run_dir = sentimix_project.experiments / "lid_test_run"
    assert {p.name for p in run_dir.iterdir()} == {
        "config.yaml",
        "metrics.json",
        "predictions_val.jsonl",
        "env.txt",
        "NOTES.md",
    }

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["primary_metric"] == "macro_f1"
    assert set(metrics["val_macro_f1_by_c"]) == {str(c) for c in lid_experiment.C_GRID}
    for split in ("val", "test"):
        assert metrics[split]["coverage"]["tweets"] == 30
        assert metrics[split]["n_tokens"] == 120  # 4 scored words per tweet; "!!" is not scored
        assert 0.0 <= metrics[split]["macro_f1"] <= 1.0
        assert len(metrics[split]["macro_f1_ci95"]) == 2
        assert metrics[split]["majority_class_accuracy"] == pytest.approx(0.5)
    assert metrics["train_coverage"]["scored_roman_words"] == 480
    # These words are trivially separable, so a correct pipeline must get them all.
    assert metrics["test"]["macro_f1"] == pytest.approx(1.0)

    config = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config["dataset"] == "sentimix20"
    assert config["dataset_version"] == "test-version"
    assert config["chosen_c"] in lid_experiment.C_GRID
    assert config["seeds"].startswith("none")

    predictions = [
        json.loads(line)
        for line in (run_dir / "predictions_val.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(predictions) == 30
    assert set(predictions[0]) == {"id", "gold", "pred"}
    assert set(predictions[0]["gold"]) <= {"h", "e"}
    raw_words = set(HINDI) | set(ENGLISH)
    assert not any(word in json.dumps(predictions) for word in raw_words if len(word) > 3)

    env = (run_dir / "env.txt").read_text(encoding="utf-8")
    assert "git_sha:" in env
    assert "scikit-learn==" in env
    notes = (run_dir / "NOTES.md").read_text(encoding="utf-8")
    assert "tags are noisy" in notes
    assert "HingBERT-LID" in notes


def test_run_refuses_a_dataset_that_is_not_allowed(sentimix_project: ProjectPaths) -> None:
    Path(sentimix_project.datasets).write_text(
        REGISTRY.format(status="to_verify"), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="not allowed"):
        lid_experiment.main([])


def test_run_needs_the_fetched_archive(sentimix_project: ProjectPaths) -> None:
    (sentimix_project.raw / "sentimix20" / "Semeval_2020_task9_data.zip").unlink()
    with pytest.raises(SystemExit, match="missing"):
        lid_experiment.main([])
