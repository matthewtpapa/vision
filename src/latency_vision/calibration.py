"""Calibration utilities for candidate probabilities."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from numpy.typing import DTypeLike

_T_MIN = 0.5
_T_MAX = 5.0
_EPS = 1e-8
_LOG_T_MIN = -3.0
_LOG_T_MAX = 3.0

_CALIB_ASSERT = os.getenv("VISION__CALIB__LOCK", "0") == "1"


def _as_array(values: object, *, dtype: DTypeLike | None = None) -> np.ndarray:
    """Coerce arbitrary 1D/2D-like inputs to an ndarray, with optional dtype."""

    if isinstance(values, Iterable) and not isinstance(values, np.ndarray):
        values = list(values)
    arr = np.asarray(values, dtype=dtype)
    if arr.ndim not in (1, 2):
        raise ValueError("values must be 1-D or 2-D")

    if arr.ndim == 2:
        if arr.dtype == object:
            width = arr.shape[1]
            for row in arr:
                try:
                    row_len = len(row)
                except TypeError as exc:  # pragma: no cover - defensive
                    msg = "2-D inputs must have consistent row lengths"
                    raise ValueError(msg) from exc
                if row_len != width:
                    raise ValueError("2-D inputs must have consistent row lengths")
    elif arr.dtype == object and arr.size > 0:
        if not all(np.isscalar(item) for item in arr):
            raise ValueError("1-D inputs must be scalar-like")

    return arr


def distances_to_logits(d: np.ndarray | Iterable[float], method: str = "neg") -> np.ndarray:
    """Convert *d* distances into logits.

    The default ``method='neg'`` simply negates the distances so that lower
    distances translate into larger logits. The resulting array is guaranteed to
    be finite; NaNs and infinities are replaced with zeros.
    """

    arr = _as_array(d, dtype=np.float64)
    if method != "neg":  # pragma: no cover - future extension hook
        raise ValueError(f"unsupported method: {method}")
    logits = -arr
    logits[~np.isfinite(logits)] = 0.0
    return logits


def temperature_scale(logits: np.ndarray | Iterable[float], T: float) -> np.ndarray:
    """Return logits divided by the clipped temperature ``T``."""

    clipped_T = float(np.clip(T, _T_MIN, _T_MAX))
    arr = _as_array(logits, dtype=np.float64)
    stable_T = max(clipped_T, _EPS)
    return arr / stable_T


def softmax(logits: np.ndarray | Iterable[float]) -> np.ndarray:
    """Numerically stable softmax for one- or two-dimensional logits."""

    arr = _as_array(logits, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr[np.newaxis, :]
    maxes = np.max(arr, axis=1, keepdims=True)
    shifted = arr - maxes
    exp = np.exp(shifted)
    exp_sum = np.sum(exp, axis=1, keepdims=True)
    probs = exp / np.maximum(exp_sum, 1e-12)
    if probs.shape[0] == 1:
        return probs[0]
    return probs


def _nll_log_T(logits_2d: np.ndarray, labels_1d: np.ndarray, u: float) -> float:
    """Mean NLL when scaling by ``T = exp(u)``. Optimizes in log-space."""

    T = float(np.exp(u))
    z = temperature_scale(logits_2d, T)
    z = z - z.max(axis=1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(axis=1, keepdims=True)
    return float(-np.log(p[np.arange(p.shape[0]), labels_1d]).mean())


def fit_temperature(
    logits: np.ndarray | Iterable[Iterable[float]],
    labels: np.ndarray | Iterable[int],
    *,
    max_iter: int = 50,
    seed: int = 123,
) -> float:
    """Return a positive temperature ``T`` such that scaled logits = logits / T.

    Uses golden-section search over log-space ``u = log(T)`` to improve
    numerical stability while remaining dependency-free and deterministic.
    """

    rng = np.random.default_rng(seed)
    logits_arr = _as_array(logits, dtype=np.float64)
    if logits_arr.ndim != 2:
        raise ValueError("logits must be 2-D")
    labels_arr = np.asarray(labels, dtype=np.int64)
    if labels_arr.shape[0] != logits_arr.shape[0]:
        raise ValueError("labels and logits size mismatch")

    # Shuffle copies to avoid accidental correlations when callers pass views.
    perm = rng.permutation(logits_arr.shape[0])
    logits_arr = logits_arr[perm]
    labels_arr = labels_arr[perm]

    phi = (np.sqrt(5.0) - 1.0) / 2.0
    a, b = _LOG_T_MIN, _LOG_T_MAX
    c = b - phi * (b - a)
    d = a + phi * (b - a)
    fc = _nll_log_T(logits_arr, labels_arr, c)
    fd = _nll_log_T(logits_arr, labels_arr, d)

    for _ in range(max_iter):
        if abs(b - a) < 1e-4:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - phi * (b - a)
            fc = _nll_log_T(logits_arr, labels_arr, c)
        else:
            a, c, fc = c, d, fd
            d = a + phi * (b - a)
            fd = _nll_log_T(logits_arr, labels_arr, d)

    u_opt = (a + b) / 2.0
    raw_T = float(np.exp(u_opt))
    T = float(np.clip(raw_T, _T_MIN, _T_MAX))
    assert T > 0.0, "fit_temperature must return a positive temperature"
    if _CALIB_ASSERT:
        assert T > 1.0, "Convention lock: fit_temperature must return T, not alpha"
    if os.getenv("VISION__CALIB__DEBUG") == "1":
        print(f"[calib] u_opt={u_opt:.6f} -> T={T:.6f}", file=sys.stderr)
    return T


@dataclass(frozen=True)
class CalibrationReport:
    temperature: float
    nll: float
    ece: float


def unknown_rate_guard(flags: list[bool]) -> float:
    """Return the fraction of truthy *flags*, guarding against empty inputs."""

    if not flags:
        return 0.0
    return float(sum(flags)) / len(flags)


__all__ = [
    "CalibrationReport",
    "distances_to_logits",
    "fit_temperature",
    "unknown_rate_guard",
    "softmax",
    "temperature_scale",
]
