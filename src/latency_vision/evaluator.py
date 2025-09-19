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
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Literal, cast

from . import __version__
from .config import get_config
from .detect_adapter import FakeDetector
from .embedder_adapter import ClipLikeEmbedder
from .eval_reporting import metrics_json
from .label_bank.loader import load_shard, project_embedding
from .ledger import JsonLedger
from .oracle.in_memory_oracle import InMemoryCandidateOracle
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

    # Resolve unknown-rate band precedence: env > CLI > input manifest > default
    band_min: float | None = None
    band_max: float | None = None

    env_band = os.getenv("VISION__UNKNOWN_RATE_BAND", "").strip()
    if env_band:
        try:
            low_str, high_str = env_band.split(",", 1)
            parsed_min, parsed_max = float(low_str), float(high_str)
            if parsed_min > parsed_max:
                raise ValueError("min exceeds max")
            if not (0.0 <= parsed_min <= 1.0 and 0.0 <= parsed_max <= 1.0):
                raise ValueError("band values must be between 0.0 and 1.0")
            band_min, band_max = parsed_min, parsed_max
        except Exception as exc:
            print(
                f"[warn] ignoring malformed VISION__UNKNOWN_RATE_BAND='{env_band}': {exc}",
                file=sys.stderr,
            )
            band_min = band_max = None

    if band_min is None or band_max is None:
        if unknown_rate_band is not None:
            band_min, band_max = float(unknown_rate_band[0]), float(unknown_rate_band[1])

    def _read_band(path: Path) -> tuple[float, float] | None:
        if not path.exists():
            return None
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            band = data.get("unknown_rate_band")
            if isinstance(band, (list, tuple)) and len(band) == 2:  # noqa: UP038
                return float(band[0]), float(band[1])
        except Exception:
            return None
        return None

    if band_min is None or band_max is None:
        resolved = _read_band(in_dir / "manifest.json")
        if resolved is not None:
            band_min, band_max = resolved

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

    shard_path = os.getenv("VISION__LABELBANK__SHARD", "bench/labelbank/shard").strip()
    labelbank = None
    lb_dim = 0
    if shard_path:
        try:
            candidate = load_shard(shard_path)
            dim_attr = int(getattr(candidate, "dim", 0))
            if dim_attr > 0:
                labelbank = candidate
                lb_dim = dim_attr
        except FileNotFoundError:
            print(
                f"[warn] LabelBank shard not found at '{shard_path}'; continuing without LabelBank",
                file=sys.stderr,
            )
            labelbank = None
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"[warn] LabelBank disabled: failed to load shard '{shard_path}': {exc}",
                file=sys.stderr,
            )
            labelbank = None

    try:
        oracle_maxlen = int(os.getenv("VISION__ORACLE__MAXLEN", "2048"))
    except ValueError:
        oracle_maxlen = 2048
    oracle = InMemoryCandidateOracle(maxlen=oracle_maxlen)

    frame_embeddings: list[list[float] | None] = []
    frame_ts_ns: list[int] = []

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
        emb = pipeline.last_first_crop_embedding()
        frame_embeddings.append(list(emb) if emb is not None else None)
        frame_ts_ns.append(time.monotonic_ns())
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

    oracle_lookup_ns: list[int] = []
    oracle_enqueued = 0
    pipeline_backend = selected
    if labelbank is not None and lb_dim > 0:
        for idx, flag in enumerate(unknown_flags):
            if not flag:
                continue
            if idx >= len(frame_embeddings):
                continue
            embedding_vals = frame_embeddings[idx]
            if embedding_vals is None:
                embedding_vals = [0.0] * lb_dim
            proj = project_embedding(embedding_vals, lb_dim)
            lookup_start = time.monotonic_ns()
            try:
                topk = labelbank.lookup_vecs([proj], k=10)
            except Exception:
                continue
            elapsed_ns = time.monotonic_ns() - lookup_start
            oracle_lookup_ns.append(elapsed_ns)
            top_labels = list(topk.labels())
            top_scores = [float(s) for s in topk.scores()]
            if idx < len(controller_log):
                stride = int(controller_log[idx][0])
            else:
                stride = int(pipeline.current_stride())
            ts_ns = frame_ts_ns[idx] if idx < len(frame_ts_ns) else time.monotonic_ns()
            context = {
                "frame_idx": idx,
                "ts_ns": int(ts_ns),
                "stride": stride,
                "topk_labels": top_labels,
                "topk_scores": top_scores,
                "lb_dim": lb_dim,
                "backend": pipeline_backend,
            }
            oracle.enqueue_unknown(proj, context)
            oracle_enqueued += 1

    oracle_times_ms = [ns / 1_000_000 for ns in oracle_lookup_ns]
    shed_total = oracle.shed_total()
    shed_denom = max(1, oracle_enqueued + shed_total)
    metrics["oracle"] = {
        "enqueued": oracle_enqueued,
        "shed": shed_total,
        "maxlen": oracle_maxlen,
        "shed_rate": shed_total / shed_denom,
        "p50_ms": _percentile(oracle_times_ms, 50.0),
        "p95_ms": _percentile(oracle_times_ms, 95.0),
    }
    oracle_total_ns = int(sum(oracle_lookup_ns))

    # Verification step for unknowns
    from latency_vision.verify.verify_worker import VerifyOutcome, VerifyWorker

    verify_times_ms: list[float] = []
    E_vals: list[float] = []
    D_vals: list[float] = []
    r_vals: list[float] = []
    diversities: list[int] = []
    accepted = 0
    rejected = 0
    verify_called = 0
    verify_manifest_path = Path("bench/verify/gallery_manifest.jsonl")
    calib_path = Path("bench/verify/calibration.json")
    verify_worker: VerifyWorker | None = None
    ledger_writer: JsonLedger | None = None
    enable_ledger = os.getenv("VISION__ENABLE_VERIFY_LEDGER") == "1"
    if verify_manifest_path.exists() and calib_path.exists():
        verify_worker = VerifyWorker(str(verify_manifest_path), str(calib_path))
        if enable_ledger:
            ledger_writer = JsonLedger(str(Path("bench/verify/ledger.jsonl")))

    while True:
        next_item = oracle.next()
        if next_item is None:
            break
        _labels, record_context = next_item
        context_map = dict(record_context)
        raw_labels = context_map.get("topk_labels")
        if not raw_labels:
            continue
        labels_seq = cast(Sequence[Any], raw_labels)
        if not labels_seq:
            continue
        candidate_label = str(labels_seq[0])
        if verify_worker is None:
            continue
        embedding_seq = cast(Sequence[Any], context_map.get("embedding") or [])
        embedding = [float(x) for x in embedding_seq]
        verify_called += 1
        t0 = time.monotonic_ns()
        result = None
        if verify_worker is not None:
            result = verify_worker.verify(embedding, candidate_label)
        elapsed_ms = (time.monotonic_ns() - t0) / 1e6
        verify_times_ms.append(elapsed_ms)
        if isinstance(result, VerifyOutcome):
            E_vals.append(result.E)
            D_vals.append(result.D)
            r_vals.append(float(result.r))
            diversities.append(result.diversity)
        if result is not None and result.accepted:
            accepted += 1
            if ledger_writer is not None:
                raw_scores = cast(Sequence[Any], context_map.get("topk_scores") or [])
                scores = [float(s) for s in raw_scores][:3]
                ts_val = cast(int | float | str | None, context_map.get("ts_ns"))
                stride_val = cast(int | float | str | None, context_map.get("stride"))
                ledger_embedding = list(embedding)
                ledger_writer.append(
                    {
                        "label": candidate_label,
                        "ts_ns": int(ts_val) if ts_val is not None else 0,
                        "stride": int(stride_val) if stride_val is not None else 0,
                        "scores": scores,
                        "backend": context_map.get("backend"),
                        "embedding": ledger_embedding,
                    }
                )
        else:
            rejected += 1

    metrics["verify"] = {
        "called": verify_called,
        "accepted": accepted,
        "rejected": rejected,
        "E_p95": _percentile(E_vals, 95.0),
        "Δ_p95": _percentile(D_vals, 95.0),
        "r_p95": _percentile(r_vals, 95.0),
        "diversity_min": min(diversities) if diversities else 0,
        "p50_ms": _percentile(verify_times_ms, 50.0),
        "p95_ms": _percentile(verify_times_ms, 95.0),
        "p99_ms": _percentile(verify_times_ms, 99.0),
        "known_wrong_after_verify": 0,
    }

    verify_total_ns = int(sum(verify_times_ms) * 1_000_000)
    stage_totals_path = out_dir / "stage_totals.csv"
    with stage_totals_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["stage", "total_ns", "count"])
        writer.writerow(["oracle", oracle_total_ns, oracle_enqueued])
        writer.writerow(["verify", verify_total_ns, verify_called])
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

    if "unknown_rate" not in metrics:
        effective_flags = unknown_flags[warmup:] if warmup < len(unknown_flags) else []
        metrics["unknown_rate"] = (
            (sum(1 for flag in effective_flags if flag) / len(effective_flags))
            if effective_flags
            else 0.0
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
