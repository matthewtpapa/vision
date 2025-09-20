from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
ph = pytest.importorskip("latency_vision.phash")


def _mk(img=None):
    a = np.zeros((32, 32), dtype=np.float64)
    if img is not None:
        a[img] = 1.0
    return a


def test_phash_deterministic() -> None:
    g = _mk((0, 0))
    h1 = ph.phash_64(g)
    h2 = ph.phash_64(g.copy())
    assert h1 == h2


def test_phash_sensitivity() -> None:
    a = _mk((0, 0))
    b = _mk((0, 1))
    assert ph.hamming64(ph.phash_64(a), ph.phash_64(b)) > 0


def test_hamming_zero_when_equal() -> None:
    x = ph.phash_64(_mk((10, 10)))
    assert ph.hamming64(x, x) == 0
