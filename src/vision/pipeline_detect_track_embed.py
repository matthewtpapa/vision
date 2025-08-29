"""Detection → tracking → embedding pipeline."""

from __future__ import annotations

from collections.abc import Callable

from .associations import TrackEmbedding
from .detect_adapter import Detector
from .embedder_adapter import Embedder
from .track_adapter import Tracker
from .types import BBox, Track

Cropper = Callable[[object, list[BBox]], list[object]]


class DetectTrackEmbedPipeline:
    """Pipeline that runs detection, tracking, cropping, and embedding."""

    def __init__(
        self, detector: Detector, tracker: Tracker, cropper: Cropper, embedder: Embedder
    ) -> None:
        self._detector = detector
        self._tracker = tracker
        self._cropper = cropper
        self._embedder = embedder

    def process(self, frame) -> list[TrackEmbedding]:
        """Run the detector, tracker, cropper, and embedder on *frame*."""
        detections = self._detector.detect(frame)
        tracks: list[Track] = self._tracker.update(detections)
        bboxes = [t.bbox for t in tracks]
        crops = self._cropper(frame, bboxes)
        embeddings = self._embedder.encode(crops)
        return [TrackEmbedding(track=t, embedding=e) for t, e in zip(tracks, embeddings)]


__all__ = ["DetectTrackEmbedPipeline", "Cropper"]
