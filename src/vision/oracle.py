"""Candidate oracle with temperature scaling and EMA-based abstention."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .calibration import distances_to_logits, softmax, temperature_scale


@dataclass
class OracleDecision:
    label: str
    confidence: float
    abstained: bool


class CandidateOracle:
    """Predict candidate labels with calibrated confidence and EMA smoothing."""

    def __init__(self, T: float, abstain_p: float, smoothing_alpha: float = 0.2) -> None:
        self._temperature = float(np.clip(T, 0.5, 5.0))
        self._abstain_p = float(np.clip(abstain_p, 0.0, 1.0))
        self._alpha = float(np.clip(smoothing_alpha, 0.0, 1.0))
        self._ema: dict[int, float] = {}

    def predict(
        self,
        track_id: int,
        label_ids: Sequence[str],
        distances: Sequence[float],
    ) -> tuple[str, float, bool]:
        if not label_ids:
            return "__unknown__", 0.0, True

        dist_arr = np.asarray(distances, dtype=np.float64)
        logits = distances_to_logits(dist_arr)
        scaled = temperature_scale(logits, self._temperature)
        probs = softmax(scaled)
        if probs.ndim > 1:
            probs = probs[0]
        idx = int(np.argmax(probs))
        p_max = float(probs[idx]) if probs.size else 0.0
        best_label = str(label_ids[idx])

        prev = self._ema.get(track_id, p_max)
        ema = self._alpha * p_max + (1.0 - self._alpha) * prev
        self._ema[track_id] = ema

        if ema < self._abstain_p:
            return "__unknown__", ema, True
        return best_label, ema, False


__all__ = ["CandidateOracle", "OracleDecision"]
