# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from math import sqrt

import pytest

pytest.importorskip("numpy")

from vision.matcher.py_fallback import NumpyMatcher


def test_cosine_math_and_ordering() -> None:
    matcher = NumpyMatcher()
    matcher.add([1, 0, 0], "A")
    matcher.add([0, 1, 0], "B")
    matcher.add([1, 1, 0], "C")
    result = matcher.topk([1, 0, 0], 2)
    assert result[0][0] == "A"
    assert result[0][1] == pytest.approx(1.0, abs=1e-6)
    assert result[1][0] == "C"
    assert result[1][1] == pytest.approx(1 / sqrt(2), abs=1e-6)


def test_add_many_and_dim_checks() -> None:
    matcher = NumpyMatcher()
    matcher.add_many([[1, 0, 0], [0, 1, 0]], ["A", "B"])
    with pytest.raises(ValueError, match="dim mismatch"):
        matcher.add_many([[1, 0]], ["C"])


def test_deterministic_ties_stable() -> None:
    matcher = NumpyMatcher()
    matcher.add([1, 0, 0], "L1")
    matcher.add([1, 0, 0], "L2")
    result = matcher.topk([1, 0, 0], 2)
    assert result[0][0] == "L1"
    assert result[1][0] == "L2"
    assert result[0][1] == pytest.approx(1.0)
    assert result[1][1] == pytest.approx(1.0)
