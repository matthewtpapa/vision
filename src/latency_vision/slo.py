"""Service level objective gates for latency vision benches."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SLOGates:
    """SLO thresholds enforced across offline and e2e benches."""

    offline_recall: float = 0.95
    offline_p95_ms: float = 10.0
    e2e_p_at_1: float = 0.80
    e2e_p95_ms: float = 33.0


def _coerce_metric(metrics: Mapping[str, float], key: str) -> float:
    try:
        value = metrics[key]
    except KeyError as exc:
        raise KeyError(f"missing metric: {key}") from exc
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"metric {key!r} must be numeric, received {type(value)!r}")
    return float(value)


def assert_slo(
    *,
    offline_stats: Mapping[str, float],
    e2e_stats: Mapping[str, float],
    gates: SLOGates = SLOGates(),
) -> None:
    """Assert that measured metrics meet the configured gates."""

    recall = _coerce_metric(offline_stats, "candidate_at_k_recall")
    lookup_p95 = _coerce_metric(offline_stats, "p95_ms")
    p_at_1 = e2e_stats.get("p_at_1")
    if p_at_1 is None and "p@1" in e2e_stats:
        p_at_1 = e2e_stats["p@1"]
    if p_at_1 is None:
        raise KeyError("missing metric: p_at_1")
    if isinstance(p_at_1, bool) or not isinstance(p_at_1, int | float):
        raise TypeError("metric 'p_at_1' must be numeric")
    e2e_p95 = _coerce_metric(e2e_stats, "e2e_p95_ms")

    if recall < gates.offline_recall:
        raise AssertionError(f"offline recall {recall:.4f} < gate {gates.offline_recall:.4f}")
    if lookup_p95 > gates.offline_p95_ms:
        raise AssertionError(f"offline p95 {lookup_p95:.4f}ms > gate {gates.offline_p95_ms:.4f}ms")
    p_at_1 = float(p_at_1)
    if p_at_1 < gates.e2e_p_at_1:
        raise AssertionError(f"p@1 {p_at_1:.4f} < gate {gates.e2e_p_at_1:.4f}")
    if e2e_p95 > gates.e2e_p95_ms:
        raise AssertionError(f"e2e p95 {e2e_p95:.4f}ms > gate {gates.e2e_p95_ms:.4f}ms")


__all__ = ["SLOGates", "assert_slo"]
