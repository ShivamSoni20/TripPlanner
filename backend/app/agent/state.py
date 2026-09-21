from typing import TypedDict

from app.models.domain import TripConstraints, TripPlan
from app.services.trip_extraction import TripExtractionResult


class TripAgentState(TypedDict, total=False):
    request_id: str
    prompt: str
    extraction: TripExtractionResult
    constraints: TripConstraints
    missing: list[str]
    plan: TripPlan
    warnings: list[str]
    errors: list[str]
    revision_count: int
