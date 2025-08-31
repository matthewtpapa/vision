# SPDX-License-Identifier: Apache-2.0
"""Timing helpers for lightweight telemetry.

This module provides a minimal in-memory aggregator for stage timings along
with a context manager that measures execution duration. It is intentionally
simple so it can be replaced by a real metrics backend in later milestones.
"""

from __future__ import annotations

import time
from pathlib import Path

now_ns = time.perf_counter_ns


class StageTimer:
    """Context manager that records elapsed time for a pipeline stage."""

    def __init__(self, sink: Telemetry, stage: str) -> None:
        self._sink = sink
        self._stage = stage
        self._t0 = 0

    def __enter__(self) -> StageTimer:
        self._t0 = now_ns()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        dt_ms = (now_ns() - self._t0) / 1e6
        self._sink.record(self._stage, dt_ms)


class Telemetry:
    """Aggregator for timing metrics."""

    def __init__(self) -> None:
        self._stats: dict[str, list[float]] = {}

    def record(self, stage: str, ms: float) -> None:
        self._stats.setdefault(stage, []).append(float(ms))

    def summary(self) -> dict[str, dict[str, float]]:
        summary: dict[str, dict[str, float]] = {}
        for stage, samples in self._stats.items():
            count = float(len(samples))
            total = float(sum(samples))
            mean = total / count if count else 0.0
            max_ms = max(samples) if samples else 0.0
            summary[stage] = {
                "count": count,
                "total_ms": total,
                "mean_ms": mean,
                "max_ms": max_ms,
            }
        return summary

    def to_csv(self) -> str:
        lines = ["stage,count,total_ms,mean_ms,max_ms"]
        for stage in sorted(self._stats):
            samples = self._stats[stage]
            count = len(samples)
            total = sum(samples)
            mean = total / count if count else 0.0
            max_ms = max(samples) if samples else 0.0
            lines.append(f"{stage},{count},{total},{mean},{max_ms}")
        return "\n".join(lines)

    def write_csv(self, path: str | Path) -> None:
        """Persist ``to_csv`` output to ``path`` atomically."""

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(self.to_csv(), encoding="utf-8")
        tmp.replace(p)
