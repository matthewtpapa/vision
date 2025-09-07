# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Simple detection-to-tracking pipeline."""

from __future__ import annotations

from .detect_adapter import Detector
from .track_adapter import Tracker
from .types import Track


class DetectTrackPipeline:
    """Pipeline that runs detection followed by tracking."""

    def __init__(self, detector: Detector, tracker: Tracker) -> None:
        self._detector = detector
        self._tracker = tracker

    def process(self, frame) -> list[Track]:
        """Run the detector and tracker on *frame* and return tracks."""
        detections = self._detector.detect(frame)
        return self._tracker.update(detections)


__all__ = ["DetectTrackPipeline"]
