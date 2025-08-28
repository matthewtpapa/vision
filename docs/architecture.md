# Architecture

## Module Map

- **video:** `src/vision/webcam.py`
- **detect:** `src/vision/fake_detector.py`
- **track:** `src/vision/tracker.py`
- **embed:** `src/vision/embedder.py`
- **match:** `src/vision/matcher.py`
- **label:** `src/vision/labeler.py`
- **kb:** `src/vision/cluster_store.py`
- **ris:** `src/vision/ris.py`
- **telemetry:** `src/vision/telemetry.py`
- **ui:** overlay drawing in `webcam.py`

## Pipeline (M0)

Webcam (or Dry Run)
→ Detect (FakeDetector)
→ Track (Tracker)
→ Embed (Embedder)
→ Match (Matcher)
→ Label (Labeler)
→ Cluster Store (add_exemplar with provenance)
→ UI Overlay (rectangles, ID, label)

## Exemplar Schema (JSON)

```json
{
  "label": "unknown",
  "bbox": [x1, y1, x2, y2],
  "embedding": [0.0, "... 128 floats ..."],
  "provenance": { "source": "fake", "ts": "<ISO8601>", "note": "stub" }
}

```

Default path: data/kb.json

Persistence is atomic (temp file replace).

Notes

Dry run exercises the full control flow without requiring OpenCV or network access.

RIS and Telemetry are stubs in M0; real integrations come in M1+.

All modules are unit-tested stubs; CI runs tests and markdown lint.
