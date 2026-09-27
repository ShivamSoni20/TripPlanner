"""SerpAPI Google Flights adapter implementing FlightProvider contract."""

from datetime import UTC, datetime
from typing import Any
import httpx

from app.models.domain import AirportLocation, FlightOption, Money, TripConstraints
from app.providers.contracts import FlightProvider
from app.providers.errors import ProviderErrorCategory, ProviderException


class SerpApiFlightProvider(FlightProvider):
    """Fetches real-time flight data using SerpAPI's Google Flights Engine."""

    def __init__(self, *, api_key: str, timeout_seconds: float = 12):
        if not api_key:
            raise ValueError("SERPAPI_API_KEY is required when FLIGHTS_PROVIDER=serpapi")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def search(self, request: TripConstraints) -> list[FlightOption]:
        currency_code = request.budget.currency if request.budget else "USD"
        params: dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": request.origin,
            "arrival_id": request.destination,
            "outbound_date": request.start_date.strftime("%Y-%m-%d"),
            "currency": currency_code,
            "api_key": self.api_key,
            "hl": "en",
        }

        if request.end_date:
            params["return_date"] = request.end_date.strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.get("https://serpapi.com/search.json", params=params)
                if res.status_code != 200:
                    raise ProviderException(
                        ProviderErrorCategory.PROVIDER_DOWN,
                        f"SerpAPI returned HTTP {res.status_code}: {res.text[:200]}",
                        retryable=True,
                    )
                data = res.json()
        except httpx.RequestError as exc:
            raise ProviderException(
                ProviderErrorCategory.TIMEOUT,
                f"Network error querying SerpAPI: {exc}",
                retryable=True,
            ) from exc

        best_flights = data.get("best_flights", []) or data.get("other_flights", [])
        results: list[FlightOption] = []
        now = datetime.now(UTC)

        for idx, flight in enumerate(best_flights[:5]):
            flights_leg = flight.get("flights", [])
            if not flights_leg:
                continue

            first_segment = flights_leg[0]
            last_segment = flights_leg[-1]

            airline = first_segment.get("airline", "Unknown Airline")
            price_val = flight.get("price", 0)
            duration = flight.get("total_duration", 120)
            layovers = len(flights_leg) - 1

            dep_dt = datetime.combine(request.start_date, datetime.min.time()).replace(tzinfo=UTC)
            arr_dt = dep_dt

            dep_code = first_segment.get("departure_airport", {}).get("id", request.origin)
            arr_code = last_segment.get("arrival_airport", {}).get("id", request.destination)

            results.append(
                FlightOption(
                    id=f"serpapi-{idx+1}",
                    airline=airline,
                    departure_airport=dep_code,
                    arrival_airport=arr_code,
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    duration_minutes=int(duration),
                    stops=layovers,
                    price=Money(amount=float(price_val), currency=currency_code),
                    provider="serpapi",
                    booking_url="https://www.google.com/travel/flights",
                    retrieved_at=now,
                )
            )

        return results

    async def resolve_location(self, query: str) -> list[AirportLocation]:
        query_clean = query.strip().upper()
        return [
            AirportLocation(
                code=query_clean[:3],
                name=f"{query.title()} Airport",
                city_name=query.title(),
                country_code="IN",
            )
        ]
