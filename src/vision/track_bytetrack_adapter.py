# SPDX-License-Identifier: Apache-2.0
"""ByteTrack-like tracker adapter."""

from __future__ import annotations

from .track_adapter import Tracker
from .types import BBox, Detection, Track


class ByteTrackLikeTracker(Tracker):
    """Approximate ByteTrack by maintaining IDs using IoU matching."""

    def __init__(self, iou_threshold: float = 0.3) -> None:
        self._iou_threshold = iou_threshold
        self._next_id = 1
        self._tracks: dict[int, BBox] = {}

    def _iou(self, a: BBox, b: BBox) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter = inter_w * inter_h
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union = area_a + area_b - inter
        if union == 0:
            return 0.0
        return inter / union

    def update(self, detections: list[Detection]) -> list[Track]:
        det_indices = set(range(len(detections)))
        track_ids = set(self._tracks.keys())
        matches: list[tuple[int, int]] = []  # (det_idx, track_id)

        ious: list[tuple[float, int, int]] = []
        for det_idx in det_indices:
            for track_id in track_ids:
                iou = self._iou(detections[det_idx].bbox, self._tracks[track_id])
                ious.append((iou, det_idx, track_id))
        ious.sort(reverse=True)

        for iou, det_idx, track_id in ious:
            if iou < self._iou_threshold:
                break
            if det_idx in det_indices and track_id in track_ids:
                matches.append((det_idx, track_id))
                det_indices.remove(det_idx)
                track_ids.remove(track_id)
                self._tracks[track_id] = detections[det_idx].bbox

        det_to_id: dict[int, int] = {det_idx: track_id for det_idx, track_id in matches}

        for det_idx in det_indices:
            track_id = self._next_id
            self._next_id += 1
            self._tracks[track_id] = detections[det_idx].bbox
            det_to_id[det_idx] = track_id

        for track_id in track_ids:
            self._tracks.pop(track_id, None)

        tracks: list[Track] = []
        for idx, det in enumerate(detections):
            track_id = det_to_id[idx]
            tracks.append(Track(track_id=track_id, bbox=det.bbox, score=det.score, cls=det.cls))
        return tracks


__all__ = ["ByteTrackLikeTracker"]
