# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import pytest

pytest.importorskip("faiss")
pytest.importorskip("numpy")

import numpy as np

from latency_vision.matcher.faiss_backend import FaissMatcher
from latency_vision.matcher.py_fallback import NumpyMatcher


def test_faiss_and_numpy_parity() -> None:
    data = np.array([[1, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]], dtype=np.float32)
    labels = ["A", "B", "C", "D"]
    query = np.array([1, 0, 0], dtype=np.float32)

    numpy_matcher = NumpyMatcher()
    numpy_matcher.add_many(data, labels)
    faiss_matcher = FaissMatcher(3)
    faiss_matcher.add_many(data, labels)

    expected = numpy_matcher.topk(query, 3)
    actual = faiss_matcher.topk(query, 3)

    for (el, es), (al, ascore) in zip(expected, actual):
        assert el == al
        assert ascore == pytest.approx(es, abs=1e-6)
