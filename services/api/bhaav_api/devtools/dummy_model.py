"""Build a random-weight model directory with the real input/output contract.

    uv run python -m bhaav_api.devtools.dummy_model --out dist/dummy

The API and the web app are developed against this until a trained teacher exists (Phase 4).
**Its predictions are meaningless.** Every file it writes says so: ``model-meta.json`` and
``lid.json`` carry ``"dummy": true`` and the version starts with ``bhaav-dummy``.

Needs the ``dummy`` extra (``onnx``). The serving code itself never imports this module.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import onnx
import yaml
from onnx import TensorProto, helper, numpy_helper
from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors, trainers

from bhaav_api.inference.lid import LidModel, ngram_features
from bhaav_api.inference.model_meta import META_FILE, ModelMeta
from bhaav_api.inference.pipeline import LID_FILE, MODEL_FILE, RESOURCES, TOKENIZER_FILE

DUMMY_VERSION = "bhaav-dummy-0.1.0"
HIDDEN = 32
VOCAB_SIZE = 1200
OPSET = 17

#: Synthetic sentences used only to give the tokenizer a plausible vocabulary.
CORPUS = (
    "yaar aaj ka din bahut bekaar tha",
    "kya baat hai bhai maza aa gaya",
    "kal interview hai bohot tension ho rahi hai",
    "result aane wala hai dil dhak dhak kar raha hai",
    "mummy ne finally haan bol diya",
    "teen ghante se wait kar raha hu koi sunne wala nahi hai",
    "ye khana dekh ke ulti aa gayi ghatiya",
    "kya tu sach mein canada ja raha hai",
    "meeting paanch baje shift ho gayi hai",
    "ghar ki bahut yaad aa rahi hai aaj",
    "promotion mil gaya party toh banti hai",
    "mujhe kuch accha nahi lag raha thoda udaas hoon",
    "the result is out and i am very happy today",
    "this service is really bad and i am angry",
    "सच में बहुत खुश हूँ आज",
    "आज मन बहुत उदास है",
    "कल का पेपर सोच कर डर लग रहा है",
    "ये क्या तरीका है बात करने का",
)
HINDI_WORDS = (
    "yaar aaj ka din bahut bekaar tha kya baat hai bhai maza aa gaya nahi mujhe kuch accha lagta "
    "khush dukh gussa darr ghar kal abhi raha rahi hoon main tum hum kyun kaise kab kahan dil"
).split()
ENGLISH_WORDS = (
    "the is are was happy sad angry result exam interview office meeting train phone service "
    "order cancel finally trip confirm party promotion school team match report very today"
).split()


def _initial_alphabet() -> list[str]:
    latin = [chr(c) for c in range(ord("a"), ord("z") + 1)]
    digits = [chr(c) for c in range(ord("0"), ord("9") + 1)]
    devanagari = [chr(c) for c in range(0x0900, 0x0980)]
    return [*latin, *digits, *devanagari, *"!?.,'<>"]


def build_tokenizer() -> Tokenizer:
    tokenizer = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    tokenizer.normalizer = normalizers.NFC()
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.WordPieceTrainer(  # type: ignore[no-untyped-call]
        vocab_size=VOCAB_SIZE,
        special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]"],
        initial_alphabet=_initial_alphabet(),
        show_progress=False,
    )
    tokenizer.train_from_iterator(CORPUS, trainer)
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=[
            ("[CLS]", tokenizer.token_to_id("[CLS]")),
            ("[SEP]", tokenizer.token_to_id("[SEP]")),
        ],
    )
    return tokenizer


def build_onnx(vocab_size: int, n_labels: int, n_emotions: int, seed: int) -> onnx.ModelProto:
    """Embedding → masked mean-pool → two linear heads. Same I/O as the real export."""
    rng = np.random.default_rng(seed)

    def weight(name: str, *shape: int) -> onnx.TensorProto:
        return numpy_helper.from_array(rng.normal(size=shape).astype(np.float32), name)

    emotion_bias = np.full(n_labels, -1.0, dtype=np.float32)
    initializers = [
        weight("embedding", vocab_size, HIDDEN),
        weight("emotion_weight", HIDDEN, n_labels),
        numpy_helper.from_array(emotion_bias, "emotion_bias"),
        weight("intensity_weight", HIDDEN, n_emotions * 3),
        weight("intensity_bias", n_emotions * 3),
        numpy_helper.from_array(np.asarray([2], dtype=np.int64), "axis_last"),
        numpy_helper.from_array(np.asarray([1], dtype=np.int64), "axis_sequence"),
        numpy_helper.from_array(np.asarray([1.0], dtype=np.float32), "one"),
        numpy_helper.from_array(np.asarray([0, n_emotions, 3], dtype=np.int64), "coral_shape"),
    ]
    nodes = [
        helper.make_node("Gather", ["embedding", "input_ids"], ["embedded"]),
        helper.make_node("Cast", ["attention_mask"], ["mask"], to=TensorProto.FLOAT),
        helper.make_node("Unsqueeze", ["mask", "axis_last"], ["mask3"]),
        helper.make_node("Mul", ["embedded", "mask3"], ["masked"]),
        helper.make_node("ReduceSum", ["masked", "axis_sequence"], ["summed"], keepdims=0),
        helper.make_node("ReduceSum", ["mask3", "axis_sequence"], ["count"], keepdims=0),
        helper.make_node("Max", ["count", "one"], ["safe_count"]),
        helper.make_node("Div", ["summed", "safe_count"], ["pooled"]),
        helper.make_node("Gemm", ["pooled", "emotion_weight", "emotion_bias"], ["logits"]),
        helper.make_node("Gemm", ["pooled", "intensity_weight", "intensity_bias"], ["coral_flat"]),
        helper.make_node("Reshape", ["coral_flat", "coral_shape"], ["intensity_logits"]),
    ]
    graph = helper.make_graph(
        nodes,
        "bhaav_dummy",
        inputs=[
            helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["batch", "sequence"]),
            helper.make_tensor_value_info(
                "attention_mask", TensorProto.INT64, ["batch", "sequence"]
            ),
        ],
        outputs=[
            helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", n_labels]),
            helper.make_tensor_value_info(
                "intensity_logits", TensorProto.FLOAT, ["batch", n_emotions, 3]
            ),
        ],
        initializer=initializers,
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", OPSET)])
    model.ir_version = 8  # readable by every ONNX Runtime release we support
    onnx.checker.check_model(model)
    return model


def build_lid() -> LidModel:
    """A crude n-gram counter over two short word lists. Right format, no evaluated accuracy."""
    n_features = 1 << 12
    ngram_range = (1, 5)
    weights = np.zeros((2, n_features), dtype=np.float32)
    for row, words in enumerate((ENGLISH_WORDS, HINDI_WORDS)):
        for word in words:
            weights[row, ngram_features(word, ngram_range, n_features)] += 1.0
    return LidModel(
        version="lid-dummy-0.1.0",
        classes=("en", "hi"),
        ngram_range=ngram_range,
        n_features=n_features,
        weights=weights,
        bias=np.zeros(2, dtype=np.float32),
        dummy=True,
        trained_on="two hand-written word lists (development only)",
    )


def build_meta() -> ModelMeta:
    with (RESOURCES / "label_schema.yaml").open(encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)
    with (RESOURCES / "normalization.yaml").open(encoding="utf-8") as fh:
        normalization = yaml.safe_load(fh)
    labels = tuple(schema["labels"])
    return ModelMeta(
        model_version=DUMMY_VERSION,
        dummy=True,
        schema_version=str(schema["schema_version"]),
        labels=labels,
        emotions=tuple(schema["emotions"]),
        neutral_label=schema["neutral_label"],
        neutral_rule=schema["neutral_rule"],
        intensity_scale={str(k): str(v) for k, v in schema["intensity"]["scale"].items()},
        temperature=tuple(1.0 for _ in labels),
        thresholds=dict.fromkeys(labels, 0.5),
        tau=0.4,
        max_length=128,
        normalization_version=str(normalization["version"]),
        created_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    )


def build_dummy_model(out_dir: Path, seed: int = 13) -> ModelMeta:
    """Write the four model files into ``out_dir`` and return the metadata."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = build_meta()
    tokenizer = build_tokenizer()
    tokenizer.save(str(out_dir / TOKENIZER_FILE))
    model = build_onnx(tokenizer.get_vocab_size(), len(meta.labels), len(meta.emotions), seed)
    onnx.save(model, str(out_dir / MODEL_FILE))
    build_lid().save(out_dir / LID_FILE)
    (out_dir / META_FILE).write_text(
        json.dumps(meta.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    return meta


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bhaav_api.devtools.dummy_model")
    parser.add_argument("--out", type=Path, required=True, help="directory to write the model to")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)
    meta = build_dummy_model(args.out, args.seed)
    print(f"wrote {meta.model_version} to {args.out} (random weights - development only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
