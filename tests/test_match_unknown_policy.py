# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
import pytest

pytest.importorskip("numpy")

from vision.matcher.py_fallback import NumpyMatcher


def test_unknown_policy_threshold_and_min_neighbors():
    matcher = NumpyMatcher()
    matcher.add([1.0, 0.0, 0.0], "A")
    matcher.add([0.0, 1.0, 0.0], "B")

    neighbors = matcher.topk([1.0, 0.0, 0.0], k=5)
    assert len(neighbors) == 2  # bounded by index size

    above = [(lab, s) for lab, s in neighbors if s >= 0.9]
    is_unknown = len(above) < 1
    assert is_unknown is False

    above = [(lab, s) for lab, s in neighbors if s >= 1.01]
    is_unknown = len(above) < 1
    assert is_unknown is True
