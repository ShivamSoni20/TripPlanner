import type { BudgetBreakdown, Trip } from "@/domain/trip";

export interface TripPlanResponse {
  trip: Trip;
  flights: unknown[];
  hotels: unknown[];
  places: unknown[];
  itinerary: unknown[];
  budget: BudgetBreakdown;
  warnings: string[];
}

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
  flights: unknown[];
  hotels: unknown[];
  places: unknown[];
  itinerary: unknown[];
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
          hotelStyle: constraints.preferences.hotel_style ?? undefined,
          transportPreferences: constraints.preferences.transport_preferences,
        },
      },
    },
    flights: plan.flights,
    hotels: plan.hotels,
    places: plan.places,
    itinerary: plan.itinerary,
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
    warnings: plan.warnings,
  };
}

const API_URL = import.meta.env["VITE_TRIPPILOT_API_URL"] ?? "http://localhost:8000";

export async function createTripPlan(
  prompt: string,
  signal?: AbortSignal,
): Promise<TripPlanResponse> {
  const requestInit: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    ...(signal ? { signal } : {}),
  };
  const response = await fetch(`${API_URL}/api/v1/trips/plan`, requestInit);
  if (!response.ok) {
    throw new Error(`Trip planning failed (${response.status})`);
  }
  return normalizePlan((await response.json()) as ApiTripPlanResponse);
}
