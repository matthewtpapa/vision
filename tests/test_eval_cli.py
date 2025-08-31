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

pytest.importorskip("PIL")
pytest.importorskip("numpy")
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    from vision.cli import main

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

    result = run_cli("eval", "--input", str(in_dir), "--output", str(out_dir), "--warmup", "0")
    assert result.returncode == 0

    metrics_path = out_dir / "metrics.json"
    timings_path = out_dir / "stage_timings.csv"
    assert metrics_path.exists()
    assert timings_path.exists()

    data = json.loads(metrics_path.read_text())
    assert {"fps", "p50", "p95", "kb_size", "backend_selected", "stage_ms"} <= data.keys()
    assert "overhead" in data["stage_ms"]

    header = timings_path.read_text().splitlines()[0]
    for col in ["stage", "total_ms", "mean_ms", "count"]:
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
    monkeypatch.setattr("vision.telemetry.Telemetry.now_ns", lambda self: next(seq))
    monkeypatch.setattr("vision.telemetry.now_ns", lambda: next(seq))
    monkeypatch.setattr("vision.pipeline_detect_track_embed.now_ns", lambda: next(seq))
    monkeypatch.setenv("VISION__LATENCY__BUDGET_MS", "30")

    cp = run_cli("eval", "--input", str(in_dir), "--output", str(out_dir), "--warmup", "0")
    assert cp.returncode != 0
