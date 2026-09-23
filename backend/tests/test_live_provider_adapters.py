import httpx
import pytest

from app.models.domain import Money, Pace, TripConstraints, TripPreferences
from app.providers.amadeus import AmadeusClient, AmadeusFlightProvider
from app.providers.booking import BookingDemandClient, BookingHotelProvider
from app.providers.errors import ProviderErrorCategory, ProviderException


def constraints() -> TripConstraints:
    return TripConstraints(
        origin="Indore",
        destination="Goa",
        start_date="2026-11-12",
        end_date="2026-11-17",
        travelers=2,
        budget=Money(amount=30_000),
        preferences=TripPreferences(interests=["beaches"], pace=Pace.RELAXED),
    )


@pytest.mark.asyncio
async def test_amadeus_token_is_cached_and_offer_is_normalized() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/oauth2/token"):
            return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
        if request.url.path.endswith("/locations"):
            code = "IDR" if request.url.params["keyword"] == "Indore" else "GOI"
            return httpx.Response(
                200,
                json={"data": [{"iataCode": code, "name": f"{code} Airport"}]},
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "offer-1",
                        "price": {"grandTotal": "8400.00", "currency": "INR"},
                        "itineraries": [
                            {
                                "segments": [
                                    {
                                        "carrierCode": "6E",
                                        "departure": {
                                            "iataCode": "IDR",
                                            "at": "2026-11-12T07:20:00+05:30",
                                        },
                                        "arrival": {
                                            "iataCode": "GOI",
                                            "at": "2026-11-12T09:05:00+05:30",
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AmadeusFlightProvider(
        AmadeusClient(client_id="id", client_secret="secret", client=client)
    )
    options = await provider.search(constraints())
    await client.aclose()

    assert calls.count("/v1/security/oauth2/token") == 1
    assert options[0].id == "amadeus:offer-1"
    assert options[0].stops == 0
    assert options[0].booking_url is None


@pytest.mark.asyncio
async def test_amadeus_normalizes_rate_limit() -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(429, json={"errors": []}))
    )
    adapter = AmadeusClient(client_id="id", client_secret="secret", client=client, max_retries=0)
    with pytest.raises(ProviderException) as error:
        await adapter.token()
    await client.aclose()
    assert error.value.category == ProviderErrorCategory.RATE_LIMITED


@pytest.mark.asyncio
async def test_booking_search_uses_server_auth_and_validates_redirect() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/cities"):
            return httpx.Response(200, json={"data": [{"id": -2612321}]})
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": 99,
                        "name": "Safe Stay",
                        "location": {"latitude": 15.5, "longitude": 73.8},
                        "price": {"total": "9000"},
                        "currency": {"booker": "INR"},
                        "url": "https://www.booking.com/hotel/in/safe.html",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = BookingHotelProvider(
        BookingDemandClient(api_token="token", affiliate_id="123", client=client)
    )
    hotels = await provider.search(constraints())
    await client.aclose()

    assert requests[0].headers["Authorization"] == "Bearer token"
    assert requests[0].headers["X-Affiliate-Id"] == "123"
    assert hotels[0].booking_url is not None
    assert hotels[0].nightly_price and hotels[0].nightly_price.amount == 1800
