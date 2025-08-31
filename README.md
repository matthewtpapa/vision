# Vision SDK — Open-Set Recognition for Real-Time Apps

Latency-bounded open-set recognition SDK — predictable, measurable, embeddable in AR/robotics pipelines.

<!-- markdownlint-disable-next-line MD001 -->
> ### Name mapping (current → M1.1)
>
> **Today (this repo):**
>
> - PyPI/package: `vision` (dev install)
> - Import: `vision`
> - CLI: `python -m vision` (or `vision` via entry point)
>
> **M1.1 target (investor-grade):**
>
> - PyPI: `latency-vision`
> - Import: `latency_vision`
> - CLI: `latvision`  *(best-effort alias: `vision`)*

## Install

```bash
pip install vision-sdk
```

## Quickstart

### (M1.1 façade – target)

```python
import numpy as np
from latency_vision import add_exemplar, query_frame

add_exemplar("red-mug", np.random.rand(512).astype("float32"))
frame = np.zeros((640, 640, 3), dtype=np.uint8)
result = query_frame(frame)
print(result["label"], result["confidence"], result["backend"])
```

Note: The façade lands in a subsequent PR. Until then, use the current snippet:

(Current repo – today)

```python
import numpy as np
from vision import add_exemplar, query_frame  # placeholder; façade arrives in a later PR

# API shape will match the schema v0.1 in docs/schema.md
add_exemplar(label="red-mug", embedding=np.random.rand(512).astype("float32"))
frame = np.zeros((640, 640, 3), dtype=np.uint8)
result = query_frame(frame)
print(result["label"], result.get("confidence"), result.get("is_unknown"))
```

## Docs

- Charter (vision & roadmap): **[docs/charter.md](docs/charter.md)**
- Milestone M1.1 Spec (Gates A–D): **[docs/specs/m1.1.md](docs/specs/m1.1.md)**
- Result Schema v0.1 (frozen): **[docs/schema.md](docs/schema.md)**
- Latency & process model: **[docs/latency.md](docs/latency.md)**
- Benchmarks methodology: **[docs/benchmarks.md](docs/benchmarks.md)**
- Third-party attributions: **[THIRD_PARTY.md](THIRD_PARTY.md)**

## Demo path (coming in M1.1)

```bash
pip install latency-vision
latvision hello
latvision eval --frames 2000 --seed 42 --kb 1000 --budget-ms 33 \
  --report out/metrics.json --stages out/stage_timings.csv
make plot
```

latvision hello prints OS/Python, SIMD flags (AVX2/NEON/no-SIMD), backend availability, and versions.

### Schema v0.1

This project ships a **frozen** result schema for the 0.1.x series. See
**[docs/schema.md](docs/schema.md)** for the contract and invariants.

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
  "sdk_version": "0.1.1"
}
```

> **Important:** Keep the README example **byte-for-byte identical** to the one in `docs/schema.md`. Subsequent PRs will add CI guards to prevent drift.

## CLI

Invoke the evaluator to emit latency metrics and telemetry:

```bash
python -m vision eval --input <dir> --output <dir> --warmup <int>
```

Running from a source checkout? Use the local fallback:

```bash
PYTHONPATH=src python -m vision eval …
```

Required dependencies: `numpy` and `pillow`. A friendly guard exits with code `3` if either is missing.

Exit codes:

- `0` — success
- `2` — `p95` latency budget breached
- `3` — missing `numpy` or `pillow`

The evaluator can adaptively skip frames to stay within the latency budget; see the **[Eval Guide](docs/eval.md)** and **[Latency Guide](docs/latency.md)** for controller details.

See [Benchmarks](docs/benchmarks.md)
for measurement details and artifact fields. Try `make bench` then `make plot` to generate local metrics and a latency PNG. See docs/benchmarks.md for details.

Example with environment overrides:

```bash
VISION__LATENCY__BUDGET_MS=33 \
VISION__PIPELINE__AUTO_STRIDE=0 \
python -m vision eval --input <dir> --output <dir>
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

## Architecture (M1 vertical slice)

Webcam → Detect (YOLO) → Track (ByteTrack) → Embed (CLIP-B32) → Match (FAISS/NumPy) → Label/Unknown → Persist Exemplar → Telemetry

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs should not change both Charter and Spec in one go; Specs track code, Charter evolves at milestone boundaries.

## License

Apache-2.0 — see LICENSE and NOTICE
