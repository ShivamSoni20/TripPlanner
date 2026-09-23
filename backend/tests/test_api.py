import os
from uuid import UUID

from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"

from app.core.config import get_settings
from app.main import app
from app.models.domain import Money, Pace, TripConstraints, TripPreferences
from app.services.trip_extraction import TripExtractionResult

get_settings.cache_clear()
client = TestClient(app)

USER_A_AUTH = {"Authorization": "Bearer test-token-00000000-0000-0000-0000-000000000001"}
USER_B_AUTH = {"Authorization": "Bearer test-token-00000000-0000-0000-0000-000000000002"}


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "providers" in response.json()


def test_unauthenticated_requests_fail() -> None:
    response = client.post(
        "/api/v1/trips/plan",
        json={"prompt": "Goa for five days from Indore for two people under ?130,000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["category"] == "UNAUTHORIZED"

    list_resp = client.get("/api/v1/trips")
    assert list_resp.status_code == 401


def test_demo_plan_is_grounded_and_reconciled() -> None:
    response = client.post(
        "/api/v1/trips/plan",
        headers=USER_A_AUTH,
        json={"prompt": "Goa for five days from Indore for two people under ?130,000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["trip"]["data_mode"] == "demo"
    assert body["trip"]["version"] == 1
    UUID(body["trip"]["id"])
    for item in body["itinerary"]:
        UUID(item["id"])
    assert len(body["flights"]) == 3
    assert len(body["hotels"]) == 3


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
        headers=USER_A_AUTH,
        json={"prompt": "Kerala from Pune, 2–7 December 2026, three people, ?160,000"},
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
        headers=USER_A_AUTH,
        json={"prompt": "Plan a relaxed Goa holiday for two people"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "needs_input",
        "missing": ["origin", "start_date", "end_date"],
        "question": "What origin and travel dates should I use for this trip?",
    }


def test_persisted_trip_crud_and_cross_user_isolation() -> None:
    # 1. User A creates trip
    plan_resp = client.post(
        "/api/v1/trips/plan",
        headers=USER_A_AUTH,
        json={"prompt": "Goa for five days from Indore for two people under ?130,000"},
    )
    assert plan_resp.status_code == 200
    trip_a = plan_resp.json()
    trip_id = trip_a["trip"]["id"]

    # 2. User A can list and retrieve trip
    list_resp = client.get("/api/v1/trips", headers=USER_A_AUTH)
    assert list_resp.status_code == 200
    assert any(t["id"] == trip_id for t in list_resp.json())

    get_resp = client.get(f"/api/v1/trips/{trip_id}", headers=USER_A_AUTH)
    assert get_resp.status_code == 200
    assert get_resp.json()["trip"]["id"] == trip_id

    # 3. User B CANNOT list or retrieve User A's trip (cross-user isolation)
    b_list = client.get("/api/v1/trips", headers=USER_B_AUTH)
    assert b_list.status_code == 200
    assert not any(t["id"] == trip_id for t in b_list.json())

    b_get = client.get(f"/api/v1/trips/{trip_id}", headers=USER_B_AUTH)
    assert b_get.status_code == 404

    # 4. User A explores persisted places
    window = (
        trip_a["free_time_windows"][0]
        if trip_a.get("free_time_windows")
        else {
            "start_at": "2026-11-13T10:00:00Z",
            "end_at": "2026-11-13T13:00:00Z",
            "origin": {"lat": 15.4921, "lng": 73.7737},
            "duration_minutes": 180,
        }
    )
    explore_resp = client.post(
        f"/api/v1/trips/{trip_id}/explore",
        headers=USER_A_AUTH,
        json={"window": window, "interests": ["history"]},
    )
    assert explore_resp.status_code == 200
    recs = explore_resp.json()
    assert isinstance(recs, list)
    assert recs

    if recs:
        place_id = recs[0]["place"]["place_id"]

        # 5. Stale version bump check (passing wrong version returns 409 Conflict)
        stale_add = client.post(
            f"/api/v1/trips/{trip_id}/itinerary-items",
            headers=USER_A_AUTH,
            json={
                "place_id": place_id,
                "window": window,
                "expected_trip_version": 999,
            },
        )
        assert stale_add.status_code == 409
        assert stale_add.json()["detail"]["category"] == "STALE_TRIP_STATE"

        # 6. User B cannot mutate User A's trip
        b_add = client.post(
            f"/api/v1/trips/{trip_id}/itinerary-items",
            headers=USER_B_AUTH,
            json={
                "place_id": place_id,
                "window": window,
                "expected_trip_version": 1,
            },
        )
        assert b_add.status_code == 404

        # 7. Valid Add to Today for User A
        add_resp = client.post(
            f"/api/v1/trips/{trip_id}/itinerary-items",
            headers=USER_A_AUTH,
            json={
                "place_id": place_id,
                "window": window,
                "expected_trip_version": 1,
            },
        )
        assert add_resp.status_code == 200
        updated_plan = add_resp.json()
        assert updated_plan["trip"]["version"] == 2
        assert updated_plan["budget"]["remaining"] == (
            trip_a["budget"]["remaining"] - recs[0]["place"]["price"]["amount"]
        )
        user_item = next(
            (i for i in updated_plan["itinerary"] if i.get("source") == "user_added"), None
        )
        assert user_item is not None
        reloaded = client.get(f"/api/v1/trips/{trip_id}", headers=USER_A_AUTH).json()
        assert any(i["id"] == user_item["id"] for i in reloaded["itinerary"])
        assert reloaded["budget"] == updated_plan["budget"]

        # 8. Durable Undo (Delete item)
        item_id = user_item["id"]
        del_resp = client.delete(
            f"/api/v1/trips/{trip_id}/itinerary-items/{item_id}?expected_version=2",
            headers=USER_A_AUTH,
        )
        assert del_resp.status_code == 200
        final_plan = del_resp.json()
        assert final_plan["trip"]["version"] == 3
        assert not any(i["id"] == item_id for i in final_plan["itinerary"])
        assert final_plan["budget"] == trip_a["budget"]


def test_explorer_rejects_a_client_invented_window() -> None:
    plan = client.post(
        "/api/v1/trips/plan",
        headers=USER_A_AUTH,
        json={"prompt": "Goa for five days from Indore for two people under 30000"},
    ).json()
    forged = dict(plan["free_time_windows"][0])
    forged["start_at"] = "2026-11-12T02:00:00Z"
    response = client.post(
        f"/api/v1/trips/{plan['trip']['id']}/explore",
        headers=USER_A_AUTH,
        json={"window": forged},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["category"] == "INVALID_WINDOW"
