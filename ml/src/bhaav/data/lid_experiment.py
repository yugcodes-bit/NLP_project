"""Train and evaluate the word-level LID model on SemEval-2020 SentiMix (Hinglish).

    uv run python -m bhaav.data.lid_experiment --run-id lid_charngram_sentimix_v1

Protocol (no test-set tuning):

* **train** — official train file (14k tweets): fit
* **val** — official validation file (3k tweets): choose the regularisation ``C``
* **test** — official test file (3k tweets): reported once, with the chosen ``C``

Only tokens the deployed tagger would actually send to the model are scored: gold tag ``Hin`` or
``Eng``, and a single Roman-script word under ``bhaav.data.lid.tokenize``. Emoji, numbers,
punctuation and Devanagari are decided by rule, not by the model.

Logistic regression with L-BFGS is a convex problem, so there are no random seeds to average
over; uncertainty is reported as a bootstrap 95% interval over tweets.

Outputs: the model at ``data/interim/lid/lid_model.json`` (git-ignored) and the run folder
``experiments/<run_id>/`` with config, metrics, validation predictions (no text), env and notes.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from bhaav.data.lid import LidModel, tokenize
from bhaav.data.lid_train import (
    DEFAULT_N_FEATURES,
    DEFAULT_NGRAM_RANGE,
    evaluate_lid,
    train_lid,
)
from bhaav.data.registry import DatasetStatus, load_registry
from bhaav.experiment import write_run_files, write_text
from bhaav.paths import ProjectPaths
from bhaav.schema import load_label_schema

DATASET = "sentimix20"
ARCHIVE = "Semeval_2020_task9_data.zip"
MEMBERS = {
    "train": "Semeval_2020_task9_data/Hinglish/Hinglish_train_14k_split_conll.txt",
    "val": "Semeval_2020_task9_data/Hinglish/Hinglish_dev_3k_split_conll.txt",
    "test": "Semeval_2020_task9_data/Hinglish/Hinglish_test_unalbelled_conll_updated.txt",
}
TAG_TO_LANG = {"Hin": "hi", "Eng": "en"}
C_GRID = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0)
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 2026


@dataclass(frozen=True)
class TaggedTweet:
    id: str
    tokens: tuple[tuple[str, str], ...]  # (token, source tag)


def parse_conll(text: str) -> list[TaggedTweet]:
    """Parse the SentiMix layout: a ``meta<TAB>id[<TAB>sentiment]`` line, then ``token<TAB>tag``
    lines, tweets separated by blank lines.

    A meta line is recognised by position (first line of a block), not by its text: the word
    "meta" also occurs as an ordinary token.
    """
    tweets: list[TaggedTweet] = []
    tweet_id: str | None = None
    tokens: list[tuple[str, str]] = []
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if not line.strip():
            if tweet_id is not None:
                tweets.append(TaggedTweet(tweet_id, tuple(tokens)))
            tweet_id, tokens = None, []
            continue
        fields = line.split("\t")
        if tweet_id is None:
            if fields[0] != "meta" or len(fields) < 2:
                raise ValueError(f"expected a meta line, got {fields[:2]!r}")
            tweet_id = fields[1].strip()
        elif len(fields) >= 2:
            tokens.append((fields[0], fields[1].strip()))
    if tweet_id is not None:
        tweets.append(TaggedTweet(tweet_id, tuple(tokens)))
    return tweets


def read_split(archive: Path, member: str) -> list[TaggedTweet]:
    with zipfile.ZipFile(archive) as zf:
        return parse_conll(zf.read(member).decode("utf-8"))


def model_tokens(tweet: TaggedTweet) -> list[tuple[int, str, str]]:
    """``(token index, word, language)`` for the tokens the model is responsible for."""
    scored: list[tuple[int, str, str]] = []
    for index, (token, tag) in enumerate(tweet.tokens):
        lang = TAG_TO_LANG.get(tag)
        if lang is None:
            continue
        pieces = tokenize(token)
        if len(pieces) == 1 and pieces[0].kind == "word" and pieces[0].script == "roman":
            scored.append((index, token, lang))
    return scored


def pairs_of(tweets: Sequence[TaggedTweet]) -> list[tuple[str, str]]:
    return [(word, lang) for tweet in tweets for _, word, lang in model_tokens(tweet)]


def coverage(tweets: Sequence[TaggedTweet]) -> dict[str, int]:
    """How the source tokens split into scored / rule-decided / skipped."""
    tags = Counter(tag for tweet in tweets for _, tag in tweet.tokens)
    scored = sum(len(model_tokens(tweet)) for tweet in tweets)
    language_tagged = tags.get("Hin", 0) + tags.get("Eng", 0)
    return {
        "tweets": len(tweets),
        "tokens": sum(tags.values()),
        "gold_hin_or_eng": language_tagged,
        "scored_roman_words": scored,
        "hin_or_eng_not_scored": language_tagged - scored,
    }


def _macro_f1(counts: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Macro-F1 over (hi, en) from rows of ``[hi→hi, hi→en, en→hi, en→en]`` (gold→predicted)."""
    hh, he, eh, ee = counts[..., 0], counts[..., 1], counts[..., 2], counts[..., 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        f1_hi = np.where(2 * hh + he + eh > 0, 2 * hh / (2 * hh + he + eh), 0.0)
        f1_en = np.where(2 * ee + he + eh > 0, 2 * ee / (2 * ee + he + eh), 0.0)
    return np.asarray((f1_hi + f1_en) / 2.0, dtype=np.float64)


def bootstrap_intervals(
    per_tweet: npt.NDArray[np.float64],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, list[float]]:
    """95% percentile intervals for macro-F1 and accuracy, resampling whole tweets."""
    rng = np.random.default_rng(seed)
    n = per_tweet.shape[0]
    picks = rng.integers(0, n, size=(resamples, n))
    totals = per_tweet[picks].sum(axis=1)
    accuracy = (totals[:, 0] + totals[:, 3]) / totals.sum(axis=1)
    low_f1, high_f1 = np.percentile(_macro_f1(totals), [2.5, 97.5])
    low_acc, high_acc = np.percentile(accuracy, [2.5, 97.5])
    return {
        "macro_f1_ci95": [float(low_f1), float(high_f1)],
        "accuracy_ci95": [float(low_acc), float(high_acc)],
    }


def predict_tweets(
    model: LidModel, tweets: Sequence[TaggedTweet]
) -> tuple[list[dict[str, str]], npt.NDArray[np.float64]]:
    """Per-tweet gold/predicted strings (``h``/``e`` per scored token) and confusion counts."""
    cache: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    counts = np.zeros((len(tweets), 4), dtype=np.float64)
    for position, tweet in enumerate(tweets):
        gold: list[str] = []
        predicted: list[str] = []
        for _, word, lang in model_tokens(tweet):
            if word not in cache:
                cache[word] = model.predict(word)
            gold.append(lang[0])
            predicted.append(cache[word][0])
            counts[position, (0 if lang == "hi" else 2) + (0 if cache[word] == "hi" else 1)] += 1
        rows.append({"id": tweet.id, "gold": "".join(gold), "pred": "".join(predicted)})
    return rows, counts


def evaluate_split(model: LidModel, tweets: Sequence[TaggedTweet]) -> dict[str, object]:
    metrics = evaluate_lid(model, pairs_of(tweets))
    _, counts = predict_tweets(model, tweets)
    majority = max(Counter(lang for _, lang in pairs_of(tweets)).values()) / max(
        1, int(counts.sum())
    )
    return {
        **metrics,
        **bootstrap_intervals(counts),
        "majority_class_accuracy": float(majority),
        "coverage": coverage(tweets),
    }


def render_notes(run_id: str, config: dict[str, object], metrics: dict[str, object]) -> str:
    test = metrics["test"]
    val = metrics["val"]
    assert isinstance(test, dict)
    assert isinstance(val, dict)
    low, high = test["macro_f1_ci95"]

    def row(name: str, split: dict[str, object], bold: str = "") -> str:
        coverage_ = split["coverage"]
        assert isinstance(coverage_, dict)
        cells = [
            name,
            str(coverage_["tweets"]),
            str(split["n_tokens"]),
            f"{split['accuracy']:.4f}",
            f"{bold}{split['macro_f1']:.4f}{bold}",
            f"{split['majority_class_accuracy']:.4f}",
        ]
        return "| " + " | ".join(cells) + " |"

    val_row = row("val (official validation)", val)
    test_row = row("**test (official test)**", test, bold="**")
    interval = f"[{low:.4f}, {high:.4f}]"
    return f"""# {run_id}

Word-level language identification (Hindi vs English) for Roman-script words: logistic regression
on hashed character 1–5-grams (ADR-006). Trained and evaluated on SemEval-2020 Task 9 SentiMix
(Hinglish), CC-BY-4.0, DOI 10.5281/zenodo.3974927.

## Result

| split | tweets | scored tokens | accuracy | macro-F1 | majority-class accuracy |
|---|---|---|---|---|---|
{val_row}
{test_row}

Test macro-F1 95% bootstrap interval over tweets ({BOOTSTRAP_RESAMPLES} resamples): {interval}.
`C` = {config["chosen_c"]} was chosen on val from {list(C_GRID)}; test was scored once.

## How to read this number

- It measures **agreement with SentiMix's own word tags**, and those tags are noisy: names and
  some non-Hindi, non-English words carry `Eng` or `Hin` tags in the source. The score is
  therefore not a clean accuracy against expert labels, and its ceiling is below 1.
- Only Roman-script words tagged `Hin`/`Eng` are scored. Emoji, numbers, punctuation and
  Devanagari are tagged by rule in `bhaav.data.lid` and are not part of this number.
- One deterministic fit (convex objective), so there is no seed variance to report; the interval
  above reflects sampling of tweets only.
- Train, val and test come from the same Twitter collection. Nothing here says how the tagger
  behaves on chat-style text.
- ADR-006 also calls for a comparison with HingBERT-LID. That is not done yet.

## Files

`config.yaml`, `metrics.json`, `predictions_val.jsonl` (per tweet: gold and predicted language of
each scored token as `h`/`e`; no text), `env.txt`.
"""


def run(paths: ProjectPaths, run_id: str) -> dict[str, object]:
    registry = load_registry(paths.datasets, load_label_schema(paths.label_schema))
    entry = registry.datasets[DATASET]
    if entry.status is not DatasetStatus.ALLOWED or entry.fetch is None:
        raise SystemExit(f"{DATASET} is not allowed in configs/datasets.yaml")
    archive = paths.raw / DATASET / ARCHIVE
    if not archive.is_file():
        raise SystemExit(f"{archive} missing: run python -m bhaav.data.fetch --dataset {DATASET}")

    splits = {name: read_split(archive, member) for name, member in MEMBERS.items()}
    train_pairs = pairs_of(splits["train"])
    val_pairs = pairs_of(splits["val"])

    sweep: dict[str, float] = {}
    for c in C_GRID:
        candidate = train_lid(train_pairs, version=run_id, trained_on=DATASET, c=c)
        macro_f1 = evaluate_lid(candidate, val_pairs)["macro_f1"]
        assert isinstance(macro_f1, float)
        sweep[str(c)] = macro_f1
        print(f"C={c}: val macro-F1 {macro_f1:.4f}")
    chosen = max(C_GRID, key=lambda c: (sweep[str(c)], -c))  # ties → stronger regularisation

    model = train_lid(
        train_pairs,
        version=run_id,
        trained_on=f"{DATASET} train ({entry.fetch.version})",
        c=chosen,
    )
    model.save(paths.lid_model)

    metrics: dict[str, object] = {
        "task": "word-level language identification (hi vs en), Roman-script words",
        "primary_metric": "macro_f1",
        "val_macro_f1_by_c": sweep,
        "val": evaluate_split(model, splits["val"]),
        "test": evaluate_split(model, splits["test"]),
        "train_coverage": coverage(splits["train"]),
        "model_bytes": paths.lid_model.stat().st_size,
    }
    config: dict[str, object] = {
        "run_id": run_id,
        "model": "multinomial logistic regression on hashed character n-grams",
        "ngram_range": list(DEFAULT_NGRAM_RANGE),
        "n_features": DEFAULT_N_FEATURES,
        "c_grid": list(C_GRID),
        "chosen_c": chosen,
        "selection": "highest val macro-F1; ties → smaller C",
        "dataset": DATASET,
        "dataset_version": entry.fetch.version,
        "dataset_license": entry.license,
        "archive_sha256": entry.fetch.files[0].sha256,
        "splits": MEMBERS,
        "label_map": TAG_TO_LANG,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "unit": "tweet"},
        "seeds": "none: deterministic convex fit",
    }

    run_dir = paths.experiments / run_id
    rows, _ = predict_tweets(model, splits["val"])
    write_text(run_dir / "predictions_val.jsonl", "".join(json.dumps(row) + "\n" for row in rows))
    write_run_files(
        run_dir,
        root=paths.root,
        config=config,
        metrics=metrics,
        notes=render_notes(run_id, config, metrics),
    )
    return metrics


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bhaav.data.lid_experiment", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--run-id", default="lid_charngram_sentimix_v1")
    args = parser.parse_args(argv)
    paths = ProjectPaths.discover()
    metrics = run(paths, args.run_id)
    test = metrics["test"]
    assert isinstance(test, dict)
    print(
        f"test macro-F1 {test['macro_f1']:.4f} (95% CI {test['macro_f1_ci95']}), "
        f"accuracy {test['accuracy']:.4f} → experiments/{args.run_id}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
