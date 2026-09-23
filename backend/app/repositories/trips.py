import contextlib
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.models.domain import (
    BudgetBreakdown,
    DataSourceStatus,
    FlightOption,
    GeoPoint,
    HotelOption,
    ItineraryItem,
    Money,
    Pace,
    PlaceCandidate,
    Trip,
    TripConstraints,
    TripPlan,
    TripPreferences,
    TripStatus,
    UserSelection,
    WeatherForecast,
)
from app.services.free_time import detect_free_windows


def parse_datetime(val: str | datetime) -> datetime:
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(val.replace("Z", "+00:00"))


def parse_date(val: str | date) -> date:
    if isinstance(val, date):
        return val
    return date.fromisoformat(val)


class TripRepository:
    def __init__(self, db: Client, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def create_plan(self, plan: TripPlan) -> TripPlan:
        trip_id = plan.trip.id
        now_str = datetime.now(UTC).isoformat()
        root_created = False

        try:
            # 1. Insert trips row
            trip_data = {
                "id": trip_id,
                "user_id": str(self.user_id),
                "origin": plan.trip.constraints.origin,
                "destination": plan.trip.constraints.destination,
                "start_date": plan.trip.constraints.start_date.isoformat(),
                "end_date": plan.trip.constraints.end_date.isoformat(),
                "travellers": plan.trip.constraints.travelers,
                "budget": plan.trip.constraints.budget.amount,
                "currency": plan.trip.constraints.budget.currency,
                "status": plan.trip.status,
                "data_mode": plan.trip.data_mode,
                "version": plan.trip.version,
                "plan_metadata": {
                    "food": plan.budget.food,
                    "local_transport": plan.budget.local_transport,
                    "sources": plan.sources.model_dump(mode="json"),
                    "weather": plan.weather.model_dump(mode="json") if plan.weather else None,
                    "warnings": plan.warnings,
                },
                "created_at": now_str,
                "updated_at": now_str,
            }
            self.db.table("trips").insert(trip_data).execute()
            root_created = True

            # 2. Insert preferences
            prefs_data = {
                "trip_id": trip_id,
                "interests": plan.trip.constraints.preferences.interests,
                "pace": plan.trip.constraints.preferences.pace,
                "hotel_style": plan.trip.constraints.preferences.hotel_style,
                "transport_preferences": plan.trip.constraints.preferences.transport_preferences,
            }
            self.db.table("trip_preferences").insert(prefs_data).execute()

            # 3. Insert trip_options (flights, hotels, places)
            options = []
            for flight in plan.flights:
                options.append(
                    {
                        "trip_id": trip_id,
                        "type": "flight",
                        "provider": flight.provider,
                        "provider_id": flight.id,
                        "payload": flight.model_dump(mode="json"),
                        "booking_url": str(flight.booking_url) if flight.booking_url else None,
                        "retrieved_at": flight.retrieved_at.isoformat(),
                    }
                )
            for hotel in plan.hotels:
                options.append(
                    {
                        "trip_id": trip_id,
                        "type": "hotel",
                        "provider": hotel.provider,
                        "provider_id": hotel.id,
                        "payload": hotel.model_dump(mode="json"),
                        "booking_url": str(hotel.booking_url) if hotel.booking_url else None,
                        "retrieved_at": hotel.retrieved_at.isoformat(),
                    }
                )
            for place in plan.places:
                options.append(
                    {
                        "trip_id": trip_id,
                        "type": "place",
                        "provider": place.provider,
                        "provider_id": place.place_id,
                        "payload": place.model_dump(mode="json"),
                        "retrieved_at": place.retrieved_at.isoformat()
                        if place.retrieved_at
                        else now_str,
                    }
                )
            if options:
                self.db.table("trip_options").insert(options).execute()

            # 4. Insert itinerary_items
            items = []
            for item in plan.itinerary:
                items.append(
                    {
                        "id": item.id,
                        "trip_id": trip_id,
                        "provider_place_id": item.place_id,
                        "title": item.title,
                        "category": item.category,
                        "start_at": item.start_at.isoformat(),
                        "end_at": item.end_at.isoformat(),
                        "latitude": item.location.lat,
                        "longitude": item.location.lng,
                        "cost": item.cost.amount,
                        "currency": item.cost.currency,
                        "travel_from_previous_minutes": item.travel_from_previous_minutes,
                        "source": getattr(item, "source", "planned"),
                    }
                )
            if items:
                self.db.table("itinerary_items").insert(items).execute()

            return await self.get_trip(trip_id)
        except Exception as exc:
            # Cleanup trip root row if inserted
            if root_created:
                with contextlib.suppress(Exception):
                    self.db.table("trips").delete().eq("id", trip_id).execute()
            raise HTTPException(
                status_code=500,
                detail={"category": "PERSISTENCE_FAILED", "message": "Failed to save trip"},
            ) from exc

    async def get_trip(self, trip_id: str) -> TripPlan:
        # 1. Fetch trip
        trip_res = self.db.table("trips").select("*").eq("id", trip_id).execute()
        if not trip_res.data:
            raise HTTPException(
                status_code=404,
                detail={"category": "NOT_FOUND", "message": "Trip not found or access denied"},
            )
        trip_row = trip_res.data[0]

        # 2. Fetch preferences
        prefs_res = self.db.table("trip_preferences").select("*").eq("trip_id", trip_id).execute()
        prefs_row = prefs_res.data[0] if prefs_res.data else {}

        # 3. Fetch options
        options_res = self.db.table("trip_options").select("*").eq("trip_id", trip_id).execute()
        flights: list[FlightOption] = []
        hotels: list[HotelOption] = []
        places: list[PlaceCandidate] = []

        for opt in options_res.data:
            p = opt["payload"]
            if opt["type"] == "flight":
                flights.append(FlightOption.model_validate(p))
            elif opt["type"] == "hotel":
                hotels.append(HotelOption.model_validate(p))
            elif opt["type"] == "place":
                places.append(PlaceCandidate.model_validate(p))

        # 4. Fetch itinerary_items
        items_res = (
            self.db.table("itinerary_items")
            .select("*")
            .eq("trip_id", trip_id)
            .order("start_at")
            .execute()
        )
        itinerary: list[ItineraryItem] = []
        for row in items_res.data:
            itinerary.append(
                ItineraryItem(
                    id=row["id"],
                    title=row["title"],
                    category=row["category"],
                    start_at=parse_datetime(row["start_at"]),
                    end_at=parse_datetime(row["end_at"]),
                    location=GeoPoint(lat=row["latitude"], lng=row["longitude"]),
                    place_id=row.get("provider_place_id"),
                    cost=Money(amount=int(row["cost"]), currency=row.get("currency", "INR")),
                    travel_from_previous_minutes=row.get("travel_from_previous_minutes", 0),
                    source=row.get("source", "planned"),
                )
            )

        # Reconstruct domain Trip
        constraints = TripConstraints(
            origin=trip_row["origin"],
            destination=trip_row["destination"],
            start_date=parse_date(trip_row["start_date"]),
            end_date=parse_date(trip_row["end_date"]),
            travelers=trip_row["travellers"],
            budget=Money(amount=int(trip_row["budget"]), currency=trip_row.get("currency", "INR")),
            preferences=TripPreferences(
                interests=prefs_row.get("interests", []),
                pace=Pace(prefs_row.get("pace", "balanced")),
                hotel_style=prefs_row.get("hotel_style"),
                transport_preferences=prefs_row.get("transport_preferences", []),
            ),
        )

        trip = Trip(
            id=trip_row["id"],
            constraints=constraints,
            status=TripStatus(trip_row.get("status", "planning")),
            created_at=parse_datetime(trip_row["created_at"]),
            updated_at=parse_datetime(trip_row["updated_at"]),
            data_mode=trip_row.get("data_mode", "demo"),
            version=trip_row.get("version", 1),
        )

        # Recompute budget & free time windows
        total_budget = int(trip_row["budget"])
        activities_cost = sum(int(item.cost.amount) for item in itinerary)
        metadata = trip_row.get("plan_metadata") or {}
        selections_res = (
            self.db.table("user_selections").select("*").eq("trip_id", trip_id).execute()
        )
        options_by_uuid = {str(opt["id"]): opt for opt in options_res.data}
        selections: list[UserSelection] = []
        for selection in selections_res.data:
            option = options_by_uuid.get(str(selection.get("option_id")))
            if not option:
                continue
            payload = selection.get("payload") or {}
            price = payload.get("confirmed_price")
            selections.append(
                UserSelection(
                    option_id=option["provider_id"],
                    selection_type=selection["selection_type"],
                    confirmed_price=Money.model_validate(price) if price else None,
                    reference=payload.get("reference"),
                    confirmed_at=parse_datetime(selection["created_at"]),
                )
            )

        selection_by_type = {selection.selection_type: selection for selection in selections}
        selected_hotel_id = selection_by_type.get("confirmed_hotel") or selection_by_type.get(
            "selected_hotel"
        )
        selected_flight_id = selection_by_type.get("confirmed_flight") or selection_by_type.get(
            "selected_flight"
        )
        selected_hotel_id = selected_hotel_id.option_id if selected_hotel_id else None
        selected_flight_id = selected_flight_id.option_id if selected_flight_id else None
        selected_hotel = next(
            (hotel for hotel in hotels if hotel.id == selected_hotel_id),
            hotels[0] if hotels else None,
        )
        selected_flight = next(
            (flight for flight in flights if flight.id == selected_flight_id),
            flights[0] if flights else None,
        )
        confirmed_hotel = next(
            (
                selection
                for selection in selections
                if selection.selection_type == "confirmed_hotel"
            ),
            None,
        )
        confirmed_flight = next(
            (
                selection
                for selection in selections
                if selection.selection_type == "confirmed_flight"
            ),
            None,
        )
        hotel_cost = (
            confirmed_hotel.confirmed_price.amount
            if confirmed_hotel and confirmed_hotel.confirmed_price
            else selected_hotel.total_price.amount
            if selected_hotel
            else 0
        )
        flight_cost = (
            confirmed_flight.confirmed_price.amount
            if confirmed_flight and confirmed_flight.confirmed_price
            else selected_flight.price.amount
            if selected_flight
            else 0
        )
        days_count = (constraints.end_date - constraints.start_date).days
        food_cost = metadata.get("food", 540 * constraints.travelers * days_count)
        local_transport = metadata.get("local_transport", 350 * constraints.travelers * days_count)
        total_spent = activities_cost + hotel_cost + flight_cost + food_cost + local_transport
        remaining = total_budget - total_spent

        budget = BudgetBreakdown(
            transport=flight_cost,
            hotel=hotel_cost,
            food=food_cost,
            activities=activities_cost,
            local_transport=local_transport,
            total=total_spent,
            remaining=remaining,
            currency=trip_row.get("currency", "INR"),
            within_budget=remaining >= 0,
        )

        free_windows = detect_free_windows(itinerary)

        return TripPlan(
            trip=trip,
            flights=flights,
            hotels=hotels,
            places=places,
            itinerary=itinerary,
            budget=budget,
            sources=DataSourceStatus.model_validate(metadata.get("sources", {})),
            weather=WeatherForecast.model_validate(metadata["weather"])
            if metadata.get("weather")
            else None,
            free_time_windows=free_windows,
            warnings=metadata.get("warnings", []),
            selections=selections,
        )

    async def list_trips(self) -> list[dict]:
        res = (
            self.db.table("trips")
            .select("id, destination, origin, start_date, end_date, status, version, updated_at")
            .order("updated_at", desc=True)
            .execute()
        )
        return res.data or []

    async def add_itinerary_item(
        self,
        trip_id: str,
        item: ItineraryItem,
        expected_version: int,
    ) -> TripPlan:
        item_data = {
            "id": item.id,
            "trip_id": trip_id,
            "provider_place_id": item.place_id,
            "title": item.title,
            "category": item.category,
            "start_at": item.start_at.isoformat(),
            "end_at": item.end_at.isoformat(),
            "latitude": item.location.lat,
            "longitude": item.location.lng,
            "cost": item.cost.amount,
            "currency": item.cost.currency,
            "travel_from_previous_minutes": item.travel_from_previous_minutes,
            "source": "user_added",
        }
        try:
            self.db.rpc(
                "add_user_itinerary_item",
                {"p_trip_id": trip_id, "p_expected_version": expected_version, "p_item": item_data},
            ).execute()
        except Exception as exc:
            if "STALE_TRIP_STATE" in str(exc):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "category": "STALE_TRIP_STATE",
                        "message": "The itinerary changed. TripPilot refreshed the latest plan.",
                    },
                ) from exc
            raise HTTPException(
                status_code=500,
                detail={"category": "PERSISTENCE_FAILED", "message": "Could not add this activity"},
            ) from exc

        return await self.get_trip(trip_id)

    async def delete_itinerary_item(
        self,
        trip_id: str,
        item_id: str,
        expected_version: int,
    ) -> TripPlan:
        try:
            self.db.rpc(
                "remove_user_itinerary_item",
                {
                    "p_trip_id": trip_id,
                    "p_item_id": item_id,
                    "p_expected_version": expected_version,
                },
            ).execute()
        except Exception as exc:
            if "STALE_TRIP_STATE" in str(exc):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "category": "STALE_TRIP_STATE",
                        "message": "The itinerary changed. TripPilot refreshed the latest plan.",
                    },
                ) from exc
            if "ITEM_NOT_REMOVABLE" in str(exc):
                raise HTTPException(
                    status_code=404,
                    detail={"category": "NOT_FOUND", "message": "User-added activity not found"},
                ) from exc
            raise HTTPException(
                status_code=500,
                detail={
                    "category": "PERSISTENCE_FAILED",
                    "message": "Could not remove this activity",
                },
            ) from exc

        return await self.get_trip(trip_id)

    async def set_selection(
        self,
        trip_id: str,
        option_id: str,
        selection_type: str,
        expected_version: int,
        payload: dict,
    ) -> TripPlan:
        try:
            self.db.rpc(
                "set_trip_selection",
                {
                    "p_trip_id": trip_id,
                    "p_provider_option_id": option_id,
                    "p_selection_type": selection_type,
                    "p_expected_version": expected_version,
                    "p_payload": payload,
                },
            ).execute()
        except Exception as error:
            message = str(error)
            if "STALE_TRIP_STATE" in message:
                raise HTTPException(
                    status_code=409, detail={"category": "STALE_TRIP_STATE"}
                ) from error
            if "OPTION_NOT_FOUND" in message:
                raise HTTPException(status_code=404, detail={"category": "NOT_FOUND"}) from error
            raise HTTPException(
                status_code=500, detail={"category": "PERSISTENCE_FAILED"}
            ) from error
        return await self.get_trip(trip_id)


class InMemoryTripRepository:
    """In-memory repository for unit testing FastAPI endpoints without a live Supabase server."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        if not hasattr(InMemoryTripRepository, "_storage"):
            InMemoryTripRepository._storage = {}

    @property
    def storage(self) -> dict[str, tuple[UUID, TripPlan]]:
        return InMemoryTripRepository._storage

    async def create_plan(self, plan: TripPlan) -> TripPlan:
        self.storage[plan.trip.id] = (self.user_id, plan.model_copy(deep=True))
        return plan

    async def get_trip(self, trip_id: str) -> TripPlan:
        if trip_id not in self.storage:
            raise HTTPException(
                status_code=404, detail={"category": "NOT_FOUND", "message": "Trip not found"}
            )
        owner_id, plan = self.storage[trip_id]
        if owner_id != self.user_id:
            raise HTTPException(
                status_code=404,
                detail={"category": "NOT_FOUND", "message": "Trip not found or access denied"},
            )
        return plan.model_copy(deep=True)

    async def list_trips(self) -> list[dict]:
        user_trips = []
        for _trip_id, (owner_id, plan) in self.storage.items():
            if owner_id == self.user_id:
                user_trips.append(
                    {
                        "id": plan.trip.id,
                        "destination": plan.trip.constraints.destination,
                        "origin": plan.trip.constraints.origin,
                        "start_date": plan.trip.constraints.start_date.isoformat(),
                        "end_date": plan.trip.constraints.end_date.isoformat(),
                        "status": plan.trip.status,
                        "version": plan.trip.version,
                        "updated_at": plan.trip.updated_at.isoformat(),
                    }
                )
        return user_trips

    async def add_itinerary_item(
        self,
        trip_id: str,
        item: ItineraryItem,
        expected_version: int,
    ) -> TripPlan:
        plan = await self.get_trip(trip_id)
        if plan.trip.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "category": "STALE_TRIP_STATE",
                    "message": "The itinerary changed. TripPilot refreshed the latest plan.",
                },
            )
        new_plan = plan.model_copy(deep=True)
        new_plan.itinerary.append(item)
        new_plan.budget.activities += item.cost.amount
        new_plan.budget.total += item.cost.amount
        new_plan.budget.remaining -= item.cost.amount
        new_plan.budget.within_budget = new_plan.budget.remaining >= 0
        new_plan.free_time_windows = detect_free_windows(new_plan.itinerary)
        new_plan.trip.version += 1
        new_plan.trip.updated_at = datetime.now(UTC)
        self.storage[trip_id] = (self.user_id, new_plan)
        return new_plan

    async def delete_itinerary_item(
        self,
        trip_id: str,
        item_id: str,
        expected_version: int,
    ) -> TripPlan:
        plan = await self.get_trip(trip_id)
        if plan.trip.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "category": "STALE_TRIP_STATE",
                    "message": "The itinerary changed. TripPilot refreshed the latest plan.",
                },
            )
        new_plan = plan.model_copy(deep=True)
        removable = next(
            (i for i in new_plan.itinerary if i.id == item_id and i.source == "user_added"),
            None,
        )
        if removable is None:
            raise HTTPException(
                status_code=404,
                detail={"category": "NOT_FOUND", "message": "User-added activity not found"},
            )
        new_plan.itinerary = [
            i
            for i in new_plan.itinerary
            if i.id != item_id or getattr(i, "source", "planned") != "user_added"
        ]
        new_plan.budget.activities -= removable.cost.amount
        new_plan.budget.total -= removable.cost.amount
        new_plan.budget.remaining += removable.cost.amount
        new_plan.budget.within_budget = new_plan.budget.remaining >= 0
        new_plan.free_time_windows = detect_free_windows(new_plan.itinerary)
        new_plan.trip.version += 1
        new_plan.trip.updated_at = datetime.now(UTC)
        self.storage[trip_id] = (self.user_id, new_plan)
        return new_plan

    async def set_selection(
        self,
        trip_id: str,
        option_id: str,
        selection_type: str,
        expected_version: int,
        payload: dict,
    ) -> TripPlan:
        plan = await self.get_trip(trip_id)
        if plan.trip.version != expected_version:
            raise HTTPException(status_code=409, detail={"category": "STALE_TRIP_STATE"})
        options = plan.flights if selection_type.endswith("flight") else plan.hotels
        if not any(option.id == option_id for option in options):
            raise HTTPException(status_code=404, detail={"category": "NOT_FOUND"})
        next_plan = plan.model_copy(deep=True)
        next_plan.selections = [
            item for item in next_plan.selections if item.selection_type != selection_type
        ]
        next_plan.selections.append(
            UserSelection(
                option_id=option_id,
                selection_type=selection_type,
                confirmed_price=Money.model_validate(payload["confirmed_price"])
                if payload.get("confirmed_price")
                else None,
                reference=payload.get("reference"),
                confirmed_at=datetime.now(UTC),
            )
        )
        flight = next(
            (
                selection
                for selection in next_plan.selections
                if selection.selection_type == "confirmed_flight"
            ),
            next(
                (
                    selection
                    for selection in next_plan.selections
                    if selection.selection_type == "selected_flight"
                ),
                None,
            ),
        )
        hotel = next(
            (
                selection
                for selection in next_plan.selections
                if selection.selection_type == "confirmed_hotel"
            ),
            next(
                (
                    selection
                    for selection in next_plan.selections
                    if selection.selection_type == "selected_hotel"
                ),
                None,
            ),
        )
        selected_flight = next(
            (item for item in next_plan.flights if flight and item.id == flight.option_id),
            None,
        )
        selected_hotel = next(
            (item for item in next_plan.hotels if hotel and item.id == hotel.option_id),
            None,
        )
        next_plan.budget.transport = (
            flight.confirmed_price.amount
            if flight and flight.confirmed_price
            else selected_flight.price.amount
            if selected_flight
            else next_plan.budget.transport
        )
        next_plan.budget.hotel = (
            hotel.confirmed_price.amount
            if hotel and hotel.confirmed_price
            else selected_hotel.total_price.amount
            if selected_hotel
            else next_plan.budget.hotel
        )
        next_plan.budget.total = (
            next_plan.budget.transport
            + next_plan.budget.hotel
            + next_plan.budget.food
            + next_plan.budget.local_transport
            + next_plan.budget.activities
        )
        next_plan.budget.remaining = (
            next_plan.trip.constraints.budget.amount - next_plan.budget.total
        )
        next_plan.budget.within_budget = next_plan.budget.remaining >= 0
        next_plan.trip.version += 1
        next_plan.trip.updated_at = datetime.now(UTC)
        self.storage[trip_id] = (self.user_id, next_plan)
        return next_plan
