# Project Charter and Vision

## North Star

Deliver a real-time, open-set recognition SDK: detect, track, embed, and match objects in live video against a continually growing exemplar knowledge base.

- Sustains latency-bounded performance on reference hardware
- Modular and backend-agnostic
- Exposes a simple, typed Python API
- Serves AR, robotics, and vision pipelines as infrastructure
- Not a consumer app — this is **FFmpeg-for-open-set recognition**: boring, reliable infra that others depend on.

## Milestones (Roadmap)

- **M0 (Complete)** — Foundations: stubs, CLI scaffolding, local KB, dev workflow
- **M1** — Latency-Bounded Vertical Slice: end-to-end loop; telemetry + `--eval`; incremental KB updates; factory-based matcher
- **M1.1 (In Progress)** — Investor-grade gates (SDK façade, install matrix, latency SLOs, reproducible benches)
- **M2** — Developer SDK: stable API; exemplar management; packaging & distribution; AR/robotics demos
- **M3** — Scaling: multi-backend abstraction (FAISS-GPU, Torch/ONNX); KB persistence/versioning; frozen telemetry schema; gRPC/REST API
- **M4** — Production Hardening: continuous ingestion; pruning/compaction; robustness tests; deployment profiles
- **M5 (Stretch)** — Enterprise: ARKit/ARCore/Vision Pro integrations; telemetry dashboard; licensing model; OSS + commercial split

## M1 Focus (Highlights)

- Real-time vertical slice (detect → track → embed → match)
- Incremental KB updates
- Telemetry with `--eval` export (latency, FPS, unknown-rate, KB size)
- Matcher factory: FAISS (preferred) + NumPy fallback
- Minimal Python API surface: `add_exemplar(...)`, `query_frame(...)`

## Acceptance Highlights

- p95 latency ≤ 33 ms on reference CPU (CLIP-B32 baseline)
- KB bootstrap ≤ 50 ms (N=1k)
- Deterministic eval fixture (≥2k frames, seeded)

## Process Guardrails

- **Charter (this doc)** → sets vision, roadmap, and themes. Evolves slowly (reviewed at major milestones)
- **Specs (per milestone)** → exact contracts, telemetry schemas, CI gates. Evolve quickly, live close to code
- Charter answers "what and why"; Specs answer "how and with what guarantees"

## Milestone M1.1 — SDK Reality & Latency SLO (Investor-Facing)

**Goal (0.1.x):** Ship a latency-bounded open-set SDK with a minimal façade (`add_exemplar`, `query_frame`), a canonical CLI (`latvision`), and a one-command reproducible benchmark. Public positioning: *predictable, measurable, embeddable*.

### What ships in M1.1

- Python façade (importable in 5 lines), canonical CLI rename, and “hello → eval → plot” demo path.
- Frozen result schema v0.1; CI guard against breaking changes.
- Windowed p95 controller (stride/skip only), with sustained-run SLO reporting.
- Reproducible fixture + summary/plot scripts; artifacts published on RC tags.

### Acceptance gates (all must be green)

- **Gate A — SDK Reality & Platform Matrix.** `pip install latency-vision` works on macOS/Windows/Linux; `from latency_vision import add_exemplar, query_frame` imports succeed; README 5-liner returns a `MatchResult` that matches **[docs/schema.md](../schema.md)**. CI matrix: Python 3.10/3.11/3.12 × macOS (x86_64/arm64), Windows (x86_64), Linux (manylinux2014 x86_64).
- **Gate B — Latency & SLO.** On reference CPUs, windowed run (≥2k frames; warm-up excluded) yields `p95 ≤ 33 ms`, `p99 ≤ 66 ms`, `FPS ≥ 25`. Sustained 10-minute run: ≥99.5% frames within 33 ms. Cold-start ≤ 1.0 s, index bootstrap @ N=1k ≤ 50 ms.
- **Gate C — Reproducibility (1 command).** `make bench` builds fixture, runs eval with fixed seed, emits `out/metrics.json` + `out/stage_timings.csv`, and prints a summary. Artifacts record `sdk_version`, `git_commit`, `hardware_id`, `fixture_hash`.
- **Gate D — Installability & Hello World.** Clean macOS/Windows/Linux installs succeed; a Windows user can run the README 5-liner (NumPy backend fallback) and share `MatchResult` JSON.

### Cross-references

- M1.1 detailed spec & gates: **[docs/specs/m1.1.md](../specs/m1.1.md)**
- Result schema v0.1 (frozen): **[docs/schema.md](../schema.md)**
- Controller & process model: **[docs/latency.md](../latency.md)**
- Benchmark methodology: **[docs/benchmarks.md](../benchmarks.md)**
