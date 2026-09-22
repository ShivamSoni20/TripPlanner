import json

import httpx
import pytest

from app.models.domain import GeoPoint
from app.providers.demo import DemoRoutesProvider
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.providers.google.routes import (
    ROUTE_FIELD_MASK,
    GoogleRoutesClient,
    GoogleRoutesProvider,
    parse_duration,
)


def test_duration_parsing_ceil_conservatively() -> None:
    assert parse_duration("160s") == 3
    assert parse_duration("60s") == 1
    assert parse_duration("0.5s") == 1
    assert parse_duration("3600s") == 60
    with pytest.raises(ValueError):
        parse_duration(None)
    with pytest.raises(ValueError):
        parse_duration("not-a-duration")


@pytest.mark.asyncio
async def test_compute_route_request_is_bounded_and_uses_field_mask() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"routes": [{"duration": "60s", "distanceMeters": 5000}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GoogleRoutesClient(api_key="secret", client=http_client)
        provider = GoogleRoutesProvider(client)
        estimate = await provider.compute_route(
            GeoPoint(lat=15.5, lng=73.77), GeoPoint(lat=15.6, lng=73.8)
        )

    assert estimate.duration_minutes == 1
    assert estimate.distance_meters == 5000
    assert captured["url"].endswith("/v2:computeRoutes")
    assert captured["headers"]["x-goog-api-key"] == "secret"
    assert captured["headers"]["x-goog-fieldmask"] == ROUTE_FIELD_MASK
    assert "*" not in ROUTE_FIELD_MASK


@pytest.mark.asyncio
async def test_compute_matrix_handles_route_exists_and_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            200,
            json=[
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "condition": "ROUTE_EXISTS",
                    "duration": "120s",
                    "distanceMeters": 3000,
                },
                {
                    "originIndex": 0,
                    "destinationIndex": 1,
                    "condition": "ROUTE_NOT_FOUND",
                },
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GoogleRoutesClient(api_key="secret", client=http_client)
        provider = GoogleRoutesProvider(client)
        entries = await provider.compute_matrix(
            [GeoPoint(lat=15.5, lng=73.77)],
            [GeoPoint(lat=15.6, lng=73.8), GeoPoint(lat=90, lng=90)],
        )

    assert len(entries) == 2
    assert entries[0].route_exists is True
    assert entries[0].duration_minutes == 2
    assert entries[1].route_exists is False
    assert entries[1].duration_minutes is None


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (400, ProviderErrorCategory.INVALID_REQUEST),
        (401, ProviderErrorCategory.AUTH_FAILED),
        (403, ProviderErrorCategory.AUTH_FAILED),
        (429, ProviderErrorCategory.RATE_LIMITED),
        (500, ProviderErrorCategory.PROVIDER_DOWN),
    ],
)
@pytest.mark.asyncio
async def test_google_routes_errors_are_normalized(status, category) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status, json={"error": {"message": "provider error"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GoogleRoutesClient(api_key="secret", max_retries=0, client=http_client)
        with pytest.raises(ProviderException) as captured:
            await client.compute_route(GeoPoint(lat=15, lng=73), GeoPoint(lat=16, lng=74))
    assert captured.value.category == category


@pytest.mark.asyncio
async def test_demo_routes_provider_satisfies_contract() -> None:
    provider = DemoRoutesProvider()
    estimate = await provider.compute_route(
        GeoPoint(lat=15.5, lng=73.77), GeoPoint(lat=15.6, lng=73.8)
    )
    assert estimate.duration_minutes > 0
    assert estimate.provider == "demo"
    matrix = await provider.compute_matrix(
        [GeoPoint(lat=15.5, lng=73.77)], [GeoPoint(lat=15.6, lng=73.8)]
    )
    assert len(matrix) == 1
    assert matrix[0].route_exists is True
