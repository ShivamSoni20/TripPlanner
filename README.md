# TripPilot

TripPilot is a stateful AI travel operating system. A traveler describes a goal in natural language; TripPilot gathers provider data, applies deterministic schedule and budget rules, produces a coherent trip, and keeps booking decisions with the user.

The repository preserves the original Sunlit Cartography + Soft Bento interface while adding a typed FastAPI/LangGraph backend, provider boundaries, deterministic validation, a Supabase schema, tests, and CI.

> Default provider status: **demo mode**. Flight and hotel inventory remains deterministic demo data for the Indore–Goa fixture only. Amadeus Self-Service and Booking.com Demand API v3.2 adapters are available behind explicit server-only credentials but have not been live-verified here. Places, routes, and weather also have server-side live adapters when configured. No provider key is shipped in this repository.

## What works

- Natural-language trip submission from the existing UI
- FastAPI planning API invoked through a real LangGraph workflow
- OpenRouter strict structured extraction in live mode, including one bounded validation retry
- Structured follow-up questions when critical trip fields are missing
- Concurrent typed flight, hotel, and place providers
- Amadeus Flight Offers adapter with OAuth token caching, provider-backed airport/city resolution, normalized offers, and no invented booking links
- Booking.com Demand API v3.2 accommodation adapter with location resolution, bounded inventory, server-only auth headers, and provider-returned redirect validation
- Google Places API (New) adapter for destination, nearby, and details lookup
- Google Routes adapter for route and matrix duration checks; missing routes are never treated as a guessed duration
- WeatherAPI adapter with normalized daily/hourly forecasts and alerts; dates 14 or more days ahead return `not_available_yet`
- Smart Explorer combines backend Places, Routes, opening-hour checks, hard time/budget feasibility, and weather suitability
- Explorer cards and Route Thread render normalized backend results; filters issue distinct backend queries
- Add to Today revalidates a server-derived free window and persists a versioned itinerary mutation
- Supabase email magic-link and Google OAuth UI, recent trips, and reloadable `/trips/{id}` URLs
- Centralized domain models and deterministic budget/schedule validation
- Free-time feasibility, place scoring, and outbound-link security services
- Shared frontend plan state and recoverable backend error UI
- Responsive existing views for trip, explorer, inventory, map, budget, alerts, and re-planning
- Supabase ownership RLS migration, request-scoped user JWT Data API access, and atomic add/undo functions
- Explicit, versioned flight/hotel selection and optional external-booking confirmation; no payment credentials are collected
- Cheap `/api/v1/ready` configuration readiness endpoint and no canned planning SSE/progress events
- Backend unit/API tests and frontend/backend CI

## Architecture

```text
TanStack Start + React
        │ typed REST
        ▼
FastAPI → LangGraph planning workflow
              ├── provider contracts (demo/live)
              └── deterministic planning services
        │
        ▼
Supabase Auth + PostgreSQL (user-scoped RLS)
```

OpenRouter performs structured constraint extraction when live mode is configured. Providers supply facts; deterministic code owns arithmetic, time, route feasibility, opening-hour checks, and URL safety. Booking occurs externally. The current disruption comparison is an explicitly labeled demo preview and does not modify a plan.

Read [architecture](docs/architecture.md), [agent design](docs/agent-system.md), [evaluation](docs/evaluation.md), [failure analysis](docs/failure-analysis.md), and the [repository audit](docs/codebase-audit.md).

## Local development

Prerequisites: Node.js 22+ and Python 3.12+.

```powershell
Copy-Item .env.example .env
npm ci
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
```

Run the API:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Run the frontend separately:

```powershell
npm run dev
```

The browser defaults to `http://localhost:8000`; override it with `VITE_TRIPPILOT_API_URL`. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` for browser sign-in and matching backend `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` for verified JWT and user-scoped persistence. Enable email OTP and/or Google OAuth and allow your frontend callback origin in Supabase Auth.

## Environment and security

Copy `.env.example` and fill only the providers you use. Key settings include `TRAVEL_DATA_MODE`, `PLACES_PROVIDER`, OpenRouter/model values, database/Supabase values, Google and weather credentials, optional travel inventory credentials, and LangSmith observability values. For Google mode, enable Places API (New), restrict the key to that API and the deployed backend where practical, then set `GOOGLE_MAPS_API_KEY` server-side.

The frontend never receives the service-role key and cannot choose `user_id`. FastAPI verifies the bearer token with Supabase Auth, then creates a new Data API client with that user's JWT for each request. Database RLS independently enforces ownership; a copied trip ID alone grants no access. The service-role key is reserved for trusted administration and is not used for trip CRUD. Never expose provider secrets through `VITE_` variables.

## Quality checks

```powershell
npm run lint
npm run typecheck
npm run build
backend/.venv/Scripts/python.exe -m ruff format --check backend
backend/.venv/Scripts/python.exe -m ruff check backend
backend/.venv/Scripts/python.exe -m pytest backend -q
```

The backend suite contains correctness and API tests. See [evaluation](docs/evaluation.md) for the latest measured count. Benchmark percentages are omitted until the full scenario evaluation suite is executed.

## Database

Apply all migrations under `supabase/migrations/` in order. The Phase F migration adds bounded selection types, an event dedupe key, and a security-invoker `set_trip_selection` RPC. It stops neither existing data nor RLS; it does require applying to a real Supabase project before selection persistence can be live-tested. The local environment has no TripPilot Supabase project or credentials, so these SQL changes have not been applied or live-tested here.

## Deployment

- Deploy the frontend to Vercel or another TanStack Start-compatible runtime and set `VITE_TRIPPILOT_API_URL`.
- Deploy `backend/` to Railway, Render, or another ASGI host using `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Connect a TripPilot Supabase project, apply both migrations, and configure email/Google Auth redirect URLs before enabling persistence.
- Restrict backend CORS to deployed frontend origins.

## Known limitations

- Demo mode intentionally maps requests to the deterministic Goa evaluation fixture; live mode uses OpenRouter extraction.
- Google Places and Routes require `GOOGLE_MAPS_API_KEY`; WeatherAPI requires `WEATHER_API_KEY`. Live calls have not been verified on this host because those keys are unavailable.
- Amadeus and Booking adapters are implemented and mock-tested but live/sandbox verification is blocked on credentials and partner access.
- The map is an explicitly schematic visual, not geographic rendering.
- The authenticated persistence code and RLS migration are implemented but live Supabase sign-in, two-user RLS, and browser reload flows could not be verified without a TripPilot project and credentials. Fake-repository tests are not live RLS proof.
- The disruption view is a demo preview, not a persisted re-plan. Full evaluations and browser end-to-end tests remain incomplete.

TripPilot never processes payments or issues tickets. Purchases happen on approved external provider sites.
