import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.graph import build_planning_graph
from app.core.config import get_settings
from app.model_gateway.errors import ModelGatewayError, StructuredOutputValidationError
from app.model_gateway.openrouter import OpenRouterModelGateway
from app.models.domain import DataSourceStatus, PlaceRecommendation, PlanningRequest, TimeWindow
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
from app.services.explorer import ExplorerService
from app.services.planner import TripPlanner
from app.services.trip_extraction import DemoTripExtractor, ModelTripExtractor, TripExtractor

router = APIRouter(prefix="/api/v1")


class ExploreRequest(BaseModel):
    interests: list[str] = Field(default_factory=list)
    window: TimeWindow
    excluded_place_ids: list[str] = Field(default_factory=list)
    remaining_budget: int | None = None


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

    # Places provider
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

    # Routes provider
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
        "live"
        if (settings.places_provider == "google" or settings.routes_provider == "google")
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
