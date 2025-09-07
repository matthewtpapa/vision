# SPDX-License-Identifier: Apache-2.0
"""Tests for cold-start measurement startpoint."""

from __future__ import annotations

import json
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


def test_cold_start_respects_process_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = tmp_path / "in"
    out = tmp_path / "o"
    _create_frame(in_dir)

    # Fake timestamps: ready=100ms, first result=200ms, end=250ms
    calls = iter([100_000_000, 200_000_000, 250_000_000])

    def fake_monotonic_ns() -> int:
        return next(calls)

    monkeypatch.setattr(evaluator.time, "monotonic_ns", fake_monotonic_ns)

    evaluator.run_eval(str(in_dir), str(out), warmup=0, process_start_ns=150_000_000)
    cold_start = _cold_start(out / "metrics.json")

    assert 49.0 <= cold_start <= 51.0
