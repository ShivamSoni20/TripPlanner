# TripPilot architecture

TripPilot keeps the existing TanStack Start/React interface and places all factual travel access and planning rules behind a FastAPI service.

## Runtime boundaries

- **Frontend:** TanStack Start, React 19, TanStack Router, Tailwind CSS, and the existing shadcn-based design system. `src/lib/trip-api.ts` is the browser's only planning boundary.
- **Backend:** FastAPI exposes versioned REST endpoints. API keys and provider credentials remain server-side.
- **Agent:** LangGraph owns the stateful planning transition. It delegates factual retrieval to typed providers and correctness checks to deterministic services.
- **Providers:** flight, hotel, and place contracts have deterministic demo implementations. Live adapters can replace them without changing the graph.
- **Planning services:** budget arithmetic, schedule validation, free-time feasibility, and outbound URL validation do not depend on an LLM.
- **Database:** the Supabase migration creates trip, option, itinerary, event, alert, run, and tool-call records. RLS is enabled and browser roles are denied until authenticated ownership policies are introduced.

## Request flow

1. The existing trip prompt calls `POST /api/v1/trips/plan`.
2. FastAPI builds a typed planning state and invokes the LangGraph workflow.
3. Independent demo providers run concurrently.
4. The planner creates itinerary candidates and runs schedule and budget validation.
5. A typed `TripPlan` is returned and normalized into the frontend domain model.
6. All screens read the shared plan; the budget view no longer performs independent arithmetic.

## Deployment shape

The frontend can deploy to Vercel or Cloudflare-compatible hosting. The Python service can deploy to Railway, Render, or another ASGI host. Supabase hosts PostgreSQL. Configure the frontend with `VITE_TRIPPILOT_API_URL`; configure the backend only with server-side secrets described in `.env.example`.

No browser code calls OpenRouter, Google, flight, hotel, weather, or Supabase service-role APIs directly.
