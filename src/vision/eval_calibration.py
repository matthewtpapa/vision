"""Compatibility wrapper for calibration evaluation helpers."""

from __future__ import annotations

from latency_vision.eval_calibration import (
    compute_ece,
    evaluate_labelbank_calibration,
)

__all__ = [
    "compute_ece",
    "evaluate_labelbank_calibration",
]
