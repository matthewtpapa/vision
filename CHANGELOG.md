# Changelog

## v0.0.2 - 2025-08-28

- Finalize M0 harden & polish:
  - CI calls Makefile targets (single source of truth).
  - Dev tools pinned to stable ranges to reduce churn.
  - Coverage artifacts always uploaded.
  - Markdownlint runs in CI only; no local Node/npm required.
  - Docs updated: CI status note and coverage workflow.
  - Local coverage target fails fast when `pytest-cov` is missing; CI remains the source of truth.

## v0.0.1 - 2025-08-28

- Initial M0 release.
- Stub modules: FakeDetector, Tracker, Embedder, Matcher, Labeler, ClusterStore, Telemetry, ReverseImageSearchStub, and supporting utilities.
- CLI commands: `vision --version`, `vision webcam`, `vision webcam --dry-run`, and `vision webcam --use-fake-detector`.
- Documentation: project charter and architecture overview.
