# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""FAISS matcher backend implementing :class:`MatcherProtocol`."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from .matcher_protocol import Label, MatcherProtocol, Neighbor

try:  # pragma: no cover - import guarded for environments without faiss
    import faiss
except Exception as e:  # pragma: no cover
    raise ImportError("faiss not available") from e

_EPS = 1e-12


def _ensure_norm_f32(x: Sequence[float] | NDArray[np.float32]) -> NDArray[np.float32]:
    arr = np.asarray(x, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def _ensure_norm_f32_batch(
    X: Sequence[Sequence[float]] | NDArray[np.float32],
) -> NDArray[np.float32]:
    arr = np.asarray(X, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


class FaissMatcher(MatcherProtocol):
    """FAISS-based matcher using inner-product search over normalised vectors."""

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)
        self._labels: list[Label] = []

    def add(self, vec: Sequence[float], label: Label) -> None:
        arr = _ensure_norm_f32(vec)
        if arr.shape[1] != self._dim:
            raise ValueError(f"dim mismatch: expected {self._dim}, got {arr.shape[1]}")
        self._index.add(arr)
        self._labels.append(label)

    def add_many(
        self, vecs: Sequence[Sequence[float]] | np.ndarray, labels: Sequence[Label]
    ) -> None:
        arr = _ensure_norm_f32_batch(vecs)
        if arr.shape[1] != self._dim:
            raise ValueError(f"dim mismatch: expected {self._dim}, got {arr.shape[1]}")
        label_list = list(labels)
        if arr.shape[0] != len(label_list):
            raise ValueError("vecs and labels length mismatch")
        self._index.add(arr)
        self._labels.extend(label_list)

    def topk(self, query: Sequence[float], k: int) -> list[Neighbor]:
        if k <= 0 or not self._labels:
            return []
        q = _ensure_norm_f32(query)
        if q.shape[1] != self._dim:
            raise ValueError(f"dim mismatch: expected {self._dim}, got {q.shape[1]}")
        k = min(k, len(self._labels))
        scores, idx = self._index.search(q, k)
        order = np.lexsort((idx[0], -scores[0]))
        return [(self._labels[int(idx[0][i])], float(scores[0][i])) for i in order]
