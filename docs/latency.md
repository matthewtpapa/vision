# Latency Controller

The evaluator uses a windowed p95 controller to adapt frame stride.

## Windowed p95

- Rolling window (default 120 frames)
- Inclusive p95 computation
- Low-water hysteresis of 0.8
- Bounds: `min_stride=1`, `max_stride=4`

## Policy

- `p95 > budget_ms` → `stride + 1` (capped at `max_stride`)
- `p95 < budget_ms * low_water` for a full window → `stride - 1` (floored at `min_stride`)

Skipped frames:

- Per-frame timing is still recorded.
- Stage timings only include processed frames.
- Unknown flag is reused from the last processed frame.

## Configuration

| Env var | Description |
| --- | --- |
| `VISION__LATENCY__BUDGET_MS` | Target p95 latency budget in ms |
| `VISION__LATENCY__WINDOW` | Size of the rolling window |
| `VISION__LATENCY__LOW_WATER` | Low-water hysteresis ratio |
| `VISION__PIPELINE__FRAME_STRIDE` | Starting frame stride |
| `VISION__PIPELINE__MIN_STRIDE` | Minimum allowed stride |
| `VISION__PIPELINE__MAX_STRIDE` | Maximum allowed stride |
| `VISION__PIPELINE__AUTO_STRIDE` | Enable adaptive stride |

## Troubleshooting

- `p95_window_ms=null` → run longer or reduce the window size.
- Unknown rate spikes → ensure you're on a build ≥ this PR (skipped-frame fix).
- In bare environments, install `numpy` and `pillow` or rely on the built-in guard.
