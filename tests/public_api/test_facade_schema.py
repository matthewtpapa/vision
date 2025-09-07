from __future__ import annotations

import json
import os

from latency_vision import add_exemplar, query_frame
from latency_vision.config import _reset_config_cache


def test_facade_exports_and_schema_keys_match_readme(tmp_path):
    os.environ["VISION__PATHS__KB_JSON"] = str(tmp_path / "kb.json")
    _reset_config_cache()

    add_exemplar("red-mug", [0.0] * 128)
    out = query_frame(object())
    example = json.loads(open("docs/schema.md", "r", encoding="utf-8").read())
    assert set(out.keys()) >= set(example.keys())

