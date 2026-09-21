import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.models.domain import (
    GeoPoint,
    Money,
    OpeningHours,
    OpeningPeriod,
    PlaceCandidate,
    TripConstraints,
)
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.services.url_security import is_safe_outbound_url

SEARCH_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.location",
        "places.primaryType",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.formattedAddress",
        "places.priceLevel",
        "places.currentOpeningHours",
        "places.googleMapsUri",
    ]
)
DETAIL_FIELD_MASK = SEARCH_FIELD_MASK.replace("places.", "")

INTEREST_TYPES: dict[str, tuple[str, ...]] = {
    "history": ("historical_landmark", "history_museum", "museum"),
    "beaches": ("beach",),
    "beach": ("beach",),
    "nature": ("park", "national_park", "tourist_attraction"),
    "food": ("restaurant", "cafe"),
    "nightlife": ("bar", "night_club"),
}


class GooglePlacesClient:
    base_url = "https://places.googleapis.com/v1"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 12,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is required when PLACES_PROVIDER=google")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client

    async def search_text(
        self, query: str, *, included_type: str | None = None, max_results: int = 10
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "textQuery": query,
            "maxResultCount": min(max(max_results, 1), 20),
            "languageCode": "en",
            "regionCode": "IN",
        }
        if included_type:
            body.update({"includedType": included_type, "strictTypeFiltering": False})
        data = await self._request("POST", "/places:searchText", SEARCH_FIELD_MASK, json=body)
        return self._places(data)

    async def search_nearby(
        self,
        location: GeoPoint,
        *,
        included_types: list[str],
        radius_meters: int = 5000,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        body = {
            "includedTypes": included_types[:50],
            "maxResultCount": min(max(max_results, 1), 20),
            "rankPreference": "POPULARITY",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": location.lat, "longitude": location.lng},
                    "radius": float(min(max(radius_meters, 100), 25_000)),
                }
            },
        }
        data = await self._request("POST", "/places:searchNearby", SEARCH_FIELD_MASK, json=body)
        return self._places(data)

    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        if not place_id or len(place_id) > 255 or "/" in place_id:
            raise ProviderException(
                ProviderErrorCategory.INVALID_REQUEST, "Invalid Google Place ID", retryable=False
            )
        return await self._request("GET", f"/places/{quote(place_id, safe='')}", DETAIL_FIELD_MASK)

    async def _request(
        self, method: str, path: str, field_mask: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        for attempt in range(self.max_retries + 1):
            try:
                if self._client:
                    response = await self._client.request(
                        method, self.base_url + path, headers=headers, json=json
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.request(
                            method, self.base_url + path, headers=headers, json=json
                        )
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise ProviderException(
                    ProviderErrorCategory.TIMEOUT, "Google Places request timed out", retryable=True
                ) from error
            except httpx.HTTPError as error:
                raise ProviderException(
                    ProviderErrorCategory.PROVIDER_DOWN,
                    "Google Places request failed",
                    retryable=True,
                ) from error

            if response.status_code in {401, 403}:
                raise ProviderException(
                    ProviderErrorCategory.AUTH_FAILED,
                    "Google Places authentication failed",
                    retryable=False,
                )
            if response.status_code == 400:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Google Places rejected the request",
                    retryable=False,
                )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                category = (
                    ProviderErrorCategory.RATE_LIMITED
                    if response.status_code == 429
                    else ProviderErrorCategory.PROVIDER_DOWN
                )
                raise ProviderException(category, "Google Places is unavailable", retryable=True)
            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Google Places returned invalid JSON",
                    retryable=False,
                ) from error
            if not isinstance(payload, dict):
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Google Places returned an unexpected response",
                    retryable=False,
                )
            return payload
        raise AssertionError("bounded retry loop exited unexpectedly")

    @staticmethod
    def _places(payload: dict[str, Any]) -> list[dict[str, Any]]:
        places = payload.get("places", [])
        if not isinstance(places, list):
            raise ProviderException(
                ProviderErrorCategory.INVALID_RESPONSE,
                "Google Places response has an invalid places collection",
                retryable=False,
            )
        return [place for place in places if isinstance(place, dict)]


class GooglePlacesProvider:
    def __init__(self, client: GooglePlacesClient) -> None:
        self.client = client

    async def search(self, request: TripConstraints) -> list[PlaceCandidate]:
        interests = request.preferences.interests or ["tourist attractions"]
        searches = [
            self.client.search_text(
                f"{interest} in {request.destination}",
                included_type=self._types([interest])[0] if self._types([interest]) else None,
                max_results=min(8, 20),
            )
            for interest in interests[:5]
        ]
        batches = await asyncio.gather(*searches)
        return self._normalize_many(place for batch in batches for place in batch)[:20]

    async def search_nearby(
        self,
        location: GeoPoint,
        interests: list[str],
        *,
        radius_meters: int = 5000,
        max_results: int = 10,
    ) -> list[PlaceCandidate]:
        rows = await self.client.search_nearby(
            location,
            included_types=self._types(interests) or ["tourist_attraction"],
            radius_meters=radius_meters,
            max_results=max_results,
        )
        return self._normalize_many(rows)[:max_results]

    async def get_details(self, place_id: str) -> PlaceCandidate | None:
        return self._normalize(await self.client.get_place_details(place_id))

    def _normalize_many(self, rows) -> list[PlaceCandidate]:
        result: list[PlaceCandidate] = []
        seen: set[str] = set()
        for row in rows:
            candidate = self._normalize(row)
            if candidate and candidate.provider_id not in seen:
                seen.add(candidate.provider_id or candidate.place_id)
                result.append(candidate)
        return result

    @staticmethod
    def _normalize(row: dict[str, Any]) -> PlaceCandidate | None:
        try:
            place_id = row["id"]
            name = row["displayName"]["text"]
            if (
                not isinstance(place_id, str)
                or not place_id
                or not isinstance(name, str)
                or not name
            ):
                return None
            location = GeoPoint(lat=row["location"]["latitude"], lng=row["location"]["longitude"])
            hours_data = row.get("currentOpeningHours")
            hours = None
            open_now = None
            if isinstance(hours_data, dict):
                open_now = hours_data.get("openNow")
                periods = []
                for period in hours_data.get("periods", []):
                    opened, closed = period.get("open", {}), period.get("close", {})
                    periods.append(
                        OpeningPeriod(
                            open_day=opened["day"],
                            open_hour=opened.get("hour", 0),
                            open_minute=opened.get("minute", 0),
                            close_day=closed.get("day"),
                            close_hour=closed.get("hour"),
                            close_minute=closed.get("minute"),
                        )
                    )
                hours = OpeningHours(
                    status="OPEN"
                    if open_now is True
                    else "CLOSED"
                    if open_now is False
                    else "UNKNOWN",
                    periods=periods,
                    weekday_descriptions=hours_data.get("weekdayDescriptions", []),
                )
            maps_url = row.get("googleMapsUri")
            if maps_url and not is_safe_outbound_url(
                maps_url, {"google.com", "www.google.com", "maps.google.com"}
            ):
                maps_url = None
            types = row.get("types", [])
            primary_type = row.get("primaryType") or (types[0] if types else "place")
            return PlaceCandidate(
                place_id=f"google:{place_id}",
                provider="google",
                provider_id=place_id,
                name=name,
                category=primary_type,
                types=types,
                location=location,
                rating=row.get("rating"),
                rating_count=row.get("userRatingCount"),
                price=Money(amount=0),
                maps_url=maps_url,
                open_now=open_now,
                opening_hours=hours,
                formatted_address=row.get("formattedAddress"),
                price_level=row.get("priceLevel"),
                retrieved_at=datetime.now(UTC),
                interest_tags=GooglePlacesProvider._interest_tags(types),
            )
        except (KeyError, TypeError, ValueError, ValidationError):
            return None

    @staticmethod
    def _types(interests: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                t for interest in interests for t in INTEREST_TYPES.get(interest.lower(), ())
            )
        )

    @staticmethod
    def _interest_tags(types: list[str]) -> list[str]:
        return [
            interest
            for interest, mapped in INTEREST_TYPES.items()
            if set(types).intersection(mapped)
        ]
