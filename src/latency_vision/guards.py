# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Guardrail checks for Latency Vision benchmarks."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


def unknowns_false_accept_rate(samples: Iterable[dict]) -> float:
    """Return the false-accept rate for unknown queries.

    The rate is computed as the fraction of total samples that were marked as
    unknown (``is_unknown_truth``) and simultaneously accepted (``accepted``).
    """

    total = 0
    false_accepts = 0
    for sample in samples:
        total += 1
        if bool(sample.get("is_unknown_truth")) and bool(sample.get("accepted")):
            false_accepts += 1
    if total == 0:
        return 0.0
    return false_accepts / total


def unknowns_false_accept_guard(samples_path: str | Path, threshold: float = 0.025) -> None:
    """Guard against false accepts for unknown queries.

    Parameters
    ----------
    samples_path:
        Path to the JSONL file containing end-to-end sample rows.
    threshold:
        Maximum tolerated false-accept rate (expressed as a fraction).
    """

    path = Path(samples_path)
    with path.open("r", encoding="utf-8") as handle:
        samples = [json.loads(line) for line in handle if line.strip()]
    rate = unknowns_false_accept_rate(samples)
    if rate > threshold:
        rate_pct = rate * 100
        threshold_pct = threshold * 100
        raise AssertionError(
            f"unknowns false-accept rate {rate_pct:.2f}% exceeds threshold {threshold_pct:.2f}%"
        )


__all__ = ["unknowns_false_accept_guard", "unknowns_false_accept_rate"]
