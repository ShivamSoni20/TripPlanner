import math
from datetime import UTC, date, datetime, time

from app.models.domain import (
    DailyWeather,
    FlightOption,
    GeoPoint,
    HotelOption,
    Money,
    PlaceCandidate,
    RouteEstimate,
    RouteMatrixEntry,
    TripConstraints,
    WeatherAvailability,
    WeatherForecast,
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
        _ = request
        return self._places()

    async def search_nearby(
        self,
        location: GeoPoint,
        interests: list[str],
        *,
        radius_meters: int = 5000,
        max_results: int = 10,
    ) -> list[PlaceCandidate]:
        _ = (location, radius_meters)
        places = self._places()
        if interests:
            normalized = {interest.lower() for interest in interests}
            places = [place for place in places if normalized.intersection(place.interest_tags)]
        return places[:max_results]

    async def get_details(self, place_id: str) -> PlaceCandidate | None:
        return next((place for place in self._places() if place.place_id == place_id), None)

    @staticmethod
    def _places() -> list[PlaceCandidate]:
        now = datetime.now(UTC)
        return [
            PlaceCandidate(
                place_id="demo-fort-aguada",
                provider_id="demo-fort-aguada",
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
                retrieved_at=now,
            ),
            PlaceCandidate(
                place_id="demo-sinquerim-beach",
                provider_id="demo-sinquerim-beach",
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
                retrieved_at=now,
            ),
            PlaceCandidate(
                place_id="demo-museum-goa",
                provider_id="demo-museum-goa",
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
                retrieved_at=now,
            ),
        ]


def _haversine_distance_meters(p1: GeoPoint, p2: GeoPoint) -> int:
    R = 6371000.0  # Earth radius in meters
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lng)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(R * c)


class DemoRoutesProvider:
    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_at: datetime | None = None,
    ) -> RouteEstimate:
        _ = departure_at
        meters = _haversine_distance_meters(origin, destination)
        km = meters / 1000.0
        # Estimate ~30 km/h driving speed = 2 mins per km, min 3 mins
        duration_minutes = max(3, math.ceil(km * 2.0))
        return RouteEstimate(
            origin=origin,
            destination=destination,
            distance_meters=meters,
            duration_minutes=duration_minutes,
            travel_mode="DRIVE",
            provider="demo",
            retrieved_at=datetime.now(UTC),
        )

    async def compute_matrix(
        self,
        origins: list[GeoPoint],
        destinations: list[GeoPoint],
        *,
        departure_at: datetime | None = None,
    ) -> list[RouteMatrixEntry]:
        _ = departure_at
        results: list[RouteMatrixEntry] = []
        for o_idx, origin in enumerate(origins):
            for d_idx, dest in enumerate(destinations):
                meters = _haversine_distance_meters(origin, dest)
                km = meters / 1000.0
                duration_minutes = max(3, math.ceil(km * 2.0))
                results.append(
                    RouteMatrixEntry(
                        origin_index=o_idx,
                        destination_index=d_idx,
                        distance_meters=meters,
                        duration_minutes=duration_minutes,
                        route_exists=True,
                        provider="demo",
                    )
                )
        return results


class DemoWeatherProvider:
    async def get_forecast(
        self, *, location: GeoPoint, start_date: date, end_date: date
    ) -> WeatherForecast:
        days = []
        conditions = [("Sunny", 1000, 10), ("Afternoon rain", 1183, 70), ("Clear", 1000, 5)]
        for offset in range(max(0, (end_date - start_date).days + 1)):
            condition, code, rain = conditions[offset % len(conditions)]
            days.append(
                DailyWeather(
                    date=start_date.fromordinal(start_date.toordinal() + offset),
                    min_temperature_c=24,
                    max_temperature_c=30,
                    condition_text=condition,
                    condition_code=code,
                    chance_of_rain=rain,
                    total_precipitation_mm=2.0 if rain else 0,
                    max_wind_kph=18,
                )
            )
        return WeatherForecast(
            availability=WeatherAvailability.AVAILABLE,
            location=location,
            provider="demo",
            days=days,
        )
