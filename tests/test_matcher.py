# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from vision.matcher import Matcher


def test_matcher_finds_exact_match_and_returns_index():
    matcher = Matcher()
    query = [1.0, 2.0]
    candidates = [[1.0, 2.0], [3.0, 4.0]]
    assert matcher.match(query, candidates) == 0
    assert matcher.match([5.0], candidates) == -1
