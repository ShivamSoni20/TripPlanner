from datetime import UTC, datetime

import pytest

from app.models.domain import (
    DailyWeather,
    GeoPoint,
    Money,
    OpeningHours,
    OpeningPeriod,
    PlaceCandidate,
    RouteMatrixEntry,
    TimeWindow,
    WeatherAvailability,
    WeatherForecast,
)
from app.providers.demo import DemoPlacesProvider, DemoRoutesProvider
from app.services.explorer import ExplorerService
from app.services.free_time import detect_free_windows, is_open_for_visit


@pytest.mark.asyncio
async def test_explorer_recommends_feasible_places() -> None:
    places = DemoPlacesProvider()
    routes = DemoRoutesProvider()
    explorer = ExplorerService(places, routes)

    window = TimeWindow(
        start_at=datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 11, 13, 13, 0, tzinfo=UTC),
        origin=GeoPoint(lat=15.5183, lng=73.7625),  # Candolim
        next_destination=GeoPoint(lat=15.4989, lng=73.8278),  # Panjim
        duration_minutes=180,
    )

    recs = await explorer.explore(window=window, interests=["history"])
    assert len(recs) > 0
    assert recs[0].rank == "Best Fit"
    assert recs[0].feasible is True
    assert recs[0].travel_to_minutes > 0


@pytest.mark.asyncio
async def test_explorer_returns_empty_when_window_too_short() -> None:
    places = DemoPlacesProvider()
    routes = DemoRoutesProvider()
    explorer = ExplorerService(places, routes)

    window = TimeWindow(
        start_at=datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 11, 13, 10, 15, tzinfo=UTC),
        origin=GeoPoint(lat=15.5183, lng=73.7625),
        next_destination=GeoPoint(lat=15.4989, lng=73.8278),
        duration_minutes=15,  # 15 minutes is not enough for travel + visit + travel
    )

    recs = await explorer.explore(window=window, interests=["history"])
    assert len(recs) == 0


def test_free_window_detection() -> None:
    from app.models.domain import ItineraryItem, Money

    day = datetime(2026, 11, 13, 0, 0, tzinfo=UTC)
    item1 = ItineraryItem(
        id="item-1",
        title="Breakfast",
        category="food",
        start_at=day.replace(hour=9),
        end_at=day.replace(hour=10),
        location=GeoPoint(lat=15.5, lng=73.7),
        cost=Money(amount=500),
    )
    item2 = ItineraryItem(
        id="item-2",
        title="Dinner",
        category="food",
        start_at=day.replace(hour=19, minute=30),
        end_at=day.replace(hour=21),
        location=GeoPoint(lat=15.49, lng=73.82),
        cost=Money(amount=2000),
    )

    windows = detect_free_windows([item1, item2], min_duration_minutes=60)
    assert len(windows) == 1
    assert windows[0].duration_minutes == 570  # 10:00 to 19:30 = 9h 30m = 570 min
    assert windows[0].origin == item1.location
    assert windows[0].next_destination == item2.location


def test_opening_hours_cover_entire_proposed_visit() -> None:
    place = PlaceCandidate(
        place_id="museum",
        name="Museum",
        category="museum",
        location=GeoPoint(lat=15.5, lng=73.8),
        opening_hours=OpeningHours(
            periods=[
                OpeningPeriod(
                    open_day=4,
                    open_hour=10,
                    open_minute=0,
                    close_day=4,
                    close_hour=12,
                    close_minute=0,
                )
            ]
        ),
    )
    thursday = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
    assert is_open_for_visit(place, thursday, 60) is True
    assert is_open_for_visit(place, thursday, 120) is False
    assert is_open_for_visit(place, thursday.replace(hour=9), 30) is False
    assert is_open_for_visit(place.model_copy(update={"opening_hours": None}), thursday, 60) is None


@pytest.mark.asyncio
async def test_explorer_excludes_rainy_outdoor_unaffordable_and_unroutable_places() -> None:
    origin = GeoPoint(lat=15.5, lng=73.8)
    candidates = [
        PlaceCandidate(
            place_id="beach",
            name="Beach",
            category="beach",
            location=GeoPoint(lat=15.51, lng=73.8),
            rating=4.9,
            price=Money(amount=0),
        ),
        PlaceCandidate(
            place_id="museum",
            name="Museum",
            category="museum",
            location=GeoPoint(lat=15.52, lng=73.8),
            rating=4.5,
            price=Money(amount=100),
        ),
        PlaceCandidate(
            place_id="expensive",
            name="Expensive",
            category="museum",
            location=GeoPoint(lat=15.53, lng=73.8),
            price=Money(amount=2000),
        ),
        PlaceCandidate(
            place_id="unroutable",
            name="Unroutable",
            category="museum",
            location=GeoPoint(lat=15.54, lng=73.8),
            price=Money(amount=0),
        ),
    ]

    class Places:
        async def search_nearby(self, **kwargs):
            return candidates

    class Routes:
        async def compute_matrix(self, origins, destinations):
            return [
                RouteMatrixEntry(
                    origin_index=0, destination_index=i, duration_minutes=10, route_exists=True
                )
                for i in range(3)
            ]

    class Weather:
        async def get_forecast(self, **kwargs):
            return WeatherForecast(
                availability=WeatherAvailability.AVAILABLE,
                location=origin,
                provider="test",
                days=[
                    DailyWeather(
                        date=datetime(2026, 11, 12, tzinfo=UTC).date(),
                        condition_text="Rain",
                        chance_of_rain=80,
                    )
                ],
            )

    window = TimeWindow(
        start_at=datetime(2026, 11, 12, 10, tzinfo=UTC),
        end_at=datetime(2026, 11, 12, 13, tzinfo=UTC),
        origin=origin,
        duration_minutes=180,
    )
    results = await ExplorerService(Places(), Routes(), Weather()).explore(
        window=window, interests=["history"], remaining_budget=500
    )
    assert [result.place.place_id for result in results] == ["museum"]
