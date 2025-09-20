# Schema Guide (v0.1)

The JSON contract lives in `docs/schema.md`. This guide covers metrics emitted by the evaluator.

Config precedence: CLI > ENV > manifest (TOML) > defaults.

## metrics.json top-level fields

- `metrics_schema_version` — required; string. Current version: `"0.1"`.
- `unknown_rate_band` — `[low, high]` array of the resolved unknown-rate band after precedence.
- `process_cold_start_ms` — optional debug field emitted only when `VISION_DEBUG_TIMING=1`; measures CLI entry to first result and is not used for gates.
- `purity` — summary of hot-loop network blocks. Example: `{ "sockets_blocked": 0, "dns_blocked": 0 }`.

## Artifacts

- `artifacts/config_precedence.json`
- `artifacts/metrics_hash.txt`
- `artifacts/purity_report.json`
