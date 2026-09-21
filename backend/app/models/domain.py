from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Pace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class TripStatus(StrEnum):
    PLANNING = "planning"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"


class Money(BaseModel):
    amount: int = Field(ge=0, description="Minor-free whole currency units for MVP")
    currency: str = Field(default="INR", min_length=3, max_length=3)


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripPreferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    pace: Pace = Pace.BALANCED
    hotel_style: str | None = None
    transport_preferences: list[str] = Field(default_factory=list)


class TripConstraints(BaseModel):
    origin: str = Field(min_length=2)
    destination: str = Field(min_length=2)
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=20)
    budget: Money
    preferences: TripPreferences

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "TripConstraints":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class Trip(BaseModel):
    id: str
    constraints: TripConstraints
    status: TripStatus = TripStatus.PLANNING
    created_at: datetime
    updated_at: datetime
    data_mode: str = "demo"


class FlightOption(BaseModel):
    id: str
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int = Field(gt=0)
    stops: int = Field(ge=0)
    price: Money
    provider: str
    booking_url: HttpUrl | None = None
    retrieved_at: datetime


class HotelOption(BaseModel):
    id: str
    name: str
    location: GeoPoint
    rating: float | None = Field(default=None, ge=0, le=5)
    total_price: Money
    nightly_price: Money | None = None
    amenities: list[str] = Field(default_factory=list)
    provider: str
    booking_url: HttpUrl | None = None
    retrieved_at: datetime


class OpeningPeriod(BaseModel):
    open_day: int = Field(ge=0, le=6)
    open_hour: int = Field(ge=0, le=23)
    open_minute: int = Field(ge=0, le=59)
    close_day: int | None = Field(default=None, ge=0, le=6)
    close_hour: int | None = Field(default=None, ge=0, le=23)
    close_minute: int | None = Field(default=None, ge=0, le=59)


class OpeningHours(BaseModel):
    status: str = "UNKNOWN"
    periods: list[OpeningPeriod] = Field(default_factory=list)
    weekday_descriptions: list[str] = Field(default_factory=list)


class PlaceCandidate(BaseModel):
    place_id: str
    provider: str = "demo"
    provider_id: str | None = None
    name: str
    category: str
    types: list[str] = Field(default_factory=list)
    location: GeoPoint
    rating: float | None = Field(default=None, ge=0, le=5)
    rating_count: int | None = Field(default=None, ge=0)
    price: Money = Field(default_factory=lambda: Money(amount=0))
    maps_url: HttpUrl | None = None
    open_now: bool | None = None
    opening_hours: OpeningHours | None = None
    formatted_address: str | None = None
    price_level: str | None = None
    photo_reference: str | None = None
    retrieved_at: datetime | None = None
    suggested_visit_minutes: int = Field(default=60, gt=0)
    weather_suitability: float = Field(default=1, ge=0, le=1)
    interest_tags: list[str] = Field(default_factory=list)


class ItineraryItem(BaseModel):
    id: str
    title: str
    category: str
    start_at: datetime
    end_at: datetime
    location: GeoPoint
    place_id: str | None = None
    cost: Money = Field(default_factory=lambda: Money(amount=0))
    travel_from_previous_minutes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def times_are_ordered(self) -> "ItineraryItem":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class TimeWindow(BaseModel):
    start_at: datetime
    end_at: datetime
    origin: GeoPoint
    next_destination: GeoPoint | None = None
    duration_minutes: int = Field(gt=0)


class PlaceRecommendation(BaseModel):
    rank: str
    place: PlaceCandidate
    travel_to_minutes: int = Field(ge=0)
    visit_duration_minutes: int = Field(gt=0)
    travel_to_next_minutes: int = Field(ge=0)
    safety_buffer_minutes: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    reason: list[str]
    feasible: bool


class BudgetBreakdown(BaseModel):
    transport: int = Field(ge=0)
    hotel: int = Field(ge=0)
    food: int = Field(ge=0)
    activities: int = Field(ge=0)
    local_transport: int = Field(ge=0)
    total: int = Field(ge=0)
    remaining: int
    currency: str = "INR"
    within_budget: bool


class TripPlan(BaseModel):
    trip: Trip
    flights: list[FlightOption]
    hotels: list[HotelOption]
    places: list[PlaceCandidate]
    itinerary: list[ItineraryItem]
    budget: BudgetBreakdown
    warnings: list[str] = Field(default_factory=list)


class PlanningRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000)


class ProviderError(BaseModel):
    category: str
    provider: str
    message: str
    retryable: bool
    details: dict[str, Any] = Field(default_factory=dict)
