# Result Schema — v0.1 (Frozen for 0.1.x)

This document freezes the public result object returned by the façade API
(e.g., `query_frame(...)`) and emitted by the CLI evaluator. Any breaking
change to this schema is disallowed in the 0.1.x series.

> Purpose: investor-grade stability for demos, RC artifact validation, and
> future CI guards that load golden JSON.

---

## Object: `MatchResult` (v0.1)

| Field          | Type                                    | Required | Notes                                                                                 |
|----------------|-----------------------------------------|----------|---------------------------------------------------------------------------------------|
| `label`        | `string` \| `"unknown"`                 | yes      | Top-1 label or `"unknown"` under open-set policy.                                     |
| `confidence`   | `number`                                | yes      | Top-1 cosine score in `[-1, 1]` (uncalibrated).                                       |
| `neighbors`    | `array` of `{label: string, score: number}` | yes  | Sorted desc by `score`; at least 0 elements; `score` in `[-1, 1]`.                    |
| `backend`      | `"faiss"` \| `"numpy"`                  | yes      | Active matcher backend.                                                               |
| `stride`       | `integer`                               | yes      | Current frame stride used by the controller (≥1).                                     |
| `budget_hit`   | `boolean`                               | yes      | True if the controller skipped/adjusted this frame to respect the latency budget.     |
| `bbox`         | `[number, number, number, number]` \| `null` | yes  | `[x1, y1, x2, y2]` if a best region is known; otherwise `null`.                   |
| `timestamp_ms` | `integer`                                | no       | Milliseconds since epoch (monotonic/approx wall clock acceptable).                    |
| `sdk_version`  | `string`                                 | yes      | Semver of the SDK producing this result (e.g., `"0.1.1"`).                            |

### Invariants

- `neighbors` items must respect: `-1.0 ≤ score ≤ 1.0`.
- If `label != "unknown"`, it **should** match `neighbors[0].label` (when present).
- `stride ≥ 1`. Controller is stride/skip only; no model-degrade path in v0.1.
- `bbox` is present but may be `null` if the pipeline cannot localize.

---

## Example `MatchResult` (valid v0.1)

```json
{
  "label": "red-mug",
  "confidence": 0.78,
  "neighbors": [
    { "label": "red-mug", "score": 0.78 },
    { "label": "maroon-cup", "score": 0.65 }
  ],
  "backend": "numpy",
  "stride": 1,
  "budget_hit": false,
  "bbox": [120, 96, 220, 196],
  "timestamp_ms": 1725043200123,
  "sdk_version": "0.1.1"
}
```

Notes & Forward Compatibility

Frozen: Field removals/renames are not allowed in 0.1.x.

Additive fields may be introduced in 0.2.0 with a new schema doc.

CLI metrics envelopes (e.g., controller/config, stage means) are not
part of MatchResult; they are covered by the benchmarking docs.

Related docs:

Milestone spec & gates: docs/specs/m1.1.md

Latency controller & process model: docs/latency.md

Benchmarks methodology: docs/benchmarks.md
