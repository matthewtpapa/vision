# Schema Guide (v0.1)

The JSON contract lives in `docs/schema.md`. This guide covers metrics emitted by the evaluator.

## metrics.json top-level fields

- `metrics_schema_version` — required; string. Current version: `"0.1"`.
- `unknown_rate_band` — `[low, high]` array of the resolved unknown-rate band after precedence (CLI > fixture manifest > default `0.10,0.40`).
- `process_cold_start_ms` — optional debug field emitted only when `VISION_DEBUG_TIMING=1`; measures CLI entry to first result and is not used for gates.
