# Changelog

## [Unreleased]

### Added
- Matcher v1 with FAISS/NumPy backends, typed `MatchResult`, and pipeline introspection helpers
- docs/charter.md: slim Charter (vision, roadmap, acceptance highlights)
- docs/specs/m1.md: M1 developer spec (API, similarity semantics, telemetry schema, gates, determinism)
- docs/eval.md: --eval guide with frozen JSON/CSV schemas

### Changed

- README.md: SDK-first intro, Quickstart, links to Charter/Spec, config snippet
- CONTRIBUTING.md: clarified Charter vs Spec split and CI gates

### Notes

- No runtime code changes; docs-only reorg

## v0.0.2 - 2025-08-28

- Fixed markdownlint CI failures and blank-line issues.
- Added `.editorconfig` and `.gitattributes` for whitespace normalization.
- Strict `make mdlint` with pre-commit/npx fallback and optional `make mdfix` for auto-fixes.
- Setup and coverage targets now degrade gracefully when tooling is missing.
- Docs updated for constrained environments; CI uploads coverage artifacts and uses Makefile targets.
- New CONTRIBUTING.md describing local setup, verification, and markdown workflow.
- README badge fix to point to matthewtpapa/vision.
- Minor CI polish: added success echo after verify checks.
- Version alignment enforced: pyproject.toml, __init__.py, and CLI tests now lockstep at 0.0.2 to prevent drift.

## v0.0.1 - 2025-08-28

- Initial M0 release.
- Stub modules: FakeDetector, Tracker, Embedder, Matcher, Labeler, ClusterStore, Telemetry, ReverseImageSearchStub, and supporting utilities.
- CLI commands: `vision --version`, `vision webcam`, `vision webcam --dry-run`, and `vision webcam --use-fake-detector`.
- Documentation: project charter and architecture overview.
