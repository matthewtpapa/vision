# Vision SDK — Open-Set Recognition for Real-Time Apps

Latency-bounded open-set recognition SDK — predictable, measurable, embeddable in AR/robotics pipelines.

Why now: transformer encoders + FAISS + laptop-class CPUs make real-time open-set feasible on commodity hardware.

> **Name mapping**
>
> - PyPI: `latency-vision`
> - Import: `latency_vision`
> - CLI: `latvision`
> - `vision` (alias; deprecated)

`vision` remains a temporary alias of `latvision` (deprecated).

## Install

Base (NumPy matcher fallback):

```bash
pip install latency-vision
```

Faster cosine search (CPU FAISS; macOS/Linux):

```bash
pip install "latency-vision[speed]"
```

GPU FAISS (Linux/macOS where supported):

```bash
pip install "latency-vision[gpu]"
```

Windows defaults to the NumPy backend unless FAISS wheels are available.

Until PyPI publish, run locally with: PYTHONPATH=src latvision …

## Quickstart

Prereq: `pip install numpy`

### SDK façade

```python
# (Available)
import numpy as np
from latency_vision import add_exemplar, query_frame

add_exemplar("red-mug", np.random.rand(512).astype("float32"))
frame = np.zeros((640, 640, 3), dtype=np.uint8)
result = query_frame(frame)
print(result["label"], result["confidence"], result["backend"])
```

### Demo: hello → eval → plot

```bash
# 1) Hello — environment snapshot
latvision hello

# 2) Eval — build a tiny fixture, run evaluator, print summary
python scripts/build_fixture.py --seed 42 --out bench/fixture --n 400
PYTHONPATH=src latvision eval --input bench/fixture --output bench/out
python scripts/print_summary.py --metrics bench/out/metrics.json  # prints index_bootstrap_ms alongside other latency metrics
# Example:
# fps=... p95=... p99=... cold_start_ms=... index_bootstrap_ms=... unknown_rate=... sustained_in_budget=... metrics_schema_version=... frames=... processed=... backend=... sdk=... stride=... window_p95=...

# 3) Plot (optional)
python scripts/plot_latency.py --input bench/out/stage_times.csv
# Writes bench/out/latency.png
```

## Gold Path

Run the hardened CI pipeline locally to reproduce the release gate output:

```bash
make prove
make kb-promote
```

- Network forbidden in benches/hot loop; enforced by purity guard.
- Network allowed only in supply-chain (SBOM/wheel download) stage.
- Supply-chain is a hard gate on license allowlist; artifacts upload even on red.

Artifacts are written to `artifacts/` (metrics hashes, SBOM, license report, wheel
hashes, purity outputs, promotion report), and log files land in `logs/`.

## How CI proves claims

Jobs: **“SoT-Check (S1)”**, **“SoT-Check (S2)”**.

## Roadmap

- M2-01 LabelBank core — deterministic protocol (done)
- M2-02 LabelBank shard+bench — lookup_p95_ms ≤ 10.0; recall@10 ≥ 0.99 (done)
- M2-03 Verify calibration + wiring — unknown false-known ≤ 1%; types green
- M2-04 CandidateOracle — candidate@5_recall ≥ 0.95; topk_p95_ms ≤ 5.0
- M2-05 Unknown path → Oracle→Verify→Ledger — e2e_p95 ≤ 33.0; p@1 ≥ 0.80
- M2-06 SLO controller — p95 ≤ 33ms; p99 ≤ 66ms; cold_start ≤ 1100ms; index_bootstrap ≤ 50ms (≤10k labels on 2-vCPU)
- M2-07 Repro + telemetry schema — stable metrics_hash across A/B runs
- M2-08 CI & release hygiene — artifacts attached (benches, metrics_hash, precedence)
- M2-09 Purity & supply-chain — no network in the hot loop; purity_report.json = zeros

> Invariant: No network in the hot loop. Runtime never performs RIS/web requests. Oracle proposes from local sources; Verify uses a curated local gallery.

## M2 — Oracle-first

| Metric | Target |
| --- | --- |
| p95_ms | ≤33 |
| p99_ms | ≤66 |
| cold_start_ms | ≤1100 |
| index_bootstrap_ms | ≤50 |
| unknown_rate | 0.10–0.40 |
| LabelBank lookup_p95_ms | ≤10 |
| LabelBank recall@10 | ≥0.99 |

> **M2-03 scope:** Verify remains in the live loop and Oracle abstains by default; LabelBank supplies the only runtime evidence while KB promotion stays offline. Ledger writes are disabled unless `VISION__ENABLE_VERIFY_LEDGER=1`. CI feature flags (all default to `0`) expose follow-on gates: `ENABLE_M204` (Oracle queue), `ENABLE_M205` (KB promotion), and `ENABLE_SUPPLY` (supply-chain scans).

Set `VISION__LABELBANK__SHARD=bench/labelbank/shard` to enable offline LabelBank lookups.
`make verify-eval` constrains the oracle queue via `VISION__ORACLE__MAXLEN=64` so shed-rate gates
match CI.
M2-04 wires unknown frames through a read-only LabelBank top-k pass and enqueues results on a bounded
in-memory `CandidateOracle`; accepted candidates append to `bench/verify/ledger.jsonl` after
verification.
`make kb-promote` ingests the accepted ledger, caps medoids at three per class, writes
`bench/kb/medoids/<label>.int8.npy` + metadata, and records the promotion in
`bench/kb/promotion_ledger.jsonl` for audits.

Exit codes: 0 success · 2 user/data error (bad path, empty/invalid files) · 3 missing optional dep (pillow, matplotlib).

See docs/latency.md (process model), docs/benchmarks.md (method: monotonic_ns, NumPy percentile “linear”, warm-up exclusion, GC/BLAS notes, CPU features), docs/schema.md (v0.1 JSON contract), and docs/schema-guide.md.

## Docs

- Charter (vision & roadmap): **[docs/charter.md](docs/charter.md)**
- Oracle-first ADR: **[docs/adr/0001-oracle-first.md](docs/adr/0001-oracle-first.md)**
- Result Schema v0.1 (frozen): **[docs/schema.md](docs/schema.md)**
- Schema guide: **[docs/schema-guide.md](docs/schema-guide.md)**
- Latency & process model: **[docs/latency.md](docs/latency.md)**
- Benchmarks methodology: **[docs/benchmarks.md](docs/benchmarks.md)**
- Third-party attributions: **[THIRD_PARTY.md](THIRD_PARTY.md)**

### Schema v0.1

This project ships a **frozen** result schema for the 0.1.x series. See
**[docs/schema.md](docs/schema.md)** for the contract and invariants and
**[docs/schema-guide.md](docs/schema-guide.md)** for metrics field guidance.

**Example `MatchResult` (v0.1):**

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

> **Important:** Keep the README example **byte-for-byte identical** to the one in `docs/schema.md`. Subsequent PRs will add CI guards to prevent drift.

## CLI

Invoke the evaluator to emit latency metrics and telemetry:

```bash
latvision eval --input <dir> --output <dir> --warmup <int>
```

Running from a source checkout? Use the local fallback:

```bash
PYTHONPATH=src latvision eval …
```

Dependencies:

- **numpy** — required
- **pillow** — required when evaluating from image directories (e.g., PNG fixtures)
- **matplotlib** — optional; only needed for `scripts/plot_latency.py`

Guards print a clear message and exit with code `3` when an optional dep is missing.

Exit codes:

- `0` — success
- `2` — user/data error (bad path, empty/invalid files)
- `3` — missing optional dependency (`pillow`, `matplotlib`)

### Flags

- `--duration-min` (replaces any "sustain-minutes" mentions)
- `--unknown-rate-band LOW,HIGH` is optional; precedence = env `VISION__UNKNOWN_RATE_BAND` > CLI > input manifest > default [0.10,0.40]
- Cold-start is defined as [SDK ready (post-deps, pipeline initialized) → first MatchResult](docs/benchmarks.md#cold-start-definition)
- See [schema](docs/schema.md) and [schema guide](docs/schema-guide.md) for `metrics_schema_version`, resolved `unknown_rate_band`, and the debug-only `process_cold_start_ms`

The evaluator can adaptively skip frames to stay within the latency budget; see the **[Eval Guide](docs/eval.md)** and **[Latency Guide](docs/latency.md)** for controller details.

Example with environment overrides:

```bash
VISION__LATENCY__BUDGET_MS=33 \
VISION__PIPELINE__AUTO_STRIDE=0 \
latvision eval --input <dir> --output <dir>
```

## Config

All tunables live in `vision.toml` (env overrides supported). Useful keys:

```toml
[matcher]
topk = 5
threshold = 0.35
min_neighbors = 1

[paths]
kb_json = "data/kb.json"

[latency]
budget_ms = 33

[pipeline]
frame_stride = 1
```

## Make targets

Helpful development targets:

| Target | Description |
|--------|-------------|
| `make labelbank-shard` | build the offline P31 shard |
| `make labelbank-bench` | run the LabelBank micro-benchmark |
| `make verify-calibrate` | derive VerifyWorker calibration thresholds |
| `make verify-eval` | run evaluation with verification metrics |
| `make calib` | run the calibration bench on the offline shard |
| `make gate-calib` | enforce calibration thresholds (ECE/AUROC/oracle latency) |
| `make gate-purity` | run the hot-loop purity audit (deny shim + strace); emits `artifacts/purity_report.json` |
| `make repro` | compare metrics JSONs for reproducibility |

## Architecture (M2 oracle-first hot loop)

Detector → Tracker → Embedder → Match → (if unknown) Oracle → Verify → Ledger

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs should not change both Charter and Spec in one go; Specs track code, Charter evolves at milestone boundaries.

## License

Apache-2.0 — see LICENSE and NOTICE

[Contributing](CONTRIBUTING.md) • [Changelog](CHANGELOG.md)
