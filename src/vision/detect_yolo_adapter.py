# SPDX-License-Identifier: Apache-2.0
"""YOLO-like detection adapter."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .detect_adapter import Detector
from .types import Detection


class YoloLikeDetector(Detector):
    """Adapt YOLO-style model outputs into :class:`Detection` objects."""

    def __init__(
        self,
        runner: Callable[[Any, int], list[tuple[float, float, float, float, float, int]]],
        input_size: int = 640,
        score_threshold: float = 0.25,
    ) -> None:
        self._runner = runner
        self._input_size = input_size
        self._score_threshold = score_threshold

    def detect(self, frame) -> list[Detection]:
        results = self._runner(frame, self._input_size)
        detections: list[Detection] = []
        for x1, y1, x2, y2, score, cls_id in results:
            if score < self._score_threshold:
                continue
            bbox = (
                int(math.floor(x1)),
                int(math.floor(y1)),
                int(math.ceil(x2)),
                int(math.ceil(y2)),
            )
            detections.append(Detection(bbox, score, cls_id))
        return detections


__all__ = ["YoloLikeDetector"]
