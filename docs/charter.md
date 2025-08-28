# Charter

## Goal

- Deliver a minimal vision pipeline to explore detection, tracking, embedding, matching, labeling, and exemplar persistence on webcam frames (or dry run), with deterministic stubs in M0.

## Scope v0 (M0)

- Stub implementations for: Detector, Tracker, Embedder, Matcher, Labeler, Cluster Store, RIS (Reverse Image Search), and Telemetry.
- Command line interface with `vision webcam` and `--dry-run`.
- JSON persistence of exemplars (label, bbox, embedding, provenance).
- Unit tests for each stub and CLI dry-run output.

## Scope v1

- Real detection and tracking models (e.g., YOLO/RT-DETR, DeepSORT/ByteTrack).
- Replace Embedder with CLIP/OpenCLIP.
- Real RIS connector + forward search; proper similarity thresholds and smoothing.
- Telemetry backend integration; evaluation harness; label hysteresis.
- Configurable thresholds; performance tuning.

## Out of Scope (for now)

- Training custom models, quantization/acceleration.
- Multi-camera fusion/SLAM.
- Cloud DBs (start local only).

## Success Metrics (MVP)

- Latency: P95 ≤ 800 ms @ 720p (single object).
- Stability: ≥ 90% identical labels across a 2s window (stationary object).
- Unknown resolution: ≤ 3.0 s median to resolve to a label (when RIS enabled in later milestones).
- Reliability: zero crashes in a 20-minute webcam session.

## Operating Principles

- **Open-set first:** everything unknown until evidence accumulates.
- **Provenance everywhere:** store sources, timestamps, confidence trails.
- **Deterministic scaffolding:** swap implementations without churn.
- **Atomic PRs:** small, testable, reviewable increments.
- **Privacy & ToS:** persist embeddings, URLs, metadata only.

## High-Level Architecture (modules)

- `video/` — Frame capture loop (OpenCV) → `src/vision/webcam.py`
- `detect/` — Object detection (stub → YOLO/RT-DETR) → `src/vision/fake_detector.py`
- `track/` — Object tracking (stub → DeepSORT/ByteTrack) → `src/vision/tracker.py`
- `embed/` — Embedding abstraction (stub → CLIP) → `src/vision/embedder.py`
- `match/` — Similarity search → `src/vision/matcher.py`
- `label/` — Label choice → `src/vision/labeler.py`
- `kb/` — Cluster store (label, exemplars, provenance) → `src/vision/cluster_store.py`
- `ris/` — Reverse image search connector → `src/vision/ris.py`
- `telemetry/` — Metrics → `src/vision/telemetry.py`
- `ui/` — AR overlay (OpenCV) → overlay in `webcam.py`

## Deliverables

- This charter (`docs/charter.md`) and the architecture doc (`docs/architecture.md`).
- README entries that link to both docs and show exact CLI dry-run outputs.
- CI runs markdown lint and tests.

## Definition of Done

- `docs/charter.md` and `docs/architecture.md` present and linked from README.
- `pytest -q` passes; markdown lint in CI passes.
- No changes to runtime behavior; all existing tests remain green.
