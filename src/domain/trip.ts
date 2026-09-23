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
  dataMode: "demo" | "live" | "mixed" | string;
  version: number;
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
  source?: "planned" | "user_added" | "replan";
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
  weather: WeatherAssessment;
}

export interface WeatherAssessment {
  fit: WeatherFit;
  score: number;
  reason: string[];
}

export type WeatherAvailability = "available" | "not_available_yet" | "unavailable";
export type WeatherFit = "good" | "caution" | "unsuitable" | "unknown";

export interface HourlyWeather {
  timestamp: string;
  temperatureC?: number;
  feelsLikeC?: number;
  conditionText: string;
  conditionCode?: number;
  chanceOfRain?: number;
  precipitationMm?: number;
  windKph?: number;
}

export interface DailyWeather {
  date: string;
  minTemperatureC?: number;
  maxTemperatureC?: number;
  conditionText: string;
  conditionCode?: number;
  chanceOfRain?: number;
  totalPrecipitationMm?: number;
  maxWindKph?: number;
  hours: HourlyWeather[];
}

export interface WeatherAlert {
  headline: string;
  severity?: string;
  areas?: string;
  effectiveAt?: string;
  expiresAt?: string;
}

export interface WeatherForecast {
  availability: WeatherAvailability;
  location: GeoPoint;
  timezone?: string;
  provider: string;
  retrievedAt: string;
  alerts: WeatherAlert[];
  days: DailyWeather[];
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

export interface TripPlan {
  trip: Trip;
  flights: FlightOption[];
  hotels: HotelOption[];
  places: PlaceCandidate[];
  itinerary: ItineraryItem[];
  budget: BudgetBreakdown;
  sources: DataSourceStatus;
  weather?: WeatherForecast;
  freeTimeWindows: TimeWindow[];
  warnings: string[];
}
