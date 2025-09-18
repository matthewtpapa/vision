# Changelog

All notable changes to this project are documented in this file.

<!-- markdownlint-disable MD024 -->

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- New: cold-start definition/measurement anchor.
- New: `metrics_schema_version` and optional `process_cold_start_ms`.
- CLI: `--duration-min` wording + `--unknown-rate-band` precedence clarified.
- Tests: precedence + cold-start startpoint.
- Offline P31 LabelBank shard builder and deterministic micro-benchmark with stable `bench_struct_hash` (structure-only; latency p95/recall gates still enforced separately).
- Verification manifest, calibration script, and integration with evaluation metrics.
- Reproducibility harness for metrics hashing.
- CI guard banning forbidden RIS tokens and hot-loop syscall audit.

## [0.1.0-rc.2] - 2025-09-15

### Added

- Package flip to `latency-vision` with façade freeze. (Issue 1)
- manylinux2014, universal2, and Windows wheels via cibuildwheel. (Issue 3)
- Windows demo gate. (Issue 4)
- README Quickstart. (Issue 5)
- Deterministic fixture and `stage_times` output. (Issue 6)
- Publish workflow. (Issue 7)

## [0.1.0-rc.1] - 2025-09-01

### Added

- M1.1 vertical slice with evaluator, fixture builder, and plots.
