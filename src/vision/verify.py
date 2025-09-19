"""Verification accounting helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import time_ns


@dataclass
class VerifyResult:
    accepted: bool
    score: float
    details: Mapping[str, float]


@dataclass
class _Counters:
    called: int = 0
    accepted: int = 0
    rejected: int = 0
    known_wrong_after_verify: int = 0
    seed: int = 0
    ts_ns: int = time_ns()


class VerifyWorker:
    """Minimal verify worker that tracks accounting and deterministic scoring."""

    def __init__(self, threshold: float = 0.0, seed: int = 0) -> None:
        self._threshold = float(threshold)
        self._seed = seed
        self._counters = _Counters(seed=seed, ts_ns=time_ns())

    def verify(self, embedding: Sequence[float], candidate_label: str) -> VerifyResult:
        score = float(sum(float(x) for x in embedding))
        accepted = score >= self._threshold and candidate_label != "__unknown__"
        self._counters.called += 1
        if accepted:
            self._counters.accepted += 1
        else:
            self._counters.rejected += 1
        return VerifyResult(accepted=accepted, score=score, details={"sum": score})

    def metrics_snapshot(self) -> Mapping[str, int | float]:
        return {
            "called": self._counters.called,
            "accepted": self._counters.accepted,
            "rejected": self._counters.rejected,
            "known_wrong_after_verify": self._counters.known_wrong_after_verify,
            "seed": self._counters.seed,
            "ts_ns": self._counters.ts_ns,
        }


__all__ = ["VerifyResult", "VerifyWorker"]
