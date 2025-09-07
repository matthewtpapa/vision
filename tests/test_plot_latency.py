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
