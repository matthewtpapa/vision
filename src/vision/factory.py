"""Factories for constructing detector and tracker implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .detect_adapter import FakeDetector
from .detect_yolo_adapter import YoloLikeDetector
from .embedder_adapter import ClipLikeEmbedder
from .embedding_types import Embedding as _Embedding  # noqa: F401
from .track_bytetrack_adapter import ByteTrackLikeTracker

Runner = Callable[[Any, int], list[tuple[float, float, float, float, float, int]]]
EmbedRunner = Callable[[list[object]], list[list[float]]]


def build_detector(
    cfg: Any,
    *,
    use_fake: bool = False,
    yolo_runner: Runner | None = None,
    score_threshold: float = 0.25,
):
    """Construct a detector instance based on *cfg* and flags."""
    if use_fake:
        return FakeDetector()
    if yolo_runner is None:
        raise NotImplementedError("yolo_runner required for YoloLikeDetector in M1-02")
    return YoloLikeDetector(
        yolo_runner,
        input_size=cfg.detector.input_size,
        score_threshold=score_threshold,
    )


def build_tracker(cfg: Any, *, kind: str | None = None):
    """Construct a tracker instance based on *cfg* and *kind*."""
    tracker_kind = kind or cfg.tracker.type
    if tracker_kind == "bytetrack":
        return ByteTrackLikeTracker()
    raise ValueError(f"unknown tracker type: {tracker_kind}")


def build_embedder(
    cfg: Any,
    *,
    clip_runner,
    dim: int = 512,
    normalize: bool = True,
):
    """Construct a :class:`ClipLikeEmbedder` using *cfg* and injected runner."""
    if clip_runner is None:
        raise NotImplementedError(
            "clip_runner required for ClipLikeEmbedder in M1-03"
        )
    return ClipLikeEmbedder(
        clip_runner,
        dim=dim,
        normalize=normalize,
        batch_size=cfg.embedder.batch_size,
    )


__all__ = ["build_detector", "build_tracker", "build_embedder"]
