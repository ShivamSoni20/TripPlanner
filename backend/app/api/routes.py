import json
from collections.abc import AsyncIterator
from datetime import date

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.graph import build_planning_graph
from app.models.domain import Money, Pace, PlanningRequest, TripConstraints, TripPreferences
from app.providers.demo import DemoFlightProvider, DemoHotelProvider, DemoPlacesProvider
from app.services.planner import TripPlanner

router = APIRouter(prefix="/api/v1")


def get_planner() -> TripPlanner:
    return TripPlanner(DemoFlightProvider(), DemoHotelProvider(), DemoPlacesProvider())


def demo_constraints() -> TripConstraints:
    return TripConstraints(
        origin="Indore",
        destination="Goa",
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 17),
        travelers=2,
        budget=Money(amount=30_000),
        preferences=TripPreferences(
            interests=["beaches", "history", "nightlife"], pace=Pace.RELAXED
        ),
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "demo"}


@router.post("/trips/plan")
async def plan_trip(request: PlanningRequest):
    # Demo mode intentionally maps the canonical portfolio prompt to deterministic,
    # labeled provider results. Live mode will use validated model extraction.
    _ = request
    graph = build_planning_graph(get_planner())
    result = await graph.ainvoke(
        {"request_id": "demo-request", "constraints": demo_constraints(), "revision_count": 0}
    )
    if result.get("errors"):
        return {"errors": result["errors"]}
    return result["plan"]


async def planning_events() -> AsyncIterator[str]:
    events = [
        ("constraints.parsed", {"origin": "Indore", "destination": "Goa"}),
        ("flights.completed", {"count": 3, "provider": "demo"}),
        ("hotels.completed", {"count": 3, "provider": "demo"}),
        ("places.completed", {"count": 3, "provider": "demo"}),
        ("itinerary.optimizing", {}),
        ("budget.validated", {"limit": 30000}),
        ("plan.completed", {"data_mode": "demo"}),
    ]
    for event, data in events:
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/trips/plan/events")
async def stream_plan_events() -> StreamingResponse:
    return StreamingResponse(planning_events(), media_type="text/event-stream")
