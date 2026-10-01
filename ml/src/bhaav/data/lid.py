"""Script detection, word-level language ID and the Code-Mixing Index.

Design: ``docs/08_ml_methodology.md`` §2.2 and ADR-006. Input is always *normalised* text.

This module is copied verbatim into ``services/api`` by ``bhaav.sync_shared`` (ADR-008), so it
must only import the standard library, ``regex``, ``numpy`` and its sibling ``normalize`` module.
Training lives in ``bhaav.data.lid_train``; this file is inference only.

Tagging rules
    * emoji, punctuation, numbers, ``<url>``/``<user>`` placeholders → ``univ``
    * a word containing Devanagari → ``hi`` (by script; English written in Devanagari is
      therefore tagged ``hi`` — a documented limitation)
    * a Roman-script word → the char n-gram model decides
    * a word in any other script → ``other``

``ne`` (named entity) is part of the tag set but is never predicted by this model.
"""

from __future__ import annotations

import base64
import json
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import regex

from .normalize import EMOJI_SEQUENCE

Lang = Literal["hi", "en", "univ", "ne", "other"]
Script = Literal["roman", "devanagari", "mixed"]
TokenKind = Literal["word", "number", "emoji", "punct", "placeholder"]
TokenScript = Literal["roman", "devanagari", "mixed", "other", "none"]

#: Tags that are language-independent and therefore excluded from the CMI denominator.
LANGUAGE_INDEPENDENT: frozenset[str] = frozenset({"univ", "ne"})

_PLACEHOLDER = r"<[a-z]+>"
_WORD = r"[\p{L}\p{M}\p{N}]+(?:['’][\p{L}\p{M}\p{N}]+)*"
_TOKEN_RE = regex.compile(
    rf"(?P<placeholder>{_PLACEHOLDER})"
    rf"|(?P<emoji>{EMOJI_SEQUENCE})"
    rf"|(?P<word>{_WORD})"
    rf"|(?P<punct>(?:(?!{_PLACEHOLDER}|{EMOJI_SEQUENCE})[^\s\p{{L}}\p{{M}}\p{{N}}])+)"
)
_DEVANAGARI_RE = regex.compile(r"\p{Script=Devanagari}")
_LATIN_RE = regex.compile(r"\p{Script=Latin}")
_LETTER_RE = regex.compile(r"\p{L}")

_MODEL_FORMAT = "bhaav-lid-charngram"
_MODEL_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class RawToken:
    text: str
    kind: TokenKind
    script: TokenScript


@dataclass(frozen=True, slots=True)
class TaggedToken:
    text: str
    lang: Lang


def _word_script(word: str) -> TokenScript:
    has_devanagari = _DEVANAGARI_RE.search(word) is not None
    has_latin = _LATIN_RE.search(word) is not None
    if has_devanagari and has_latin:
        return "mixed"
    if has_devanagari:
        return "devanagari"
    if has_latin:
        return "roman"
    return "other"


def tokenize(text: str) -> list[RawToken]:
    """Split normalised text into words, numbers, emoji, punctuation runs and placeholders."""
    tokens: list[RawToken] = []
    for match in _TOKEN_RE.finditer(text):
        piece = match.group()
        kind = match.lastgroup
        if kind == "word":
            if _LETTER_RE.search(piece) is None:
                tokens.append(RawToken(piece, "number", "none"))
            else:
                tokens.append(RawToken(piece, "word", _word_script(piece)))
        elif kind == "emoji":
            tokens.append(RawToken(piece, "emoji", "none"))
        elif kind == "placeholder":
            tokens.append(RawToken(piece, "placeholder", "none"))
        else:
            tokens.append(RawToken(piece, "punct", "none"))
    return tokens


def script_of(tokens: Sequence[RawToken]) -> Script:
    """Utterance script: ``mixed`` if both Devanagari and Roman letters occur.

    Text with no Devanagari at all (including emoji-only text) is reported as ``roman``; the
    unified schema has no fourth value.
    """
    has_devanagari = any(t.script in ("devanagari", "mixed") for t in tokens)
    has_latin = any(t.script in ("roman", "mixed") for t in tokens)
    if has_devanagari and has_latin:
        return "mixed"
    if has_devanagari:
        return "devanagari"
    return "roman"


def detect_script(text: str) -> Script:
    return script_of(tokenize(text))


# --------------------------------------------------------------------------- char n-gram model


def fnv1a_32(data: bytes) -> int:
    """32-bit FNV-1a. Chosen because it is trivial to reproduce exactly in TypeScript."""
    h = 0x811C9DC5
    for byte in data:
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def ngram_features(word: str, ngram_range: tuple[int, int], n_features: int) -> list[int]:
    """Hashed indices of the distinct character n-grams of ``^word$`` (lower-cased)."""
    padded = f"^{word.lower()}$"
    low, high = ngram_range
    indices: set[int] = set()
    for n in range(low, high + 1):
        for start in range(len(padded) - n + 1):
            indices.add(fnv1a_32(padded[start : start + n].encode("utf-8")) % n_features)
    return sorted(indices)


@dataclass(frozen=True, eq=False)
class LidModel:
    """Multinomial logistic regression over hashed character n-grams of a single word."""

    version: str
    classes: tuple[str, ...]
    ngram_range: tuple[int, int]
    n_features: int
    weights: npt.NDArray[np.float32]  # (n_classes, n_features)
    bias: npt.NDArray[np.float32]  # (n_classes,)
    dummy: bool = False
    trained_on: str = ""

    def __post_init__(self) -> None:
        if self.weights.shape != (len(self.classes), self.n_features):
            raise ValueError(f"weights shape {self.weights.shape} does not match classes/features")
        if self.bias.shape != (len(self.classes),):
            raise ValueError(f"bias shape {self.bias.shape} does not match classes")

    def logits(self, word: str) -> npt.NDArray[np.float32]:
        indices = ngram_features(word, self.ngram_range, self.n_features)
        summed = self.weights[:, indices].sum(axis=1) / math.sqrt(len(indices))
        return np.asarray(self.bias + summed, dtype=np.float32)

    def predict(self, word: str) -> str:
        return self.classes[int(np.argmax(self.logits(word)))]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": _MODEL_FORMAT,
            "format_version": _MODEL_FORMAT_VERSION,
            "version": self.version,
            "dummy": self.dummy,
            "trained_on": self.trained_on,
            "classes": list(self.classes),
            "ngram_range": list(self.ngram_range),
            "n_features": self.n_features,
            "bias": [float(b) for b in self.bias],
            # float32, little-endian, row-major (class by class)
            "weights_b64": base64.b64encode(self.weights.astype("<f4").tobytes()).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LidModel:
        if payload.get("format") != _MODEL_FORMAT:
            raise ValueError(f"not a {_MODEL_FORMAT} file")
        if payload.get("format_version") != _MODEL_FORMAT_VERSION:
            raise ValueError(f"unsupported LID format_version {payload.get('format_version')!r}")
        classes = tuple(str(c) for c in payload["classes"])
        n_features = int(payload["n_features"])
        flat = np.frombuffer(base64.b64decode(payload["weights_b64"]), dtype="<f4")
        low, high = payload["ngram_range"]
        return cls(
            version=str(payload["version"]),
            classes=classes,
            ngram_range=(int(low), int(high)),
            n_features=n_features,
            weights=flat.reshape(len(classes), n_features).astype(np.float32),
            bias=np.asarray(payload["bias"], dtype=np.float32),
            dummy=bool(payload.get("dummy", False)),
            trained_on=str(payload.get("trained_on", "")),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> LidModel:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- tagging + CMI


def tag_tokens(tokens: Sequence[RawToken], model: LidModel) -> list[TaggedToken]:
    tagged: list[TaggedToken] = []
    for token in tokens:
        lang: Lang
        if token.kind != "word":
            lang = "univ"
        elif token.script in ("devanagari", "mixed"):
            lang = "hi"
        elif token.script == "roman":
            lang = "hi" if model.predict(token.text) == "hi" else "en"
        else:
            lang = "other"
        tagged.append(TaggedToken(token.text, lang))
    return tagged


def code_mixing_index(langs: Sequence[str]) -> float:
    """Gambäck & Das CMI: ``100 × (1 − max_lang / (N − u))``.

    Returns 0 when every token is language-independent. ``N`` is the token count, ``u`` the
    language-independent tokens (``univ``, ``ne``) and ``max_lang`` the count of the dominant
    language.
    """
    counts = Counter(lang for lang in langs if lang not in LANGUAGE_INDEPENDENT)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return 100.0 * (1.0 - max(counts.values()) / total)


def lang_share(langs: Sequence[str]) -> dict[str, float]:
    """Share of each language among language-bearing tokens. Always has ``hi`` and ``en``."""
    counts = Counter(lang for lang in langs if lang not in LANGUAGE_INDEPENDENT)
    total = sum(counts.values())
    shares = {"hi": 0.0, "en": 0.0}
    if total == 0:
        return shares
    for lang, count in counts.items():
        shares[lang] = count / total
    return shares


@dataclass(frozen=True, slots=True)
class CodeMixAnalysis:
    tokens: list[TaggedToken]
    script: Script
    cmi: float
    lang_share: dict[str, float]


def analyze_code_mixing(text: str, model: LidModel) -> CodeMixAnalysis:
    """Tokenise normalised ``text``, tag each token and compute script, CMI and language shares."""
    raw = tokenize(text)
    tagged = tag_tokens(raw, model)
    langs = [t.lang for t in tagged]
    return CodeMixAnalysis(
        tokens=tagged,
        script=script_of(raw),
        cmi=code_mixing_index(langs),
        lang_share=lang_share(langs),
    )
