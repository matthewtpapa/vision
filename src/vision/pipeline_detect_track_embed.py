"""Detection → tracking → embedding pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import nullcontext
from typing import Literal, cast

from .associations import TrackEmbedding
from .cluster_store import JsonClusterStore
from .config import get_config
from .detect_adapter import Detector
from .embedder_adapter import Embedder
from .index_utils import add_exemplars_to_index
from .matcher.factory import build_matcher
from .matcher.matcher_protocol import MatcherProtocol
from .matcher.types import MatchResult
from .telemetry import StageTimer, Telemetry, now_ns
from .track_adapter import Tracker
from .types import BBox, Track

Cropper = Callable[[object, list[BBox]], list[object]]


class DetectTrackEmbedPipeline:
    """Pipeline that runs detection, tracking, cropping, and embedding."""

    def __init__(
        self,
        detector: Detector,
        tracker: Tracker,
        cropper: Cropper,
        embedder: Embedder,
        telemetry: Telemetry | None = None,
    ) -> None:
        self._detector = detector
        self._tracker = tracker
        self._cropper = cropper
        self._embedder = embedder
        self._matcher: MatcherProtocol | None = None
        self._store: JsonClusterStore | None = None
        self._cfg = get_config()
        self._tel = telemetry
        self._eval_per_frame_ms: list[float] = []
        self._eval_stage_ms: dict[str, list[float]] = {}
        self._eval_unknown_flags: list[bool] = []

    def process(self, frame) -> list[TrackEmbedding]:
        """Run the detector, tracker, cropper, and embedder on *frame*."""
        frame_t0 = now_ns()
        cm = StageTimer(self._tel, "frame") if self._tel else nullcontext()
        with cm:
            t0 = now_ns()
            with StageTimer(self._tel, "detect") if self._tel else nullcontext():
                detections = self._detector.detect(frame)
            detect_ms = (now_ns() - t0) / 1e6
            self._eval_stage_ms.setdefault("detect", []).append(detect_ms)

            t0 = now_ns()
            with StageTimer(self._tel, "track") if self._tel else nullcontext():
                tracks: list[Track] = self._tracker.update(detections)
            track_ms = (now_ns() - t0) / 1e6
            self._eval_stage_ms.setdefault("track", []).append(track_ms)

            bboxes = [t.bbox for t in tracks]
            with StageTimer(self._tel, "crop") if self._tel else nullcontext():
                crops = self._cropper(frame, bboxes)

            t0 = now_ns()
            with StageTimer(self._tel, "embed") if self._tel else nullcontext():
                embeddings = self._embedder.encode(crops)
            embed_ms = (now_ns() - t0) / 1e6
            self._eval_stage_ms.setdefault("embed", []).append(embed_ms)

            results: list[TrackEmbedding] = []
            match_total = 0.0
            for track, emb in zip(tracks, embeddings):
                if self._matcher is None:
                    dim = emb.dim
                    matcher = build_matcher(dim)
                    store = JsonClusterStore(self._cfg.paths.kb_json)
                    added = add_exemplars_to_index(matcher, store.load_all())
                    logging.info("[matcher] bootstrap: %s exemplars", added)
                    self._matcher = matcher
                    self._store = store

                    def _on_exemplar(item: dict[str, object]) -> None:
                        # item has keys: "label", "embedding", ...
                        vec = cast(list[float], item["embedding"])
                        lab = str(item["label"])
                        assert self._matcher is not None
                        self._matcher.add(vec, lab)

                    self._store.add_listener(_on_exemplar)
                assert self._matcher is not None
                t0_match = now_ns()
                with StageTimer(self._tel, "match") if self._tel else nullcontext():
                    neighbors = self._matcher.topk(emb.vec, k=self._cfg.matcher.topk)
                match_ms = (now_ns() - t0_match) / 1e6
                match_total += match_ms
                above = [(lab, s) for (lab, s) in neighbors if s >= self._cfg.matcher.threshold]
                is_unknown = len(above) < self._cfg.matcher.min_neighbors
                payload: MatchResult = {"neighbors": neighbors, "is_unknown": is_unknown}
                results.append(
                    TrackEmbedding(
                        track=track,
                        embedding=emb,
                        match=payload,
                    )
                )
            self._eval_stage_ms.setdefault("match", []).append(match_total)
        frame_ms = (now_ns() - frame_t0) / 1e6
        self._eval_per_frame_ms.append(frame_ms)
        frame_unknown = len(results) == 0 or all(
            cast(MatchResult, r.match)["is_unknown"] for r in results
        )
        self._eval_unknown_flags.append(frame_unknown)
        return results

    def flush_telemetry_csv(self, path: str | None = None) -> None:
        """Write accumulated telemetry to ``path`` or config default."""

        if self._tel is None:
            return
        out = path or self._cfg.paths.telemetry_csv
        self._tel.write_csv(out)

    def backend_selected(self) -> Literal["faiss", "numpy", "none"]:
        """Return the matcher backend selected by this pipeline."""

        if self._matcher is None:
            return "none"
        name = self._matcher.__class__.__name__.lower()
        return "faiss" if "faiss" in name else "numpy"

    def kb_size(self) -> int:
        """Return the number of exemplars in the knowledge base."""

        return len(self._store.load_all()) if self._store else 0

    def get_eval_counters(self) -> tuple[list[float], dict[str, list[float]], list[bool]]:
        """Return accumulated (per_frame_ms, per_stage_ms, unknown_flags)."""

        return self._eval_per_frame_ms, self._eval_stage_ms, self._eval_unknown_flags

    def reset_eval_counters(self) -> None:
        """Clear accumulated evaluation counters."""

        self._eval_per_frame_ms.clear()
        self._eval_stage_ms.clear()
        self._eval_unknown_flags.clear()


__all__ = ["DetectTrackEmbedPipeline", "Cropper"]
