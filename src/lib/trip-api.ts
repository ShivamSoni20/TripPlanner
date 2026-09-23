import {
  BudgetBreakdown,
  DataSourceStatus,
  ExploreRequest,
  FlightOption,
  GeoPoint,
  HotelOption,
  ItineraryItem,
  Money,
  OpeningHours,
  OpeningPeriod,
  PlaceCandidate,
  PlaceRecommendation,
  TimeWindow,
  Trip,
  TripPlan,
  UserSelection,
  WeatherAssessment,
  WeatherForecast,
} from "../domain/trip";
import { supabase } from "./supabase";

export interface MissingInformationResponse {
  status: "needs_input";
  missing: string[];
  question: string;
}

export type PlanningResponse = TripPlan | MissingInformationResponse;
export type TripPlanResponse = TripPlan;

export interface TripSummary {
  id: string;
  destination: string;
  origin: string;
  startDate: string;
  endDate: string;
  status: string;
  version: number;
  updatedAt: string;
}

interface ApiMoney {
  amount: number;
  currency: string;
}
interface ApiGeo {
  lat: number;
  lng: number;
}
interface ApiPeriod {
  open_day: number;
  open_hour: number;
  open_minute: number;
  close_day?: number | null;
  close_hour?: number | null;
  close_minute?: number | null;
}
interface ApiHours {
  status: string;
  periods: ApiPeriod[];
  weekday_descriptions: string[];
}
interface ApiPlace {
  place_id: string;
  provider: string;
  provider_id?: string | null;
  name: string;
  category: string;
  types: string[];
  location: ApiGeo;
  rating?: number | null;
  rating_count?: number | null;
  price: ApiMoney;
  maps_url?: string | null;
  open_now?: boolean | null;
  opening_hours?: ApiHours | null;
  formatted_address?: string | null;
  price_level?: string | null;
  photo_reference?: string | null;
  retrieved_at?: string | null;
  suggested_visit_minutes: number;
  weather_suitability: number;
  interest_tags: string[];
}

interface ApiItineraryItem {
  id: string;
  title: string;
  category: string;
  start_at: string;
  end_at: string;
  location: ApiGeo;
  place_id?: string | null;
  cost: ApiMoney;
  travel_from_previous_minutes: number;
  source?: string;
}

interface ApiTimeWindow {
  start_at: string;
  end_at: string;
  origin: ApiGeo;
  next_destination?: ApiGeo | null;
  duration_minutes: number;
}

interface ApiWeatherAssessment {
  fit: "good" | "caution" | "unsuitable" | "unknown";
  score: number;
  reason: string[];
}

interface ApiRecommendation {
  rank: string;
  place: ApiPlace;
  travel_to_minutes: number;
  visit_duration_minutes: number;
  travel_to_next_minutes: number;
  safety_buffer_minutes: number;
  total_required_minutes: number;
  remaining_buffer_minutes: number;
  score: number;
  reason: string[];
  feasible: boolean;
  weather: ApiWeatherAssessment;
}

interface ApiWeatherAlert {
  headline: string;
  severity?: string | null;
  areas?: string | null;
  effective_at?: string | null;
  expires_at?: string | null;
}

interface ApiHourlyWeather {
  timestamp: string;
  temperature_c?: number | null;
  feels_like_c?: number | null;
  condition_text: string;
  condition_code?: number | null;
  chance_of_rain?: number | null;
  precipitation_mm?: number | null;
  wind_kph?: number | null;
}

interface ApiDailyWeather {
  date: string;
  min_temperature_c?: number | null;
  max_temperature_c?: number | null;
  condition_text: string;
  condition_code?: number | null;
  chance_of_rain?: number | null;
  total_precipitation_mm?: number | null;
  max_wind_kph?: number | null;
  hours: ApiHourlyWeather[];
}

interface ApiWeather {
  availability: "available" | "not_available_yet" | "unavailable";
  location: ApiGeo;
  timezone?: string | null;
  provider: string;
  retrieved_at: string;
  alerts: ApiWeatherAlert[];
  days: ApiDailyWeather[];
}

interface ApiTripPlanResponse {
  trip: {
    id: string;
    status: "planning" | "ready" | "active" | "completed";
    created_at: string;
    updated_at: string;
    data_mode: string;
    version?: number;
    constraints: {
      origin: string;
      destination: string;
      start_date: string;
      end_date: string;
      travelers: number;
      budget: ApiMoney;
      preferences: {
        interests: string[];
        pace: "relaxed" | "balanced" | "packed";
        hotel_style?: string | null;
        transport_preferences: string[];
      };
    };
  };
  flights: Array<{
    id: string;
    airline: string;
    departure_airport: string;
    arrival_airport: string;
    departure_time: string;
    arrival_time: string;
    duration_minutes: number;
    stops: number;
    price: ApiMoney;
    provider: string;
    booking_url?: string | null;
    retrieved_at: string;
  }>;
  hotels: Array<{
    id: string;
    name: string;
    location: ApiGeo;
    rating?: number | null;
    total_price: ApiMoney;
    nightly_price?: ApiMoney | null;
    amenities: string[];
    provider: string;
    booking_url?: string | null;
    retrieved_at: string;
  }>;
  places: ApiPlace[];
  itinerary: ApiItineraryItem[];
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
  sources: {
    model: string;
    flights: string;
    hotels: string;
    places: string;
    routes: string;
    weather: string;
  };
  weather?: ApiWeather | null;
  free_time_windows?: ApiTimeWindow[];
  warnings: string[];
  selections?: Array<{
    option_id: string;
    selection_type: UserSelection["selectionType"];
    confirmed_price?: ApiMoney | null;
    reference?: string | null;
    confirmed_at?: string | null;
  }>;
}

function money(v: ApiMoney): Money {
  return { amount: v.amount, currency: v.currency };
}

function geo(v: ApiGeo): GeoPoint {
  return { lat: v.lat, lng: v.lng };
}

function normalizePlaceCandidate(v: ApiPlace): PlaceCandidate {
  return {
    placeId: v.place_id,
    provider: v.provider,
    ...(v.provider_id ? { providerId: v.provider_id } : {}),
    name: v.name,
    category: v.category,
    types: v.types,
    location: geo(v.location),
    ...(v.rating != null ? { rating: v.rating } : {}),
    ...(v.rating_count != null ? { ratingCount: v.rating_count } : {}),
    price: money(v.price),
    ...(v.maps_url ? { mapsUrl: v.maps_url } : {}),
    ...(v.open_now != null ? { openNow: v.open_now } : {}),
    ...(v.opening_hours
      ? {
          openingHours: {
            status: v.opening_hours.status,
            weekdayDescriptions: v.opening_hours.weekday_descriptions,
            periods: v.opening_hours.periods.map((p) => ({
              openDay: p.open_day,
              openHour: p.open_hour,
              openMinute: p.open_minute,
              ...(p.close_day != null ? { closeDay: p.close_day } : {}),
              ...(p.close_hour != null ? { closeHour: p.close_hour } : {}),
              ...(p.close_minute != null ? { closeMinute: p.close_minute } : {}),
            })),
          },
        }
      : {}),
    ...(v.formatted_address ? { formattedAddress: v.formatted_address } : {}),
    ...(v.price_level ? { priceLevel: v.price_level } : {}),
    ...(v.photo_reference ? { photoReference: v.photo_reference } : {}),
    ...(v.retrieved_at ? { retrievedAt: v.retrieved_at } : {}),
    suggestedVisitMinutes: v.suggested_visit_minutes,
    weatherSuitability: v.weather_suitability,
    interestTags: v.interest_tags,
  };
}

function normalizeWeatherAssessment(value: ApiWeatherAssessment): WeatherAssessment {
  return { fit: value.fit, score: value.score, reason: [...value.reason] };
}

function normalizeDataSourceStatus(value: {
  model: string;
  flights: string;
  hotels: string;
  places: string;
  routes: string;
  weather: string;
}): DataSourceStatus {
  return {
    model: value.model,
    flights: value.flights,
    hotels: value.hotels,
    places: value.places,
    routes: value.routes,
    weather: value.weather,
  };
}

function normalizePlaceRecommendation(v: ApiRecommendation): PlaceRecommendation {
  return {
    rank: v.rank,
    place: normalizePlaceCandidate(v.place),
    travelToMinutes: v.travel_to_minutes,
    visitDurationMinutes: v.visit_duration_minutes,
    travelToNextMinutes: v.travel_to_next_minutes,
    safetyBufferMinutes: v.safety_buffer_minutes,
    totalRequiredMinutes: v.total_required_minutes,
    remainingBufferMinutes: v.remaining_buffer_minutes,
    score: v.score,
    reason: v.reason,
    feasible: v.feasible,
    weather: normalizeWeatherAssessment(v.weather),
  };
}

function normalizeWeather(v?: ApiWeather | null): WeatherForecast | undefined {
  return v
    ? {
        availability: v.availability,
        location: geo(v.location),
        ...(v.timezone ? { timezone: v.timezone } : {}),
        provider: v.provider,
        retrievedAt: v.retrieved_at,
        alerts: v.alerts.map((a) => ({
          headline: a.headline,
          ...(a.severity ? { severity: a.severity } : {}),
          ...(a.areas ? { areas: a.areas } : {}),
          ...(a.effective_at ? { effectiveAt: a.effective_at } : {}),
          ...(a.expires_at ? { expiresAt: a.expires_at } : {}),
        })),
        days: v.days.map((d) => ({
          date: d.date,
          conditionText: d.condition_text,
          ...(d.condition_code != null ? { conditionCode: d.condition_code } : {}),
          ...(d.min_temperature_c != null ? { minTemperatureC: d.min_temperature_c } : {}),
          ...(d.max_temperature_c != null ? { maxTemperatureC: d.max_temperature_c } : {}),
          ...(d.chance_of_rain != null ? { chanceOfRain: d.chance_of_rain } : {}),
          ...(d.total_precipitation_mm != null
            ? { totalPrecipitationMm: d.total_precipitation_mm }
            : {}),
          ...(d.max_wind_kph != null ? { maxWindKph: d.max_wind_kph } : {}),
          hours: d.hours.map((h) => ({
            timestamp: h.timestamp,
            conditionText: h.condition_text,
            ...(h.temperature_c != null ? { temperatureC: h.temperature_c } : {}),
            ...(h.feels_like_c != null ? { feelsLikeC: h.feels_like_c } : {}),
            ...(h.condition_code != null ? { conditionCode: h.condition_code } : {}),
            ...(h.chance_of_rain != null ? { chanceOfRain: h.chance_of_rain } : {}),
            ...(h.precipitation_mm != null ? { precipitationMm: h.precipitation_mm } : {}),
            ...(h.wind_kph != null ? { windKph: h.wind_kph } : {}),
          })),
        })),
      }
    : undefined;
}

function normalizePlan(p: ApiTripPlanResponse): TripPlan {
  const c = p.trip.constraints;
  const w = normalizeWeather(p.weather);
  return {
    trip: {
      id: p.trip.id,
      status: p.trip.status,
      createdAt: p.trip.created_at,
      updatedAt: p.trip.updated_at,
      dataMode: p.trip.data_mode,
      version: p.trip.version ?? 1,
      constraints: {
        origin: c.origin,
        destination: c.destination,
        startDate: c.start_date,
        endDate: c.end_date,
        travelers: c.travelers,
        budget: money(c.budget),
        preferences: {
          interests: c.preferences.interests,
          pace: c.preferences.pace,
          transportPreferences: c.preferences.transport_preferences,
          ...(c.preferences.hotel_style ? { hotelStyle: c.preferences.hotel_style } : {}),
        },
      },
    },
    flights: p.flights.map((f) => ({
      id: f.id,
      airline: f.airline,
      departureAirport: f.departure_airport,
      arrivalAirport: f.arrival_airport,
      departureTime: f.departure_time,
      arrivalTime: f.arrival_time,
      durationMinutes: f.duration_minutes,
      stops: f.stops,
      price: money(f.price),
      provider: f.provider,
      ...(f.booking_url ? { bookingUrl: f.booking_url } : {}),
      retrievedAt: f.retrieved_at,
    })),
    hotels: p.hotels.map((h) => ({
      id: h.id,
      name: h.name,
      location: geo(h.location),
      ...(h.rating != null ? { rating: h.rating } : {}),
      totalPrice: money(h.total_price),
      ...(h.nightly_price ? { nightlyPrice: money(h.nightly_price) } : {}),
      amenities: h.amenities,
      provider: h.provider,
      ...(h.booking_url ? { bookingUrl: h.booking_url } : {}),
      retrievedAt: h.retrieved_at,
    })),
    places: p.places.map(normalizePlaceCandidate),
    itinerary: p.itinerary.map((i) => ({
      id: i.id,
      title: i.title,
      category: i.category,
      startAt: i.start_at,
      endAt: i.end_at,
      location: geo(i.location),
      ...(i.place_id ? { placeId: i.place_id } : {}),
      cost: money(i.cost),
      travelFromPreviousMinutes: i.travel_from_previous_minutes,
      ...(i.source ? { source: i.source as "planned" | "user_added" | "replan" } : {}),
    })),
    budget: {
      transport: p.budget.transport,
      hotel: p.budget.hotel,
      food: p.budget.food,
      activities: p.budget.activities,
      localTransport: p.budget.local_transport,
      total: p.budget.total,
      remaining: p.budget.remaining,
      currency: p.budget.currency,
      withinBudget: p.budget.within_budget,
    },
    sources: normalizeDataSourceStatus(p.sources),
    warnings: p.warnings,
    selections: (p.selections ?? []).map((selection) => ({
      optionId: selection.option_id,
      selectionType: selection.selection_type,
      ...(selection.confirmed_price ? { confirmedPrice: money(selection.confirmed_price) } : {}),
      ...(selection.reference ? { reference: selection.reference } : {}),
      ...(selection.confirmed_at ? { confirmedAt: selection.confirmed_at } : {}),
    })),
    freeTimeWindows: (p.free_time_windows ?? []).map((x) => ({
      startAt: x.start_at,
      endAt: x.end_at,
      origin: geo(x.origin),
      ...(x.next_destination ? { nextDestination: geo(x.next_destination) } : {}),
      durationMinutes: x.duration_minutes,
    })),
    ...(w ? { weather: w } : {}),
  };
}

const API_URL = import.meta.env["VITE_TRIPPILOT_API_URL"] ?? "http://localhost:8000";
const apiUrl = (path: string) => `${API_URL.replace(/\/$/, "")}${path}`;

async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

async function authorizedFetch(url: string, init?: RequestInit): Promise<Response> {
  let token = await getAccessToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let r = await fetch(url, { ...init, headers });

  if (r.status === 401 && supabase) {
    // Attempt one session refresh if 401
    const { data } = await supabase.auth.refreshSession();
    if (data.session?.access_token) {
      token = data.session.access_token;
      headers.set("Authorization", `Bearer ${token}`);
      r = await fetch(url, { ...init, headers });
    }
    if (r.status === 401) {
      await supabase.auth.signOut();
    }
  }

  return r;
}

export async function createTripPlan(
  prompt: string,
  signal?: AbortSignal,
): Promise<PlanningResponse> {
  const r = await authorizedFetch(apiUrl("/api/v1/trips/plan"), {
    method: "POST",
    body: JSON.stringify({ prompt }),
    ...(signal ? { signal } : {}),
  });

  if (r.status === 401) {
    throw new Error("UNAUTHORIZED");
  }

  if (!r.ok) {
    const errPayload = await r.json().catch(() => null);
    throw new Error(errPayload?.detail?.message || "Trip planning failed");
  }

  const payload: unknown = await r.json();
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
      missing: payload.missing.filter((x): x is string => typeof x === "string"),
      question: payload.question,
    };
  }

  return normalizePlan(payload as ApiTripPlanResponse);
}

export async function listTrips(): Promise<TripSummary[]> {
  const r = await authorizedFetch(apiUrl("/api/v1/trips"), { method: "GET" });
  if (r.status === 401) throw new Error("UNAUTHORIZED");
  if (!r.ok) throw new Error("Failed to list trips");
  const data: Array<{
    id: string;
    destination: string;
    origin: string;
    start_date: string;
    end_date: string;
    status: string;
    version: number;
    updated_at: string;
  }> = await r.json();

  return data.map((t) => ({
    id: t.id,
    destination: t.destination,
    origin: t.origin,
    startDate: t.start_date,
    endDate: t.end_date,
    status: t.status,
    version: t.version,
    updatedAt: t.updated_at,
  }));
}

export async function getTrip(tripId: string): Promise<TripPlan> {
  const r = await authorizedFetch(apiUrl(`/api/v1/trips/${encodeURIComponent(tripId)}`), {
    method: "GET",
  });
  if (r.status === 401) throw new Error("UNAUTHORIZED");
  if (r.status === 404) throw new Error("Trip not found or access denied");
  if (!r.ok) throw new Error("Failed to load trip");
  const payload: ApiTripPlanResponse = await r.json();
  return normalizePlan(payload);
}

export async function exploreTrip(
  tripId: string,
  window: TimeWindow,
  interests: string[] = [],
  signal?: AbortSignal,
): Promise<PlaceRecommendation[]> {
  const r = await authorizedFetch(apiUrl(`/api/v1/trips/${encodeURIComponent(tripId)}/explore`), {
    method: "POST",
    body: JSON.stringify({
      window: {
        start_at: window.startAt,
        end_at: window.endAt,
        origin: window.origin,
        next_destination: window.nextDestination,
        duration_minutes: window.durationMinutes,
      },
      interests,
    }),
    ...(signal ? { signal } : {}),
  });

  if (!r.ok) throw new Error("Explore request failed");
  const payload: unknown = await r.json();
  return Array.isArray(payload)
    ? payload.map((item) => normalizePlaceRecommendation(item as ApiRecommendation))
    : [];
}

export async function addPlaceToTrip(
  tripId: string,
  placeId: string,
  window: TimeWindow,
  expectedVersion: number,
  interests: string[] = [],
): Promise<TripPlan> {
  const r = await authorizedFetch(
    apiUrl(`/api/v1/trips/${encodeURIComponent(tripId)}/itinerary-items`),
    {
      method: "POST",
      body: JSON.stringify({
        place_id: placeId,
        window: {
          start_at: window.startAt,
          end_at: window.endAt,
          origin: window.origin,
          next_destination: window.nextDestination,
          duration_minutes: window.durationMinutes,
        },
        expected_trip_version: expectedVersion,
        interests,
      }),
    },
  );

  if (r.status === 409) {
    throw new Error("STALE_TRIP_STATE");
  }

  if (!r.ok) {
    const errPayload = await r.json().catch(() => null);
    throw new Error(errPayload?.detail?.message || "Add place failed");
  }

  const payload: ApiTripPlanResponse = await r.json();
  return normalizePlan(payload);
}

export async function removeAddedItineraryItem(
  tripId: string,
  itemId: string,
  expectedVersion: number,
): Promise<TripPlan> {
  const r = await authorizedFetch(
    apiUrl(
      `/api/v1/trips/${encodeURIComponent(tripId)}/itinerary-items/${encodeURIComponent(itemId)}?expected_version=${expectedVersion}`,
    ),
    { method: "DELETE" },
  );

  if (r.status === 409) {
    throw new Error("STALE_TRIP_STATE");
  }

  if (!r.ok) throw new Error("Remove item failed");
  const payload: ApiTripPlanResponse = await r.json();
  return normalizePlan(payload);
}

export async function selectTripOption(
  tripId: string,
  optionId: string,
  selectionType: UserSelection["selectionType"],
  expectedVersion: number,
  confirmedFinalPrice?: Money,
  bookingReference?: string,
): Promise<TripPlan> {
  const r = await authorizedFetch(
    apiUrl(`/api/v1/trips/${encodeURIComponent(tripId)}/selections`),
    {
      method: "POST",
      body: JSON.stringify({
        option_id: optionId,
        selection_type: selectionType,
        expected_trip_version: expectedVersion,
        ...(confirmedFinalPrice ? { confirmed_final_price: confirmedFinalPrice } : {}),
        ...(bookingReference ? { booking_reference: bookingReference } : {}),
      }),
    },
  );
  if (r.status === 409) throw new Error("STALE_TRIP_STATE");
  if (!r.ok) throw new Error("Could not save selection");
  return normalizePlan((await r.json()) as ApiTripPlanResponse);
}

// Backward-compatible fallback for stateless explore
export async function exploreNearbyPlaces(
  request: ExploreRequest,
  signal?: AbortSignal,
): Promise<PlaceRecommendation[]> {
  const r = await authorizedFetch(apiUrl("/api/v1/trips/explore"), {
    method: "POST",
    body: JSON.stringify({
      interests: request.interests,
      window: {
        start_at: request.window.startAt,
        end_at: request.window.endAt,
        origin: request.window.origin,
        next_destination: request.window.nextDestination,
        duration_minutes: request.window.durationMinutes,
      },
      excluded_place_ids: request.excludedPlaceIds ?? [],
      remaining_budget: request.remainingBudget,
    }),
    ...(signal ? { signal } : {}),
  });
  if (!r.ok) throw new Error("Explore request failed");
  const payload: unknown = await r.json();
  return Array.isArray(payload)
    ? payload.map((item) => normalizePlaceRecommendation(item as ApiRecommendation))
    : [];
}
