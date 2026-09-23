"""Narrow Amadeus Self-Service flight adapter.

Only provider-returned inventory is normalized.  The adapter intentionally leaves
``booking_url`` empty because Flight Offers Search does not provide an official
consumer booking redirect that TripPilot can safely construct.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.models.domain import AirportLocation, FlightOption, Money, TripConstraints
from app.providers.errors import ProviderErrorCategory, ProviderException


class AmadeusClient:
    """OAuth and REST client for the documented Self-Service endpoints."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        environment: str = "test",
        timeout_seconds: float = 12,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("Amadeus credentials are required when FLIGHTS_PROVIDER=amadeus")
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = (
            "https://test.api.amadeus.com" if environment == "test" else "https://api.amadeus.com"
        )
        self.timeout_seconds, self.max_retries, self._client = (
            timeout_seconds,
            max_retries,
            client,
        )
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    async def token(self) -> str:
        if self._token and self._token_expires_at and self._token_expires_at > datetime.now(UTC):
            return self._token
        async with self._token_lock:
            if (
                self._token
                and self._token_expires_at
                and self._token_expires_at > datetime.now(UTC)
            ):
                return self._token
            data = await self._raw_request(
                "POST",
                "/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                authenticated=False,
            )
            token = data.get("access_token")
            expires_in = data.get("expires_in")
            if not isinstance(token, str) or not token or not isinstance(expires_in, int):
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Amadeus token response was invalid",
                    retryable=False,
                )
            self._token = token
            self._token_expires_at = datetime.now(UTC) + timedelta(seconds=max(0, expires_in - 60))
            return token

    async def locations(self, keyword: str) -> list[dict[str, Any]]:
        return self._data_list(
            await self.request(
                "GET",
                "/v1/reference-data/locations",
                params={"keyword": keyword[:40], "subType": "AIRPORT,CITY", "page[limit]": "8"},
            )
        )

    async def flight_offers(self, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self.request("GET", "/v2/shopping/flight-offers", params=params)
        return self._data_list(response)

    async def request(
        self, method: str, path: str, *, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        return await self._raw_request(method, path, params=params, authenticated=True)

    async def _raw_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        authenticated: bool,
    ) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            headers: dict[str, str] = {}
            if authenticated:
                headers["Authorization"] = f"Bearer {await self.token()}"
            try:
                if self._client:
                    response = await self._client.request(
                        method, self.base_url + path, params=params, data=data, headers=headers
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.request(
                            method, self.base_url + path, params=params, data=data, headers=headers
                        )
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise ProviderException(
                    ProviderErrorCategory.TIMEOUT, "Amadeus request timed out", retryable=True
                ) from error
            except httpx.HTTPError as error:
                raise ProviderException(
                    ProviderErrorCategory.PROVIDER_DOWN, "Amadeus request failed", retryable=True
                ) from error
            if response.status_code in {401, 403}:
                raise ProviderException(
                    ProviderErrorCategory.AUTH_FAILED,
                    "Amadeus authentication failed",
                    retryable=False,
                )
            if response.status_code == 400:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Amadeus rejected the request",
                    retryable=False,
                )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.05 * 2**attempt)
                    continue
                category = (
                    ProviderErrorCategory.RATE_LIMITED
                    if response.status_code == 429
                    else ProviderErrorCategory.PROVIDER_DOWN
                )
                raise ProviderException(category, "Amadeus is unavailable", retryable=True)
            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Amadeus returned invalid JSON",
                    retryable=False,
                ) from error
            if not isinstance(payload, dict):
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Amadeus returned an unexpected response",
                    retryable=False,
                )
            return payload
        raise AssertionError("bounded retry loop exited unexpectedly")

    @staticmethod
    def _data_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise ProviderException(
                ProviderErrorCategory.INVALID_RESPONSE,
                "Amadeus response has an invalid data collection",
                retryable=False,
            )
        return [row for row in data if isinstance(row, dict)]


class AmadeusFlightProvider:
    def __init__(self, client: AmadeusClient) -> None:
        self.client = client

    async def resolve_location(self, query: str) -> list[AirportLocation]:
        if not query.strip():
            return []
        rows = await self.client.locations(query)
        locations: list[AirportLocation] = []
        for row in rows:
            code = row.get("iataCode")
            name = row.get("name")
            if not isinstance(code, str) or len(code) != 3 or not isinstance(name, str):
                continue
            address = row.get("address") if isinstance(row.get("address"), dict) else {}
            locations.append(
                AirportLocation(
                    code=code,
                    name=name,
                    city_name=address.get("cityName"),
                    country_code=address.get("countryCode"),
                )
            )
        return locations

    async def search(self, request: TripConstraints) -> list[FlightOption]:
        origins, destinations = await asyncio.gather(
            self.resolve_location(request.origin), self.resolve_location(request.destination)
        )
        if not origins or not destinations:
            return []
        params = {
            "originLocationCode": origins[0].code,
            "destinationLocationCode": destinations[0].code,
            "departureDate": request.start_date.isoformat(),
            "returnDate": request.end_date.isoformat(),
            "adults": str(request.travelers),
            "currencyCode": request.budget.currency,
            "max": "12",
        }
        return self._normalize_many(await self.client.flight_offers(params))

    @staticmethod
    def _normalize_many(rows: list[dict[str, Any]]) -> list[FlightOption]:
        normalized: list[FlightOption] = []
        now = datetime.now(UTC)
        for row in rows:
            try:
                itineraries = row["itineraries"]
                outbound = itineraries[0]
                segments = outbound["segments"]
                first, last = segments[0], segments[-1]
                departure = datetime.fromisoformat(first["departure"]["at"])
                arrival = datetime.fromisoformat(last["arrival"]["at"])
                price = row["price"]
                amount = int(round(float(price["grandTotal"])))
                carrier = first.get("carrierCode", "Unknown carrier")
                normalized.append(
                    FlightOption(
                        id=f"amadeus:{row['id']}",
                        airline=carrier,
                        departure_airport=first["departure"]["iataCode"],
                        arrival_airport=last["arrival"]["iataCode"],
                        departure_time=departure,
                        arrival_time=arrival,
                        duration_minutes=max(1, int((arrival - departure).total_seconds() // 60)),
                        stops=max(0, len(segments) - 1),
                        price=Money(amount=amount, currency=price.get("currency", "INR")),
                        provider="amadeus",
                        booking_url=None,
                        retrieved_at=now,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return normalized
