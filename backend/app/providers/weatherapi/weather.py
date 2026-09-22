import asyncio
from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.models.domain import (
    DailyWeather,
    GeoPoint,
    HourlyWeather,
    WeatherAlert,
    WeatherAvailability,
    WeatherForecast,
)
from app.providers.errors import ProviderErrorCategory, ProviderException


class WeatherApiClient:
    base_url = "https://api.weatherapi.com/v1"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 12,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("WEATHER_API_KEY is required when WEATHER_PROVIDER=weatherapi")
        self.api_key, self.timeout_seconds, self.max_retries, self._client = (
            api_key,
            timeout_seconds,
            max_retries,
            client,
        )

    async def forecast(self, *, location: GeoPoint, days: int) -> dict[str, Any]:
        params = {
            "key": self.api_key,
            "q": f"{location.lat},{location.lng}",
            "days": min(max(days, 1), 14),
            "alerts": "yes",
            "aqi": "no",
        }
        for attempt in range(self.max_retries + 1):
            try:
                if self._client:
                    response = await self._client.get(
                        f"{self.base_url}/forecast.json", params=params
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.get(f"{self.base_url}/forecast.json", params=params)
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    continue
                raise ProviderException(
                    ProviderErrorCategory.TIMEOUT, "Weather forecast timed out", retryable=True
                ) from error
            if response.status_code in {401, 403}:
                raise ProviderException(
                    ProviderErrorCategory.AUTH_FAILED,
                    "Weather authentication failed",
                    retryable=False,
                )
            if response.status_code == 400:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Weather request rejected",
                    retryable=False,
                )
            if 400 <= response.status_code < 500 and response.status_code != 429:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Weather request rejected",
                    retryable=False,
                )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.05 * 2**attempt)
                    continue
                raise ProviderException(
                    ProviderErrorCategory.RATE_LIMITED
                    if response.status_code == 429
                    else ProviderErrorCategory.PROVIDER_DOWN,
                    "Weather service unavailable",
                    retryable=True,
                )
            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Weather service returned invalid JSON",
                    retryable=False,
                ) from error
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("forecast"), dict)
                or not isinstance(payload["forecast"].get("forecastday"), list)
            ):
                raise ProviderException(
                    ProviderErrorCategory.INVALID_RESPONSE,
                    "Weather service returned an unexpected response",
                    retryable=False,
                )
            return payload
        raise AssertionError("bounded retry loop exited unexpectedly")


class WeatherApiProvider:
    def __init__(self, client: WeatherApiClient, *, today: date | None = None) -> None:
        self.client, self.today = client, today

    async def get_forecast(
        self, *, location: GeoPoint, start_date: date, end_date: date
    ) -> WeatherForecast:
        today = self.today or date.today()
        if start_date < today or (start_date - today).days >= 14:
            return WeatherForecast(
                availability=WeatherAvailability.NOT_AVAILABLE_YET,
                location=location,
                provider="weatherapi",
            )
        payload = await self.client.forecast(
            location=location, days=min(14, (end_date - today).days + 1)
        )
        try:
            return self._normalize(payload, location)
        except (KeyError, TypeError, ValueError, ValidationError, AttributeError) as error:
            raise ProviderException(
                ProviderErrorCategory.INVALID_RESPONSE,
                "Weather service returned an unexpected response",
                retryable=False,
            ) from error

    def _normalize(self, payload: dict[str, Any], location: GeoPoint) -> WeatherForecast:
        days = []
        for row in payload["forecast"]["forecastday"]:
            day = row.get("day", {})
            condition = day.get("condition", {})
            hours = [
                HourlyWeather(
                    timestamp=datetime.fromtimestamp(h["time_epoch"], UTC),
                    temperature_c=h.get("temp_c"),
                    feels_like_c=h.get("feelslike_c"),
                    condition_text=h.get("condition", {}).get("text", "Unknown"),
                    condition_code=h.get("condition", {}).get("code"),
                    chance_of_rain=h.get("chance_of_rain"),
                    precipitation_mm=h.get("precip_mm"),
                    wind_kph=h.get("wind_kph"),
                )
                for h in row.get("hour", [])
                if isinstance(h, dict) and "time_epoch" in h
            ]
            days.append(
                DailyWeather(
                    date=date.fromisoformat(row["date"]),
                    min_temperature_c=day.get("mintemp_c"),
                    max_temperature_c=day.get("maxtemp_c"),
                    condition_text=condition.get("text", "Unknown"),
                    condition_code=condition.get("code"),
                    chance_of_rain=day.get("daily_chance_of_rain"),
                    total_precipitation_mm=day.get("totalprecip_mm"),
                    max_wind_kph=day.get("maxwind_kph"),
                    hours=hours,
                )
            )
        alerts = [
            WeatherAlert(
                headline=a.get("headline", "Weather alert"),
                severity=a.get("severity"),
                areas=a.get("areas"),
                effective_at=datetime.fromtimestamp(a["effective_epoch"], UTC)
                if a.get("effective_epoch")
                else None,
                expires_at=datetime.fromtimestamp(a["expires_epoch"], UTC)
                if a.get("expires_epoch")
                else None,
            )
            for a in payload.get("alerts", {}).get("alert", [])
            if isinstance(a, dict)
        ]
        return WeatherForecast(
            availability=WeatherAvailability.AVAILABLE,
            location=location,
            timezone=payload.get("location", {}).get("tz_id"),
            days=days,
            alerts=alerts,
            provider="weatherapi",
        )
