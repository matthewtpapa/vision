# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Top-level package for latency_vision."""

# ruff: noqa: I001

from pathlib import Path
from collections.abc import Iterable, Sequence

try:
    from .version import __version__
except Exception:  # pragma: no cover - fallback for missing version module.
    __version__ = "0.0.0+unknown"

from .cluster_store import ClusterStore
from .config import get_config
from .detect_adapter import FakeDetector
from .embedder import Embedder
from .embedder_adapter import ClipLikeEmbedder
from .labeler import Labeler
from .matcher import Matcher
from .pipeline_detect_track_embed import DetectTrackEmbedPipeline
from .ris import ReverseImageSearchStub
from .telemetry import Telemetry
from .track_bytetrack_adapter import ByteTrackLikeTracker

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
    bb = tuple(bbox) if bbox is not None else (0, 0, 0, 0)
    store.add_exemplar(
        label=label,
        bbox=(bb[0], bb[1], bb[2], bb[3]),
        embedding=[float(x) for x in embedding],
        provenance={"source": "api"},
    )
    store.flush()


def query_frame(frame) -> dict:
    """Run detect→track→embed→match once; return a MatchResult JSON (schema v0.1)."""
    det = FakeDetector(boxes=[(50, 50, 200, 200)])
    trk = ByteTrackLikeTracker()

    def cropper(_frame, bboxes):
        return [object() for _ in bboxes]

    def runner(crops, *, dim: int, batch_size: int):
        return [[0.0] * dim for _ in crops]

    emb = ClipLikeEmbedder(runner, dim=128, normalize=True, batch_size=8)

    class _DummyMatcher:
        def add(self, vec, label):
            return None

        def add_many(self, vecs, labels):
            return None

        def topk(self, vec, k):
            return []

    pipe = DetectTrackEmbedPipeline(det, trk, cropper, emb)
    pipe._matcher = _DummyMatcher()
    tracks = pipe.process(frame)
    first = tracks[0] if tracks else None
    neighbors: list[tuple[str, float]] = []
    label = ""
    confidence = 0.0
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
