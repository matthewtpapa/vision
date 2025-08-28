"""Typed data contracts for detection and tracking.

This module defines lightweight immutable dataclasses that model the
results of object detection and tracking. No runtime validation is
performed; the meanings of fields are documented in the corresponding
docstrings.
"""

from __future__ import annotations

from dataclasses import dataclass

BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class Detection:
    """A single object detection.

    Attributes:
        bbox: Bounding box in integer ``(x1, y1, x2, y2)`` format.
        score: Confidence score for the detection.
        cls: Integer class identifier.
    """

    bbox: BBox
    score: float
    cls: int


@dataclass(frozen=True)
class Track:
    """A tracked object.

    Attributes:
        track_id: Identifier assigned by the tracker.
        bbox: Bounding box in integer ``(x1, y1, x2, y2)`` format.
        score: Optional confidence score for the detection that produced the
            track.
        cls: Optional class identifier.
    """

    track_id: int
    bbox: BBox
    score: float | None = None
    cls: int | None = None


__all__ = ["BBox", "Detection", "Track"]
