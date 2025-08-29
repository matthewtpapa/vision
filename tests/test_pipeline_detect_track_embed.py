from __future__ import annotations

import pytest

from vision.associations import TrackEmbedding
from vision.config import _reset_config_cache, get_config
from vision.detect_adapter import FakeDetector
from vision.embedder_adapter import ClipLikeEmbedder
from vision.factory import build_embedder
from vision.pipeline_detect_track_embed import DetectTrackEmbedPipeline
from vision.track_bytetrack_adapter import ByteTrackLikeTracker


@pytest.fixture(autouse=True)
def reset_config_cache():
    _reset_config_cache()
    yield
    _reset_config_cache()


def test_detect_track_embed_pipeline_calls_cropper_and_returns_aligned_pairs():
    det = FakeDetector(boxes=[(10, 10, 30, 30), (50, 50, 80, 80)])
    trk = ByteTrackLikeTracker()
    captured = {}

    def cropper(frame, bboxes):
        captured["bboxes"] = bboxes
        return [object(), object()]

    def runner(crops, *, dim, batch_size):
        return [[1, 0, 0], [0, 1, 0]]

    embedder = ClipLikeEmbedder(runner, dim=3, normalize=False, batch_size=2)
    pipeline = DetectTrackEmbedPipeline(det, trk, cropper, embedder)
    results = pipeline.process(frame=None)

    assert captured["bboxes"] == [r.track.bbox for r in results]
    assert len(results) == 2
    assert [r.track.track_id for r in results] == [1, 2]
    assert all(isinstance(r, TrackEmbedding) for r in results)
    assert all(r.embedding.dim == 3 for r in results)


def test_build_embedder_uses_cfg_batch_size():
    cfg = get_config()
    captured: dict[str, int] = {}

    def runner(crops, *, dim, batch_size):
        captured["dim"] = dim
        captured["batch_size"] = batch_size
        return [[0.0] * dim for _ in crops]

    embedder = build_embedder(cfg, clip_runner=runner, dim=4, normalize=False)
    embedder.encode([object(), object(), object()])
    assert captured["batch_size"] == cfg.embedder.batch_size
    assert captured["dim"] == 4
