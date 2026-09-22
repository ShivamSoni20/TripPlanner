# TripPilot

TripPilot is a stateful AI travel operating system. A traveler describes a goal in natural language; TripPilot gathers provider data, applies deterministic schedule and budget rules, produces a coherent trip, and keeps booking decisions with the user.

The repository preserves the original Sunlit Cartography + Soft Bento interface while adding a typed FastAPI/LangGraph backend, provider boundaries, deterministic validation, a Supabase schema, tests, and CI.

> Default provider status: **demo mode**. Flight and hotel inventory remains deterministic demo data for the Indore–Goa fixture only. Places, routes, and weather have server-side live adapters when configured. No provider key is shipped in this repository.

## What works

- Natural-language trip submission from the existing UI
- FastAPI planning API invoked through a real LangGraph workflow
- OpenRouter strict structured extraction in live mode, including one bounded validation retry
- Structured follow-up questions when critical trip fields are missing
- Concurrent typed flight, hotel, and place providers
- Google Places API (New) adapter for destination, nearby, and details lookup
- Google Routes adapter for route and matrix duration checks; missing routes are never treated as a guessed duration
- WeatherAPI adapter with normalized daily/hourly forecasts and alerts; dates 14 or more days ahead return `not_available_yet`
- Smart Explorer combines backend Places, Routes, opening-hour checks, hard time/budget feasibility, and weather suitability
- Explorer cards and Route Thread render normalized backend results; filters issue distinct backend queries
- Generic Add to Today updates an in-memory itinerary, free window, and shared budget display
- Centralized domain models and deterministic budget/schedule validation
- Free-time feasibility, place scoring, and outbound-link security services
- Shared frontend plan state and recoverable backend error UI
- Responsive existing views for trip, explorer, inventory, map, budget, alerts, and re-planning
- Supabase migration with RLS and a server-only access posture
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
Supabase PostgreSQL schema (persistence integration pending)
```

OpenRouter performs structured constraint extraction when live mode is configured. Providers supply facts; deterministic code owns arithmetic, time, route feasibility, opening-hour checks, and URL safety. Booking occurs externally. The current disruption comparison is an explicitly labeled demo preview and does not modify a plan.

Read [architecture](docs/architecture.md), [agent design](docs/agent-system.md), [evaluation](docs/evaluation.md), [failure analysis](docs/failure-analysis.md), and the [repository audit](docs/codebase-audit.md).

## Local development

Prerequisites: Node.js 22+, Bun or npm, and Python 3.12+.

```powershell
Copy-Item .env.example .env
bun install
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
```

Run the API:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Run the frontend separately:

```powershell
bun run dev
```

The browser defaults to `http://localhost:8000`; override it with `VITE_TRIPPILOT_API_URL`.

## Environment and security

Copy `.env.example` and fill only the providers you use. Key settings include `TRAVEL_DATA_MODE`, `PLACES_PROVIDER`, OpenRouter/model values, database/Supabase values, Google and weather credentials, optional travel inventory credentials, and LangSmith observability values. For Google mode, enable Places API (New), restrict the key to that API and the deployed backend where practical, then set `GOOGLE_MAPS_API_KEY` server-side.

Never expose provider secrets or `SUPABASE_SERVICE_ROLE_KEY` through `VITE_` variables. The browser calls only TripPilot's backend.

## Quality checks

```powershell
bun run lint
bun run typecheck
bun run build
backend/.venv/Scripts/python.exe -m ruff format --check backend
backend/.venv/Scripts/python.exe -m ruff check backend
backend/.venv/Scripts/python.exe -m pytest backend -q
```

The backend suite contains correctness and API tests. See [evaluation](docs/evaluation.md) for the latest measured count. Benchmark percentages are omitted until the full scenario evaluation suite is executed.

## Database

The timestamped migration under `supabase/migrations/` creates the initial schema. Apply it through a linked Supabase CLI project or your normal migration pipeline. Every public table has RLS enabled; `anon` and `authenticated` access is revoked until authentication and ownership policies are implemented.

## Deployment

- Deploy the frontend to Vercel or another TanStack Start-compatible runtime and set `VITE_TRIPPILOT_API_URL`.
- Deploy `backend/` to Railway, Render, or another ASGI host using `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Create a Supabase project and apply the migration before enabling persistence.
- Restrict backend CORS to deployed frontend origins.

## Known limitations

- Demo mode intentionally maps requests to the deterministic Goa evaluation fixture; live mode uses OpenRouter extraction.
- Google Places and Routes require `GOOGLE_MAPS_API_KEY`; WeatherAPI requires `WEATHER_API_KEY`. Live calls have not been verified on this host because those keys are unavailable.
- Flights and hotels remain demo providers; for other origins/destinations they return no fixture inventory.
- The map is an explicitly schematic visual, not geographic rendering.
- Add to Today is local/in-memory and resets on refresh. The disruption view is a demo preview, not a persisted re-plan.
- Authentication, ownership policies, full evaluations, and browser end-to-end tests remain incomplete.

TripPilot never processes payments or issues tickets. Purchases happen on approved external provider sites.
