# SPDX-License-Identifier: Apache-2.0
"""Tracking adapter interfaces and simple implementations."""

from __future__ import annotations

from .types import Detection, Track


class Tracker:
    """Interface for object trackers."""

    def update(self, detections: list[Detection]) -> list[Track]:  # pragma: no cover - interface
        """Update tracker with ``detections`` and return current tracks."""
        raise NotImplementedError


class SimpleIdTracker(Tracker):
    """Assigns incremental IDs to detections on each update."""

    def update(self, detections: list[Detection]) -> list[Track]:
        tracks: list[Track] = []
        for i, det in enumerate(detections, start=1):
            tracks.append(Track(track_id=i, bbox=det.bbox, score=det.score, cls=det.cls))
        return tracks


__all__ = ["Tracker", "SimpleIdTracker"]
