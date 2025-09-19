from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latency_vision.verify.verify_worker import VerifyWorker


def test_build_and_load_manifest(tmp_path: Path) -> None:
    out = tmp_path / "gallery_manifest.jsonl"
    cmd = [
        sys.executable,
        "scripts/verify_build_manifest.py",
        "--seed",
        "data/verify/seed_gallery/seed.jsonl",
        "--data",
        "data/verify/seed_gallery",
        "--out",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 3
    assert sum(1 for r in rows if r["label"] == "alpha") == 1
    calib = tmp_path / "calibration.json"
    calib.write_text(
        json.dumps(
            {
                "E_q": {"p5": 0.0, "p50": 0.0, "p95": 0.0},
                "Δ_q": {"p5": 0.0, "p50": 0.0, "p95": 0.0},
                "r_q": {"p5": 0.0, "p50": 0.0, "p95": 0.0},
                "diversity_min": 0,
                "sprt": {"accept": 0.0, "reject": 0.0},
            }
        )
    )
    worker = VerifyWorker(str(out), str(calib))
    count, sample = worker.load_manifest()
    assert count == 3
    assert sample is not None
    assert set(sample) == {"source", "path", "license", "phash", "label", "lang"}
