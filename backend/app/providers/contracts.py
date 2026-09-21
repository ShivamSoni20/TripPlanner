from typing import Protocol

from app.models.domain import FlightOption, GeoPoint, HotelOption, PlaceCandidate, TripConstraints


class FlightProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[FlightOption]: ...


class HotelProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[HotelOption]: ...


class PlacesProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[PlaceCandidate]: ...

    async def search_nearby(
        self,
        location: GeoPoint,
        interests: list[str],
        *,
        radius_meters: int = 5000,
        max_results: int = 10,
    ) -> list[PlaceCandidate]: ...

    async def get_details(self, place_id: str) -> PlaceCandidate | None: ...
