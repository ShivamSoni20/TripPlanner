from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import Money, Pace, TripConstraints, TripPreferences
from app.services.trip_extraction import TripExtractionResult

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "providers" in response.json()


def test_demo_plan_is_grounded_and_reconciled() -> None:
    response = client.post(
        "/api/v1/trips/plan",
        json={"prompt": "Goa for five days from Indore for two people under ₹130,000"},
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


def test_graph_plans_with_extracted_constraints(monkeypatch) -> None:
    class StaticExtractor:
        async def extract(self, prompt: str) -> TripExtractionResult:
            assert "Kerala" in prompt
            return TripExtractionResult(
                status="complete",
                constraints=TripConstraints(
                    origin="Pune",
                    destination="Kerala",
                    start_date="2026-12-02",
                    end_date="2026-12-07",
                    travelers=3,
                    budget=Money(amount=60_000),
                    preferences=TripPreferences(interests=["nature"], pace=Pace.RELAXED),
                ),
            )

    monkeypatch.setattr("app.api.routes.get_extractor", lambda: StaticExtractor())
    response = client.post(
        "/api/v1/trips/plan",
        json={"prompt": "Kerala from Pune, 2–7 December 2026, three people, ₹160,000"},
    )

    assert response.status_code == 200
    constraints = response.json()["trip"]["constraints"]
    assert constraints["origin"] == "Pune"
    assert constraints["destination"] == "Kerala"
    assert constraints["travelers"] == 3


def test_api_returns_structured_missing_requirements(monkeypatch) -> None:
    class MissingExtractor:
        async def extract(self, prompt: str) -> TripExtractionResult:
            _ = prompt
            return TripExtractionResult(
                status="needs_input",
                missing=["origin", "start_date", "end_date"],
                question="What origin and travel dates should I use for this trip?",
            )

    monkeypatch.setattr("app.api.routes.get_extractor", lambda: MissingExtractor())
    response = client.post(
        "/api/v1/trips/plan",
        json={"prompt": "Plan a relaxed Goa holiday for two people"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "needs_input",
        "missing": ["origin", "start_date", "end_date"],
        "question": "What origin and travel dates should I use for this trip?",
    }


def test_explore_endpoint_returns_recommendations() -> None:
    response = client.post(
        "/api/v1/trips/explore",
        json={
            "interests": ["history"],
            "window": {
                "start_at": "2026-11-13T10:00:00Z",
                "end_at": "2026-11-13T13:00:00Z",
                "origin": {"lat": 15.4921, "lng": 73.7737},
                "duration_minutes": 180,
            },
        },
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
