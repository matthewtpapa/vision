# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Evaluator utilities."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from . import __version__
from .config import get_config
from .detect_adapter import FakeDetector
from .embedder_adapter import ClipLikeEmbedder
from .eval_reporting import metrics_json
from .pipeline_detect_track_embed import DetectTrackEmbedPipeline
from .telemetry import Telemetry
from .track_bytetrack_adapter import ByteTrackLikeTracker

_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def _atomic_write_json(path: Path, obj: dict) -> None:
    """Atomically write *obj* as JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _discover_images(directory: Path) -> list[Path]:
    files: Iterable[Path] = directory.iterdir()
    return sorted(p for p in files if p.suffix.lower() in _ALLOWED_EXTS)


def run_eval(input_dir: str, output_dir: str, warmup: int) -> int:
    """Run the evaluation pipeline over frames in *input_dir*."""
    import numpy as np
    from PIL import Image

    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = _discover_images(in_dir)

    cfg = get_config()
    tel = Telemetry()

    detector = FakeDetector()
    tracker = ByteTrackLikeTracker()

    def cropper(frame: np.ndarray, bboxes: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
        return [frame[y1:y2, x1:x2] for x1, y1, x2, y2 in bboxes]

    def runner(crops, *, dim: int, batch_size: int) -> list[list[float]]:
        return [[0.0] * dim for _ in crops]

    embedder = ClipLikeEmbedder(runner, dim=4, normalize=False, batch_size=cfg.embedder.batch_size)

    pipeline = DetectTrackEmbedPipeline(detector, tracker, cropper, embedder, telemetry=tel)

    for frame_path in frames:
        with Image.open(frame_path) as img:
            frame = np.asarray(img.convert("RGB"))
        pipeline.process(frame)

    pipeline.flush_telemetry_csv(out_dir / "stage_timings.csv")

    per_frame_ms, per_stage_ms, unknown_flags = pipeline.get_eval_counters()
    n = len(per_frame_ms)
    warmup = min(max(0, warmup), n)
    if warmup:
        per_frame_ms = per_frame_ms[warmup:]
        unknown_flags = unknown_flags[warmup:]
        per_stage_ms = {k: v[warmup:] for k, v in per_stage_ms.items()}

    metrics = metrics_json(
        per_frame_ms,
        per_stage_ms,
        unknown_flags,
        pipeline.kb_size(),
        pipeline.backend_selected(),
        __version__,
    )
    _atomic_write_json(out_dir / "metrics.json", metrics)

    budget = cfg.latency.budget_ms
    exit_code = 2 if metrics["p95"] > float(budget) else 0

    return exit_code


__all__ = ["run_eval"]
