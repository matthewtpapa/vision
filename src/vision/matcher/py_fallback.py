# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""NumPy matcher backend implementing :class:`MatcherProtocol`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import numpy as np
import numpy.typing as npt

from .matcher_protocol import Label, MatcherProtocol, Neighbor


def _normalize_rows(arr: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    norms = np.linalg.norm(arr, axis=1, keepdims=True).astype(np.float32)
    norms[norms == 0] = 1.0
    out = arr / norms
    return cast(npt.NDArray[np.float32], out)


def _ensure_norm_f32(
    vecs: Sequence[Sequence[float]] | npt.NDArray[Any],
) -> npt.NDArray[np.float32]:
    arr = np.asarray(vecs, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr[None, :]
    return _normalize_rows(arr)


class NumpyMatcher(MatcherProtocol):
    """In-memory matcher using NumPy with deterministic tie-breaking."""

    def __init__(self) -> None:
        self._embeddings: npt.NDArray[np.float32] | None = None
        self._labels: list[Label] = []
        self._dim: int | None = None

    def add(self, vec: Sequence[float], label: Label) -> None:
        arr = _ensure_norm_f32(vec)
        self._add_many(arr, [label])

    def add_many(
        self, vecs: Sequence[Sequence[float]] | npt.NDArray[Any], labels: Sequence[Label]
    ) -> None:
        arr = _ensure_norm_f32(vecs)
        label_list = list(labels)
        if arr.shape[0] != len(label_list):
            raise ValueError("vecs and labels length mismatch")
        self._add_many(arr, label_list)

    def _add_many(self, arr: np.ndarray, labels: list[Label]) -> None:
        if self._dim is None:
            self._dim = arr.shape[1]
        elif arr.shape[1] != self._dim:
            raise ValueError(f"dim mismatch: expected {self._dim}, got {arr.shape[1]}")
        if self._embeddings is None:
            self._embeddings = arr
        else:
            self._embeddings = np.vstack([self._embeddings, arr])
        self._labels.extend(labels)

    def topk(self, query: Sequence[float], k: int) -> list[Neighbor]:
        if self._embeddings is None or k <= 0:
            return []
        q = _ensure_norm_f32(query)
        if q.shape[1] != self._dim:
            raise ValueError(f"dim mismatch: expected {self._dim}, got {q.shape[1]}")
        scores = self._embeddings @ q[0]
        k = min(k, len(self._labels))
        idx = np.argpartition(-scores, k - 1)[:k]
        idx.sort()
        idx = idx[np.argsort(-scores[idx], kind="stable")]
        return [(self._labels[i], float(scores[i])) for i in idx]
