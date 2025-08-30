# Vision SDK — Open-Set Recognition for Real-Time Apps

**Problem:** Apps need to recognize *any* object, not just classes a model was trained on — and do it in real time on edge/consumer hardware.  
**Solution:** A modular SDK that detects, tracks, embeds, and **matches** crops against a growing exemplar KB, with tight latency budgets and boring reliability.

**Who it's for:** AR, robotics, and vision teams that want infra, not a consumer app. Think *FFmpeg for open-set recognition.*

## Install
 
```bash
pip install vision-sdk
```

## Quickstart

```python
import numpy as np
from vision import add_exemplar, query_frame

# Add a known exemplar (embedding can be raw; SDK will L2-normalize float32)
add_exemplar(
    label="red-mug",
    embedding=np.random.rand(512).astype("float32"),
    bbox=None,
    provenance={"source": "example"},
)

# Query a frame (numpy image array)
frame = np.zeros((640, 640, 3), dtype=np.uint8)
result = query_frame(frame)
print(result["label"], result.get("confidence"), result.get("is_unknown"))
```

## CLI

Evaluate latency and export telemetry:

```bash
vision --eval --input examples/eval_frames --output out/
cat out/metrics.json
```

Schema and details: see **[Eval Guide](docs/eval.md)**.

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

## Roadmap & Spec

- Charter (north star, roadmap): [docs/charter.md](docs/charter.md)
- M1 Spec (contracts, schemas, gates): [docs/specs/m1.md](docs/specs/m1.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs should not change both Charter and Spec in one go; Specs track code, Charter evolves at milestone boundaries.

## License

Apache-2.0 (TBD; see LICENSE)
