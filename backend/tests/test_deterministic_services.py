from datetime import UTC, datetime

import pytest

from app.models.domain import GeoPoint, ItineraryItem, Money, TimeWindow
from app.services.budget import calculate_budget
from app.services.free_time import is_feasible
from app.services.schedule import validate_schedule
from app.services.url_security import is_safe_outbound_url


def item(id_: str, start_hour: int, end_hour: int, travel: int = 0) -> ItineraryItem:
    return ItineraryItem(
        id=id_,
        title=id_,
        category="test",
        start_at=datetime(2026, 11, 12, start_hour, tzinfo=UTC),
        end_at=datetime(2026, 11, 12, end_hour, tzinfo=UTC),
        location=GeoPoint(lat=15.5, lng=73.8),
        cost=Money(amount=100),
        travel_from_previous_minutes=travel,
    )


def test_budget_reconciles() -> None:
    result = calculate_budget(
        budget_limit=30_000,
        transport=8_400,
        hotel=8_250,
        food=5_400,
        local_transport=3_500,
        itinerary=[item("a", 9, 10), item("b", 11, 12)],
    )
    assert result.total == 25_750
    assert result.remaining == 4_250
    assert result.within_budget


def test_schedule_detects_travel_conflict() -> None:
    assert validate_schedule([item("a", 9, 10), item("b", 10, 11, travel=20)]) == [
        "b starts before required travel completes"
    ]


def test_free_time_hard_constraint() -> None:
    window = TimeWindow(
        start_at=datetime(2026, 11, 12, 13, tzinfo=UTC),
        end_at=datetime(2026, 11, 12, 15, 45, tzinfo=UTC),
        origin=GeoPoint(lat=15.5, lng=73.8),
        duration_minutes=165,
    )
    assert is_feasible(
        window=window,
        travel_to_minutes=12,
        visit_duration_minutes=75,
        travel_to_next_minutes=28,
        safety_buffer_minutes=50,
    )
    assert not is_feasible(
        window=window,
        travel_to_minutes=30,
        visit_duration_minutes=90,
        travel_to_next_minutes=30,
        safety_buffer_minutes=30,
    )


def test_booking_url_allowlist() -> None:
    assert is_safe_outbound_url("https://www.google.com/travel/flights")
    assert not is_safe_outbound_url("javascript:alert(1)")
    assert not is_safe_outbound_url("https://evil.example/book")


@pytest.mark.asyncio
async def test_generic_planner_non_goa_destination() -> None:
    from datetime import date

    from app.models.domain import Pace, PlaceCandidate, TripConstraints, TripPreferences
    from app.providers.demo import DemoFlightProvider, DemoHotelProvider, DemoRoutesProvider
    from app.services.planner import TripPlanner

    class KeralaPlacesProvider:
        async def search(self, request: TripConstraints) -> list[PlaceCandidate]:
            return [
                PlaceCandidate(
                    place_id="kerala-fort-kochi",
                    provider_id="kerala-fort-kochi",
                    name="Fort Kochi Beach",
                    category="beach",
                    location=GeoPoint(lat=9.9657, lng=76.2421),
                    rating=4.7,
                    rating_count=12000,
                    price=Money(amount=0),
                    open_now=True,
                    suggested_visit_minutes=90,
                    weather_suitability=1.0,
                    interest_tags=["beaches", "nature"],
                    retrieved_at=datetime.now(UTC),
                ),
                PlaceCandidate(
                    place_id="kerala-mattancherry",
                    provider_id="kerala-mattancherry",
                    name="Mattancherry Palace",
                    category="history",
                    location=GeoPoint(lat=9.9585, lng=76.2592),
                    rating=4.5,
                    rating_count=8500,
                    price=Money(amount=50),
                    open_now=True,
                    suggested_visit_minutes=60,
                    weather_suitability=1.0,
                    interest_tags=["history"],
                    retrieved_at=datetime.now(UTC),
                ),
            ]

        async def search_nearby(self, location, interests, *, radius_meters=5000, max_results=10):
            return []

        async def get_details(self, place_id):
            return None

    constraints = TripConstraints(
        origin="Pune",
        destination="Kerala",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 4),
        travelers=2,
        budget=Money(amount=50_000),
        preferences=TripPreferences(interests=["beaches", "history"], pace=Pace.RELAXED),
    )

    planner = TripPlanner(
        DemoFlightProvider(),
        DemoHotelProvider(),
        KeralaPlacesProvider(),
        DemoRoutesProvider(),
    )
    plan = await planner.plan(constraints)

    assert len(plan.itinerary) > 0
    itinerary_titles = [item.title for item in plan.itinerary]
    assert "Breakfast in Candolim" not in itinerary_titles
    assert "Dinner in Panjim" not in itinerary_titles
    assert any("Fort Kochi" in title for title in itinerary_titles)
