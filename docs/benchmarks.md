# Benchmarks Methodology (v0.1)

This document defines how we measure performance and what artifacts we publish.
It is the source of truth for Gates **B** (Latency/SLO) and **C** (Repro in one command).

---

## Scope

- Vertical slice: detect → track → embed → match (open-set).
- Controller: windowed p95, **stride/skip only** (no degrade).
- Outputs: summary JSON/CSV + optional time-series plot.

Related docs:

- Process model & controller: **docs/latency.md**
- Result schema (MatchResult v0.1): **docs/schema.md**
- Milestone spec & gates: **docs/specs/m1.1.md**

---

## Measurement Primitives

- **Clock:** `time.monotonic_ns()` (or equivalent) only.
- **Percentiles:** NumPy percentiles using the "linear" method.
  - Documented to avoid implementation drift across NumPy versions.
- **Warm-up:** Explicitly **excluded** (default: 100 frames) from p50/p95/p99/FPS.
- **Window p95:** Controller uses **inclusive p95** over a rolling window (see `docs/latency.md`).

---

## What We Compute / Report

**Run-level metrics (metrics.json):**

- `fps` — overall (post warm-up)
- `p50`, `p95`, `p99` — per-frame end-to-end
- `stage_ms` — mean per stage: `detect`, `track`, `embed`, `match`, `overhead`
- `kb_size`, `backend_selected`, `sdk_version`
- **Controller block**:
  - `auto_stride`, `min_stride`, `max_stride`, `window`, `low_water`
  - `start_stride`, `end_stride`
  - `frames_total`, `frames_processed`
  - `p95_window_ms` (latest window value or `null` during warm-up)
- **Repro fields** (required for RCs):
  - `git_commit`, `hardware_id` (CPU model / SIMD flags / OS), `fixture_hash`

**Stage summary (stage_times.csv):**

- Columns: `stage,total_ms,mean_ms,count`
- Only **processed** frames contribute to `count`.

**Optional plot (latency.png):**

- Time-series of p50/p95/p99 & FPS; annotate stride changes.

---

## Warm-up & Unknown-Rate Handling

- Warm-up frames are **excluded** from p-stats and FPS.
- When frames are **skipped** by the controller:
  - Per-frame **duration** is still recorded.
  - **Stage timings** are recorded **only** for processed frames.
  - The `unknown` flag for skipped frames **reuses** the last processed frame’s
    value (prevents artificial unknown-rate inflation). (See `docs/latency.md`.)

**Fixture guardrail:** On the reference fixture, unknown-rate must lie within
the manifest band `[low, high]`. CLI fails the bench if out of band.

---

## CPU / BLAS / GC Notes (record & control)

- **SIMD:** Record AVX2/AVX512/NEON or “no-SIMD”; include in `hardware_id`.
- **BLAS / Threading:** Note OpenBLAS/MKL/Accelerate and thread count.
  - Prefer single-threaded BLAS during benches for stability (document value if changed).
- **Python GC:** Leave enabled; if disabled for experiments, state it explicitly.
- **Power plans:** Avoid turbo-boost pinning/thermal throttling during long runs; include caveats if observed.

---

## Fixture & Repro (Gate C)

- **Builder:** `scripts/build_fixture.py --seed 42 --out data/fixture`
- **Contents:** Deterministic list of image IDs, fixed resolution/crops, reproducible augments.
- **Manifest:** `ids`, transforms, `unknown_band`, `fixture_hash`.
- If distribution is restricted, provide a **synthetic** generator that yields equivalent shape/guardrails.

**One-command bench (wired in later PRs):**

```makefile
bench:
    python scripts/build_fixture.py --seed 42 --out data/fixture
    latvision eval --frames 2000 --kb 1000 --budget-ms 33 --seed 42 \
      --report out/metrics.json --stages out/stage_times.csv
    python scripts/print_summary.py out/metrics.json

plot:
    python scripts/plot_latency.py --metrics out/metrics.json --out out/latency.png

Artifact Requirements (RC tags)

Attach to every RC tag:

out/metrics.json

out/stage_times.csv

out/latency.png (time-series)

README section linking these artifacts

Versions: sdk_version, git_commit, Python, OS, wheel flavor, CPU features

Pass / Fail (Gate B Targets)

On reference boxes (see spec for models):

Windowed run (≥ 2,000 frames; warm-up 100 excluded):

p95 ≤ 33 ms, p99 ≤ 66 ms, FPS ≥ 25

Sustained SLO (10 minutes):

≥ 99.5% frames within 33 ms (Error Budget ≤ 0.5%)

Cold-start: import → first MatchResult ≤ 1.0 s

Bootstrap: index load @ N=1k ≤ 50 ms

Unknown-rate band: within fixture manifest range

Summary Table (printout guidance)

When scripts/print_summary.py runs, it should print a concise table:

metric    value
fps    27.4
p50 (ms)    21.1
p95 (ms)    31.7
p99 (ms)    58.9
frames processed    1800/2000
stride start→end    1→2
unknown-rate    0.21
backend    numpy
kb_size    1000
cold-start (ms)    722
bootstrap (ms)    41

Include a single-line verdict: PASS or FAIL for Gate B conditions.

Known Pitfalls

Mixing clocks (wall vs monotonic) skews SLOs → use monotonic_ns only.

Different NumPy percentile methods shift tails → stick to "linear" and record version.

Counting skipped frames as processed corrupts stage means → don’t; see rules above.

Short runs (< window) yield unstable p95 → allow warm-up and report p95_window_ms=null until ready.

Glossary

Budget: latency target in ms (e.g., 33).

Stride: process every Nth frame (≥1).

Error Budget: share of frames allowed to breach the budget (e.g., 0.5%).


---

## Acceptance

- [ ] `docs/benchmarks.md` created matching the content above.
- [ ] README references `docs/benchmarks.md` once under the evaluator section.
- [ ] `npx markdownlint-cli2 docs/benchmarks.md README.md` passes.
- [ ] No runtime changes.

---

## Quick test commands

```bash
npx markdownlint-cli2 docs/benchmarks.md README.md
pytest -q
```
