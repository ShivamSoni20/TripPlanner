import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.domain import (
    GeoPoint,
    ItineraryItem,
    Money,
    Trip,
    TripConstraints,
    TripPlan,
    TripStatus,
)
from app.providers.contracts import FlightProvider, HotelProvider, PlacesProvider
from app.services.budget import calculate_budget
from app.services.schedule import validate_schedule


class TripPlanner:
    def __init__(
        self,
        flights: FlightProvider,
        hotels: HotelProvider,
        places: PlacesProvider,
        *,
        data_mode: str = "demo",
    ) -> None:
        self.flights = flights
        self.hotels = hotels
        self.places = places
        self.data_mode = data_mode

    async def plan(self, constraints: TripConstraints) -> TripPlan:
        flight_options, hotel_options, places = await asyncio.gather(
            self.flights.search(constraints),
            self.hotels.search(constraints),
            self.places.search(constraints),
        )
        itinerary = self._build_demo_itinerary(constraints, places)
        schedule_errors = validate_schedule(itinerary)
        if schedule_errors:
            raise ValueError("; ".join(schedule_errors))
        budget = calculate_budget(
            budget_limit=constraints.budget.amount,
            transport=flight_options[0].price.amount if flight_options else 0,
            hotel=hotel_options[0].total_price.amount if hotel_options else 0,
            food=5400,
            local_transport=3500,
            itinerary=itinerary,
        )
        now = datetime.now(UTC)
        trip = Trip(
            id=f"trip_{uuid4().hex[:12]}",
            constraints=constraints,
            status=TripStatus.READY,
            created_at=now,
            updated_at=now,
            data_mode=self.data_mode,
        )
        warnings = [] if budget.within_budget else ["Plan exceeds the requested budget"]
        return TripPlan(
            trip=trip,
            flights=flight_options,
            hotels=hotel_options,
            places=places,
            itinerary=itinerary,
            budget=budget,
            warnings=warnings,
        )

    @staticmethod
    def _build_demo_itinerary(constraints: TripConstraints, places) -> list[ItineraryItem]:
        day = constraints.start_date + timedelta(days=1)
        location = places[1].location if len(places) > 1 else GeoPoint(lat=15.5, lng=73.8)
        return [
            ItineraryItem(
                id="day2-breakfast",
                title="Breakfast in Candolim",
                category="food",
                start_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                + timedelta(hours=9),
                end_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=10),
                location=location,
                cost=Money(amount=500),
            ),
            ItineraryItem(
                id="day2-dinner",
                title="Dinner in Panjim",
                category="food",
                start_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                + timedelta(hours=19, minutes=30),
                end_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=21),
                location=GeoPoint(lat=15.4989, lng=73.8278),
                cost=Money(amount=2400),
                travel_from_previous_minutes=28,
            ),
        ]
