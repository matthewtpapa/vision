# SPDX-License-Identifier: Apache-2.0
"""Tests for unknown_rate_band precedence."""

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


def _read_band(metrics_path: Path) -> list[float]:
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    return data["unknown_rate_band"]


def test_cli_overrides_manifest(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    _create_frame(in_dir)
    (in_dir / "manifest.json").write_text(
        json.dumps({"unknown_rate_band": [0.5, 0.6]}), encoding="utf-8"
    )
    evaluator.run_eval(
        str(in_dir),
        str(out_dir),
        warmup=0,
        unknown_rate_band=(0.1, 0.2),
    )
    band = _read_band(out_dir / "metrics.json")
    assert band == [0.1, 0.2]


def test_manifest_overrides_default(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    _create_frame(in_dir)
    (in_dir / "manifest.json").write_text(
        json.dumps({"unknown_rate_band": [0.2, 0.3]}), encoding="utf-8"
    )
    evaluator.run_eval(str(in_dir), str(out_dir), warmup=0)
    band = _read_band(out_dir / "metrics.json")
    assert band == [0.2, 0.3]


def test_default_band_when_missing(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    _create_frame(in_dir)
    evaluator.run_eval(str(in_dir), str(out_dir), warmup=0)
    band = _read_band(out_dir / "metrics.json")
    assert band == [0.10, 0.40]

