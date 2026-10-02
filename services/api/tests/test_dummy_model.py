"""The dummy model must have exactly the I/O contract the real export will have."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import pytest
from tokenizers import Tokenizer

from bhaav_api.devtools import dummy_model
from bhaav_api.inference.lid import LidModel
from bhaav_api.inference.model_meta import load_model_meta
from bhaav_api.inference.pipeline import EmotionPipeline, ModelLoadError


def session(model_dir: Path) -> ort.InferenceSession:
    return ort.InferenceSession(
        str(model_dir / "model_quantized.onnx"), providers=["CPUExecutionProvider"]
    )


def test_files_written(model_dir: Path) -> None:
    names = {p.name for p in model_dir.iterdir()}
    assert names == {"model_quantized.onnx", "tokenizer.json", "model-meta.json", "lid.json"}
    onnx.checker.check_model(onnx.load(str(model_dir / "model_quantized.onnx")))


def test_everything_is_flagged_as_dummy(model_dir: Path) -> None:
    meta = load_model_meta(model_dir / "model-meta.json")
    assert meta.dummy
    assert meta.model_version.startswith("bhaav-dummy")
    assert LidModel.load(model_dir / "lid.json").dummy


def test_meta_matches_the_label_schema(model_dir: Path) -> None:
    meta = load_model_meta(model_dir / "model-meta.json")
    assert meta.labels == ("anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral")
    assert meta.emotions == meta.labels[:-1]
    assert meta.intensity_scale == {"0": "absent", "1": "low", "2": "moderate", "3": "high"}
    assert meta.schema_version == "1.0"
    assert meta.normalization_version == "1.0"


def test_onnx_input_output_contract(model_dir: Path) -> None:
    sess = session(model_dir)
    assert {i.name: (i.type, i.shape) for i in sess.get_inputs()} == {
        "input_ids": ("tensor(int64)", ["batch", "sequence"]),
        "attention_mask": ("tensor(int64)", ["batch", "sequence"]),
    }
    assert {o.name: (o.type, o.shape) for o in sess.get_outputs()} == {
        "logits": ("tensor(float)", ["batch", 7]),
        "intensity_logits": ("tensor(float)", ["batch", 6, 3]),
    }


def test_padding_does_not_change_a_prediction(model_dir: Path) -> None:
    """Dynamic batch and sequence axes, and masked pooling: padded rows score like single rows."""
    sess = session(model_dir)
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    texts = [
        "yaar aaj bahut khush hu",
        "ok",
        "kal interview hai aur mujhe bohot tension ho rahi hai",
    ]
    encodings = [tokenizer.encode(text) for text in texts]

    alone = []
    for enc in encodings:
        feeds = {
            "input_ids": np.asarray([enc.ids], dtype=np.int64),
            "attention_mask": np.asarray([enc.attention_mask], dtype=np.int64),
        }
        alone.append(sess.run(["logits", "intensity_logits"], feeds))

    width = max(len(enc.ids) for enc in encodings)
    ids = np.zeros((len(texts), width), dtype=np.int64)
    mask = np.zeros((len(texts), width), dtype=np.int64)
    for row, enc in enumerate(encodings):
        ids[row, : len(enc.ids)] = enc.ids
        mask[row, : len(enc.ids)] = 1
    logits, coral = sess.run(
        ["logits", "intensity_logits"], {"input_ids": ids, "attention_mask": mask}
    )

    assert logits.shape == (3, 7)
    assert coral.shape == (3, 6, 3)
    for row, (single_logits, single_coral) in enumerate(alone):
        np.testing.assert_allclose(logits[row], single_logits[0], atol=1e-5)
        np.testing.assert_allclose(coral[row], single_coral[0], atol=1e-5)


def test_tokenizer_adds_special_tokens_and_handles_both_scripts(model_dir: Path) -> None:
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    for text in ("yaar aaj bahut khush hu", "सच में बहुत खुश हूँ"):
        tokens = tokenizer.encode(text).tokens
        assert tokens[0] == "[CLS]"
        assert tokens[-1] == "[SEP]"
        assert "[UNK]" not in tokens


def test_same_seed_same_weights_different_seed_different(tmp_path: Path, model_dir: Path) -> None:
    dummy_model.build_dummy_model(tmp_path / "a", seed=13)
    dummy_model.build_dummy_model(tmp_path / "b", seed=99)
    feeds = {
        "input_ids": np.asarray([[2, 10, 11, 3]], dtype=np.int64),
        "attention_mask": np.ones((1, 4), dtype=np.int64),
    }
    reference = session(model_dir).run(["logits"], feeds)[0]
    np.testing.assert_array_equal(session(tmp_path / "a").run(["logits"], feeds)[0], reference)
    assert not np.allclose(session(tmp_path / "b").run(["logits"], feeds)[0], reference)


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert dummy_model.main(["--out", str(tmp_path / "out")]) == 0
    assert "development only" in capsys.readouterr().out
    assert (tmp_path / "out" / "model_quantized.onnx").is_file()


# ------------------------------------------------------------------ loading


def test_pipeline_loads_the_dummy_model(model_dir: Path) -> None:
    pipeline = EmotionPipeline.load(model_dir)
    assert pipeline.meta.dummy
    assert pipeline.max_chars == 1000
    decision = pipeline.infer("yaar aaj bahut khush hu")
    assert set(decision.scores) == set(pipeline.meta.labels)
    assert all(0.0 <= p <= 1.0 for p in decision.scores.values())
    assert pipeline.code_mix("yaar aaj meeting hai") is not None


def _copy(model_dir: Path, dest: Path, skip: str = "") -> Path:
    dest.mkdir()
    for path in model_dir.iterdir():
        if path.name != skip:
            (dest / path.name).write_bytes(path.read_bytes())
    return dest


@pytest.mark.parametrize("missing", ["model_quantized.onnx", "tokenizer.json", "model-meta.json"])
def test_missing_file_is_a_load_error(model_dir: Path, tmp_path: Path, missing: str) -> None:
    with pytest.raises(ModelLoadError, match=missing):
        EmotionPipeline.load(_copy(model_dir, tmp_path / "m", skip=missing))


def test_lid_file_is_optional(model_dir: Path, tmp_path: Path) -> None:
    pipeline = EmotionPipeline.load(_copy(model_dir, tmp_path / "m", skip="lid.json"))
    assert pipeline.code_mix("yaar aaj meeting hai") is None


def test_normalisation_version_mismatch_is_a_load_error(model_dir: Path, tmp_path: Path) -> None:
    broken = _copy(model_dir, tmp_path / "m")
    meta = json.loads((broken / "model-meta.json").read_text(encoding="utf-8"))
    meta["normalization_version"] = "0.9"
    (broken / "model-meta.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ModelLoadError, match=r"normalisation '0\.9'"):
        EmotionPipeline.load(broken)


def test_invalid_meta_is_a_load_error(model_dir: Path, tmp_path: Path) -> None:
    broken = _copy(model_dir, tmp_path / "m")
    meta = json.loads((broken / "model-meta.json").read_text(encoding="utf-8"))
    meta["thresholds"].pop("joy")
    (broken / "model-meta.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ModelLoadError, match=r"invalid model-meta\.json"):
        EmotionPipeline.load(broken)
