# ADR 0001: Oracle-first

## Decision

Oracle-first loop = LabelBank ANN → bounded CandidateOracle → curated Verify → KB promotion (capped medoids) with EvidenceLedger.

## Invariants

- No runtime RIS in hot loop (RIS allowed only in offline ingestion).
- Thresholds are quantile-calibrated per shard (no global constants).
- KB medoids are int8, ≤ 3 per class (herding + caps).
- Gates/SLOs: p95≤33ms, p99≤66ms, fps≥25; cold_start≤1100ms; index_bootstrap≤50ms; LabelBank p95≤10ms & recall@10≥0.99; repro hash; resource caps; supply-chain hygiene; queue depth≤64 & shed-rate≤5%.
- Hot-loop purity: zero network I/O (validated via strace in CI; syscall_report.txt artifact)

## Module boundaries & non-goals

Modules: LabelBank, CandidateOracle, Verify, KB promotion, EvidenceLedger, LabelBankProtocol.
Non-goals: no changes to detect/track/embed/matcher APIs here.
