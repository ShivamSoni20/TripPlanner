import type {
  BudgetBreakdown,
  DataSourceStatus,
  ItineraryItem,
  PlaceRecommendation,
  TimeWindow,
  WeatherForecast,
} from "@/domain/trip";

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours ? `${hours}h${rest ? ` ${rest}m` : ""}` : `${rest}m`;
}

export function tripDayCount(start: string, end: string): number {
  return Math.max(
    1,
    Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86_400_000),
  );
}

export function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

export function formatDateRange(start: string, end: string): string {
  const formatter = new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
  return `${formatter.format(new Date(`${start}T00:00:00Z`))}–${formatter.format(new Date(`${end}T00:00:00Z`))}`;
}

export function deriveDisplayBudget(
  budget: BudgetBreakdown,
  added: ItineraryItem[],
): BudgetBreakdown {
  const additional = added.reduce((sum, item) => sum + item.cost.amount, 0);
  const remaining = budget.remaining - additional;
  return {
    ...budget,
    activities: budget.activities + additional,
    total: budget.total + additional,
    remaining,
    withinBudget: remaining >= 0,
  };
}

export function createItineraryItemFromRecommendation(
  recommendation: PlaceRecommendation,
  window: TimeWindow,
): ItineraryItem {
  const start = new Date(Date.parse(window.startAt) + recommendation.travelToMinutes * 60_000);
  const end = new Date(start.getTime() + recommendation.visitDurationMinutes * 60_000);
  return {
    id: `local-${recommendation.place.placeId}-${window.startAt}`,
    title: recommendation.place.name,
    category: recommendation.place.category,
    startAt: start.toISOString(),
    endAt: end.toISOString(),
    location: recommendation.place.location,
    placeId: recommendation.place.placeId,
    cost: recommendation.place.price,
    travelFromPreviousMinutes: recommendation.travelToMinutes,
  };
}

export function mergeItinerary(base: ItineraryItem[], added: ItineraryItem[]): ItineraryItem[] {
  return [...base, ...added].sort((a, b) => Date.parse(a.startAt) - Date.parse(b.startAt));
}

export function remainingWindow(
  window: TimeWindow,
  added: ItineraryItem[],
  minimumMinutes = 45,
): TimeWindow | null {
  const consumed = added
    .filter(
      (item) =>
        Date.parse(item.startAt) >= Date.parse(window.startAt) &&
        Date.parse(item.endAt) <= Date.parse(window.endAt),
    )
    .sort((a, b) => Date.parse(b.endAt) - Date.parse(a.endAt))[0];
  if (!consumed) return window;
  const durationMinutes = Math.floor(
    (Date.parse(window.endAt) - Date.parse(consumed.endAt)) / 60_000,
  );
  if (durationMinutes < minimumMinutes) return null;
  return { ...window, startAt: consumed.endAt, origin: consumed.location, durationMinutes };
}

export function getSourceSummary(sources: DataSourceStatus, forecast?: WeatherForecast): string {
  const entries = Object.entries(sources).filter(([name]) => name !== "weather");
  const demo = entries.filter(([, value]) => value === "demo").map(([name]) => name);
  const live = entries
    .filter(([, value]) => value !== "demo" && value !== "unavailable")
    .map(([name]) => name);
  if (sources.weather !== "demo" && forecast?.availability === "available") live.push("weather");
  if (sources.weather === "demo") demo.push("weather");
  if (live.length === 0) return "Demo data";
  return demo.length
    ? `Mixed data · provider ${live.join(", ")}; demo ${demo.join(", ")}`
    : `Provider data: ${live.join(", ")}`;
}

export function weatherSummary(forecast?: WeatherForecast, tripStartDate?: string): string {
  if (!forecast || forecast.availability === "unavailable") return "Weather unavailable";
  if (forecast.availability === "not_available_yet") return "Forecast available closer to trip";
  const day = tripStartDate
    ? forecast.days.find((item) => item.date === tripStartDate)
    : forecast.days[0];
  if (!day) return "Weather unavailable";
  const temperatures = [day.minTemperatureC, day.maxTemperatureC].filter(
    (n): n is number => n != null,
  );
  return `${temperatures.length ? `${temperatures.map(Math.round).join("–")}°C · ` : ""}${day.conditionText}`;
}
