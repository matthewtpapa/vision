# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Helpers for summarising evaluation latency metrics."""

from __future__ import annotations

from statistics import fmean
from typing import Literal


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (q / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return float(d0 + d1)


def metrics_json(
    per_frame_ms: list[float],
    per_stage_ms: dict[str, list[float]],
    unknown_flags: list[bool],
    kb_size: int,
    backend_selected: Literal["faiss", "numpy"],
    sdk_version: str,
    *,
    warmup: int = 0,
    slo_budget_ms: float = 33.0,
) -> dict:
    """Return an aggregated metrics dictionary.

    ``warmup`` specifies the number of initial samples to exclude from the
    statistics. ``slo_budget_ms`` is used to compute the percentage of frames
    within the latency SLO budget.
    """

    if warmup > 0:
        per_frame_ms = per_frame_ms[warmup:]
        unknown_flags = unknown_flags[warmup:]
        per_stage_ms = {k: v[warmup:] for k, v in per_stage_ms.items()}

    fps = 1000.0 / fmean(per_frame_ms) if per_frame_ms else 0.0
    p50 = _percentile(per_frame_ms, 50.0)
    p95 = _percentile(per_frame_ms, 95.0)
    p99 = _percentile(per_frame_ms, 99.0)

    stage_means: dict[str, float] = {}
    stages = ("detect", "track", "embed", "match")
    for stage in stages:
        samples = per_stage_ms.get(stage, [])
        stage_means[stage] = fmean(samples) if samples else 0.0

    overheads: list[float] = []
    for idx, frame_ms in enumerate(per_frame_ms):
        d = per_stage_ms.get("detect", [])
        t = per_stage_ms.get("track", [])
        e = per_stage_ms.get("embed", [])
        m = per_stage_ms.get("match", [])
        detect_ms = d[idx] if idx < len(d) else 0.0
        track_ms = t[idx] if idx < len(t) else 0.0
        embed_ms = e[idx] if idx < len(e) else 0.0
        match_ms = m[idx] if idx < len(m) else 0.0
        overheads.append(frame_ms - (detect_ms + track_ms + embed_ms + match_ms))
    stage_means["overhead"] = fmean(overheads) if overheads else 0.0

    unknown_rate = (sum(unknown_flags) / len(unknown_flags)) if unknown_flags else 0.0
    slo_within = (
        sum(1 for ms in per_frame_ms if ms <= slo_budget_ms) / len(per_frame_ms) * 100
        if per_frame_ms
        else 0.0
    )

    return {
        "stage_ms": stage_means,
        "fps": fps,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "slo_budget_ms": float(slo_budget_ms),
        "slo_within_budget_pct": slo_within,
        "unknown_rate": unknown_rate,
        "kb_size": int(kb_size),
        "backend_selected": backend_selected,
        "sdk_version": sdk_version,
    }


__all__ = ["metrics_json"]
