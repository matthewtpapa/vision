# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from latency_vision.tracker import Tracker


def test_tracker_assigns_incremental_ids():
    tracker = Tracker()
    boxes = [(0, 0, 10, 10), (10, 10, 20, 20)]
    assert tracker.update(boxes) == [(1, boxes[0]), (2, boxes[1])]
    assert tracker.update([boxes[0]]) == [(3, boxes[0])]
