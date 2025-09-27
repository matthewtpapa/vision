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
- Oracle drain into Verify with JSON ledger emission and maxlen/shed-rate gates.
- KB promotion pipeline with capped int8 medoids, promotion ledger, and CI gates.
- Calibration utilities with temperature fitting, EMA-based oracle abstention,
  offline calibration bench + gates, and syscall purity guard targets.
- S1: SoT foundation — seeds/fileset/signing/purity/PDF/gates + CI gate (workflow: `verify`).
- Docs: Stage specs **S01–S17** (SoT-anchored) + UTF-8 normalized SoT HTML; added docs drift check (non-gating).

### Removed

- CI: retire legacy workflows `pre_s1_check.yml`, `s1.yml`, `s2.yml`, `sot_check.yml`
  (all checks covered by `verify` + Docs Drift Check).

### Changed

- CI: consolidate to verify.yml; quarantine legacy workflows; gate summary + artifacts.

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
