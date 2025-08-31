# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from vision.index_utils import add_exemplars_to_index
from vision.matcher.py_fallback import NumpyMatcher


def test_adds_items_and_allows_query() -> None:
    index = NumpyMatcher()
    items = [
        {"label": "A", "embedding": [1.0, 0.0, 0.0]},
        {"label": "B", "embedding": [0.0, 1.0, 0.0]},
        {"label": "C", "embedding": [0.0, 0.0, 1.0]},
    ]
    count = add_exemplars_to_index(index, items)
    assert count == 3
    result = index.topk([1.0, 0.0, 0.0], 1)
    assert result[0][0] == "A"


def test_empty_list_returns_zero() -> None:
    index = NumpyMatcher()
    count = add_exemplars_to_index(index, [])
    assert count == 0


def test_missing_key_raises() -> None:
    index = NumpyMatcher()
    with pytest.raises(KeyError):
        add_exemplars_to_index(index, [{"embedding": [1.0, 0.0, 0.0]}])
