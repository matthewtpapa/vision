# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Evaluator utilities."""

from __future__ import annotations

import itertools
import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from . import __version__
from .config import get_config
from .detect_adapter import FakeDetector
from .embedder_adapter import ClipLikeEmbedder
from .eval_reporting import metrics_json
from .pipeline_detect_track_embed import DetectTrackEmbedPipeline
from .provenance import collect_provenance
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


def run_eval(
    input_dir: str,
    output_dir: str,
    warmup: int,
    *,
    budget_ms: int = 33,
    sustain_minutes: int = 0,
) -> int:
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

    start_ns = time.perf_counter_ns()
    deadline = None
    if sustain_minutes > 0:
        deadline = time.perf_counter() + sustain_minutes * 60.0
        warmup = 100

    frame_iter = frames if sustain_minutes == 0 else itertools.cycle(frames)

    first_result_ns: int | None = None
    bootstrap_ns: int | None = None
    processed = 0
    for frame_path in frame_iter:
        if deadline is not None and time.perf_counter() >= deadline:
            break
        with Image.open(frame_path) as img:
            frame = np.asarray(img.convert("RGB"))
        pipeline.process(frame)
        processed += 1
        if first_result_ns is None:
            first_result_ns = time.perf_counter_ns()
        if processed == 1000 and bootstrap_ns is None:
            bootstrap_ns = time.perf_counter_ns()

    end_ns = time.perf_counter_ns()
    if first_result_ns is None:
        first_result_ns = end_ns
    if bootstrap_ns is None:
        bootstrap_ns = end_ns

    cold_start_ms = (first_result_ns - start_ns) / 1e6
    bootstrap_ms = (bootstrap_ns - start_ns) / 1e6

    pipeline.flush_telemetry_csv(str(out_dir / "stage_timings.csv"))

    per_frame_ms, per_stage_ms, unknown_flags = pipeline.get_eval_counters()
    frames_total = len(per_frame_ms)

    selected = pipeline.backend_selected()
    backend: Literal["faiss", "numpy"] = "faiss" if selected == "faiss" else "numpy"

    metrics = metrics_json(
        per_frame_ms,
        per_stage_ms,
        unknown_flags,
        pipeline.kb_size(),
        backend,
        __version__,
        warmup=warmup,
        slo_budget_ms=float(budget_ms),
    )
    prov = collect_provenance(frames)
    metrics.update(prov)
    metrics.update(
        {
            "cold_start_ms": cold_start_ms,
            "bootstrap_ms": bootstrap_ms,
        }
    )
    cfg_block = pipeline.controller_config()
    metrics["controller"] = {
        **cfg_block,
        "end_stride": pipeline.current_stride(),
        "frames_total": frames_total,
        "frames_processed": pipeline.frames_processed(),
        "p95_window_ms": pipeline.last_window_p95(),
    }
    _atomic_write_json(out_dir / "metrics.json", metrics)

    budget = float(budget_ms)
    exit_code = 2 if metrics["p95_ms"] > budget else 0

    return exit_code


__all__ = ["run_eval"]
