import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.domain import (
    DataSourceStatus,
    GeoPoint,
    ItineraryItem,
    PlaceCandidate,
    Trip,
    TripConstraints,
    TripPlan,
    TripStatus,
)
from app.providers.contracts import FlightProvider, HotelProvider, PlacesProvider, RoutesProvider
from app.providers.errors import ProviderException
from app.services.budget import calculate_budget
from app.services.schedule import validate_schedule


class TripPlanner:
    def __init__(
        self,
        flights: FlightProvider,
        hotels: HotelProvider,
        places: PlacesProvider,
        routes: RoutesProvider,
        *,
        data_mode: str = "demo",
        sources: DataSourceStatus | None = None,
    ) -> None:
        self.flights = flights
        self.hotels = hotels
        self.places = places
        self.routes = routes
        self.data_mode = data_mode
        self.sources = sources or DataSourceStatus()

    async def plan(self, constraints: TripConstraints) -> TripPlan:
        flight_options, hotel_options, places = await asyncio.gather(
            self.flights.search(constraints),
            self.hotels.search(constraints),
            self.places.search(constraints),
        )

        itinerary = await self._build_route_aware_itinerary(constraints, places)
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
            sources=self.sources,
            warnings=warnings,
        )

    async def _build_route_aware_itinerary(
        self, constraints: TripConstraints, places: list[PlaceCandidate]
    ) -> list[ItineraryItem]:
        if not places:
            return []

        days_count = max(1, (constraints.end_date - constraints.start_date).days)
        pace = constraints.preferences.pace
        per_day = 2 if pace == "relaxed" else 4 if pace == "packed" else 3

        items: list[ItineraryItem] = []
        place_idx = 0
        total_places = len(places)

        for d in range(days_count):
            day_date = constraints.start_date + timedelta(days=d)
            daily_count = min(per_day, total_places - place_idx)
            if daily_count <= 0:
                break

            current_time = datetime.combine(day_date, datetime.min.time(), tzinfo=UTC) + timedelta(
                hours=9
            )
            prev_location: GeoPoint | None = None

            for i in range(daily_count):
                place = places[place_idx % total_places]
                place_idx += 1

                travel_min = 0
                if prev_location is not None:
                    try:
                        estimate = await self.routes.compute_route(prev_location, place.location)
                    except ProviderException:
                        # A route-dependent transition cannot be proven feasible without a route.
                        continue
                    travel_min = estimate.duration_minutes

                start_at = current_time + timedelta(minutes=travel_min)
                visit_min = place.suggested_visit_minutes or 60
                end_at = start_at + timedelta(minutes=visit_min)

                item_id = f"day{d + 1}-item{i + 1}-{place.place_id.replace(':', '_')}"
                items.append(
                    ItineraryItem(
                        id=item_id,
                        title=place.name,
                        category=place.category or "attraction",
                        start_at=start_at,
                        end_at=end_at,
                        location=place.location,
                        place_id=place.place_id,
                        cost=place.price,
                        travel_from_previous_minutes=travel_min,
                    )
                )
                prev_location = place.location
                current_time = end_at + timedelta(minutes=30)  # 30 min buffer

        return items
