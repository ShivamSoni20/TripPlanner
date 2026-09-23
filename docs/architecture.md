# TripPilot architecture

TripPilot keeps the existing TanStack Start/React interface and places all factual travel access and planning rules behind a FastAPI service.

## Runtime boundaries

- **Frontend:** TanStack Start, React 19, TanStack Router, Tailwind CSS, and the existing shadcn-based design system. `src/lib/trip-api.ts` is the browser's only planning boundary.
- **Backend:** FastAPI exposes versioned REST endpoints. API keys and provider credentials remain server-side.
- **Agent:** LangGraph owns the stateful planning transition. It delegates factual retrieval to typed providers and correctness checks to deterministic services.
- **Providers:** flights and hotels use deterministic Indore–Goa demo fixtures; Places, Routes, and Weather use demo or configured server-side live adapters.
- **Places:** `PLACES_PROVIDER=demo` uses deterministic fixtures; `PLACES_PROVIDER=google` selects Places API (New) Text Search, Nearby Search, and Place Details through a focused server-side client. Google payloads are normalized before entering graph state.
- **Routes:** `ROUTES_PROVIDER=google` uses Google Routes and matrix responses. Missing or invalid durations fail closed.
- **Weather:** `WEATHER_PROVIDER=weatherapi` uses WeatherAPI. Forecasts beyond the 14-day horizon report `not_available_yet` without an API call.
- **Planning services:** budget arithmetic, schedule validation, opening-hour checks, free-time feasibility, weather suitability, and outbound URL validation do not depend on an LLM.
- **Identity:** browser Supabase Auth obtains a session; FastAPI calls Auth `get_user(jwt)` before protected operations.
- **Database:** each FastAPI request creates a Supabase Data API client authenticated with that user's JWT. The second migration grants authenticated access and RLS restricts root and child rows to owned trips. The service-role key is never used for ordinary trip CRUD.

## Request flow

1. The existing trip prompt calls `POST /api/v1/trips/plan`.
2. FastAPI builds a typed planning state and invokes the LangGraph workflow.
3. Independent provider searches run concurrently. Flight and hotel searches remain demo-only.
4. The planner creates itinerary candidates and runs schedule and budget validation.
5. The validated `TripPlan` is persisted as an owned root trip, preferences, options, and itinerary before it is returned.
6. Direct `/trips/{id}` navigation rehydrates the normalized plan. Explorer loads server state; Add to Today rechecks version, window, route, schedule and budget before an atomic security-invoker mutation increments the version.

```text
React / TanStack Query
    ↓ typed REST normalization
FastAPI → LangGraph → TripPlanner
                       ├── FlightsProvider (demo)
                       ├── HotelProvider (demo)
                       ├── PlacesProvider (demo / Google)
                       ├── RoutesProvider (demo / Google)
                       └── WeatherProvider (demo / WeatherAPI)

TimeWindow → nearby Places → route matrix → opening-hour check
           → hard time and budget filters → weather filter → ranking → Explorer UI
```

## Deployment shape

The frontend can deploy to Vercel or Cloudflare-compatible hosting. The Python service can deploy to Railway, Render, or another ASGI host. Configure the frontend with `VITE_TRIPPILOT_API_URL` and the Supabase publishable browser values; configure the backend with Supabase URL/publishable key and server-side provider secrets described in `.env.example`. The Phase E migration still requires deployment and live RLS verification.

No browser code calls OpenRouter, Google, flight, hotel, weather, or Supabase service-role APIs directly.

## Google Places cost and security boundary

TripPilot uses explicit search and detail field masks rather than `*`. Search asks only for stable identity, display name, coordinates, types, rating counts, address, price level, current opening hours, and the provider-returned Maps URI. Place Details is called only when a caller explicitly needs details; search results are not expanded with an N+1 request pattern. Field masks affect Google Places billing, so new fields require a product need and review.

The web-service API key exists only as `GOOGLE_MAPS_API_KEY` on the backend. Production Google Cloud credentials should be restricted to Places API (New) and to the deployed backend where practical. Returned Maps URLs pass the outbound HTTPS host validator. Curated repository photography remains in the UI; Google Place Photos are intentionally out of scope for this phase.
