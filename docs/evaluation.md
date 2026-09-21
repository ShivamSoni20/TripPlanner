# Evaluation

Only measured results belong in this document.

## Current baseline

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend -q
```

Result on 21 September 2026: **7 tests passed**. These tests cover budget reconciliation, schedule overlap/travel validation, free-time hard feasibility, booking URL security, and the planning API. They are correctness tests, not a statistically meaningful planning benchmark.

## Benchmark status

The 20–30 scenario benchmark and single-prompt LLM baseline are not yet measured. No completion-rate, constraint-satisfaction, latency, or model-cost percentages are claimed yet. Results will be added only from persisted evaluation output under `evals/results/`.

Planned deterministic graders include budget overflow, overlap, trip-date bounds, travel feasibility, duplicate IDs, grounded provider entities, approved booking URLs, and free-window fit.
