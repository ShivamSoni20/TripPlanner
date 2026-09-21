from datetime import UTC, datetime, time

from app.models.domain import (
    FlightOption,
    GeoPoint,
    HotelOption,
    Money,
    PlaceCandidate,
    TripConstraints,
)


def _at(day, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


class DemoFlightProvider:
    async def search(self, request: TripConstraints) -> list[FlightOption]:
        now = datetime.now(UTC)
        rows = [
            ("indigo-6e-813", "IndiGo", 7, 20, 9, 5, 0, 8400),
            ("aix-ix-198", "Air India Express", 14, 10, 18, 25, 1, 7620),
            ("airindia-ai-634", "Air India", 10, 30, 13, 40, 1, 9180),
        ]
        return [
            FlightOption(
                id=id_,
                airline=airline,
                departure_airport="IDR",
                arrival_airport="GOI",
                departure_time=_at(request.start_date, depart_hour, depart_minute),
                arrival_time=_at(request.start_date, arrival_hour, arrival_minute),
                duration_minutes=(arrival_hour * 60 + arrival_minute)
                - (depart_hour * 60 + depart_minute),
                stops=stops,
                price=Money(amount=price),
                provider="demo",
                booking_url="https://www.google.com/travel/flights",
                retrieved_at=now,
            )
            for (
                id_,
                airline,
                depart_hour,
                depart_minute,
                arrival_hour,
                arrival_minute,
                stops,
                price,
            ) in rows
        ]


class DemoHotelProvider:
    async def search(self, request: TripConstraints) -> list[HotelOption]:
        now = datetime.now(UTC)
        rows = [
            ("casa-anjuna", "Casa Anjuna", 15.5732, 73.7419, 4.7, 8250),
            ("heritage-panjim", "The Heritage Panjim", 15.4989, 73.8278, 4.6, 9400),
            ("candolim-garden", "Candolim Garden House", 15.5183, 73.7625, 4.5, 7850),
        ]
        nights = max(1, (request.end_date - request.start_date).days)
        return [
            HotelOption(
                id=id_,
                name=name,
                location=GeoPoint(lat=lat, lng=lng),
                rating=rating,
                total_price=Money(amount=total),
                nightly_price=Money(amount=round(total / nights)),
                amenities=["Breakfast", "Wi-Fi", "Flexible cancellation"],
                provider="demo",
                booking_url="https://www.google.com/travel/hotels",
                retrieved_at=now,
            )
            for id_, name, lat, lng, rating, total in rows
        ]


class DemoPlacesProvider:
    async def search(self, request: TripConstraints) -> list[PlaceCandidate]:
        return [
            PlaceCandidate(
                place_id="demo-fort-aguada",
                name="Fort Aguada",
                category="history",
                location=GeoPoint(lat=15.4921, lng=73.7737),
                rating=4.5,
                rating_count=34210,
                price=Money(amount=100),
                maps_url="https://www.google.com/maps/search/?api=1&query=Fort+Aguada",
                open_now=True,
                suggested_visit_minutes=75,
                weather_suitability=0.9,
                interest_tags=["history", "architecture"],
            ),
            PlaceCandidate(
                place_id="demo-sinquerim-beach",
                name="Sinquerim Beach",
                category="beach",
                location=GeoPoint(lat=15.5008, lng=73.7676),
                rating=4.6,
                rating_count=8700,
                price=Money(amount=0),
                maps_url="https://www.google.com/maps/search/?api=1&query=Sinquerim+Beach",
                open_now=True,
                suggested_visit_minutes=60,
                weather_suitability=0.95,
                interest_tags=["beaches", "nature"],
            ),
            PlaceCandidate(
                place_id="demo-museum-goa",
                name="Museum of Goa",
                category="museum",
                location=GeoPoint(lat=15.5595, lng=73.7979),
                rating=4.3,
                rating_count=4100,
                price=Money(amount=300),
                maps_url="https://www.google.com/maps/search/?api=1&query=Museum+of+Goa",
                open_now=True,
                suggested_visit_minutes=60,
                weather_suitability=1,
                interest_tags=["history", "art"],
            ),
        ]
