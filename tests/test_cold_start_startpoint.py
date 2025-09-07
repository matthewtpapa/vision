# SPDX-License-Identifier: Apache-2.0
"""Tests for cold-start measurement startpoint."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from latency_vision import evaluator

pytest.importorskip("numpy")
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _create_frame(path: Path) -> None:
    path.mkdir()
    Image.new("RGB", (8, 8)).save(path / "f.png")


def _cold_start(metrics_path: Path) -> float:
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    return float(data["cold_start_ms"])


def test_cold_start_respects_process_start(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    _create_frame(in_dir)

    start = time.monotonic_ns()
    evaluator.run_eval(str(in_dir), str(out1), warmup=0, process_start_ns=start)
    base = _cold_start(out1 / "metrics.json")

    earlier = start - 1_000_000_000  # 1 second earlier
    evaluator.run_eval(str(in_dir), str(out2), warmup=0, process_start_ns=earlier)
    shifted = _cold_start(out2 / "metrics.json")

    assert 900.0 <= shifted - base <= 1100.0

