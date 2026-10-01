from __future__ import annotations

import pytest

from bhaav.data.dedupe import Item, dedupe_key, find_duplicates, jaccard, shingles


def item(
    id_: str,
    text: str,
    split: str = "train",
    source: str = "a",
    labels: tuple[str, ...] = ("joy",),
    source_rank: int = 0,
    protected: bool = False,
) -> Item:
    return Item(
        id=id_,
        source=source,
        split=split,
        text_norm=text,
        labels=frozenset(labels),
        source_rank=source_rank,
        protected=protected,
    )


# ------------------------------------------------------------------ comparison key


def test_key_ignores_punctuation_and_repeated_characters() -> None:
    """The example from docs/17 §2."""
    assert dedupe_key("bahut accha") == dedupe_key("bahut acha!!") == "bahut acha"


def test_key_drops_placeholders_but_keeps_emoji() -> None:
    assert dedupe_key("<user> dekho <url> kya scene hai") == "dekho kya scene hai"
    assert dedupe_key("maza aa gaya 😂") != dedupe_key("maza aa gaya 😢")


def test_key_keeps_devanagari_and_digits() -> None:
    assert dedupe_key("आज 2 बजे, मिलते हैं!") == "आज 2 बजे मिलते हैं"


def test_key_falls_back_to_the_text_when_nothing_is_left() -> None:
    assert dedupe_key("!!") == "!!"
    assert dedupe_key("??") == "??"


def test_shingles_and_jaccard() -> None:
    assert shingles("abc") == {"abc"}
    assert shingles("abcdefg") == {"abcde", "bcdef", "cdefg"}
    assert jaccard(shingles("abcdefg"), shingles("abcdefg")) == 1.0
    # {abcde, bcdef} vs {bcdef, cdefg}: 1 shared of 3 distinct.
    assert jaccard(shingles("abcdef"), shingles("bcdefg")) == pytest.approx(1 / 3)
    assert jaccard(frozenset(), frozenset()) == 1.0


# ------------------------------------------------------------------ duplicate detection


def test_planted_near_duplicate_across_splits_is_caught() -> None:
    """docs/17 §2: "bahut accha" vs "bahut acha!!" across splits."""
    removals = find_duplicates(
        [item("a-1", "bahut accha", "train"), item("a-2", "bahut acha!!", "val")]
    )
    assert [(r.id, r.kept_id, r.tier) for r in removals] == [("a-1", "a-2", "punct_insensitive")]


def test_exact_duplicate_tier() -> None:
    removals = find_duplicates(
        [item("a-1", "yaar aaj bahut khush hu"), item("a-2", "yaar aaj bahut khush hu")]
    )
    assert [(r.id, r.kept_id, r.tier, r.jaccard) for r in removals] == [
        ("a-2", "a-1", "exact", 1.0)
    ]


def test_near_duplicate_tier_uses_jaccard_threshold() -> None:
    base = "teen ghante se line mein khada hu aur counter pe koi sunne wala hi nahi hai"
    near = base + " yaar"
    far = "teen ghante se train ka wait kar raha hu aur koi announcement hi nahi hui"
    score = jaccard(shingles(dedupe_key(base)), shingles(dedupe_key(near)))
    assert score >= 0.8
    assert jaccard(shingles(dedupe_key(base)), shingles(dedupe_key(far))) < 0.8

    removals = find_duplicates([item("a-1", base), item("a-2", near), item("a-3", far)])
    assert [(r.id, r.kept_id, r.tier) for r in removals] == [("a-2", "a-1", "near")]
    assert removals[0].jaccard == pytest.approx(score, abs=1e-4)


def test_similar_but_distinct_short_texts_are_kept() -> None:
    texts = ["bahut acha", "bahut bura", "bahut achi baat", "kya baat hai", "kya baat thi"]
    assert find_duplicates([item(f"a-{i}", t) for i, t in enumerate(texts)]) == []


@pytest.mark.parametrize(
    ("splits", "kept"),
    [
        (("train", "val"), "a-2"),
        (("train", "test_in_domain"), "a-2"),
        (("val", "test_in_domain"), "a-2"),
        (("test_in_domain", "train"), "a-1"),
        (("ood_eval", "train"), "a-1"),
        (("train", "train"), "a-1"),
    ],
)
def test_evaluation_copy_survives(splits: tuple[str, str], kept: str) -> None:
    removals = find_duplicates(
        [item("a-1", "same text here", splits[0]), item("a-2", "same text here", splits[1])]
    )
    assert [r.kept_id for r in removals] == [kept]


def test_earlier_source_wins_within_a_split() -> None:
    removals = find_duplicates(
        [
            item("b-1", "same text here", source="b", source_rank=1),
            item("a-1", "same text here", source="a", source_rank=0),
        ]
    )
    assert [(r.id, r.kept_id, r.source, r.kept_source) for r in removals] == [
        ("b-1", "a-1", "b", "a")
    ]


def test_protected_records_are_never_removed() -> None:
    gold = [
        item(
            "g-1",
            "same text here",
            "gold",
            source="gold",
            labels=(),
            source_rank=-1,
            protected=True,
        ),
        item(
            "g-2",
            "same text here!!",
            "gold",
            source="gold",
            labels=(),
            source_rank=-1,
            protected=True,
        ),
    ]
    train = [
        item("a-1", "same text here", "test_in_domain"),
        item("a-2", "same text here.", "train"),
    ]
    removals = find_duplicates([*gold, *train])
    assert sorted(r.id for r in removals) == ["a-1", "a-2"]
    assert {r.kept_id for r in removals} == {"g-1"}


def test_label_conflict_is_flagged() -> None:
    removals = find_duplicates(
        [
            item("a-1", "same text here", labels=("joy",)),
            item("a-2", "same text here", labels=("sadness",)),
            item("a-3", "same text here", labels=("joy",)),
        ]
    )
    assert {r.id: r.label_conflict for r in removals} == {"a-2": True, "a-3": False}


def test_cluster_of_many_keeps_exactly_one() -> None:
    variants = [
        "kya baat hai bhai",
        "kya baat hai bhai!!",
        "kya baat hai bhaiii",
        "kya baat hai, bhai",
    ]
    removals = find_duplicates([item(f"a-{i}", t) for i, t in enumerate(variants)])
    assert len(removals) == 3
    assert {r.kept_id for r in removals} == {"a-0"}


def test_result_is_deterministic_and_order_independent() -> None:
    items = [
        item(f"a-{i}", t)
        for i, t in enumerate(["x y z same", "x y z same", "other text", "x y z same!"])
    ]
    assert find_duplicates(items) == find_duplicates(list(reversed(items)))


def test_empty_input() -> None:
    assert find_duplicates([]) == []
