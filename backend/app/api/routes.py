import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import Client

from app.agent.graph import build_planning_graph
from app.auth.dependencies import AuthenticatedUser, get_current_user, get_user_db_client
from app.core.config import get_settings
from app.model_gateway.errors import ModelGatewayError, StructuredOutputValidationError
from app.model_gateway.openrouter import OpenRouterModelGateway
from app.models.domain import (
    DataSourceStatus,
    ItineraryItem,
    Money,
    PlaceRecommendation,
    PlanningRequest,
    TimeWindow,
    TripPlan,
)
from app.providers.demo import (
    DemoFlightProvider,
    DemoHotelProvider,
    DemoPlacesProvider,
    DemoRoutesProvider,
    DemoWeatherProvider,
)
from app.providers.errors import ProviderErrorCategory, ProviderException
from app.providers.google import (
    GooglePlacesClient,
    GooglePlacesProvider,
    GoogleRoutesClient,
    GoogleRoutesProvider,
)
from app.providers.weatherapi import WeatherApiClient, WeatherApiProvider
from app.repositories.trips import InMemoryTripRepository, TripRepository
from app.services.explorer import ExplorerService
from app.services.free_time import detect_free_windows
from app.services.planner import TripPlanner
from app.services.schedule import validate_schedule
from app.services.trip_extraction import DemoTripExtractor, ModelTripExtractor, TripExtractor

router = APIRouter(prefix="/api/v1")


class ExploreRequest(BaseModel):
    interests: list[str] = Field(default_factory=list)
    window: TimeWindow
    excluded_place_ids: list[str] = Field(default_factory=list)
    remaining_budget: int | None = None


class PersistedExploreRequest(BaseModel):
    window: TimeWindow
    interests: list[str] = Field(default_factory=list)


class AddItineraryItemRequest(BaseModel):
    place_id: str
    window: TimeWindow
    expected_trip_version: int = Field(ge=1)
    interests: list[str] = Field(default_factory=list)


def get_weather_provider():
    settings = get_settings()
    if settings.weather_provider == "weatherapi":
        if not settings.weather_api_key:
            raise HTTPException(
                status_code=503,
                detail={
                    "category": "AUTH_FAILED",
                    "message": "WEATHER_API_KEY is required when WEATHER_PROVIDER=weatherapi",
                },
            )
        return WeatherApiProvider(
            WeatherApiClient(
                api_key=settings.weather_api_key,
                timeout_seconds=settings.request_timeout_seconds,
                max_retries=settings.provider_max_retries,
            )
        )
    return DemoWeatherProvider()


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

    if settings.routes_provider == "google":
        if not settings.google_maps_api_key:
            raise HTTPException(
                status_code=503,
                detail={
                    "category": "AUTH_FAILED",
                    "message": "GOOGLE_MAPS_API_KEY is required when ROUTES_PROVIDER=google",
                },
            )
        routes = GoogleRoutesProvider(
            GoogleRoutesClient(
                api_key=settings.google_maps_api_key,
                timeout_seconds=settings.request_timeout_seconds,
                max_retries=settings.provider_max_retries,
            ),
            travel_mode=settings.routes_travel_mode,
            routing_preference=settings.routes_routing_preference,
        )
    else:
        routes = DemoRoutesProvider()

    model_status = "live" if settings.travel_data_mode == "live" else "demo"
    data_mode = (
        "mixed"
        if (
            settings.travel_data_mode == "live"
            or settings.places_provider == "google"
            or settings.routes_provider == "google"
            or settings.weather_provider == "weatherapi"
        )
        else "demo"
    )

    sources = DataSourceStatus(
        model=model_status,
        flights="demo",
        hotels="demo",
        places=settings.places_provider,
        routes=settings.routes_provider,
        weather="unavailable",
    )

    weather = get_weather_provider()
    sources.weather = settings.weather_provider
    return TripPlanner(
        DemoFlightProvider(),
        DemoHotelProvider(),
        places,
        routes,
        weather,
        data_mode=data_mode,
        sources=sources,
    )


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


def get_repository(user: AuthenticatedUser, db_client: Client | None = None):
    settings = get_settings()
    if settings.app_env == "test":
        return InMemoryTripRepository(user_id=user.id)
    if db_client is None:
        raise HTTPException(
            status_code=503,
            detail={"category": "CONFIGURATION_ERROR", "message": "Supabase is not configured"},
        )
    return TripRepository(db=db_client, user_id=user.id)


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "providers": {
            "model": "live" if settings.travel_data_mode == "live" else "demo",
            "places": settings.places_provider,
            "routes": settings.routes_provider,
            "flights": "demo",
            "hotels": "demo",
            "weather": settings.weather_provider,
        },
    }


@router.post("/trips/plan")
async def plan_trip(
    request: PlanningRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
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

    plan: TripPlan = result["plan"]
    repo = get_repository(user, db_client)
    return await repo.create_plan(plan)


@router.get("/trips")
async def list_trips(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
    repo = get_repository(user, db_client)
    return await repo.list_trips()


@router.get("/trips/{trip_id}", response_model=TripPlan)
async def get_trip(
    trip_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
    repo = get_repository(user, db_client)
    return await repo.get_trip(trip_id)


@router.post("/trips/{trip_id}/explore", response_model=list[PlaceRecommendation])
async def explore_persisted_places(
    trip_id: str,
    request: PersistedExploreRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
    repo = get_repository(user, db_client)
    plan = await repo.get_trip(trip_id)
    window = next(
        (w for w in detect_free_windows(plan.itinerary) if w.start_at == request.window.start_at),
        None,
    )
    if window is None:
        raise HTTPException(
            status_code=422,
            detail={
                "category": "INVALID_WINDOW",
                "message": "This free window is no longer available",
            },
        )
    planner = get_planner()
    explorer = ExplorerService(planner.places, planner.routes, get_weather_provider())

    excluded = [item.place_id for item in plan.itinerary if item.place_id]
    interests = request.interests or plan.trip.constraints.preferences.interests

    try:
        return await explorer.explore(
            window=window,
            interests=interests,
            excluded_place_ids=excluded,
            remaining_budget=plan.budget.remaining,
        )
    except ProviderException as error:
        raise HTTPException(
            status_code=503,
            detail={"category": error.category.value, "message": str(error)},
        ) from error


@router.post("/trips/{trip_id}/itinerary-items", response_model=TripPlan)
async def add_itinerary_item(
    trip_id: str,
    request: AddItineraryItemRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
    repo = get_repository(user, db_client)
    plan = await repo.get_trip(trip_id)

    if plan.trip.version != request.expected_trip_version:
        raise HTTPException(
            status_code=409,
            detail={
                "category": "STALE_TRIP_STATE",
                "message": "The itinerary changed. TripPilot refreshed the latest plan.",
            },
        )

    window = next(
        (w for w in detect_free_windows(plan.itinerary) if w.start_at == request.window.start_at),
        None,
    )
    if window is None:
        raise HTTPException(
            status_code=422,
            detail={
                "category": "INVALID_WINDOW",
                "message": "This free window is no longer available",
            },
        )

    planner = get_planner()
    explorer = ExplorerService(planner.places, planner.routes, get_weather_provider())
    excluded = [item.place_id for item in plan.itinerary if item.place_id]
    interests = request.interests or plan.trip.constraints.preferences.interests

    recs = await explorer.explore(
        window=window,
        interests=interests,
        excluded_place_ids=excluded,
        remaining_budget=plan.budget.remaining,
    )

    matching_rec = next(
        (r for r in recs if r.place.place_id == request.place_id and r.feasible), None
    )
    if not matching_rec:
        raise HTTPException(
            status_code=422,
            detail={
                "category": "UNFEASIBLE_ADDITION",
                "message": "The place is no longer feasible for the selected free window",
            },
        )

    # Calculate timestamps
    from datetime import timedelta

    start_at = window.start_at + timedelta(minutes=matching_rec.travel_to_minutes)
    end_at = start_at + timedelta(minutes=matching_rec.visit_duration_minutes)

    item = ItineraryItem(
        id=str(uuid4()),
        title=matching_rec.place.name,
        category=matching_rec.place.category,
        start_at=start_at,
        end_at=end_at,
        location=matching_rec.place.location,
        place_id=matching_rec.place.place_id,
        cost=matching_rec.place.price or Money(amount=0),
        travel_from_previous_minutes=matching_rec.travel_to_minutes,
        source="user_added",
    )

    if validate_schedule([*plan.itinerary, item]):
        raise HTTPException(
            status_code=422,
            detail={
                "category": "INVALID_SCHEDULE",
                "message": "The activity conflicts with the itinerary",
            },
        )
    if item.cost.amount > plan.budget.remaining:
        raise HTTPException(
            status_code=422,
            detail={
                "category": "BUDGET_EXCEEDED",
                "message": "The activity exceeds the remaining budget",
            },
        )

    return await repo.add_itinerary_item(
        trip_id=trip_id,
        item=item,
        expected_version=request.expected_trip_version,
    )


@router.delete("/trips/{trip_id}/itinerary-items/{item_id}", response_model=TripPlan)
async def delete_itinerary_item(
    trip_id: str,
    item_id: str,
    expected_version: Annotated[int, Query(ge=1)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_client: Annotated[Client | None, Depends(get_user_db_client)] = None,
):
    repo = get_repository(user, db_client)
    return await repo.delete_itinerary_item(
        trip_id=trip_id,
        item_id=item_id,
        expected_version=expected_version,
    )


# Keep legacy stateless explore endpoint for backward compatibility
@router.post("/trips/explore", response_model=list[PlaceRecommendation])
async def explore_places(request: ExploreRequest):
    planner = get_planner()
    explorer = ExplorerService(planner.places, planner.routes, get_weather_provider())
    try:
        return await explorer.explore(
            window=request.window,
            interests=request.interests,
            excluded_place_ids=request.excluded_place_ids,
            remaining_budget=request.remaining_budget,
        )
    except ProviderException as error:
        raise HTTPException(
            status_code=503,
            detail={"category": error.category.value, "message": str(error)},
        ) from error


async def planning_events() -> AsyncIterator[str]:
    events = [
        ("constraints.parsed", {}),
        ("flights.completed", {}),
        ("hotels.completed", {}),
        ("places.completed", {}),
        ("routes.completed", {}),
        ("itinerary.optimizing", {}),
        ("budget.validated", {}),
        ("plan.completed", {}),
    ]
    for event, data in events:
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/trips/plan/events")
async def stream_plan_events() -> StreamingResponse:
    return StreamingResponse(planning_events(), media_type="text/event-stream")
