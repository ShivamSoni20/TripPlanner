export type CurrencyCode = "INR" | "USD" | "EUR" | string;

export interface Money {
  amount: number;
  currency: CurrencyCode;
}

export interface GeoPoint {
  lat: number;
  lng: number;
}

export interface TripPreferences {
  interests: string[];
  pace: "relaxed" | "balanced" | "packed";
  hotelStyle?: string;
  transportPreferences: string[];
}

export interface TripConstraints {
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
  travelers: number;
  budget: Money;
  preferences: TripPreferences;
}

export interface Trip {
  id: string;
  constraints: TripConstraints;
  status: "planning" | "ready" | "active" | "completed";
  createdAt: string;
  updatedAt: string;
  dataMode: "demo" | "live";
}

export interface FlightOption {
  id: string;
  airline: string;
  departureAirport: string;
  arrivalAirport: string;
  departureTime: string;
  arrivalTime: string;
  durationMinutes: number;
  stops: number;
  price: Money;
  provider: string;
  bookingUrl?: string;
  retrievedAt: string;
}

export interface HotelOption {
  id: string;
  name: string;
  location: GeoPoint;
  rating?: number;
  totalPrice: Money;
  nightlyPrice?: Money;
  amenities: string[];
  provider: string;
  bookingUrl?: string;
  retrievedAt: string;
}

export interface OpeningPeriod {
  openDay: number;
  openHour: number;
  openMinute: number;
  closeDay?: number;
  closeHour?: number;
  closeMinute?: number;
}

export interface OpeningHours {
  status: string;
  periods: OpeningPeriod[];
  weekdayDescriptions: string[];
}

export interface PlaceCandidate {
  placeId: string;
  provider: string;
  providerId?: string;
  name: string;
  category: string;
  types: string[];
  location: GeoPoint;
  rating?: number;
  ratingCount?: number;
  price: Money;
  mapsUrl?: string;
  openNow?: boolean;
  openingHours?: OpeningHours;
  formattedAddress?: string;
  priceLevel?: string;
  photoReference?: string;
  retrievedAt?: string;
  suggestedVisitMinutes: number;
  weatherSuitability: number;
  interestTags: string[];
}

export interface ItineraryItem {
  id: string;
  title: string;
  category: string;
  startAt: string;
  endAt: string;
  location: GeoPoint;
  placeId?: string;
  cost: Money;
  travelFromPreviousMinutes: number;
}

export interface TimeWindow {
  startAt: string;
  endAt: string;
  origin: GeoPoint;
  nextDestination?: GeoPoint;
  durationMinutes: number;
}

export interface PlaceRecommendation {
  rank: string;
  place: PlaceCandidate;
  travelToMinutes: number;
  visitDurationMinutes: number;
  travelToNextMinutes: number;
  safetyBufferMinutes: number;
  totalRequiredMinutes: number;
  remainingBufferMinutes: number;
  score: number;
  reason: string[];
  feasible: boolean;
}

export interface DataSourceStatus {
  model: "demo" | "live" | string;
  flights: "demo" | "live" | string;
  hotels: "demo" | "live" | string;
  places: "demo" | "google" | string;
  routes: "demo" | "google" | string;
  weather: "unavailable" | "demo" | "live" | string;
}

export interface BudgetBreakdown {
  transport: number;
  hotel: number;
  food: number;
  activities: number;
  localTransport: number;
  total: number;
  remaining: number;
  currency: CurrencyCode;
  withinBudget: boolean;
}

export interface ExploreRequest {
  interests: string[];
  window: TimeWindow;
  excludedPlaceIds?: string[];
  remainingBudget?: number;
}
