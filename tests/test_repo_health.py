from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_schema_guide_mentions_metrics_schema_version():
    text = (ROOT / "docs" / "schema-guide.md").read_text(encoding="utf-8")
    assert "metrics_schema_version" in text


def test_benchmarks_has_cold_start_anchor():
    text = (ROOT / "docs" / "benchmarks.md").read_text(encoding="utf-8")
    assert "cold-start-definition" in text
