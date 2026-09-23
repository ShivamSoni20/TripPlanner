import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/auth/auth-provider";
import { AuthModal } from "@/components/auth-modal";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertTriangle,
  ArrowRight,
  BedDouble,
  Bell,
  CalendarDays,
  Check,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  CloudSun,
  Compass,
  ExternalLink,
  Hotel,
  LocateFixed,
  Map,
  MapPin,
  Navigation,
  Plane,
  Plus,
  RefreshCw,
  Route as RouteIcon,
  Search,
  Sparkles,
  Star,
  Sun,
  Umbrella,
  Users,
  Utensils,
  WifiOff,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  addPlaceToTrip,
  createTripPlan,
  exploreTrip,
  getTrip,
  listTrips,
  removeAddedItineraryItem,
  selectTripOption,
  type TripPlanResponse,
} from "@/lib/trip-api";
import {
  formatDateRange,
  formatDuration,
  formatTime,
  getSourceSummary,
  tripDayCount,
  weatherSummary,
} from "@/lib/trip-display";
import type {
  BudgetBreakdown,
  ItineraryItem,
  PlaceRecommendation,
  TimeWindow,
} from "@/domain/trip";
import goaHero from "@/assets/goa-hero.jpg";
import fortImage from "@/assets/fort-aguada.jpg";
import beachImage from "@/assets/goa-beach.jpg";
import hotelImage from "@/assets/goa-hotel.jpg";

export type TripView =
  "overview" | "itinerary" | "explore" | "flights" | "hotels" | "map" | "budget" | "alerts";
type AppStage = "prompt" | "planning" | "trip";

type TripContextValue = {
  stage: AppStage;
  setStage: (value: AppStage) => void;
  plan: TripPlanResponse | null;
  planningError: string | null;
  followUpQuestion: string | null;
  startPlanning: (prompt: string) => Promise<void>;
  view: TripView;
  setView: (value: TripView) => void;
  selectedStopId: string | null;
  setSelectedStopId: (value: string | null) => void;
  activeFreeTimeWindowIndex: number;
  setActiveFreeTimeWindowIndex: (value: number) => void;
  activeFreeTimeWindow: TimeWindow | null;
  displayItinerary: ItineraryItem[];
  displayBudget: BudgetBreakdown | null;
  addedRecommendations: PlaceRecommendation[];
  addRecommendation: (value: PlaceRecommendation) => Promise<void>;
  removeRecommendation: (itemId: string) => Promise<void>;
  addingPlace: boolean;
  tripLoadError: string | null;
  delayOpen: boolean;
  setDelayOpen: (value: boolean) => void;
  selectOption: (
    optionId: string,
    selectionType: "selected_flight" | "selected_hotel",
  ) => Promise<void>;
};

const TripContext = createContext<TripContextValue | null>(null);

export function TripProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const previousUserId = useRef<string | null>(null);
  const [stage, setStage] = useState<AppStage>("prompt");
  const [view, setView] = useState<TripView>("overview");
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null);
  const [activeFreeTimeWindowIndex, setActiveFreeTimeWindowIndex] = useState(0);
  const [addingPlace, setAddingPlace] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const [delayOpen, setDelayOpen] = useState(false);
  const [plan, setPlan] = useState<TripPlanResponse | null>(null);
  const [planningError, setPlanningError] = useState<string | null>(null);
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  useEffect(() => {
    const userId = auth.user?.id ?? null;
    if (previousUserId.current !== userId) {
      previousUserId.current = userId;
      setPlan(null);
      setStage("prompt");
      queryClient.removeQueries({ queryKey: ["trip"] });
    }
  }, [auth.user?.id, queryClient]);
  const tripId = /^\/trips\/([^/]+)/.exec(location.pathname)?.[1];
  const persistedTrip = useQuery({
    queryKey: ["trip", auth.user?.id, tripId],
    queryFn: () => getTrip(tripId!),
    enabled: Boolean(tripId && auth.user && !auth.loading),
  });
  useEffect(() => {
    if (persistedTrip.data) {
      setPlan(persistedTrip.data);
      setStage("trip");
    }
  }, [persistedTrip.data]);
  useEffect(() => {
    if (tripId && !auth.loading && !auth.user) setAuthOpen(true);
  }, [tripId, auth.loading, auth.user]);
  useEffect(() => {
    if (auth.user && pendingPrompt) {
      const prompt = pendingPrompt;
      setPendingPrompt(null);
      setAuthOpen(false);
      void startPlanning(prompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.user, pendingPrompt]);

  const startPlanning = async (prompt: string) => {
    if (!auth.user) {
      setPendingPrompt(prompt);
      setAuthOpen(true);
      return;
    }
    setPlanningError(null);
    setFollowUpQuestion(null);
    setStage("planning");
    try {
      const response = await createTripPlan(prompt);
      if ("missing" in response) {
        setFollowUpQuestion(response.question);
        setStage("prompt");
        return;
      }
      setPlan(response);
      queryClient.setQueryData(["trip", auth.user.id, response.trip.id], response);
      void queryClient.invalidateQueries({ queryKey: ["trips", auth.user.id] });
      setActiveFreeTimeWindowIndex(0);
      setSelectedStopId(response.itinerary[0]?.id ?? null);
      setStage("trip");
      void navigate({ to: "/trips/$tripId", params: { tripId: response.trip.id } });
    } catch (error) {
      setPlanningError(error instanceof Error ? error.message : "Trip planning failed");
    }
  };
  const displayItinerary = plan?.itinerary ?? [];
  const displayBudget = plan?.budget ?? null;
  const activeFreeTimeWindow = useMemo(() => {
    const original = plan?.freeTimeWindows[activeFreeTimeWindowIndex];
    return original ?? null;
  }, [plan, activeFreeTimeWindowIndex]);
  const addRecommendation = async (recommendation: PlaceRecommendation) => {
    if (!recommendation.feasible || !activeFreeTimeWindow || !plan || addingPlace) return;
    setAddingPlace(true);
    try {
      const updated = await addPlaceToTrip(
        plan.trip.id,
        recommendation.place.placeId,
        activeFreeTimeWindow,
        plan.trip.version,
      );
      setPlan(updated);
      setSelectedStopId(
        updated.itinerary.find((item) => item.placeId === recommendation.place.placeId)?.id ?? null,
      );
      queryClient.setQueryData(["trip", auth.user?.id, plan.trip.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["trip-explorer", plan.trip.id] });
      void queryClient.invalidateQueries({ queryKey: ["trips", auth.user?.id] });
    } catch (error) {
      if (error instanceof Error && error.message === "STALE_TRIP_STATE") {
        const fresh = await getTrip(plan.trip.id);
        setPlan(fresh);
        setPlanningError("The itinerary changed. TripPilot refreshed the latest plan.");
      } else {
        setPlanningError(error instanceof Error ? error.message : "Could not add this place");
      }
    } finally {
      setAddingPlace(false);
    }
  };
  const removeRecommendation = async (itemId: string) => {
    if (!plan || addingPlace) return;
    setAddingPlace(true);
    try {
      const updated = await removeAddedItineraryItem(plan.trip.id, itemId, plan.trip.version);
      setPlan(updated);
      queryClient.setQueryData(["trip", auth.user?.id, plan.trip.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["trip-explorer", plan.trip.id] });
      void queryClient.invalidateQueries({ queryKey: ["trips", auth.user?.id] });
    } catch (error) {
      if (error instanceof Error && error.message === "STALE_TRIP_STATE") {
        setPlan(await getTrip(plan.trip.id));
      }
      setPlanningError(error instanceof Error ? error.message : "Could not remove this activity");
    } finally {
      setAddingPlace(false);
    }
  };
  const selectOption = async (
    optionId: string,
    selectionType: "selected_flight" | "selected_hotel",
  ) => {
    if (!plan) return;
    try {
      const updated = await selectTripOption(
        plan.trip.id,
        optionId,
        selectionType,
        plan.trip.version,
      );
      setPlan(updated);
      queryClient.setQueryData(["trip", auth.user?.id, plan.trip.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["trips", auth.user?.id] });
    } catch (error) {
      setPlanningError(error instanceof Error ? error.message : "Could not save selection");
    }
  };
  const value: TripContextValue = {
    stage,
    setStage,
    plan,
    planningError,
    followUpQuestion,
    startPlanning,
    view,
    setView,
    selectedStopId,
    setSelectedStopId,
    activeFreeTimeWindowIndex,
    setActiveFreeTimeWindowIndex,
    activeFreeTimeWindow,
    displayItinerary,
    displayBudget,
    addedRecommendations: [],
    addRecommendation,
    removeRecommendation,
    addingPlace,
    tripLoadError: persistedTrip.isError
      ? persistedTrip.error instanceof Error
        ? persistedTrip.error.message
        : "Trip not found or you don't have access"
      : null,
    delayOpen,
    setDelayOpen,
    selectOption,
  };
  return (
    <TripContext.Provider value={value}>
      <AuthModal isOpen={authOpen} onClose={() => setAuthOpen(false)} />
      {children}
    </TripContext.Provider>
  );
}

function useTrip() {
  const value = useContext(TripContext);
  if (!value) throw new Error("TripProvider is missing");
  return value;
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2 font-display font-bold text-foreground">
      <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
        <Sparkles className="size-5" />
      </span>
      {!compact && <span className="text-lg">TripPilot</span>}
    </div>
  );
}

export function TripPrompt() {
  const { followUpQuestion, startPlanning } = useTrip();
  const auth = useAuth();
  const navigate = useNavigate();
  const recentTrips = useQuery({
    queryKey: ["trips", auth.user?.id],
    queryFn: listTrips,
    enabled: Boolean(auth.user),
  });
  const [query, setQuery] = useState(
    "Goa for 5 days, two people, ₹30k. Beaches, nightlife and history. Keep it relaxed.",
  );
  const chips = ["Goa under ₹30k", "Weekend escape", "Mountains", "Beaches", "Surprise me"];
  return (
    <main className="relative min-h-screen overflow-hidden bg-background px-5 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Brand />
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {auth.user ? (
            <>
              <span className="hidden sm:inline">{auth.user.email}</span>
              <Button type="button" variant="outline" onClick={() => void auth.signOut()}>
                Sign out
              </Button>
            </>
          ) : (
            <span>Sign in to save trips</span>
          )}
        </div>
      </header>
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-35"
        viewBox="0 0 1400 850"
      >
        <path
          d="M-40 610 C230 420 290 800 610 610 S1030 430 1460 570"
          fill="none"
          stroke="var(--coral)"
          strokeDasharray="7 14"
          strokeWidth="2"
        />
        <circle cx="190" cy="525" r="8" fill="var(--coral)" />
        <circle cx="1175" cy="510" r="8" fill="var(--coral)" />
      </svg>
      <section className="relative mx-auto flex min-h-[calc(100vh-80px)] max-w-4xl flex-col items-center justify-center pb-16 text-center">
        <div className="mb-8 flex items-center gap-3 rounded-full bg-lavender/60 px-4 py-2 text-sm font-semibold">
          <Sparkles className="size-4 text-primary" /> Your AI travel operating system
        </div>
        <h1 className="max-w-3xl text-5xl font-bold leading-[1.08] sm:text-7xl">
          Where should we go next?
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-muted-foreground">
          Tell me the feeling, budget and pace. I’ll connect the flights, stays, places and moments.
        </p>
        <form
          className="mt-10 w-full rounded-[28px] border bg-card p-3 text-left shadow-[0_24px_70px_-36px_color-mix(in_oklab,var(--foreground)_25%,transparent)]"
          onSubmit={(event) => {
            event.preventDefault();
            if (query.trim()) void startPlanning(query.trim());
          }}
        >
          {followUpQuestion && (
            <div role="status" className="mx-2 mb-2 rounded-2xl bg-butter/55 px-4 py-3 text-sm">
              <span className="font-semibold">One detail before I plan:</span> {followUpQuestion}
            </div>
          )}
          <label className="sr-only" htmlFor="trip-query">
            Describe your trip
          </label>
          <textarea
            id="trip-query"
            name="trip-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Goa for 5 days, two people, ₹30k. Beaches, nightlife and history. Keep it relaxed."
            className="min-h-32 w-full resize-none rounded-2xl bg-transparent p-4 text-lg leading-7 outline-none placeholder:text-muted-foreground"
          />
          <div className="flex justify-end">
            <Button
              size="lg"
              type="submit"
              disabled={!query.trim()}
              className="h-13 rounded-full px-6 text-base"
            >
              <Sparkles /> Plan my adventure
            </Button>
          </div>
        </form>
        {auth.user && recentTrips.data && recentTrips.data.length > 0 && (
          <section className="mt-8 w-full text-left" aria-label="Recent trips">
            <h2 className="mb-3 text-lg font-bold">Recent trips</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {recentTrips.data.slice(0, 4).map((recent) => (
                <button
                  key={recent.id}
                  type="button"
                  onClick={() =>
                    void navigate({ to: "/trips/$tripId", params: { tripId: recent.id } })
                  }
                  className="rounded-2xl border bg-card p-4 text-left hover:border-primary"
                >
                  <span className="font-bold">{recent.destination}</span>
                  <span className="mt-1 block text-sm text-muted-foreground">
                    {formatDateRange(recent.startDate, recent.endDate)} · {recent.status}
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {chips.map((chip) => (
            <button
              key={chip}
              onClick={() =>
                setQuery(
                  chip === "Goa under ₹30k"
                    ? "Goa for 5 days, two people, ₹30k. Beaches, nightlife and history. Keep it relaxed."
                    : chip,
                )
              }
              className="rounded-full border bg-card px-4 py-2.5 text-sm font-medium shadow-sm transition hover:-translate-y-0.5 hover:border-primary"
            >
              {chip}
            </button>
          ))}
        </div>
        <div className="mt-14 grid grid-cols-3 gap-7 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <Sun className="size-4 text-primary" />
            Weather-aware
          </span>
          <span className="flex items-center gap-2">
            <RouteIcon className="size-4 text-primary" />
            Route-smart
          </span>
          <span className="flex items-center gap-2">
            <CircleDollarSign className="size-4 text-primary" />
            Budget-safe
          </span>
        </div>
      </section>
    </main>
  );
}

export function AgentProgress() {
  const { planningError, setStage } = useTrip();
  return (
    <main className="min-h-screen bg-background p-5 md:p-10">
      <header className="mx-auto max-w-6xl">
        <Brand />
      </header>
      <section className="mx-auto grid min-h-[calc(100vh-100px)] max-w-6xl items-center gap-12 py-12 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-lavender px-4 py-2 text-sm font-semibold">
            <Sparkles className="star-motion size-4 text-primary" /> TripPilot is working
          </div>
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">Planning your adventure</h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Your request is running. TripPilot will show the finished plan once the configured
            providers and deterministic checks return.
          </p>
          <div className="mt-10 space-y-3">
            <div className="flex items-center gap-4 rounded-2xl border bg-card px-4 py-3">
              <span className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <span className="size-2 animate-pulse rounded-full bg-primary-foreground" />
              </span>
              <p className="font-semibold">Waiting for the planning response</p>
            </div>
            {planningError && (
              <div
                role="alert"
                className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4"
              >
                <p className="font-semibold text-destructive">The planner could not be reached</p>
                <p className="mt-1 text-sm text-muted-foreground">{planningError}</p>
                <Button className="mt-4" variant="outline" onClick={() => setStage("prompt")}>
                  Back to trip request
                </Button>
              </div>
            )}
          </div>
        </div>
        <TripMap compact items={[]} selectedId={null} onSelect={() => undefined} />
      </section>
    </main>
  );
}

const desktopViews: { id: TripView; label: string; icon: typeof Map }[] = [
  { id: "overview", label: "Overview", icon: Compass },
  { id: "itinerary", label: "Itinerary", icon: RouteIcon },
  { id: "explore", label: "Explore", icon: Search },
  { id: "flights", label: "Flights", icon: Plane },
  { id: "hotels", label: "Hotels", icon: BedDouble },
  { id: "map", label: "Map", icon: Map },
  { id: "budget", label: "Budget", icon: CircleDollarSign },
  { id: "alerts", label: "Alerts", icon: Bell },
];

export function AppShell() {
  const trip = useTrip();
  return (
    <div className="min-h-screen bg-background pb-20 md:pb-0">
      <header className="sticky top-0 z-40 border-b bg-background/95 px-4 backdrop-blur md:px-7">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-6">
          <button onClick={() => trip.setView("overview")}>
            <Brand />
          </button>
          <nav className="hidden items-center gap-1 xl:flex">
            {desktopViews.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => trip.setView(id)}
                className={cn(
                  "rounded-full px-3.5 py-2 text-sm font-semibold transition",
                  trip.view === id
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {label}
                {id === "alerts" && (
                  <span className="ml-1.5 inline-block size-2 rounded-full bg-primary" />
                )}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold">
                {trip.plan?.trip.constraints.destination} ·{" "}
                {trip.plan
                  ? tripDayCount(
                      trip.plan.trip.constraints.startDate,
                      trip.plan.trip.constraints.endDate,
                    )
                  : 0}{" "}
                days
              </p>
              <p className="text-xs text-muted-foreground">
                {trip.plan
                  ? formatDateRange(
                      trip.plan.trip.constraints.startDate,
                      trip.plan.trip.constraints.endDate,
                    )
                  : ""}
              </p>
            </div>
            <button
              aria-label="Open alerts"
              onClick={() => trip.setView("alerts")}
              className="relative flex size-10 items-center justify-center rounded-full border bg-card"
            >
              <Bell className="size-4" />
              <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-primary" />
            </button>
          </div>
        </div>
        <div className="mx-auto flex max-w-[1440px] gap-2 overflow-x-auto pb-3 xl:hidden">
          {desktopViews.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => trip.setView(id)}
              className={cn(
                "whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium",
                trip.view === id ? "bg-foreground text-background" : "bg-card",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </header>
      <div className="mx-auto max-w-[1440px] p-4 md:p-7">
        <AnimatePresence mode="wait">
          <motion.div
            key={trip.view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.24 }}
          >
            {trip.view === "overview" && <Overview />}
            {trip.view === "itinerary" && <Itinerary />}
            {trip.view === "explore" && <SmartExplorer />}
            {trip.view === "flights" && <Flights />}
            {trip.view === "hotels" && <Hotels />}
            {trip.view === "map" && <MapView />}
            {trip.view === "budget" && <Budget />}
            {trip.view === "alerts" && <Alerts />}
          </motion.div>
        </AnimatePresence>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t bg-card px-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-2 md:hidden">
        {[
          { id: "overview" as TripView, label: "Trip", icon: Compass },
          { id: "explore" as TripView, label: "Explore", icon: Search },
          { id: "map" as TripView, label: "Map", icon: Map },
          { id: "alerts" as TripView, label: "Alerts", icon: Bell },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => trip.setView(id)}
            className={cn(
              "flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl text-xs font-semibold",
              trip.view === id ? "text-primary" : "text-muted-foreground",
            )}
          >
            <Icon className="size-5" />
            {label}
          </button>
        ))}
      </nav>
      <AnimatePresence>{trip.delayOpen && <ReplanComparison />}</AnimatePresence>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  copy,
  action,
}: {
  eyebrow?: string;
  title: string;
  copy?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="mb-2 text-sm font-bold uppercase text-primary">{eyebrow}</p>}
        <h2 className="text-3xl font-bold md:text-4xl">{title}</h2>
        {copy && <p className="mt-2 max-w-2xl text-muted-foreground">{copy}</p>}
      </div>
      {action}
    </div>
  );
}

function TripHero() {
  const { plan, setView } = useTrip();
  const destination = plan?.trip.constraints.destination ?? "Your destination";
  const travelers = plan?.trip.constraints.travelers ?? 0;
  const start = plan?.trip.constraints.startDate;
  const end = plan?.trip.constraints.endDate;
  const isGoa = destination.toLowerCase().includes("goa");
  return (
    <section className="relative min-h-[390px] overflow-hidden rounded-[28px] bg-foreground text-primary-foreground">
      {isGoa && (
        <img
          src={goaHero}
          width={1600}
          height={1000}
          className="absolute inset-0 h-full w-full object-cover"
          alt="Sunlit coastal view across Goa"
        />
      )}
      <div className="absolute inset-0 bg-[linear-gradient(90deg,color-mix(in_oklab,var(--foreground)_82%,transparent),transparent_78%)]" />
      <div className="relative flex min-h-[390px] max-w-2xl flex-col justify-end p-6 md:p-10">
        <div className="mb-auto flex w-fit max-w-full items-center gap-2 rounded-2xl bg-background/90 px-3 py-2 text-sm font-semibold text-foreground">
          <span className="size-2 rounded-full bg-aqua" /> Trip ready ·{" "}
          {plan ? getSourceSummary(plan.sources, plan.weather) : "Trip data"}
        </div>
        <p className="text-sm font-bold uppercase">
          {start && end ? formatDateRange(start, end) : "Your travel dates"}
        </p>
        <h1 className="mt-2 text-6xl font-bold uppercase md:text-8xl">{destination}</h1>
        <div className="mt-5 flex flex-wrap gap-3 text-sm font-semibold">
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <CalendarDays className="mr-2 inline size-4" />
            {start && end ? `${tripDayCount(start, end)} days` : "Trip"}
          </span>
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <Users className="mr-2 inline size-4" />
            {travelers} travellers
          </span>
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <CloudSun className="mr-2 inline size-4" />
            {weatherSummary(plan?.weather, start)}
          </span>
        </div>
        <Button
          onClick={() => setView("itinerary")}
          className="mt-7 w-fit rounded-full bg-background text-foreground hover:bg-background/90"
        >
          See your itinerary <ArrowRight />
        </Button>
      </div>
    </section>
  );
}

function BudgetMeter({ compact = false }: { compact?: boolean }) {
  const { plan, displayBudget } = useTrip();
  if (!plan || !displayBudget) return null;
  const spent = displayBudget.total;
  const limit = plan.trip.constraints.budget.amount;
  const remaining = displayBudget.remaining;
  const percentage = limit > 0 ? Math.min((spent / limit) * 100, 100) : 0;
  return (
    <div className={cn("rounded-3xl border bg-mint/45", compact ? "p-5" : "p-6")}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-muted-foreground">Trip budget</p>
          <p className="mt-1 text-2xl font-bold">
            ₹{spent.toLocaleString("en-IN")}{" "}
            <span className="text-base font-medium text-muted-foreground">
              / ₹{limit.toLocaleString("en-IN")}
            </span>
          </p>
        </div>
        <span className="rounded-full bg-card px-3 py-1 text-sm font-bold">
          ₹{remaining.toLocaleString("en-IN")} left
        </span>
      </div>
      <Progress value={percentage} className="mt-5 h-2.5 bg-card [&>div]:bg-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">
        {remaining >= 0
          ? "On track within your requested budget."
          : "Over budget — review options."}
      </p>
    </div>
  );
}

function Overview() {
  const {
    plan,
    setView,
    setDelayOpen,
    displayItinerary,
    activeFreeTimeWindow,
    selectedStopId,
    setSelectedStopId,
  } = useTrip();
  const flight = plan?.flights[0];
  const hotel = plan?.hotels[0];
  const firstStop = displayItinerary[0];
  return (
    <div className="space-y-6">
      <TripHero />
      <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
        <div className="grid gap-6">
          <BudgetMeter />
          {activeFreeTimeWindow && (
            <button
              onClick={() => setView("explore")}
              className="group rounded-3xl border bg-butter/55 p-6 text-left transition hover:-translate-y-1"
            >
              <div className="flex items-start gap-4">
                <span className="flex size-11 items-center justify-center rounded-2xl bg-card text-primary">
                  <Sparkles />
                </span>
                <div>
                  <p className="font-display text-xl font-bold">
                    You have {formatDuration(activeFreeTimeWindow.durationMinutes)} free
                  </p>
                  <p className="mt-2 text-muted-foreground">
                    Explore what fits before your next scheduled stop.
                  </p>
                  <span className="mt-5 inline-flex items-center gap-2 font-bold text-primary">
                    Explore free time{" "}
                    <ArrowRight className="size-4 transition group-hover:translate-x-1" />
                  </span>
                </div>
              </div>
            </button>
          )}
          <button
            onClick={() => setDelayOpen(true)}
            className="flex items-center justify-between rounded-3xl border bg-peach/55 p-5 text-left"
          >
            <div className="flex items-center gap-3">
              <Plane className="size-5 text-primary" />
              <div>
                <p className="font-bold">Demo disruption preview</p>
                <p className="text-sm text-muted-foreground">
                  See a sample delayed-arrival comparison.
                </p>
              </div>
            </div>
            <ChevronRight />
          </button>
        </div>
        <TripMap
          items={displayItinerary}
          selectedId={selectedStopId}
          onSelect={(id) => {
            setSelectedStopId(id);
            setView("itinerary");
          }}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <MiniStatus
          icon={Plane}
          label="Flight option"
          value={
            flight
              ? `${flight.airline} · ${formatTime(flight.departureTime)}`
              : "No flight option available"
          }
          note={
            flight
              ? `${flight.departureAirport} → ${flight.arrivalAirport} · ${flight.stops ? `${flight.stops} stop` : "Direct"} · ${plan?.sources.flights} data`
              : "Search can be retried later"
          }
        />
        <MiniStatus
          icon={Hotel}
          label="Stay option"
          value={hotel?.name ?? "No hotel option available"}
          note={
            hotel
              ? `₹${hotel.totalPrice.amount.toLocaleString("en-IN")} total · ${plan?.sources.hotels} data`
              : "Search can be retried later"
          }
        />
        <MiniStatus
          icon={Utensils}
          label="First planned stop"
          value={firstStop?.title ?? "No stops planned"}
          note={
            firstStop
              ? `${formatDateRange(firstStop.startAt.slice(0, 10), firstStop.startAt.slice(0, 10))} · ${formatTime(firstStop.startAt)}`
              : "Your itinerary is empty"
          }
        />
      </div>
    </div>
  );
}

function MiniStatus({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof Plane;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-3xl border bg-card p-5">
      <div className="flex size-10 items-center justify-center rounded-xl bg-sky/50">
        <Icon className="size-5" />
      </div>
      <p className="mt-5 text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 font-bold">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{note}</p>
    </div>
  );
}

function RouteThread() {
  const trip = useTrip();
  const shown = trip.displayItinerary;
  return (
    <div className="relative space-y-2 pl-9 before:absolute before:bottom-12 before:left-[13px] before:top-10 before:w-px before:bg-border">
      {shown.length === 0 && (
        <p className="p-5 text-muted-foreground">No itinerary stops are available yet.</p>
      )}
      {shown.map((stop, index) => (
        <div key={stop.id}>
          {index > 0 && (
            <div className="my-3 ml-1 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
              <Navigation className="size-3.5" />
              {stop.travelFromPreviousMinutes} min travel from previous stop
            </div>
          )}
          <button
            onClick={() => trip.setSelectedStopId(stop.id)}
            className={cn(
              "relative flex w-full gap-4 rounded-3xl border bg-card p-4 text-left transition",
              trip.selectedStopId === stop.id &&
                "border-primary shadow-[0_8px_30px_-18px_var(--coral)]",
            )}
          >
            <span
              className={cn(
                "absolute -left-[34px] top-7 z-10 flex size-7 items-center justify-center rounded-full border-4 border-background text-xs font-bold",
                trip.selectedStopId === stop.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-foreground text-background",
              )}
            >
              {index + 1}
            </span>
            <div className="min-w-0 py-1">
              <p className="text-sm font-bold text-primary">
                {formatDateRange(stop.startAt.slice(0, 10), stop.startAt.slice(0, 10))} ·{" "}
                {formatTime(stop.startAt)}
              </p>
              <h3 className="mt-1 text-lg font-bold">{stop.title}</h3>
              <p className="text-sm text-muted-foreground">
                {stop.category} ·{" "}
                {formatDuration(
                  Math.round((Date.parse(stop.endAt) - Date.parse(stop.startAt)) / 60_000),
                )}
              </p>
            </div>
          </button>
          {stop.source === "user_added" && (
            <Button
              type="button"
              variant="ghost"
              disabled={trip.addingPlace}
              onClick={() => void trip.removeRecommendation(stop.id)}
              className="mt-1 text-sm"
            >
              Undo added activity
            </Button>
          )}
          {trip.plan?.freeTimeWindows.map(
            (window, windowIndex) =>
              stop.endAt === window.startAt && (
                <FreeTimeCard key={window.startAt} windowIndex={windowIndex} />
              ),
          )}
        </div>
      ))}
    </div>
  );
}

function FreeTimeCard({ windowIndex }: { windowIndex: number }) {
  const { setView, plan, setActiveFreeTimeWindowIndex } = useTrip();
  const window = plan?.freeTimeWindows[windowIndex];
  if (!window) return null;
  const start = formatTime(window.startAt);
  const end = formatTime(window.endAt);
  return (
    <button
      onClick={() => {
        setActiveFreeTimeWindowIndex(windowIndex);
        setView("explore");
      }}
      className="relative my-3 w-full rounded-3xl border border-dashed border-primary/50 bg-butter/55 p-5 text-left"
    >
      <span className="absolute -left-[34px] top-6 z-10 flex size-7 items-center justify-center rounded-full border-4 border-background bg-butter">
        <Sparkles className="size-3 text-primary" />
      </span>
      <p className="text-sm font-bold text-primary">
        {start}–{end}
      </p>
      <p className="mt-1 text-xl font-bold">
        {Math.floor(window.durationMinutes / 60)}h {window.durationMinutes % 60}m free
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Check route-aware activities that can safely fit this window.
      </p>
      <span className="mt-4 inline-flex items-center gap-2 text-sm font-bold">
        Explore nearby <ArrowRight className="size-4" />
      </span>
    </button>
  );
}

function Itinerary() {
  const trip = useTrip();
  const destination = trip.plan?.trip.constraints.destination ?? "Your trip";
  return (
    <>
      <SectionHeading
        eyebrow="Day by day"
        title={`${destination} itinerary`}
        copy={
          trip.addedRecommendations.length
            ? `${trip.addedRecommendations.at(-1)?.place.name} was added locally to your itinerary.`
            : "Your scheduled activities and travel times."
        }
      />
      <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
        <section className="rounded-[28px] border bg-background p-2 md:p-5">
          <RouteThread />
        </section>
        <div className="lg:sticky lg:top-28 lg:h-fit">
          <TripMap
            items={trip.displayItinerary}
            selectedId={trip.selectedStopId}
            onSelect={trip.setSelectedStopId}
          />
        </div>
      </div>
    </>
  );
}

function SmartExplorer() {
  const trip = useTrip();
  const [filter, setFilter] = useState("Best Fit");
  const [selected, setSelected] = useState<string | null>(null);
  const window = trip.activeFreeTimeWindow;
  const interests =
    filter === "Best Fit"
      ? (trip.plan?.trip.constraints.preferences.interests ?? [])
      : [filter.toLowerCase()];
  const excludedPlaceIds = [
    ...new Set(
      trip.displayItinerary.map((item) => item.placeId).filter((id): id is string => Boolean(id)),
    ),
  ].sort();
  const explorer = useQuery({
    queryKey: [
      "trip-explorer",
      trip.plan?.trip.id,
      trip.plan?.trip.version,
      window?.startAt,
      window?.endAt,
      window?.origin.lat,
      window?.origin.lng,
      window?.nextDestination?.lat,
      window?.nextDestination?.lng,
      interests.join("|"),
      excludedPlaceIds.join("|"),
      trip.displayBudget?.remaining,
    ],
    queryFn: ({ signal }) => exploreTrip(trip.plan!.trip.id, window!, interests, signal),
    enabled: Boolean(trip.plan && window),
  });
  const liveRecommendations = explorer.data ?? [];
  const windowLabel = window
    ? `${formatTime(window.startAt)}–${formatTime(window.endAt)}`
    : "No free window";
  return (
    <>
      <SectionHeading
        eyebrow="Smart free-time explorer"
        title={
          window ? `${formatDuration(window.durationMinutes)} free` : "No free time window yet"
        }
        copy={
          window
            ? "Recommendations are route-, budget-, opening-hours-, and weather-checked."
            : "Add more itinerary detail to unlock nearby recommendations."
        }
        action={
          <span className="rounded-full bg-butter px-4 py-2 text-sm font-bold">
            <Clock3 className="mr-2 inline size-4" />
            {windowLabel}
          </span>
        }
      />
      <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
        {["Best Fit", "History", "Beach", "Food", "Nature", "Nightlife"].map((item) => (
          <button
            key={item}
            onClick={() => setFilter(item)}
            className={cn(
              "whitespace-nowrap rounded-full border px-4 py-2 text-sm font-semibold",
              filter === item ? "border-foreground bg-foreground text-background" : "bg-card",
            )}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.08fr_.92fr]">
        <div className="flex snap-x gap-4 overflow-x-auto pb-4 xl:grid xl:grid-cols-1">
          {explorer.isLoading && (
            <p className="rounded-3xl border bg-card p-6 text-muted-foreground">
              Checking nearby places, routes, opening hours, and weather…
            </p>
          )}
          {explorer.isError && (
            <div className="rounded-3xl border bg-peach/40 p-6">
              <p>
                TripPilot couldn't check nearby options.{" "}
                {explorer.error instanceof Error ? explorer.error.message : "Please try again."}
              </p>
              <Button className="mt-3" onClick={() => void explorer.refetch()}>
                Retry
              </Button>
            </div>
          )}
          {!explorer.isLoading &&
            !explorer.isError &&
            window &&
            liveRecommendations.length === 0 && (
              <p className="rounded-3xl border bg-card p-6 text-muted-foreground">
                Nothing worthwhile fits safely before your next activity.
              </p>
            )}
          {liveRecommendations.map((item, index) => (
            <motion.article
              layout
              key={item.place.placeId}
              aria-current={selected === item.place.placeId ? "true" : undefined}
              className={cn(
                "min-w-[86vw] snap-center overflow-hidden rounded-[28px] border bg-card sm:min-w-[520px] xl:min-w-0",
                selected === item.place.placeId && "border-primary",
              )}
            >
              <div className="grid sm:grid-cols-[210px_1fr]">
                <div
                  className="h-52 w-full bg-[radial-gradient(circle_at_30%_25%,var(--butter),transparent_45%),linear-gradient(145deg,var(--aqua),var(--sky))] sm:h-full"
                  aria-hidden="true"
                />
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <span
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-bold",
                        index === 0 ? "bg-lavender" : "bg-muted",
                      )}
                    >
                      {item.rank}
                    </span>
                    <span className="flex items-center gap-1 text-sm font-bold">
                      <Star className="size-4 fill-current text-primary" />
                      {item.place.rating ?? "—"}
                    </span>
                  </div>
                  <h3 className="mt-4 text-xl font-bold">{item.place.name}</h3>
                  <p className="text-sm text-muted-foreground">{item.place.category}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                    <span>
                      <Navigation className="mr-1 inline size-3.5" />
                      {item.travelToMinutes} min away
                    </span>
                    <span>
                      <Clock3 className="mr-1 inline size-3.5" />
                      {item.visitDurationMinutes} min visit
                    </span>
                    <span>{item.travelToNextMinutes} min to next</span>
                    <span>₹{item.place.price.amount} estimated</span>
                  </div>
                  <p className="mt-3 font-semibold text-foreground">
                    <Check className="mr-1 inline size-4 text-primary" />
                    {item.remainingBufferMinutes} min buffer
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {
                      {
                        good: "Good for this window",
                        caution: "Weather caution",
                        unsuitable: "Weather not recommended",
                        unknown: "Forecast unavailable",
                      }[item.weather.fit]
                    }{" "}
                    · {item.weather.reason.join(" · ") || "No weather signal"}
                  </p>
                  <div className="mt-4 rounded-2xl bg-lavender/35 p-3 text-sm">
                    <p className="font-bold">Why this works</p>
                    <p className="mt-1 text-muted-foreground">{item.reason.join(" · ")}</p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setSelected(item.place.placeId)}
                      className="rounded-full"
                    >
                      <MapPin /> Preview route
                    </Button>
                    <Button
                      disabled={
                        trip.displayItinerary.some(
                          (added) => added.placeId === item.place.placeId,
                        ) ||
                        !item.feasible ||
                        trip.addingPlace ||
                        item.place.price.amount > (trip.displayBudget?.remaining ?? 0)
                      }
                      onClick={(event) => {
                        event.stopPropagation();
                        trip.addRecommendation(item);
                      }}
                      className="rounded-full"
                    >
                      <Plus />
                      {trip.displayItinerary.some((added) => added.placeId === item.place.placeId)
                        ? "Added to today"
                        : "Add to today"}
                    </Button>
                    {item.place.mapsUrl && (
                      <Button asChild variant="outline" className="rounded-full">
                        <a href={item.place.mapsUrl} target="_blank" rel="noreferrer">
                          Open in Maps <ExternalLink />
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </motion.article>
          ))}
        </div>
        <div className="xl:sticky xl:top-28 xl:h-fit">
          <TripMap
            items={[]}
            recommendations={liveRecommendations}
            selectedId={selected}
            onSelect={setSelected}
          />
        </div>
      </div>
    </>
  );
}

function TripMap({
  selectedId,
  onSelect,
  items,
  recommendations = [],
  compact = false,
}: {
  selectedId: string | null;
  onSelect: (id: string) => void;
  items: ItineraryItem[];
  recommendations?: PlaceRecommendation[];
  compact?: boolean;
}) {
  const pins = recommendations.length
    ? recommendations.map((item) => ({ id: item.place.placeId, label: item.place.name }))
    : items.map((item) => ({ id: item.id, label: item.title }));
  const visiblePins = pins.slice(0, 12);
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border bg-sky/45",
        compact ? "min-h-[520px]" : "min-h-[440px]",
      )}
    >
      <div
        className="absolute inset-0 opacity-55"
        style={{
          backgroundImage:
            "linear-gradient(31deg, transparent 47%, color-mix(in oklab,var(--background) 70%,transparent) 48% 52%, transparent 53%), linear-gradient(115deg, transparent 45%, color-mix(in oklab,var(--aqua) 45%,transparent) 46% 55%, transparent 56%)",
          backgroundSize: "110px 95px, 170px 130px",
        }}
      />
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 600 440"
        preserveAspectRatio="none"
      >
        <path
          d="M120 300 C210 240 160 150 230 160 S355 300 415 240"
          fill="none"
          stroke="var(--coral)"
          strokeWidth="4"
          strokeDasharray="9 12"
          className="route-motion"
        />
        <path
          d="M230 160 C300 205 310 265 420 320"
          fill="none"
          stroke="var(--foreground)"
          strokeOpacity=".18"
          strokeWidth="3"
          strokeDasharray="6 11"
        />
      </svg>
      <div className="absolute left-5 top-5 z-10 rounded-2xl border bg-card/95 p-3 shadow-sm">
        <p className="text-xs font-bold uppercase text-muted-foreground">Illustrative route view</p>
        <p className="mt-1 font-bold">{visiblePins.length} visible stops</p>
      </div>
      {visiblePins.map((pin, index) => (
        <button
          key={pin.id}
          onClick={() => onSelect(pin.id)}
          style={{ left: `${17 + (index % 4) * 22}%`, top: `${31 + Math.floor(index / 4) * 22}%` }}
          aria-label={`Select ${pin.label}`}
          className="absolute z-20 -translate-x-1/2 -translate-y-1/2"
        >
          <span
            className={cn(
              "flex size-10 items-center justify-center rounded-full border-4 border-card text-sm font-bold shadow-lg transition",
              selectedId === pin.id
                ? "scale-110 bg-primary text-primary-foreground"
                : "bg-card text-foreground",
            )}
          >
            {index + 1}
          </span>
          <span className="mt-1 block max-w-24 truncate rounded-full bg-card/90 px-2 py-1 text-xs font-bold shadow-sm">
            {pin.label}
          </span>
        </button>
      ))}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-2xl border bg-card/95 p-3 text-sm">
        <span className="flex items-center gap-2">
          <LocateFixed className="size-4 text-primary" /> Map preview unavailable
        </span>
        <span className="font-bold">See itinerary for travel times</span>
      </div>
    </div>
  );
}

function BookingLinkButton({ url }: { url: string | undefined }) {
  if (!url || !/^https:\/\//i.test(url))
    return <span className="text-sm text-muted-foreground">Booking link unavailable</span>;
  return (
    <Button asChild className="rounded-full">
      <a href={url} target="_blank" rel="noopener noreferrer">
        View & Book <ExternalLink />
      </a>
    </Button>
  );
}

function Flights() {
  const { plan, selectOption } = useTrip();
  const options = plan?.flights ?? [];
  return (
    <>
      <SectionHeading
        eyebrow={`${plan?.trip.constraints.origin ?? "Origin"} to ${plan?.trip.constraints.destination ?? "destination"}`}
        title="Flights that fit your trip"
        copy={`${plan?.sources.flights ?? "Demo"} provider options. Prices may change before external booking.`}
      />
      {!options.length && (
        <p className="rounded-3xl border bg-card p-6">
          No flight options are available for this plan.
        </p>
      )}
      <div className="space-y-4">
        {options.map((option) => (
          <article
            key={option.id}
            className="grid gap-5 rounded-[28px] border bg-card p-5 md:grid-cols-[170px_1fr_auto] md:items-center"
          >
            <div>
              <span className="rounded-full bg-lavender px-3 py-1 text-xs font-bold">
                {option.provider} data
              </span>
              <p className="mt-4 text-xl font-bold">{option.airline}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {option.departureAirport} → {option.arrivalAirport} ·{" "}
                {option.stops === 0 ? "Direct" : `${option.stops} stop(s)`}
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold">
                {formatTime(option.departureTime)} → {formatTime(option.arrivalTime)}
              </p>
              <p className="text-sm text-muted-foreground">
                {formatDuration(option.durationMinutes)}
              </p>
              <div className="mt-3 rounded-2xl bg-muted p-3 text-sm">
                <Sparkles className="mr-2 inline size-4 text-primary" />
                Retrieved {new Date(option.retrievedAt).toLocaleString()}; confirm details with the
                provider.
              </div>
            </div>
            <div className="md:text-right">
              <p className="text-2xl font-bold">₹{option.price.amount.toLocaleString("en-IN")}</p>
              <BookingLinkButton url={option.bookingUrl} />
              <Button
                className="mt-2 rounded-full"
                variant={
                  plan?.selections.some(
                    (selection) =>
                      selection.optionId === option.id &&
                      selection.selectionType === "selected_flight",
                  )
                    ? "secondary"
                    : "outline"
                }
                onClick={() => void selectOption(option.id, "selected_flight")}
              >
                Select this flight
              </Button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function Hotels() {
  const { plan, selectOption } = useTrip();
  const hotels = plan?.hotels ?? [];
  return (
    <>
      <SectionHeading
        eyebrow="Stay shortlist"
        title="A good base changes everything"
        copy={`${plan?.sources.hotels ?? "Demo"} provider options. Check current prices before booking externally.`}
      />
      {!hotels.length && (
        <p className="rounded-3xl border bg-card p-6">
          No hotel options are available for this plan.
        </p>
      )}
      <div className="grid gap-5 lg:grid-cols-3">
        {hotels.map((hotel) => (
          <article key={hotel.id} className="overflow-hidden rounded-[28px] border bg-card">
            <div
              className="aspect-[4/3] bg-[radial-gradient(circle_at_25%_30%,var(--aqua),transparent_50%),linear-gradient(125deg,var(--sky),var(--butter))]"
              aria-hidden="true"
            />
            <div className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-primary">{hotel.provider} data</p>
                <span className="font-bold">
                  <Star className="mr-1 inline size-4 fill-current text-primary" />
                  {hotel.rating ?? "Not rated"}
                </span>
              </div>
              <h3 className="mt-2 text-xl font-bold">{hotel.name}</h3>
              <p className="text-sm text-muted-foreground">
                {hotel.amenities.length ? hotel.amenities.join(" · ") : "Amenities not supplied"}
              </p>
              <p className="mt-4 text-xl font-bold">
                ₹{hotel.totalPrice.amount.toLocaleString("en-IN")} total
              </p>
              <p className="text-sm text-muted-foreground">
                {hotel.nightlyPrice
                  ? `₹${hotel.nightlyPrice.amount.toLocaleString("en-IN")}/night`
                  : "Nightly price unavailable"}
              </p>
              <div className="my-4 rounded-2xl bg-lavender/35 p-3 text-sm">
                <Sparkles className="mr-2 inline size-4 text-primary" />
                Retrieved {new Date(hotel.retrievedAt).toLocaleString()}; confirm availability with
                the provider.
              </div>
              <BookingLinkButton url={hotel.bookingUrl} />
              <Button
                className="mt-2 w-full rounded-full"
                variant={
                  plan?.selections.some(
                    (selection) =>
                      selection.optionId === hotel.id &&
                      selection.selectionType === "selected_hotel",
                  )
                    ? "secondary"
                    : "outline"
                }
                onClick={() => void selectOption(hotel.id, "selected_hotel")}
              >
                Select this stay
              </Button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function MapView() {
  const trip = useTrip();
  return (
    <>
      <SectionHeading
        eyebrow="Route overview"
        title="Your trip, spatially"
        copy="Select a stop on either side to keep the day and map in sync."
      />
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <div className="order-2 space-y-3 lg:order-1">
          {trip.displayItinerary.map((stop, index) => (
            <button
              key={stop.id}
              onClick={() => trip.setSelectedStopId(stop.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-3xl border bg-card p-3 text-left",
                trip.selectedStopId === stop.id && "border-primary",
              )}
            >
              <span className="flex size-9 items-center justify-center rounded-full bg-primary font-bold text-primary-foreground">
                {index + 1}
              </span>
              <div>
                <p className="font-bold">{stop.title}</p>
                <p className="text-sm text-muted-foreground">
                  {formatTime(stop.startAt)} · {stop.category}
                </p>
              </div>
            </button>
          ))}
        </div>
        <div className="order-1 lg:order-2">
          <TripMap
            items={trip.displayItinerary}
            selectedId={trip.selectedStopId}
            onSelect={trip.setSelectedStopId}
          />
        </div>
      </div>
    </>
  );
}

function Budget() {
  const { plan, displayBudget: budget } = useTrip();
  if (!plan || !budget) return null;
  const limit = plan.trip.constraints.budget.amount;
  const total = budget.total;
  const remaining = budget.remaining;
  const rows = [
    { label: "Flights", amount: budget.transport, color: "bg-sky" },
    { label: "Hotel", amount: budget.hotel, color: "bg-lavender" },
    { label: "Food estimate", amount: budget.food, color: "bg-butter" },
    { label: "Activities", amount: budget.activities, color: "bg-aqua" },
    { label: "Local travel estimate", amount: budget.localTransport, color: "bg-peach" },
  ].map((row) => ({
    ...row,
    value: `₹${row.amount.toLocaleString("en-IN")}`,
    pct: limit > 0 ? Math.round((row.amount / limit) * 100) : 0,
  }));
  return (
    <>
      <SectionHeading
        eyebrow="Budget guardrail"
        title={`₹${total.toLocaleString("en-IN")} / ₹${limit.toLocaleString("en-IN")}`}
        copy={
          remaining >= 0
            ? `₹${remaining.toLocaleString("en-IN")} remains in your budget.`
            : `Over budget by ₹${Math.abs(remaining).toLocaleString("en-IN")}.`
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
        <section className="rounded-[28px] border bg-card p-6 md:p-8">
          <div className="flex h-7 overflow-hidden rounded-full">
            {rows.map((row) => (
              <div key={row.label} className={row.color} style={{ width: `${row.pct}%` }} />
            ))}
            <div
              className="bg-muted"
              style={{
                width: `${Math.max(0, 100 - rows.reduce((sum, row) => sum + row.pct, 0))}%`,
              }}
            />
          </div>
          <div className="mt-8 space-y-5">
            {rows.map((row) => (
              <div key={row.label} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={cn("size-4 rounded-full", row.color)} />
                  <span className="font-semibold">{row.label}</span>
                </div>
                <div className="text-right">
                  <p className="font-bold">{row.value}</p>
                  <p className="text-sm text-muted-foreground">{row.pct}%</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <div className="space-y-5">
          <BudgetMeter />
          <div className="rounded-3xl border bg-lavender/40 p-6">
            <Sparkles className="text-primary" />
            <p className="mt-4 text-lg font-bold">TripPilot insight</p>
            <p className="mt-2 leading-7 text-muted-foreground">
              Your hotel uses {limit > 0 ? Math.round((budget.hotel / limit) * 100) : 0}% of the
              budget.{" "}
              {remaining >= 0
                ? `You have ₹${remaining.toLocaleString("en-IN")} left.`
                : "The current plan exceeds your budget."}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function Alerts() {
  const trip = useTrip();
  const weatherAlerts = trip.plan?.weather?.alerts ?? [];
  const freeWindow = trip.activeFreeTimeWindow;
  const alerts = [
    {
      icon: Plane,
      tone: "bg-peach/55",
      title: "Demo: simulate a flight delay",
      copy: "Preview a sample disruption comparison. It does not monitor flights or change this itinerary.",
      action: "Preview demo",
      target: "demo",
    },
    ...weatherAlerts.map((alert) => ({
      icon: CloudSun,
      tone: "bg-sky/55",
      title: alert.headline,
      copy: [alert.severity, alert.areas].filter(Boolean).join(" · ") || "Weather provider alert",
      action: "View itinerary",
      target: "itinerary",
    })),
    ...(freeWindow
      ? [
          {
            icon: Sparkles,
            tone: "bg-butter/55",
            title: `${Math.floor(freeWindow.durationMinutes / 60)}h ${freeWindow.durationMinutes % 60}m free time available`,
            copy: "Route-aware nearby recommendations are ready to check.",
            action: "Explore places",
            target: "explore",
          },
        ]
      : []),
  ];
  return (
    <>
      <SectionHeading
        eyebrow="Trip monitor"
        title="Things worth your attention"
        copy="Every update explains what changes in the actual trip."
      />
      <div className="space-y-4">
        {alerts.map(({ icon: Icon, tone, title, copy, action, target }, index) => (
          <article
            key={title}
            className={cn(
              "flex flex-col gap-4 rounded-[28px] border p-5 md:flex-row md:items-center",
              tone,
            )}
          >
            <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-card">
              <Icon className="size-5" />
            </span>
            <div className="flex-1">
              <h3 className="text-lg font-bold">{title}</h3>
              <p className="mt-1 text-muted-foreground">{copy}</p>
            </div>
            <Button
              variant={index === 0 ? "default" : "outline"}
              onClick={() =>
                target === "demo"
                  ? trip.setDelayOpen(true)
                  : trip.setView(target === "explore" ? "explore" : "itinerary")
              }
              className="rounded-full"
            >
              {action}
              <ChevronRight />
            </Button>
          </article>
        ))}
      </div>
    </>
  );
}

function ReplanComparison() {
  const trip = useTrip();
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") trip.setDelayOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [trip]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[70] flex items-end justify-center bg-foreground/30 p-0 backdrop-blur-sm md:items-center md:p-5"
      onClick={() => trip.setDelayOpen(false)}
      role="presentation"
    >
      <motion.section
        role="dialog"
        aria-modal="true"
        aria-labelledby="replan-title"
        aria-describedby="replan-description"
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        onClick={(event) => event.stopPropagation()}
        className="max-h-[92vh] w-full max-w-3xl overflow-auto rounded-t-[28px] border bg-background p-5 shadow-2xl md:rounded-[28px] md:p-8"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-peach">
              <AlertTriangle />
            </span>
            <div>
              <p className="text-sm font-bold uppercase text-primary">Demo disruption preview</p>
              <h2 id="replan-title" className="mt-1 text-3xl font-bold">
                Sample flight delay: 4h 05m
              </h2>
              <p id="replan-description" className="mt-2 text-muted-foreground">
                This example does not alter your actual trip.
              </p>
            </div>
          </div>
          <button
            aria-label="Close"
            onClick={() => trip.setDelayOpen(false)}
            className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted"
          >
            <X />
          </button>
        </div>
        <div className="mt-7 grid gap-4 md:grid-cols-2">
          <ScheduleColumn
            title="ORIGINAL"
            faded
            rows={trip.displayItinerary
              .slice(0, 4)
              .map((item) => `${formatTime(item.startAt)}  ${item.title}`)}
          />
          <ScheduleColumn
            title="UPDATED"
            rows={[
              "Sample: arrival delayed",
              "Affected stops need route and budget checks",
              "A real revision would require your approval",
            ]}
          />
        </div>
        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            onClick={() => trip.setDelayOpen(false)}
            className="rounded-full"
          >
            Keep original
          </Button>
          <Button onClick={() => trip.setDelayOpen(false)} className="rounded-full">
            Close preview <ArrowRight />
          </Button>
        </div>
      </motion.section>
    </motion.div>
  );
}

function ScheduleColumn({
  title,
  rows,
  faded = false,
}: {
  title: string;
  rows: string[];
  faded?: boolean;
}) {
  return (
    <div className={cn("rounded-3xl border bg-card p-5", faded && "opacity-55")}>
      <p className="text-xs font-bold text-muted-foreground">{title}</p>
      <div className="mt-4 space-y-3">
        {rows.map((row, index) => (
          <div key={row} className="flex items-center gap-3 rounded-xl bg-muted/60 p-3">
            <span
              className={cn("size-2 rounded-full", index === 1 ? "bg-primary" : "bg-foreground")}
            />
            <span className="font-semibold">{row}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TripPilotApp() {
  const { stage, tripLoadError } = useTrip();
  const auth = useAuth();
  const location = useLocation();
  if (auth.loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
        Restoring your session…
      </main>
    );
  }
  if (location.pathname.startsWith("/trips/") && tripLoadError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4">
        <p role="alert">Trip not found or you don't have access.</p>
        <Button asChild>
          <a href="/">Back to your trips</a>
        </Button>
      </main>
    );
  }
  if (location.pathname.startsWith("/trips/") && auth.user && stage !== "trip") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
        Loading your trip…
      </main>
    );
  }
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={stage}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {stage === "prompt" ? (
          <TripPrompt />
        ) : stage === "planning" ? (
          <AgentProgress />
        ) : (
          <AppShell />
        )}
      </motion.div>
    </AnimatePresence>
  );
}
