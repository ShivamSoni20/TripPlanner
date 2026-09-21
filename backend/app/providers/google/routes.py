import asyncio
import math
from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.domain import GeoPoint, RouteEstimate, RouteMatrixEntry
from app.providers.errors import ProviderErrorCategory, ProviderException

ROUTE_FIELD_MASK = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
MATRIX_FIELD_MASK = "originIndex,destinationIndex,status,condition,distanceMeters,duration"


def parse_duration(duration_str: str | None) -> int:
    if not duration_str or not isinstance(duration_str, str):
        return 0
    cleaned = duration_str.rstrip("s").strip()
    try:
        seconds = float(cleaned)
        return max(0, math.ceil(seconds / 60.0))
    except ValueError:
        return 0


class GoogleRoutesClient:
    base_url = "https://routes.googleapis.com"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 12,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is required when ROUTES_PROVIDER=google")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client

    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        travel_mode: str = "DRIVE",
        routing_preference: str = "TRAFFIC_UNAWARE",
    ) -> dict[str, Any]:
        body = {
            "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}},
            "destination": {
                "location": {"latLng": {"latitude": destination.lat, "longitude": destination.lng}}
            },
            "travelMode": travel_mode,
            "routingPreference": routing_preference,
        }
        return await self._request(
            "POST", "/directions/v2:computeRoutes", ROUTE_FIELD_MASK, json=body
        )

    async def compute_route_matrix(
        self,
        origins: list[GeoPoint],
        destinations: list[GeoPoint],
        *,
        travel_mode: str = "DRIVE",
        routing_preference: str = "TRAFFIC_UNAWARE",
    ) -> list[dict[str, Any]]:
        body = {
            "origins": [
                {"waypoint": {"location": {"latLng": {"latitude": pt.lat, "longitude": pt.lng}}}}
                for pt in origins[:15]
            ],
            "destinations": [
                {"waypoint": {"location": {"latLng": {"latitude": pt.lat, "longitude": pt.lng}}}}
                for pt in destinations[:15]
            ],
            "travelMode": travel_mode,
            "routingPreference": routing_preference,
        }
        res = await self._request(
            "POST", "/distanceMatrix/v2:computeRouteMatrix", MATRIX_FIELD_MASK, json=body
        )
        if isinstance(res, list):
            return res
        if isinstance(res, dict) and "elements" in res:
            return res["elements"]
        return []

    async def _request(
        self, method: str, path: str, field_mask: str, *, json: dict[str, Any] | None = None
    ) -> Any:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        url = self.base_url + path
        for attempt in range(self.max_retries + 1):
            try:
                if self._client:
                    response = await self._client.request(method, url, headers=headers, json=json)
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.request(method, url, headers=headers, json=json)
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise ProviderException(
                    ProviderErrorCategory.TIMEOUT, "Google Routes request timed out", retryable=True
                ) from error
            except httpx.HTTPError as error:
                raise ProviderException(
                    ProviderErrorCategory.PROVIDER_DOWN,
                    "Google Routes request failed",
                    retryable=True,
                ) from error

            if response.status_code in {401, 403}:
                raise ProviderException(
                    ProviderErrorCategory.AUTH_FAILED,
                    "Google Routes authentication failed",
                    retryable=False,
                )
            if response.status_code == 400:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Google Routes rejected the request",
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
                raise ProviderException(category, "Google Routes is unavailable", retryable=True)

            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Google Routes returned invalid JSON",
                    retryable=False,
                ) from error
            return payload
        raise AssertionError("bounded retry loop exited unexpectedly")


class GoogleRoutesProvider:
    def __init__(
        self,
        client: GoogleRoutesClient,
        *,
        travel_mode: str = "DRIVE",
        routing_preference: str = "TRAFFIC_UNAWARE",
    ) -> None:
        self.client = client
        self.travel_mode = travel_mode
        self.routing_preference = routing_preference

    async def compute_route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        *,
        departure_at: datetime | None = None,
    ) -> RouteEstimate:
        _ = departure_at
        data = await self.client.compute_route(
            origin,
            destination,
            travel_mode=self.travel_mode,
            routing_preference=self.routing_preference,
        )
        routes = data.get("routes", [])
        if not routes or not isinstance(routes, list):
            raise ProviderException(
                ProviderErrorCategory.INVALID_RESPONSE,
                "Google Routes returned no valid route",
                retryable=False,
            )
        first = routes[0]
        duration_minutes = parse_duration(first.get("duration"))
        distance_meters = int(first.get("distanceMeters", 0))
        polyline = None
        polyline_data = first.get("polyline")
        if isinstance(polyline_data, dict):
            polyline = polyline_data.get("encodedPolyline")

        return RouteEstimate(
            origin=origin,
            destination=destination,
            distance_meters=distance_meters,
            duration_minutes=duration_minutes,
            travel_mode=self.travel_mode,
            provider="google",
            polyline=polyline,
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
        if not origins or not destinations:
            return []
        elements = await self.client.compute_route_matrix(
            origins,
            destinations,
            travel_mode=self.travel_mode,
            routing_preference=self.routing_preference,
        )
        results: list[RouteMatrixEntry] = []
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            origin_idx = elem.get("originIndex", 0)
            dest_idx = elem.get("destinationIndex", 0)
            condition = elem.get("condition", "ROUTE_EXISTS")
            status_info = elem.get("status")

            is_ok = condition == "ROUTE_EXISTS" and (
                status_info is None or status_info.get("code", 0) == 0
            )

            if is_ok:
                dist = int(elem.get("distanceMeters", 0)) if "distanceMeters" in elem else None
                dur = parse_duration(elem.get("duration")) if "duration" in elem else None
                results.append(
                    RouteMatrixEntry(
                        origin_index=origin_idx,
                        destination_index=dest_idx,
                        distance_meters=dist,
                        duration_minutes=dur,
                        route_exists=True,
                        provider="google",
                    )
                )
            else:
                results.append(
                    RouteMatrixEntry(
                        origin_index=origin_idx,
                        destination_index=dest_idx,
                        distance_meters=None,
                        duration_minutes=None,
                        route_exists=False,
                        provider="google",
                    )
                )
        return results
