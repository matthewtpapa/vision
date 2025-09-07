# SPDX-License-Identifier: Apache-2.0
"""Tests for latency plotting utility."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.plot_latency import render_plot  # noqa: E402

pytest.importorskip("matplotlib")


def test_plot_contains_slo_line(tmp_path: Path) -> None:
    latencies = [10.0] * 150
    out = tmp_path / "latency.png"
    fig = render_plot(latencies, 33.0, out)
    ax = fig.axes[0]
    assert any(all(y == 33.0 for y in line.get_ydata()) for line in ax.lines)
    texts = [t.get_text() for t in fig.texts]
    assert any("warm-up excluded" in t for t in texts)


def test_warmup_shaded(tmp_path: Path) -> None:
    latencies = [10.0] * 200
    out = tmp_path / "latency.png"
    fig = render_plot(latencies, 33.0, out, warmup=100)
    ax = fig.axes[0]
    patches = [p for p in ax.patches if hasattr(p, "get_xy")]
    assert any(
        min(v[0] for v in p.get_xy()) <= 0 and max(v[0] for v in p.get_xy()) >= 100 for p in patches
    )


def test_breach_spans_present(tmp_path: Path) -> None:
    lat = [10.0] * 100 + [60.0] * 60 + [10.0] * 200
    out = tmp_path / "latency.png"
    fig = render_plot(lat, 33.0, out, window=30, warmup=50)
    ax = fig.axes[0]
    assert len(ax.patches) >= 2
