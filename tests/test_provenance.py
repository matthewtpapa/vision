# SPDX-License-Identifier: Apache-2.0
"""Tests for provenance helpers."""

from __future__ import annotations

from pathlib import Path

from latency_vision.provenance import collect_provenance


def test_collect_provenance(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    data = collect_provenance([f])
    assert data["git_commit"]
    assert data["hardware_id"]
    assert len(data["fixture_hash"]) == 64
