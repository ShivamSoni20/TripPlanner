from typing import TypedDict

from app.models.domain import TripConstraints, TripPlan


class TripAgentState(TypedDict, total=False):
    request_id: str
    constraints: TripConstraints
    plan: TripPlan
    warnings: list[str]
    errors: list[str]
    revision_count: int
