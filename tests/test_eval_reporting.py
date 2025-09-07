# SPDX-License-Identifier: Apache-2.0
"""Tests for metrics aggregation helpers."""

from __future__ import annotations

from vision.eval_reporting import metrics_json


def test_warmup_exclusion() -> None:
    per_frame = [100.0] * 100 + [10.0] * 100
    stages: dict[str, list[float]] = {}
    unknown = [False] * 200
    m = metrics_json(
        per_frame,
        stages,
        unknown,
        kb_size=0,
        backend_selected="numpy",
        sdk_version="0.0",
        warmup=100,
        slo_budget_ms=33.0,
    )
    assert m["p50_ms"] == 10.0
    assert m["slo_within_budget_pct"] == 100.0
