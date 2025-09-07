from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

from vision.cli import main

pytest.importorskip("PIL")

def run_cli(*args: str):
    out, err, code = StringIO(), StringIO(), 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            main(list(args))
    except SystemExit as e:
        code = int(e.code)
    return code, out.getvalue(), err.getvalue()

def test_unknown_rate_guardrail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Force metrics_json unknown_rate high via monkeypatch
    import vision.evaluator as evaluator

    real_metrics_json = evaluator.metrics_json
    def fake_metrics_json(*a, **k):
        m = real_metrics_json(*a, **k)
        m["unknown_rate"] = 0.75
        return m
    monkeypatch.setattr(evaluator, "metrics_json", fake_metrics_json)

    # Minimal fixture
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    from PIL import Image
    Image.new("RGB", (8, 8)).save(in_dir / "f.png")

    # Manifest with tight band
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"unknown_band":[0.0,0.1]}), encoding="utf-8")

    code, _out, err = run_cli(
        "eval", "--input", str(in_dir), "--output", str(out_dir),
        "--warmup", "0", "--fixture-manifest", str(manifest)
    )
    assert code == 2
    assert "unknown_rate" in err
