"""Compatibility wrapper for calibration utilities."""

from __future__ import annotations

from latency_vision.calibration import (
    CalibrationReport,
    distances_to_logits,
    fit_temperature,
    softmax,
    temperature_scale,
    unknown_rate_guard,
)

__all__ = [
    "CalibrationReport",
    "distances_to_logits",
    "fit_temperature",
    "unknown_rate_guard",
    "softmax",
    "temperature_scale",
]
