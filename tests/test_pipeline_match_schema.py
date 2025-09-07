# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from latency_vision.config import _reset_config_cache
from latency_vision.detect_adapter import FakeDetector
from latency_vision.embedder_adapter import ClipLikeEmbedder
from latency_vision.pipeline_detect_track_embed import DetectTrackEmbedPipeline
from latency_vision.track_bytetrack_adapter import ByteTrackLikeTracker


@pytest.fixture(autouse=True)
def reset_config_cache():
    _reset_config_cache()
    yield
    _reset_config_cache()


def test_match_payload_has_stable_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("VISION__PATHS__KB_JSON", str(tmp_path / "kb.json"))
    _reset_config_cache()

    det = FakeDetector(boxes=[(0, 0, 1, 1)])
    trk = ByteTrackLikeTracker()

    def cropper(frame, bboxes):
        return [object()]

    def runner(crops, *, dim, batch_size):
        return [[1.0, 0.0, 0.0]]

    embedder = ClipLikeEmbedder(runner, dim=3, normalize=False, batch_size=1)
    pipeline = DetectTrackEmbedPipeline(det, trk, cropper, embedder)
    out = pipeline.process(frame=None)
    assert len(out) == 1
    match = out[0].match
    assert match is not None
    assert set(match.keys()) == {"neighbors", "is_unknown"}
    assert isinstance(match["neighbors"], list)
    assert isinstance(match["is_unknown"], bool)
