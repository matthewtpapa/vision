# Changelog

## v0.0.2 - 2025-08-28

- Fixed markdownlint CI failures and blank-line issues.
- Added `.editorconfig` and `.gitattributes` for whitespace normalization.
- `make mdlint` falls back to pre-commit, npx, or skips with a warning.
- Setup and coverage targets now degrade gracefully when tooling is missing.
- Docs updated for constrained environments; CI uploads coverage artifacts and uses Makefile targets.

## v0.0.1 - 2025-08-28

- Initial M0 release.
- Stub modules: FakeDetector, Tracker, Embedder, Matcher, Labeler, ClusterStore, Telemetry, ReverseImageSearchStub, and supporting utilities.
- CLI commands: `vision --version`, `vision webcam`, `vision webcam --dry-run`, and `vision webcam --use-fake-detector`.
- Documentation: project charter and architecture overview.
