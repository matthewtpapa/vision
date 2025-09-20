# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SLOGates:
    """Latency SLO thresholds (milliseconds)."""

    p95_ms: float = 33.0
    p99_ms: float = 66.0
    cold_start_ms: float = 1100.0
    index_bootstrap_ms: float = 50.0


def assert_slo(
    p95: float,
    p99: float,
    *,
    cold: float | None = None,
    boot: float | None = None,
    g: SLOGates = SLOGates(),
) -> None:
    if p95 > g.p95_ms or p99 > g.p99_ms:
        raise AssertionError(f"SLO fail p95={p95:.3f} p99={p99:.3f}")
    if cold is not None and cold > g.cold_start_ms:
        raise AssertionError(f"SLO fail cold_start={cold:.3f}ms > {g.cold_start_ms:.3f}ms")
    if boot is not None and boot > g.index_bootstrap_ms:
        raise AssertionError(
            f"SLO fail index_bootstrap={boot:.3f}ms > {g.index_bootstrap_ms:.3f}ms"
        )
