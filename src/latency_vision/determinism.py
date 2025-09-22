"""Deterministic runtime helpers for latency benchmarks."""

from __future__ import annotations

import os
import random
import secrets
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

DEFAULT_SEED = 20240520
_THREAD_ENV_VARS = (
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "BLIS_NUM_THREADS",
)


@dataclass(frozen=True)
class DeterminismConfig:
    """Configuration for deterministic runtime setup."""

    seed: int = DEFAULT_SEED
    threads: int = 1


def _quantize_env_value(value: int) -> str:
    return str(max(1, int(value)))


def seed_everything(seed: int = DEFAULT_SEED) -> None:
    """Seed Python RNGs and hash randomization."""

    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    secrets.SystemRandom(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        # NumPy is optional; ignore if unavailable.
        pass


def cap_threads(max_threads: int = 1) -> None:
    """Limit BLAS/OpenMP style thread pools."""

    for var in _THREAD_ENV_VARS:
        os.environ[var] = _quantize_env_value(max_threads)
    # Opt-out of dynamic thread pools when available.
    os.environ.setdefault("OMP_PROC_BIND", "TRUE")
    os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
    # Silence verbose BLAS output and select a deterministic MKL mode when
    # available.
    os.environ.setdefault("OPENBLAS_VERBOSE", "0")
    os.environ.setdefault("MKL_CBWR", "COMPATIBLE")


def configure_runtime(config: DeterminismConfig | None = None) -> None:
    """Apply deterministic runtime configuration exactly once."""

    if config is None:
        config = DeterminismConfig()
    seed_everything(config.seed)
    cap_threads(config.threads)


def set_global_determinism(seed: int = DEFAULT_SEED, threads: int = 1) -> None:
    """Seed RNGs and cap BLAS/OpenMP thread pools for reproducible runs.

    The helper caps MKL/BLAS/OpenMP thread pools (``MKL_NUM_THREADS``,
    ``OPENBLAS_NUM_THREADS``, ``OMP_NUM_THREADS``, etc.) to the requested value
    and seeds Python/NumPy RNGs. Some BLAS libraries may still exhibit
    nondeterministic kernels despite the caps.
    """

    configure_runtime(DeterminismConfig(seed=seed, threads=threads))


def quantize_float(value: float, places: int = 4) -> float:
    """Quantize floating point values for deterministic serialization."""

    q = Decimal(10) ** -places
    return float(Decimal(value).quantize(q, rounding=ROUND_HALF_UP))


def blas_fingerprint() -> dict[str, Any]:
    """Attempt to fingerprint the active BLAS implementation.

    Returns a JSON-serializable structure capturing the BLAS vendor hints and
    thread-related environment variables.
    """

    fingerprint: dict[str, Any] = {
        "thread_env": {var: os.environ.get(var, "unset") for var in _THREAD_ENV_VARS},
    }
    try:
        import numpy as np
        from numpy import __config__

        fingerprint["numpy"] = {
            "version": str(np.__version__),
            "blas_keys": [],
            "build_info": {},
        }
        for key in dir(__config__):
            if not key.endswith("_info"):
                continue
            value = getattr(__config__, key)
            if not isinstance(value, dict):
                continue
            if value:
                fingerprint["numpy"]["build_info"][key] = {
                    inner_key: value[inner_key]
                    for inner_key in sorted(value)
                    if isinstance(value[inner_key], str | int | float | list | tuple)
                }
                fingerprint["numpy"]["blas_keys"].append(key)
        fingerprint["numpy"]["blas_keys"].sort()
    except Exception:
        fingerprint.setdefault("numpy", {"available": False})
    return fingerprint


__all__ = [
    "DEFAULT_SEED",
    "DeterminismConfig",
    "blas_fingerprint",
    "cap_threads",
    "configure_runtime",
    "set_global_determinism",
    "quantize_float",
    "seed_everything",
]
