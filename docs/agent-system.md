# Agent system

## Current graph

The compiled LangGraph contains two explicit nodes:

1. `validate_constraints` rejects missing state before any provider work.
2. `plan_trip` queries typed providers concurrently, builds the plan, validates the schedule, and calculates the budget.

The conditional edge stops invalid work before the planning node. `TripAgentState` carries constraints, the completed plan, warnings, errors, and revision count.

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

The next graph expansion separates request extraction, flights, hotels, places, weather, routes, candidate generation, optimization, schedule validation, and finalization. Weather and route nodes require configured live adapters. OpenRouter structured output will parse free-form constraints when a key is present; demo mode retains the canonical Goa fixture.

## Failures and retries

Provider errors will be normalized as `TIMEOUT`, `RATE_LIMITED`, `AUTH_FAILED`, `INVALID_REQUEST`, `NO_RESULTS`, `PROVIDER_DOWN`, `STALE_RESULT`, or `UNKNOWN`. Authentication and validation failures are not retried. Timeouts and server failures are bounded to two retries. Partial provider success remains a valid plan result.

No prompts, hidden reasoning, or chain-of-thought are stored. Agent-run and tool-call records contain only inputs, output summaries, timing, status, retries, and errors.
