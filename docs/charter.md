# Charter

## Goal
- Deliver a minimal vision pipeline to explore detection, tracking, embedding and matching on webcam frames.

## Scope v0
- Stub implementations for Detector, Tracker, Embedder, Matcher, Labeler and Cluster Store.
- Command line interface with webcam loop and dry-run mode.

## Scope v1
- Real detection and tracking models.
- RIS and telemetry modules with metrics collection.
- Persistence beyond local JSON exemplars.

## Out of Scope
- Production-grade models or optimizations.
- External network calls and RIS integration.
- Cloud storage or database backends.

## Success Metrics
- Latency P95 ≤ 800ms @720p.
- Pipeline initializes in ≤2s.
- Dry run completes without errors.

## Operating Principles
- Keep components loosely coupled.
- Prefer simple, deterministic stubs in M0.
- Ensure every module has unit tests.

## High-Level Architecture
- Webcam captures frames.
- Frames pass through Detector, Tracker, Embedder, Matcher and Labeler.
- Exemplars stored via Cluster Store; RIS/telemetry deferred.

## Deliverables
- CLI with webcam command.
- Stub modules for each stage.
- Documentation and tests.

## DoD
- Tests and linters pass.
- README and examples match behavior.
- CI pipeline verifies dry-run path.

## Reality Check (M0)
- Implemented stubs: FakeDetector, Tracker, Embedder, Matcher, Labeler, ClusterStore; wired in webcam loop.
- Deferred: ris/, telemetry/ modules and metrics collection (planned for M1).
- Persistence: JSON exemplars with provenance to data/kb.json.
