from datetime import UTC, datetime

import pytest

from app.models.domain import GeoPoint, TimeWindow
from app.providers.demo import DemoPlacesProvider, DemoRoutesProvider
from app.services.explorer import ExplorerService
from app.services.free_time import detect_free_windows


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
