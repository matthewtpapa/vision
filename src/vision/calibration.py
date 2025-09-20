"""Compatibility wrapper for calibration utilities."""

from __future__ import annotations

from latency_vision.calibration import (
    CalibrationReport,
    distances_to_logits,
    fit_temperature,
    unknown_rate_guard,
    softmax,
    temperature_scale,
)

__all__ = [
    "CalibrationReport",
    "distances_to_logits",
    "fit_temperature",
    "unknown_rate_guard",
    "softmax",
    "temperature_scale",
]
