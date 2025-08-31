# SPDX-License-Identifier: Apache-2.0
"""Detection adapter interfaces and fakes."""

from __future__ import annotations

from .types import BBox, Detection


class Detector:
    """Interface for object detectors."""

    def detect(self, frame) -> list[Detection]:  # pragma: no cover - interface
        """Run detection on *frame* and return a list of ``Detection`` objects."""
        raise NotImplementedError


class FakeDetector(Detector):
    """Deterministic detector that returns configured bounding boxes."""

    def __init__(
        self, boxes: list[BBox] | None = None, score: float = 0.9, cls_id: int = 0
    ) -> None:
        self._boxes = boxes
        self._score = score
        self._cls_id = cls_id

    def detect(self, frame) -> list[Detection]:
        if not self._boxes:
            return []
        return [Detection(b, self._score, self._cls_id) for b in self._boxes]


__all__ = ["Detector", "FakeDetector"]
