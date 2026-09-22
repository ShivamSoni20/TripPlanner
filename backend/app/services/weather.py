from datetime import datetime

from app.models.domain import (
    PlaceCandidate,
    WeatherAssessment,
    WeatherAvailability,
    WeatherFit,
    WeatherForecast,
)

OUTDOOR_TYPES = {
    "beach",
    "park",
    "national_park",
    "historical_landmark",
    "history",
    "tourist_attraction",
    "viewpoint",
}
INDOOR_TYPES = {"museum", "art_gallery", "cafe", "restaurant", "shopping_mall"}


def evaluate_activity_weather(
    place: PlaceCandidate, start_at: datetime, forecast: WeatherForecast
) -> WeatherAssessment:
    if forecast.availability != WeatherAvailability.AVAILABLE:
        return WeatherAssessment(
            fit=WeatherFit.UNKNOWN, score=0.5, reason=["Forecast unavailable for this date"]
        )
    day = next((item for item in forecast.days if item.date == start_at.date()), None)
    if day is None:
        return WeatherAssessment(
            fit=WeatherFit.UNKNOWN, score=0.5, reason=["Forecast unavailable for this date"]
        )
    types = {place.category.lower(), *[item.lower() for item in place.types]}
    outdoor = bool(types & OUTDOOR_TYPES)
    indoor = bool(types & INDOOR_TYPES)
    rain = day.chance_of_rain or 0
    if outdoor and rain >= 70:
        return WeatherAssessment(
            fit=WeatherFit.UNSUITABLE,
            score=0,
            reason=[f"{rain}% chance of rain for an outdoor activity"],
        )
    if outdoor and rain >= 40:
        return WeatherAssessment(
            fit=WeatherFit.CAUTION, score=0.35, reason=[f"{rain}% chance of rain"]
        )
    if indoor and rain >= 70:
        return WeatherAssessment(
            fit=WeatherFit.GOOD, score=0.9, reason=["Indoor-friendly during rain"]
        )
    return WeatherAssessment(fit=WeatherFit.GOOD, score=0.8, reason=[day.condition_text])
