# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import pytest

from latency_vision.config import _reset_config_cache, get_config
from latency_vision.detect_adapter import FakeDetector
from latency_vision.factory import build_detector, build_tracker
from latency_vision.pipeline_detect_track import DetectTrackPipeline
from latency_vision.track_bytetrack_adapter import ByteTrackLikeTracker


@pytest.fixture(autouse=True)
def reset_config_cache():
    _reset_config_cache()
    yield
    _reset_config_cache()


def test_pipeline_runs_detect_then_track_and_returns_tracks():
    det = FakeDetector(boxes=[(10, 10, 30, 30), (50, 50, 80, 80)])
    trk = ByteTrackLikeTracker()
    pipeline = DetectTrackPipeline(det, trk)
    tracks = pipeline.process(frame=None)
    assert [t.track_id for t in tracks] == [1, 2]
    assert [t.bbox for t in tracks] == [(10, 10, 30, 30), (50, 50, 80, 80)]


def test_factory_builds_fake_detector_when_flag_true():
    cfg = get_config()
    det = build_detector(cfg, use_fake=True)
    assert isinstance(det, FakeDetector)


def test_factory_builds_yololike_detector_with_injected_runner():
    cfg = get_config()

    def fake_runner(frame, input_size):
        return [(1.2, 2.2, 10.9, 11.1, 0.9, 7)]

    det = build_detector(cfg, yolo_runner=fake_runner, score_threshold=0.25)
    detections = det.detect(None)
    assert len(detections) == 1
    detection = detections[0]
    assert detection.bbox == (1, 2, 11, 12)
    assert detection.score == 0.9
    assert detection.cls == 7


def test_factory_builds_bytetrack_from_config_default():
    cfg = get_config()
    trk = build_tracker(cfg)
    assert isinstance(trk, ByteTrackLikeTracker)


def test_factory_raises_on_unknown_tracker_kind():
    cfg = get_config()
    with pytest.raises(ValueError):
        build_tracker(cfg, kind="unknown")
