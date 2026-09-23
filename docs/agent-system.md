# Agent system

## Current graph

The compiled LangGraph currently contains three explicit nodes:

1. `parse_constraints` uses the deterministic fixture extractor in demo mode or strict OpenRouter structured output in live mode.
2. `validate_constraints` rejects missing or invalid state before any provider work.
3. `plan_trip` queries typed providers concurrently, builds the plan, validates the schedule, and calculates the budget.

The parsing edge returns a structured `needs_input` result when critical fields are absent. Invalid model output is retried once with Pydantic validation feedback, then fails gracefully. The conditional validation edge stops invalid work before the planning node. `TripAgentState` carries the request, extraction result, constraints, completed plan, warnings, errors, and revision count.

## Correctness boundary

The model is not authoritative for arithmetic or feasibility. Deterministic services enforce:

- end dates after start dates;
- non-overlapping itinerary items;
- required travel time between activities;
- exact budget category totals;
- free-time recommendations fitting travel, visit, onward travel, and safety buffer;
- HTTPS booking URLs from approved domains.

Provider outputs use Pydantic models before they enter state. Demo values are deterministic and explicitly labelled `demo`; they are not presented as current prices.

## Planned production nodes

The next graph expansion separates flights, hotels, places, weather, routes, candidate generation, optimization, schedule validation, and finalization. Weather and route nodes require configured live adapters. OpenRouter now parses free-form constraints when live mode and a key are configured; demo mode retains the canonical Goa fixture.

## Failures and retries

Provider errors will be normalized as `TIMEOUT`, `RATE_LIMITED`, `AUTH_FAILED`, `INVALID_REQUEST`, `NO_RESULTS`, `PROVIDER_DOWN`, `STALE_RESULT`, or `UNKNOWN`. Authentication and validation failures are not retried. Timeouts and server failures are bounded to two retries. Partial provider success remains a valid plan result.

No prompts, hidden reasoning, or chain-of-thought are stored. Agent-run and tool-call records contain only inputs, output summaries, timing, status, retries, and errors.

## Durable trip boundary

The graph remains unaware of Supabase. After it returns a validated plan, the API's `TripRepository` persists the trip under the verified Supabase principal. Reloading reconstructs the domain plan from root, preferences, options and itinerary rows, with budget and free windows recomputed deterministically. Explorer and Add to Today read that stored state, not a browser-supplied plan. Add and undo use an expected trip version and a security-invoker PostgreSQL function so the item change and version bump commit together. The model does not authorize users or override these checks.
