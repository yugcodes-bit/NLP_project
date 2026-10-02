"""Loads the model directory and runs one text through it.

Model directory layout (``MODEL_DIR``):

* ``model_quantized.onnx`` — inputs ``input_ids``, ``attention_mask`` (optionally
  ``token_type_ids``), all int64 ``[batch, sequence]``; outputs ``logits`` ``[batch, n_labels]``
  and ``intensity_logits`` ``[batch, n_emotions, 3]``
* ``tokenizer.json`` — a ``tokenizers`` fast tokenizer
* ``model-meta.json`` — see ``model_meta.py``
* ``lid.json`` — optional word-level LID model; without it ``lid`` is ``null`` in responses
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from bhaav_api.inference.lid import CodeMixAnalysis, LidModel, analyze_code_mixing
from bhaav_api.inference.model_meta import META_FILE, ModelMeta, load_model_meta
from bhaav_api.inference.normalize import Normalizer, load_normalization_config
from bhaav_api.inference.postprocess import Decision, decide

MODEL_FILE = "model_quantized.onnx"
TOKENIZER_FILE = "tokenizer.json"
LID_FILE = "lid.json"
RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_REQUIRED_OUTPUTS = ("logits", "intensity_logits")


class ModelLoadError(RuntimeError):
    pass


class EmotionPipeline:
    def __init__(
        self,
        *,
        session: Any,
        tokenizer: Tokenizer,
        meta: ModelMeta,
        normalizer: Normalizer,
        lid_model: LidModel | None,
    ) -> None:
        self.meta = meta
        self.normalizer = normalizer
        self._session = session
        self._tokenizer = tokenizer
        self._lid_model = lid_model
        self._input_names = {node.name for node in session.get_inputs()}
        missing = set(_REQUIRED_OUTPUTS) - {node.name for node in session.get_outputs()}
        if missing:
            raise ModelLoadError(f"model is missing outputs: {sorted(missing)}")

    @classmethod
    def load(cls, model_dir: Path, *, threads: int = 0) -> EmotionPipeline:
        for name in (MODEL_FILE, TOKENIZER_FILE, META_FILE):
            if not (model_dir / name).is_file():
                raise ModelLoadError(f"{name} not found in MODEL_DIR ({model_dir})")
        try:
            meta = load_model_meta(model_dir / META_FILE)
        except ValueError as exc:
            raise ModelLoadError(f"invalid {META_FILE}: {exc}") from exc

        config = load_normalization_config(RESOURCES / "normalization.yaml")
        if meta.normalization_version != config.version:
            # Training and serving must clean text identically, or accuracy silently drops.
            raise ModelLoadError(
                f"model was built with normalisation {meta.normalization_version!r} but this "
                f"service ships {config.version!r}"
            )

        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        session = ort.InferenceSession(
            str(model_dir / MODEL_FILE), sess_options=options, providers=["CPUExecutionProvider"]
        )
        tokenizer = Tokenizer.from_file(str(model_dir / TOKENIZER_FILE))
        tokenizer.enable_truncation(max_length=meta.max_length)
        tokenizer.no_padding()

        lid_path = model_dir / LID_FILE
        lid_model = LidModel.load(lid_path) if lid_path.is_file() else None
        pipeline = cls(
            session=session,
            tokenizer=tokenizer,
            meta=meta,
            normalizer=Normalizer(config),
            lid_model=lid_model,
        )
        pipeline.infer("warm up")  # first call pays the lazy-initialisation cost, not a user
        return pipeline

    @property
    def max_chars(self) -> int:
        return self.normalizer.config.max_chars

    def infer(self, text_normalized: str) -> Decision:
        """Run the model on already-normalised text."""
        encoding = self._tokenizer.encode(text_normalized)
        feeds = {
            "input_ids": np.asarray([encoding.ids], dtype=np.int64),
            "attention_mask": np.asarray([encoding.attention_mask], dtype=np.int64),
        }
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.asarray([encoding.type_ids], dtype=np.int64)
        logits, coral_logits = self._session.run(list(_REQUIRED_OUTPUTS), feeds)
        return decide(logits[0], coral_logits[0], self.meta)

    def code_mix(self, text_normalized: str) -> CodeMixAnalysis | None:
        if self._lid_model is None:
            return None
        return analyze_code_mixing(text_normalized, self._lid_model)
