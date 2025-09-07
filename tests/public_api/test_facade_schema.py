from __future__ import annotations

import json
from pathlib import Path

from latency_vision import add_exemplar, query_frame
from latency_vision.config import _reset_config_cache


def test_facade_exports_and_schema_keys_match_readme(tmp_path, monkeypatch):
    monkeypatch.setenv("VISION__PATHS__KB_JSON", str(tmp_path / "kb.json"))
    _reset_config_cache()

    add_exemplar("red-mug", [0.0] * 128)
    out = query_frame(object())
    example = json.loads(Path("docs/schema.md").read_text(encoding="utf-8"))
    assert set(out.keys()) == set(example.keys())
    assert isinstance(out["neighbors"], list)
    assert isinstance(out["backend"], str)
    assert isinstance(out["stride"], int)
    assert isinstance(out["budget_hit"], bool)
