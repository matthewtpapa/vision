# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from functools import cache

import numpy as np


@cache
def _dct_mat(n: int) -> np.ndarray:
    """Create an orthonormal DCT-II matrix of size ``n``."""
    k = np.arange(n, dtype=np.float64).reshape(-1, 1)
    x = np.arange(n, dtype=np.float64).reshape(1, -1)
    C = np.cos((math.pi / n) * (x + 0.5) * k)
    C[0, :] *= 1.0 / math.sqrt(2.0)
    return C * math.sqrt(2.0 / n)


def phash_64(gray32: np.ndarray) -> int:
    """Compute a 64-bit perceptual hash from a 32×32 grayscale image."""
    if gray32.shape != (32, 32):
        raise ValueError("expected 32x32 grayscale matrix")

    C = _dct_mat(32)
    d = C @ gray32 @ C.T
    block = d[1:9, 1:9]

    coeffs = block.reshape(-1)
    med = np.median(coeffs)
    bits = (coeffs >= med).astype(np.uint8)

    h = 0
    for i in range(64):
        h |= int(bits[i]) << i
    return h


def hamming64(a: int, b: int) -> int:
    """Return the Hamming distance between two 64-bit integers."""
    return (a ^ b).bit_count()
