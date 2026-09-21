from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_mode": "demo"}


def test_demo_plan_is_grounded_and_reconciled() -> None:
    response = client.post(
        "/api/v1/trips/plan",
        json={"prompt": "Goa for five days from Indore for two people under ₹30,000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["trip"]["data_mode"] == "demo"
    assert len(body["flights"]) == 3
    assert len(body["hotels"]) == 3
    assert body["budget"]["total"] + body["budget"]["remaining"] == 30_000


def test_progress_stream_never_exposes_reasoning() -> None:
    response = client.get("/api/v1/trips/plan/events")
    assert response.status_code == 200
    assert "constraints.parsed" in response.text
    assert "chain-of-thought" not in response.text.lower()
