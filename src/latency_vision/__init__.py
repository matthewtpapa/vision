# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Top-level package for latency_vision."""

from pathlib import Path
from typing import Iterable, Sequence
from .embedder import Embedder
from .detect_adapter import FakeDetector
from .labeler import Labeler
from .matcher import Matcher
from .ris import ReverseImageSearchStub
from .telemetry import Telemetry
from .config import get_config
from .cluster_store import ClusterStore
from .track_bytetrack_adapter import ByteTrackLikeTracker
from .pipeline_detect_track_embed import DetectTrackEmbedPipeline
from .embedder_adapter import ClipLikeEmbedder

__version__ = "0.1.0-rc.2"
__all__ = [
    "__version__",
    "FakeDetector",
    "Embedder",
    "Matcher",
    "Labeler",
    "ReverseImageSearchStub",
    "Telemetry",
    "add_exemplar",
    "query_frame",
]

def add_exemplar(label: str, embedding: Iterable[float], bbox: Sequence[int] | None = None) -> None:
    """Persist an exemplar into the KB and notify listeners."""
    cfg = get_config()
    store = ClusterStore(Path(cfg.paths.kb_json))
    store.add_exemplar(
        label=label,
        bbox=tuple(bbox) if bbox is not None else (0, 0, 0, 0),
        embedding=[float(x) for x in embedding],
        provenance={"source": "api"},
    )
    store.flush()


def query_frame(frame) -> dict:
    """Run detect→track→embed→match once; return a MatchResult JSON (schema v0.1)."""
    det = FakeDetector()
    trk = ByteTrackLikeTracker()

    def cropper(_frame, bboxes):
        return [object() for _ in bboxes]

    def runner(crops, *, dim: int, batch_size: int):
        return [[0.0] * dim for _ in crops]

    emb = ClipLikeEmbedder(runner, dim=128, normalize=True, batch_size=8)
    pipe = DetectTrackEmbedPipeline(det, trk, cropper, emb)
    tracks = pipe.process(frame)
    first = tracks[0] if tracks else None
    neighbors = first.match["neighbors"] if first and first.match else []
    label = neighbors[0][0] if neighbors else ""
    confidence = neighbors[0][1] if neighbors else 0.0
    return {
        "label": label,
        "confidence": confidence,
        "neighbors": [{"label": lab, "score": score} for lab, score in neighbors],
        "backend": "numpy",
        "stride": 1,
        "budget_hit": False,
        "bbox": list(first.track.bbox) if first else [0, 0, 0, 0],
        "timestamp_ms": 0,
        "sdk_version": __version__,
    }
