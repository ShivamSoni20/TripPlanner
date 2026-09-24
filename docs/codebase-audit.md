# TripPilot codebase audit

## Existing architecture

- **Framework:** TanStack Start 1.168 with React 19 and Vite 8.
- **Routing:** TanStack Router file routes. Only `/` exists today; views are local state.
- **Styling:** Tailwind CSS 4 with semantic OKLCH tokens in `src/styles.css`.
- **Components:** shadcn/Radix primitives in `src/components/ui`.
- **Animation:** Motion for transitions plus reduced-motion-safe CSS animations.
- **Data fetching:** TanStack Query is installed and provided, but no product queries exist.
- **State:** one React context in `trip-pilot.tsx` with six UI state values.
- **Map:** a decorative SVG/CSS map, not a geographic provider.
- **Deployment:** Vite and TanStack Start build a Cloudflare-compatible Nitro bundle.

## Product status before production work

| Capability                    | Status  | Notes                                                      |
| ----------------------------- | ------- | ---------------------------------------------------------- |
| New Trip                      | Partial | Accessible form, but input is not parsed or persisted.     |
| Planning progress             | Mocked  | Timer advances hardcoded counts.                           |
| Overview                      | Static  | Goa fixture only.                                          |
| Itinerary / Route Thread      | Partial | Selection sync works locally; data is hardcoded.           |
| Smart Explorer                | Partial | Local add interaction works only for Fort Aguada.          |
| Flights / Hotels              | Mocked  | Hardcoded inventory and generic booking URL.               |
| Map                           | Mocked  | Coordinates are percentages, not geographic points.        |
| Budget                        | Static  | Values reconcile, but are duplicated across screens.       |
| Alerts / disruption           | Partial | Approval interaction works locally; no persisted proposal. |
| Mobile / desktop navigation   | Working | Responsive local-state navigation.                         |
| Backend / persistence / agent | Missing | No API, database, providers, or LangGraph.                 |
| Tests / evaluations / CI      | Missing | No test runner or automation.                              |

## Primary technical debt

1. The 1,464-line `trip-pilot.tsx` couples domain fixtures, mutations, navigation, and UI.
2. Goa-specific values are duplicated across overview, itinerary, map, budget, and alerts.
3. Existing progress text claims provider work that never ran.
4. User actions do not survive refresh and are not validated before mutation.
5. Booking/map URLs are generic rather than validated provider-returned URLs.
6. There are no loading/error contracts between product UI and a server.
7. Views are not addressable with the required trip URLs.

## Migration approach

Preserve the visual system and migrate behind it incrementally:

1. Establish shared typed domain models and deterministic services.
2. Add a FastAPI service with provider interfaces and deterministic demo providers.
3. Add streaming planning events and a typed frontend API client.
4. Replace each hardcoded view with query-backed data without redesigning it.
5. Add Supabase persistence, RLS, evaluations, CI, and live providers as credentials arrive.
