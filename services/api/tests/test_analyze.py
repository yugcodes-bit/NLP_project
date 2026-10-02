"""POST /v1/analyze against the dummy model: shape, validation and consistency (FR-01 … FR-09).

The dummy model's *predictions* are random, so nothing here asserts which emotion comes out —
only that the response obeys the contract and is internally consistent.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

LABELS = ["anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral"]
CONTRACT_FIELDS = {
    "text_normalized", "script", "emotions", "scores", "top", "abstained", "candidates",
    "confidence", "lid", "explanation", "wellbeing", "model_version", "mode", "latency_ms",
}  # fmt: skip
SAMPLES = [
    "yaar aaj ka din bahut bekaar tha 😩",
    "kya baat hai bhai, maza aa gaya!!",
    "kal interview hai, bohot tension ho rahi hai",
    "सच में बहुत खुश हूँ आज",
    "बहुत khush हूँ yaar",
    "meeting 5 baje shift ho gayi hai",
    "ok",
    "😂😂",
    "the result is out and I am very happy today",
    "ye khana dekh ke ulti aa gayi, ghatiya",
]


def analyze(client: TestClient, text: str, **options: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if options:
        payload["options"] = options
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def problem(client: TestClient, **kwargs: Any) -> dict[str, Any]:
    response = client.post("/v1/analyze", **kwargs)
    assert response.status_code == 422, response.text
    assert response.headers["content-type"] == "application/problem+json"
    body: dict[str, Any] = response.json()
    assert set(body) == {"type", "title", "status", "detail", "code"}
    assert body["status"] == 422
    return body


# ------------------------------------------------------------------ response shape


@pytest.mark.parametrize("text", SAMPLES)
def test_response_obeys_the_contract(client: TestClient, text: str) -> None:
    body = analyze(client, text)
    assert set(body) == CONTRACT_FIELDS
    assert body["mode"] == "server"
    assert body["model_version"] == "bhaav-dummy-0.1.0"
    assert isinstance(body["latency_ms"], int)
    assert body["script"] in {"roman", "devanagari", "mixed"}
    assert body["wellbeing"] == {"show": False}
    assert body["explanation"] is None

    scores = body["scores"]
    assert list(scores) == LABELS
    assert all(0.0 <= p <= 1.0 for p in scores.values())
    assert body["confidence"] == max(scores.values())


@pytest.mark.parametrize("text", SAMPLES)
def test_decision_is_internally_consistent(client: TestClient, text: str) -> None:
    body = analyze(client, text)
    emotions, scores = body["emotions"], body["scores"]
    active = [e["label"] for e in emotions]

    if body["abstained"]:
        assert emotions == []
        assert body["top"] is None
        assert len(body["candidates"]) == 2
        ranked = sorted(scores.values(), reverse=True)
        assert [c["probability"] for c in body["candidates"]] == ranked[:2]
        assert body["confidence"] < 0.4  # the dummy model's tau
    else:
        assert body["candidates"] is None
        assert active
        assert body["top"] == active[0]
        assert all(e["active"] for e in emotions)
        assert [e["probability"] for e in emotions] == sorted(
            (e["probability"] for e in emotions), reverse=True
        )
        assert all(e["probability"] == scores[e["label"]] for e in emotions)
        if "neutral" in active:
            assert active == ["neutral"]  # neutral is never combined with an emotion
            assert emotions[0]["intensity"] is None
        else:
            assert all(e["intensity"] in (1, 2, 3) for e in emotions)
            assert all(scores[label] >= 0.5 for label in active)  # the dummy thresholds


def test_same_text_gives_the_same_answer(client: TestClient) -> None:
    first = analyze(client, SAMPLES[0])
    second = analyze(client, SAMPLES[0])
    first.pop("latency_ms")
    second.pop("latency_ms")
    assert first == second


def test_normalised_text_is_returned_and_is_stable(client: TestClient) -> None:
    body = analyze(client, "  Kya Baat Hai Bhaiiiii!!!!   https://example.com/x  ")
    assert body["text_normalized"] == "kya baat hai bhaii!! <url>"
    again = analyze(client, body["text_normalized"])
    assert again["text_normalized"] == body["text_normalized"]
    assert again["scores"] == body["scores"]


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("yaar aaj bahut khush hu", "roman"),
        ("सच में बहुत खुश हूँ आज", "devanagari"),
        ("बहुत khush हूँ yaar", "mixed"),
    ],
)
def test_script(client: TestClient, text: str, script: str) -> None:
    assert analyze(client, text)["script"] == script


# ------------------------------------------------------------------ options


def test_lid_block(client: TestClient) -> None:
    lid = analyze(client, "yaar aaj meeting cancel ho gayi 😂")["lid"]
    assert [t["text"] for t in lid["tokens"]] == [
        "yaar", "aaj", "meeting", "cancel", "ho", "gayi", "😂",
    ]  # fmt: skip
    assert all(t["lang"] in {"hi", "en", "univ", "ne", "other"} for t in lid["tokens"])
    assert lid["tokens"][-1]["lang"] == "univ"
    assert 0.0 <= lid["cmi"] <= 100.0
    assert {"hi", "en"} <= set(lid["lang_share"])
    assert sum(lid["lang_share"].values()) == pytest.approx(1.0, abs=0.01)


def test_devanagari_words_are_tagged_hindi_with_zero_cmi(client: TestClient) -> None:
    lid = analyze(client, "सच में बहुत खुश हूँ आज")["lid"]
    assert {t["lang"] for t in lid["tokens"]} == {"hi"}
    assert lid["cmi"] == 0.0
    assert lid["lang_share"] == {"hi": 1.0, "en": 0.0}


def test_options_switch_blocks_off(client: TestClient) -> None:
    body = analyze(client, SAMPLES[0], lid=False, all_scores=False)
    assert body["lid"] is None
    assert body["scores"] is None
    assert body["confidence"] > 0.0


def test_explain_is_accepted_but_not_implemented_yet(client: TestClient) -> None:
    assert analyze(client, SAMPLES[0], explain=True)["explanation"] is None


def test_unknown_option_and_field_are_ignored(client: TestClient) -> None:
    response = client.post(
        "/v1/analyze", json={"text": "ok hai", "options": {"future": True}, "extra": 1}
    )
    assert response.status_code == 200


# ------------------------------------------------------------------ validation


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_empty_text(client: TestClient, text: str) -> None:
    body = problem(client, json={"text": text})
    assert body["code"] == "TEXT_EMPTY"


def test_text_of_only_invisible_characters_is_empty(client: TestClient) -> None:
    invisible = chr(0x200B) + chr(0x200D) + chr(0xFEFF)
    assert problem(client, json={"text": invisible})["code"] == "TEXT_EMPTY"


def test_length_limit_is_1000_characters(client: TestClient) -> None:
    at_limit = ("bahut khush " * 100)[:1000]
    assert len(at_limit) == 1000
    assert client.post("/v1/analyze", json={"text": at_limit}).status_code == 200

    body = problem(client, json={"text": at_limit + "x"})
    assert body["code"] == "TEXT_TOO_LONG"
    assert body["title"] == "Text too long"
    assert body["detail"] == "text must be ≤ 1000 characters"


def test_length_is_counted_after_trimming_and_in_code_points(client: TestClient) -> None:
    padded = " " * 50 + "a" * 1000 + " " * 50
    assert client.post("/v1/analyze", json={"text": padded}).status_code == 200
    # 1,000 emoji are 1,000 characters here (they would be 2,000 UTF-16 units in JavaScript).
    assert client.post("/v1/analyze", json={"text": "😂" * 1000}).status_code == 200
    assert problem(client, json={"text": "😂" * 1001})["code"] == "TEXT_TOO_LONG"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"json": {}},
        {"json": {"text": 123}},
        {"json": {"text": None}},
        {"json": {"text": "ok", "options": {"lid": "maybe"}}},
        {"json": ["not", "an", "object"]},
        {"content": b"{not json", "headers": {"content-type": "application/json"}},
    ],
)
def test_malformed_request(client: TestClient, kwargs: dict[str, Any]) -> None:
    body = problem(client, **kwargs)
    assert body["code"] == "INVALID_REQUEST"


def test_configured_limit_overrides_the_default(model_dir: Any) -> None:
    from bhaav_api.config import Settings
    from bhaav_api.main import create_app

    settings = Settings(_env_file=None, model_dir=model_dir, max_text_chars=10)
    with TestClient(create_app(settings)) as small:
        assert small.post("/v1/analyze", json={"text": "a" * 10}).status_code == 200
        body = small.post("/v1/analyze", json={"text": "a" * 11}).json()
        assert body["code"] == "TEXT_TOO_LONG"
        assert body["detail"] == "text must be ≤ 10 characters"
