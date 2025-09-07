# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import dataclasses

import pytest

from latency_vision.detect_adapter import FakeDetector
from latency_vision.track_adapter import SimpleIdTracker
from latency_vision.types import Detection


def test_fake_detector_returns_configured_boxes() -> None:
    boxes = [(10, 10, 50, 50), (0, 0, 100, 100)]
    detector = FakeDetector(boxes=boxes)
    detections = detector.detect(frame=None)
    assert len(detections) == 2
    assert detections[0] == Detection(boxes[0], 0.9, 0)
    assert detections[1] == Detection(boxes[1], 0.9, 0)


def test_simple_id_tracker_assigns_ids_in_order() -> None:
    dets = [Detection((1, 1, 2, 2), 0.5, 0), Detection((2, 2, 3, 3), 0.6, 1)]
    tracker = SimpleIdTracker()
    tracks = tracker.update(dets)
    assert len(tracks) == 2
    assert tracks[0].track_id == 1
    assert tracks[0].bbox == dets[0].bbox
    assert tracks[1].track_id == 2
    assert tracks[1].bbox == dets[1].bbox


def test_types_are_immutable() -> None:
    det = Detection((0, 0, 1, 1), 0.5, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(det, "score", 0.7)
