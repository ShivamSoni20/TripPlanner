from datetime import date

import pytest

from app.models.domain import GeoPoint, WeatherAvailability
from app.providers.weatherapi.weather import WeatherApiProvider


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
