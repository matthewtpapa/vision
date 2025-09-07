# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Evaluator utilities."""

from __future__ import annotations

import csv
import itertools
import json
import sys
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


def _write_stage_csv(
    path: Path, per_frame_ms: list[float], controller: list[tuple[int, bool]]
) -> None:
    """Write per-frame timings and controller data to ``path``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame_idx", "total_ns", "stride", "budget_hit"])
        for idx, (ms, (stride, hit)) in enumerate(zip(per_frame_ms, controller)):
            w.writerow([idx, int(ms * 1_000_000), stride, int(hit)])


def run_eval(
    input_dir: str,
    output_dir: str,
    warmup: int,
    *,
    budget_ms: int = 33,
    sustain_minutes: int = 0,
    fixture_manifest: str | None = None,
    unknown_band: tuple[float, float] = (0.10, 0.40),
) -> int:
    """Run the evaluation pipeline over frames in *input_dir*."""
    import numpy as np
    from PIL import Image

    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import json as _json

    if fixture_manifest:
        try:
            m = _json.loads(Path(fixture_manifest).read_text(encoding="utf-8"))
            band = m.get("unknown_band")
            if isinstance(band, list | tuple) and len(band) == 2:
                unknown_band = (float(band[0]), float(band[1]))
        except Exception:
            pass

    frames = _discover_images(in_dir)

    cfg = get_config()

    detector = FakeDetector()
    tracker = ByteTrackLikeTracker()

    def cropper(frame: np.ndarray, bboxes: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
        return [frame[y1:y2, x1:x2] for x1, y1, x2, y2 in bboxes]

    def runner(crops, *, dim: int, batch_size: int) -> list[list[float]]:
        return [[0.0] * dim for _ in crops]

    embedder = ClipLikeEmbedder(runner, dim=4, normalize=False, batch_size=cfg.embedder.batch_size)

    pipeline = DetectTrackEmbedPipeline(detector, tracker, cropper, embedder)

    start_ns = time.monotonic_ns()
    deadline = None
    if sustain_minutes > 0:
        deadline = time.monotonic() + sustain_minutes * 60.0
        warmup = 100

    frame_iter = frames if sustain_minutes == 0 else itertools.cycle(frames)

    first_result_ns: int | None = None
    processed = 0
    for frame_path in frame_iter:
        if deadline is not None and time.monotonic() >= deadline:
            break
        with Image.open(frame_path) as img:
            frame = np.asarray(img.convert("RGB"))
        results = pipeline.process(frame)
        processed += 1
        if results and first_result_ns is None:
            first_result_ns = time.monotonic_ns()

    end_ns = time.monotonic_ns()
    if first_result_ns is None:
        first_result_ns = end_ns

    cold_start_ms = (first_result_ns - start_ns) / 1e6
    bootstrap_ms = pipeline.bootstrap_time_ms() or 0.0

    per_frame_ms, per_stage_ms, unknown_flags, controller_log = pipeline.get_eval_counters()
    _write_stage_csv(out_dir / "stage_times.csv", per_frame_ms, controller_log)
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
        "p50_window_ms": pipeline.last_window_p50(),
        "p95_window_ms": pipeline.last_window_p95(),
        "p99_window_ms": pipeline.last_window_p99(),
        "fps_window": pipeline.last_window_fps(),
    }
    low, high = unknown_band
    metrics["unknown_band_low"] = float(low)
    metrics["unknown_band_high"] = float(high)
    _atomic_write_json(out_dir / "metrics.json", metrics)

    budget = float(budget_ms)
    exit_code = 2 if metrics["p95_ms"] > budget else 0

    ur = float(metrics.get("unknown_rate", 0.0))
    if not (low <= ur <= high):
        exit_code = 2
        print(
            f"[guardrail] unknown_rate {ur:.3f} outside band [{low:.3f}, {high:.3f}]",
            file=sys.stderr,
        )

    return exit_code


__all__ = ["run_eval"]
