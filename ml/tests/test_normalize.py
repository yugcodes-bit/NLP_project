from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import regex
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from bhaav.data.normalize import NormalizationConfig, Normalizer, load_normalization_config

CASES: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "fixtures" / "normalize_cases.json").read_text(encoding="utf-8")
)

# Emoji parts and invisible characters, as code points so nothing in this file is invisible:
# face-with-tears, heart, VS16, ZWJ, ZWSP, ZWNJ, BOM, thumbs-up, skin tone, two regional
# indicators, LF, TAB, NBSP, E-acute, combining acute.
_SPECIAL_CODE_POINTS = (
    0x1F602, 0x2764, 0xFE0F, 0x200D, 0x200B, 0x200C, 0xFEFF, 0x1F44D, 0x1F3FD, 0x1F1EE, 0x1F1F3,
    0x0A, 0x09, 0xA0, 0xC9, 0x301,
)  # fmt: skip
# Characters that exercise every rule
# characters we strip, and the punctuation the URL / mention / hashtag rules key on.
_ALPHABET = st.sampled_from(
    list("abAB aeiou hmrtwxWX.:/@#_!?<>-'019०१")
    + list("कखगािीुंँ्ह़")
    + [chr(code) for code in _SPECIAL_CODE_POINTS]
)
_TEXT = st.one_of(st.text(max_size=80), st.text(alphabet=_ALPHABET, max_size=60))
_RUN_RE = regex.compile(r"([^\p{Nd}])\1{2,}")


def test_fixture_has_enough_cases() -> None:
    names = [case["name"] for case in CASES]
    assert len(CASES) >= 40
    assert len(set(names)) == len(names)


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_fixture_case(normalizer: Normalizer, case: dict[str, Any]) -> None:
    result = normalizer(case["input"])
    assert result.text == case["expected"]
    assert result.has_caps_shouting is case["caps"]


@settings(max_examples=500, deadline=None)
@given(_TEXT)
def test_idempotent(normalizer: Normalizer, text: str) -> None:
    once = normalizer.normalize(text)
    assert normalizer.normalize(once) == once


@settings(max_examples=500, deadline=None)
@given(_TEXT)
def test_output_invariants(normalizer: Normalizer, text: str) -> None:
    out = normalizer.normalize(text)
    assert out == out.strip(" ")
    assert "  " not in out
    assert not any(ch in out for ch in "\t\n\r\u200b\u200c\ufeff\u00a0")
    assert _RUN_RE.search(out) is None
    assert out == out.lower()


def test_real_config_loads(repo_root: Path) -> None:
    config = load_normalization_config(repo_root / "configs" / "normalization.yaml")
    assert config.max_char_repeat == 2
    assert config.max_chars == 1000
    assert config.replace.url == "<url>"


def _config(repo_root: Path, **overrides: Any) -> NormalizationConfig:
    with (repo_root / "configs" / "normalization.yaml").open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return NormalizationConfig.model_validate({**raw, **overrides})


def test_keep_emoji_false_removes_emoji(repo_root: Path) -> None:
    no_emoji = Normalizer(_config(repo_root, keep_emoji=False))
    assert no_emoji.normalize("maza aa gaya 😂😂 yaar ❤\ufe0f") == "maza aa gaya yaar"


def test_hashtag_keep_mode(repo_root: Path) -> None:
    keep = Normalizer(_config(repo_root, hashtag="keep"))
    assert keep.normalize("#BahutKhush") == "#bahutkhush"


def test_max_char_repeat_is_configurable(repo_root: Path) -> None:
    assert Normalizer(_config(repo_root, max_char_repeat=3)).normalize("sooooo") == "sooo"
    assert Normalizer(_config(repo_root, max_char_repeat=1)).normalize("sooooo good") == "so god"


@pytest.mark.parametrize("flag", ["emoji_demojize", "canonicalize_variants"])
def test_ablation_flags_fail_loudly_until_implemented(repo_root: Path, flag: str) -> None:
    with pytest.raises(NotImplementedError):
        Normalizer(_config(repo_root, **{flag: True}))


@pytest.mark.parametrize("token", ["", "<URL>", "<u r l>", "<urrrl>"])
def test_replacement_token_must_be_stable(repo_root: Path, token: str) -> None:
    with pytest.raises(ValidationError, match="must be non-empty"):
        _config(repo_root, replace={"url": token, "mention": "<user>"})
