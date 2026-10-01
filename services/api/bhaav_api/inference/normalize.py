# GENERATED FILE - do not edit. Source: ml/src/bhaav/data/normalize.py
# Regenerate with: uv run python -m bhaav.sync_shared
"""Text normalisation shared by the ML pipeline, the API and (through fixtures) the web app.

Rules: ``docs/08_ml_methodology.md`` §2.1. Flags and replacement tokens:
``configs/normalization.yaml``.

This module is copied verbatim into ``services/api`` by ``bhaav.sync_shared`` (ADR-008), so it
must only import the standard library, ``regex``, ``pydantic`` and ``pyyaml``.

One pass applies, in order:

1. repair lone surrogates, strip invisible characters (zero-width, bidi marks, control chars);
   ZWJ survives only inside an emoji sequence
2. Unicode NFC
3. collapse whitespace
4. URLs → ``<url>``, @mentions → ``<user>`` (numbers are kept)
5. hashtags: ``#BahutKhush`` → ``Bahut Khush``
6. lower-case (Devanagari has no case, so this only affects Roman text), NFC again
7. collapse elongation to ``max_char_repeat`` (``sooooo`` → ``soo``, ``!!!!`` → ``!!``);
   digits are exempt
8. emoji are kept (``keep_emoji``)

Passes repeat until the text stops changing, which makes the function idempotent:
``normalize(normalize(x)) == normalize(x)``. Real text converges in one pass.

Length is not enforced here. ``max_chars`` is the input contract checked by callers
(the API rejects longer input; the UI shows a counter), counted in Unicode code points.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

import regex
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# One emoji "unit": a pictograph (+ variation selector or skin tone), optionally ZWJ-joined to
# more of them; or a flag (regional-indicator pair); or a keycap.
EMOJI_ATOM = r"\p{Extended_Pictographic}[\ufe0f\U0001F3FB-\U0001F3FF]?"
EMOJI_SEQUENCE = (
    rf"(?:{EMOJI_ATOM}(?:\u200d{EMOJI_ATOM})*"
    r"|[\U0001F1E6-\U0001F1FF]{2}"
    r"|[0-9#*]\ufe0f?\u20e3)"
)

# Explicit lists (not \s) so the TypeScript port can match byte for byte.
_WHITESPACE_RE = regex.compile(
    r"[\t\n\x0B\x0C\r \x85\xA0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+"
)
_INVISIBLE_RE = regex.compile(
    r"[\x00-\x08\x0E-\x1F\x7F\x80-\x84\x86-\x9F\xAD"
    r"\u200b\u200c\u200e\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]"
)
_STRAY_ZWJ_RE = regex.compile(rf"(?<!{EMOJI_ATOM})\u200d|\u200d(?!\p{{Extended_Pictographic}})")
_URL_RE = regex.compile(r"(?<![A-Za-z0-9])(?:https?://|www\.)[^ ]+", regex.IGNORECASE)
_MENTION_RE = regex.compile(r"(?<![A-Za-z0-9_.])@[A-Za-z0-9_]+")
# A hashtag needs at least one letter, so "#1" and "c#" are left alone.
_HASHTAG_RE = regex.compile(r"(?<![A-Za-z0-9_&#@])#(?=[\p{N}_]*\p{L})([\p{L}\p{M}\p{N}_]+)")
_CAMEL_RE = regex.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SHOUT_RE = regex.compile(r"(?<![A-Za-z])[A-Z]{4,}(?![A-Za-z])")
_EMOJI_RE = regex.compile(EMOJI_SEQUENCE)

_MAX_PASSES = 5


class ReplaceTokens(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    mention: str


class NormalizationConfig(BaseModel):
    """Typed view of ``configs/normalization.yaml``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    unicode_form: Literal["NFC"]
    strip_zero_width: bool
    replace: ReplaceTokens
    max_char_repeat: int = Field(ge=1)
    lowercase_roman: bool
    keep_emoji: bool
    emoji_demojize: bool
    hashtag: Literal["split_camel_case", "keep"]
    canonicalize_variants: bool
    max_chars: int = Field(gt=0)

    @model_validator(mode="after")
    def _check_replacement_tokens(self) -> Self:
        run = regex.compile(rf"(.)\1{{{self.max_char_repeat},}}")
        for name, token in (("url", self.replace.url), ("mention", self.replace.mention)):
            if not token or token != token.lower() or " " in token or run.search(token):
                raise ValueError(
                    f"replace.{name}={token!r} must be non-empty, lower-case, without spaces, and "
                    "must survive the elongation rule"
                )
        return self


def load_normalization_config(path: Path) -> NormalizationConfig:
    with path.open(encoding="utf-8") as fh:
        return NormalizationConfig.model_validate(yaml.safe_load(fh))


@dataclass(frozen=True, slots=True)
class NormalizedText:
    text: str
    #: A run of 4+ capital letters was present before lower-casing. Analysis only, never a feature.
    has_caps_shouting: bool


def _split_hashtag(match: regex.Match[str]) -> str:
    return _CAMEL_RE.sub(" ", match.group(1).replace("_", " "))


class Normalizer:
    """Applies the normalisation rules for one config. Cheap to call; build it once and reuse."""

    def __init__(self, config: NormalizationConfig) -> None:
        if config.emoji_demojize:
            raise NotImplementedError("emoji_demojize is ablation A9 and is not implemented yet")
        if config.canonicalize_variants:
            raise NotImplementedError(
                "canonicalize_variants is ablation A4 (needs LID-aware variant mapping) and is "
                "not implemented yet"
            )
        self.config = config
        n = config.max_char_repeat
        self._repeat = n
        self._emoji_run_re = regex.compile(rf"({EMOJI_SEQUENCE})\1{{{n},}}")
        self._char_run_re = regex.compile(rf"([^\p{{Nd}}])\1{{{n},}}")

    def __call__(self, text: str) -> NormalizedText:
        current, shouting = self._pass(text)
        for _ in range(_MAX_PASSES - 1):
            again, _ = self._pass(current)
            if again == current:
                break
            current = again
        return NormalizedText(text=current, has_caps_shouting=shouting)

    def normalize(self, text: str) -> str:
        return self(text).text

    def _collapse_run(self, match: regex.Match[str]) -> str:
        return match.group(1) * self._repeat

    def _pass(self, text: str) -> tuple[str, bool]:
        cfg = self.config
        # Lone surrogates (possible via JSON escapes) → U+FFFD, like JS String.toWellFormed().
        text = text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")
        if cfg.strip_zero_width:
            text = _INVISIBLE_RE.sub("", text)
            text = _STRAY_ZWJ_RE.sub("", text)
        text = unicodedata.normalize(cfg.unicode_form, text)
        text = _WHITESPACE_RE.sub(" ", text).strip(" ")
        text = _URL_RE.sub(cfg.replace.url, text)
        text = _MENTION_RE.sub(cfg.replace.mention, text)
        if cfg.hashtag == "split_camel_case":
            text = _HASHTAG_RE.sub(_split_hashtag, text)
        shouting = _SHOUT_RE.search(text) is not None
        if cfg.lowercase_roman:
            text = unicodedata.normalize(cfg.unicode_form, text.lower())
        text = self._emoji_run_re.sub(self._collapse_run, text)
        text = self._char_run_re.sub(self._collapse_run, text)
        if not cfg.keep_emoji:
            text = _EMOJI_RE.sub(" ", text)
        text = _WHITESPACE_RE.sub(" ", text).strip(" ")
        return text, shouting
