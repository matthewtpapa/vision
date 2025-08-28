# Architecture

## Module Map
- video: src/vision/webcam.py
- detect: src/vision/fake_detector.py
- track: src/vision/tracker.py
- embed: src/vision/embedder.py
- match: src/vision/matcher.py
- label: src/vision/labeler.py
- kb: src/vision/cluster_store.py
- ui: overlay in webcam.py
- ris: (stub placeholder; not implemented)
- telemetry: (stub placeholder; not implemented)

## Flow
Webcam → Detect → Track → Embed → Match → Label → (KB add_exemplar) → UI overlay

## Exemplar Schema
```
{
  "label": "unknown",
  "bbox": [x1, y1, x2, y2],
  "embedding": [0.0, ... 128 floats ...],
  "provenance": {"source": "fake", "ts": "<ISO8601>", "note": "stub"}
}
```

Default path: `data/kb.json`.
