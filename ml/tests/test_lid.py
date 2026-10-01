from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bhaav.data.lid import (
    LidModel,
    analyze_code_mixing,
    code_mixing_index,
    detect_script,
    fnv1a_32,
    lang_share,
    ngram_features,
    tag_tokens,
    tokenize,
)


def texts(text: str) -> list[str]:
    return [t.text for t in tokenize(text)]


def kinds(text: str) -> list[str]:
    return [t.kind for t in tokenize(text)]


# ------------------------------------------------------------------ tokenisation


def test_tokenize_words_and_emoji() -> None:
    assert texts("yaar aaj ka din bahut bekaar tha 😩") == [
        "yaar", "aaj", "ka", "din", "bahut", "bekaar", "tha", "😩",
    ]  # fmt: skip


def test_tokenize_separates_punctuation_runs() -> None:
    assert texts("kya baat hai bhai, maza aa gaya!!") == [
        "kya", "baat", "hai", "bhai", ",", "maza", "aa", "gaya", "!!",
    ]  # fmt: skip


def test_tokenize_kinds() -> None:
    assert kinds("<url> dekho 2 बजे !! 😂 gr8") == [
        "placeholder", "word", "number", "word", "punct", "emoji", "word",
    ]  # fmt: skip


def test_tokenize_keeps_apostrophe_words_and_emoji_sequences_whole() -> None:
    assert texts("don't worry 👨\u200d👩\u200d👧 🇮🇳 ❤\ufe0f") == [
        "don't", "worry", "👨\u200d👩\u200d👧", "🇮🇳", "❤\ufe0f",
    ]  # fmt: skip


def test_tokenize_splits_emoji_from_adjacent_punctuation_and_words() -> None:
    assert texts("gaya!!😂😂ok") == ["gaya", "!!", "😂", "😂", "ok"]


def test_tokenize_keeps_devanagari_matras_attached() -> None:
    assert texts("सच में बहुत खुश हूँ।") == ["सच", "में", "बहुत", "खुश", "हूँ", "।"]


def test_tokenize_empty() -> None:
    assert tokenize("") == []


# ------------------------------------------------------------------ script


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("yaar aaj bahut khush hu", "roman"),
        ("सच में बहुत खुश हूँ आज", "devanagari"),
        ("बहुत khush हूँ yaar", "mixed"),
        ("खुशhoon", "mixed"),
        ("😂😂 !!", "roman"),
        ("", "roman"),
        ("१२३ बजे", "devanagari"),
    ],
)
def test_detect_script(text: str, script: str) -> None:
    assert detect_script(text) == script


# ------------------------------------------------------------------ CMI


def test_cmi_all_hindi_is_zero() -> None:
    assert code_mixing_index(["hi"] * 7) == 0.0


def test_cmi_fifty_fifty_is_fifty() -> None:
    assert code_mixing_index(["hi", "en", "hi", "en"]) == 50.0


def test_cmi_only_language_independent_tokens_is_zero() -> None:
    assert code_mixing_index(["univ", "univ"]) == 0.0
    assert code_mixing_index(["univ", "ne"]) == 0.0
    assert code_mixing_index([]) == 0.0


def test_cmi_hand_computed_example() -> None:
    """N = 6 tokens, u = 1 (the emoji), dominant language hi = 3 of the 5 language tokens.

    CMI = 100 × (1 − 3 / (6 − 1)) = 100 × 0.4 = 40.
    """
    assert code_mixing_index(["hi", "hi", "hi", "en", "en", "univ"]) == pytest.approx(40.0)


def test_cmi_is_symmetric_in_the_dominant_language() -> None:
    assert code_mixing_index(["en", "en", "en", "hi"]) == code_mixing_index(
        ["hi", "hi", "hi", "en"]
    )


def test_cmi_counts_other_scripts_as_a_language() -> None:
    assert code_mixing_index(["hi", "hi", "other", "en"]) == pytest.approx(50.0)


def test_lang_share() -> None:
    assert lang_share(["hi", "hi", "hi", "en", "univ"]) == {"hi": 0.75, "en": 0.25}
    assert lang_share(["univ"]) == {"hi": 0.0, "en": 0.0}
    assert lang_share(["hi", "other"]) == {"hi": 0.5, "en": 0.0, "other": 0.5}


# ------------------------------------------------------------------ hashing + model


def test_fnv1a_32_reference_vectors() -> None:
    """Published FNV-1a 32-bit test vectors; the TypeScript port must reproduce these."""
    assert fnv1a_32(b"") == 0x811C9DC5
    assert fnv1a_32(b"a") == 0xE40C292C
    assert fnv1a_32(b"foobar") == 0xBF9CF968


def test_ngram_features_are_case_insensitive_sorted_and_bounded() -> None:
    features = ngram_features("Khush", (1, 5), 4096)
    assert features == ngram_features("khush", (1, 5), 4096)
    assert features == sorted(set(features))
    assert all(0 <= index < 4096 for index in features)
    # "^dost$" (6 chars, no repeats) has 6 + 5 + 4 + 3 + 2 = 20 n-grams of length 1–5.
    assert len(ngram_features("dost", (1, 5), 1 << 24)) == 20
    # "^khush$" has 7 + 6 + 5 + 4 + 3 = 25, but "h" occurs twice and features are distinct → 24.
    assert len(ngram_features("khush", (1, 5), 1 << 24)) == 24


def test_model_round_trips_through_json(toy_lid: LidModel, tmp_path: Path) -> None:
    path = tmp_path / "lid" / "model.json"
    toy_lid.save(path)
    loaded = LidModel.load(path)
    assert loaded.classes == toy_lid.classes
    assert loaded.version == "toy"
    assert not loaded.dummy
    for word in ("bahut", "happy", "zindagi", "meeting", "xyzzy"):
        np.testing.assert_allclose(loaded.logits(word), toy_lid.logits(word), rtol=1e-6)
        assert loaded.predict(word) == toy_lid.predict(word)


def test_model_rejects_wrong_format_and_shapes(toy_lid: LidModel) -> None:
    with pytest.raises(ValueError, match="not a bhaav-lid"):
        LidModel.from_dict({"format": "something-else"})
    with pytest.raises(ValueError, match="format_version"):
        LidModel.from_dict({**toy_lid.to_dict(), "format_version": 99})
    with pytest.raises(ValueError, match="weights shape"):
        LidModel(
            "v", ("en", "hi"), (1, 5), 8, np.zeros((2, 4), np.float32), np.zeros(2, np.float32)
        )
    with pytest.raises(ValueError, match="bias shape"):
        LidModel(
            "v", ("en", "hi"), (1, 5), 8, np.zeros((2, 8), np.float32), np.zeros(3, np.float32)
        )


# ------------------------------------------------------------------ tagging


def test_tagging_rules(toy_lid: LidModel) -> None:
    tagged = tag_tokens(tokenize("bahut happy हूँ 😂 !! 2 <url> বাংলা"), toy_lid)
    assert [(t.text, t.lang) for t in tagged] == [
        ("bahut", "hi"),  # Roman word → model
        ("happy", "en"),  # Roman word → model
        ("हूँ", "hi"),  # Devanagari → hi by script
        ("😂", "univ"),
        ("!!", "univ"),
        ("2", "univ"),
        ("<url>", "univ"),
        ("বাংলা", "other"),  # any other script
    ]


def test_analyze_code_mixing(toy_lid: LidModel) -> None:
    analysis = analyze_code_mixing("yaar aaj meeting cancel ho gaya 😂", toy_lid)
    langs = [t.lang for t in analysis.tokens]
    assert langs[-1] == "univ"
    assert analysis.script == "roman"
    assert analysis.cmi == pytest.approx(code_mixing_index(langs))
    assert analysis.lang_share == lang_share(langs)
    assert 0.0 < analysis.cmi <= 50.0
