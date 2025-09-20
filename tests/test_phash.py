from __future__ import annotations

import importlib.util

import pytest

_has_numpy = importlib.util.find_spec("numpy") is not None
_has_phash = importlib.util.find_spec("latency_vision.phash") is not None
# Ensure tests are collected, then skipped (exit code 0) if deps are missing
pytestmark = pytest.mark.skipif(
    not (_has_numpy and _has_phash), reason="numpy/phash not installed"
)


def _mk(img=None):
    import numpy as np

    a = np.zeros((32, 32), dtype=np.float64)
    if img is not None:
        a[img] = 1.0
    return a


def test_phash_deterministic() -> None:
    from latency_vision.phash import phash_64

    g = _mk((0, 0))
    h1 = phash_64(g)
    h2 = phash_64(g.copy())
    assert h1 == h2


def test_phash_sensitivity() -> None:
    from latency_vision.phash import hamming64, phash_64

    a = _mk((0, 0))
    b = _mk((0, 1))
    assert hamming64(phash_64(a), phash_64(b)) > 0


def test_hamming_zero_when_equal() -> None:
    from latency_vision.phash import hamming64, phash_64

    x = phash_64(_mk((10, 10)))
    assert hamming64(x, x) == 0
