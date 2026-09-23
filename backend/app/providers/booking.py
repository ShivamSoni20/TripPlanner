"""Booking.com Demand API v3.2 accommodation adapter.

This module targets the documented v3.2 HTTPS API. It is deliberately only
activated when credentials are provided; demo inventory remains the default.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.domain import GeoPoint, HotelOption, Money, TripConstraints
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.services.url_security import is_safe_outbound_url


class BookingDemandClient:
    def __init__(
        self,
        *,
        api_token: str,
        affiliate_id: str,
        environment: str = "sandbox",
        timeout_seconds: float = 12,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_token or not affiliate_id:
            raise ValueError("Booking API token and affiliate ID are required")
        self.base_url = (
            "https://demandapi-sandbox.booking.com/3.2"
            if environment == "sandbox"
            else "https://demandapi.booking.com/3.2"
        )
        self.api_token, self.affiliate_id = api_token, affiliate_id
        self.timeout_seconds, self.max_retries, self._client = (
            timeout_seconds,
            max_retries,
            client,
        )

    async def cities(self, name: str) -> list[dict[str, Any]]:
        return await self._post("/common/locations/cities", {"query": name[:80]})

    async def search(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        return await self._post("/accommodations/search", body)

    async def _post(self, path: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "X-Affiliate-Id": self.affiliate_id,
            "Content-Type": "application/json",
        }
        for attempt in range(self.max_retries + 1):
            try:
                if self._client:
                    response = await self._client.post(
                        self.base_url + path, json=body, headers=headers
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.post(
                            self.base_url + path, json=body, headers=headers
                        )
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise ProviderException(
                    ProviderErrorCategory.TIMEOUT,
                    "Booking request timed out",
                    retryable=True,
                ) from error
            except httpx.HTTPError as error:
                raise ProviderException(
                    ProviderErrorCategory.PROVIDER_DOWN,
                    "Booking request failed",
                    retryable=True,
                ) from error
            if response.status_code in {401, 403}:
                raise ProviderException(
                    ProviderErrorCategory.AUTH_FAILED,
                    "Booking authentication failed",
                    retryable=False,
                )
            if response.status_code == 400:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Booking rejected the request",
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
                raise ProviderException(category, "Booking is unavailable", retryable=True)
            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Booking returned invalid JSON",
                    retryable=False,
                ) from error
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Booking returned an unexpected response",
                    retryable=False,
                )
            return [row for row in data if isinstance(row, dict)]
        raise AssertionError("bounded retry loop exited unexpectedly")


class BookingHotelProvider:
    def __init__(self, client: BookingDemandClient, *, booker_country: str = "in") -> None:
        self.client, self.booker_country = client, booker_country.lower()

    async def search(self, request: TripConstraints) -> list[HotelOption]:
        cities = await self.client.cities(request.destination)
        city_id = next((row.get("id") for row in cities if isinstance(row.get("id"), int)), None)
        if city_id is None:
            return []
        rows = await self.client.search(
            {
                "city": city_id,
                "booker": {"country": self.booker_country, "platform": "desktop"},
                "checkin": request.start_date.isoformat(),
                "checkout": request.end_date.isoformat(),
                "currency": request.budget.currency,
                "guests": {"number_of_adults": request.travelers, "number_of_rooms": 1},
            }
        )
        return self._normalize_many(rows, max(1, (request.end_date - request.start_date).days))[:12]

    @staticmethod
    def _normalize_many(rows: list[dict[str, Any]], nights: int) -> list[HotelOption]:
        result: list[HotelOption] = []
        for row in rows:
            try:
                price = row["price"]
                total = price.get("total") or price.get("book")
                amount = int(round(float(total)))
                currency = row.get("currency", {}).get("booker") or price.get("currency") or "INR"
                coordinates = row.get("location", {})
                url = row.get("url")
                if url and not is_safe_outbound_url(url, {"booking.com", "www.booking.com"}):
                    url = None
                result.append(
                    HotelOption(
                        id=f"booking:{row['id']}",
                        name=row["name"],
                        location=GeoPoint(
                            lat=coordinates["latitude"], lng=coordinates["longitude"]
                        ),
                        rating=row.get("review_score"),
                        total_price=Money(amount=amount, currency=currency),
                        nightly_price=Money(amount=round(amount / nights), currency=currency),
                        amenities=[],
                        provider="booking",
                        booking_url=url,
                        retrieved_at=datetime.now(UTC),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return result
