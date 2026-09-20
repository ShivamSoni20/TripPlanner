import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
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
  view: TripView;
  setView: (value: TripView) => void;
  selectedStop: number;
  setSelectedStop: (value: number) => void;
  addedFort: boolean;
  addFort: () => void;
  delayOpen: boolean;
  setDelayOpen: (value: boolean) => void;
  replanned: boolean;
  acceptReplan: () => void;
};

const TripContext = createContext<TripContextValue | null>(null);

export function TripProvider({ children }: { children: ReactNode }) {
  const [stage, setStage] = useState<AppStage>("prompt");
  const [view, setView] = useState<TripView>("overview");
  const [selectedStop, setSelectedStop] = useState(2);
  const [addedFort, setAddedFort] = useState(false);
  const [delayOpen, setDelayOpen] = useState(false);
  const [replanned, setReplanned] = useState(false);
  const value = useMemo(
    () => ({
      stage,
      setStage,
      view,
      setView,
      selectedStop,
      setSelectedStop,
      addedFort,
      addFort: () => setAddedFort(true),
      delayOpen,
      setDelayOpen,
      replanned,
      acceptReplan: () => {
        setReplanned(true);
        setDelayOpen(false);
        setView("itinerary");
      },
    }),
    [stage, view, selectedStop, addedFort, delayOpen, replanned],
  );
  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
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
  const { setStage } = useTrip();
  const [query, setQuery] = useState(
    "Goa for 5 days, two people, ₹30k. Beaches, nightlife and history. Keep it relaxed.",
  );
  const chips = ["Goa under ₹30k", "Weekend escape", "Mountains", "Beaches", "Surprise me"];
  return (
    <main className="relative min-h-screen overflow-hidden bg-background px-5 py-6">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Brand />
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Compass className="size-4" /> Your trips
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
            if (query.trim()) setStage("planning");
          }}
        >
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

const planningSteps = [
  ["Understanding your preferences", ""],
  ["Searching flights", "18 options found"],
  ["Comparing hotels", "24 options found"],
  ["Finding places", "31 places found"],
  ["Checking weather", "Clear skies, 29°"],
  ["Calculating travel times", "12 routes checked"],
  ["Optimizing itinerary", ""],
  ["Validating ₹30,000 budget", ""],
];

export function AgentProgress() {
  const { setStage } = useTrip();
  const [active, setActive] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(
      () =>
        setActive((current) => {
          if (current >= planningSteps.length - 1) {
            window.clearInterval(timer);
            window.setTimeout(() => setStage("trip"), 850);
            return current;
          }
          return current + 1;
        }),
      520,
    );
    return () => window.clearInterval(timer);
  }, [setStage]);
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
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
            Planning your Goa adventure
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Connecting the details so every day flows naturally.
          </p>
          <div className="mt-10 space-y-3">
            {planningSteps.map(([label, result], index) => (
              <motion.div
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: index <= active ? 1 : 0.36, x: 0 }}
                key={label}
                className="flex items-center gap-4 rounded-2xl border bg-card px-4 py-3"
              >
                <span
                  className={cn(
                    "flex size-7 items-center justify-center rounded-full",
                    index < active
                      ? "bg-mint"
                      : index === active
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted",
                  )}
                >
                  {index < active ? (
                    <Check className="size-4" />
                  ) : index === active ? (
                    <span className="size-2 animate-pulse rounded-full bg-primary-foreground" />
                  ) : (
                    <span className="size-2 rounded-full border" />
                  )}
                </span>
                <div>
                  <p className="font-semibold">{label}</p>
                  {result && index < active && (
                    <p className="text-sm text-muted-foreground">{result}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
        <TripMap compact selected={Math.min(active + 1, 5)} onSelect={() => undefined} />
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
              <p className="text-sm font-semibold">Goa · 5 days</p>
              <p className="text-xs text-muted-foreground">12–17 Nov</p>
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
  const { setView } = useTrip();
  return (
    <section className="relative min-h-[390px] overflow-hidden rounded-[28px] text-primary-foreground">
      <img
        src={goaHero}
        width={1600}
        height={1000}
        className="absolute inset-0 h-full w-full object-cover"
        alt="Sunlit coastal view across Goa"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,color-mix(in_oklab,var(--foreground)_82%,transparent),transparent_78%)]" />
      <div className="relative flex min-h-[390px] max-w-2xl flex-col justify-end p-6 md:p-10">
        <div className="mb-auto flex w-fit items-center gap-2 rounded-full bg-background/90 px-3 py-2 text-sm font-semibold text-foreground">
          <span className="size-2 rounded-full bg-aqua" /> Trip ready · all systems checked
        </div>
        <p className="text-sm font-bold uppercase">India · 12–17 November</p>
        <h1 className="mt-2 text-6xl font-bold md:text-8xl">GOA</h1>
        <div className="mt-5 flex flex-wrap gap-3 text-sm font-semibold">
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <CalendarDays className="mr-2 inline size-4" />5 days
          </span>
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <Users className="mr-2 inline size-4" />2 travellers
          </span>
          <span className="rounded-full bg-background/15 px-3 py-2 backdrop-blur">
            <CloudSun className="mr-2 inline size-4" />
            29° · Sunny
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
  return (
    <div className={cn("rounded-3xl border bg-mint/45", compact ? "p-5" : "p-6")}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-muted-foreground">Trip budget</p>
          <p className="mt-1 text-2xl font-bold">
            ₹28,450 <span className="text-base font-medium text-muted-foreground">/ ₹30,000</span>
          </p>
        </div>
        <span className="rounded-full bg-card px-3 py-1 text-sm font-bold">₹1,550 left</span>
      </div>
      <Progress value={94.8} className="mt-5 h-2.5 bg-card [&>div]:bg-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">On track, with a 5% buffer.</p>
    </div>
  );
}

function Overview() {
  const { setView, setDelayOpen } = useTrip();
  return (
    <div className="space-y-6">
      <TripHero />
      <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
        <div className="grid gap-6">
          <BudgetMeter />
          <button
            onClick={() => setView("explore")}
            className="group rounded-3xl border bg-butter/55 p-6 text-left transition hover:-translate-y-1"
          >
            <div className="flex items-start gap-4">
              <span className="flex size-11 items-center justify-center rounded-2xl bg-card text-primary">
                <Sparkles />
              </span>
              <div>
                <p className="font-display text-xl font-bold">You have 2h 45m free on Day 2</p>
                <p className="mt-2 text-muted-foreground">
                  I found three nearby places that fit before dinner in Panjim.
                </p>
                <span className="mt-5 inline-flex items-center gap-2 font-bold text-primary">
                  Explore free time{" "}
                  <ArrowRight className="size-4 transition group-hover:translate-x-1" />
                </span>
              </div>
            </div>
          </button>
          <button
            onClick={() => setDelayOpen(true)}
            className="flex items-center justify-between rounded-3xl border bg-peach/55 p-5 text-left"
          >
            <div className="flex items-center gap-3">
              <Plane className="size-5 text-primary" />
              <div>
                <p className="font-bold">Preview a real-world change</p>
                <p className="text-sm text-muted-foreground">
                  Simulate a delayed arrival and re-plan Day 1.
                </p>
              </div>
            </div>
            <ChevronRight />
          </button>
        </div>
        <TripMap
          selected={2}
          onSelect={(id) => {
            setView("itinerary");
          }}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <MiniStatus
          icon={Plane}
          label="Flight saved"
          value="IndiGo · 07:20"
          note="IDR → GOI · Direct"
        />
        <MiniStatus
          icon={Hotel}
          label="Stay selected"
          value="Casa Anjuna"
          note="₹8,250 · 5 nights"
        />
        <MiniStatus
          icon={Utensils}
          label="Up next"
          value="Dinner at 7:30 PM"
          note="Mum's Kitchen · Panjim"
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

const stops = [
  {
    id: 1,
    time: "09:00",
    title: "Breakfast",
    place: "Candolim",
    duration: "1h",
    image: hotelImage,
  },
  {
    id: 2,
    time: "10:30",
    title: "Fort Aguada",
    place: "Sinquerim",
    duration: "1h 15m",
    image: fortImage,
  },
  { id: 3, time: "19:30", title: "Dinner", place: "Panjim", duration: "1h 30m", image: beachImage },
];

function RouteThread() {
  const trip = useTrip();
  const shown = trip.addedFort ? stops : stops.filter((stop) => stop.id !== 2);
  return (
    <div className="relative space-y-2 pl-9 before:absolute before:bottom-12 before:left-[13px] before:top-10 before:w-px before:bg-border">
      {shown.map((stop, index) => (
        <div key={stop.id}>
          <button
            onClick={() => trip.setSelectedStop(stop.id)}
            className={cn(
              "relative flex w-full gap-4 rounded-3xl border bg-card p-4 text-left transition",
              trip.selectedStop === stop.id &&
                "border-primary shadow-[0_8px_30px_-18px_var(--coral)]",
            )}
          >
            <span
              className={cn(
                "absolute -left-[34px] top-7 z-10 flex size-7 items-center justify-center rounded-full border-4 border-background text-xs font-bold",
                trip.selectedStop === stop.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-foreground text-background",
              )}
            >
              {stop.id}
            </span>
            <img
              src={stop.image}
              loading="lazy"
              width={1200}
              height={900}
              className="h-24 w-24 rounded-2xl object-cover"
              alt=""
            />
            <div className="min-w-0 py-1">
              <p className="text-sm font-bold text-primary">{stop.time}</p>
              <h3 className="mt-1 text-lg font-bold">{stop.title}</h3>
              <p className="text-sm text-muted-foreground">
                {stop.place} · {stop.duration}
              </p>
            </div>
          </button>
          {index < shown.length - 1 && (
            <div className="my-3 ml-1 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
              <Navigation className="size-3.5" />
              {stop.id === 1 ? "12 min drive" : "28 min drive"}
            </div>
          )}
          {!trip.addedFort && stop.id === 1 && <FreeTimeCard />}
        </div>
      ))}
    </div>
  );
}

function FreeTimeCard() {
  const { setView } = useTrip();
  return (
    <button
      onClick={() => setView("explore")}
      className="relative my-3 w-full rounded-3xl border border-dashed border-primary/50 bg-butter/55 p-5 text-left"
    >
      <span className="absolute -left-[34px] top-6 z-10 flex size-7 items-center justify-center rounded-full border-4 border-background bg-butter">
        <Sparkles className="size-3 text-primary" />
      </span>
      <p className="text-sm font-bold text-primary">13:15–16:00</p>
      <p className="mt-1 text-xl font-bold">2h 45m free</p>
      <p className="mt-1 text-sm text-muted-foreground">
        TripPilot found 3 places that fit this window.
      </p>
      <span className="mt-4 inline-flex items-center gap-2 text-sm font-bold">
        Explore nearby <ArrowRight className="size-4" />
      </span>
    </button>
  );
}

function Itinerary() {
  const trip = useTrip();
  return (
    <>
      <SectionHeading
        eyebrow="Day 2 of 5"
        title={trip.replanned ? "North Goa · revised" : "North Goa"}
        copy={
          trip.addedFort
            ? "Fort Aguada fits naturally before dinner, with a 50-minute safety buffer."
            : "A relaxed morning, an open afternoon, and dinner across the Mandovi."
        }
      />
      <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
        <section className="rounded-[28px] border bg-background p-2 md:p-5">
          <RouteThread />
        </section>
        <div className="lg:sticky lg:top-28 lg:h-fit">
          <TripMap selected={trip.selectedStop} onSelect={trip.setSelectedStop} />
        </div>
      </div>
    </>
  );
}

const recommendations = [
  {
    rank: "BEST FIT",
    name: "Fort Aguada",
    category: "Historical landmark",
    rating: "4.5",
    from: "12 min away",
    visit: "1h 15m visit",
    next: "28 min → dinner",
    buffer: "Leaves 50 min buffer",
    cost: "₹100",
    image: fortImage,
  },
  {
    rank: "ALTERNATIVE",
    name: "Sinquerim Beach",
    category: "Beach",
    rating: "4.7",
    from: "15 min away",
    visit: "1h visit",
    next: "31 min → dinner",
    buffer: "Leaves 42 min buffer",
    cost: "Free",
    image: beachImage,
  },
  {
    rank: "QUICK OPTION",
    name: "Reis Magos Fort",
    category: "History & views",
    rating: "4.4",
    from: "18 min away",
    visit: "45 min visit",
    next: "14 min → dinner",
    buffer: "Leaves 1h 02m buffer",
    cost: "₹100",
    image: goaHero,
  },
];

function SmartExplorer() {
  const trip = useTrip();
  const [filter, setFilter] = useState("Best Fit");
  const [selected, setSelected] = useState(0);
  return (
    <>
      <SectionHeading
        eyebrow="Smart free-time explorer"
        title={trip.addedFort ? "Fort Aguada fits beautifully" : "You have 2h 45m free"}
        copy="You’re in Candolim. Dinner is at 7:30 PM in Panjim. Let’s make the most of it."
        action={
          <span className="rounded-full bg-butter px-4 py-2 text-sm font-bold">
            <Clock3 className="mr-2 inline size-4" />
            Ends safely by 6:40 PM
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
          {recommendations.map((item, index) => (
            <motion.article
              layout
              key={item.name}
              aria-current={selected === index ? "true" : undefined}
              className={cn(
                "min-w-[86vw] snap-center overflow-hidden rounded-[28px] border bg-card sm:min-w-[520px] xl:min-w-0",
                selected === index && "border-primary",
              )}
            >
              <div className="grid sm:grid-cols-[210px_1fr]">
                <img
                  src={item.image}
                  loading="lazy"
                  width={1200}
                  height={900}
                  className="h-52 w-full object-cover sm:h-full"
                  alt={item.name}
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
                      {item.rating}
                    </span>
                  </div>
                  <h3 className="mt-4 text-xl font-bold">{item.name}</h3>
                  <p className="text-sm text-muted-foreground">{item.category}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                    <span>
                      <Navigation className="mr-1 inline size-3.5" />
                      {item.from}
                    </span>
                    <span>
                      <Clock3 className="mr-1 inline size-3.5" />
                      {item.visit}
                    </span>
                    <span>{item.next}</span>
                    <span>{item.cost} estimated</span>
                  </div>
                  <p className="mt-3 font-semibold text-foreground">
                    <Check className="mr-1 inline size-4 text-primary" />
                    {item.buffer}
                  </p>
                  <div className="mt-4 rounded-2xl bg-lavender/35 p-3 text-sm">
                    <p className="font-bold">Why this works</p>
                    <p className="mt-1 text-muted-foreground">
                      Matches your interests · currently open · good weather · low route detour
                    </p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setSelected(index)}
                      className="rounded-full"
                    >
                      <MapPin /> Preview route
                    </Button>
                    <Button
                      disabled={trip.addedFort && index === 0}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (index === 0) trip.addFort();
                      }}
                      className="rounded-full"
                    >
                      <Plus />
                      {trip.addedFort && index === 0 ? "Added to today" : "Add to today"}
                    </Button>
                    <Button asChild variant="outline" className="rounded-full">
                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.name)}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open in Maps <ExternalLink />
                      </a>
                    </Button>
                  </div>
                </div>
              </div>
            </motion.article>
          ))}
        </div>
        <div className="xl:sticky xl:top-28 xl:h-fit">
          <TripMap
            selected={selected + 2}
            onSelect={(id) => setSelected(Math.max(0, id - 2))}
            candidates
          />
        </div>
      </div>
    </>
  );
}

function TripMap({
  selected,
  onSelect,
  compact = false,
  candidates = false,
}: {
  selected: number;
  onSelect: (id: number) => void;
  compact?: boolean;
  candidates?: boolean;
}) {
  const pins = [
    { id: 1, x: "20%", y: "68%", label: "You" },
    { id: 2, x: "38%", y: "36%", label: "Fort Aguada" },
    { id: 3, x: "69%", y: "54%", label: "Dinner" },
    { id: 4, x: "52%", y: "72%", label: "Beach" },
  ];
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
        <p className="text-xs font-bold uppercase text-muted-foreground">Route preview</p>
        <p className="mt-1 font-bold">Candolim → Panjim</p>
      </div>
      {pins.slice(0, candidates ? 4 : 3).map((pin) => (
        <button
          key={pin.id}
          onClick={() => onSelect(pin.id)}
          style={{ left: pin.x, top: pin.y }}
          aria-label={`Select ${pin.label}`}
          className="absolute z-20 -translate-x-1/2 -translate-y-1/2"
        >
          <span
            className={cn(
              "flex size-10 items-center justify-center rounded-full border-4 border-card text-sm font-bold shadow-lg transition",
              selected === pin.id
                ? "scale-110 bg-primary text-primary-foreground"
                : "bg-card text-foreground",
            )}
          >
            {pin.id}
          </span>
          <span className="mt-1 block whitespace-nowrap rounded-full bg-card/90 px-2 py-1 text-xs font-bold shadow-sm">
            {pin.label}
          </span>
        </button>
      ))}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-2xl border bg-card/95 p-3 text-sm">
        <span className="flex items-center gap-2">
          <LocateFixed className="size-4 text-primary" /> Real travel time included
        </span>
        <span className="font-bold">40 min total</span>
      </div>
    </div>
  );
}

function BookingLinkButton() {
  return (
    <Button asChild className="rounded-full">
      <a href="https://www.google.com/travel" target="_blank" rel="noreferrer">
        View & Book <ExternalLink />
      </a>
    </Button>
  );
}

function Flights() {
  const [offline, setOffline] = useState(false);
  const options = [
    {
      airline: "IndiGo",
      times: "07:20 → 09:05",
      duration: "1h 45m",
      price: "₹8,400",
      tag: "BEST BALANCE",
      note: "Direct morning flight · preserves most of Day 1 · ₹1,600 cheaper than fastest option",
    },
    {
      airline: "Air India Express",
      times: "14:10 → 18:25",
      duration: "4h 15m",
      price: "₹7,620",
      tag: "LOWEST PRICE",
      note: "One short stop · saves ₹780 · evening arrival",
    },
    {
      airline: "Vistara",
      times: "10:30 → 13:40",
      duration: "3h 10m",
      price: "₹9,180",
      tag: "MOST COMFORT",
      note: "One stop · checked bag included · easy midday arrival",
    },
  ];
  return (
    <>
      <SectionHeading
        eyebrow="Indore to Goa"
        title="Flights that fit your trip"
        copy="Ranked for total price, useful arrival time and how much of Day 1 you keep."
        action={
          <Button onClick={() => setOffline(!offline)} variant="outline" className="rounded-full">
            <RefreshCw />
            Test status
          </Button>
        }
      />
      {offline && (
        <div className="mb-5 flex items-start gap-3 rounded-3xl border bg-peach/50 p-5">
          <WifiOff />
          <div>
            <p className="font-bold">Flight search is temporarily unavailable</p>
            <p className="text-sm text-muted-foreground">
              Your hotel and itinerary results are still ready. These saved options remain visible.
            </p>
          </div>
        </div>
      )}
      <div className="space-y-4">
        {options.map((option, index) => (
          <article
            key={option.airline}
            className="grid gap-5 rounded-[28px] border bg-card p-5 md:grid-cols-[170px_1fr_auto] md:items-center"
          >
            <div>
              <span className="rounded-full bg-lavender px-3 py-1 text-xs font-bold">
                {option.tag}
              </span>
              <p className="mt-4 text-xl font-bold">{option.airline}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                IDR → GOI · {index === 0 ? "Direct" : "1 stop"}
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold">{option.times}</p>
              <p className="text-sm text-muted-foreground">{option.duration}</p>
              <div className="mt-3 rounded-2xl bg-muted p-3 text-sm">
                <Sparkles className="mr-2 inline size-4 text-primary" />
                {option.note}
              </div>
            </div>
            <div className="md:text-right">
              <p className="text-2xl font-bold">{option.price}</p>
              <p
                className={cn(
                  "mb-4 text-sm",
                  index === 2 ? "text-primary" : "text-muted-foreground",
                )}
              >
                {index === 2 ? "Price checked 38 min ago · refresh" : "Price checked 4 min ago"}
              </p>
              <BookingLinkButton />
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function Hotels() {
  const hotels = [
    {
      name: "Casa Anjuna",
      area: "Anjuna",
      price: "₹8,250 total",
      night: "₹1,650/night",
      rating: "4.7",
      reason:
        "Best location for your itinerary — 14 minutes average travel time to planned activities.",
    },
    {
      name: "The Heritage Panjim",
      area: "Fontainhas",
      price: "₹9,400 total",
      night: "₹1,880/night",
      rating: "4.6",
      reason: "Walkable evenings and the easiest access to Panjim dining.",
    },
    {
      name: "Candolim Garden House",
      area: "Candolim",
      price: "₹7,850 total",
      night: "₹1,570/night",
      rating: "4.5",
      reason: "Best value near the beach, with breakfast and flexible cancellation.",
    },
  ];
  return (
    <>
      <SectionHeading
        eyebrow="Stay shortlist"
        title="A good base changes everything"
        copy="Compared for price, quality and real travel time to your itinerary."
      />
      <div className="grid gap-5 lg:grid-cols-3">
        {hotels.map((hotel, index) => (
          <article key={hotel.name} className="overflow-hidden rounded-[28px] border bg-card">
            <img
              src={index === 1 ? goaHero : hotelImage}
              loading="lazy"
              width={1200}
              height={900}
              alt={hotel.name}
              className="aspect-[4/3] w-full object-cover"
            />
            <div className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-primary">
                  {index === 0 ? "BEST LOCATION" : index === 1 ? "CITY PICK" : "BEST VALUE"}
                </p>
                <span className="font-bold">
                  <Star className="mr-1 inline size-4 fill-current text-primary" />
                  {hotel.rating}
                </span>
              </div>
              <h3 className="mt-2 text-xl font-bold">{hotel.name}</h3>
              <p className="text-sm text-muted-foreground">
                {hotel.area} · Pool · Breakfast · Wi-Fi
              </p>
              <p className="mt-4 text-xl font-bold">{hotel.price}</p>
              <p className="text-sm text-muted-foreground">{hotel.night}</p>
              <div className="my-4 rounded-2xl bg-lavender/35 p-3 text-sm">
                <Sparkles className="mr-2 inline size-4 text-primary" />
                {hotel.reason}
              </div>
              <BookingLinkButton />
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
        eyebrow="Live route"
        title="Your trip, spatially"
        copy="Select a stop on either side to keep the day and map in sync."
      />
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <div className="order-2 space-y-3 lg:order-1">
          {stops.map((stop) => (
            <button
              key={stop.id}
              onClick={() => trip.setSelectedStop(stop.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-3xl border bg-card p-3 text-left",
                trip.selectedStop === stop.id && "border-primary",
              )}
            >
              <span className="flex size-9 items-center justify-center rounded-full bg-primary font-bold text-primary-foreground">
                {stop.id}
              </span>
              <div>
                <p className="font-bold">{stop.title}</p>
                <p className="text-sm text-muted-foreground">
                  {stop.time} · {stop.place}
                </p>
              </div>
            </button>
          ))}
        </div>
        <div className="order-1 lg:order-2">
          <TripMap selected={trip.selectedStop} onSelect={trip.setSelectedStop} />
        </div>
      </div>
    </>
  );
}

function Budget() {
  const rows = [
    { label: "Flights", value: "₹8,400", pct: 28, color: "bg-sky" },
    { label: "Hotel", value: "₹8,250", pct: 29, color: "bg-lavender" },
    { label: "Food", value: "₹5,400", pct: 18, color: "bg-butter" },
    { label: "Activities", value: "₹2,900", pct: 10, color: "bg-aqua" },
    { label: "Local travel", value: "₹3,500", pct: 12, color: "bg-peach" },
  ];
  return (
    <>
      <SectionHeading
        eyebrow="Budget guardrail"
        title="₹28,450 / ₹30,000"
        copy="You still have ₹1,550 for the spontaneous bits."
      />
      <div className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
        <section className="rounded-[28px] border bg-card p-6 md:p-8">
          <div className="flex h-7 overflow-hidden rounded-full">
            {rows.map((row) => (
              <div key={row.label} className={row.color} style={{ width: `${row.pct}%` }} />
            ))}
            <div className="bg-muted" style={{ width: "5%" }} />
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
              Your hotel uses 29% of the budget, but your current trip still has a ₹1,550 buffer.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function Alerts() {
  const trip = useTrip();
  const alerts = [
    {
      icon: Plane,
      tone: "bg-peach/55",
      title: "Your inbound flight may arrive 4h 05m late",
      copy: "Lunch and Fort Aguada are affected. I can preserve the beach and dinner, then move the fort to Day 3.",
      action: "Review new plan",
    },
    {
      icon: CloudSun,
      tone: "bg-sky/55",
      title: "Rain expected Thursday, 2–5 PM",
      copy: "Your beach visit is affected, but the Museum of Goa fits the same time window.",
      action: "See weather option",
    },
    {
      icon: Sparkles,
      tone: "bg-butter/55",
      title: "2h 45m opened up on Day 2",
      copy: "Three places safely fit between Candolim and your dinner in Panjim.",
      action: "Explore places",
    },
    {
      icon: RefreshCw,
      tone: "bg-muted",
      title: "One flight price is getting stale",
      copy: "The Vistara fare was checked 38 minutes ago. Refresh before booking externally.",
      action: "View flights",
    },
  ];
  return (
    <>
      <SectionHeading
        eyebrow="Trip monitor"
        title="Things worth your attention"
        copy="Every update explains what changes in the actual trip."
      />
      <div className="space-y-4">
        {alerts.map(({ icon: Icon, tone, title, copy, action }, index) => (
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
                index === 0
                  ? trip.setDelayOpen(true)
                  : trip.setView(index === 1 ? "itinerary" : index === 2 ? "explore" : "flights")
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
              <p className="text-sm font-bold uppercase text-primary">Plans changed</p>
              <h2 id="replan-title" className="mt-1 text-3xl font-bold">
                Your flight is arriving 4h 05m later
              </h2>
              <p id="replan-description" className="mt-2 text-muted-foreground">
                I rebuilt Day 1 so you don’t have to start from scratch.
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
            rows={["13:00  Lunch", "15:00  Fort Aguada", "18:00  Beach", "20:30  Dinner"]}
          />
          <ScheduleColumn
            title="UPDATED"
            rows={["15:00  Late lunch", "Fort Aguada → Day 3", "17:30  Beach", "20:30  Dinner ✓"]}
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
          <Button onClick={trip.acceptReplan} className="rounded-full">
            Use new plan <ArrowRight />
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
  const { stage } = useTrip();
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
