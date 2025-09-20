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
    """Compute a 64-bit perceptual hash from a 32×32 grayscale image.
    Spec: DCT→take 8×8 top-left block; exclude DC only; threshold by median;
    pack row-major, LSB-first.
    """
    if gray32.shape != (32, 32):
        raise ValueError("expected 32x32 grayscale matrix")

    C = _dct_mat(32)
    d = C @ gray32 @ C.T
    block = d[:8, :8].copy()             # include DC inside the 8×8
    coeffs = block.ravel()
    dc = coeffs[0]
    coeffs[0] = 0.0                       # exclude DC from median calc
    med = np.median(coeffs[1:])           # median over 63 non-DC coeffs
    bits = (block >= med).astype(np.uint8).ravel()
    bits[0] = 1 if dc >= med else 0       # deterministic DC handling
    h = 0
    for i in range(64):
        h |= int(bits[i]) << i            # LSB-first, row-major
    return h


def hamming64(a: int, b: int) -> int:
    """Return the Hamming distance between two 64-bit integers."""
    return (a ^ b).bit_count()
