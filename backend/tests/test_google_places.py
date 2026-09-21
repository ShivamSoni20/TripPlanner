import json

import httpx
import pytest

from app.models.domain import GeoPoint
from app.providers.demo import DemoPlacesProvider
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.providers.google.places import (
    SEARCH_FIELD_MASK,
    GooglePlacesClient,
    GooglePlacesProvider,
)


def google_place(**overrides):
    place = {
        "id": "ChIJfortaguada",
        "displayName": {"text": "Fort Aguada", "languageCode": "en"},
        "location": {"latitude": 15.4921, "longitude": 73.7737},
        "primaryType": "historical_landmark",
        "types": ["historical_landmark", "tourist_attraction"],
        "rating": 4.5,
        "userRatingCount": 34210,
        "formattedAddress": "Fort Aguada Road, Goa",
        "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
        "googleMapsUri": "https://www.google.com/maps/place/?q=place_id:ChIJfortaguada",
        "currentOpeningHours": {
            "openNow": True,
            "weekdayDescriptions": ["Monday: 9:00 AM – 6:00 PM"],
            "periods": [
                {
                    "open": {"day": 1, "hour": 9, "minute": 0},
                    "close": {"day": 1, "hour": 18, "minute": 0},
                }
            ],
        },
    }
    place.update(overrides)
    return place


@pytest.mark.asyncio
async def test_nearby_request_is_bounded_and_uses_explicit_mask() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"places": [google_place()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", client=http_client)
        rows = await client.search_nearby(
            GeoPoint(lat=15.5, lng=73.77),
            included_types=["historical_landmark"],
            radius_meters=40_000,
            max_results=100,
        )

    assert len(rows) == 1
    assert captured["url"].endswith("/v1/places:searchNearby")
    assert captured["headers"]["x-goog-api-key"] == "secret"
    assert captured["headers"]["x-goog-fieldmask"] == SEARCH_FIELD_MASK
    assert "*" not in SEARCH_FIELD_MASK
    assert captured["body"]["maxResultCount"] == 20
    assert captured["body"]["locationRestriction"]["circle"]["radius"] == 25_000.0


@pytest.mark.asyncio
async def test_text_search_and_details_use_new_places_endpoints() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=google_place())
        return httpx.Response(200, json={"places": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", client=http_client)
        await client.search_text(
            "historical landmarks in Panjim", included_type="historical_landmark"
        )
        await client.get_place_details("ChIJfortaguada")

    assert requests[0].method == "POST"
    assert requests[0].url.path.endswith("/places:searchText")
    assert requests[1].method == "GET"
    assert requests[1].url.path.endswith("/places/ChIJfortaguada")


def test_normalization_preserves_provider_identity_and_hours() -> None:
    candidate = GooglePlacesProvider._normalize(google_place())

    assert candidate is not None
    assert candidate.provider == "google"
    assert candidate.provider_id == "ChIJfortaguada"
    assert candidate.category == "historical_landmark"
    assert candidate.opening_hours is not None
    assert candidate.opening_hours.status == "OPEN"
    assert candidate.rating == 4.5


@pytest.mark.parametrize(
    "broken",
    [
        {"id": None},
        {"displayName": {}},
        {"location": {"latitude": 999, "longitude": 73}},
    ],
)
def test_malformed_essential_place_is_skipped(broken) -> None:
    assert GooglePlacesProvider._normalize(google_place(**broken)) is None


def test_optional_place_fields_remain_unknown() -> None:
    candidate = GooglePlacesProvider._normalize(
        google_place(
            rating=None,
            currentOpeningHours=None,
            priceLevel=None,
            googleMapsUri=None,
        )
    )
    assert candidate is not None
    assert candidate.rating is None
    assert candidate.open_now is None
    assert candidate.opening_hours is None
    assert candidate.maps_url is None


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
async def test_google_errors_are_normalized(status, category) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status, json={"error": {"message": "provider detail"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", max_retries=0, client=http_client)
        with pytest.raises(ProviderException) as captured:
            await client.search_text("beaches in Goa")
    assert captured.value.category == category


@pytest.mark.asyncio
async def test_empty_result_is_not_an_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(200, json={"places": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", client=http_client)
        assert await client.search_text("unknown attraction") == []


@pytest.mark.asyncio
async def test_invalid_json_is_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(200, content=b"not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", client=http_client)
        with pytest.raises(ProviderException) as captured:
            await client.search_text("beaches in Goa")
    assert captured.value.category == ProviderErrorCategory.INVALID_RESPONSE


@pytest.mark.asyncio
async def test_timeout_is_bounded_and_normalized() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GooglePlacesClient(api_key="secret", max_retries=1, client=http_client)
        with pytest.raises(ProviderException) as captured:
            await client.search_text("beaches in Goa")
    assert attempts == 2
    assert captured.value.category == ProviderErrorCategory.TIMEOUT


@pytest.mark.asyncio
async def test_demo_provider_supports_nearby_and_details_contract() -> None:
    provider = DemoPlacesProvider()
    nearby = await provider.search_nearby(GeoPoint(lat=15.5, lng=73.77), ["history"], max_results=2)
    assert nearby
    assert all(place.provider == "demo" for place in nearby)
    details = await provider.get_details(nearby[0].place_id)
    assert details is not None
    assert details.provider_id == nearby[0].provider_id
