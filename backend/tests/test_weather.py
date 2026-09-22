from datetime import UTC, date, datetime

import httpx
import pytest

from app.models.domain import (
    DailyWeather,
    GeoPoint,
    Money,
    PlaceCandidate,
    WeatherAvailability,
    WeatherFit,
    WeatherForecast,
)
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.providers.weatherapi.weather import WeatherApiClient, WeatherApiProvider
from app.services.weather import evaluate_activity_weather


class NoCallClient:
    async def forecast(self, **kwargs):
        raise AssertionError("outside-horizon requests must not call WeatherAPI")


@pytest.mark.asyncio
async def test_far_future_forecast_is_not_fabricated() -> None:
    provider = WeatherApiProvider(NoCallClient(), today=date(2026, 9, 22))
    result = await provider.get_forecast(
        location=GeoPoint(lat=15.5, lng=73.8),
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 17),
    )
    assert result.availability == WeatherAvailability.NOT_AVAILABLE_YET
    assert result.days == []


@pytest.mark.asyncio
async def test_weather_request_and_normalization() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "location": {"tz_id": "Asia/Kolkata"},
                "forecast": {
                    "forecastday": [
                        {
                            "date": "2026-09-24",
                            "day": {
                                "mintemp_c": 24,
                                "maxtemp_c": 30,
                                "condition": {"text": "Cloudy", "code": 1006},
                                "daily_chance_of_rain": 60,
                                "totalprecip_mm": 2.5,
                                "maxwind_kph": 20,
                            },
                            "hour": [
                                {
                                    "time_epoch": 1790229600,
                                    "temp_c": 27,
                                    "feelslike_c": 29,
                                    "condition": {"text": "Rain", "code": 1183},
                                    "chance_of_rain": 80,
                                    "precip_mm": 1.2,
                                    "wind_kph": 14,
                                }
                            ],
                        }
                    ]
                },
                "alerts": {
                    "alert": [
                        {
                            "headline": "Heavy rain",
                            "severity": "Moderate",
                            "areas": "Goa",
                            "effective_epoch": 1790229600,
                            "expires_epoch": 1790233200,
                        }
                    ]
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = WeatherApiClient(api_key="test-key", client=http)
        provider = WeatherApiProvider(client, today=date(2026, 9, 23))
        forecast = await provider.get_forecast(
            location=GeoPoint(lat=15.5, lng=73.8),
            start_date=date(2026, 9, 24),
            end_date=date(2026, 9, 24),
        )
        await client.forecast(location=GeoPoint(lat=15.5, lng=73.8), days=30)
    assert seen[0].url.path.endswith("/forecast.json")
    assert seen[0].url.params["q"] == "15.5,73.8"
    assert seen[0].url.params["alerts"] == "yes"
    assert seen[0].url.params["aqi"] == "no"
    assert seen[1].url.params["days"] == "14"
    assert forecast.timezone == "Asia/Kolkata"
    assert forecast.days[0].hours[0].timestamp.tzinfo == UTC
    assert forecast.days[0].hours[0].precipitation_mm == 1.2
    assert forecast.alerts[0].headline == "Heavy rain"
    assert forecast.alerts[0].severity == "Moderate"
    assert forecast.alerts[0].effective_at.tzinfo == UTC


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,category",
    [
        (400, ProviderErrorCategory.INVALID_REQUEST),
        (401, ProviderErrorCategory.AUTH_FAILED),
        (403, ProviderErrorCategory.AUTH_FAILED),
        (429, ProviderErrorCategory.RATE_LIMITED),
        (500, ProviderErrorCategory.PROVIDER_DOWN),
    ],
)
async def test_weather_http_errors(status: int, category: ProviderErrorCategory) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status))
    ) as http:
        with pytest.raises(ProviderException) as raised:
            await WeatherApiClient(api_key="test-key", client=http, max_retries=0).forecast(
                location=GeoPoint(lat=15.5, lng=73.8), days=1
            )
    assert raised.value.category == category


@pytest.mark.asyncio
async def test_weather_timeout_and_invalid_payload() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    for handler, category in [
        (timeout, ProviderErrorCategory.TIMEOUT),
        (lambda _: httpx.Response(200, text="not json"), ProviderErrorCategory.INVALID_RESPONSE),
        (
            lambda _: httpx.Response(200, json={"forecast": {"forecastday": [{"date": "broken"}]}}),
            ProviderErrorCategory.INVALID_RESPONSE,
        ),
    ]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            provider = WeatherApiProvider(
                WeatherApiClient(api_key="test-key", client=http, max_retries=0),
                today=date(2026, 9, 23),
            )
            with pytest.raises(ProviderException) as raised:
                await provider.get_forecast(
                    location=GeoPoint(lat=15.5, lng=73.8),
                    start_date=date(2026, 9, 24),
                    end_date=date(2026, 9, 24),
                )
            assert raised.value.category == category


@pytest.mark.asyncio
async def test_weather_horizon_boundary() -> None:
    class StubClient:
        async def forecast(self, **kwargs):
            return {"forecast": {"forecastday": []}}

    provider = WeatherApiProvider(StubClient(), today=date(2026, 9, 23))
    near = await provider.get_forecast(
        location=GeoPoint(lat=15.5, lng=73.8),
        start_date=date(2026, 10, 6),
        end_date=date(2026, 10, 6),
    )
    far = await provider.get_forecast(
        location=GeoPoint(lat=15.5, lng=73.8),
        start_date=date(2026, 10, 7),
        end_date=date(2026, 10, 7),
    )
    assert near.availability == WeatherAvailability.AVAILABLE
    assert far.availability == WeatherAvailability.NOT_AVAILABLE_YET


@pytest.mark.parametrize(
    "category,rain,expected",
    [
        ("beach", 10, WeatherFit.GOOD),
        ("beach", 80, WeatherFit.UNSUITABLE),
        ("historical_landmark", 50, WeatherFit.CAUTION),
        ("museum", 80, WeatherFit.GOOD),
    ],
)
def test_weather_suitability(category: str, rain: int, expected: WeatherFit) -> None:
    place = PlaceCandidate(
        place_id="p",
        name="Place",
        category=category,
        location=GeoPoint(lat=15.5, lng=73.8),
        price=Money(amount=0),
    )
    forecast = WeatherForecast(
        availability=WeatherAvailability.AVAILABLE,
        location=place.location,
        provider="test",
        days=[DailyWeather(date=date(2026, 9, 24), condition_text="Cloudy", chance_of_rain=rain)],
    )
    assert (
        evaluate_activity_weather(place, datetime(2026, 9, 24, tzinfo=UTC), forecast).fit
        == expected
    )
    assert (
        evaluate_activity_weather(
            place,
            datetime(2026, 9, 24, tzinfo=UTC),
            forecast.model_copy(update={"availability": WeatherAvailability.UNAVAILABLE}),
        ).fit
        == WeatherFit.UNKNOWN
    )
