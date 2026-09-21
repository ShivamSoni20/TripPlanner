from datetime import datetime
from typing import Protocol

from app.models.domain import (
    FlightOption,
    GeoPoint,
    HotelOption,
    PlaceCandidate,
    RouteEstimate,
    RouteMatrixEntry,
    TripConstraints,
)


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


class RoutesProvider(Protocol):
    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_at: datetime | None = None,
    ) -> RouteEstimate: ...

    async def compute_matrix(
        self,
        origins: list[GeoPoint],
        destinations: list[GeoPoint],
        *,
        departure_at: datetime | None = None,
    ) -> list[RouteMatrixEntry]: ...
