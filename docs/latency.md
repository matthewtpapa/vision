# Latency Controller & Process Model (v0.1)

> Latest RC artifacts: [metrics.json](https://github.com/latvision/vision/releases/latest/download/metrics.json) · [stage_timings.csv](https://github.com/latvision/vision/releases/latest/download/stage_timings.csv) · [latency.png](https://github.com/latvision/vision/releases/latest/download/latency.png)

This document defines the **official latency behavior** of the SDK for the
0.1.x line. It is investor-grade and forms the basis of our SLO claims.

- Controller policy: **windowed p95**, **stride/skip only** (no model degrade).
- Process model: **single-process, single-stream**; reads thread-safe, writes serialized.
- Skipped-frame semantics are **well-defined** to avoid metric distortion.

---

## Gate D (one-shot demo)

Run a local demo to generate a synthetic fixture, evaluate, and plot latency:

```bash
make demo
```

The plot excludes warm-up frames from SLO calculations.

This produces:

- `bench/out/metrics.json`
- `bench/out/stage_timings.csv`
- `bench/out/latency.png`

---

## Process / Thread Model (v0.1)

- **Single-process, single-stream** pipeline.
- **Reads are thread-safe**; `add_exemplar` writes are **serialized**.
- There is **no embedding de-grade path** in v0.1. Adaptive behavior is *only*:
  - **Stride increase** (process every Nth frame) when over budget.
  - **Stride decrease** (back toward 1) when clearly under budget for a window.

> Rationale: predictable behavior under load; easy to reason about tail latencies.

---

## Controller: Windowed p95 (Stride/Skip Only)

We maintain a rolling **window** of per-frame latencies (default `window=120`).
On each frame:

1. Compute **inclusive p95** of the window.
2. Compare to **budget_ms** and **low_water** hysteresis.
3. Adjust **frame_stride** accordingly.

### Policy

- If `p95 > budget_ms` → `frame_stride = min(frame_stride + 1, max_stride)`
- If `p95 < budget_ms * low_water` for ≥ `window` samples
  → `frame_stride = max(frame_stride - 1, min_stride)`
- Else → hold stride.

### Defaults (v0.1)

- `budget_ms`: 66 (example default; README/demo may use 33)
- `window`: 120
- `low_water`: 0.8
- `min_stride`: 1
- `max_stride`: 4
- `auto_stride`: true

> **Warm-up:** `p95_window_ms` remains `null` until we have ≥30 samples; this avoids
> reporting unstable tail stats early in the run.

---

## Skipped-Frame Semantics (Metrics Integrity)

- We **record per-frame duration** for every frame (processed or skipped).
- **Stage timings** (detect/track/embed/match) are recorded **only** for **processed** frames.
- The `unknown` flag for skipped frames **reuses the last processed frame’s value** to prevent
  artificial inflation of unknown-rate when frames are skipped due to stride.
- Controller state exposed in metrics:
  - `start_stride`, `end_stride`, `frames_total`, `frames_processed`, `p95_window_ms`,
    and the controller config (`auto_stride`, `min_stride`, `max_stride`, `window`, `low_water`).

---

## Configuration & Env Overrides

All knobs are configurable via `vision.toml` and environment overrides.

| Key                                   | Type    | Default | Env override                           |
|--------------------------------------|---------|---------|----------------------------------------|
| `latency.budget_ms`                  | int     | 66      | `VISION__LATENCY__BUDGET_MS`           |
| `latency.window`                     | int     | 120     | `VISION__LATENCY__WINDOW`              |
| `latency.low_water`                  | float   | 0.8     | `VISION__LATENCY__LOW_WATER`           |
| `pipeline.frame_stride`              | int     | 1       | `VISION__PIPELINE__FRAME_STRIDE`       |
| `pipeline.min_stride`                | int     | 1       | `VISION__PIPELINE__MIN_STRIDE`         |
| `pipeline.max_stride`                | int     | 4       | `VISION__PIPELINE__MAX_STRIDE`         |
| `pipeline.auto_stride`               | bool    | true    | `VISION__PIPELINE__AUTO_STRIDE`        |

### Examples

Increase the budget and disable adaptation:

```bash
VISION__LATENCY__BUDGET_MS=33 \
VISION__PIPELINE__AUTO_STRIDE=0 \
latvision eval --input frames --output out
```

Force a bounded stride range:

```bash
VISION__PIPELINE__MIN_STRIDE=1 \
VISION__PIPELINE__MAX_STRIDE=2 \
latvision eval --input frames --output out
```

## What We Report

Per-run envelope (metrics.json):

fps, p50, p95

stage_ms (means for detect/track/embed/match/overhead)

kb_size, backend_selected, sdk_version

Controller block (see above)

Per-stage summary (stage_timings.csv):

Columns: stage,total_ms,mean_ms,count

Only processed frames contribute to count.

Plotting notes:

- Latency plots shade the warm-up region and highlight any rolling-p95-over-budget windows (default window 120 frames).
- Flags:

  ```bash
  python scripts/plot_latency.py --input stage_timings.csv --output latency.png \
    --window 120 --warmup 100
  ```

  `--metrics` reads the budget from metrics.json; `--slo-ms` provides a fallback.

## Sustained 10-min run (warm-up excluded)

Sustained mode runs the evaluator for a fixed wall-clock duration while
dropping the first 100 frames from SLO and percentile calculations.

```bash
latvision eval --sustain-minutes 10 --budget-ms 33
```

cold_start_ms = import/process start → first result

bootstrap_ms = start → frame #1000 processed, or last frame if <1000

During a reference run, background work at ~190s pushed p95 above budget and
the controller raised stride to 2. The system recovered around ~420s and
stride returned to 1. See GitHub Releases → the latest RC tag for the full metrics.json and annotated latency plot.

## Stress Narrative (template)

We include a qualitative narrative alongside artifacts to make controller behavior
interpretable at a glance. Use the template below for RC notes:

Scenario: 10-minute sustained run; budget 33 ms; window 120; low-water 0.8.
Behavior: At ~190s, background tasks increased CPU pressure; p95 exceeded budget.
Controller raised stride from 1→2, holding p95 under 33 ms while FPS stayed ≥25.
Pressure subsided around ~420s; after one full window under low-water, stride decreased
back to 1. Error budget stayed under 0.5%; no model degrade was used.

## FAQ

Why stride/skip only?
Predictability. We avoid dynamic model changes that can alter accuracy; we control latency
by reducing processed frames under load, then recover.

Does skipping lie about latency?
No. We measure per-frame timing for every frame and expose controller decisions explicitly.

Where are SIMD/CPU features reported?
A separate latvision hello banner (PR 8) prints OS/Python, wheel flavor, and SIMD (AVX2/NEON/no-SIMD).

## Related Docs

Milestone spec & gates: docs/specs/m1.1.md

Result schema (frozen): docs/schema.md

Benchmarks methodology: docs/benchmarks.md
