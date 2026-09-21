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
