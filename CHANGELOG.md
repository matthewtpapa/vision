# Changelog

## v0.0.2 - 2025-08-28

- Finalize M0 harden & polish:
  - Fixed markdownlint CI failure and added local markdownlint (pre-commit) with the same rules as CI.
  - Added `.editorconfig` and `.gitattributes` to standardize whitespace/line endings across OSes.
  - New `make verify` (one command to run lint, format check, types, tests, markdownlint).
  - Documented local/CI parity and workflow in README.
  - CI calls Makefile targets (single source of truth).
  - Dev tools pinned to stable ranges to reduce churn.
  - Coverage artifacts always uploaded.
  - Markdownlint runs in CI only; no local Node/npm required.
  - Docs updated: CI status note, coverage workflow, and optional local coverage steps.
  - Local coverage target fails fast when `pytest-cov` is missing; CI remains the source of truth.

## v0.0.1 - 2025-08-28

- Initial M0 release.
- Stub modules: FakeDetector, Tracker, Embedder, Matcher, Labeler, ClusterStore, Telemetry, ReverseImageSearchStub, and supporting utilities.
- CLI commands: `vision --version`, `vision webcam`, `vision webcam --dry-run`, and `vision webcam --use-fake-detector`.
- Documentation: project charter and architecture overview.
