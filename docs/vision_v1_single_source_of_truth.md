# Vision v1 — Single Source of Truth

This document serves as the authoritative reference for the Vision v1 investor
materials. It outlines the high-level narrative, core metrics, and compliance
anchors that downstream artifacts must reflect.

## Narrative Pillars

1. **Latency Leadership** – Vision delivers sub-5ms p95 candidate recall in the
   offline oracle benchmark while maintaining 0.95+ candidate@k recall.
2. **Deterministic Evidence Chain** – Benchmarks, ledgers, and manifests are
   reproducible through hash-chained append-only records and pinned environment
   seeds.
3. **Investor-Ready Transparency** – Every claim is backed by machine-verifiable
   artifacts stored under version control.

## Key Metrics

| Metric | Value | Source |
| --- | --- | --- |
| Offline candidate@k recall | ≥ 0.95 | `bench/oracle_stats.json` |
| Offline p95 latency | ≤ 5.0ms | `bench/oracle_stats.json` |
| E2E p@1 | ≥ 0.80 | `bench/oracle_e2e.json` |
| E2E p95 latency | ≤ 33.0ms | `bench/oracle_e2e.json` |

## Compliance Checklist

- [x] Benchmarks executed on deterministic commit.
- [x] Ledger tip recorded via `scripts/ledger_tip.py`.
- [x] Manifest + lock synchronized via `scripts/fileset.py`.
- [x] Purity witness stored at `artifacts/purity_report.json`.

## Change Control

Changes to this document must be reviewed by the Vision governance group.
Updates require a corresponding ledger entry and refreshed manifest signature.
