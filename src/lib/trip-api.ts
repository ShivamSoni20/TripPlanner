import type {
  BudgetBreakdown,
  DataSourceStatus,
  ExploreRequest,
  FlightOption,
  HotelOption,
  ItineraryItem,
  PlaceCandidate,
  PlaceRecommendation,
  Trip,
} from "@/domain/trip";

export interface TripPlanResponse {
  trip: Trip;
  flights: FlightOption[];
  hotels: HotelOption[];
  places: PlaceCandidate[];
  itinerary: ItineraryItem[];
  budget: BudgetBreakdown;
  sources?: DataSourceStatus;
  warnings: string[];
  free_time_windows?: Array<{ start_at: string; end_at: string; origin: PlaceCandidate["location"]; next_destination?: PlaceCandidate["location"]; duration_minutes: number }>;
  freeTimeWindows?: import("@/domain/trip").TimeWindow[];
}

export interface NeedsInputResponse {
  status: "needs_input";
  missing: string[];
  question: string;
}

export type PlanningResponse = TripPlanResponse | NeedsInputResponse;

type ApiTripPlanResponse = {
  trip: {
    id: string;
    constraints: {
      origin: string;
      destination: string;
      start_date: string;
      end_date: string;
      travelers: number;
      budget: { amount: number; currency: string };
      preferences: {
        interests: string[];
        pace: "relaxed" | "balanced" | "packed";
        hotel_style: string | null;
        transport_preferences: string[];
      };
    };
    status: Trip["status"];
    created_at: string;
    updated_at: string;
    data_mode: "demo" | "live";
  };
  flights: FlightOption[];
  hotels: HotelOption[];
  places: PlaceCandidate[];
  itinerary: ItineraryItem[];
  budget: {
    transport: number;
    hotel: number;
    food: number;
    activities: number;
    local_transport: number;
    total: number;
    remaining: number;
    currency: string;
    within_budget: boolean;
  };
  sources?: DataSourceStatus;
  warnings: string[];
};

function normalizePlan(plan: ApiTripPlanResponse): TripPlanResponse {
  const { constraints } = plan.trip;
  return {
    trip: {
      id: plan.trip.id,
      status: plan.trip.status,
      createdAt: plan.trip.created_at,
      updatedAt: plan.trip.updated_at,
      dataMode: plan.trip.data_mode,
      constraints: {
        origin: constraints.origin,
        destination: constraints.destination,
        startDate: constraints.start_date,
        endDate: constraints.end_date,
        travelers: constraints.travelers,
        budget: constraints.budget,
        preferences: {
          interests: constraints.preferences.interests,
          pace: constraints.preferences.pace,
          transportPreferences: constraints.preferences.transport_preferences,
          ...(constraints.preferences.hotel_style
            ? { hotelStyle: constraints.preferences.hotel_style }
            : {}),
        },
      },
    },
    flights: plan.flights || [],
    hotels: plan.hotels || [],
    places: plan.places || [],
    itinerary: plan.itinerary || [],
    budget: {
      transport: plan.budget.transport,
      hotel: plan.budget.hotel,
      food: plan.budget.food,
      activities: plan.budget.activities,
      localTransport: plan.budget.local_transport,
      total: plan.budget.total,
      remaining: plan.budget.remaining,
      currency: plan.budget.currency,
      withinBudget: plan.budget.within_budget,
    },
    sources: plan.sources,
    warnings: plan.warnings || [],
    freeTimeWindows: (plan.free_time_windows ?? []).map((window) => ({ startAt: window.start_at, endAt: window.end_at, origin: window.origin, ...(window.next_destination ? { nextDestination: window.next_destination } : {}), durationMinutes: window.duration_minutes })),
  };
}
const API_URL = import.meta.env["VITE_TRIPPILOT_API_URL"] ?? "http://localhost:8000";

function apiUrl(path: string): string {
  return `${API_URL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

export async function createTripPlan(
  prompt: string,
  signal?: AbortSignal,
): Promise<PlanningResponse> {
  const requestInit: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    ...(signal ? { signal } : {}),
  };
  const response = await fetch(apiUrl("/api/v1/trips/plan"), requestInit);
  if (!response.ok) {
    throw new Error(`Trip planning failed (${response.status})`);
  }
  const payload: unknown = await response.json();
  if (
    typeof payload === "object" &&
    payload !== null &&
    "status" in payload &&
    payload.status === "needs_input" &&
    "missing" in payload &&
    Array.isArray(payload.missing) &&
    "question" in payload &&
    typeof payload.question === "string"
  ) {
    return {
      status: "needs_input",
      missing: payload.missing.filter((item): item is string => typeof item === "string"),
      question: payload.question,
    };
  }
  return normalizePlan(payload as ApiTripPlanResponse);
}

export async function exploreNearbyPlaces(
  request: ExploreRequest,
  signal?: AbortSignal,
): Promise<PlaceRecommendation[]> {
  const requestInit: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interests: request.interests,
      window: {
        start_at: request.window.startAt,
        end_at: request.window.endAt,
        origin: request.window.origin,
        next_destination: request.window.nextDestination,
        duration_minutes: request.window.durationMinutes,
      },
      excluded_place_ids: request.excludedPlaceIds || [],
      remaining_budget: request.remainingBudget,
    }),
    ...(signal ? { signal } : {}),
  };
  const response = await fetch(apiUrl("/api/v1/trips/explore"), requestInit);
  if (!response.ok) {
    throw new Error(`Explore request failed (${response.status})`);
  }
  const payload: unknown = await response.json();
  if (!Array.isArray(payload)) {
    return [];
  }
  return payload.map((item) => {
    const raw = item as Record<string, unknown>;
    const place = raw["place"] as Record<string, unknown>;
    return {
      rank: String(raw["rank"]),
      place: {
        placeId: String(place["place_id"]), provider: String(place["provider"]), name: String(place["name"]), category: String(place["category"]), types: Array.isArray(place["types"]) ? place["types"].filter((v): v is string => typeof v === "string") : [], location: place["location"] as PlaceCandidate["location"], rating: typeof place["rating"] === "number" ? place["rating"] : undefined, price: place["price"] as PlaceCandidate["price"], mapsUrl: typeof place["maps_url"] === "string" ? place["maps_url"] : undefined, suggestedVisitMinutes: Number(place["suggested_visit_minutes"] ?? 60), weatherSuitability: Number(place["weather_suitability"] ?? 1), interestTags: Array.isArray(place["interest_tags"]) ? place["interest_tags"].filter((v): v is string => typeof v === "string") : [],
      },
      travelToMinutes: Number(raw["travel_to_minutes"]), visitDurationMinutes: Number(raw["visit_duration_minutes"]), travelToNextMinutes: Number(raw["travel_to_next_minutes"]), safetyBufferMinutes: Number(raw["safety_buffer_minutes"]), totalRequiredMinutes: Number(raw["total_required_minutes"]), remainingBufferMinutes: Number(raw["remaining_buffer_minutes"]), score: Number(raw["score"]), reason: Array.isArray(raw["reason"]) ? raw["reason"].filter((v): v is string => typeof v === "string") : [], feasible: raw["feasible"] === true,
    };
  });
}
