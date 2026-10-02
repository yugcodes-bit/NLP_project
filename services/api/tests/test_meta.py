from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "model_version", "uptime_s"}
    assert body["status"] == "ok"
    assert body["model_version"] == "bhaav-dummy-0.1.0"
    assert isinstance(body["uptime_s"], int)
    assert body["uptime_s"] >= 0


def test_labels_match_the_contract(client: TestClient) -> None:
    response = client.get("/v1/labels")
    assert response.status_code == 200
    assert response.json() == {
        "labels": ["anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral"],
        "intensity_scale": {"0": "absent", "1": "low", "2": "moderate", "3": "high"},
        "schema_version": "1.0",
    }


def test_response_headers(client: TestClient) -> None:
    first = client.get("/v1/health")
    second = client.get("/v1/health")
    assert first.headers["x-model-version"] == "bhaav-dummy-0.1.0"
    assert len(first.headers["x-request-id"]) == 32
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_health_reports_a_missing_model_instead_of_crashing(
    client_without_model: TestClient,
) -> None:
    response = client_without_model.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "model_not_ready"
    assert response.json()["model_version"] is None
    assert "x-model-version" not in response.headers


def test_labels_and_analyze_answer_503_without_a_model(client_without_model: TestClient) -> None:
    for response in (
        client_without_model.get("/v1/labels"),
        client_without_model.post("/v1/analyze", json={"text": "kuch bhi"}),
    ):
        assert response.status_code == 503
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json() == {
            "type": "about:blank",
            "title": "Model not ready",
            "status": 503,
            "detail": "the model is not loaded",
            "code": "MODEL_NOT_READY",
        }


def test_unknown_route_and_wrong_method_use_the_problem_format(client: TestClient) -> None:
    missing = client.get("/v1/nope")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"
    wrong_method = client.get("/v1/analyze")
    assert wrong_method.status_code == 405
    assert wrong_method.json()["code"] == "METHOD_NOT_ALLOWED"


def test_openapi_document_lists_the_v1_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/v1/health", "/v1/labels", "/v1/analyze"} <= set(paths)
