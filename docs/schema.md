# Schema v0.1

## Example `MatchResult`

```json
{
  "label": "red-mug",
  "confidence": 0.78,
  "neighbors": [
    { "label": "red-mug", "score": 0.78 },
    { "label": "maroon-cup", "score": 0.65 }
  ],
  "backend": "numpy",
  "stride": 1,
  "budget_hit": false,
  "bbox": [120, 96, 220, 196],
  "timestamp_ms": 1725043200123,
  "sdk_version": "0.1.0-rc.2"
}
```

## `metrics.json` Top-Level Fields

- `metrics_schema_version` — required; string. Current version: `"0.1"`.
- `unknown_rate_band` — `[low, high]` array of the resolved unknown-rate band after precedence (CLI > manifest > default `0.10,0.40`).
- `process_cold_start_ms` — optional debug field emitted only when `VISION_DEBUG_TIMING=1`; measures CLI entry to first result and is not used for gates.
