# Evaluation

Only measured results belong in this document.

## Current baseline

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend -q
```

Result on 24 September 2026: **63 tests passed**. These correctness and integration tests cover OpenRouter extraction, Google Places/Routes normalization, WeatherAPI requests and errors, forecast horizon boundaries, weather suitability, Smart Explorer route/time/budget/opening-hour feasibility, schedule and budget validation, booking URL security, provider status, non-Goa planning, and Phase E fake-repository auth/API behavior. They are not a statistically meaningful planning benchmark.

Local demo API smoke check: the canonical Indore–Goa request returned 3 itinerary items, 1 free window, an available demo forecast, and 2 feasible Explorer recommendations. The frontend development server returned HTTP 200. Automated browser interaction could not be completed on this Windows host because the available browser controller failed to attach; no visual or click-through result is claimed.

Phase E fake-repository API checks cover authenticated create/list/load, cross-user invisibility, stale version rejection, Explorer, Add to Today, and undo. Auth unit checks cover malformed bearer headers, verified principal extraction, and request-scoped token isolation. A ₹30k Goa smoke run returned 3 planned items, 1 free window, 2 recommendations, and a successful version-2 add. These are not live Supabase RLS or reload tests: no TripPilot project or credentials were available, and the local Supabase CLI is absent.

## Benchmark status

The 20–30 scenario benchmark and single-prompt LLM baseline are not yet measured. No completion-rate, constraint-satisfaction, latency, or model-cost percentages are claimed yet. Results will be added only from persisted evaluation output under `evals/results/`.

Planned deterministic graders include budget overflow, overlap, trip-date bounds, travel feasibility, duplicate IDs, grounded provider entities, approved booking URLs, and free-window fit.
