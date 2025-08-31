# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

import pytest

pytest.importorskip("numpy")

from vision.config import _reset_config_cache
from vision.detect_adapter import FakeDetector
from vision.embedder_adapter import ClipLikeEmbedder
from vision.pipeline_detect_track_embed import DetectTrackEmbedPipeline
from vision.track_bytetrack_adapter import ByteTrackLikeTracker


@pytest.fixture(autouse=True)
def reset_cfg():
    _reset_config_cache()
    yield
    _reset_config_cache()


def test_backend_selected_and_kb_size(monkeypatch, tmp_path):
    kb = tmp_path / "kb.json"
    kb.write_text(
        json.dumps(
            {
                "exemplars": [
                    {
                        "label": "A",
                        "bbox": [0, 0, 1, 1],
                        "embedding": [1.0, 0.0, 0.0],
                        "provenance": {},
                    },
                    {
                        "label": "B",
                        "bbox": [0, 0, 1, 1],
                        "embedding": [0.0, 1.0, 0.0],
                        "provenance": {},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VISION__PATHS__KB_JSON", str(kb))

    det = FakeDetector(boxes=[(0, 0, 1, 1)])
    trk = ByteTrackLikeTracker()

    def cropper(frame, bboxes):
        return [object()]

    def runner(crops, *, dim, batch_size):
        return [[1.0, 0.0, 0.0]]

    embedder = ClipLikeEmbedder(runner, dim=3, normalize=False, batch_size=1)
    pipe = DetectTrackEmbedPipeline(det, trk, cropper, embedder)

    assert pipe.backend_selected() == "none"
    assert pipe.kb_size() == 0

    _ = pipe.process(frame=None)

    backend = pipe.backend_selected()
    assert backend in ("numpy", "faiss")
    assert pipe.kb_size() == 2
