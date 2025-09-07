# Evaluation & Telemetry (`latvision eval`) — Prefer latvision; vision prints a deprecation warning

## Quickstart

Generate a small set of synthetic frames:

```python
from pathlib import Path
from PIL import Image

in_dir = Path("in")
in_dir.mkdir()
for i in range(8):
    img = Image.new("RGB", (64, 64), color=(i, 0, 0))
    img.save(in_dir / f"{i}.png")
```

Run the evaluator and inspect the outputs:

```bash
latvision eval --input in --output out --warmup 0
cat out/metrics.json
cat out/stage_timings.csv
```

## Metrics schema

```json
{
  "fps": 0.0,
  "p50": 0.0,
  "p95": 0.0,
  "kb_size": 0,
  "backend_selected": "faiss",
  "stage_ms": {"detect": 0.0, "track": 0.0, "embed": 0.0, "match": 0.0, "overhead": 0.0},
  "controller": {
    "auto_stride": false,
    "min_stride": 1, "max_stride": 4,
    "start_stride": 1, "end_stride": 1,
    "window": 120, "low_water": 0.8,
    "frames_total": 0, "frames_processed": 0,
    "p95_window_ms": null
  }
}
```

`p95_window_ms` remains `null` until enough samples (≥ window warmup; defaults to 30) accumulate.

## Interpreting results

- If `p95` exceeds `budget_ms`, the CLI exits with code `2`; inspect `end_stride` and `frames_processed/frames_total`.
- To tune, increase `budget_ms` or `max_stride`, or reduce model cost.
- `stage_timings.csv` columns: `stage,total_ms,mean_ms,count`. Only processed frames contribute to `count`; skipped frames are omitted.

See [latency.md](latency.md) for controller policy details.
