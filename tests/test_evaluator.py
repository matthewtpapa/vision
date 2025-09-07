# SPDX-License-Identifier: Apache-2.0
"""Tests for evaluator helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from vision import evaluator  # noqa: E402


def _create_frames(path: Path) -> None:
    path.mkdir()
    for i in range(2):
        Image.new("RGB", (8, 8), color=(i, 0, 0)).save(path / f"{i}.png")


def test_sustain_enforces_warmup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    _create_frames(in_dir)
    out_dir.mkdir()

    captured: dict[str, int] = {}

    def fake_metrics_json(*args, **kwargs):
        captured["warmup"] = kwargs.get("warmup")
        return {"p95_ms": 0.0}

    monkeypatch.setattr(evaluator, "metrics_json", fake_metrics_json)

    evaluator.run_eval(str(in_dir), str(out_dir), warmup=7, sustain_minutes=0)
    assert captured["warmup"] == 7

    evaluator.run_eval(str(in_dir), str(out_dir), warmup=7, sustain_minutes=1)
    assert captured["warmup"] == 100
