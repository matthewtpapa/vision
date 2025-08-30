# Evaluation & Telemetry (`vision --eval`)

Run the vertical-slice evaluator to produce latency/FPS/unknown-rate metrics:

```bash
vision --eval --input examples/eval_frames --output out/
```

Artifacts:
- `out/metrics.json` — JSON (schema frozen for M1)
- `out/stage_timings.csv` — deterministic per-stage summary

## JSON Schema (M1)
```json
{
  "stage_ms": {"detect": 0.0, "track": 0.0, "embed": 0.0, "match": 0.0, "overhead": 0.0},
  "fps": 0.0,
  "p50": 0.0,
  "p95": 0.0,
  "unknown_rate": 0.0,
  "kb_size": 0,
  "backend_selected": "faiss",
  "sdk_version": "0.1.0"
}
```

## CSV Columns
`stage,count,total_ms,mean_ms,max_ms`

## Pass/Fail Gates (M1)
- p95 ≤ 33 ms over ≥ 2,000 frames (warm-up 100 excluded)  
- KB bootstrap ≤ 50 ms for N=1k  
- Non-zero exit on failure (CI-friendly)
