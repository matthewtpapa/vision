# SPDX-License-Identifier: Apache-2.0
"""Tests for eval CLI."""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

from latency_vision.config import _reset_config_cache

pytest.importorskip("PIL")
pytest.importorskip("numpy")
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    from latency_vision.cli import main

    out = StringIO()
    err = StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            main(list(args))
    except SystemExit as exc:  # pragma: no cover - CLI uses sys.exit
        code = int(exc.code)
    return subprocess.CompletedProcess(
        args=[sys.executable, "-m", "vision", *args],
        returncode=code,
        stdout=out.getvalue(),
        stderr=err.getvalue(),
    )


def test_eval_cli_creates_artifacts(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    for i in range(8):
        img = Image.new("RGB", (64, 64), color=(i, 0, 0))
        img.save(in_dir / f"{i}.png")

    result = run_cli(
        "eval",
        "--input",
        str(in_dir),
        "--output",
        str(out_dir),
        "--warmup",
        "0",
    )
    assert result.returncode == 0

    metrics_path = out_dir / "metrics.json"
    timings_path = out_dir / "stage_times.csv"
    assert metrics_path.exists()
    assert timings_path.exists()

    data = json.loads(metrics_path.read_text())
    expected = {
        "fps",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "kb_size",
        "backend_selected",
        "stage_ms",
        "git_commit",
        "hardware_id",
        "fixture_hash",
        "cold_start_ms",
        "bootstrap_ms",
        "slo_budget_ms",
        "slo_within_budget_pct",
        "error_budget_pct",
        "sdk_version",
    }
    assert expected <= data.keys()
    assert "overhead" in data["stage_ms"]

    header = timings_path.read_text().splitlines()[0]
    for col in ["frame_idx", "total_ns", "stride", "budget_hit"]:
        assert col in header


def test_eval_cli_budget_breach_returns_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    for i in range(6):
        img = Image.new("RGB", (64, 64), color=(i, 0, 0))
        img.save(in_dir / f"{i}.png")

    base = 1_000_000_000
    step = int(5e7)
    seq = (base + i * step for i in itertools.count())
    monkeypatch.setattr("latency_vision.telemetry.Telemetry.now_ns", lambda self: next(seq))
    monkeypatch.setattr("latency_vision.telemetry.now_ns", lambda: next(seq))
    monkeypatch.setattr("latency_vision.pipeline_detect_track_embed.now_ns", lambda: next(seq))
    monkeypatch.setenv("VISION__LATENCY__BUDGET_MS", "30")

    cp = run_cli(
        "eval",
        "--input",
        str(in_dir),
        "--output",
        str(out_dir),
        "--warmup",
        "0",
        "--budget-ms",
        "30",
    )
    assert cp.returncode != 0


def test_eval_cli_controller_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    out_dir2 = tmp_path / "out2"
    in_dir.mkdir()
    out_dir.mkdir()
    out_dir2.mkdir()

    for i in range(3):
        img = Image.new("RGB", (64, 64), color=(i, 0, 0))
        img.save(in_dir / f"{i}.png")

    cp = run_cli("eval", "--input", str(in_dir), "--output", str(out_dir), "--warmup", "0")
    assert cp.returncode == 0
    data = json.loads((out_dir / "metrics.json").read_text())
    assert "controller" in data
    c = data["controller"]
    expected_keys = {
        "auto_stride",
        "min_stride",
        "max_stride",
        "start_stride",
        "end_stride",
        "window",
        "low_water",
        "frames_total",
        "frames_processed",
        "p50_window_ms",
        "p95_window_ms",
        "p99_window_ms",
        "fps_window",
    }
    assert expected_keys <= c.keys()
    assert c["frames_processed"] <= c["frames_total"]
    assert c["min_stride"] <= c["start_stride"] <= c["max_stride"]
    assert c["min_stride"] <= c["end_stride"] <= c["max_stride"]

    monkeypatch.setenv("VISION__PIPELINE__AUTO_STRIDE", "0")
    _reset_config_cache()
    cp = run_cli(
        "eval",
        "--input",
        str(in_dir),
        "--output",
        str(out_dir2),
        "--warmup",
        "0",
    )
    assert cp.returncode == 0
    data2 = json.loads((out_dir2 / "metrics.json").read_text())
    c2 = data2["controller"]
    assert c2["start_stride"] == c2["end_stride"]
    _reset_config_cache()


def test_budget_flag_propagates(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    for i in range(3):
        img = Image.new("RGB", (64, 64), color=(i, 0, 0))
        img.save(in_dir / f"{i}.png")

    cp = run_cli(
        "eval",
        "--input",
        str(in_dir),
        "--output",
        str(out_dir),
        "--warmup",
        "0",
        "--budget-ms",
        "40",
    )
    assert cp.returncode == 0
    data = json.loads((out_dir / "metrics.json").read_text())
    assert data["slo_budget_ms"] == 40


def test_unknown_band_fields_in_metrics(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    from PIL import Image

    Image.new("RGB", (8, 8)).save(in_dir / "0.png")
    cp = run_cli(
        "eval",
        "--input",
        str(in_dir),
        "--output",
        str(out_dir),
        "--warmup",
        "0",
        "--unknown-rate-band",
        "0.2,0.8",
    )
    assert cp.returncode in (0, 2)
    data = json.loads((out_dir / "metrics.json").read_text())
    assert data["unknown_band_low"] == 0.2
    assert data["unknown_band_high"] == 0.8
