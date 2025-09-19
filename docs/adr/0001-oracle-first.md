# ADR 0001: Oracle-first

## Decision

Oracle-first loop = LabelBank ANN → bounded CandidateOracle → curated Verify → KB promotion (capped medoids) with EvidenceLedger.

## Invariants

- No runtime RIS in hot loop (RIS allowed only in offline ingestion).
- Thresholds are quantile-calibrated per shard (no global constants).
- KB medoids are int8, ≤ 3 per class (herding + caps).
- Gates/SLOs: p95≤33ms, p99≤66ms, fps≥25; cold_start≤1100ms; index_bootstrap≤50ms; LabelBank p95≤10ms & recall@10≥0.99; repro hash; resource caps; supply-chain hygiene; queue depth≤64 & shed-rate≤5%.
- Hot-loop purity: zero network I/O (validated via strace in CI; syscall_report.txt artifact)
- Read-only LabelBank lookups run on unknown frames; enqueue uses a bounded queue that drops the oldest entries and tracks shed count; no network in the hot loop.

## Module boundaries & non-goals

Modules: LabelBank, CandidateOracle, Verify, KB promotion, EvidenceLedger, LabelBankProtocol.
Non-goals: no changes to detect/track/embed/matcher APIs here.

## M2-03 scope (default configuration)

- Verify remains in-line for all emissions; the Oracle queue exists but abstains by default so runtime behaviour matches M2-03 guardrails.
- Evidence derives solely from LabelBank lookups; KB promotion artifacts are generated offline and not enforced during evaluation.
- Runtime RIS is still prohibited in the hot loop and enforced via CI.
