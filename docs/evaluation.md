# Evaluation

Only measured results belong in this document.

## Current baseline

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend -q
```

Result on 22 September 2026: **42 tests passed**. These tests cover OpenRouter structured extraction, Google Places normalization, Google Routes duration parsing & matrix bounds, Smart Explorer feasibility & ranking, budget reconciliation, schedule travel validation, booking URL security, health provider status, and non-Goa itinerary planning. They are correctness tests, not a statistically meaningful planning benchmark.

## Benchmark status

The 20–30 scenario benchmark and single-prompt LLM baseline are not yet measured. No completion-rate, constraint-satisfaction, latency, or model-cost percentages are claimed yet. Results will be added only from persisted evaluation output under `evals/results/`.

Planned deterministic graders include budget overflow, overlap, trip-date bounds, travel feasibility, duplicate IDs, grounded provider entities, approved booking URLs, and free-window fit.
