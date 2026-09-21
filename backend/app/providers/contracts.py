from typing import Protocol

from app.models.domain import FlightOption, HotelOption, PlaceCandidate, TripConstraints


class FlightProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[FlightOption]: ...


class HotelProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[HotelOption]: ...


class PlacesProvider(Protocol):
    async def search(self, request: TripConstraints) -> list[PlaceCandidate]: ...
