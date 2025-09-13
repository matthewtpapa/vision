# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Evaluator utilities."""

from __future__ import annotations

import csv
import itertools
import json
import os
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
    duration_min: int = 0,
    unknown_rate_band: tuple[float, float] | None = None,
    process_start_ns: int | None = None,
    cli_entry_ns: int | None = None,
) -> int:
    """Run the evaluation pipeline over frames in *input_dir*."""
    import numpy as np
    from PIL import Image

    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import json as _json

    # Resolve unknown-rate band by precedence: CLI > manifest > default
    band_min: float | None = None
    band_max: float | None = None
    if unknown_rate_band is not None:
        band_min, band_max = float(unknown_rate_band[0]), float(unknown_rate_band[1])
    else:
        manifest_path = in_dir / "manifest.json"
        if manifest_path.exists():
            try:
                m = _json.loads(manifest_path.read_text(encoding="utf-8"))
                band = m.get("unknown_rate_band")
                if isinstance(band, (list, tuple)) and len(band) == 2:  # noqa: UP038
                    band_min, band_max = float(band[0]), float(band[1])
            except Exception:
                pass
    if band_min is None or band_max is None:
        band_min, band_max = 0.10, 0.40

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

    t0_ready_ns = time.monotonic_ns()
    if process_start_ns is None:
        process_start_ns = t0_ready_ns
    deadline = None
    if duration_min > 0:
        deadline = time.monotonic() + duration_min * 60.0
        warmup = 100

    frame_iter = frames if duration_min == 0 else itertools.cycle(frames)

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

    start_anchor_ns = max(process_start_ns, t0_ready_ns)
    cold_start_ms = (first_result_ns - start_anchor_ns) / 1e6
    index_bootstrap_ms = pipeline.bootstrap_time_ms() or 0.0

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

    # Verification step for unknowns
    from latency_vision.verify.verify_worker import VerifyOutcome, VerifyWorker

    verify_times_ms: list[float] = []
    E_vals: list[float] = []
    D_vals: list[float] = []
    r_vals: list[float] = []
    diversities: list[int] = []
    accepted = rejected = 0
    verify_called = 0
    verify_manifest = "bench/verify/gallery_manifest.jsonl"
    calib_path = "bench/verify/calibration.json"
    if os.path.exists(verify_manifest) and os.path.exists(calib_path):
        vw = VerifyWorker(verify_manifest, calib_path)

        for flag in unknown_flags:
            if not flag:
                continue
            verify_called += 1
            t0 = time.monotonic_ns()
            res = vw.verify([0.0], "__unknown__")
            verify_times_ms.append((time.monotonic_ns() - t0) / 1e6)
            if isinstance(res, VerifyOutcome):
                E_vals.append(res.E)
                D_vals.append(res.D)
                r_vals.append(float(res.r))
                diversities.append(res.diversity)
            if res.accepted:
                accepted += 1
            else:
                rejected += 1

    def _percentile(vals: list[float], q: float) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        k = (len(s) - 1) * (q / 100.0)
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            return float(s[f])
        return float(s[f] * (c - k) + s[c] * (k - f))

    metrics["verify"] = {
        "called": verify_called,
        "accepted": accepted,
        "rejected": rejected,
        "E_p95": _percentile(E_vals, 95.0),
        "Δ_p95": _percentile(D_vals, 95.0),
        "r_p95": _percentile(r_vals, 95.0),
        "diversity_min": min(diversities) if diversities else 0,
    }

    if verify_times_ms:
        total_ns = int(sum(verify_times_ms) * 1_000_000)
        with (out_dir / "stage_times.csv").open("a") as fh:
            fh.write(f"verify,{total_ns},{verify_called},\n")
    prov = collect_provenance(frames)
    metrics.update(prov)
    latencies_effective = per_frame_ms[warmup:]
    in_budget = sum(1 for t in latencies_effective if t <= float(budget_ms))
    total_eff = max(1, len(latencies_effective))
    metrics.update(
        {
            "cold_start_ms": cold_start_ms,
            "index_bootstrap_ms": index_bootstrap_ms,
            "sustained_in_budget": round(in_budget / total_eff, 6),
        }
    )
    metrics["metrics_schema_version"] = "0.1"
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
    metrics["unknown_rate_band"] = [band_min, band_max]
    budget = float(budget_ms)
    exit_code = 0
    if metrics["p95_ms"] > budget:
        exit_code = 2
    ur = float(metrics.get("unknown_rate", 0.0))
    if not (band_min <= ur <= band_max):
        metrics["unknown_rate_violation"] = True
        exit_code = 2
        print(
            f"[guardrail] unknown_rate {ur:.3f} outside band [{band_min:.3f}, {band_max:.3f}]",
            file=sys.stderr,
        )
    if os.getenv("VISION_DEBUG_TIMING") == "1" and cli_entry_ns is not None:
        metrics["process_cold_start_ms"] = (first_result_ns - cli_entry_ns) / 1e6
    _atomic_write_json(out_dir / "metrics.json", metrics)

    return exit_code


__all__ = ["run_eval"]
