import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.graph import build_planning_graph
from app.core.config import get_settings
from app.model_gateway.errors import ModelGatewayError, StructuredOutputValidationError
from app.model_gateway.openrouter import OpenRouterModelGateway
from app.models.domain import PlanningRequest
from app.providers.demo import DemoFlightProvider, DemoHotelProvider, DemoPlacesProvider
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.providers.google import GooglePlacesClient, GooglePlacesProvider
from app.services.planner import TripPlanner
from app.services.trip_extraction import DemoTripExtractor, ModelTripExtractor, TripExtractor

router = APIRouter(prefix="/api/v1")


def get_planner() -> TripPlanner:
    settings = get_settings()
    if settings.places_provider == "google":
        if not settings.google_maps_api_key:
            raise HTTPException(
                status_code=503,
                detail={
                    "category": "AUTH_FAILED",
                    "message": "GOOGLE_MAPS_API_KEY is required when PLACES_PROVIDER=google",
                },
            )
        places = GooglePlacesProvider(
            GooglePlacesClient(
                api_key=settings.google_maps_api_key,
                timeout_seconds=settings.request_timeout_seconds,
                max_retries=settings.provider_max_retries,
            )
        )
    else:
        places = DemoPlacesProvider()
    data_mode = "live" if settings.places_provider == "google" else "demo"
    return TripPlanner(DemoFlightProvider(), DemoHotelProvider(), places, data_mode=data_mode)


def get_extractor() -> TripExtractor:
    settings = get_settings()
    if settings.travel_data_mode == "demo":
        return DemoTripExtractor()
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "category": "AUTH_FAILED",
                "message": "OPENROUTER_API_KEY is required in live mode",
            },
        )
    gateway = OpenRouterModelGateway(
        api_key=settings.openrouter_api_key,
        model=settings.trip_agent_model,
        timeout_seconds=settings.request_timeout_seconds,
    )
    return ModelTripExtractor(gateway)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "demo"}


@router.post("/trips/plan")
async def plan_trip(request: PlanningRequest):
    graph = build_planning_graph(get_planner(), get_extractor())
    try:
        result = await graph.ainvoke(
            {"request_id": str(uuid4()), "prompt": request.prompt, "revision_count": 0}
        )
    except StructuredOutputValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "category": "INVALID_MODEL_OUTPUT",
                "message": "The trip request could not be structured after one retry",
                "validation_errors": error.errors,
            },
        ) from error
    except ModelGatewayError as error:
        raise HTTPException(
            status_code=503,
            detail={"category": "PROVIDER_DOWN", "message": str(error)},
        ) from error
    except ProviderException as error:
        status = 503
        if error.category == ProviderErrorCategory.INVALID_REQUEST:
            status = 422
        elif error.category == ProviderErrorCategory.AUTH_FAILED:
            status = 503
        elif error.category == ProviderErrorCategory.RATE_LIMITED:
            status = 429
        raise HTTPException(
            status_code=status,
            detail={"category": error.category.value, "message": str(error)},
        ) from error
    if result.get("missing"):
        extraction = result["extraction"]
        return {
            "status": "needs_input",
            "missing": extraction.missing,
            "question": extraction.question,
        }
    if result.get("errors"):
        raise HTTPException(status_code=422, detail={"errors": result["errors"]})
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
