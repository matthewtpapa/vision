# Project Charter and Vision

## North Star

Deliver a real-time, open-set recognition SDK: detect, track, embed, and match objects in live video against a continually growing exemplar knowledge base.

- Sustains latency-bounded performance on reference hardware
- Modular and backend-agnostic
- Exposes a simple, typed Python API
- Serves AR, robotics, and vision pipelines as infrastructure
- Not a consumer app — this is **FFmpeg-for-open-set recognition**: boring, reliable infra that others depend on.

## Roadmap (M2 gates)

- M2-01 LabelBank core — deterministic protocol (done)
- M2-02 LabelBank shard+bench — lookup_p95_ms ≤ 10.0; recall@10 ≥ 0.99 (done)
- M2-03 Verify calibration + wiring — unknown false-known ≤ 1%; types green
- M2-04 CandidateOracle — candidate@5_recall ≥ 0.95; topk_p95_ms ≤ 5.0
- M2-05 Unknown path → Oracle→Verify→Ledger — e2e_p95 ≤ 33.0; p@1 ≥ 0.80
- M2-06 SLO controller — p95 ≤ 33ms; p99 ≤ 66ms; cold_start ≤ 1100ms; index_bootstrap ≤ 50ms (≤10k labels on 2-vCPU)
- M2-07 Repro + telemetry schema — stable metrics_hash across A/B runs
- M2-08 CI & release hygiene — artifacts attached (benches, metrics_hash, precedence)
- M2-09 Purity & supply-chain — no network in hot loop; purity_report.json = zeros

## Invariants

- No runtime RIS (offline only).
- Deterministic outputs; schema stability.
- Evidence-first growth: accepts → ledger → capped int8 medoids (≤3/class) in offline promotion.

## Process Guardrails

- **Charter (this doc)** → sets vision, roadmap, and themes. Evolves slowly (reviewed at major milestones)
- **Specs (per milestone)** → exact contracts, telemetry schemas, CI gates. Evolve quickly, live close to code
- Charter answers "what and why"; Specs answer "how and with what guarantees"
